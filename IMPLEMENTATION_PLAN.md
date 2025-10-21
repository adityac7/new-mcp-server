# Production-Grade Multi-Database MCP Server - Detailed Implementation Plan

> **Based on**: Existing Phase 1 (server.py) with Python FastMCP
> **Language**: Python 3.11+
> **Framework**: FastAPI + FastMCP
> **Deployment**: Render.com → Azure migration path
> **Timeline**: 6-8 weeks for complete implementation

---

## Table of Contents
1. [Technology Stack Decisions](#1-technology-stack-decisions)
2. [Project Structure](#2-project-structure)
3. [Database Architecture](#3-database-architecture)
4. [Phase 2: Multi-Dataset Management + LLM Metadata](#phase-2-multi-dataset-management--llm-metadata)
5. [Phase 3: UI Dashboard](#phase-3-ui-dashboard)
6. [Phase 4: Parallel Query Execution + Optimization](#phase-4-parallel-query-execution--optimization)
7. [Phase 5: Query Logs + Monitoring](#phase-5-query-logs--monitoring)
8. [Critical Technical Decisions](#critical-technical-decisions)
9. [Implementation Checklist](#implementation-checklist)

---

## 1. Technology Stack Decisions

### Backend Stack (Python)
```
FastAPI 0.104+          → REST API + Control Plane
FastMCP 2.3.4+          → MCP Server (existing Phase 1)
asyncpg 0.29+           → Async PostgreSQL driver (parallel queries)
SQLAlchemy 2.0+         → ORM for metadata DB
psycopg2-binary         → Sync PostgreSQL (keep for compatibility)
Pydantic 2.5+           → Schema validation
Redis 5.0+              → Cache + Pub/Sub for hot-reload
Celery 5.3+             → Background tasks (LLM metadata generation)
```

### LLM Integration
```
OpenAI Python SDK       → GPT-4o-mini for metadata generation
tiktoken                → Token counting for context optimization
```

### Frontend Stack (Lightweight)
```
HTMX 1.9+               → Server-side rendered UI (simplest option)
Alpine.js 3.13+         → Minimal client-side interactivity
Tailwind CSS 3.4+       → Styling
Jinja2 Templates        → Server-side rendering
```

**Why HTMX over React/Vue?**
- Zero build step
- Server-rendered (fast)
- Perfect for dashboards and forms
- Easy for non-developers to maintain
- Works seamlessly with FastAPI

### Data Processing
```
pandas 2.1+             → Weighted calculations, aggregations
polars 0.19+            → High-performance alternative for large datasets
```

### Deployment
```
Render.com              → Phase 1-3 (simple deployment)
Docker                  → Containerization for Azure migration
Gunicorn + Uvicorn      → Production ASGI server
```

---

## 2. Project Structure

```
mcp-analytics-server/
├── README.md
├── ARCHITECTURE.md                 # High-level architecture (existing)
├── IMPLEMENTATION_PLAN.md          # This file
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Development dependencies
├── .env.example                    # Environment variables template
├── .gitignore
├── Dockerfile                      # Container definition
├── docker-compose.yml              # Local development
├── render.yaml                     # Render deployment config
│
├── alembic/                        # Database migrations
│   ├── versions/
│   └── env.py
│
├── app/
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── main.py                     # FastAPI application entry
│   │
│   ├── core/                       # Core functionality
│   │   ├── __init__.py
│   │   ├── security.py             # Encryption for connection strings
│   │   ├── database.py             # Database connection managers
│   │   ├── redis_client.py         # Redis connection
│   │   └── context_optimizer.py   # Progressive context loading
│   │
│   ├── models/                     # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── dataset.py              # Dataset registry model
│   │   ├── query_log.py            # Query logging model
│   │   └── metadata.py             # LLM-generated metadata model
│   │
│   ├── schemas/                    # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── dataset.py              # Dataset DTOs
│   │   ├── query.py                # Query request/response schemas
│   │   └── metadata.py             # Metadata schemas
│   │
│   ├── api/                        # REST API routes
│   │   ├── __init__.py
│   │   ├── datasets.py             # Dataset CRUD endpoints
│   │   ├── metadata.py             # Metadata generation endpoints
│   │   ├── queries.py              # Query execution endpoints
│   │   └── logs.py                 # Query log endpoints
│   │
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── dataset_service.py      # Dataset management
│   │   ├── schema_profiler.py      # Auto schema analysis
│   │   ├── llm_metadata_service.py # LLM metadata generation
│   │   ├── query_executor.py       # Parallel query execution
│   │   ├── weighting_service.py    # Weight calculation logic
│   │   └── context_service.py      # Progressive context loading
│   │
│   ├── mcp/                        # MCP Server (extends Phase 1)
│   │   ├── __init__.py
│   │   ├── server.py               # FastMCP server with dynamic tools
│   │   ├── tools.py                # MCP tool definitions
│   │   └── resources.py            # MCP resource definitions
│   │
│   ├── ui/                         # HTMX UI
│   │   ├── __init__.py
│   │   ├── routes.py               # UI routes
│   │   └── templates/              # Jinja2 templates
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── dataset_form.html
│   │       ├── dataset_list.html
│   │       └── query_logs.html
│   │
│   └── workers/                    # Background tasks
│       ├── __init__.py
│       ├── celery_app.py           # Celery configuration
│       └── tasks.py                # Async tasks (schema profiling, LLM)
│
├── scripts/                        # Utility scripts
│   ├── init_metadata_db.py         # Initialize metadata database
│   ├── migrate_phase1_data.py      # Migrate existing data to new structure
│   └── test_connections.py         # Test dataset connections
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_dataset_service.py
│   ├── test_query_executor.py
│   └── test_mcp_tools.py
│
└── docs/                           # Additional documentation
    ├── API.md                      # API documentation
    ├── MCP_TOOLS.md                # MCP tool reference
    └── DEPLOYMENT.md               # Deployment guide
```

---

## 3. Database Architecture

### 3.1 Metadata Database Schema

**Purpose**: Store dataset registry, schemas, LLM-generated metadata, query logs

```sql
-- Database: metadata_db (separate from user datasets)

-- =======================
-- Table: datasets
-- =======================
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,  -- Short 1-2 line description
    connection_string_encrypted TEXT NOT NULL,  -- Encrypted connection string
    dataset_type VARCHAR(50),  -- 'event_level', 'aggregated', 'mixed'
    data_source VARCHAR(100),  -- 'fabric', 'postgres', 'custom'
    status VARCHAR(50) DEFAULT 'draft',  -- 'draft', 'profiling', 'metadata_pending', 'approved', 'active', 'inactive'

    -- Metadata fields (LLM-generated)
    date_range_start DATE,
    date_range_end DATE,
    data_category VARCHAR(100),  -- 'ctv', 'mobile', 'ecommerce', 'ads'
    use_cases TEXT[],  -- ['media planning', 'ecommerce optimization']
    has_weight_column BOOLEAN DEFAULT false,
    weight_column_name VARCHAR(100),

    -- Governance
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    approved_by VARCHAR(100),

    -- Performance
    estimated_row_count BIGINT,
    last_profiled_at TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('draft', 'profiling', 'metadata_pending', 'approved', 'active', 'inactive'))
);

CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_name ON datasets(name);


-- =======================
-- Table: dataset_schemas
-- =======================
CREATE TABLE dataset_schemas (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    table_schema JSONB NOT NULL,  -- Full schema as JSON
    sample_data JSONB,  -- Sample rows for context
    row_count BIGINT,

    -- Column-level metadata
    columns JSONB NOT NULL,
    -- Example: [{"name": "user_id", "type": "bigint", "nullable": false, "description": "Unique user identifier"}]

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(dataset_id, table_name)
);

CREATE INDEX idx_dataset_schemas_dataset_id ON dataset_schemas(dataset_id);


-- =======================
-- Table: llm_metadata
-- =======================
CREATE TABLE llm_metadata (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,

    -- LLM-generated content
    generated_description TEXT,  -- Detailed description
    data_dictionary JSONB,  -- Column explanations
    quality_observations TEXT[],  -- Data quality notes
    improvement_suggestions TEXT[],  -- Suggested improvements
    recommended_use_cases TEXT[],  -- Use case recommendations

    -- LLM metadata
    llm_model VARCHAR(100),  -- 'gpt-4o-mini'
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    generation_time_seconds FLOAT,

    -- User validation
    user_edited BOOLEAN DEFAULT false,
    user_approved BOOLEAN DEFAULT false,
    user_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_llm_metadata_dataset_id ON llm_metadata(dataset_id);


-- =======================
-- Table: query_logs
-- =======================
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,

    -- Query metadata
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),  -- 'raw', 'aggregated', 'weighted'
    datasets_used INTEGER[],  -- Array of dataset IDs

    -- Execution details
    execution_time_ms INTEGER,
    rows_returned INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,

    -- Context
    tool_used VARCHAR(100),  -- 'chatgpt', 'claude', 'manus', 'api'
    user_agent TEXT,
    session_id VARCHAR(255),

    -- Response metadata
    response_format VARCHAR(50),  -- 'markdown', 'json'
    response_size_bytes INTEGER,
    was_cached BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX idx_query_logs_tool_used ON query_logs(tool_used);
CREATE INDEX idx_query_logs_datasets_used ON query_logs USING GIN(datasets_used);


-- =======================
-- Table: context_cache
-- =======================
CREATE TABLE context_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    context_level INTEGER,  -- 0=global, 1=dataset_summary, 2=table_detail, 3=full
    context_data JSONB NOT NULL,
    token_count INTEGER,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_context_cache_key ON context_cache(cache_key);
CREATE INDEX idx_context_cache_expires ON context_cache(expires_at);
```

### 3.2 Connection String Encryption

```python
# app/core/security.py
from cryptography.fernet import Fernet
import os
import base64

class ConnectionStringEncryption:
    def __init__(self):
        # Key stored in environment variable
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            # Generate new key for first-time setup
            key = Fernet.generate_key()
            print(f"Generated encryption key: {key.decode()}")
            print("Store this in ENCRYPTION_KEY environment variable!")
        else:
            key = key.encode()
        self.cipher = Fernet(key)

    def encrypt(self, connection_string: str) -> str:
        """Encrypt a database connection string"""
        return self.cipher.encrypt(connection_string.encode()).decode()

    def decrypt(self, encrypted_string: str) -> str:
        """Decrypt a database connection string"""
        return self.cipher.decrypt(encrypted_string.encode()).decode()

# Usage
encryptor = ConnectionStringEncryption()
```

### 3.3 Redis Schema (Cache + Pub/Sub)

**Keys:**
```
# Dataset schema cache
dataset:schema:{dataset_id}:level_{level}  → JSON (TTL: 3600s)

# Query result cache
query:result:{hash(query+datasets)}  → JSON (TTL: 300s)

# Connection pool status
dataset:pool:{dataset_id}:status  → JSON (TTL: none)

# Pub/Sub channels
channel:dataset:activated  → Notifications when new dataset goes live
channel:dataset:updated    → Schema changes
```

---

## Phase 2: Multi-Dataset Management + LLM Metadata

**Timeline**: Week 3-4 (2 weeks)
**Goal**: Enable adding multiple datasets with auto-generated metadata

### 2.1 Dataset Registration Flow

```
User Action                  Backend Process                 LLM Process
─────────────────────────────────────────────────────────────────────────
1. Enter connection string
   ↓
2. Click "Analyze"     →    Validate connection
                            Create dataset (status=draft)
   ↓
3. Show loading...     →    Start async profiling job
                            ├─ Connect to database
                            ├─ List all tables
                            ├─ Sample each table (1000 rows)
                            ├─ Get schema (columns, types)
                            ├─ Calculate row counts
                            ├─ Detect weight column
                            ├─ Identify date columns
                            └─ Store in dataset_schemas
   ↓
4. Profiling done      →    Trigger LLM metadata job
                            ├─ Build prompt with:          →  GPT-4o-mini analyzes
                            │  • Global context                 • Table schemas
                            │  • Table schemas                  • Sample data
                            │  • Sample data                    • Column distributions
                            │  • Business rules                 • Data quality
                            └─ Call OpenAI API
   ↓                                                        ↓
5. Show generated      ←    Store in llm_metadata      ←   Returns:
   metadata                 (status=metadata_pending)        • Description
                                                             • Data dictionary
                                                             • Use cases
                                                             • Quality notes
   ↓
6. User reviews/edits
   ↓
7. Click "Approve"     →    Update dataset (status=approved)
                            Publish to Redis pub/sub
                            MCP server reloads tools
   ↓
8. Dataset LIVE        →    MCP tools now include new dataset
```

### 2.2 Schema Profiler Implementation

```python
# app/services/schema_profiler.py
import asyncpg
from typing import Dict, List, Any
from app.models.dataset import Dataset
from app.core.security import ConnectionStringEncryption

class SchemaProfiler:
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self.encryptor = ConnectionStringEncryption()

    async def profile(self) -> Dict[str, Any]:
        """Profile the database schema"""
        conn_string = self.encryptor.decrypt(self.dataset.connection_string_encrypted)

        # Connect using asyncpg for better performance
        conn = await asyncpg.connect(conn_string)

        try:
            # 1. List all tables
            tables = await self._get_tables(conn)

            # 2. Profile each table
            table_profiles = []
            for table in tables:
                profile = await self._profile_table(conn, table)
                table_profiles.append(profile)

            # 3. Detect weight column
            weight_info = await self._detect_weight_column(conn, tables)

            return {
                'tables': table_profiles,
                'table_count': len(tables),
                'weight_info': weight_info,
                'estimated_total_rows': sum(t['row_count'] for t in table_profiles)
            }
        finally:
            await conn.close()

    async def _get_tables(self, conn) -> List[str]:
        """Get all table names in the database"""
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        rows = await conn.fetch(query)
        return [row['table_name'] for row in rows]

    async def _profile_table(self, conn, table_name: str) -> Dict[str, Any]:
        """Profile a single table"""
        # Get schema
        schema_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        columns = await conn.fetch(schema_query)

        # Get row count (use EXPLAIN for large tables)
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        row_count = await conn.fetchval(count_query)

        # Sample data (limit 1000 rows for LLM analysis)
        sample_query = f"SELECT * FROM {table_name} LIMIT 1000"
        sample_rows = await conn.fetch(sample_query)

        # Convert to dict for JSON storage
        sample_data = [dict(row) for row in sample_rows[:10]]  # Store only 10 samples

        # Get column statistics
        column_stats = []
        for col in columns:
            col_name = col['column_name']
            stats = await self._get_column_stats(conn, table_name, col_name, col['data_type'])
            column_stats.append({
                'name': col_name,
                'type': col['data_type'],
                'nullable': col['is_nullable'] == 'YES',
                'stats': stats
            })

        return {
            'table_name': table_name,
            'row_count': row_count,
            'columns': column_stats,
            'sample_data': sample_data
        }

    async def _get_column_stats(self, conn, table: str, column: str, dtype: str) -> Dict:
        """Get statistics for a column"""
        stats = {}

        # Null count
        null_query = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"
        stats['null_count'] = await conn.fetchval(null_query)

        # Distinct count (for categorical columns)
        if dtype in ['character varying', 'text', 'varchar']:
            distinct_query = f"SELECT COUNT(DISTINCT {column}) FROM {table}"
            stats['distinct_count'] = await conn.fetchval(distinct_query)

        # Date range (for date columns)
        if dtype in ['date', 'timestamp', 'timestamp with time zone']:
            range_query = f"SELECT MIN({column}), MAX({column}) FROM {table}"
            min_val, max_val = await conn.fetchrow(range_query)
            stats['min_date'] = str(min_val) if min_val else None
            stats['max_date'] = str(max_val) if max_val else None

        return stats

    async def _detect_weight_column(self, conn, tables: List[str]) -> Dict:
        """Detect if there's a weight column"""
        # Common weight column names
        weight_patterns = ['weight', 'wt', 'sample_weight', 'user_weight']

        for table in tables:
            for pattern in weight_patterns:
                # Check if column exists
                check_query = f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    AND column_name ILIKE '%{pattern}%'
                """
                result = await conn.fetchrow(check_query)
                if result:
                    return {
                        'has_weight': True,
                        'table': table,
                        'column': result['column_name']
                    }

        return {'has_weight': False}
```

### 2.3 LLM Metadata Generation

```python
# app/services/llm_metadata_service.py
from openai import AsyncOpenAI
from typing import Dict, Any
import json

class LLMMetadataService:
    def __init__(self):
        self.client = AsyncOpenAI()
        self.model = "gpt-4o-mini"

    async def generate_metadata(self, dataset_id: int, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata using LLM"""

        # Build prompt
        prompt = self._build_prompt(profile)

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more consistent output
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        return {
            'generated_description': result['description'],
            'data_dictionary': result['data_dictionary'],
            'quality_observations': result['quality_observations'],
            'improvement_suggestions': result['improvement_suggestions'],
            'recommended_use_cases': result['recommended_use_cases'],
            'llm_model': self.model,
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens
        }

    def _get_system_prompt(self) -> str:
        """System prompt with business context"""
        return """You are a data analyst expert specializing in consumer insights data from panel populations.

CRITICAL CONTEXT:
- All data comes from a sample representative population
- Data collected consentfully from smartphones/CTV using proprietary tech
- Users carry weights (e.g., 0.456 = represents 456 individuals in their cell)
- Cell = age/gender/NCCS/townclass/state combination
- All reporting MUST be at weighted level (weigh users, not events)
- Never show more than 5 raw rows (aggregated data is fine)
- Data can be event-level or aggregated
- NCCS merging: A+A1, C+D/E → C/D/E

Your task is to analyze database schemas and generate:
1. Clear, concise description (1-2 lines) for LLMs to understand the data
2. Data dictionary with column explanations
3. Date ranges and data types (CTV/Mobile/Ads/Ecommerce)
4. Recommended use cases (media planning, ecommerce optimization, etc.)
5. Data quality observations
6. Improvement suggestions (date formats, missing weights, etc.)

Output JSON format:
{
  "description": "Short 1-2 line description",
  "data_dictionary": {"column_name": "explanation", ...},
  "quality_observations": ["observation1", ...],
  "improvement_suggestions": ["suggestion1", ...],
  "recommended_use_cases": ["use_case1", ...]
}
"""

    def _build_prompt(self, profile: Dict[str, Any]) -> str:
        """Build the analysis prompt"""
        tables_summary = []

        for table in profile['tables']:
            columns_info = []
            for col in table['columns']:
                col_info = f"- {col['name']} ({col['type']})"
                if col['stats'].get('distinct_count'):
                    col_info += f" - {col['stats']['distinct_count']} unique values"
                if col['stats'].get('min_date') and col['stats'].get('max_date'):
                    col_info += f" - Range: {col['stats']['min_date']} to {col['stats']['max_date']}"
                columns_info.append(col_info)

            tables_summary.append(f"""
Table: {table['table_name']}
Rows: {table['row_count']:,}
Columns:
{chr(10).join(columns_info)}

Sample data (first 2 rows):
{json.dumps(table['sample_data'][:2], indent=2, default=str)}
""")

        return f"""Analyze this database and generate metadata:

Total Tables: {profile['table_count']}
Total Rows: ~{profile['estimated_total_rows']:,}
Weight Column Detected: {profile['weight_info']['has_weight']}
{f"Weight Column: {profile['weight_info']['table']}.{profile['weight_info']['column']}" if profile['weight_info']['has_weight'] else ""}

{chr(10).join(tables_summary)}

Generate comprehensive metadata following the required JSON format."""
```

### 2.4 Background Task Worker (Celery)

```python
# app/workers/tasks.py
from celery import Celery
from app.services.schema_profiler import SchemaProfiler
from app.services.llm_metadata_service import LLMMetadataService
from app.models.dataset import Dataset
from app.core.database import get_db

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def profile_dataset_task(dataset_id: int):
    """Async task to profile a dataset"""
    db = next(get_db())
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        return {'error': 'Dataset not found'}

    # Update status
    dataset.status = 'profiling'
    db.commit()

    # Run profiler
    profiler = SchemaProfiler(dataset)
    profile = profiler.profile()  # Async call

    # Store schema
    # ... (store in dataset_schemas table)

    # Update dataset
    dataset.estimated_row_count = profile['estimated_total_rows']
    dataset.has_weight_column = profile['weight_info']['has_weight']
    if profile['weight_info']['has_weight']:
        dataset.weight_column_name = profile['weight_info']['column']
    dataset.status = 'metadata_pending'
    dataset.last_profiled_at = datetime.now()
    db.commit()

    # Trigger LLM metadata generation
    generate_llm_metadata_task.delay(dataset_id, profile)

    return {'success': True, 'dataset_id': dataset_id}

@celery_app.task
def generate_llm_metadata_task(dataset_id: int, profile: dict):
    """Async task to generate LLM metadata"""
    db = next(get_db())

    service = LLMMetadataService()
    metadata = service.generate_metadata(dataset_id, profile)

    # Store in llm_metadata table
    # ... (SQLAlchemy insert)

    return {'success': True, 'dataset_id': dataset_id}
```

### 2.5 Dataset API Endpoints

```python
# app/api/datasets.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.dataset import DatasetCreate, DatasetResponse
from app.core.database import get_db
from app.workers.tasks import profile_dataset_task

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.post("/", response_model=DatasetResponse)
async def create_dataset(dataset: DatasetCreate, db: Session = Depends(get_db)):
    """
    Create a new dataset and start profiling

    Flow:
    1. Validate connection string
    2. Encrypt and store
    3. Trigger async profiling job
    """
    from app.services.dataset_service import DatasetService

    service = DatasetService(db)

    # Validate connection
    is_valid, error = await service.validate_connection(dataset.connection_string)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Connection failed: {error}")

    # Create dataset
    new_dataset = await service.create_dataset(dataset)

    # Start profiling (async)
    profile_dataset_task.delay(new_dataset.id)

    return new_dataset

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """Get dataset by ID"""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all datasets with optional status filter"""
    query = db.query(Dataset)
    if status:
        query = query.filter(Dataset.status == status)
    return query.offset(skip).limit(limit).all()

@router.patch("/{dataset_id}/approve")
async def approve_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """
    Approve dataset and activate it

    This triggers:
    1. Status update to 'approved'
    2. Redis pub/sub notification
    3. MCP server reload (hot-reload)
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.status != 'metadata_pending':
        raise HTTPException(status_code=400, detail="Dataset not ready for approval")

    # Update status
    dataset.status = 'approved'
    dataset.approved_at = datetime.now()
    db.commit()

    # Publish to Redis for hot-reload
    from app.core.redis_client import redis_client
    redis_client.publish('channel:dataset:activated', json.dumps({
        'dataset_id': dataset_id,
        'name': dataset.name,
        'action': 'activated'
    }))

    return {"success": True, "dataset_id": dataset_id, "status": "approved"}

@router.get("/{dataset_id}/metadata")
async def get_dataset_metadata(dataset_id: int, db: Session = Depends(get_db)):
    """Get LLM-generated metadata for a dataset"""
    metadata = db.query(LLMMetadata).filter(LLMMetadata.dataset_id == dataset_id).first()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return metadata

@router.patch("/{dataset_id}/metadata")
async def update_dataset_metadata(
    dataset_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update LLM-generated metadata (user edits)"""
    metadata = db.query(LLMMetadata).filter(LLMMetadata.dataset_id == dataset_id).first()
    if not metadata:
        raise HTTPException(status_code=404, detail="Metadata not found")

    # Update fields
    for key, value in updates.items():
        if hasattr(metadata, key):
            setattr(metadata, key, value)

    metadata.user_edited = True
    metadata.updated_at = datetime.now()
    db.commit()

    return metadata
```

---

## Phase 3: UI Dashboard

**Timeline**: Week 5-6 (2 weeks)
**Goal**: Build lightweight HTMX-based UI for dataset management

### 3.1 UI Tech Stack

```python
# requirements.txt additions
jinja2==3.1.2
python-multipart==0.0.6
```

### 3.2 UI Routes

```python
# app/ui/routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(prefix="/ui", tags=["ui"])
templates = Jinja2Templates(directory="app/ui/templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard - shows tabs for datasets and query logs"""
    datasets = db.query(Dataset).all()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "datasets": datasets
    })

@router.get("/datasets", response_class=HTMLResponse)
async def dataset_list(request: Request, db: Session = Depends(get_db)):
    """Dataset list view (HTMX partial)"""
    datasets = db.query(Dataset).all()
    return templates.TemplateResponse("dataset_list.html", {
        "request": request,
        "datasets": datasets
    })

@router.get("/datasets/new", response_class=HTMLResponse)
async def dataset_form(request: Request):
    """Dataset creation form"""
    return templates.TemplateResponse("dataset_form.html", {
        "request": request
    })

@router.get("/logs", response_class=HTMLResponse)
async def query_logs(request: Request, db: Session = Depends(get_db)):
    """Query logs view"""
    logs = db.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(100).all()
    return templates.TemplateResponse("query_logs.html", {
        "request": request,
        "logs": logs
    })
```

### 3.3 HTMX Templates

**Base Template**:
```html
<!-- app/ui/templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MCP Analytics Server{% endblock %}</title>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Alpine.js for interactivity -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.13.3/dist/cdn.min.js"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <div class="flex-shrink-0 flex items-center">
                        <h1 class="text-xl font-bold">MCP Analytics Server</h1>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

**Dashboard with Tabs**:
```html
<!-- app/ui/templates/dashboard.html -->
{% extends "base.html" %}

{% block content %}
<div x-data="{ tab: 'datasets' }">
    <!-- Tabs -->
    <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-8">
            <button
                @click="tab = 'datasets'"
                :class="tab === 'datasets' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
                class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
            >
                Datasets
            </button>
            <button
                @click="tab = 'logs'"
                :class="tab === 'logs' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'"
                class="whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm"
            >
                Query Logs
            </button>
        </nav>
    </div>

    <!-- Tab Content -->
    <div class="mt-6">
        <!-- Datasets Tab -->
        <div x-show="tab === 'datasets'">
            <div class="mb-4">
                <button
                    hx-get="/ui/datasets/new"
                    hx-target="#modal-content"
                    class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                    Add New Dataset
                </button>
            </div>

            <div
                id="dataset-list"
                hx-get="/ui/datasets"
                hx-trigger="load, datasetUpdated from:body"
            >
                <!-- Dataset list will be loaded here -->
            </div>
        </div>

        <!-- Query Logs Tab -->
        <div x-show="tab === 'logs'">
            <div
                id="query-logs"
                hx-get="/ui/logs"
                hx-trigger="load, every 10s"
            >
                <!-- Query logs will be loaded here -->
            </div>
        </div>
    </div>
</div>

<!-- Modal for forms -->
<div id="modal-content" class="hidden"></div>
{% endblock %}
```

**Dataset Form (Modal)**:
```html
<!-- app/ui/templates/dataset_form.html -->
<div class="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center">
    <div class="bg-white rounded-lg p-6 max-w-2xl w-full">
        <h2 class="text-2xl font-bold mb-4">Add New Dataset</h2>

        <form
            hx-post="/api/datasets"
            hx-target="#dataset-list"
            hx-swap="outerHTML"
        >
            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700">Dataset Name</label>
                    <input
                        type="text"
                        name="name"
                        required
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    >
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700">Connection String</label>
                    <input
                        type="text"
                        name="connection_string"
                        required
                        placeholder="postgresql://user:pass@host:port/dbname"
                        class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    >
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-700">Data Source</label>
                    <select name="data_source" class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                        <option value="fabric">Microsoft Fabric</option>
                        <option value="postgres">PostgreSQL</option>
                        <option value="custom">Custom</option>
                    </select>
                </div>

                <div class="flex justify-end space-x-3">
                    <button
                        type="button"
                        onclick="document.getElementById('modal-content').classList.add('hidden')"
                        class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                    >
                        Analyze Dataset
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>
```

---

## Phase 4: Parallel Query Execution + Optimization

**Timeline**: Week 7-8 (2 weeks)
**Goal**: Handle complex multi-query scenarios efficiently

### 4.1 Parallel Query Architecture

```python
# app/services/query_executor.py
import asyncio
import asyncpg
from typing import List, Dict, Any
from app.core.security import ConnectionStringEncryption
from app.models.dataset import Dataset

class ParallelQueryExecutor:
    def __init__(self):
        self.encryptor = ConnectionStringEncryption()
        self.connection_pools = {}  # Cache connection pools

    async def get_pool(self, dataset: Dataset) -> asyncpg.Pool:
        """Get or create connection pool for a dataset"""
        if dataset.id not in self.connection_pools:
            conn_string = self.encryptor.decrypt(dataset.connection_string_encrypted)
            pool = await asyncpg.create_pool(
                conn_string,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            self.connection_pools[dataset.id] = pool
        return self.connection_pools[dataset.id]

    async def execute_parallel(
        self,
        queries: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple queries in parallel

        Args:
            queries: List of query dicts with 'dataset_id', 'sql', 'query_type'
            max_concurrent: Maximum concurrent queries (default 5)

        Returns:
            List of results in same order as queries
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single(query_def: Dict) -> Dict[str, Any]:
            async with semaphore:
                return await self._execute_query(query_def)

        # Execute all queries concurrently
        tasks = [execute_single(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'query_index': i
                })
            else:
                processed_results.append(result)

        return processed_results

    async def _execute_query(self, query_def: Dict) -> Dict[str, Any]:
        """Execute a single query"""
        from app.core.database import get_db

        db = next(get_db())
        dataset = db.query(Dataset).filter(Dataset.id == query_def['dataset_id']).first()

        if not dataset or dataset.status != 'approved':
            return {'success': False, 'error': 'Dataset not available'}

        pool = await self.get_pool(dataset)

        async with pool.acquire() as conn:
            start_time = asyncio.get_event_loop().time()

            try:
                # Execute query
                rows = await conn.fetch(query_def['sql'])

                # Convert to dict
                results = [dict(row) for row in rows]

                # Apply weighting if needed
                if query_def.get('apply_weights', False) and dataset.has_weight_column:
                    results = self._apply_weights(results, dataset.weight_column_name)

                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000

                return {
                    'success': True,
                    'data': results,
                    'row_count': len(results),
                    'execution_time_ms': round(execution_time, 2),
                    'dataset_id': dataset.id,
                    'dataset_name': dataset.name
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'dataset_id': dataset.id
                }

    def _apply_weights(self, results: List[Dict], weight_col: str) -> List[Dict]:
        """Apply weighting to results"""
        # This is a simplified version
        # In production, use pandas/polars for complex aggregations
        import pandas as pd

        df = pd.DataFrame(results)

        # Weight numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if col != weight_col:
                df[f'{col}_weighted'] = df[col] * df[weight_col]

        return df.to_dict('records')
```

### 4.2 Progressive Context Loading

```python
# app/services/context_service.py
from typing import Dict, List, Any
from app.models.dataset import Dataset
from app.core.redis_client import redis_client
import json
import tiktoken

class ContextService:
    def __init__(self):
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.max_tokens = {
            'level_0': 500,   # Global context
            'level_1': 2000,  # Dataset summaries
            'level_2': 5000,  # Table details
            'level_3': 10000  # Full schema + samples
        }

    def get_context_level_0(self) -> str:
        """
        Global context - always included

        Returns: Markdown string with business rules
        """
        return """# MCP Analytics Server - Global Context

## Data Source
- Sample representative population from smartphones/CTV
- Collected consentfully using proprietary tech
- Panel data with weighting methodology

## Weighting Rules (CRITICAL)
- Each user carries a weight (e.g., 0.456 = represents 456 individuals)
- Cell = age/gender/NCCS/townclass/state combination
- **ALWAYS report at weighted level (weigh users, NOT events)**
- Only weigh users, not individual events

## Output Rules
- Maximum 5 raw-level rows in output
- For larger datasets, aggregate or provide summaries
- Prefer persona-level aggregations (e.g., "avg for Female 25-34")

## NCCS Merging
- Merge A and A1 → A
- Merge C, D, E → C/D/E

## Data Types
- Event-level: Individual user events (large, granular)
- Aggregated: Pre-processed summaries (smaller, faster)

## Available Tools
- `list_datasets()` - Get all active datasets
- `describe_dataset(id)` - Get detailed schema
- `execute_query(dataset_id, sql)` - Run SQL query
- `execute_multi_query(queries[])` - Run parallel queries
"""

    def get_context_level_1(self, db) -> str:
        """
        Level 1: Dataset summaries

        Returns: Markdown table of active datasets
        """
        datasets = db.query(Dataset).filter(Dataset.status == 'approved').all()

        if not datasets:
            return "No datasets available."

        md = "## Available Datasets\n\n"
        md += "| ID | Name | Description | Date Range | Type | Use Cases |\n"
        md += "|---|---|---|---|---|---|\n"

        for ds in datasets:
            date_range = f"{ds.date_range_start} to {ds.date_range_end}" if ds.date_range_start else "Unknown"
            use_cases = ", ".join(ds.use_cases[:2]) if ds.use_cases else "General"
            md += f"| {ds.id} | {ds.name} | {ds.description} | {date_range} | {ds.data_category} | {use_cases} |\n"

        return md

    def get_context_level_2(self, dataset_id: int, db) -> str:
        """
        Level 2: Table schemas for specific dataset

        Returns: Markdown with table names and column lists
        """
        from app.models.dataset import DatasetSchema

        schemas = db.query(DatasetSchema).filter(DatasetSchema.dataset_id == dataset_id).all()

        md = f"## Dataset {dataset_id} - Schema Details\n\n"

        for schema in schemas:
            md += f"### Table: {schema.table_name}\n"
            md += f"Rows: ~{schema.row_count:,}\n\n"
            md += "| Column | Type | Description |\n"
            md += "|---|---|---|\n"

            for col in schema.columns:
                desc = col.get('description', '')
                md += f"| {col['name']} | {col['type']} | {desc} |\n"

            md += "\n"

        return md

    def get_context_level_3(self, dataset_id: int, table_name: str, db) -> str:
        """
        Level 3: Full schema + sample data

        Returns: Markdown with column stats and sample rows
        """
        from app.models.dataset import DatasetSchema

        schema = db.query(DatasetSchema).filter(
            DatasetSchema.dataset_id == dataset_id,
            DatasetSchema.table_name == table_name
        ).first()

        if not schema:
            return "Table not found"

        md = f"## {table_name} - Full Details\n\n"
        md += f"**Row Count**: {schema.row_count:,}\n\n"

        # Column details with stats
        md += "### Columns\n\n"
        for col in schema.columns:
            md += f"- **{col['name']}** ({col['type']})\n"
            if col['stats'].get('null_count'):
                md += f"  - Nulls: {col['stats']['null_count']}\n"
            if col['stats'].get('distinct_count'):
                md += f"  - Unique values: {col['stats']['distinct_count']}\n"
            if col['stats'].get('min_date'):
                md += f"  - Range: {col['stats']['min_date']} to {col['stats']['max_date']}\n"

        # Sample data
        md += "\n### Sample Data (first 5 rows)\n\n"
        md += "```json\n"
        md += json.dumps(schema.sample_data[:5], indent=2, default=str)
        md += "\n```\n"

        return md

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def build_progressive_context(
        self,
        required_level: int,
        dataset_id: int = None,
        table_name: str = None,
        db = None
    ) -> str:
        """
        Build context progressively based on required level

        Args:
            required_level: 0, 1, 2, or 3
            dataset_id: Required for levels 2+
            table_name: Required for level 3
            db: Database session

        Returns:
            Markdown context string
        """
        context_parts = []

        # Level 0: Always include
        context_parts.append(self.get_context_level_0())

        # Level 1: Dataset summaries
        if required_level >= 1:
            context_parts.append(self.get_context_level_1(db))

        # Level 2: Specific dataset schema
        if required_level >= 2 and dataset_id:
            context_parts.append(self.get_context_level_2(dataset_id, db))

        # Level 3: Full table details
        if required_level >= 3 and dataset_id and table_name:
            context_parts.append(self.get_context_level_3(dataset_id, table_name, db))

        full_context = "\n\n---\n\n".join(context_parts)

        # Check token limit
        token_count = self.count_tokens(full_context)
        max_allowed = self.max_tokens.get(f'level_{required_level}', 10000)

        if token_count > max_allowed:
            # Truncate or summarize
            # For now, just return a warning
            full_context += f"\n\n**Warning**: Context exceeds token limit ({token_count}/{max_allowed})"

        return full_context
```

### 4.3 Updated MCP Server with Dynamic Tools

```python
# app/mcp/server.py
from fastmcp import FastMCP
from typing import List, Dict, Any
import json
from app.core.database import get_db
from app.models.dataset import Dataset
from app.services.query_executor import ParallelQueryExecutor
from app.services.context_service import ContextService
from app.core.redis_client import redis_client

mcp = FastMCP(name="multi-dataset-analytics-server")

# Global instances
query_executor = ParallelQueryExecutor()
context_service = ContextService()

# Subscribe to Redis for hot-reload
def reload_datasets():
    """Reload datasets when notified"""
    # This will be called when new datasets are approved
    pass

# Redis subscriber (runs in background)
pubsub = redis_client.pubsub()
pubsub.subscribe('channel:dataset:activated')

@mcp.tool()
async def list_datasets() -> str:
    """
    List all active datasets with descriptions

    Returns:
        Markdown table of available datasets
    """
    db = next(get_db())
    context = context_service.get_context_level_1(db)
    return context

@mcp.tool()
async def describe_dataset(dataset_id: int) -> str:
    """
    Get detailed schema for a specific dataset

    Args:
        dataset_id: ID of the dataset to describe

    Returns:
        Markdown with table schemas and column details
    """
    db = next(get_db())
    context = context_service.get_context_level_2(dataset_id, db)
    return context

@mcp.tool()
async def execute_query(
    dataset_id: int,
    sql: str,
    apply_weights: bool = True,
    max_rows: int = 1000
) -> str:
    """
    Execute a SQL query on a specific dataset

    Args:
        dataset_id: ID of the dataset to query
        sql: SQL SELECT query
        apply_weights: Whether to apply weight calculations (default True)
        max_rows: Maximum rows to return (default 1000)

    Returns:
        Markdown formatted results
    """
    # Validate query
    if not sql.strip().upper().startswith('SELECT'):
        return "Error: Only SELECT queries allowed"

    # Add LIMIT if not present
    if 'LIMIT' not in sql.upper():
        sql = f"{sql.rstrip(';')} LIMIT {max_rows}"

    # Execute
    result = await query_executor._execute_query({
        'dataset_id': dataset_id,
        'sql': sql,
        'apply_weights': apply_weights
    })

    if not result['success']:
        return f"Error: {result['error']}"

    # Format as markdown
    return format_result_as_markdown(result)

@mcp.tool()
async def execute_multi_query(queries: List[Dict[str, Any]]) -> str:
    """
    Execute multiple queries in parallel across datasets

    Args:
        queries: List of query objects with keys:
            - dataset_id: int
            - sql: str
            - label: str (optional, for identifying results)

    Returns:
        Markdown with all results

    Example:
        queries = [
            {"dataset_id": 1, "sql": "SELECT COUNT(*) FROM users", "label": "Total Users"},
            {"dataset_id": 2, "sql": "SELECT AVG(spend) FROM transactions", "label": "Avg Spend"}
        ]
    """
    if len(queries) > 30:
        return "Error: Maximum 30 queries allowed per request"

    # Execute in parallel
    results = await query_executor.execute_parallel(queries)

    # Format all results
    md = "# Multi-Query Results\n\n"

    for i, result in enumerate(results):
        label = queries[i].get('label', f'Query {i+1}')
        md += f"## {label}\n\n"

        if result['success']:
            md += format_result_as_markdown(result)
        else:
            md += f"**Error**: {result['error']}\n"

        md += "\n---\n\n"

    return md

@mcp.tool()
async def get_global_context() -> str:
    """
    Get global context and business rules

    Returns:
        Markdown with weighting rules, output guidelines, and best practices
    """
    return context_service.get_context_level_0()

def format_result_as_markdown(result: Dict) -> str:
    """Format query result as markdown table"""
    if result['row_count'] == 0:
        return "_No results found_"

    data = result['data']

    # Check if raw data (>5 rows) - warn if needed
    if result['row_count'] > 5 and 'GROUP BY' not in result.get('sql', '').upper():
        warning = "**Note**: Showing first 5 rows only (raw data limit)\n\n"
        data = data[:5]
    else:
        warning = ""

    # Build markdown table
    md = warning
    md += f"**Rows**: {result['row_count']} | **Execution Time**: {result['execution_time_ms']}ms\n\n"

    if not data:
        return md + "_No data_"

    # Table header
    headers = list(data[0].keys())
    md += "| " + " | ".join(headers) + " |\n"
    md += "|" + "|".join(["---"] * len(headers)) + "|\n"

    # Table rows
    for row in data:
        md += "| " + " | ".join(str(row.get(h, '')) for h in headers) + " |\n"

    return md

if __name__ == "__main__":
    # Start MCP server
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

---

## Phase 5: Query Logs + Monitoring

### 5.1 Query Logging Middleware

```python
# app/middleware/logging.py
from fastapi import Request
import time
import json
from app.core.database import get_db
from app.models.query_log import QueryLog

async def log_query_middleware(request: Request, call_next):
    """Middleware to log all MCP queries"""

    # Only log MCP queries
    if not request.url.path.startswith('/mcp'):
        return await call_next(request)

    start_time = time.time()

    # Get request body
    body = await request.body()

    # Process request
    response = await call_next(request)

    # Calculate execution time
    execution_time = int((time.time() - start_time) * 1000)

    # Parse request to extract query info
    try:
        request_data = json.loads(body) if body else {}

        # Detect tool used
        tool_used = detect_client_tool(request.headers)

        # Log to database
        db = next(get_db())
        log_entry = QueryLog(
            query_text=json.dumps(request_data.get('params', {})),
            execution_time_ms=execution_time,
            tool_used=tool_used,
            user_agent=request.headers.get('user-agent', ''),
            success=response.status_code == 200
        )
        db.add(log_entry)
        db.commit()
    except:
        pass  # Don't fail request if logging fails

    return response

def detect_client_tool(headers) -> str:
    """Detect which MCP client is being used"""
    user_agent = headers.get('user-agent', '').lower()

    if 'claude' in user_agent:
        return 'claude'
    elif 'chatgpt' in user_agent or 'openai' in user_agent:
        return 'chatgpt'
    elif 'cursor' in user_agent:
        return 'cursor'
    else:
        # Check custom headers
        mcp_client = headers.get('x-mcp-client', 'unknown')
        return mcp_client
```

### 5.2 Query Logs UI

```html
<!-- app/ui/templates/query_logs.html -->
<div class="bg-white shadow rounded-lg">
    <div class="px-4 py-5 sm:p-6">
        <h3 class="text-lg font-medium text-gray-900 mb-4">Recent Queries</h3>

        <!-- Filters -->
        <div class="mb-4 flex space-x-4">
            <select
                id="tool-filter"
                hx-get="/ui/logs"
                hx-trigger="change"
                hx-include="[id='time-filter']"
                class="rounded-md border-gray-300"
            >
                <option value="">All Tools</option>
                <option value="chatgpt">ChatGPT</option>
                <option value="claude">Claude</option>
                <option value="manus">Manus</option>
                <option value="api">API</option>
            </select>

            <select
                id="time-filter"
                hx-get="/ui/logs"
                hx-trigger="change"
                hx-include="[id='tool-filter']"
                class="rounded-md border-gray-300"
            >
                <option value="1h">Last Hour</option>
                <option value="24h" selected>Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
            </select>
        </div>

        <!-- Table -->
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tool</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Query</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Datasets</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time (ms)</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for log in logs %}
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {{ log.created_at.strftime('%Y-%m-%d %H:%M:%S') }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                                {% if log.tool_used == 'chatgpt' %}bg-green-100 text-green-800
                                {% elif log.tool_used == 'claude' %}bg-blue-100 text-blue-800
                                {% else %}bg-gray-100 text-gray-800{% endif %}">
                                {{ log.tool_used }}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-sm text-gray-900 max-w-md truncate">
                            {{ log.query_text[:100] }}...
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {% if log.datasets_used %}
                                {{ log.datasets_used|length }} dataset(s)
                            {% else %}
                                -
                            {% endif %}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {{ log.execution_time_ms }}
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                            {% if log.success %}
                                <span class="text-green-600">✓</span>
                            {% else %}
                                <span class="text-red-600">✗</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
```

---

## Critical Technical Decisions

### 1. Azure Fabric → PostgreSQL: Best Approach

**Option A: Manual Export (Current)**
- ✅ Simple, works now
- ✅ Full control over data
- ❌ Manual process
- ❌ Not real-time

**Option B: Azure PostgreSQL Flexible Server**
- ✅ Native Azure integration
- ✅ Can connect directly from Fabric
- ✅ Better for GB-scale data
- ✅ Managed service
- ❌ More expensive (~$50/month for 2-4GB)
- **Recommendation**: Use this when moving to Azure

**Option C: Synapse Serverless SQL → PostgreSQL**
- ✅ Query Fabric directly
- ✅ No data movement
- ❌ Complex setup
- ❌ Different SQL dialect

**RECOMMENDATION FOR YOU:**
1. **Phase 1-3**: Continue with Render PostgreSQL (manual export)
2. **Phase 4+**: Migrate to Azure PostgreSQL Flexible Server
3. Set up automated sync from Fabric to Azure Postgres using Azure Data Factory

### 2. Response Format: Markdown vs JSON

**Token Efficiency Test:**

JSON (100 rows):
```json
{
  "results": [
    {"user_id": 123, "gender": "F", "age": 25, "spend": 450.50},
    ...
  ]
}
```
**Tokens**: ~2,500 (lots of repeated keys)

Markdown (100 rows):
```markdown
| user_id | gender | age | spend |
|---------|--------|-----|-------|
| 123     | F      | 25  | 450.50|
...
```
**Tokens**: ~1,200 (50% reduction!)

**DECISION**: Use Markdown for all MCP responses

### 3. Hot-Reload: Redis Pub/Sub Implementation

```python
# app/mcp/server.py - Add hot-reload listener
import asyncio
from app.core.redis_client import redis_client

async def listen_for_dataset_changes():
    """Background task to listen for dataset activations"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('channel:dataset:activated')

    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            print(f"New dataset activated: {data['name']}")
            # Reload dataset cache
            await reload_dataset_cache()

# Start listener when server starts
@mcp.on_startup
async def startup():
    asyncio.create_task(listen_for_dataset_changes())
```

---

## Implementation Checklist

### Phase 2: Multi-Dataset + LLM Metadata
- [ ] Set up metadata PostgreSQL database
- [ ] Implement database models (Dataset, DatasetSchema, LLMMetadata)
- [ ] Create Alembic migrations
- [ ] Implement ConnectionStringEncryption
- [ ] Build SchemaProfiler service
- [ ] Build LLMMetadataService
- [ ] Set up Celery worker
- [ ] Implement background tasks (profiling, LLM generation)
- [ ] Create Dataset API endpoints
- [ ] Set up Redis for pub/sub
- [ ] Test hot-reload mechanism
- [ ] Deploy to Render (add worker service)

### Phase 3: UI Dashboard
- [ ] Set up Jinja2 templates
- [ ] Create base.html layout
- [ ] Build dashboard with tabs
- [ ] Implement dataset list view
- [ ] Build dataset creation form
- [ ] Add HTMX interactions
- [ ] Style with Tailwind CSS
- [ ] Test form submission flow
- [ ] Test metadata review/edit flow
- [ ] Deploy UI to Render

### Phase 4: Parallel Execution
- [ ] Implement ParallelQueryExecutor
- [ ] Add connection pooling (asyncpg)
- [ ] Build ContextService for progressive loading
- [ ] Update MCP tools with dynamic dataset support
- [ ] Implement execute_multi_query tool
- [ ] Add weighting logic
- [ ] Test parallel query performance
- [ ] Optimize for 30 concurrent queries
- [ ] Add result caching

### Phase 5: Query Logs
- [ ] Create QueryLog model
- [ ] Implement logging middleware
- [ ] Build query logs UI
- [ ] Add filters (tool, time range)
- [ ] Create dashboard charts (optional)
- [ ] Set up log retention policy
- [ ] Test with different MCP clients

---

## Next Steps

1. **Review this plan** with your team
2. **Set up development environment** (see next section)
3. **Initialize metadata database**
4. **Start Phase 2 implementation**

Would you like me to create:
1. Detailed setup instructions for local development?
2. Updated requirements.txt with all dependencies?
3. Docker Compose for local testing?
4. Render deployment configuration for multi-service setup?
