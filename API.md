# MCP Analytics Server - API Documentation

## Base URLs

- **Local Development**: `http://localhost:8000`
- **Render Production**: `https://your-app.onrender.com`

## Authentication

**Phase 1-3**: No authentication (internal tool)
**Phase 4+**: Add Bearer token authentication if needed

---

## REST API Endpoints

### Datasets API

#### 1. Create Dataset
**POST** `/api/datasets`

Create a new dataset and trigger background profiling.

**Request Body:**
```json
{
  "name": "q1_2024_ctv_data",
  "description": "CTV viewership data for Q1 2024",
  "connection_string": "postgresql://user:pass@host:port/dbname",
  "dataset_type": "event_level",
  "data_source": "fabric",
  "created_by": "user@example.com"
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "q1_2024_ctv_data",
  "status": "profiling",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Dataset created. Profiling in progress..."
}
```

**Errors:**
- `400 Bad Request` - Invalid connection string or duplicate name
- `500 Internal Server Error` - Database connection failed

---

#### 2. List Datasets
**GET** `/api/datasets`

List all datasets with optional filters.

**Query Parameters:**
- `status` (optional): Filter by status (`draft`, `approved`, `active`, etc.)
- `skip` (default: 0): Pagination offset
- `limit` (default: 100): Max results

**Example:**
```
GET /api/datasets?status=approved&limit=50
```

**Response:** `200 OK`
```json
{
  "total": 5,
  "datasets": [
    {
      "id": 1,
      "name": "q1_2024_ctv_data",
      "description": "CTV viewership data for Q1 2024",
      "status": "approved",
      "data_category": "ctv",
      "date_range_start": "2024-01-01",
      "date_range_end": "2024-03-31",
      "estimated_row_count": 15000000,
      "has_weight_column": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_profiled_at": "2024-01-15T10:35:00Z"
    }
  ]
}
```

---

#### 3. Get Dataset Details
**GET** `/api/datasets/{dataset_id}`

Get detailed information about a specific dataset.

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "q1_2024_ctv_data",
  "description": "CTV viewership data for Q1 2024",
  "status": "approved",
  "dataset_type": "event_level",
  "data_source": "fabric",
  "data_category": "ctv",
  "date_range_start": "2024-01-01",
  "date_range_end": "2024-03-31",
  "use_cases": ["media planning", "audience analysis"],
  "has_weight_column": true,
  "weight_column_name": "weight",
  "estimated_row_count": 15000000,
  "estimated_size_mb": 1250.5,
  "created_by": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "approved_at": "2024-01-15T11:00:00Z",
  "last_profiled_at": "2024-01-15T10:35:00Z"
}
```

**Errors:**
- `404 Not Found` - Dataset doesn't exist

---

#### 4. Get Dataset Schema
**GET** `/api/datasets/{dataset_id}/schema`

Get profiled schema for all tables in the dataset.

**Response:** `200 OK`
```json
{
  "dataset_id": 1,
  "dataset_name": "q1_2024_ctv_data",
  "tables": [
    {
      "table_name": "viewership_events",
      "row_count": 15000000,
      "size_mb": 1250.5,
      "columns": [
        {
          "name": "user_id",
          "type": "bigint",
          "nullable": false,
          "description": "Unique user identifier",
          "stats": {
            "null_count": 0,
            "distinct_count": 125000
          }
        },
        {
          "name": "timestamp",
          "type": "timestamp",
          "nullable": false,
          "stats": {
            "min_date": "2024-01-01",
            "max_date": "2024-03-31"
          }
        },
        {
          "name": "weight",
          "type": "numeric",
          "nullable": false,
          "description": "User weight for population representation"
        }
      ],
      "sample_data": [
        {
          "user_id": 12345,
          "timestamp": "2024-01-01T08:30:00Z",
          "weight": 0.456
        }
      ]
    }
  ]
}
```

---

#### 5. Get Dataset Metadata
**GET** `/api/datasets/{dataset_id}/metadata`

Get LLM-generated metadata for a dataset.

**Response:** `200 OK`
```json
{
  "dataset_id": 1,
  "generated_description": "This dataset contains CTV viewership events from a representative panel of 125K users across Q1 2024. Each event represents a viewing session with weighted user representation.",
  "data_dictionary": {
    "user_id": "Unique identifier for panel users",
    "timestamp": "Event timestamp in UTC",
    "weight": "User weight for population extrapolation (cell-based)",
    "content_id": "Unique content identifier",
    "duration_seconds": "Viewing duration in seconds"
  },
  "quality_observations": [
    "Data coverage is complete for Q1 2024",
    "Weight column present and properly formatted",
    "No significant null values in key columns"
  ],
  "improvement_suggestions": [
    "Consider standardizing timestamp format to ISO 8601",
    "Add indexes on user_id and timestamp for faster queries"
  ],
  "recommended_use_cases": [
    "Media planning and reach analysis",
    "Audience segmentation",
    "Content performance tracking"
  ],
  "llm_model": "gpt-4o-mini",
  "user_edited": false,
  "user_approved": true,
  "created_at": "2024-01-15T10:40:00Z"
}
```

---

#### 6. Update Dataset Metadata
**PATCH** `/api/datasets/{dataset_id}/metadata`

Update LLM-generated metadata (user edits).

**Request Body:**
```json
{
  "generated_description": "Updated description here...",
  "data_dictionary": {
    "user_id": "Updated explanation..."
  },
  "user_notes": "Added clarification about weight calculation"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "metadata_id": 1,
  "user_edited": true,
  "updated_at": "2024-01-15T11:30:00Z"
}
```

---

#### 7. Approve Dataset
**POST** `/api/datasets/{dataset_id}/approve`

Approve a dataset and activate it for MCP queries.

**Request Body:**
```json
{
  "approved_by": "user@example.com"
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "dataset_id": 1,
  "status": "approved",
  "approved_at": "2024-01-15T11:00:00Z",
  "message": "Dataset approved and activated. MCP server updated."
}
```

**Side Effects:**
- Dataset status changes to `approved`
- Redis pub/sub notification sent
- MCP server automatically reloads available tools

---

#### 8. Delete Dataset
**DELETE** `/api/datasets/{dataset_id}`

Soft-delete a dataset (marks as deleted, doesn't remove data).

**Response:** `200 OK`
```json
{
  "success": true,
  "dataset_id": 1,
  "message": "Dataset soft-deleted successfully"
}
```

---

### Query Execution API

#### 9. Execute Query
**POST** `/api/query/execute`

Execute a SQL query on a specific dataset.

**Request Body:**
```json
{
  "dataset_id": 1,
  "sql": "SELECT gender, COUNT(DISTINCT user_id) as users FROM viewership_events GROUP BY gender",
  "apply_weights": true,
  "max_rows": 1000
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "dataset_id": 1,
  "dataset_name": "q1_2024_ctv_data",
  "row_count": 2,
  "execution_time_ms": 245,
  "columns": ["gender", "users"],
  "data": [
    {"gender": "M", "users": 65000},
    {"gender": "F", "users": 60000}
  ],
  "weights_applied": true,
  "query_log_id": 1234
}
```

**Errors:**
- `400 Bad Request` - Invalid SQL or dangerous query
- `403 Forbidden` - Dataset not approved
- `500 Internal Server Error` - Query execution failed

---

#### 10. Execute Multi-Query
**POST** `/api/query/execute-multi`

Execute multiple queries in parallel across datasets.

**Request Body:**
```json
{
  "queries": [
    {
      "dataset_id": 1,
      "sql": "SELECT COUNT(DISTINCT user_id) FROM viewership_events",
      "label": "Total CTV Users"
    },
    {
      "dataset_id": 2,
      "sql": "SELECT COUNT(DISTINCT user_id) FROM mobile_events",
      "label": "Total Mobile Users"
    }
  ],
  "max_concurrent": 5
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "total_queries": 2,
  "successful": 2,
  "failed": 0,
  "total_execution_time_ms": 450,
  "results": [
    {
      "label": "Total CTV Users",
      "success": true,
      "dataset_id": 1,
      "row_count": 1,
      "execution_time_ms": 245,
      "data": [{"count": 125000}]
    },
    {
      "label": "Total Mobile Users",
      "success": true,
      "dataset_id": 2,
      "row_count": 1,
      "execution_time_ms": 205,
      "data": [{"count": 230000}]
    }
  ]
}
```

---

### Query Logs API

#### 11. Get Query Logs
**GET** `/api/logs`

Get query execution logs with filters.

**Query Parameters:**
- `tool` (optional): Filter by tool (`chatgpt`, `claude`, `api`)
- `time_range` (optional): `1h`, `24h`, `7d`, `30d` (default: `24h`)
- `dataset_id` (optional): Filter by dataset
- `success` (optional): `true` or `false`
- `skip` (default: 0): Pagination offset
- `limit` (default: 100): Max results

**Example:**
```
GET /api/logs?tool=chatgpt&time_range=24h&limit=50
```

**Response:** `200 OK`
```json
{
  "total": 245,
  "logs": [
    {
      "id": 1234,
      "query_text": "SELECT gender, COUNT(*) FROM ...",
      "query_type": "aggregated",
      "datasets_used": [1, 2],
      "tool_used": "chatgpt",
      "execution_time_ms": 450,
      "rows_returned": 25,
      "success": true,
      "weights_applied": true,
      "created_at": "2024-01-15T14:30:00Z"
    }
  ]
}
```

---

#### 12. Get Query Log Details
**GET** `/api/logs/{log_id}`

Get detailed information about a specific query execution.

**Response:** `200 OK`
```json
{
  "id": 1234,
  "query_text": "SELECT gender, AVG(duration) FROM viewership_events GROUP BY gender",
  "query_hash": "abc123def456",
  "query_type": "aggregated",
  "datasets_used": [1],
  "primary_dataset_id": 1,
  "execution_time_ms": 450,
  "rows_returned": 2,
  "success": true,
  "tool_used": "chatgpt",
  "user_agent": "ChatGPT/1.0",
  "session_id": "session_xyz",
  "response_format": "markdown",
  "response_size_bytes": 1024,
  "weights_applied": true,
  "weight_column_used": "weight",
  "db_connection_time_ms": 50,
  "query_parsing_time_ms": 10,
  "result_formatting_time_ms": 40,
  "created_at": "2024-01-15T14:30:00Z"
}
```

---

#### 13. Get Query Analytics
**GET** `/api/logs/analytics`

Get aggregated analytics about query usage.

**Query Parameters:**
- `time_range` (optional): `24h`, `7d`, `30d` (default: `7d`)
- `group_by` (optional): `tool`, `dataset`, `hour`, `day`

**Response:** `200 OK`
```json
{
  "time_range": "7d",
  "total_queries": 1250,
  "successful_queries": 1200,
  "failed_queries": 50,
  "avg_execution_time_ms": 425,
  "p95_execution_time_ms": 1200,
  "unique_sessions": 45,
  "by_tool": {
    "chatgpt": 750,
    "claude": 400,
    "api": 100
  },
  "by_dataset": {
    "q1_2024_ctv_data": 600,
    "mobile_events_2024": 650
  },
  "daily_breakdown": [
    {
      "date": "2024-01-15",
      "queries": 180,
      "avg_time_ms": 420
    }
  ]
}
```

---

### System API

#### 14. Health Check
**GET** `/health`

Check system health and database connectivity.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T15:00:00Z",
  "services": {
    "metadata_db": "connected",
    "redis": "connected",
    "celery": "running"
  },
  "version": "2.0.0"
}
```

---

#### 15. Get System Config
**GET** `/api/config`

Get system-wide configuration.

**Response:** `200 OK`
```json
{
  "weighting_rules": {
    "merge_nccs": {
      "A": ["A", "A1"],
      "C/D/E": ["C", "D", "E"]
    },
    "always_apply": true
  },
  "query_limits": {
    "max_raw_rows": 5,
    "max_aggregated_rows": 1000,
    "max_parallel_queries": 30
  },
  "llm_config": {
    "model": "gpt-4o-mini",
    "temperature": 0.3
  }
}
```

---

## MCP Server Endpoints

### MCP Protocol Endpoint
**POST** `/mcp`

Main MCP protocol endpoint for LLM clients (ChatGPT, Claude, etc.).

**Transport**: Streamable HTTP (SSE)
**Protocol Version**: 2024-11-05

### Available MCP Tools

#### 1. `list_datasets()`

**Description**: List all active datasets with descriptions

**Parameters**: None

**Returns**: Markdown table of datasets

**Example Call:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_datasets",
    "arguments": {}
  }
}
```

**Example Response:**
```markdown
## Available Datasets

| ID | Name | Description | Date Range | Type | Use Cases |
|---|---|---|---|---|---|
| 1 | q1_2024_ctv_data | CTV viewership Q1 2024 | 2024-01-01 to 2024-03-31 | ctv | media planning, audience analysis |
```

---

#### 2. `describe_dataset(dataset_id: int)`

**Description**: Get detailed schema for a specific dataset

**Parameters:**
- `dataset_id` (integer, required): Dataset ID

**Returns**: Markdown with table schemas

---

#### 3. `execute_query(dataset_id: int, sql: str, apply_weights: bool, max_rows: int)`

**Description**: Execute SQL query on a dataset

**Parameters:**
- `dataset_id` (integer, required): Dataset ID
- `sql` (string, required): SQL SELECT query
- `apply_weights` (boolean, default: true): Apply weight calculations
- `max_rows` (integer, default: 1000): Max rows to return

**Returns**: Markdown formatted results

**Example:**
```json
{
  "name": "execute_query",
  "arguments": {
    "dataset_id": 1,
    "sql": "SELECT gender, COUNT(*) FROM viewership_events GROUP BY gender",
    "apply_weights": true
  }
}
```

---

#### 4. `execute_multi_query(queries: array)`

**Description**: Execute multiple queries in parallel

**Parameters:**
- `queries` (array, required): List of query objects

**Returns**: Markdown with all results

---

#### 5. `get_global_context()`

**Description**: Get global business rules and context

**Parameters**: None

**Returns**: Markdown with weighting rules and guidelines

---

## UI Endpoints (HTMX)

### Dashboard
**GET** `/ui/`

Main dashboard with tabs for datasets and query logs.

---

### Dataset List (Partial)
**GET** `/ui/datasets`

HTMX partial for dataset list.

---

### Dataset Form (Modal)
**GET** `/ui/datasets/new`

HTMX partial for dataset creation form.

---

### Query Logs (Partial)
**GET** `/ui/logs`

HTMX partial for query logs table.

**Query Parameters:**
- `tool` (optional): Filter by tool
- `time` (optional): Time range filter

---

## Error Responses

All API endpoints follow standard HTTP error codes:

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid SQL query: Only SELECT statements allowed",
  "code": "INVALID_QUERY"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid authentication token"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "Dataset not approved for querying"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Dataset with ID 999 not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "Database connection failed",
  "details": "Connection timeout after 30s"
}
```

---

## Rate Limiting

**Phase 1-3**: No rate limiting
**Phase 4+**: Consider implementing:
- 100 requests/minute per IP
- 1000 requests/hour per session

---

## Versioning

API versioning will be introduced in future releases:
- **Current**: No versioning (v1 implied)
- **Future**: `/api/v2/datasets`

---

## OpenAPI Specification

Full OpenAPI (Swagger) spec available at:
- **Development**: `http://localhost:8000/docs`
- **Production**: `https://your-app.onrender.com/docs`

Interactive API documentation powered by FastAPI.
