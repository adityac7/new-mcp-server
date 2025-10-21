"""
Enhanced MCP Server with multi-dataset support
Dynamically registers tools for each active dataset
"""
import json
from typing import Dict, Any
import psycopg2
import sqlparse
from fastmcp import FastMCP

from app.database import get_db_context, get_dataset_connection
from app.models import Dataset, DatasetSchema, Metadata, QueryLog
from app.encryption import get_encryption_manager

# Security configuration
MAX_ROWS = 1000
ALLOWED_STATEMENTS = ['SELECT']

# Initialize FastMCP server
mcp = FastMCP(name="analytics-server-multi")


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


def execute_query_on_dataset(dataset_id: int, query: str, limit: int = None) -> Dict[str, Any]:
    """Execute a SQL query on a specific dataset"""
    is_valid, error_msg = validate_query(query)
    if not is_valid:
        return {'success': False, 'error': error_msg}
    
    if limit is None:
        limit = MAX_ROWS
    else:
        limit = min(limit, MAX_ROWS)
    
    query_upper = query.upper().strip()
    if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
        query = f"{query.rstrip().rstrip(';')} LIMIT {limit}"
    
    with get_db_context() as db:
        # Get dataset
        dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.is_active == True
        ).first()
        
        if not dataset:
            return {'success': False, 'error': 'Dataset not found or inactive'}
        
        # Decrypt connection string
        encryption_manager = get_encryption_manager()
        connection_string = encryption_manager.decrypt(dataset.connection_string_encrypted)
        
        # Execute query
        try:
            start_time = __import__('time').time()
            conn = get_dataset_connection(connection_string)
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            results = [dict(zip(columns, row)) for row in rows]
            execution_time = int((__import__('time').time() - start_time) * 1000)
            cur.close()
            conn.close()
            
            # Log query
            query_log = QueryLog(
                dataset_id=dataset_id,
                query=query,
                execution_time_ms=execution_time,
                row_count=len(results),
                success=True
            )
            db.add(query_log)
            db.commit()
            
            return {
                'success': True,
                'rows': results,
                'columns': columns,
                'row_count': len(results),
                'execution_time_ms': execution_time
            }
        except Exception as e:
            # Log failed query
            query_log = QueryLog(
                dataset_id=dataset_id,
                query=query,
                success=False,
                error_message=str(e)
            )
            db.add(query_log)
            db.commit()
            
            return {'success': False, 'error': str(e)}


def get_dataset_context(dataset_id: int) -> str:
    """Get formatted context about a dataset (schema + metadata)"""
    with get_db_context() as db:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            return "Dataset not found"
        
        # Get schema grouped by table
        schemas = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id
        ).order_by(DatasetSchema.table_name, DatasetSchema.column_name).all()
        
        # Get metadata
        metadata_dict = {}
        metadata_entries = db.query(Metadata).filter(
            Metadata.dataset_id == dataset_id
        ).all()
        
        for meta in metadata_entries:
            key = f"{meta.table_name}.{meta.column_name}"
            metadata_dict[key] = meta.description
        
        # Format as markdown
        output = [f"# Dataset: {dataset.name}"]
        if dataset.description:
            output.append(f"\n{dataset.description}\n")
        
        # Group by table
        current_table = None
        for schema in schemas:
            if schema.table_name != current_table:
                current_table = schema.table_name
                output.append(f"\n## Table: {schema.table_name}")
                output.append("\n| Column | Type | Description |")
                output.append("|--------|------|-------------|")
            
            # Get metadata description
            key = f"{schema.table_name}.{schema.column_name}"
            description = metadata_dict.get(key, "")
            
            output.append(f"| {schema.column_name} | {schema.data_type} | {description} |")
        
        return "\n".join(output)


# Register MCP tools
@mcp.tool()
async def list_available_datasets() -> str:
    """List all available datasets with their IDs and descriptions.
    
    Use this first to see what datasets are available for querying.
    
    Returns:
        Markdown-formatted list of datasets
    """
    with get_db_context() as db:
        datasets = db.query(Dataset).filter(Dataset.is_active == True).all()
        
        if not datasets:
            return "No datasets available."
        
        output = ["# Available Datasets\n"]
        for ds in datasets:
            output.append(f"## Dataset ID: {ds.id}")
            output.append(f"**Name:** {ds.name}")
            if ds.description:
                output.append(f"**Description:** {ds.description}")
            output.append(f"**Created:** {ds.created_at.strftime('%Y-%m-%d')}\n")
        
        return "\n".join(output)


@mcp.tool()
async def get_dataset_schema(dataset_id: int) -> str:
    """Get the complete schema and metadata for a specific dataset.
    
    This returns table structures, column names, data types, and AI-generated descriptions.
    
    Args:
        dataset_id: The ID of the dataset (use list_available_datasets to find IDs)
    
    Returns:
        Markdown-formatted schema with metadata descriptions
    """
    return get_dataset_context(dataset_id)


@mcp.tool()
async def query_dataset(dataset_id: int, query: str) -> str:
    """Execute a SQL SELECT query on a specific dataset.
    
    Maximum 1000 rows will be returned. Only SELECT statements are allowed.
    
    Args:
        dataset_id: The ID of the dataset to query
        query: SQL SELECT query to execute
    
    Returns:
        JSON string with query results including row_count, columns, and data
    """
    result = execute_query_on_dataset(dataset_id, query)
    
    if result['success']:
        return json.dumps({
            'row_count': result['row_count'],
            'execution_time_ms': result['execution_time_ms'],
            'columns': result['columns'],
            'data': result['rows']
        }, indent=2, default=str)
    else:
        return f"Error: {result['error']}"


@mcp.tool()
async def get_dataset_sample(dataset_id: int, table_name: str, limit: int = 10) -> str:
    """Get sample data from a specific table in a dataset.
    
    Args:
        dataset_id: The ID of the dataset
        table_name: Name of the table to sample
        limit: Number of rows to return (max 100)
    
    Returns:
        JSON string with sample data
    """
    limit = min(limit, 100)
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    result = execute_query_on_dataset(dataset_id, query)
    
    if result['success']:
        return json.dumps({
            'table': table_name,
            'sample_size': result['row_count'],
            'columns': result['columns'],
            'data': result['rows']
        }, indent=2, default=str)
    else:
        return f"Error: {result['error']}"


# Mount MCP server to FastAPI
def mount_mcp_to_fastapi(app):
    """Mount the MCP server to a FastAPI app"""
    from fastapi import Request, Response
    
    @app.post("/mcp")
    @app.get("/mcp")
    async def mcp_endpoint(request: Request):
        """MCP protocol endpoint"""
        # This will be handled by FastMCP's built-in HTTP transport
        pass
    
    return mcp

