#!/usr/bin/env python3
"""
Simple UI Server Start Script
Runs the MCP Analytics Server with Web UI
"""
import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get port from environment or command line
    port = int(os.getenv("PORT", 8000))
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    host = os.getenv("HOST", "0.0.0.0")

    print("=" * 60)
    print("🚀 MCP Analytics Server - Web UI Edition")
    print("=" * 60)
    print()
    print(f"📍 Server URL: http://{host}:{port}")
    print(f"🎨 Web UI: http://{host}:{port}/ui")
    print(f"🔧 API Docs: http://{host}:{port}/docs")
    print(f"❤️  Health: http://{host}:{port}/health")
    print()
    print("Features:")
    print("  ✓ Dataset management via Web UI")
    print("  ✓ Connection string encryption")
    print("  ✓ 40-row query limit (all queries)")
    print("  ✓ Query logging & monitoring")
    print()
    print("=" * 60)
    print()

    # Run uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Set to True for development
    )
