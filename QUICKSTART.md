# Quick Start Guide - MCP Analytics Server

Get your MCP server running in 5 minutes with the Web UI for dataset management.

## 🚀 What's New

✅ **Fixed UI Issues:**
- Web UI now properly accessible
- Connection string validation works
- Error messages display correctly
- Form preserves values on errors

✅ **Updated Row Limits:**
- ALL queries limited to 40 rows (both aggregated and raw data)
- Prevents large data transfers
- Ensures fast response times

## 📋 Prerequisites

Before starting, you need:

1. **Python 3.11+** installed
2. **PostgreSQL database** for metadata storage
3. **OpenAI API key** (optional, for AI metadata)
4. **Encryption key** (we'll generate this)

## 🏁 Setup Steps

### Step 1: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### Step 2: Create Environment File

```bash
# Copy example
cp .env.example .env

# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env file
nano .env
```

**Minimal .env configuration:**

```env
# Your metadata database (stores dataset info)
DATABASE_URL=postgresql://user:password@host:port/metadata_db

# Encryption key (paste the generated key from above)
ENCRYPTION_KEY=<your-generated-key>

# OpenAI API key (optional)
OPENAI_API_KEY=sk-<your-key>

# Row limit (default: 40)
MAX_ROWS=40
```

### Step 3: Initialize Database

```bash
# Run migrations
alembic upgrade head
```

### Step 4: Start the Server

```bash
# Start unified server (UI + MCP)
python deploy_server.py

# Or specify port
python deploy_server.py 8080
```

## 🌐 Accessing the Server

Once started, you have two interfaces:

### **1. Web UI** (for YOU - manage datasets)
**URL:** http://localhost:8000/ui

**Pages:**
- `http://localhost:8000/ui` - Dataset management dashboard
- `http://localhost:8000/ui/datasets` - List all datasets
- `http://localhost:8000/ui/datasets/new` - Add new dataset
- `http://localhost:8000/ui/logs` - Query logs

### **2. MCP API** (for ChatGPT/Claude - query data)
**URL:** http://localhost:8000/mcp

**Use this URL in:**
- ChatGPT integrations
- Claude Desktop config
- Other MCP clients

### **Other Endpoints:**
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/docs` - API documentation

## ➕ Adding Your First Dataset

### Via Web UI (Recommended)

1. **Navigate to UI**
   ```
   http://localhost:8000/ui/datasets/new
   ```

2. **Fill in the form:**
   - **Dataset Name:** `my_analytics_db`
   - **Description:** `My analytics database` (optional)
   - **Connection String:** `postgresql://user:password@host:port/database`

3. **Click "Add Dataset"**

The system will:
- ✅ Test the connection (you'll see an error if it fails)
- ✅ Encrypt and store the connection string
- ✅ Profile the database schema
- ✅ Generate AI metadata (if OpenAI key configured)
- ✅ Make the dataset ready for querying

### Via API (Alternative)

```bash
curl -X POST http://localhost:8000/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_analytics_db",
    "description": "My analytics database",
    "connection_string": "postgresql://user:password@host:port/database"
  }'
```

## 🔍 Testing Connection Strings

Before adding a dataset, test your connection:

```bash
# Test with psql
psql "postgresql://user:password@host:port/database" -c "SELECT 1"

# Should output:
# ?column?
#----------
#        1
```

Common connection string formats:

```bash
# Local PostgreSQL
postgresql://postgres:password@localhost:5432/mydb

# Remote PostgreSQL
postgresql://user:password@db.example.com:5432/production_db

# Render.com PostgreSQL
postgresql://user:pass@dpg-xxxxx.oregon-postgres.render.com/dbname

# With SSL required
postgresql://user:password@host:port/database?sslmode=require
```

## 📊 Query Limits

**All queries are limited to 40 rows:**

- SELECT statements without GROUP BY: 40 rows max
- SELECT statements with GROUP BY: 40 rows max
- Aggregated queries: 40 rows max

**Why 40 rows?**
- Prevents large data transfers
- Ensures fast response times
- Encourages proper aggregation
- Suitable for most analytics use cases

**Example:**

```sql
-- Returns up to 40 rows
SELECT * FROM users LIMIT 100

-- Returns up to 40 rows (grouped results)
SELECT city, COUNT(*) FROM users GROUP BY city
```

## 🐛 Troubleshooting

### Connection Failed Error

**Error:** "Connection failed: could not connect to server"

**Solutions:**
1. Check connection string format
2. Verify database is accessible from your server
3. Check firewall rules
4. Try connecting with `psql` first

### Encryption Key Error

**Error:** "ENCRYPTION_KEY environment variable not set"

**Solution:**
```bash
# Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
echo "ENCRYPTION_KEY=<generated-key>" >> .env

# Restart server
```

### UI Not Loading

**Error:** Blank page or 404

**Solutions:**
1. Make sure you're running `start_ui.py` not `server.py`
2. Check if server is running: `curl http://localhost:8000/health`
3. Check templates exist: `ls app/ui/templates/`

### Dataset Name Already Exists

**Error:** "Dataset name 'xxx' already exists"

**Solution:**
- Use a different name, or
- Delete the existing dataset via UI first

## 🔒 Security Notes

⚠️ **This server has NO authentication by default**

**For development:**
- Run on localhost only
- Don't expose to internet

**For production:**
- Deploy behind VPN
- Use firewall rules to restrict access
- Add nginx basic auth
- Use IP whitelisting

## 📦 Deployment

### On Render.com

1. Push code to GitHub
2. Connect repo to Render
3. Set environment variables in Render dashboard
4. Deploy will use `render.yaml` automatically

### On Your VM

See `DEPLOY_VM.md` for full instructions:

```bash
# Quick VM deployment
git clone <repo> mcp-server
cd mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env
alembic upgrade head
python start_ui.py
```

## 🎯 Next Steps

Once your server is running:

1. **Add datasets** via UI at `/ui/datasets/new`
2. **View schema** for each dataset
3. **Connect ChatGPT/Claude** using MCP endpoint
4. **Start querying your data!**

## 🔌 Connecting MCP Clients

**Your MCP URL:**
```
http://localhost:8000/mcp
```

**For Render.com deployment:**
```
https://your-app.onrender.com/mcp
```

**See full instructions:** `MCP_CONNECTION_GUIDE.md`

- How to connect ChatGPT
- How to connect Claude Desktop
- Available MCP tools
- Usage examples
- Troubleshooting

## 📚 Additional Resources

- **`MCP_CONNECTION_GUIDE.md`** - Connect ChatGPT and Claude Desktop ⭐
- **`DEPLOY_VM.md`** - Full VM deployment guide
- **`README.md`** - Project overview
- **`API.md`** - API documentation
- **`/docs` endpoint** - Interactive API docs

## 💬 Need Help?

Common issues:
- Connection strings - check format and credentials
- Encryption key - must be Fernet-compatible base64
- Database migrations - run `alembic upgrade head`
- Port already in use - change port: `python start_ui.py 8080`

---

**You're all set!** Open http://localhost:8000/ui and start adding datasets. 🎉
