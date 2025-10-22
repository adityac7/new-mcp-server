#!/usr/bin/env python3
"""
MCP Analytics Server - Phase 2 Optimized
Multi-dataset support with AI-powered metadata via FastMCP
Compatible with ChatGPT and Claude Desktop via Streamable HTTP

New Features:
- Markdown responses (50% token savings)
- Progressive context loading (4 levels)
- Automatic weighting with NCCS merging
- 5-row raw data limit enforcement
- Hot-reload via Redis pub/sub
- Query logging to database
"""
import os
import argparse
import json
import time
import asyncio
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

from app.database import get_db, metadata_engine
from app.models import Dataset, DatasetSchema, Metadata
from app.encryption import get_encryption_manager
from app.services.response_formatter import ResponseFormatter
from app.services.context_service import context_service
from app.services.weighting_service import weighting_service
from app.services.query_logger import query_logger
from app.services.parallel_query_executor import parallel_executor
import sqlparse
import psycopg2

# Security configuration
MAX_ROWS = int(os.getenv('MAX_ROWS', 1000))
MAX_RAW_ROWS = 5  # Maximum rows for raw data (no aggregation)
ALLOWED_STATEMENTS = ['SELECT']

# Initialize FastMCP server
mcp = FastMCP(name="mcp-analytics-phase2-optimized")

# Global formatter instance
formatter = ResponseFormatter()


def get_active_datasets() -> List[Dict]:
    """Get all active datasets with rich information"""
    db = next(get_db())
    try:
        datasets = db.query(Dataset).filter(Dataset.is_active == True).all()
        result = []
        
        for ds in datasets:
            # Get row count from the dataset
            row_count = None
            table_count = 0
            column_count = 0
            has_metadata = False
            
            try:
                # Get connection and query for stats
                encryption_manager = get_encryption_manager()
                connection_string = encryption_manager.decrypt(ds.connection_string_encrypted)
                if connection_string.startswith('postgres://'):
                    connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
                
                conn = psycopg2.connect(connection_string)
                cur = conn.cursor()
                
                # Get table count
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                table_count = cur.fetchone()[0]
                
                # Get row count from main table (assuming table name = dataset name)
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {ds.name}")
                    row_count = cur.fetchone()[0]
                except:
                    pass  # Table might not exist or have different name
                
                cur.close()
                conn.close()
            except:
                pass  # Don't fail if we can't get stats
            
            # Get schema info
            schema_entries = db.query(DatasetSchema).filter(
                DatasetSchema.dataset_id == ds.id
            ).all()
            column_count = len(schema_entries)
            
            # Check if metadata exists
            metadata_entries = db.query(Metadata).filter(
                Metadata.dataset_id == ds.id
            ).first()
            has_metadata = metadata_entries is not None or ds.metadata_text is not None
            
            result.append({
                'id': ds.id,
                'name': ds.name,
                'description': ds.description,
                'row_count': row_count,
                'table_count': table_count,
                'column_count': column_count,
                'has_metadata': has_metadata,
                'created_at': ds.created_at.isoformat() if ds.created_at else None
            })
        
        return result
    finally:
        db.close()


def get_dataset_connection(dataset_id: int):
    """Get decrypted connection string for a dataset"""
    db = next(get_db())
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.is_active:
            return None
        
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        # Fix postgres:// to postgresql://
        if connection_string.startswith('postgres://'):
            connection_string = connection_string.replace('postgres://', 'postgresql://', 1)
        
        return connection_string
    finally:
        db.close()


def validate_query(query: str) -> tuple[bool, str]:
    """Validate that the query is safe to execute"""
    parsed = sqlparse.parse(query)
    if not parsed:
        return False, "Empty or invalid query"
    
    for statement in parsed:
        stmt_type = statement.get_type()
        if stmt_type not in ALLOWED_STATEMENTS:
            return False, f"Only SELECT statements allowed. Got: {stmt_type}"
        
        dangerous = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        query_upper = query.upper()
        for keyword in dangerous:
            if keyword in query_upper:
                return False, f"Dangerous keyword: {keyword}"
    
    return True, ""


def execute_query_on_dataset(
    dataset_id: int,
    query: str,
    limit: int = None,
    apply_weights: bool = True,
    apply_nccs_merging: bool = True
) -> Dict[str, Any]:
    """
    Execute a SQL query on a specific dataset with automatic optimizations

    Args:
        dataset_id: ID of dataset to query
        query: SQL SELECT query
        limit: Row limit (None = auto-detect based on query type)
        apply_weights: Apply weighting if weight column detected
        apply_nccs_merging: Apply NCCS merging rules

    Returns:
        Dict with success, rows, columns, metadata
    """
    start_time = time.time()

    # Validate query
    is_valid, error_msg = validate_query(query)
    if not is_valid:
        return {'success': False, 'error': error_msg}

    # Get connection string
    connection_string = get_dataset_connection(dataset_id)
    if not connection_string:
        return {'success': False, 'error': 'Dataset not found or inactive'}

    # Detect query type and apply appropriate limit
    is_aggregated = weighting_service.is_aggregated_query(query)

    if limit is None:
        # Auto-detect limit based on query type
        if is_aggregated:
            limit = MAX_ROWS  # Aggregated queries can return more rows
        else:
            limit = MAX_RAW_ROWS  # Raw data limited to 5 rows
    else:
        limit = min(limit, MAX_ROWS)

    query_upper = query.upper().strip()
    if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
        query = f"{query.rstrip().rstrip(';')} LIMIT {limit}"

    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        results = [dict(zip(columns, row)) for row in rows]
        cur.close()
        conn.close()

        # Detect weight column
        weight_column = weighting_service.detect_weight_column(columns) if apply_weights else None

        # Detect NCCS column
        nccs_column = weighting_service.detect_nccs_column(columns) if apply_nccs_merging else None

        # Apply NCCS merging if applicable
        if nccs_column and results:
            results = weighting_service.apply_nccs_merging(results, nccs_column)

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Determine if 5-row limit was applied
        should_limit, is_raw = weighting_service.should_apply_5_row_limit(query, len(results))
        row_limit_applied = should_limit and limit == MAX_RAW_ROWS

        return {
            'success': True,
            'rows': results,
            'columns': columns,
            'row_count': len(results),
            'execution_time_ms': execution_time_ms,
            'weight_column': weight_column,
            'nccs_column': nccs_column,
            'is_aggregated': is_aggregated,
            'row_limit_applied': row_limit_applied,
            'dataset_id': dataset_id
        }
    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return {
            'success': False,
            'error': str(e),
            'execution_time_ms': execution_time_ms
        }


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
async def list_available_datasets() -> str:
    """
    List all available datasets in the analytics platform.

    Returns:
        Markdown formatted table of datasets with id, name, and description
    """
    datasets = get_active_datasets()

    # Log the tool call
    db = next(get_db())
    try:
        query_logger.log_mcp_tool_call(
            db=db,
            tool_name='list_available_datasets',
            parameters={},
            result={'count': len(datasets)},
            execution_time_ms=0,
            tool_used='chatgpt'  # Default, will be detected from headers in production
        )
    except Exception:
        pass  # Don't fail if logging fails
    finally:
        db.close()

    return formatter.format_dataset_list(datasets)


@mcp.tool()
async def get_dataset_schema(dataset_id: int) -> str:
    """
    Get the schema metadata for a specific dataset in ONE call.

    Returns the complete schema with table structures, column types, and descriptions
    in a single markdown response. LLM can immediately use this to write queries.

    Args:
        dataset_id: ID of the dataset to get schema for

    Returns:
        Markdown formatted schema with ALL tables, columns, types, and descriptions
    """
    start_time = time.time()
    db = next(get_db())

    try:
        # Get dataset info
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset or not dataset.is_active:
            return f"❌ Error: Dataset {dataset_id} not found or inactive"

        # Return pre-generated metadata text (metadata tables already filtered out)
        if dataset.metadata_text:
            return dataset.metadata_text
        else:
            return f"""# {dataset.name}
{dataset.description or 'No description'}

⚠️  **Schema metadata not yet generated**

Run: `python3 generate_metadata.py {dataset_id}` to generate schema metadata.
"""
    finally:
        db.close()


@mcp.tool()
async def query_dataset(dataset_id: int, query: str, apply_weights: bool = True) -> str:
    """
    Execute a SQL SELECT query on a specific dataset with automatic optimizations.
    
    🚀 **For multiple queries: Call this tool multiple times in parallel!**
    Each call executes independently and returns immediately when done.
    Fast queries won't wait for slow ones.

    Features:
    - Only SELECT statements allowed
    - Raw data queries (no GROUP BY): Limited to 5 rows
    - Aggregated queries (with GROUP BY): Up to 1000 rows
    - Automatic NCCS merging applied (A1→A, C/D/E→C/D/E)
    - Weighting applied if weight column detected
    - Parallel execution when called multiple times

    Args:
        dataset_id: ID of the dataset to query
        query: SQL SELECT query to execute
        apply_weights: Apply automatic weighting (default: True)

    Returns:
        Markdown formatted results table with metadata
        
    Example - Multiple parallel queries:
        # These execute in parallel automatically:
        query_dataset(1, "SELECT gender, SUM(weights) FROM digital_insights GROUP BY gender")
        query_dataset(1, "SELECT age_bucket, SUM(weights) FROM digital_insights GROUP BY age_bucket")
        query_dataset(1, "SELECT state_grp, SUM(weights) FROM digital_insights GROUP BY state_grp")
    """
    # Execute query with all optimizations
    result = execute_query_on_dataset(
        dataset_id=dataset_id,
        query=query,
        apply_weights=apply_weights,
        apply_nccs_merging=True
    )

    # Log the query
    db = next(get_db())
    try:
        query_logger.log_query(
            db=db,
            query_text=query,
            dataset_id=dataset_id,
            execution_time_ms=result.get('execution_time_ms'),
            row_count=result.get('row_count'),
            success=result.get('success', False),
            error_message=result.get('error'),
            tool_used='chatgpt'
        )
    except Exception:
        pass
    finally:
        db.close()

    # Format response
    if not result['success']:
        return formatter.format_error(result['error'], f'Query: {query[:100]}')

    # Build markdown response
    md = formatter.format_query_result(
        result=result,
        query=query,
        is_raw_data=not result.get('is_aggregated', False),
        row_limit_applied=result.get('row_limit_applied', False)
    )

    # Add minimal metadata if applicable
    if result.get('weight_column') or result.get('nccs_column'):
        md += "\n---\n\n"
        if result.get('weight_column'):
            md += f"⚖️ Weighted: `{result['weight_column']}` | "
        if result.get('nccs_column'):
            md += f"🔄 NCCS merged: {result['nccs_column']}"
        md += "\n"

    return md


@mcp.tool()
async def get_dataset_sample(dataset_id: int, table_name: str, limit: int = 10) -> str:
    """
    Get sample data from a specific table in a dataset.

    Args:
        dataset_id: ID of the dataset
        table_name: Name of the table to sample from
        limit: Number of sample rows (max 100)

    Returns:
        Markdown formatted sample data table
    """
    limit = min(limit, 100)
    query = f"SELECT * FROM {table_name} LIMIT {limit}"

    result = execute_query_on_dataset(
        dataset_id,
        query,
        limit=limit,
        apply_weights=False,  # Don't apply weighting to samples
        apply_nccs_merging=False  # Don't merge NCCS for samples
    )

    # Log the tool call
    db = next(get_db())
    try:
        query_logger.log_mcp_tool_call(
            db=db,
            tool_name='get_dataset_sample',
            parameters={'dataset_id': dataset_id, 'table_name': table_name, 'limit': limit},
            result={'row_count': result.get('row_count', 0)},
            execution_time_ms=result.get('execution_time_ms', 0),
            tool_used='chatgpt'
        )
    except Exception:
        pass
    finally:
        db.close()

    if not result['success']:
        return formatter.format_error(result['error'], f'Table: {table_name}')

    return formatter.format_sample_data(
        dataset_id=dataset_id,
        table_name=table_name,
        sample_size=result['row_count'],
        columns=result['columns'],
        data=result['rows']
    )


@mcp.tool()
async def execute_multi_query(queries: List[Dict[str, Any]], apply_weights: bool = True) -> str:
    """
    ⚠️ **DEPRECATED** - Do not use this tool.
    
    **Use `query_dataset()` multiple times instead for true parallel execution.**
    
    Why deprecated:
    - This tool waits for ALL queries to complete before returning
    - Slow queries block fast queries
    - Single large response instead of streaming results
    - Failed queries can block successful ones
    
    **Recommended approach:**
    Instead of calling execute_multi_query() once, call query_dataset() multiple times:
    
    ✅ GOOD (Parallel, streaming responses):
    ```
    # Call these separately - they execute in parallel automatically
    query_dataset(dataset_id=1, query="SELECT gender, SUM(weights) FROM digital_insights GROUP BY gender")
    query_dataset(dataset_id=1, query="SELECT age_bucket, SUM(weights) FROM digital_insights GROUP BY age_bucket")
    query_dataset(dataset_id=1, query="SELECT app_name, SUM(weights) FROM digital_insights GROUP BY app_name LIMIT 10")
    ```
    
    ❌ BAD (Blocks until all complete):
    ```
    execute_multi_query(queries=[...])  # Don't use this
    ```
    
    Benefits of multiple query_dataset() calls:
    - Each query returns immediately when done
    - Fast queries don't wait for slow ones
    - Failed queries don't block successful ones
    - Better user experience with streaming results
    - Natural parallelism handled by the LLM client
    
    This tool is kept for backward compatibility but will be removed in a future version.
    """
    start_time = time.time()

    # Execute queries in parallel
    execution_result = await parallel_executor.execute_parallel(
        queries=queries,
        apply_weights=apply_weights,
        apply_nccs_merging=True
    )

    # Log the multi-query execution
    db = next(get_db())
    try:
        query_logger.log_mcp_tool_call(
            db=db,
            tool_name='execute_multi_query',
            parameters={'num_queries': len(queries), 'apply_weights': apply_weights},
            result=execution_result,
            execution_time_ms=execution_result.get('total_execution_time_ms', 0),
            tool_used='chatgpt'
        )
    except Exception:
        pass
    finally:
        db.close()

    # Handle execution error
    if not execution_result.get('success', False):
        return formatter.format_error(
            execution_result.get('error', 'Unknown error'),
            f"Multi-query execution with {len(queries)} queries"
        )

    # Format as combined Markdown response
    md = formatter.format_multi_query_results(
        results=execution_result['results'],
        queries=queries,
        metadata=execution_result
    )

    return md


@mcp.tool()
async def get_context(level: int = 0, dataset_id: Optional[int] = None) -> str:
    """
    Get progressive context about the MCP server and datasets.

    Context Levels:
    - Level 0: Global rules (weighting, NCCS merging, output rules)
    - Level 1: List of all active datasets
    - Level 2: Detailed schema for specific dataset (requires dataset_id)
    - Level 3: Full details with samples (requires dataset_id)

    Args:
        level: Context level (0-3)
        dataset_id: Dataset ID (required for levels 2-3)

    Returns:
        Markdown formatted context
    """
    db = next(get_db()) if level >= 1 else None

    try:
        context = context_service.build_progressive_context(
            required_level=level,
            dataset_id=dataset_id,
            db=db
        )

        # Log the tool call
        if db:
            query_logger.log_mcp_tool_call(
                db=db,
                tool_name='get_context',
                parameters={'level': level, 'dataset_id': dataset_id},
                result={'level': level},
                execution_time_ms=0,
                tool_used='chatgpt'
            )

        return context
    finally:
        if db:
            db.close()


# ============================================================================
# Hot-Reload Support (Redis Pub/Sub)
# ============================================================================

# Global dataset cache
_dataset_cache = None
_cache_timestamp = None


def reload_datasets_cache():
    """Reload dataset cache from database"""
    global _dataset_cache, _cache_timestamp
    _dataset_cache = get_active_datasets()
    _cache_timestamp = time.time()
    print(f"✅ Reloaded dataset cache: {len(_dataset_cache)} datasets")


async def listen_for_dataset_changes():
    """
    Background task to listen for dataset activation events via Redis pub/sub

    This enables hot-reload: when a new dataset is approved via the API,
    the MCP server automatically picks it up without restart.
    """
    try:
        # Check if Redis is available
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

        # Import redis only if available
        try:
            import redis.asyncio as aioredis
        except ImportError:
            print("⚠️  Redis not available - hot-reload disabled")
            return

        # Connect to Redis
        redis_client = await aioredis.from_url(redis_url, decode_responses=True)
        pubsub = redis_client.pubsub()

        # Subscribe to dataset activation channel
        await pubsub.subscribe('channel:dataset:activated')
        print("🔔 Listening for dataset changes on Redis pub/sub...")

        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                print(f"📢 Dataset activated: {data.get('name')} (ID: {data.get('dataset_id')})")

                # Reload dataset cache
                reload_datasets_cache()

    except Exception as e:
        print(f"⚠️  Hot-reload listener error: {e}")
        print("   Continuing without hot-reload...")


async def startup_event():
    """
    Startup event handler

    Initializes dataset cache and starts hot-reload listener
    """
    print("🚀 MCP Server starting up...")

    # Initialize dataset cache
    reload_datasets_cache()

    # Start hot-reload listener in background (non-blocking)
    asyncio.create_task(listen_for_dataset_changes())

    print("✅ MCP Server ready!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Analytics Server Phase 2")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    print(f"🚀 Starting MCP Analytics Server Phase 2 - Optimized Edition")
    print(f"   - MCP endpoint: http://{args.host}:{args.port}/mcp")
    print()
    print(f"📊 Features:")
    print(f"   ✓ Multi-dataset support")
    print(f"   ✓ AI-powered metadata (gpt-4.1-mini)")
    print(f"   ✓ Markdown responses (50% token savings)")
    print(f"   ✓ Progressive context loading (4 levels)")
    print(f"   ✓ Automatic weighting & NCCS merging")
    print(f"   ✓ 5-row raw data limit enforcement")
    print(f"   ✓ Hot-reload via Redis pub/sub")
    print(f"   ✓ Query logging to database")
    print()
    print(f"🛠️  MCP Tools Available:")
    print(f"   1. list_available_datasets()")
    print(f"   2. get_dataset_schema(dataset_id)")
    print(f"   3. query_dataset(dataset_id, query, apply_weights=True)")
    print(f"   4. get_dataset_sample(dataset_id, table_name, limit=10)")
    print(f"   5. execute_multi_query(queries[], apply_weights=True)  ⚡ NEW!")
    print(f"   6. get_context(level=0-3, dataset_id=None)")
    print()
    print(f"💡 Pro Tip: Use execute_multi_query() for multiple queries = ONE approval!")
    print()

    # Initialize server (dataset cache + hot-reload listener)
    print("Initializing server...")
    asyncio.run(startup_event())

    # Start the server with HTTP transport (uses Streamable HTTP protocol internally)
    # This creates a /mcp endpoint that both ChatGPT and Claude Desktop can connect to
    mcp.run(transport="http", host=args.host, port=args.port)

