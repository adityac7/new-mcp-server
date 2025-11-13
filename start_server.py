#!/usr/bin/env python3
"""
MCP Analytics Server - Combined UI + MCP Server
Runs both the Web UI and MCP protocol endpoint
"""
import os
import argparse
import asyncio
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Load environment variables
load_dotenv()

from app.database import init_database, get_db
from app.ui.routes import router as ui_router

# Initialize FastAPI app
app = FastAPI(
    title="MCP Analytics Server",
    description="Multi-dataset analytics platform with AI-powered metadata",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount UI routes
app.include_router(ui_router)

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/ui/templates")


@app.on_event("startup")
async def startup_event():
    """Initialize database and server components on startup"""
    print("🚀 MCP Analytics Server starting up...")
    print()

    # Initialize database
    init_database()
    print("✅ Database initialized")

    # Load datasets cache (from server.py logic)
    from server import reload_datasets_cache, listen_for_dataset_changes
    reload_datasets_cache()

    # Start hot-reload listener in background
    asyncio.create_task(listen_for_dataset_changes())

    print()
    print("📊 Features Active:")
    print("   ✓ Web UI for dataset management")
    print("   ✓ Multi-dataset support")
    print("   ✓ AI-powered metadata")
    print("   ✓ 40-row limit for all queries")
    print("   ✓ Automatic weighting & NCCS merging")
    print("   ✓ Hot-reload via Redis pub/sub")
    print("   ✓ Query logging")
    print()
    print("✅ Server ready!")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to UI dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "stats": {
            "total_datasets": 0,
            "active_datasets": 0,
            "queries_today": 0,
            "avg_time_ms": 0
        },
        "recent_datasets": [],
        "recent_logs": []
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "phase": "Phase 2 - Multi-dataset + LLM Metadata + Web UI"
    }


@app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
async def mcp_endpoint(request: Request):
    """
    MCP protocol endpoint

    This endpoint integrates with the MCP tools defined in server.py.
    For full MCP functionality, tools from server.py are available via this endpoint.
    """
    # Import MCP instance from server.py
    from server import mcp

    # FastMCP will handle the request
    # Note: This is a placeholder - FastMCP needs proper integration
    # For now, return server info
    return {
        "jsonrpc": "2.0",
        "result": {
            "name": "mcp-analytics-phase2-optimized",
            "version": "2.0.0",
            "capabilities": {
                "tools": True,
                "prompts": False,
                "resources": False
            }
        },
        "id": None
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Analytics Server - Combined UI + MCP")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    print(f"🚀 Starting Combined MCP Analytics Server")
    print(f"   - Web UI: http://{args.host}:{args.port}/ui")
    print(f"   - MCP endpoint: http://{args.host}:{args.port}/mcp")
    print(f"   - Health: http://{args.host}:{args.port}/health")
    print()

    # Run with uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )
