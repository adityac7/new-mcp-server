# UI Dashboard Documentation

## Overview

The MCP Analytics Server now includes a fully functional web-based UI dashboard for managing datasets and monitoring query logs. Built with **HTMX**, **Alpine.js**, and **Tailwind CSS** for a modern, zero-build-step experience.

## Tech Stack

- **HTMX 1.9.10**: Server-side rendering with AJAX (no JavaScript build step)
- **Alpine.js 3.13.3**: Minimal client-side interactivity
- **Tailwind CSS**: Utility-first styling (via CDN)
- **Jinja2**: Server-side template rendering
- **FastAPI**: Backend routing and API

## Pages

### 1. Dashboard (`/ui`)

**Purpose**: Overview of system status

**Features**:
- **Stats Grid** (4 cards):
  - Total Datasets
  - Active Datasets
  - Queries Today
  - Average Query Time (ms)
- **Recent Datasets** (last 5)
- **Recent Query Logs** (last 5)
- **Quick Actions**: Add Dataset, View Logs, API Docs

**Route**: `GET /ui/`

---

### 2. Datasets List (`/ui/datasets`)

**Purpose**: Manage all datasets

**Features**:
- **Stats Summary** (3 cards):
  - Total Datasets
  - Active Datasets
  - Pending Datasets
- **Dataset Table**:
  - Name, Description, Table Count, Status, Created Date
  - Actions: View, Activate/Deactivate, Delete
  - HTMX-powered inline actions (no page reload)
- **Add Dataset** button → redirects to `/ui/datasets/new`

**Routes**:
- `GET /ui/datasets` - List all datasets
- `POST /ui/datasets/{id}/activate` - Activate dataset
- `POST /ui/datasets/{id}/deactivate` - Deactivate dataset
- `DELETE /ui/datasets/{id}` - Delete dataset

---

### 3. Add Dataset (`/ui/datasets/new`)

**Purpose**: Add new database connection

**Features**:
- **Form Fields**:
  - Dataset Name (required)
  - Description (optional)
  - PostgreSQL Connection String (required)
- **Info Boxes**:
  - "What happens next?" - Explains profiling process
  - "Read-Only & Secure" - Security guarantees
- **Example Connection Strings** (local, remote, Render.com)

**Backend Processing**:
1. Connection string encrypted with Fernet
2. Dataset stored in metadata DB
3. Background profiling triggered (Celery)
4. Schema metadata generated
5. AI descriptions generated (GPT-4.1-mini)

**Routes**:
- `GET /ui/datasets/new` - Show form
- `POST /ui/datasets` - Create dataset and trigger profiling

---

### 4. Dataset Detail (`/ui/datasets/{id}`)

**Purpose**: View dataset schema and recent queries

**Features**:
- **Info Cards** (4 cards):
  - Tables Count
  - Total Columns
  - Queries Today
  - Created Date
- **Database Schema**:
  - Expandable table sections (Alpine.js)
  - Column details: name, type, nullable, AI description
  - "View sample data" link for each table
- **Recent Queries** (last 10):
  - Query text, execution time, row count, success/error status
- **Actions**:
  - Activate/Deactivate Dataset
  - Refresh Schema (re-trigger profiling)
  - Delete Dataset

**Routes**:
- `GET /ui/datasets/{id}` - Show dataset details
- `POST /ui/datasets/{id}/reprocess` - Re-trigger profiling

---

### 5. Query Logs (`/ui/logs`)

**Purpose**: Monitor all MCP query executions

**Features**:
- **Stats Summary** (4 cards):
  - Total Queries
  - Success Rate (%)
  - Average Time (ms)
  - Queries Today
- **Filters**:
  - Dataset (dropdown)
  - Client (ChatGPT, Claude Desktop, Cursor)
  - Status (All, Success, Error)
- **Query Table** (paginated, 50 per page):
  - Time, Query text, Dataset, Client, Rows, Time (ms), Status
  - "View" button → opens modal with full query and error message
- **Clear Logs** button (with confirmation)

**Query Detail Modal** (Alpine.js):
- Full SQL query (formatted)
- Error message (if failed)

**Routes**:
- `GET /ui/logs` - List query logs with filters
- `DELETE /ui/logs` - Clear all logs

---

## Installation & Setup

### 1. Install Dependencies

The UI uses CDN-hosted libraries, so no additional npm packages needed. Just ensure FastAPI dependencies:

```bash
pip install fastapi jinja2 python-multipart
```

### 2. Run the Server

**Control Plane (UI + REST API)**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**MCP Server (for ChatGPT connection)**:
```bash
python server.py
```

### 3. Access the UI

Open your browser and navigate to:

```
http://localhost:8000/ui
```

---

## File Structure

```
app/
├── ui/
│   ├── __init__.py             # UI module initialization
│   ├── routes.py               # FastAPI routes for UI
│   └── templates/
│       ├── base.html           # Base template with CDN imports
│       ├── dashboard.html      # Dashboard homepage
│       ├── datasets.html       # Datasets list
│       ├── dataset_new.html    # Add dataset form
│       ├── dataset_detail.html # Dataset details with schema
│       └── logs.html           # Query logs
├── main.py                     # FastAPI app (imports UI routes)
└── ...
```

---

## How It Works

### HTMX Pattern

HTMX allows server-side rendering with AJAX requests **without writing JavaScript**:

**Example**: Activate Dataset

```html
<button
    hx-post="/ui/datasets/{{ dataset.id }}/activate"
    hx-swap="outerHTML"
    hx-target="closest tr"
    class="text-green-600 hover:text-green-900">
    Activate
</button>
```

**What happens**:
1. User clicks "Activate"
2. HTMX sends POST to `/ui/datasets/123/activate`
3. Server updates dataset status
4. Server returns new HTML for the table row
5. HTMX swaps the old row with the new one (no page reload!)

### Alpine.js Pattern

Alpine.js adds minimal JavaScript for client-side interactivity:

**Example**: Expandable Schema Table

```html
<div x-data="{ expanded: false }">
    <div @click="expanded = !expanded">
        <h4>Table Name</h4>
        <svg :class="expanded && 'rotate-180'">...</svg>
    </div>

    <div x-show="expanded" x-collapse>
        <!-- Table columns details -->
    </div>
</div>
```

**What happens**:
1. User clicks table name
2. Alpine.js toggles `expanded` state
3. Details section shows/hides with animation
4. Arrow icon rotates

---

## API Routes Summary

| Route | Method | Purpose |
|-------|--------|---------|
| `/ui` | GET | Dashboard homepage |
| `/ui/datasets` | GET | List all datasets |
| `/ui/datasets/new` | GET | Show add dataset form |
| `/ui/datasets` | POST | Create new dataset |
| `/ui/datasets/{id}` | GET | Dataset details |
| `/ui/datasets/{id}/activate` | POST | Activate dataset |
| `/ui/datasets/{id}/deactivate` | POST | Deactivate dataset |
| `/ui/datasets/{id}/reprocess` | POST | Re-trigger profiling |
| `/ui/datasets/{id}` | DELETE | Delete dataset |
| `/ui/logs` | GET | Query logs (with filters) |
| `/ui/logs` | DELETE | Clear all logs |

---

## Deployment Notes

### Production Deployment (Render.com)

1. **Deploy Control Plane**:
   - Service: `mcp-analytics-control-plane`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Exposes UI at: `https://your-service.onrender.com/ui`

2. **Deploy MCP Server** (separate service):
   - Service: `mcp-analytics-mcp-server`
   - Start command: `python server.py`
   - Port: 8001
   - Used by ChatGPT via MCP protocol

### Environment Variables

```bash
# Control Plane
METADATA_DATABASE_URL=postgresql://user:pass@host/metadata_db
ENCRYPTION_KEY=your_fernet_key_here
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
OPENAI_API_KEY=sk-...

# MCP Server (inherits from above)
MCP_SERVER_PORT=8001
```

---

## User Workflow

### Adding a Dataset

1. Navigate to **Dashboard** → Click **"Add Dataset"**
2. Fill in form:
   - Name: `CMI Panel Data`
   - Description: `Consumer panel data with NCCS and weighting`
   - Connection String: `postgresql://user:pass@host:5432/panel_db`
3. Click **"Add Dataset"**
4. Background processing starts:
   - ✅ Connection tested
   - ✅ Connection string encrypted
   - ✅ Schema profiled (tables, columns, types)
   - ✅ Weight/NCCS columns detected
   - ✅ AI metadata generated (GPT-4.1-mini)
   - ✅ Dataset marked as **Active**
5. View dataset in **Datasets** list

### Querying via ChatGPT

1. ChatGPT connects to MCP server (port 8001)
2. ChatGPT discovers available tools via MCP protocol
3. User asks: *"Show me top 10 brands by sales"*
4. ChatGPT:
   - Calls `get_datasets()` → sees `CMI Panel Data`
   - Calls `get_dataset_schema(1)` → sees tables and columns
   - Calls `execute_query_on_dataset()` with SQL
5. Query logged to database
6. User can view query in **Query Logs** page

### Monitoring Queries

1. Navigate to **Query Logs**
2. Filter by:
   - Dataset (dropdown)
   - Client (ChatGPT, Claude, Cursor)
   - Status (Success/Error)
3. Click **"View"** on any query → see full SQL and error message
4. Click **"Clear Logs"** to reset

---

## Next Steps (Future Enhancements)

1. **Real-time Updates**: WebSockets for live query log updates
2. **Query Templates**: Pre-built queries for common use cases
3. **Performance Charts**: Chart.js visualizations for query performance
4. **User Management**: Authentication and authorization
5. **Dataset Search**: Full-text search across datasets and schemas
6. **Export Logs**: Download query logs as CSV
7. **Dark Mode**: Toggle light/dark theme
8. **API Key Management**: UI for managing API keys

---

## Troubleshooting

### UI not loading

```bash
# Check if templates directory exists
ls -la app/ui/templates/

# Check if routes are registered
curl http://localhost:8000/ui
```

### HTMX requests failing

- Open browser DevTools → Network tab
- Check for failed POST/DELETE requests
- Verify CORS settings in `app/main.py`

### Alpine.js not working

- Check browser console for JavaScript errors
- Ensure CDN links are accessible
- Verify `x-data` and `x-show` syntax

---

## Support

For issues or questions:
1. Check `/docs` endpoint for API documentation
2. Review logs: `docker logs <container_id>`
3. GitHub Issues: https://github.com/your-repo/issues

---

**Built with ❤️ using HTMX, Alpine.js, and Tailwind CSS**
