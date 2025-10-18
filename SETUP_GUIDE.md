# MCP Analytics Server - Complete Setup Guide

## What Was Fixed

### Issues Found and Resolved:

1. **Deprecated FastMCP Configuration** ✅
   - **Before:** `FastMCP(name="...", json_response=False, stateless_http=False)`
   - **After:** `FastMCP(name="...")` (settings moved to `run()` method)
   - **Reason:** FastMCP 2.3.4+ deprecated these constructor parameters

2. **Wrong Server Startup Method** ✅
   - **Before:** `uvicorn.run(mcp.streamable_http_app, ...)`
   - **After:** `mcp.run(transport="streamable-http", ...)`
   - **Reason:** Using FastMCP's built-in run method ensures proper protocol handling

3. **Incomplete MCP Endpoint Documentation** ✅
   - **Before:** README showed `https://your-app.onrender.com`
   - **After:** README shows `https://your-app.onrender.com/mcp`
   - **Reason:** The `/mcp` endpoint is critical for Streamable HTTP protocol

## Quick Start

### Local Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your database URL
export DATABASE_URL="postgresql://user:pass@host:port/dbname"

# 3. Run the server
python server.py

# Server will start on http://localhost:8000
# MCP endpoint: http://localhost:8000/mcp
```

### Deploy to Render.com

Follow the README instructions - the server is now properly configured!

## Configuration for Different MCP Clients

### 1. ChatGPT Desktop (OpenAI)

**Requirements:**
- Plus, Pro, Business, Enterprise, or Education account
- Developer Mode enabled
- Public URL (cannot use localhost)

**Steps:**
1. Settings → Connectors → Advanced → Developer Mode
2. Enable Developer Mode
3. Add server configuration:

```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app.onrender.com/mcp"
    }
  }
}
```

**Testing:**
After adding, ask ChatGPT:
- "What tools do you have available?"
- "Show me the database schema"
- "Get sample data from the analytics database"

---

### 2. Claude Desktop

**Requirements:**
- Pro, Max, Team, or Enterprise plan
- Claude Desktop app installed

**Steps:**
1. Settings → Developer → Edit Config
2. Opens `claude_desktop_config.json`
3. Add configuration:

**For deployed server:**
```json
{
  "mcpServers": {
    "analytics": {
      "transport": {
        "type": "http",
        "url": "https://your-app.onrender.com/mcp"
      }
    }
  }
}
```

**For local development:**
```json
{
  "mcpServers": {
    "analytics": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      }
    }
  }
}
```

4. Restart Claude Desktop

**Testing:**
Ask Claude:
- "What MCP tools do you have?"
- "Get the database schema from analytics"
- "Query the analytics database for statistics"

---

### 3. Claude Code (VS Code Extension)

**Using CLI:**
```bash
# For deployed server
claude mcp add --transport http analytics https://your-app.onrender.com/mcp

# For local development
claude mcp add --transport http analytics http://localhost:8000/mcp
```

**Testing:**
- "@analytics get the database schema"
- "@analytics show me sample data"

---

## Available MCP Tools

Your server exposes these tools to MCP clients:

1. **execute_sql_query**
   - Execute SELECT queries (max 1000 rows)
   - Example: "SELECT * FROM digital_insights WHERE type='CTV'"

2. **get_database_schema**
   - Get table structure with column names and types
   - No parameters needed

3. **get_sample_data**
   - Get sample rows (default 10, max 100)
   - Example: "Get 20 sample rows"

4. **get_database_statistics**
   - Get overall stats and platform distribution
   - No parameters needed

5. **get_column_value_counts**
   - Get frequency distribution for a column
   - Valid columns: type, cat, genre, age_bucket, gender, nccs_class, state_grp, day_of_week, population, app_name

---

## Troubleshooting

### ChatGPT Can't Connect

**Symptoms:** Server doesn't appear in connectors or shows connection error

**Solutions:**
1. ✓ Verify the URL includes `/mcp`: `https://your-url.com/mcp`
2. ✓ Ensure server is deployed to a public URL (not localhost)
3. ✓ Check that Developer Mode is enabled
4. ✓ Verify you have a Plus/Pro/Enterprise account
5. ✓ Try accessing the URL in your browser - it should respond

### Claude Desktop Can't Connect

**Symptoms:** Tools don't appear or connection errors

**Solutions:**
1. ✓ Verify JSON syntax in `claude_desktop_config.json`
2. ✓ Ensure the `/mcp` endpoint is included in the URL
3. ✓ Check the transport type is `"http"` with nested `url` field
4. ✓ Restart Claude Desktop after config changes
5. ✓ Check Claude Desktop logs for errors

### Server Won't Start

**Symptoms:** Errors when running `python server.py`

**Solutions:**
1. ✓ Install dependencies: `pip install -r requirements.txt`
2. ✓ Set DATABASE_URL environment variable
3. ✓ Verify PostgreSQL database is running and accessible
4. ✓ Check that port 8000 is available (or use `--port` flag)

### Database Connection Errors

**Symptoms:** Tools return database connection errors

**Solutions:**
1. ✓ Verify DATABASE_URL format: `postgresql://user:pass@host:port/dbname`
2. ✓ Ensure database is running and accessible
3. ✓ Check that the `digital_insights` table exists
4. ✓ Verify database credentials are correct

---

## Testing the Connection

### 1. Test Server Health

```bash
# Should return server info
curl http://localhost:8000/

# Test MCP endpoint (will show MCP protocol response)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

### 2. Test from MCP Client

After configuring in ChatGPT or Claude Desktop:

**Sample prompts:**
- "What database tools do you have available?"
- "Show me the schema of the analytics database"
- "Get 10 sample rows from the digital_insights table"
- "What's the distribution of platforms (CTV vs Mobile)?"
- "Query the database for the top 10 genres by count"

---

## Key Changes Made to Fix Your Server

### File: `server.py`

**Line 25:** Removed deprecated parameters from FastMCP constructor
```python
# Before:
mcp = FastMCP(name="analytics-server", json_response=False, stateless_http=False)

# After:
mcp = FastMCP(name="analytics-server")
```

**Line 246:** Changed from uvicorn to FastMCP's run method
```python
# Before:
uvicorn.run(mcp.streamable_http_app, host=args.host, port=args.port)

# After:
mcp.run(transport="streamable-http", host=args.host, port=args.port)
```

### File: `README.md`

- Updated ChatGPT configuration to include `/mcp` endpoint
- Added Claude Desktop configuration with proper HTTP transport format
- Added Claude Code CLI configuration
- Clarified that `/mcp` endpoint is required

---

## Next Steps

1. **Deploy to Render.com** (follow main README)
2. **Configure your MCP client** (ChatGPT or Claude Desktop)
3. **Test the connection** with sample prompts
4. **Start querying your analytics data!**

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your configuration matches the examples exactly
3. Review Render logs for deployment issues
4. Test the `/mcp` endpoint directly with curl

---

**The server is now fully compatible with both ChatGPT and Claude Desktop using the latest Streamable HTTP protocol! 🚀**
