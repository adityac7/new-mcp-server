#!/usr/bin/env python3
"""
MCP Analytics Server - Streamable HTTP Transport (2025-06-18)
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
from mcp.types import Tool, TextContent

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
        "protocol": "Streamable HTTP (2025-06-18)",
        "mcp_endpoint": "/mcp"
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

@app.api_route("/mcp", methods=["GET", "POST"])
async def mcp_endpoint(request: Request):
    """
    Single MCP endpoint supporting both POST and GET as per Streamable HTTP spec
    """
    
    # Validate Origin header for security
    origin = request.headers.get("origin", "")
    # In production, validate against allowed origins
    
    if request.method == "GET":
        # GET request - return SSE stream
        accept = request.headers.get("accept", "")
        if "text/event-stream" not in accept:
            return JSONResponse(
                status_code=406,
                content={"error": "Accept header must include text/event-stream"}
            )
        
        async def sse_generator():
            try:
                # Send connection message
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
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    
    elif request.method == "POST":
        # POST request - handle JSON-RPC message
        try:
            body = await request.json()
            method = body.get("method")
            msg_id = body.get("id")
            
            # Check Accept header
            accept = request.headers.get("accept", "")
            supports_sse = "text/event-stream" in accept
            supports_json = "application/json" in accept
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "analytics-server", "version": "1.0.0"}
                    }
                }
                
                # For initialize, return JSON directly
                return JSONResponse(content=response)
            
            elif method == "tools/list":
                tools = await list_tools()
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": t.inputSchema
                        } for t in tools
                    ]}
                }
                
                # Return JSON response
                return JSONResponse(content=response)
            
            elif method == "tools/call":
                params = body.get("params", {})
                name = params.get("name")
                arguments = params.get("arguments", {})
                result = await call_tool(name, arguments)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": r.text} for r in result]}
                }
                
                # For tool calls, can return either SSE or JSON
                if supports_sse:
                    # Return as SSE stream
                    async def tool_sse():
                        yield f"data: {json.dumps(response)}\n\n"
                    
                    return StreamingResponse(
                        tool_sse(),
                        media_type="text/event-stream",
                        headers={"Cache-Control": "no-cache"}
                    )
                else:
                    # Return as JSON
                    return JSONResponse(content=response)
            
            # Unknown method
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                },
                status_code=400
            )
        
        except Exception as e:
            logger.error(f"MCP endpoint error: {e}")
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                },
                status_code=500
            )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

