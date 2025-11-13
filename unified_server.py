#!/usr/bin/env python3
"""
Unified MCP Analytics Server
Serves BOTH Web UI and MCP protocol on same port
"""
import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Load environment variables
load_dotenv()

from app.database import init_database
from app.ui.routes import router as ui_router

# Initialize FastAPI app
app = FastAPI(
    title="MCP Analytics Server - Unified",
    description="Multi-dataset analytics with Web UI and MCP protocol",
    version="2.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount UI routes
app.include_router(ui_router)


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    print("=" * 70)
    print("🚀 MCP Analytics Server - Unified Edition")
    print("=" * 70)

    # Initialize database
    init_database()
    print("✅ Database initialized")

    # Initialize dataset cache
    from server import reload_datasets_cache, listen_for_dataset_changes
    reload_datasets_cache()

    # Start hot-reload listener
    asyncio.create_task(listen_for_dataset_changes())

    print()
    print("📊 Features:")
    print("   ✓ Web UI for dataset management")
    print("   ✓ MCP protocol endpoint")
    print("   ✓ 40-row query limit")
    print("   ✓ Connection string encryption")
    print("   ✓ Query logging")
    print()


@app.get("/")
async def root():
    """Root endpoint - redirect to UI"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "endpoints": {
            "ui": "/ui",
            "mcp": "/mcp",
            "docs": "/docs"
        }
    }


# Import and mount MCP tools from server.py
from server import mcp as mcp_instance

# Mount MCP endpoint using FastMCP
# FastMCP will handle the /mcp endpoint automatically
mcp_instance.mount(app)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified MCP Analytics Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host")
    args = parser.parse_args()

    # Support port as first argument
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        args.port = int(sys.argv[1])

    port = args.port
    host = args.host

    print()
    print("🌐 Server starting on:")
    print(f"   Web UI:  http://{host}:{port}/ui")
    print(f"   MCP API: http://{host}:{port}/mcp")
    print(f"   Health:  http://{host}:{port}/health")
    print()
    print("=" * 70)
    print()

    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
