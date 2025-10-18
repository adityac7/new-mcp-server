#!/usr/bin/env python3
"""
MCP Analytics Server - Using FastMCP for proper protocol support
"""
import os
import argparse
from typing import Any, Dict
import psycopg2
import sqlparse
import uvicorn
from mcp.server.fastmcp import FastMCP

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Security configuration
MAX_ROWS = 1000
ALLOWED_STATEMENTS = ['SELECT']

# Initialize FastMCP server
# json_response=False uses SSE streaming (better for real-time)
# stateless_http=False maintains session state
mcp = FastMCP(
    name="analytics-server",
    json_response=False,
    stateless_http=False
)

def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(DATABASE_URL)

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

def execute_query(query: str, limit: int = None) -> Dict[str, Any]:
    """Execute a SQL query with safety checks"""
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
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        results = [dict(zip(columns, row)) for row in rows]
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'rows': results,
            'columns': columns,
            'row_count': len(results)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

@mcp.tool()
async def execute_sql_query(query: str) -> str:
    """Execute a SQL SELECT query on the digital_insights database.
    
    Maximum 1000 rows will be returned. Only SELECT statements are allowed.
    
    Args:
        query: SQL SELECT query to execute
    
    Returns:
        JSON string with query results including row_count, columns, and data
    """
    result = execute_query(query)
    
    if result['success']:
        import json
        return json.dumps({
            'row_count': result['row_count'],
            'columns': result['columns'],
            'data': result['rows']
        }, indent=2, default=str)
    else:
        return f"Error: {result['error']}"

@mcp.tool()
async def get_database_schema() -> str:
    """Get the schema of the digital_insights table.
    
    Returns all column names, data types, and nullable information.
    
    Returns:
        JSON string with table schema information
    """
    query = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'digital_insights'
    ORDER BY ordinal_position;
    """
    
    result = execute_query(query)
    
    if result['success']:
        import json
        return json.dumps({
            'table': 'digital_insights',
            'total_columns': result['row_count'],
            'columns': result['rows']
        }, indent=2)
    else:
        return f"Error: {result['error']}"

@mcp.tool()
async def get_sample_data(limit: int = 10) -> str:
    """Get sample data from the digital_insights table.
    
    Args:
        limit: Number of sample rows to return (max 100)
    
    Returns:
        JSON string with sample data
    """
    limit = min(limit, 100)
    result = execute_query(f"SELECT * FROM digital_insights LIMIT {limit}")
    
    if result['success']:
        import json
        return json.dumps({
            'sample_size': result['row_count'],
            'columns': result['columns'],
            'data': result['rows']
        }, indent=2, default=str)
    else:
        return f"Error: {result['error']}"

@mcp.tool()
async def get_database_statistics() -> str:
    """Get statistics about the digital_insights database.
    
    Returns platform distribution (CTV vs Mobile) with counts and average durations.
    
    Returns:
        JSON string with database statistics
    """
    # Get total count
    count_result = execute_query("SELECT COUNT(*) as total FROM digital_insights")
    
    # Get platform distribution
    platform_result = execute_query("""
        SELECT 
            type as platform,
            COUNT(*) as count,
            ROUND(AVG(duration_sum)::numeric, 2) as avg_duration_seconds,
            ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())::numeric, 2) as percentage
        FROM digital_insights
        GROUP BY type
        ORDER BY count DESC
    """)
    
    if count_result['success'] and platform_result['success']:
        import json
        return json.dumps({
            'total_rows': count_result['rows'][0]['total'] if count_result['rows'] else 0,
            'platforms': platform_result['rows']
        }, indent=2, default=str)
    else:
        error = count_result.get('error') or platform_result.get('error')
        return f"Error: {error}"

@mcp.tool()
async def get_column_value_counts(column_name: str, limit: int = 20) -> str:
    """Get frequency distribution for a specific column.
    
    Args:
        column_name: Name of the column to analyze
        limit: Maximum number of values to return (default 20)
    
    Returns:
        JSON string with value counts and percentages
    """
    # Validate column name to prevent SQL injection
    valid_columns = [
        'type', 'cat', 'genre', 'age_bucket', 'gender', 'nccs_class',
        'state_grp', 'day_of_week', 'population', 'app_name'
    ]
    
    if column_name not in valid_columns:
        return f"Error: Invalid column name. Valid columns are: {', '.join(valid_columns)}"
    
    query = f"""
    SELECT 
        {column_name} as value,
        COUNT(*) as count,
        ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ())::numeric, 2) as percentage
    FROM digital_insights
    WHERE {column_name} IS NOT NULL
    GROUP BY {column_name}
    ORDER BY count DESC
    LIMIT {min(limit, 100)}
    """
    
    result = execute_query(query)
    
    if result['success']:
        import json
        return json.dumps({
            'column': column_name,
            'unique_values': result['row_count'],
            'distribution': result['rows']
        }, indent=2, default=str)
    else:
        return f"Error: {result['error']}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Analytics Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()
    
    # Start the server with Streamable HTTP transport
    # FastMCP automatically creates the /mcp endpoint
    uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)

