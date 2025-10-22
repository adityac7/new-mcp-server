# 🚀 Render.com Deployment Guide

Complete guide to deploy MCP Analytics Server with UI Dashboard, MCP Server, Redis, and PostgreSQL.

---

## 🏗️ Architecture (4 Services)

```
1. PostgreSQL (Metadata DB)    → Stores datasets, schemas, logs
2. Redis (Cache + Celery)      → Background tasks, hot-reload  
3. Web Service (UI + API)      → Dashboard + REST API (port 8000)
4. Web Service (MCP Server)    → ChatGPT connection (port 8001)
```

**Total Cost**: ~$24/month (or $3/month with free tier + Redis)

---

## 📋 Step-by-Step Setup

### **Step 1: Create PostgreSQL Database**

1. Render Dashboard → **New** → **PostgreSQL**
2. Settings:
   - Name: `mcp-metadata-db`
   - Region: **Singapore**
   - Plan: **Starter ($7/mo)** or **Free**
3. **Save Internal Database URL** → You'll need this for services

---

### **Step 2: Create Redis**

1. Render Dashboard → **New** → **Redis**
2. Settings:
   - Name: `mcp-redis`
   - Region: **Singapore** (same as database!)
   - Plan: **Starter ($3/mo)**
3. **Save Internal Redis URL**

---

### **Step 3: Generate Encryption Key**

Run locally:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
**Save the output** (e.g., `RnVacvrjVNzUq4kOKW-p1NGs-_VkvrjsncybnQzsT_c=`)

---

### **Step 4: Deploy UI + REST API**

1. Render Dashboard → **New** → **Web Service**
2. Connect repo: `adityac7/mcp-analytics-server`
3. Settings:
   - **Name**: `mcp-analytics-ui`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Build Command**:
     ```
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Starter ($7/mo)

4. **Environment Variables**:
   ```bash
   DATABASE_URL=<INTERNAL_POSTGRES_URL_FROM_STEP_1>
   REDIS_URL=<INTERNAL_REDIS_URL_FROM_STEP_2>
   CELERY_BROKER_URL=<SAME_AS_REDIS_URL>
   CELERY_RESULT_BACKEND=<SAME_AS_REDIS_URL>
   ENCRYPTION_KEY=<FROM_STEP_3>
   SECRET_KEY=<ANY_RANDOM_STRING>
   OPENAI_API_KEY=sk-your-key-here
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   MAX_ROWS=1000
   ```

5. Deploy → **Save URL**: `https://mcp-analytics-ui.onrender.com`

---

### **Step 5: Deploy MCP Server**

1. Render Dashboard → **New** → **Web Service**
2. Connect same repo: `adityac7/mcp-analytics-server`
3. Settings:
   - **Name**: `mcp-analytics-mcp-server`
   - **Region**: Singapore
   - **Branch**: `main`
   - **Build Command**:
     ```
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```
     python server.py
     ```
   - **Plan**: Starter ($7/mo)

4. **Environment Variables**: (Copy ALL from Step 4 + add):
   ```bash
   MCP_SERVER_PORT=8001
   ```

5. Deploy → **Save URL**: `https://mcp-analytics-mcp-server.onrender.com`

---

### **Step 6: Initialize Database Schema**

Via Render Shell (UI service):

```bash
# Add metadata_text column
python3 -c "
from app.database import metadata_engine
from sqlalchemy import text
with metadata_engine.connect() as conn:
    conn.execute(text('ALTER TABLE datasets ADD COLUMN IF NOT EXISTS metadata_text TEXT'))
    conn.commit()
print('✅ Column added')
"
```

---

### **Step 7: Add Your Dataset**

#### **Via UI:**
1. Go to: `https://mcp-analytics-ui.onrender.com/ui/datasets/new`
2. Add your database connection string
3. Click "Add Dataset"

#### **Profile Schema (Render Shell):**

```bash
# List datasets
python3 -c "from app.database import get_db; from app.models import Dataset; db=next(get_db()); [print(f'{d.id}: {d.name}') for d in db.query(Dataset).all()]"

# Profile dataset (replace 1 with your ID)
python3 manual_profile.py 1

# Generate metadata
python3 generate_metadata.py 1

# Update descriptions (optional)
python3 edit_descriptions.py
```

---

### **Step 8: Connect ChatGPT**

1. ChatGPT → Settings → MCP Servers → Add
2. Configure:
   - **Name**: `CMI Analytics`
   - **URL**: `https://mcp-analytics-mcp-server.onrender.com/mcp`
3. Test:
   ```
   "List available datasets"
   "Show schema for dataset 1"
   "Get top 10 apps by usage"
   ```

---

## 🎯 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| UI Dashboard | `https://mcp-analytics-ui.onrender.com/ui` | Manage datasets |
| API Docs | `https://mcp-analytics-ui.onrender.com/docs` | REST API |
| MCP Server | `https://mcp-analytics-mcp-server.onrender.com/mcp` | ChatGPT |

---

## 🐛 Troubleshooting

**Database connection error:**
- Use **Internal URLs** (not External)
- Check environment variables

**MCP not responding:**
- Check: `https://mcp-analytics-mcp-server.onrender.com/health`
- Verify logs in Render Dashboard

**No schema showing:**
- Run `python3 generate_metadata.py <id>` in Shell

---

## 💰 Cost

**Production Setup**: ~$24/month
- PostgreSQL Starter: $7
- Redis Starter: $3  
- UI Service: $7
- MCP Service: $7

**Budget Setup**: ~$3/month
- PostgreSQL Free (90 days)
- Redis Starter: $3
- UI Service Free (sleeps)
- MCP Service Free (sleeps)

---

## ✅ Deployment Checklist

- [ ] PostgreSQL created
- [ ] Redis created
- [ ] Encryption key generated
- [ ] UI service deployed
- [ ] MCP service deployed
- [ ] Database initialized
- [ ] Dataset added & profiled
- [ ] ChatGPT connected
- [ ] Test query successful

**You're ready to go!** 🎉
