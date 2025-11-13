# 🚀 Quick Setup & Fix Guide

## ⚠️ Problem: Dataset Shows 0 Tables/0 Columns

Your dataset is empty because schema profiling didn't run. Here's how to fix it:

## ✅ Quick Fix (Run This Now)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Fix existing datasets
python fix_existing_dataset.py

# 3. Check UI - tables should appear now!
```

## 🎯 Complete Setup (First Time)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your DATABASE_URL and ENCRYPTION_KEY
```

### 3. Initialize Database
```bash
alembic upgrade head
```

### 4. Start Server
```bash
python production_server.py
```

### 5. Access UI
```
http://localhost:8000/ui
```

## 🔧 Manual Profiling

Profile specific dataset:
```bash
python profile_dataset.py 1
```

## 📍 Your URLs

- **Web UI:** http://localhost:8000/ui (manage datasets)
- **MCP API:** http://localhost:8000/mcp (for ChatGPT/Claude)
- **Health:** http://localhost:8000/health

## 🚀 Deploy to Render

1. Push code to GitHub
2. Create Web Service on Render
3. Set environment variables
4. Use: `python production_server.py $PORT`

## 🔌 Connect ChatGPT

Use this URL: `https://your-app.onrender.com/mcp`

---

**See MCP_CONNECTION_GUIDE.md for full ChatGPT/Claude setup**
