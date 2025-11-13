# MCP Connection Guide

How to connect ChatGPT, Claude Desktop, and other MCP clients to your deployed server.

## 📍 **Your Deployment URLs**

After deploying, you'll have ONE server URL with two endpoints:

### **On Render.com:**
```
https://your-app-name.onrender.com
```

### **On Your VM:**
```
http://your-vm-ip:8000
```

---

## 🌐 **Available Endpoints**

| Endpoint | Purpose | Who Uses It |
|----------|---------|-------------|
| `/ui` | Web dashboard for managing datasets | You (via browser) |
| `/mcp` | MCP protocol API for queries | ChatGPT, Claude Desktop |
| `/health` | Health check | Monitoring tools |
| `/docs` | API documentation | Developers |

---

## 🔌 **Connecting ChatGPT**

### **Step 1: Get Your MCP URL**

Your MCP connection URL is:

**Render:**
```
https://your-app-name.onrender.com/mcp
```

**VM:**
```
http://your-vm-ip:8000/mcp
```

### **Step 2: Add to ChatGPT**

1. Open ChatGPT
2. Go to Settings → Integrations
3. Add new MCP server
4. **Server URL:** `https://your-app-name.onrender.com/mcp`
5. **Name:** `My Analytics Server`
6. Save

### **Step 3: Test Connection**

Ask ChatGPT:
```
List available datasets
```

ChatGPT should call the `list_available_datasets` tool and show your datasets.

---

## 🖥️ **Connecting Claude Desktop**

### **Option A: HTTP MCP Server**

Edit your Claude Desktop config file:

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Add your server:**

```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app-name.onrender.com/mcp",
      "transport": "http"
    }
  }
}
```

### **Option B: Using Local Proxy (for localhost)**

If your server is on `localhost:8000`:

1. Keep the server running locally
2. Use Claude Desktop's local transport:

```json
{
  "mcpServers": {
    "analytics": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

3. Restart Claude Desktop

### **Test Connection**

Ask Claude:
```
What datasets are available?
```

Claude should use the MCP tools to list your datasets.

---

## 🛠️ **Available MCP Tools**

Your server exposes these tools via the `/mcp` endpoint:

### **1. list_available_datasets**
Lists all active datasets with metadata.

**No parameters required**

**Example:**
```
Show me all available datasets
```

---

### **2. get_dataset_schema**
Get complete schema for a dataset with table structures and column descriptions.

**Parameters:**
- `dataset_id` (integer, required)

**Example:**
```
Show me the schema for dataset 1
```

---

### **3. query_dataset**
Execute SQL SELECT queries on a dataset.

**Parameters:**
- `dataset_id` (integer, required)
- `query` (string, required) - SQL SELECT statement
- `apply_weights` (boolean, optional, default: true)

**Limits:**
- Maximum 40 rows returned
- Only SELECT statements allowed

**Example:**
```
Query dataset 1: SELECT gender, COUNT(*) FROM users GROUP BY gender
```

---

### **4. get_dataset_sample**
Get sample data from a specific table.

**Parameters:**
- `dataset_id` (integer, required)
- `table_name` (string, required)
- `limit` (integer, optional, default: 10, max: 100)

**Example:**
```
Get a sample of 5 rows from the users table in dataset 1
```

---

### **5. get_context**
Get progressive context about the server and datasets.

**Parameters:**
- `level` (integer, 0-3)
  - 0: Global rules
  - 1: List of datasets
  - 2: Schema for specific dataset (requires dataset_id)
  - 3: Full details with samples (requires dataset_id)
- `dataset_id` (integer, optional)

**Example:**
```
Get full context for dataset 1
```

---

## 🧪 **Testing Your Connection**

### **Test 1: Check Health**

```bash
curl https://your-app-name.onrender.com/health
```

Should return:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "features": ["ui", "mcp", "encryption", "logging"]
}
```

### **Test 2: Check MCP Endpoint**

```bash
curl -X POST https://your-app-name.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1
  }'
```

Should return server info with capabilities.

### **Test 3: List Tools**

```bash
curl -X POST https://your-app-name.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

Should return list of 5 available tools.

---

## 🔒 **Security Notes**

### **⚠️ No Authentication**

Your MCP server has **NO authentication** by default.

**Implications:**
- Anyone with the URL can query your datasets
- Only deploy on:
  - Private networks
  - Behind VPN
  - With firewall rules

**For Production:**

1. **Use IP Whitelisting** (Render.com has this feature)
2. **Add Nginx Basic Auth**
3. **Use VPN or SSH Tunnel**
4. **Implement API Key Authentication** (custom)

### **URL Security**

Your MCP URL contains your database access:
- **Don't share publicly**
- **Don't commit to git**
- **Use environment variables**

---

## 📊 **Usage Examples**

### **Example 1: Explore Available Data**

**You:** "What datasets are available?"

**ChatGPT/Claude calls:** `list_available_datasets()`

**Response:** Shows all your datasets with names and descriptions

---

### **Example 2: Get Schema**

**You:** "Show me the structure of dataset 1"

**ChatGPT/Claude calls:** `get_dataset_schema(dataset_id=1)`

**Response:** Tables, columns, data types, and AI-generated descriptions

---

### **Example 3: Query Data**

**You:** "How many users do we have by gender in dataset 1?"

**ChatGPT/Claude calls:**
```
query_dataset(
  dataset_id=1,
  query="SELECT gender, COUNT(*) as count FROM users GROUP BY gender"
)
```

**Response:** Query results (up to 40 rows)

---

### **Example 4: Complex Analysis**

**You:** "Analyze user engagement patterns in dataset 1"

**ChatGPT/Claude:**
1. Calls `get_dataset_schema(dataset_id=1)` to understand data
2. Calls multiple `query_dataset()` for different metrics
3. Synthesizes results into analysis

---

## 🐛 **Troubleshooting**

### **Connection Refused**

**Problem:** Can't connect to MCP endpoint

**Solutions:**
1. Check server is running: `curl https://your-app.onrender.com/health`
2. Verify URL is correct (include `/mcp`)
3. Check firewall rules

---

### **Tool Not Found**

**Problem:** ChatGPT/Claude says tool doesn't exist

**Solutions:**
1. Verify tools are listed: Test 3 above
2. Restart ChatGPT/Claude Desktop
3. Check server logs for errors

---

### **Query Limit Errors**

**Problem:** "Row limit exceeded" errors

**Solution:**
- All queries limited to 40 rows
- Use aggregation (GROUP BY) for large datasets
- Sample data instead of full tables

---

### **Authentication Errors**

**Problem:** "Unauthorized" or "403 Forbidden"

**Solutions:**
1. Check Render IP whitelist settings
2. Verify VPN is connected
3. Check nginx auth configuration

---

## 📱 **Deployment Checklist**

Before connecting MCP clients:

- [ ] Server deployed and running
- [ ] Health check returns "healthy"
- [ ] At least one dataset added via UI
- [ ] MCP endpoint responds to test requests
- [ ] Security configured (IP whitelist, VPN, etc.)
- [ ] Connection URL documented

---

## 🆘 **Need Help?**

**Common Issues:**

1. **Can't access UI:**
   - Go to `https://your-app.onrender.com/ui`
   - Not `https://your-app.onrender.com`

2. **MCP not working:**
   - Must include `/mcp` in URL
   - Test with curl first

3. **No datasets shown:**
   - Add datasets via UI first
   - Check they're marked "Active"

4. **Query errors:**
   - Only SELECT statements allowed
   - 40 row limit enforced
   - Check SQL syntax

---

## 📚 **Next Steps**

1. ✅ Deploy server to Render or VM
2. ✅ Access UI at `/ui` and add datasets
3. ✅ Test MCP endpoint with curl
4. ✅ Connect ChatGPT or Claude Desktop
5. ✅ Start querying your data!

---

**Your MCP Connection URLs:**

| Service | URL |
|---------|-----|
| Web UI | `https://your-app.onrender.com/ui` |
| MCP API | `https://your-app.onrender.com/mcp` |
| Health | `https://your-app.onrender.com/health` |

Save these URLs securely! 🔐
