# MCP Analytics Server - Phase 2 Deployment Guide

## 🎯 Overview

This guide covers deploying the **Phase 2 MCP Analytics Server** to Render.com with:
- ✅ Multi-dataset management
- ✅ Encrypted connection strings
- ✅ AI-powered metadata generation (GPT-4o-mini)
- ✅ Background processing with Celery
- ✅ Redis for task queue
- ✅ MCP protocol support

---

## 📋 Prerequisites

- [x] Render.com account (free tier works)
- [x] GitHub account
- [x] OpenAI API key (for metadata generation)
- [x] PostgreSQL database on Render (already set up)

---

## 🏗️ Architecture on Render

```
┌─────────────────────────────────────────────────┐
│                  Render.com                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐     ┌──────────────┐        │
│  │   Web Service│────▶│  PostgreSQL  │        │
│  │  (FastAPI)   │     │  (Metadata)  │        │
│  │  Port: 8000  │     │              │        │
│  └──────┬───────┘     └──────────────┘        │
│         │                                       │
│         │             ┌──────────────┐        │
│         ├────────────▶│    Redis     │        │
│         │             │  (Free 25MB) │        │
│         │             └──────────────┘        │
│         │                                       │
│  ┌──────▼───────┐                              │
│  │Celery Worker │                              │
│  │ (Background) │                              │
│  └──────────────┘                              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Deployment Steps

### Step 1: Push Code to GitHub

```bash
cd /home/ubuntu/mcp-analytics-server

# Initialize git if not already done
git init
git add .
git commit -m "Phase 2: Multi-dataset + LLM metadata"

# Push to your repository
git branch -M main
git remote add origin https://github.com/adityac7/mcp-analytics-server.git
git push -u origin main
```

### Step 2: Create Redis Instance on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Redis**
3. Configure:
   - **Name**: `mcp-redis`
   - **Region**: **Singapore** (same as your database)
   - **Plan**: **Free** (25MB)
   - **Maxmemory Policy**: `allkeys-lru`
4. Click **Create Redis**
5. Once created, copy the **Internal Redis URL**
   - Format: `redis://red-xxx:6379`

### Step 3: Deploy Web Service

1. Click **New +** → **Web Service**
2. Connect your GitHub repository: `adityac7/mcp-analytics-server`
3. Configure:
   - **Name**: `mcp-analytics-server-phase2`
   - **Region**: **Singapore**
   - **Branch**: `main`
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: **Free**

4. **Environment Variables** - Add these:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug` |
   | `REDIS_URL` | `redis://red-xxx:6379` (from Step 2) |
   | `OPENAI_API_KEY` | `sk-your-openai-api-key` |
   | `ENCRYPTION_KEY` | `armY7L2xF4nQJOD8_1RHD5ooxTKd2gABYYnmnkxV2OQ=` |
   | `SECRET_KEY` | `Bu_2SzKx7MQ97dA51vJAfdIp27Q8tiPd8ONLWtqaPAM` |
   | `ENVIRONMENT` | `production` |

5. Click **Create Web Service**
6. Wait for deployment (~3-5 minutes)

### Step 4: Deploy Celery Worker

1. Click **New +** → **Background Worker**
2. Connect same GitHub repository
3. Configure:
   - **Name**: `mcp-celery-worker`
   - **Region**: **Singapore**
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A app.workers.celery_app worker --loglevel=info --concurrency=2`
   - **Plan**: **Free**

4. **Environment Variables** - Copy ALL from web service:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `OPENAI_API_KEY`
   - `ENCRYPTION_KEY`

5. Click **Create Background Worker**

---

## ✅ Verify Deployment

### 1. Health Check

```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "phase": "Phase 2 - Multi-dataset + LLM Metadata"
}
```

### 2. Check API Documentation

Open in browser: `https://your-app.onrender.com/docs`

### 3. Add Your First Dataset

```bash
curl -X POST https://your-app.onrender.com/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "digital_insights",
    "description": "Digital insights data - CTV and Mobile analytics",
    "connection_string": "postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug"
  }'
```

### 4. Check Processing Status

```bash
curl https://your-app.onrender.com/api/datasets/1/status
```

Expected response:
```json
{
  "dataset_id": 1,
  "dataset_name": "digital_insights",
  "is_active": true,
  "tables_found": 1,
  "columns_profiled": 15,
  "metadata_generated": 15,
  "processing_complete": true
}
```

### 5. View Generated Metadata

```bash
curl https://your-app.onrender.com/api/datasets/1/metadata
```

---

## 🔧 Configuration for MCP Clients

### For ChatGPT Desktop

Add to ChatGPT MCP configuration:

```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app.onrender.com/mcp",
      "transport": "http"
    }
  }
}
```

### For Claude Desktop

Add to `claude_desktop_config.json`:

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

---

## 📊 Available MCP Tools

Once deployed, the following MCP tools will be available:

1. **list_available_datasets** - List all datasets
2. **get_dataset_schema** - Get schema with AI-generated metadata
3. **query_dataset** - Execute SQL queries on a dataset
4. **get_dataset_sample** - Get sample data from a table

---

## 💰 Cost Breakdown (Free Tier)

| Service | Plan | Limits | Cost |
|---------|------|--------|------|
| PostgreSQL | Free | 1GB, 90 days retention | $0 |
| Redis | Free | 25MB | $0 |
| Web Service | Free | 512MB RAM, cold starts | $0 |
| Worker | Free | 512MB RAM | $0 |
| **Total** | | | **$0/month** |

### Upgrade Options

When you need more:

- **Starter Plan** ($7/month per service):
  - No cold starts
  - Always-on
  - More resources

---

## 🔒 Security Features

- ✅ Connection strings encrypted with Fernet
- ✅ Only SELECT queries allowed
- ✅ Maximum 1000 rows per query
- ✅ SQL injection protection
- ✅ Dangerous keywords blocked
- ✅ Query logging for audit

---

## 🐛 Troubleshooting

### Issue: Worker not processing tasks

**Check:**
1. Redis URL is correct in both web service and worker
2. Worker is running (check Render dashboard)
3. Check worker logs for errors

**Fix:**
```bash
# Restart worker from Render dashboard
# Or check logs: Render Dashboard → Worker → Logs
```

### Issue: Metadata not generating

**Check:**
1. OPENAI_API_KEY is set correctly
2. Worker is running
3. Check worker logs for OpenAI errors

**Fix:**
- Verify API key is valid
- Check OpenAI account has credits
- Manually trigger reprocessing:
  ```bash
  curl -X POST https://your-app.onrender.com/api/datasets/1/reprocess
  ```

### Issue: Database connection failed

**Check:**
1. DATABASE_URL is correct
2. Database is running
3. Connection string format is `postgresql://` not `postgres://`

---

## 📈 Monitoring

### View Logs

1. **Web Service Logs**: Render Dashboard → Web Service → Logs
2. **Worker Logs**: Render Dashboard → Worker → Logs
3. **Redis Metrics**: Render Dashboard → Redis → Metrics

### Query Logs

All queries are logged in the `query_logs` table:

```sql
SELECT * FROM query_logs ORDER BY executed_at DESC LIMIT 10;
```

---

## 🎯 Next Steps

1. ✅ Deploy to Render
2. ✅ Add your datasets via API
3. ✅ Verify metadata generation
4. ⬜ Configure MCP clients (ChatGPT/Claude)
5. ⬜ Test queries through MCP
6. ⬜ Monitor usage and performance

---

## 📞 Support

- **Render Status**: https://status.render.com
- **Render Docs**: https://render.com/docs
- **OpenAI Status**: https://status.openai.com

---

## 🎉 Success Checklist

- [ ] Redis instance created
- [ ] Web service deployed
- [ ] Worker deployed
- [ ] All environment variables set
- [ ] Health check passes
- [ ] Dataset added successfully
- [ ] Schema profiled
- [ ] Metadata generated
- [ ] MCP client configured
- [ ] Test query executed

---

**Your Phase 2 MCP Analytics Server is now ready for production!** 🚀

