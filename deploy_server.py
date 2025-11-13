#!/usr/bin/env python3
"""
Production Deployment Server
Unified server with UI and MCP on same port
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI(
    title="MCP Analytics Server",
    description="Multi-dataset analytics with Web UI and MCP protocol",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import database and UI routes
from app.database import init_database
from app.ui.routes import router as ui_router

# Mount UI
app.include_router(ui_router)


@app.on_event("startup")
async def startup():
    """Initialize database and caches"""
    print("=" * 70)
    print("🚀 MCP Analytics Server - Production")
    print("=" * 70)
    init_database()
    print("✅ Database ready")

    # Load dataset cache
    from server import reload_datasets_cache, listen_for_dataset_changes
    reload_datasets_cache()
    asyncio.create_task(listen_for_dataset_changes())

    print()
    print("📍 Endpoints:")
    print("   • Web UI:     /ui")
    print("   • MCP API:    /mcp")
    print("   • Health:     /health")
    print("   • API Docs:   /docs")
    print()
    print("🔧 Configuration:")
    print(f"   • Max rows:   {os.getenv('MAX_ROWS', 40)}")
    print(f"   • Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print()
    print("=" * 70)
    print()


@app.get("/")
async def root():
    """Redirect to UI"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": ["ui", "mcp", "encryption", "logging"]
    }


# ============================================================================
# MCP Protocol Integration
# ============================================================================

# Import MCP tools from server.py
from server import (
    list_available_datasets,
    get_dataset_schema,
    query_dataset,
    get_dataset_sample,
    execute_multi_query,
    get_context
)


@app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
async def mcp_endpoint(request: Request):
    """
    MCP Protocol Endpoint

    This endpoint handles MCP protocol requests from ChatGPT, Claude Desktop, etc.

    Connection URL for ChatGPT/Claude:
        https://your-domain.com/mcp
    """
    try:
        # Handle OPTIONS for CORS
        if request.method == "OPTIONS":
            return JSONResponse({"status": "ok"})

        # Get request body
        if request.method == "POST":
            body = await request.json()
        else:
            body = {}

        method = body.get("method", "")

        # Handle MCP protocol methods
        if method == "initialize":
            return JSONResponse({
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mcp-analytics-phase2-optimized",
                        "version": "2.0.0"
                    },
                    "capabilities": {
                        "tools": {},
                    }
                },
                "id": body.get("id")
            })

        elif method == "tools/list":
            # Return available MCP tools
            return JSONResponse({
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "list_available_datasets",
                            "description": "List all available datasets",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "get_dataset_schema",
                            "description": "Get schema for a dataset",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset_id": {"type": "integer"}
                                },
                                "required": ["dataset_id"]
                            }
                        },
                        {
                            "name": "query_dataset",
                            "description": "Execute SQL query on dataset (40 row limit)",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset_id": {"type": "integer"},
                                    "query": {"type": "string"},
                                    "apply_weights": {"type": "boolean", "default": True}
                                },
                                "required": ["dataset_id", "query"]
                            }
                        },
                        {
                            "name": "get_dataset_sample",
                            "description": "Get sample data from a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "dataset_id": {"type": "integer"},
                                    "table_name": {"type": "string"},
                                    "limit": {"type": "integer", "default": 10}
                                },
                                "required": ["dataset_id", "table_name"]
                            }
                        },
                        {
                            "name": "get_context",
                            "description": "Get progressive context about server",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "level": {"type": "integer", "default": 0},
                                    "dataset_id": {"type": "integer"}
                                }
                            }
                        }
                    ]
                },
                "id": body.get("id")
            })

        elif method == "tools/call":
            # Execute a tool
            tool_name = body.get("params", {}).get("name")
            arguments = body.get("params", {}).get("arguments", {})

            # Call the appropriate tool
            if tool_name == "list_available_datasets":
                result = await list_available_datasets()
            elif tool_name == "get_dataset_schema":
                result = await get_dataset_schema(**arguments)
            elif tool_name == "query_dataset":
                result = await query_dataset(**arguments)
            elif tool_name == "get_dataset_sample":
                result = await get_dataset_sample(**arguments)
            elif tool_name == "get_context":
                result = await get_context(**arguments)
            else:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Tool not found: {tool_name}"},
                    "id": body.get("id")
                }, status_code=404)

            return JSONResponse({
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                },
                "id": body.get("id")
            })

        else:
            # Unknown method
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": body.get("id")
            }, status_code=404)

    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {"code": -32000, "message": str(e)},
            "id": body.get("id", None)
        }, status_code=500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
