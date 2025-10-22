# Root Cause Analysis: Render MCP Connection Timeout

## Issue
ChatGPT connection to Render endpoint times out with OAuth error:
```
Error: failed to create connection: OAuth authentication failed: 
failed to initialize client: transport error: response should contain RPC id
```

## Findings from Render Logs

### ✅ What's Working on Render:
1. **Service is live and running**
   - Service ID: `srv-d3s5o9pr0fns73a858ug`
   - URL: `https://new-mcp-server.onrender.com`
   - Status: "Your service is live 🎉"
   - Port: 10000 (detected by Render)

2. **Application is starting correctly**
   ```
   INFO:     Started server process [7]
   INFO:     Waiting for application startup.
   ✅ Database initialized
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:10000
   ```

3. **MCP endpoint is responding**
   ```
   INFO:     POST /mcp HTTP/1.1" 200 OK
   ```
   Multiple successful POST requests to `/mcp` endpoint

4. **Database connection working**
   - ✅ Database initialized successfully
   - No connection errors

### ❌ Root Cause Identified:

**The service is running `app/main.py` (FastAPI UI) instead of `server.py` (MCP server)**

Evidence:
1. **Uvicorn is starting** (FastAPI server)
   ```
   INFO:     Uvicorn running on http://0.0.0.0:10000
   ```

2. **Database initialization message** from `app/main.py`:
   ```
   ✅ Database initialized
   ```
   This is from `app/main.py:44` startup event, NOT from `server.py`

3. **MCP endpoint is the placeholder** from `app/main.py:285-298`:
   ```python
   @app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
   async def mcp_endpoint_placeholder(request: Request):
       return {
           "jsonrpc": "2.0",
           "error": {
               "code": -32000,
               "message": "MCP endpoint available. For full MCP support, run server.py..."
           }
       }
   ```

4. **Dockerfile is being used** (not render.yaml):
   - Logs show Docker build process
   - `env: docker` in service details
   - Dockerfile CMD is probably running `app/main.py`

## Why Ngrok Link Works but Render Doesn't:

| Aspect | Ngrok (Local) | Render (Production) |
|--------|---------------|---------------------|
| **What's running** | `server.py` (FastMCP) | `app/main.py` (FastAPI) |
| **MCP endpoint** | Real FastMCP server | Placeholder returning error |
| **SSE support** | ✅ Full FastMCP SSE | ❌ JSON error response only |
| **OAuth handling** | Not required locally | Required for HTTPS endpoints |
| **Response format** | Proper MCP protocol | Error JSON (no RPC id) |

## The OAuth Error Explained:

ChatGPT sees:
1. HTTPS endpoint → Assumes production → Requires OAuth
2. Sends OAuth initialization request
3. Expects proper JSON-RPC response with `id` field
4. Gets error JSON from placeholder: `{"jsonrpc": "2.0", "error": {...}, "id": null}`
5. No `id` field → "response should contain RPC id" error

## Solution:

### Option 1: Fix Dockerfile (Recommended)
Update Dockerfile to run `server.py` instead of `app/main.py`

### Option 2: Remove Dockerfile
Delete Dockerfile so Render uses `render.yaml` configuration which specifies:
```yaml
startCommand: python server.py --port $PORT --host 0.0.0.0
```

### Option 3: Update Dockerfile CMD
Change the CMD in Dockerfile to:
```dockerfile
CMD ["python", "server.py", "--port", "${PORT}", "--host", "0.0.0.0"]
```

## Verification Steps:

After fix, Render logs should show:
```
🚀 Starting MCP Analytics Server Phase 2 - Optimized Edition
   - MCP endpoint: http://0.0.0.0:10000/mcp

📊 Features:
   ✓ Multi-dataset support
   ✓ AI-powered metadata
   ...

🛠️  MCP Tools Available:
   1. list_available_datasets()
   ...

Initializing server...
✅ MCP Server ready!
```

NOT:
```
✅ Database initialized
INFO:     Application startup complete.
```

## Action Items:

1. ✅ Check if Dockerfile exists
2. ✅ Update Dockerfile to run server.py
3. ✅ Redeploy on Render
4. ✅ Verify logs show "MCP Server ready!"
5. ✅ Test ChatGPT connection

---

**Status**: Root cause identified - wrong application running on Render
**Next**: Fix Dockerfile or remove it to use render.yaml

