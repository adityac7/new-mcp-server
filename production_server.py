#!/usr/bin/env python3
"""
Production MCP Analytics Server - TESTED VERSION
Unified server with UI and MCP on same port

ARCHITECTURE:
- Web UI at /ui (FastAPI + Jinja2)
- MCP API at /mcp (JSON-RPC 2.0)
- Single deployment, single port
"""
import os
import sys
import asyncio
import traceback
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
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

    try:
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")

    # Load dataset cache
    try:
        from server import reload_datasets_cache, listen_for_dataset_changes
        reload_datasets_cache()
        asyncio.create_task(listen_for_dataset_changes())
        print("✅ Dataset cache loaded")
    except Exception as e:
        print(f"⚠️  Cache initialization warning: {e}")

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
    return RedirectResponse(url="/ui")


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": ["ui", "mcp", "encryption", "logging"],
        "row_limit": int(os.getenv('MAX_ROWS', 40))
    }


# ============================================================================
# MCP Protocol Integration - JSON-RPC 2.0
# ============================================================================

# Import MCP tools from server.py
try:
    from server import (
        list_available_datasets,
        get_dataset_schema,
        query_dataset,
        get_dataset_sample,
        get_context
    )
    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  MCP tools import error: {e}")
    MCP_TOOLS_AVAILABLE = False


@app.api_route("/mcp", methods=["GET", "POST", "OPTIONS"])
async def mcp_endpoint(request: Request):
    """
    MCP Protocol Endpoint - JSON-RPC 2.0

    Connection URL: https://your-domain.com/mcp
    """
    try:
        # Handle OPTIONS for CORS preflight
        if request.method == "OPTIONS":
            return JSONResponse(
                {"status": "ok"},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                }
            )

        # Handle GET for basic info
        if request.method == "GET":
            return JSONResponse({
                "name": "mcp-analytics-phase2-optimized",
                "version": "2.0.0",
                "protocol": "json-rpc-2.0",
                "endpoint": "/mcp",
                "tools_available": MCP_TOOLS_AVAILABLE
            })

        # Handle POST for JSON-RPC requests
        try:
            body = await request.json()
        except Exception as e:
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                "id": None
            }, status_code=400)

        method = body.get("method", "")
        request_id = body.get("id")

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
                "id": request_id
            })

        elif method == "tools/list":
            # Return available MCP tools
            tools = [
                {
                    "name": "list_available_datasets",
                    "description": "List all available datasets with metadata",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "get_dataset_schema",
                    "description": "Get complete schema for a dataset with AI-generated descriptions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "dataset_id": {
                                "type": "integer",
                                "description": "ID of the dataset"
                            }
                        },
                        "required": ["dataset_id"]
                    }
                },
                {
                    "name": "query_dataset",
                    "description": "Execute SQL query on dataset (40 row limit, SELECT only)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "dataset_id": {
                                "type": "integer",
                                "description": "ID of the dataset"
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL SELECT query"
                            },
                            "apply_weights": {
                                "type": "boolean",
                                "description": "Apply weighting if weight column detected",
                                "default": True
                            }
                        },
                        "required": ["dataset_id", "query"]
                    }
                },
                {
                    "name": "get_dataset_sample",
                    "description": "Get sample data from a specific table",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "dataset_id": {
                                "type": "integer",
                                "description": "ID of the dataset"
                            },
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of sample rows (max 100)",
                                "default": 10
                            }
                        },
                        "required": ["dataset_id", "table_name"]
                    }
                },
                {
                    "name": "get_context",
                    "description": "Get progressive context about server and datasets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer",
                                "description": "Context level (0=rules, 1=datasets, 2=schema, 3=full)",
                                "default": 0
                            },
                            "dataset_id": {
                                "type": "integer",
                                "description": "Dataset ID (required for level 2-3)"
                            }
                        },
                        "required": []
                    }
                }
            ]

            return JSONResponse({
                "jsonrpc": "2.0",
                "result": {"tools": tools},
                "id": request_id
            })

        elif method == "tools/call":
            if not MCP_TOOLS_AVAILABLE:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": "MCP tools not available - check server logs"
                    },
                    "id": request_id
                }, status_code=500)

            # Execute a tool
            params = body.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            # Validate tool name
            valid_tools = [
                "list_available_datasets",
                "get_dataset_schema",
                "query_dataset",
                "get_dataset_sample",
                "get_context"
            ]

            if tool_name not in valid_tools:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Tool not found: {tool_name}. Available: {', '.join(valid_tools)}"
                    },
                    "id": request_id
                }, status_code=404)

            # Call the tool with error handling
            try:
                if tool_name == "list_available_datasets":
                    result = await list_available_datasets()

                elif tool_name == "get_dataset_schema":
                    dataset_id = arguments.get("dataset_id")
                    if dataset_id is None:
                        raise ValueError("dataset_id is required")
                    result = await get_dataset_schema(dataset_id=int(dataset_id))

                elif tool_name == "query_dataset":
                    dataset_id = arguments.get("dataset_id")
                    query = arguments.get("query")
                    if dataset_id is None or query is None:
                        raise ValueError("dataset_id and query are required")
                    apply_weights = arguments.get("apply_weights", True)
                    result = await query_dataset(
                        dataset_id=int(dataset_id),
                        query=str(query),
                        apply_weights=bool(apply_weights)
                    )

                elif tool_name == "get_dataset_sample":
                    dataset_id = arguments.get("dataset_id")
                    table_name = arguments.get("table_name")
                    if dataset_id is None or table_name is None:
                        raise ValueError("dataset_id and table_name are required")
                    limit = arguments.get("limit", 10)
                    result = await get_dataset_sample(
                        dataset_id=int(dataset_id),
                        table_name=str(table_name),
                        limit=int(limit)
                    )

                elif tool_name == "get_context":
                    level = arguments.get("level", 0)
                    dataset_id = arguments.get("dataset_id")
                    result = await get_context(
                        level=int(level),
                        dataset_id=int(dataset_id) if dataset_id is not None else None
                    )

                # Return successful result
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
                    "id": request_id
                })

            except ValueError as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"Invalid params: {str(e)}"
                    },
                    "id": request_id
                }, status_code=400)

            except Exception as e:
                # Log the full error for debugging
                print(f"❌ Tool execution error: {tool_name}")
                print(traceback.format_exc())

                return JSONResponse({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32000,
                        "message": f"Tool execution failed: {str(e)}"
                    },
                    "id": request_id
                }, status_code=500)

        else:
            # Unknown method
            return JSONResponse({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }, status_code=404)

    except Exception as e:
        print(f"❌ MCP endpoint error: {str(e)}")
        print(traceback.format_exc())

        return JSONResponse({
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": f"Internal server error: {str(e)}"
            },
            "id": None
        }, status_code=500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    # Allow port as first argument
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])

    print(f"🌐 Starting server on http://0.0.0.0:{port}")
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
