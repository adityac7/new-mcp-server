"""
MCP Integration for FastAPI
Integrates FastMCP server into FastAPI app for proper SSE support
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import server module
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
import asyncio
import json

# Import the MCP server instance from server.py
from server import mcp

router = APIRouter()

@router.api_route("/mcp", methods=["GET", "POST"])
async def mcp_endpoint(request: Request):
    """
    MCP protocol endpoint with proper SSE support for ChatGPT
    """
    # Get the FastMCP app
    from fastmcp.server import Server
    
    # Handle SSE connection
    if request.headers.get("accept") == "text/event-stream":
        async def event_stream():
            """Stream SSE events for MCP protocol"""
            try:
                # Initialize MCP session
                yield f"data: {json.dumps({'jsonrpc': '2.0', 'method': 'initialize', 'params': {}})}\n\n"
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(30)
                    yield f": keepalive\n\n"
                    
            except asyncio.CancelledError:
                pass
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Handle regular JSON-RPC requests
    body = await request.json()
    
    # Process MCP request
    # This is a simplified version - full implementation would use FastMCP's internal handlers
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mcp-analytics-phase2-optimized",
                "version": "2.0.0"
            }
        },
        "id": body.get("id")
    }

