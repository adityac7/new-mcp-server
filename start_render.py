"""
Unified startup script for Render deployment
Runs both MCP server and UI dashboard in the same process
"""
import os
import sys
import asyncio
import multiprocessing
from dotenv import load_dotenv

load_dotenv()

def run_mcp_server():
    """Run the MCP server on /mcp endpoint"""
    print("🚀 Starting MCP Server...")
    os.system(f"python server.py --port {os.getenv('PORT', 8000)}")

def run_ui_dashboard():
    """Run the UI dashboard on root endpoint"""
    print("🎨 Starting UI Dashboard...")
    port = int(os.getenv('PORT', 8000))
    os.system(f"uvicorn app.main:app --host 0.0.0.0 --port {port}")

if __name__ == "__main__":
    # For Render, we need to run UI only since MCP is embedded
    # The issue is that FastMCP's HTTP transport doesn't work well with ChatGPT
    # We need to mount the MCP endpoint in the FastAPI app
    
    print("⚠️  Running UI Dashboard only")
    print("   MCP endpoint needs to be integrated into FastAPI")
    run_ui_dashboard()

