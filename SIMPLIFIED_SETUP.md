# Simplified Setup Guide - No Docker, Direct Connection Strings

## Overview

This simplified setup **skips Docker** and uses **direct PostgreSQL connection strings** from your team. Perfect for getting started quickly without containerization complexity.

---

## Prerequisites

- **Python 3.11+** installed locally
- **PostgreSQL connection strings** (provided by your team)
- **OpenAI API key**
- **Git** (for version control)

---

## Quick Start (10 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/mcp-analytics-server.git
cd mcp-analytics-server
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Optional: Install dev dependencies
pip install -r requirements-dev.txt
```

### 4. Set Up Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit .env file
nano .env  # or use any text editor
```

**Add your connection strings:**

```bash
# .env file

# Metadata Database (provided by your team)
METADATA_DATABASE_URL=postgresql://user:password@host:port/metadata_db

# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# Generate encryption key (run this command)
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=your-generated-key-here

# Redis (optional for Phase 2+)
# If not available, the app will skip Redis features
REDIS_URL=redis://localhost:6379/0

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 5. Initialize Metadata Database

**One-time setup** - Run the schema script:

```bash
# Using psql (if installed)
psql "$METADATA_DATABASE_URL" -f database_schema.sql

# OR using Python script
python scripts/init_metadata_db.py
```

### 6. Run the Server

```bash
# For Phase 1 (existing code)
python server.py

# For Phase 2+ (new code structure)
uvicorn app.main:app --reload --port 8000
```

### 7. Verify It's Working

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status": "healthy", "database": "connected"}
```

---

## Development Workflow (Without Docker)

### Running the Application

```bash
# Terminal 1: Main application
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker (Phase 2+ only)
source venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Redis (if needed, Phase 2+)
# Install Redis locally or skip if not using Phase 2 features yet
redis-server
```

### Testing

```bash
source venv/bin/activate
pytest
```

### Code Quality

```bash
source venv/bin/activate

# Format
black app/

# Lint
ruff check app/

# Type check
mypy app/
```

---

## Connection Strings Setup

### Scenario 1: Team Provides Connection Strings Directly

**Your team gives you:**
```
Metadata DB: postgresql://user:pass@host.com:5432/metadata_db
User Dataset 1: postgresql://user:pass@host2.com:5432/dataset1
User Dataset 2: postgresql://user:pass@host3.com:5432/dataset2
```

**You add to .env:**
```bash
# Metadata DB (for app internals)
METADATA_DATABASE_URL=postgresql://user:pass@host.com:5432/metadata_db
```

**User datasets** are added via the UI or API (Phase 2+), not hardcoded.

---

### Scenario 2: Local PostgreSQL for Development

If you want to test locally without external database:

```bash
# Install PostgreSQL locally
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql

# Start PostgreSQL
# macOS: brew services start postgresql
# Ubuntu: sudo systemctl start postgresql

# Create database
createdb metadata_db

# Set .env
METADATA_DATABASE_URL=postgresql://localhost:5432/metadata_db

# Run schema
psql metadata_db < database_schema.sql
```

---

## Phase-by-Phase Setup

### Phase 1 (Current - Existing Code)

**What you need:**
- Python 3.11+
- One PostgreSQL connection string

**Setup:**
```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://..."
python server.py
```

**Done!** Your Phase 1 MCP server is running.

---

### Phase 2 (Multi-Dataset + LLM Metadata)

**Additional requirements:**
- Metadata database connection string
- Redis (optional but recommended)
- OpenAI API key

**Setup:**
```bash
# 1. Install Redis locally (optional)
# macOS: brew install redis
brew services start redis

# 2. Update .env
METADATA_DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...

# 3. Run database migrations
alembic upgrade head

# 4. Start app
uvicorn app.main:app --reload

# 5. Start worker (in separate terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

---

### Phase 3 (UI Dashboard)

**No additional setup needed!** UI is served by same FastAPI app.

```bash
# Start app
uvicorn app.main:app --reload

# Access UI
open http://localhost:8000/ui/
```

---

### Phase 4 (Parallel Queries)

**No additional infrastructure needed!** Uses asyncpg (already in requirements.txt).

---

### Phase 5 (Query Logs)

**No additional setup needed!** Logs stored in metadata database.

---

## Redis: Optional or Required?

### Phase 1: ❌ Not needed

### Phase 2: ⚠️ Optional but recommended
- **Without Redis:**
  - No dataset hot-reload (need to restart server when adding datasets)
  - No caching (slower queries)
  - Celery uses database backend (slower)

- **With Redis:**
  - Hot-reload works (add datasets without restart)
  - Faster query responses (caching)
  - Better Celery performance

**Decision:** Start without Redis, add it later if needed.

### How to skip Redis in code:

```python
# app/core/redis_client.py
import os

REDIS_URL = os.getenv('REDIS_URL')

if REDIS_URL:
    import redis
    redis_client = redis.from_url(REDIS_URL)
else:
    # Mock Redis client (no-op)
    redis_client = None
    print("Warning: Redis not configured. Some features disabled.")
```

---

## Database Schema Setup Options

### Option 1: Run SQL Script Directly (Recommended)

```bash
psql "$METADATA_DATABASE_URL" -f database_schema.sql
```

**Pros:** Simple, fast, one command
**Cons:** No migration history

---

### Option 2: Use Alembic Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create initial migration from models
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

**Pros:** Migration history, rollback support
**Cons:** More complex setup

**For MVP: Use Option 1. Switch to Option 2 in production.**

---

## Deployment to Render (Simplified)

### Step 1: Create Metadata Database on Render

1. Go to Render Dashboard → New → PostgreSQL
2. Name: `mcp-metadata-db`
3. Plan: Free
4. Click Create
5. **Copy connection string** (Internal Database URL)

### Step 2: Initialize Schema

```bash
# From your local machine
export DB_URL="postgres://user:pass@dpg-xxx.oregon-postgres.render.com/metadata_db"

# Run schema
psql "$DB_URL" -f database_schema.sql
```

### Step 3: Deploy Web Service

1. Render Dashboard → New → Web Service
2. Connect GitHub repo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Environment Variables:
   ```
   METADATA_DATABASE_URL=<from step 1>
   OPENAI_API_KEY=sk-your-key
   ENCRYPTION_KEY=<generate locally>
   ```
5. Deploy!

**No Docker needed!** Render builds from requirements.txt.

---

## When Would You Need Docker?

### You DON'T need Docker if:
- ✅ Deploying to Render (uses buildpacks)
- ✅ Running locally with Python virtual env
- ✅ Team is comfortable with Python setup

### You MIGHT want Docker if:
- Multiple developers need identical environments
- Deploying to Azure Container Instances later
- Running on a machine without Python 3.11+
- Want isolated testing environments

**For your use case: Skip Docker entirely.** ✅

---

## Simplified Project Structure

```
mcp-analytics-server/
├── venv/                    # Python virtual environment
├── app/                     # Application code (Phase 2+)
│   ├── main.py
│   ├── models/
│   ├── api/
│   └── services/
├── server.py                # Phase 1 (existing)
├── requirements.txt         # Dependencies
├── .env                     # Your secrets (DO NOT COMMIT)
├── database_schema.sql      # Database schema
└── README.md
```

**No docker-compose.yml needed!**
**No Dockerfile needed!**

---

## Common Issues & Solutions

### Issue: "ModuleNotFoundError"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: "Cannot connect to database"

**Solution:**
```bash
# Test connection manually
psql "$METADATA_DATABASE_URL" -c "SELECT 1"

# Check .env file has correct URL
cat .env | grep DATABASE_URL

# Verify format: postgresql:// (not postgres://)
```

---

### Issue: "Redis connection failed"

**Solution:**
```bash
# If you don't need Redis yet (Phase 1), skip it
# OR install Redis:
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt-get install redis-server && sudo systemctl start redis

# Test Redis
redis-cli ping
```

---

### Issue: "Celery worker won't start"

**Solution:**
```bash
# Celery is only needed for Phase 2+
# For Phase 1, you don't need it

# If needed, make sure Redis is running
redis-cli ping

# Start worker with verbose logging
celery -A app.workers.celery_app worker --loglevel=debug
```

---

## Simplified Requirements

### Phase 1 (Existing Code)
- ✅ Python 3.11+
- ✅ One PostgreSQL connection string
- ✅ That's it!

### Phase 2+ (New Features)
- ✅ Python 3.11+
- ✅ Metadata PostgreSQL connection string
- ✅ OpenAI API key
- ⚠️ Redis (optional, recommended)

**No Docker, no Kubernetes, no complex infra.**

---

## What We Removed

From the original documentation:
- ❌ Docker setup (docker-compose.yml, Dockerfile) → **OPTIONAL**
- ❌ Azure migration guide → **OUT OF SCOPE**
- ❌ Azure Data Factory setup → **OUT OF SCOPE**
- ❌ Fabric integration details → **OUT OF SCOPE**

**Simplified approach:**
1. Your team gives you connection strings
2. You add them to `.env`
3. You run the app
4. Done!

---

## Updated Quick Start Commands

```bash
# Complete setup from scratch
git clone <repo>
cd mcp-analytics-server

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Edit .env with your connection strings
nano .env

# Initialize database (one-time)
psql "$METADATA_DATABASE_URL" -f database_schema.sql

# Run Phase 1
python server.py

# OR run Phase 2+ (when ready)
uvicorn app.main:app --reload
```

**That's it!** No Docker, no Azure, just Python + PostgreSQL connection strings.

---

## Next Steps

1. **Get connection strings** from your team
2. **Install Python 3.11+** if not already installed
3. **Follow Quick Start** above
4. **Start with Phase 1** (existing server.py)
5. **Move to Phase 2** when ready (new app/ structure)

---

## Questions?

**Q: Do we need Docker at all?**
A: No! Only if you want it for consistency across team members.

**Q: What about Azure?**
A: Skipped for now. When you migrate later, you'll just change the connection strings in .env.

**Q: How do we add new datasets?**
A: Via the UI (Phase 3) or API (Phase 2). Just provide connection strings.

**Q: What's the minimum to get Phase 1 running?**
A: Python + one connection string. 2 commands: `pip install -r requirements.txt` and `python server.py`.

---

**Simplified and ready to go!** 🚀
