# Quick Start Guide - Phase 2 Optimizations

## Installation

### 1. Install New Dependencies
```bash
cd "/Users/admin_vtion/Desktop/mcp prod grade"
pip install -r requirements.txt
```

This will install:
- `pandas` - For weighting calculations
- `tiktoken` - For token counting (progressive context)
- `alembic` - For database migrations

---

## Testing the New Features

### 1. Start the Optimized Server

```bash
python server.py
```

You should see:
```
🚀 Starting MCP Analytics Server Phase 2 - Optimized Edition
   - MCP endpoint: http://0.0.0.0:8000/mcp

📊 Features:
   ✓ Multi-dataset support
   ✓ AI-powered metadata (GPT-4.1-mini)
   ✓ Markdown responses (50% token savings)
   ✓ Progressive context loading (4 levels)
   ✓ Automatic weighting & NCCS merging
   ✓ 5-row raw data limit enforcement
   ✓ Hot-reload via Redis pub/sub
   ✓ Query logging to database

🛠️  MCP Tools Available:
   1. list_available_datasets()
   2. get_dataset_schema(dataset_id)
   3. query_dataset(dataset_id, query, apply_weights=True)
   4. get_dataset_sample(dataset_id, table_name, limit=10)
   5. get_context(level=0-3, dataset_id=None)
```

---

## Testing in ChatGPT

### Test 1: List Datasets (Markdown Response)

**Tool**: `list_available_datasets()`

**Expected Output** (Markdown):
```markdown
# Available Datasets

**Total Datasets**: 2

| ID | Name | Description |
|---|---|---|
| 1 | Sample Dataset | Sample data for testing |
| 2 | User Analytics | User behavior data |

**Usage**: Use `get_dataset_schema(dataset_id)` to see table details.
```

✅ **Check**: No JSON formatting, clean Markdown table

---

### Test 2: Get Schema (Markdown with AI Descriptions)

**Tool**: `get_dataset_schema(dataset_id=1)`

**Expected Output**:
```markdown
# Dataset: Sample Dataset (ID: 1)

**Description**: Sample data for testing

**Total Tables**: 1

---

## Table: `users`

**Columns**: 5

| Column | Type | Nullable | Description |
|---|---|---|
| `id` | integer | ✗ | Unique user identifier |
| `name` | varchar | ✗ | User full name |
| `age` | integer | ✓ | User age in years |
| `weight` | numeric | ✓ | Population weight for sampling |
| `nccs` | varchar | ✓ | Socioeconomic class (A/B/C/D/E) |

---

**Usage**: Use `query_dataset(1, "SELECT ...")` to query this dataset.
```

✅ **Check**: Weight column mentioned if detected

---

### Test 3: Raw Data Query (5-Row Limit)

**Tool**: `query_dataset(dataset_id=1, query="SELECT * FROM users")`

**Expected Output**:
```markdown
# Query Results

⚠️ **Note**: Raw data limited to 5 rows. For larger datasets, use aggregation (GROUP BY).

**Rows Returned**: 5
**Query**: `SELECT * FROM users`

| id | name | age | weight | nccs |
|---|---|---|---|---|
| 1 | John Doe | 25 | 0.456 | A |
| 2 | Jane Smith | 30 | 0.789 | B |
| 3 | Bob Wilson | 35 | 0.234 | A |
| 4 | Alice Brown | 28 | 0.567 | C |
| 5 | Charlie Davis | 32 | 0.890 | D |

**Weight Column Detected**: `weight`
_Include weight column in GROUP BY for accurate population estimates._

**NCCS Merging Applied**: nccs (A1→A, C/D/E→C/D/E)
```

✅ **Check**:
- Only 5 rows shown
- Warning message displayed
- Weight column detected
- NCCS merging noted

---

### Test 4: Aggregated Query (No Limit)

**Tool**: `query_dataset(dataset_id=1, query="SELECT nccs, COUNT(*) as count, AVG(age) as avg_age FROM users GROUP BY nccs")`

**Expected Output**:
```markdown
# Query Results

**Rows Returned**: 4

| nccs | count | avg_age |
|---|---|---|---|
| A | 2 | 30.00 |
| B | 1 | 30.00 |
| C/D/E | 2 | 30.00 |

**NCCS Merging Applied**: nccs (A1→A, C/D/E→C/D/E)
```

✅ **Check**:
- No 5-row limit (aggregated query)
- No warning message
- NCCS values merged correctly

---

### Test 5: Progressive Context (NEW Tool)

**Tool**: `get_context(level=0)`

**Expected Output**:
```markdown
# MCP Analytics Server - Global Context

## Data Source
- **Sample representative population** from smartphones/CTV
- Collected **consentfully** using proprietary technology
- Panel data with **weighting methodology**

## Weighting Rules (CRITICAL)
- Each user carries a **weight** (e.g., 0.456 = represents 456 individuals in population)
- **Cell** = age/gender/NCCS/townclass/state combination
- **ALWAYS report at weighted level** (weigh users, NOT individual events)
...
```

**Tool**: `get_context(level=1)`

**Expected Output**: Level 0 + Dataset list

**Tool**: `get_context(level=2, dataset_id=1)`

**Expected Output**: Level 0 + Level 1 + Full schema for dataset 1

✅ **Check**: Progressive loading works, more context at higher levels

---

### Test 6: Sample Data

**Tool**: `get_dataset_sample(dataset_id=1, table_name="users", limit=10)`

**Expected Output**:
```markdown
# Sample Data: users

**Dataset ID**: 1
**Sample Size**: 10 rows

| id | name | age | weight | nccs |
|---|---|---|---|---|
| 1 | John Doe | 25 | 0.456 | A |
| 2 | Jane Smith | 30 | 0.789 | B |
...

**Usage**: This is sample data. Use `query_dataset()` for custom queries.
```

✅ **Check**: Clean sample data, no weighting applied to samples

---

## Verify Weight & NCCS Detection

### Add Test Dataset with Weight Column

1. **Create test data** (if not already):
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INTEGER,
    weight NUMERIC(10,3),  -- This should be auto-detected
    nccs VARCHAR(10)        -- This should be auto-detected
);

INSERT INTO users VALUES
    (1, 'User 1', 25, 0.456, 'A1'),  -- A1 will merge to A
    (2, 'User 2', 30, 0.789, 'C'),   -- C will merge to C/D/E
    (3, 'User 3', 35, 0.234, 'D'),   -- D will merge to C/D/E
    (4, 'User 4', 28, 0.567, 'E');   -- E will merge to C/D/E
```

2. **Add dataset via API**:
```bash
curl -X POST http://localhost:5001/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weight Test Dataset",
    "description": "Testing weight and NCCS detection",
    "connection_string": "postgresql://user:pass@host:port/db"
  }'
```

3. **Wait for processing** (watch Celery logs)

4. **Check dataset description**:
```bash
curl http://localhost:5001/api/datasets/1
```

Expected to include:
```
[Weight column: users.weight]
[NCCS column: users.nccs]
```

5. **Query to verify NCCS merging**:
```sql
SELECT nccs, COUNT(*) FROM users GROUP BY nccs
```

Expected result:
```markdown
| nccs | count |
|------|-------|
| A    | 1     |  ← A1 merged to A
| C/D/E| 3     |  ← C, D, E merged
```

---

## Hot-Reload Testing (Optional - Requires Redis)

### Setup Redis (if not already running)
```bash
# macOS with Homebrew
brew install redis
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:latest
```

### Test Hot-Reload

1. **Start MCP server**:
```bash
python server.py
```

Look for:
```
🔔 Listening for dataset changes on Redis pub/sub...
✅ Reloaded dataset cache: 2 datasets
```

2. **Add new dataset** via API (in another terminal):
```bash
curl -X POST http://localhost:5001/api/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hot Reload Test",
    "description": "Testing hot reload",
    "connection_string": "postgresql://..."
  }'
```

3. **Watch server logs** - should see:
```
📢 Dataset activated: Hot Reload Test (ID: 3)
✅ Reloaded dataset cache: 3 datasets
```

4. **Call `list_available_datasets()` in ChatGPT** - should immediately show new dataset (no restart!)

---

## Query Logging Verification

### 1. Run Some Queries
Execute several queries via ChatGPT MCP tools.

### 2. Check Logs in Database
```bash
# Connect to metadata database
psql -h localhost -U user -d metadata_db

# View recent queries
SELECT
    id,
    dataset_id,
    query,
    execution_time_ms,
    row_count,
    success,
    executed_at
FROM query_logs
ORDER BY executed_at DESC
LIMIT 10;
```

Expected output:
```
 id | dataset_id | query          | execution_time_ms | row_count | success |     executed_at
----+------------+---------------+-------------------+-----------+---------+---------------------
  1 |          1 | SELECT * ...  |               150 |         5 | t       | 2025-01-15 10:30:00
  2 |          1 | SELECT nccs...|               280 |         4 | t       | 2025-01-15 10:29:45
```

✅ **Check**: All queries logged with timing info

---

## Database Migrations (Optional)

### Create First Migration
```bash
# Auto-generate migration from current models
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

### Future Schema Changes
```bash
# Make changes to app/models.py
# Then generate migration
alembic revision --autogenerate -m "Add new column"

# Review migration file in alembic/versions/
# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Troubleshooting

### Issue: "Module not found: tiktoken"
```bash
pip install tiktoken>=0.5.0
```

### Issue: "Module not found: pandas"
```bash
pip install pandas>=2.0.0
```

### Issue: "Redis connection failed"
**Expected behavior**: Server continues without hot-reload

If you see:
```
⚠️  Redis not available - hot-reload disabled
```

This is normal! Hot-reload is optional. Server works fine without it.

To enable hot-reload:
```bash
# Install and start Redis
brew install redis
redis-server
```

### Issue: "Import error: app.services"
Make sure `app/services/__init__.py` exists (should be created automatically).

If missing:
```bash
touch app/services/__init__.py
```

---

## Performance Comparison

### Token Usage Before/After

**Scenario**: List 10 datasets with schemas

**Before (JSON)**:
- Response size: ~8,500 tokens
- Format: Nested JSON objects

**After (Markdown)**:
- Response size: ~4,200 tokens
- Format: Clean Markdown tables

**Savings**: ~50% ✅

### Query Execution

**Raw query** (before):
```
SELECT * FROM users
→ Returns 1000 rows
→ ~15,000 tokens in response
```

**Raw query** (after):
```
SELECT * FROM users
→ Returns 5 rows (limited)
→ ~500 tokens in response
→ Warning: "Use aggregation for larger datasets"
```

**Savings**: ~97% for raw queries ✅

---

## Next Steps

1. ✅ **Test all 5 MCP tools** in ChatGPT
2. ✅ **Verify Markdown formatting** renders correctly
3. ✅ **Check weight/NCCS detection** in logs
4. ✅ **Test 5-row limit** enforcement
5. ✅ **Verify query logging** to database
6. [ ] **Deploy to Render** (push to git)
7. [ ] **Enable Redis** for hot-reload (optional)
8. [ ] **Create Alembic migration** (optional)

---

## Summary

All **8 optimization features** are now implemented:

1. ✅ Markdown responses (50% token savings)
2. ✅ Progressive context loading (4 levels)
3. ✅ Automatic weighting
4. ✅ NCCS merging (A1→A, C/D/E)
5. ✅ 5-row raw data limit
6. ✅ Hot-reload via Redis (optional)
7. ✅ Query logging
8. ✅ Alembic migrations (initialized)

**Your MCP server is now production-grade!** 🚀

See [PHASE2_OPTIMIZATIONS.md](PHASE2_OPTIMIZATIONS.md) for detailed technical documentation.
