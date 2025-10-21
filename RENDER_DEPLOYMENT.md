# Render.com Deployment Guide - Multi-Service Setup

Complete guide to deploy the production-grade MCP Analytics Server on Render.com with multiple services (Web, Worker, Redis).

---

## Prerequisites

- [x] GitHub account
- [x] Render.com account (free tier works)
- [x] OpenAI API key
- [x] Code pushed to GitHub repository

---

## Architecture on Render

```
┌─────────────────────────────────────────────────┐
│                  Render.com                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐     ┌──────────────┐        │
│  │   Web Service│────▶│  PostgreSQL  │        │
│  │  (MCP Server)│     │  (Metadata)  │        │
│  │  Port: 8000  │     │              │        │
│  └──────┬───────┘     └──────────────┘        │
│         │                                       │
│         │             ┌──────────────┐        │
│         ├────────────▶│    Redis     │        │
│         │             │  (Cache+Queue)│        │
│         │             └──────────────┘        │
│         │                                       │
│  ┌──────▼───────┐                              │
│  │Background Wrkr│                              │
│  │   (Celery)   │                              │
│  └──────────────┘                              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Step-by-Step Deployment

### Phase 1: Deploy Existing MCP Server (Current)

This phase deploys your existing Phase 1 server without modifications.

#### 1.1 Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **PostgreSQL**
3. Configure:
   ```
   Name: mcp-metadata-db
   Database: metadata_db
   User: mcp_admin
   Region: Oregon (or closest to you)
   PostgreSQL Version: 16
   Plan: Free (1GB, 90-day retention)
   ```
4. Click **Create Database**
5. Once created, go to the database page
6. Copy the **External Database URL**
   - Format: `postgres://mcp_admin:xxx@dpg-xxx.oregon-postgres.render.com/metadata_db`

#### 1.2 Run Database Schema Setup

On your local machine:

```bash
# Install psql if not available
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql-client

# Set the database URL
export DATABASE_URL="postgres://mcp_admin:xxx@dpg-xxx.oregon-postgres.render.com/metadata_db"

# Run the schema script
psql "$DATABASE_URL" -f database_schema.sql

# Verify tables were created
psql "$DATABASE_URL" -c "\dt"
```

Expected output:
```
             List of relations
 Schema |       Name        | Type  |   Owner
--------+-------------------+-------+-----------
 public | datasets          | table | mcp_admin
 public | dataset_schemas   | table | mcp_admin
 public | llm_metadata      | table | mcp_admin
 public | query_logs        | table | mcp_admin
```

#### 1.3 Deploy Web Service (Phase 1 - Existing Code)

1. Click **New +** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   ```
   Name: mcp-analytics-server
   Region: Oregon (same as database)
   Branch: main
   Root Directory: (leave blank)
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python server.py --port $PORT
   Instance Type: Free (512 MB RAM)
   ```

4. **Environment Variables** - Add these:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `postgresql://mcp_admin:xxx@dpg-xxx.oregon-postgres.render.com/metadata_db` |
   | `PORT` | `8000` |

5. Click **Create Web Service**

6. Wait for deployment (~3-5 minutes)

7. Once live, copy your service URL:
   ```
   https://mcp-analytics-server-xxx.onrender.com
   ```

#### 1.4 Test Phase 1 Deployment

```bash
# Health check
curl https://your-app.onrender.com/health

# MCP endpoint test
curl -X POST https://your-app.onrender.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

---

### Phase 2: Add Multi-Dataset Support + LLM Metadata

#### 2.1 Create Redis Instance

1. Click **New +** → **Redis**
2. Configure:
   ```
   Name: mcp-redis
   Region: Oregon (same region!)
   Plan: Free (25 MB)
   Maxmemory Policy: allkeys-lru
   ```
3. Click **Create Redis**
4. Copy **Internal Redis URL**:
   ```
   redis://red-xxx:6379
   ```

#### 2.2 Update Web Service Environment Variables

Go to your web service → **Environment** tab, add:

| Key | Value |
|-----|-------|
| `REDIS_URL` | `redis://red-xxx:6379` |
| `OPENAI_API_KEY` | `sk-your-openai-api-key` |
| `ENCRYPTION_KEY` | Generate with command below |
| `SECRET_KEY` | Generate with command below |

**Generate Encryption Keys:**
```bash
# ENCRYPTION_KEY (Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 2.3 Deploy Background Worker (Celery)

1. Click **New +** → **Background Worker**
2. Connect same GitHub repository
3. Configure:
   ```
   Name: mcp-celery-worker
   Region: Oregon
   Branch: main
   Build Command: pip install -r requirements.txt
   Start Command: celery -A app.workers.celery_app worker --loglevel=info
   Instance Type: Free
   ```

4. **Environment Variables** - Copy ALL from web service:
   - `METADATA_DATABASE_URL`
   - `REDIS_URL`
   - `OPENAI_API_KEY`
   - `ENCRYPTION_KEY`

5. Click **Create Background Worker**

---

### Phase 3: Deploy UI Dashboard

The UI is served by the same web service (FastAPI serves both API and UI).

1. Update your web service's **Start Command**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

2. Access UI at:
   ```
   https://your-app.onrender.com/ui/
   ```

---

## Service Configuration Matrix

| Service | Type | Purpose | Free Tier Limits | Command |
|---------|------|---------|------------------|---------|
| **mcp-metadata-db** | PostgreSQL | Metadata storage | 1GB, 90 days | N/A |
| **mcp-redis** | Redis | Cache + Pub/Sub | 25MB | N/A |
| **mcp-analytics-server** | Web Service | API + MCP + UI | 512MB RAM | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **mcp-celery-worker** | Background Worker | Async tasks | 512MB RAM | `celery -A app.workers.celery_app worker --loglevel=info` |

---

## render.yaml (Infrastructure as Code)

Create `render.yaml` in your repo root for automated deployment:

```yaml
services:
  # PostgreSQL Database
  - type: postgres
    name: mcp-metadata-db
    databaseName: metadata_db
    user: mcp_admin
    plan: free
    region: oregon

  # Redis
  - type: redis
    name: mcp-redis
    plan: free
    region: oregon
    maxmemoryPolicy: allkeys-lru

  # Web Service (MCP Server + API + UI)
  - type: web
    name: mcp-analytics-server
    runtime: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: mcp-metadata-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: mcp-redis
          property: connectionString
      - key: OPENAI_API_KEY
        sync: false  # Set manually in dashboard
      - key: ENCRYPTION_KEY
        generateValue: true
      - key: SECRET_KEY
        generateValue: true
      - key: ENVIRONMENT
        value: production
    healthCheckPath: /health

  # Background Worker (Celery)
  - type: worker
    name: mcp-celery-worker
    runtime: python
    region: oregon
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: mcp-metadata-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: mcp-redis
          property: connectionString
      - key: OPENAI_API_KEY
        sync: false
      - key: ENCRYPTION_KEY
        sync: false
```

**Usage:**
```bash
# Deploy all services at once
render deploy

# Or link repo in Render dashboard for auto-deployment
```

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Example | Where to Get |
|----------|-------------|---------|--------------|
| `METADATA_DATABASE_URL` | Postgres connection | `postgresql://...` | Render DB dashboard |
| `REDIS_URL` | Redis connection | `redis://...` | Render Redis dashboard |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` | OpenAI dashboard |
| `ENCRYPTION_KEY` | Fernet encryption | `gAAAAAB...` | Generate locally |
| `SECRET_KEY` | Session secret | `abc123...` | Generate locally |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_RAW_ROWS` | `5` | Max raw rows in output |
| `MAX_PARALLEL_QUERIES` | `30` | Max concurrent queries |
| `QUERY_LOG_RETENTION_DAYS` | `90` | Query log retention |

---

## Scaling on Render

### Free Tier Limitations

- **Web Service**: Spins down after 15 min inactivity (~30s cold start)
- **Database**: 1GB storage, 90-day retention
- **Redis**: 25MB memory
- **Worker**: Limited to 1 instance

### Upgrade Path

When you need more performance:

1. **Starter Plan** ($7/month per service):
   - Web Service: Always on, no cold starts
   - Database: 10GB, unlimited retention, backups
   - Worker: More memory and CPU

2. **Production Setup** (~$28/month total):
   - Web Service Starter: $7
   - Database Starter: $7
   - Redis Starter: $7
   - Worker Starter: $7

3. **High Performance** (~$100/month):
   - Web Service Pro: $25 (2GB RAM)
   - Database Standard: $20 (100GB)
   - Redis Standard: $30 (250MB)
   - Worker Standard: $25 (2GB RAM)

---

## Monitoring & Logs

### View Logs

**Web Service Logs:**
```bash
# Via Render CLI
render logs mcp-analytics-server --follow

# Or in dashboard: Services → mcp-analytics-server → Logs
```

**Worker Logs:**
```bash
render logs mcp-celery-worker --follow
```

### Health Monitoring

1. Set up uptime monitoring:
   - Dashboard → Service → Settings → Health Check Path: `/health`

2. External monitoring (optional):
   - UptimeRobot: Monitor `https://your-app.onrender.com/health`
   - Better Uptime: Free tier available

### Metrics

Available in Render dashboard:
- CPU usage
- Memory usage
- Request count
- Response time (p50, p95, p99)
- Error rate

---

## Troubleshooting

### Issue: Service Won't Start

**Check:**
1. View deployment logs in Render dashboard
2. Verify all environment variables are set
3. Check Python version compatibility (3.11+)

**Fix:**
```bash
# Test build locally
docker build -t mcp-test .
docker run --env-file .env -p 8000:8000 mcp-test
```

### Issue: Database Connection Failed

**Check:**
1. Verify `DATABASE_URL` is set correctly
2. Ensure URL uses `postgresql://` not `postgres://`
3. Check database is in same region

**Fix:**
```bash
# Test connection
psql "$DATABASE_URL" -c "SELECT 1"
```

### Issue: Redis Connection Failed

**Check:**
1. Verify `REDIS_URL` is set
2. Ensure web service and Redis are in same region

**Fix:**
```bash
# Test Redis connection
redis-cli -u "$REDIS_URL" ping
```

### Issue: Worker Not Processing Tasks

**Check:**
1. Worker service is running (check dashboard)
2. Redis connection is working
3. View worker logs for errors

**Fix:**
```bash
# View worker logs
render logs mcp-celery-worker --tail 100
```

### Issue: Cold Start Too Slow

**Symptoms:** First request after inactivity takes >30 seconds

**Solutions:**
1. Upgrade to Starter plan ($7/month) for always-on
2. Use external cron to ping every 10 minutes:
   ```bash
   # crontab -e
   */10 * * * * curl https://your-app.onrender.com/health
   ```
3. Use UptimeRobot to ping every 5 minutes

---

## Migration to Azure

When ready to move to your Azure infrastructure:

1. **Export data** from Render:
   ```bash
   pg_dump "$RENDER_DATABASE_URL" > backup.sql
   ```

2. **Create Azure resources**:
   - Azure Database for PostgreSQL Flexible Server
   - Azure Cache for Redis
   - Azure Container Instances or App Service

3. **Deploy Docker container**:
   ```bash
   # Build image
   docker build -t mcp-server .

   # Push to Azure Container Registry
   az acr login --name youracr
   docker tag mcp-server youracr.azurecr.io/mcp-server:latest
   docker push youracr.azurecr.io/mcp-server:latest
   ```

4. **Import data**:
   ```bash
   psql "$AZURE_DATABASE_URL" < backup.sql
   ```

---

## Cost Estimates

### Free Tier (Current)
- **Total: $0/month**
- Web Service: Free (750 hrs/month)
- Database: Free (1GB, 90 days)
- Redis: Free (25MB)
- Worker: Free (750 hrs/month)
- **Limitations**: Cold starts, limited storage, 90-day data retention

### Starter Tier (Recommended for 10-100 users)
- **Total: $28/month**
- Web Service: $7 (always on)
- Database: $7 (10GB)
- Redis: $7 (256MB)
- Worker: $7 (always on)

### Production Tier (100+ users)
- **Total: $100-200/month**
- Depends on traffic and data size
- Consider Azure migration at this scale

---

## Next Steps

1. ✅ Deploy Phase 1 (existing code)
2. ✅ Set up database schema
3. ✅ Configure environment variables
4. ⬜ Test MCP endpoint with Claude/ChatGPT
5. ⬜ Implement Phase 2 code (multi-dataset)
6. ⬜ Deploy worker service
7. ⬜ Build and deploy UI
8. ⬜ Monitor and optimize

---

## Support Resources

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Render Status**: https://status.render.com
- **MCP Docs**: https://modelcontextprotocol.io

---

**Your deployment is ready!** 🚀

Service URLs:
- **API/MCP**: `https://mcp-analytics-server-xxx.onrender.com`
- **UI**: `https://mcp-analytics-server-xxx.onrender.com/ui/`
- **Docs**: `https://mcp-analytics-server-xxx.onrender.com/docs`
