# Getting Started - MCP Analytics Server

Welcome to the MCP Analytics Server project! This guide will help your development team get started with local development and understand the project structure.

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.11+** installed
- **Docker & Docker Compose** installed
- **Git** installed
- **OpenAI API Key** (for Phase 2+)

### Local Development with Docker

```bash
# 1. Clone the repository
git clone https://github.com/your-org/mcp-analytics-server.git
cd mcp-analytics-server

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env and add your OpenAI API key
nano .env  # or vim, code, etc.
# Set: OPENAI_API_KEY=sk-your-key-here

# 4. Generate encryption keys
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())" >> .env

# 5. Start all services
docker-compose up -d

# 6. Wait for services to be ready (~30 seconds)
docker-compose logs -f app

# 7. Check health
curl http://localhost:8000/health

# 8. Access the application
# - API: http://localhost:8000
# - UI: http://localhost:8000/ui
# - API Docs: http://localhost:8000/docs
# - PgAdmin: http://localhost:5050 (admin@mcp.local / admin)
```

---

## Project Overview

### What is This Project?

A production-grade **Model Context Protocol (MCP) server** that allows LLMs (ChatGPT, Claude, etc.) to query multiple PostgreSQL datasets with:
- Auto-generated metadata using LLM
- Weighted population calculations
- Parallel query execution
- Progressive context loading for token efficiency

### Use Case

Internal tool for CMI (Consumer & Market Insights) teams to:
1. Add datasets from Microsoft Fabric via Postgres connection strings
2. Auto-generate data dictionaries and descriptions using GPT-4o-mini
3. Query data through natural language (via ChatGPT/Claude)
4. Get weighted, persona-level insights automatically

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Analytics Server                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  FastAPI     │  │   FastMCP    │  │    HTMX      │         │
│  │  REST API    │  │  MCP Server  │  │   UI         │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                 │                   │
│         └─────────────────┴─────────────────┘                   │
│                           │                                     │
│         ┌─────────────────┴─────────────────┐                   │
│         │                                   │                   │
│  ┌──────▼──────┐                    ┌──────▼──────┐            │
│  │  Metadata   │                    │    Redis    │            │
│  │  PostgreSQL │                    │Cache+Pub/Sub│            │
│  └─────────────┘                    └─────────────┘            │
│                                                                 │
│  ┌──────────────┐                                              │
│  │    Celery    │◀───────────────────────────────────────────┐ │
│  │   Worker     │  (Background tasks: schema profiling,       │ │
│  └──────────────┘   LLM metadata generation)                  │ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │                                  │
          │                                  │
   ┌──────▼──────┐                    ┌──────▼──────┐
   │   ChatGPT   │                    │   Claude    │
   │  (via MCP)  │                    │  (via MCP)  │
   └─────────────┘                    └─────────────┘
```

---

## Development Phases

### ✅ Phase 1: Basic MCP Server (COMPLETED)
- Single dataset support
- Basic SQL query execution
- Security controls (SELECT only, row limits)
- Deployed on Render

**Files:**
- `server.py` - FastMCP server with 5 tools
- `load_data_cloud.py` - Data migration script

---

### 🔄 Phase 2: Multi-Dataset + LLM Metadata (IN PROGRESS)

**Deliverables:**
- [ ] Metadata database setup
- [ ] Dataset registry with encrypted connection strings
- [ ] Schema profiler service (async)
- [ ] LLM metadata generation using GPT-4o-mini
- [ ] Background worker (Celery)
- [ ] Hot-reload mechanism (Redis pub/sub)

**Timeline:** 2 weeks

**Key Files to Create:**
```
app/
├── models/
│   ├── dataset.py            # SQLAlchemy models
│   └── query_log.py
├── services/
│   ├── schema_profiler.py    # Auto-analyze database schemas
│   ├── llm_metadata_service.py  # GPT-4o-mini integration
│   └── dataset_service.py
├── api/
│   └── datasets.py           # REST endpoints
└── workers/
    └── tasks.py              # Celery background tasks
```

**See:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md#phase-2-multi-dataset-management--llm-metadata)

---

### 🔄 Phase 3: UI Dashboard (NEXT)

**Deliverables:**
- [ ] HTMX-based lightweight UI
- [ ] Dataset onboarding wizard
- [ ] Metadata review/edit interface
- [ ] Query logs dashboard

**Timeline:** 2 weeks

**Tech Stack:**
- HTMX (no build step)
- Alpine.js (minimal JS)
- Tailwind CSS
- Jinja2 templates

**See:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md#phase-3-ui-dashboard)

---

### 🔄 Phase 4: Parallel Query Execution (LATER)

**Deliverables:**
- [ ] Async query executor (asyncpg)
- [ ] Connection pooling per dataset
- [ ] Progressive context loading
- [ ] Support for up to 30 concurrent queries

**Timeline:** 2 weeks

**See:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md#phase-4-parallel-query-execution--optimization)

---

### 🔄 Phase 5: Query Logs + Monitoring (LATER)

**Deliverables:**
- [ ] Query logging middleware
- [ ] Analytics dashboard
- [ ] Tool usage tracking (ChatGPT vs Claude)
- [ ] Performance metrics

**Timeline:** 1 week

**See:** [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md#phase-5-query-logs--monitoring)

---

## Development Workflow

### 1. Local Setup (First Time)

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing & linting

# Or use Docker (recommended)
docker-compose up -d
```

### 2. Database Setup

```bash
# Using Docker (automatic)
docker-compose up -d metadata-db

# Or manually
createdb metadata_db
psql metadata_db < database_schema.sql
```

### 3. Run Migrations (Phase 2+)

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add dataset tables"

# Apply migrations
alembic upgrade head
```

### 4. Start Development Server

**Option A: Docker Compose (recommended)**
```bash
docker-compose up
```

**Option B: Local Python**
```bash
# Terminal 1: FastAPI app
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker (Phase 2+)
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Redis (if not using Docker)
redis-server
```

### 5. Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_dataset_service.py

# Run with verbose output
pytest -v
```

### 6. Code Quality

```bash
# Format code
black app/
isort app/

# Lint
ruff check app/

# Type checking
mypy app/
```

---

## Project Structure

```
mcp-analytics-server/
│
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Configuration management
│   │
│   ├── core/                     # Core utilities
│   │   ├── database.py           # DB connection
│   │   ├── security.py           # Encryption
│   │   └── redis_client.py       # Redis connection
│   │
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── dataset.py
│   │   └── query_log.py
│   │
│   ├── schemas/                  # Pydantic schemas (DTOs)
│   │   ├── dataset.py
│   │   └── query.py
│   │
│   ├── api/                      # REST API endpoints
│   │   ├── datasets.py
│   │   ├── queries.py
│   │   └── logs.py
│   │
│   ├── services/                 # Business logic
│   │   ├── schema_profiler.py
│   │   ├── llm_metadata_service.py
│   │   ├── query_executor.py
│   │   └── context_service.py
│   │
│   ├── mcp/                      # MCP server
│   │   ├── server.py             # FastMCP implementation
│   │   └── tools.py              # MCP tool definitions
│   │
│   ├── ui/                       # HTMX UI
│   │   ├── routes.py
│   │   └── templates/
│   │
│   └── workers/                  # Background tasks
│       ├── celery_app.py
│       └── tasks.py
│
├── alembic/                      # Database migrations
│   └── versions/
│
├── tests/                        # Test suite
│   ├── conftest.py
│   ├── test_dataset_service.py
│   └── test_query_executor.py
│
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # High-level architecture
│   ├── IMPLEMENTATION_PLAN.md    # Detailed implementation plan
│   ├── API.md                    # API reference
│   └── RENDER_DEPLOYMENT.md      # Deployment guide
│
├── scripts/                      # Utility scripts
│   └── init_metadata_db.py
│
├── database_schema.sql           # PostgreSQL schema
├── docker-compose.yml            # Local development stack
├── Dockerfile                    # Production container
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore
├── README.md
└── GETTING_STARTED.md            # This file
```

---

## Key Concepts

### 1. Weighting Methodology

All data comes from a **representative panel population** where each user has a **weight**.

**Example:**
```
user_id: 12345
weight: 0.456
```
This means user 12345 represents **456 people** in their demographic cell.

**Cell** = age/gender/NCCS/townclass/state combination

**Rules:**
- Always weigh **users**, NOT events
- Report at **weighted level** unless specified
- Limit raw data to **max 5 rows** (aggregated data can be larger)

### 2. Progressive Context Loading

To stay within LLM token limits, we load context progressively:

- **Level 0**: Global rules (weighting, output limits)
- **Level 1**: Dataset names + 1-2 line descriptions
- **Level 2**: Table schemas (column names, types)
- **Level 3**: Full schema + sample data + statistics

### 3. Hot-Reload Mechanism

When a new dataset is approved:
1. Status changes to `approved` in database
2. Redis pub/sub notification sent
3. MCP server reloads dataset list (no restart needed!)
4. ChatGPT/Claude immediately see new dataset

---

## Environment Variables

### Required

```bash
# Database
METADATA_DATABASE_URL=postgresql://user:pass@host:port/metadata_db

# Redis
REDIS_URL=redis://:password@host:6379/0

# Security
ENCRYPTION_KEY=<fernet-key>      # Generate with script
SECRET_KEY=<random-string>        # Generate with script

# LLM (Phase 2+)
OPENAI_API_KEY=sk-your-key-here
```

### Optional

```bash
# Query Limits
MAX_RAW_ROWS=5
MAX_AGGREGATED_ROWS=1000
MAX_PARALLEL_QUERIES=30

# Cache TTL (seconds)
CACHE_TTL_LEVEL_0=3600   # 1 hour
CACHE_TTL_LEVEL_1=1800   # 30 min
CACHE_TTL_LEVEL_2=900    # 15 min
CACHE_TTL_LEVEL_3=300    # 5 min
```

**See:** [.env.example](.env.example)

---

## Common Tasks

### Add a New MCP Tool

```python
# app/mcp/tools.py

@mcp.tool()
async def my_new_tool(param: str) -> str:
    """
    Tool description for the LLM

    Args:
        param: Parameter description

    Returns:
        Markdown formatted result
    """
    # Your logic here
    return "Result"
```

### Add a New API Endpoint

```python
# app/api/my_endpoint.py

from fastapi import APIRouter

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.get("/")
async def my_endpoint():
    return {"message": "Hello"}

# Register in app/main.py
app.include_router(my_endpoint.router)
```

### Create a Database Migration

```bash
# After modifying models in app/models/
alembic revision --autogenerate -m "Add new column to datasets"

# Review the generated migration file
cat alembic/versions/xxxxx_add_new_column.py

# Apply migration
alembic upgrade head
```

### Run Background Task

```python
# app/workers/tasks.py

@celery_app.task
def my_background_task(dataset_id: int):
    # Long-running task
    return {"success": True}

# Call from API
from app.workers.tasks import my_background_task
my_background_task.delay(dataset_id=123)
```

---

## Testing

### Unit Tests

```bash
# Test a specific service
pytest tests/test_schema_profiler.py -v

# Test with fixtures
pytest tests/test_dataset_service.py --fixtures
```

### Integration Tests

```bash
# Test with real database (uses Docker)
pytest tests/integration/ -v
```

### Test MCP Tools Locally

```python
# scripts/test_mcp_tool.py

import asyncio
from app.mcp.server import list_datasets

async def test():
    result = await list_datasets()
    print(result)

asyncio.run(test())
```

---

## Debugging

### View Logs

```bash
# Docker Compose
docker-compose logs -f app
docker-compose logs -f celery-worker

# Local development
# Logs appear in terminal
```

### Connect to Database

```bash
# Via Docker
docker-compose exec metadata-db psql -U mcp_admin -d metadata_db

# Local
psql metadata_db
```

### Redis CLI

```bash
# Via Docker
docker-compose exec redis redis-cli -a dev_redis_password

# Check pub/sub
SUBSCRIBE channel:dataset:activated
```

### Debug with IPython

```python
# Add to code
import ipdb; ipdb.set_trace()

# Or use breakpoint()
breakpoint()
```

---

## Documentation

### Available Docs

- **[README.md](README.md)** - Project overview
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level system design
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed implementation guide
- **[API.md](API.md)** - REST API reference
- **[RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** - Deployment instructions
- **[database_schema.sql](database_schema.sql)** - Database schema with comments

### Auto-Generated Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Getting Help

### Internal Resources

- Product Manager: [Your Name]
- Tech Lead: [TBD]
- Slack Channel: #mcp-analytics-dev

### External Resources

- **FastAPI**: https://fastapi.tiangolo.com
- **FastMCP**: https://github.com/jlowin/fastmcp
- **MCP Protocol**: https://modelcontextprotocol.io
- **SQLAlchemy**: https://docs.sqlalchemy.org
- **Celery**: https://docs.celeryq.dev

---

## Next Steps

1. **Review Documentation**:
   - Read [ARCHITECTURE.md](ARCHITECTURE.md)
   - Read [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)

2. **Set Up Local Environment**:
   ```bash
   docker-compose up -d
   curl http://localhost:8000/health
   ```

3. **Explore Existing Code**:
   - Review `server.py` (Phase 1 implementation)
   - Test MCP tools with Claude/ChatGPT

4. **Start Phase 2 Development**:
   - Create database models (`app/models/dataset.py`)
   - Implement schema profiler (`app/services/schema_profiler.py`)
   - Build REST API (`app/api/datasets.py`)

5. **Regular Check-ins**:
   - Daily standups
   - Weekly sprint planning
   - Bi-weekly demos

---

## FAQ

**Q: Why FastMCP instead of official MCP SDK?**
A: FastMCP is a Python wrapper that simplifies MCP server creation and integrates well with FastAPI. The official Python SDK requires more boilerplate.

**Q: Why HTMX for UI instead of React?**
A: HTMX requires zero build step, is simpler for backend developers to maintain, and perfect for internal tools. Faster development time.

**Q: Can we support MySQL or other databases?**
A: Currently only PostgreSQL. MySQL support can be added in Phase 4+ by extending the connection manager.

**Q: How do we handle PII in datasets?**
A: Datasets should be pre-anonymized before adding to the system. No PII should be in sample data shown to LLMs.

**Q: What's the cost of LLM metadata generation?**
A: GPT-4o-mini costs ~$0.01 per dataset profiled (varies by table size). For 100 datasets: ~$1.

---

**Happy Coding!** 🚀

If you have questions, check the docs or ask in #mcp-analytics-dev.
