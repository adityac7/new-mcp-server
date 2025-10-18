#!/usr/bin/env python3
"""
MCP Analytics Server - Cloud Deployment with MCP Protocol Support
"""
import os
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
import psycopg2
import sqlparse
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.types import Tool, TextContent, Prompt, PromptMessage
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-analytics-server")

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Security configuration
MAX_ROWS = 1000
ALLOWED_STATEMENTS = ['SELECT']

# Create FastAPI app
app = FastAPI(title="MCP Analytics Server", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyticsDB:
    """Database operations"""
    
    @staticmethod
    def get_connection():
        return psycopg2.connect(DATABASE_URL)
    
    @staticmethod
    def validate_query(query: str) -> tuple[bool, str]:
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
    
    @staticmethod
    def execute_query(query: str, limit: Optional[int] = None) -> Dict[str, Any]:
        is_valid, error_msg = AnalyticsDB.validate_query(query)
        if not is_valid:
            return {'success': False, 'error': error_msg, 'rows': [], 'columns': []}
        
        if limit is None:
            limit = MAX_ROWS
        else:
            limit = min(limit, MAX_ROWS)
        
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
            query = f"{query.rstrip().rstrip(';')} LIMIT {limit}"
        
        try:
            conn = AnalyticsDB.get_connection()
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
            logger.error(f"Query error: {e}")
            return {'success': False, 'error': str(e), 'rows': [], 'columns': []}

# Create MCP server
mcp_server = Server("analytics-server")

@mcp_server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="execute_query",
            description="Execute SQL SELECT query on digital_insights database (max 1000 rows)",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string", "description": "SQL SELECT query"}},
                "required": ["query"]
            }
        ),
        Tool(
            name="get_schema",
            description="Get table schema with column names and types",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_sample_data",
            description="Get sample data (up to 100 rows)",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "number", "default": 10}}
            }
        ),
        Tool(
            name="get_stats",
            description="Get database statistics",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    try:
        if name == "execute_query":
            result = AnalyticsDB.execute_query(arguments.get("query"))
            if result['success']:
                return [TextContent(type="text", text=json.dumps({
                    'row_count': result['row_count'],
                    'columns': result['columns'],
                    'data': result['rows']
                }, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        elif name == "get_schema":
            query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'digital_insights'
            ORDER BY ordinal_position;
            """
            result = AnalyticsDB.execute_query(query)
            if result['success']:
                return [TextContent(type="text", text=json.dumps({
                    'table': 'digital_insights',
                    'columns': result['rows']
                }, indent=2))]
            else:
                return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        elif name == "get_sample_data":
            limit = min(arguments.get("limit", 10), 100)
            result = AnalyticsDB.execute_query(f"SELECT * FROM digital_insights LIMIT {limit}")
            if result['success']:
                return [TextContent(type="text", text=json.dumps({
                    'sample_size': result['row_count'],
                    'data': result['rows']
                }, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        elif name == "get_stats":
            result = AnalyticsDB.execute_query("""
                SELECT type, COUNT(*) as count, AVG(duration_sum) as avg_duration
                FROM digital_insights GROUP BY type
            """)
            if result['success']:
                return [TextContent(type="text", text=json.dumps({
                    'platforms': result['rows']
                }, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

# FastAPI routes
@app.get("/")
async def root():
    return {
        "name": "MCP Analytics Server",
        "version": "1.0.0",
        "description": "Digital Insights Analytics - 839K rows",
        "status": "running",
        "mcp_endpoint": "/sse"
    }

@app.get("/health")
async def health():
    try:
        conn = AnalyticsDB.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM digital_insights")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"status": "healthy", "database": "connected", "rows": count}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/sse")
async def sse_endpoint(request: Request):
    """MCP Server-Sent Events endpoint"""
    
    async def event_generator():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected'})}\n\n"
            
            # Keep connection alive
            while True:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(1)
                yield f": keepalive\n\n"
        except Exception as e:
            logger.error(f"SSE error: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/messages")
async def handle_messages(request: Request):
    """Handle MCP protocol messages"""
    try:
        body = await request.json()
        method = body.get("method")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "analytics-server", "version": "1.0.0"}
                }
            }
        
        elif method == "tools/list":
            tools = await list_tools()
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema
                    } for t in tools
                ]}
            }
        
        elif method == "tools/call":
            params = body.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            result = await call_tool(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {"content": [{"type": "text", "text": r.text} for r in result]}
            }
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }
    
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": body.get("id") if 'body' in locals() else None,
            "error": {"code": -32603, "message": str(e)}
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

