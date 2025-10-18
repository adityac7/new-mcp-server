#!/usr/bin/env python3
"""
MCP Analytics Server - Cloud Deployment Version
Provides remote access to analytics database via HTTP
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional
import psycopg2
import sqlparse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-analytics-server")

# Database configuration from environment variables
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Security configuration
MAX_ROWS = 1000
ALLOWED_STATEMENTS = ['SELECT']

# Create FastAPI app
app = FastAPI(
    title="MCP Analytics Server",
    version="1.0.0",
    description="Digital Insights Analytics Server with CTV and mobile usage data"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyticsServer:
    """MCP Server for analytics database access"""
    
    def get_db_connection(self):
        """Create a database connection"""
        if DATABASE_URL:
            return psycopg2.connect(DATABASE_URL)
        else:
            raise Exception("DATABASE_URL environment variable not set")
    
    def validate_query(self, query: str) -> tuple[bool, str]:
        """
        Validate that the query is safe to execute
        Returns: (is_valid, error_message)
        """
        # Parse the SQL query
        parsed = sqlparse.parse(query)
        
        if not parsed:
            return False, "Empty or invalid query"
        
        # Check each statement
        for statement in parsed:
            # Get the statement type
            stmt_type = statement.get_type()
            
            if stmt_type not in ALLOWED_STATEMENTS:
                return False, f"Only SELECT statements are allowed. Got: {stmt_type}"
            
            # Check for dangerous keywords
            dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
            query_upper = query.upper()
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    return False, f"Dangerous keyword detected: {keyword}"
        
        return True, ""
    
    def execute_query(self, query: str, limit: Optional[int] = None, skip_validation: bool = False) -> Dict[str, Any]:
        """
        Execute a SQL query with safety checks
        """
        # Validate the query
        if not skip_validation:
            is_valid, error_msg = self.validate_query(query)
            if not is_valid:
                return {
                    'success': False,
                    'error': error_msg,
                    'rows': [],
                    'columns': []
                }
        
        # Apply row limit only to SELECT queries
        if limit is None:
            limit = MAX_ROWS
        else:
            limit = min(limit, MAX_ROWS)
        
        # Add LIMIT clause if not present and it's a SELECT query
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
            query_clean = query.rstrip().rstrip(';')
            query = f"{query_clean} LIMIT {limit}"
        
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Execute the query
            cur.execute(query)
            
            # Fetch results
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            cur.close()
            conn.close()
            
            return {
                'success': True,
                'rows': results,
                'columns': columns,
                'row_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'rows': [],
                'columns': []
            }
    
    def get_table_schema(self, table_name: str = 'digital_insights') -> Dict[str, Any]:
        """Get the schema information for a table"""
        query = f"""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
        """
        
        result = self.execute_query(query, skip_validation=True)
        return result
    
    def get_sample_data(self, table_name: str = 'digital_insights', limit: int = 100) -> Dict[str, Any]:
        """Get a sample of data from the table"""
        query = f"SELECT * FROM {table_name} LIMIT {min(limit, 100)}"
        return self.execute_query(query, limit=min(limit, 100))

# Create global server instance
analytics_server = AnalyticsServer()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MCP Analytics Server",
        "version": "1.0.0",
        "description": "Digital Insights Analytics Server with CTV and mobile usage data",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "schema": "/api/schema",
            "sample": "/api/sample",
            "query": "/api/query",
            "stats": "/api/stats",
            "value_counts": "/api/value_counts"
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = analytics_server.get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/schema")
async def get_schema(table: str = "digital_insights"):
    """Get table schema"""
    try:
        result = analytics_server.get_table_schema(table)
        if result['success']:
            return {
                "table": table,
                "columns": result['rows']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        logger.error(f"Schema error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sample")
async def get_sample(table: str = "digital_insights", limit: int = 10):
    """Get sample data"""
    try:
        result = analytics_server.get_sample_data(table, limit)
        if result['success']:
            return {
                "table": table,
                "sample_size": result['row_count'],
                "columns": result['columns'],
                "data": result['rows']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except Exception as e:
        logger.error(f"Sample error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def execute_query(request: Request):
    """Execute a custom SQL query"""
    try:
        body = await request.json()
        query = body.get('query')
        
        if not query:
            raise HTTPException(status_code=400, detail="Query parameter is required")
        
        result = analytics_server.execute_query(query)
        
        if result['success']:
            return {
                "row_count": result['row_count'],
                "columns": result['columns'],
                "data": result['rows']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get basic statistics about the database"""
    try:
        # Get row count
        count_result = analytics_server.execute_query("SELECT COUNT(*) as total FROM digital_insights")
        
        # Get platform distribution
        platform_result = analytics_server.execute_query("""
            SELECT type, COUNT(*) as count, AVG(duration_sum) as avg_duration
            FROM digital_insights
            GROUP BY type
        """)
        
        if count_result['success'] and platform_result['success']:
            return {
                "total_rows": count_result['rows'][0]['total'] if count_result['rows'] else 0,
                "platforms": platform_result['rows']
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to get statistics")
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/value_counts")
async def get_value_counts(request: Request):
    """Get frequency distribution for a column"""
    try:
        body = await request.json()
        column = body.get('column')
        limit = body.get('limit', 20)
        
        if not column:
            raise HTTPException(status_code=400, detail="Column parameter is required")
        
        query = f"""
        SELECT {column}, COUNT(*) as count
        FROM digital_insights
        WHERE {column} IS NOT NULL
        GROUP BY {column}
        ORDER BY count DESC
        LIMIT {limit}
        """
        
        result = analytics_server.execute_query(query)
        
        if result['success']:
            return {
                "column": column,
                "value_counts": result['rows']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Value counts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

