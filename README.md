# MCP Analytics Server - Production-Grade Multi-Database Platform

**A production-ready Model Context Protocol (MCP) server** that enables LLMs (ChatGPT, Claude, etc.) to query multiple PostgreSQL datasets with intelligent context loading, automated metadata generation, and weighted population analysis.

---

## 🎯 Overview

This platform allows **CMI (Consumer & Market Insights) teams** to:

1. **Add multiple datasets** from Microsoft Fabric via PostgreSQL connection strings
2. **Auto-generate metadata** using LLM (data dictionaries, use cases, quality checks)
3. **Query data via natural language** through ChatGPT, Claude, or other MCP clients
4. **Get weighted, persona-level insights** automatically applied
5. **Track usage** across different tools and datasets

---

## ✨ Key Features

### Phase 1 (✅ Completed)
- ✅ Basic MCP server with 5 analytical tools
- ✅ Single dataset support
- ✅ Security controls (SELECT-only, row limits)
- ✅ FastMCP protocol implementation
- ✅ Deployed on Render.com

### Phase 2 (🔄 In Development)
- 🔄 Multi-dataset registry with encrypted connection strings
- 🔄 Auto-generated metadata using GPT-4o-mini
- 🔄 Background workers for schema profiling
- 🔄 Hot-reload mechanism (add datasets without restart)
- 🔄 Progressive context loading for token efficiency

### Phase 3 (📋 Planned)
- 📋 HTMX-based UI dashboard
- 📋 Dataset onboarding wizard
- 📋 Metadata review/edit interface
- 📋 Query logs visualization

### Phase 4 (📋 Planned)
- 📋 Parallel query execution (up to 30 concurrent queries)
- 📋 Connection pooling per dataset
- 📋 Advanced weighting calculations
- 📋 Performance optimizations

### Phase 5 (📋 Planned)
- 📋 Comprehensive query logging
- 📋 Usage analytics by tool (ChatGPT vs Claude)
- 📋 Performance metrics dashboard
- 📋 Cost tracking

---

## 📚 Documentation

- **[SIMPLIFIED_SETUP.md](SIMPLIFIED_SETUP.md)** ⭐ **START HERE** - No Docker, direct connection strings
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Developer onboarding guide
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed implementation specifications
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level system architecture
- **[API.md](API.md)** - REST API and MCP endpoint reference
- **[RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** - Production deployment guide
- **[database_schema.sql](database_schema.sql)** - Complete database schema
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete package overview

---

## 🚀 Quick Start

### Simple Setup (No Docker - Recommended)

```bash
# 1. Clone repository
git clone https://github.com/your-org/mcp-analytics-server.git
cd mcp-analytics-server

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env and add:
# - METADATA_DATABASE_URL (from your team)
# - OPENAI_API_KEY

# 5. Initialize database (one-time)
psql "$METADATA_DATABASE_URL" -f database_schema.sql

# 6. Run Phase 1
python server.py

# OR run Phase 2+ (when ready)
uvicorn app.main:app --reload --port 8000
```

### Advanced: Docker Setup (Optional)

If you prefer Docker:
```bash
docker-compose up -d
```

See **[SIMPLIFIED_SETUP.md](SIMPLIFIED_SETUP.md)** for detailed instructions.

### Production Deployment (Render.com)

See **[RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** for complete deployment instructions.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│              MCP Analytics Server                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │  FastAPI    │  │  FastMCP    │  │   HTMX     │  │
│  │  REST API   │  │  Protocol   │  │  UI        │  │
│  └──────┬──────┘  └──────┬──────┘  └─────┬──────┘  │
│         │                │               │          │
│         └────────────────┴───────────────┘          │
│                          │                          │
│  ┌───────────────────────┴──────────────────┐       │
│  │                                          │       │
│  ▼                                          ▼       │
│  Metadata DB                              Redis     │
│  (Datasets, Logs, Schemas)         (Cache+Pub/Sub)  │
│                                                      │
│  Background Worker (Celery)                          │
│  └─ Schema Profiling                                │
│  └─ LLM Metadata Generation                         │
│                                                      │
└──────────────────────────────────────────────────────┘
           │                       │
           ▼                       ▼
      ChatGPT               Claude Desktop
     (via MCP)               (via MCP)
```

---

## 🔧 Technology Stack

- **Backend**: Python 3.11+, FastAPI, FastMCP
- **Database**: PostgreSQL 16 (metadata + user datasets via connection strings)
- **Cache/Queue**: Redis 7 (optional, recommended for Phase 2+)
- **Workers**: Celery (Phase 2+)
- **LLM**: OpenAI GPT-4o-mini
- **Frontend**: HTMX + Alpine.js + Tailwind CSS
- **Deployment**: Render.com (no Docker required)

---

## Phase 1: Deployment Steps (Current)

### 1. Create Render Account

Go to [render.com](https://render.com) and sign up for a free account.

### 2. Create PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Name: `analytics-db`
3. Database: `analytics_db`
4. User: `analytics_user`
5. Region: Choose closest to you
6. Plan: **Free** (1GB storage, 90 days retention)
7. Click "Create Database"
8. Copy the **External Database URL** (starts with `postgres://`)

### 3. Load Data to Database

On your local machine:

```bash
# Set the database URL
export DATABASE_URL="postgres://analytics_user:password@host/analytics_db"

# Run the data loading script
python3 load_data_cloud.py
```

This will migrate all 839K rows from your local database to the cloud.

### 4. Deploy Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository (or use "Deploy from Git URL")
3. Name: `mcp-analytics-server`
4. Region: Same as database
5. Branch: `main`
6. Runtime: **Python 3**
7. Build Command: `pip install -r requirements.txt`
8. Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
9. Plan: **Free** (750 hours/month)
10. Environment Variables:
    - `DATABASE_URL`: Paste the External Database URL from step 2
11. Click "Create Web Service"

### 5. Wait for Deployment

Render will:
- Install dependencies
- Start the server
- Assign a permanent URL (e.g., `https://mcp-analytics-server.onrender.com`)

## Alternative: Deploy via GitHub

### 1. Push to GitHub

```bash
cd /home/ubuntu/mcp_analytics_deploy
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mcp-analytics-server.git
git push -u origin main
```

### 2. Connect Render to GitHub

1. In Render dashboard, click "New +" → "Web Service"
2. Click "Connect GitHub"
3. Select your repository
4. Follow steps 3-11 from above

## API Endpoints

Once deployed, your server will have these endpoints:

- `GET /` - Server info
- `GET /health` - Health check
- `GET /api/schema` - Get table schema
- `GET /api/sample?limit=10` - Get sample data
- `POST /api/query` - Execute custom SQL query
- `GET /api/stats` - Get database statistics
- `POST /api/value_counts` - Get frequency distributions

## Usage Examples

### Get Schema

```bash
curl https://your-app.onrender.com/api/schema
```

### Get Sample Data

```bash
curl https://your-app.onrender.com/api/sample?limit=10
```

### Execute Query

```bash
curl -X POST https://your-app.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT type, COUNT(*) FROM digital_insights GROUP BY type"}'
```

### Get Statistics

```bash
curl https://your-app.onrender.com/api/stats
```

## Configuration for MCP Clients

### For ChatGPT Desktop (OpenAI)

1. Open ChatGPT Settings → Connectors → Advanced → Developer Mode
2. Enable Developer Mode
3. Add your deployed MCP server using the Streamable HTTP endpoint:

**Configuration:**
```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app.onrender.com/mcp"
    }
  }
}
```

**Note:** ChatGPT cannot connect to localhost. You must deploy to a public URL (e.g., Render, ngrok, etc.)

### For Claude Desktop

1. Open Claude Desktop Settings → Developer → Edit Config
2. Add the following to `claude_desktop_config.json`:

**For Remote Server (Deployed):**
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

**For Local Development:**
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

**Note:** The `/mcp` endpoint is critical - don't forget it!

### For Claude Code (VS Code Extension)

Use the CLI command:
```bash
claude mcp add --transport http analytics https://your-app.onrender.com/mcp
```

Or for local:
```bash
claude mcp add --transport http analytics http://localhost:8000/mcp
```

## Free Tier Limits

### Render PostgreSQL Free Tier
- 1 GB storage
- 90 days data retention
- Shared CPU
- 256 MB RAM

### Render Web Service Free Tier
- 750 hours/month
- Shared CPU
- 512 MB RAM
- Spins down after 15 min inactivity
- Cold start: ~30 seconds

## Security

- Only SELECT queries allowed
- Maximum 1000 rows per query
- Dangerous keywords blocked
- SQL injection protection
- Environment-based configuration

## Monitoring

- Health endpoint: `/health`
- Render provides automatic health checks
- View logs in Render dashboard
- Automatic restart on failure

## Scaling

To upgrade from free tier:

1. **Database**: Upgrade to Starter ($7/month) for 10GB storage
2. **Web Service**: Upgrade to Starter ($7/month) for always-on service

## Troubleshooting

### Database Connection Failed

Check that:
1. DATABASE_URL is set correctly
2. Database is running (check Render dashboard)
3. Database URL format is `postgresql://` not `postgres://`

### Server Not Responding

1. Check Render logs for errors
2. Verify the server is running (check Render dashboard)
3. On free tier, wait 30 seconds for cold start

### Data Not Loading

1. Verify local database has data
2. Check DATABASE_URL is accessible
3. Review data loading script logs

## Support

For issues:
1. Check Render status page
2. Review server logs in Render dashboard
3. Test endpoints with curl
4. Check database connection

---

## 📖 Development Phases

| Phase | Status | Timeline | Description |
|-------|--------|----------|-------------|
| **Phase 1** | ✅ Complete | Week 1-2 | Basic MCP server with single dataset |
| **Phase 2** | 🔄 In Progress | Week 3-4 | Multi-dataset + LLM metadata generation |
| **Phase 3** | 📋 Planned | Week 5-6 | UI dashboard for dataset management |
| **Phase 4** | 📋 Planned | Week 7-8 | Parallel query execution + optimization |
| **Phase 5** | 📋 Planned | Week 9 | Query logs + monitoring dashboard |

**See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed specifications.**

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific tests
pytest tests/test_dataset_service.py -v
```

---

## 🤝 Contributing

### Development Workflow

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test locally
3. Run linting: `black app/ && ruff check app/`
4. Run tests: `pytest`
5. Commit: `git commit -m "Add feature"`
6. Push and create PR

### Code Quality

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

## 📊 Key Concepts

### Weighting Methodology
All data represents a **sample population** where each user has a **weight**:
- User weight 0.456 = represents 456 people in their demographic cell
- Cell = age/gender/NCCS/townclass/state
- **Always weigh users, NOT events**
- Report at **weighted level** unless specified

### Progressive Context Loading
To optimize token usage:
- **Level 0**: Global rules only (~500 tokens)
- **Level 1**: Dataset summaries (~2000 tokens)
- **Level 2**: Table schemas (~5000 tokens)
- **Level 3**: Full schema + samples (~10000 tokens)

### Hot-Reload Mechanism
When a new dataset is approved:
1. Status changes to `approved`
2. Redis pub/sub notification sent
3. MCP server reloads (no restart!)
4. LLM clients see new dataset immediately

---

## 🔐 Security

- Connection strings encrypted at rest (Fernet)
- SQL injection protection (query validation)
- SELECT-only queries enforced
- Row limits (5 for raw data, 1000 for aggregated)
- Environment-based secrets management

---

## 📈 Scaling

### Free Tier (Current)
- **Cost**: $0/month
- **Limitations**: Cold starts, 1GB storage, 90-day retention
- **Best for**: 5-10 users, development/testing

### Starter Tier (Recommended for Production)
- **Cost**: $28/month
- **Benefits**: Always-on, 10GB storage, unlimited retention
- **Best for**: 10-100 users

### Enterprise (Future)
- **Cost**: Custom
- **Benefits**: Dedicated resources, autoscaling, SLA
- **Best for**: 100+ users, mission-critical
- **Migration**: Simply update connection strings in .env (no code changes)

**See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for scaling guide.**

---

## 📞 Support

- **Documentation**: See [docs](docs/) folder
- **Issues**: GitHub Issues
- **API Docs**: `https://your-app.onrender.com/docs`

---

## 📝 License

Proprietary - Internal Use Only

---

## 🎉 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [OpenAI](https://openai.com)

---

## Next Steps

### For Developers
1. Read [GETTING_STARTED.md](GETTING_STARTED.md)
2. Set up local environment
3. Review [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
4. Start implementing Phase 2

### For Product Managers
1. Review [ARCHITECTURE.md](ARCHITECTURE.md)
2. Check implementation timeline
3. Prepare test datasets
4. Define success metrics

### For DevOps
1. Review [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
2. Get PostgreSQL connection strings from data team
3. Set up CI/CD pipeline
4. Configure monitoring

