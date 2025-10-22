# Migration Guide: execute_multi_query() → Multiple query_dataset() Calls

## 🚨 Important Change

`execute_multi_query()` has been **deprecated** and will be removed in a future version.

## Why the Change?

The old `execute_multi_query()` approach had several issues:

1. **Blocking behavior**: Waits for ALL queries to complete before returning
2. **Slow queries block fast ones**: A 30-second query blocks a 1-second query
3. **Single large response**: All results returned in one chunky response
4. **Poor error handling**: One failed query can affect the entire batch
5. **No streaming**: User waits for everything to finish

## New Approach: True Parallel Execution

Instead of calling `execute_multi_query()` once, call `query_dataset()` multiple times.

### ❌ OLD WAY (Deprecated)

```python
execute_multi_query(queries=[
    {
        "dataset_id": 1,
        "query": "SELECT gender, SUM(weights) as total FROM digital_insights GROUP BY gender",
        "label": "Gender Distribution"
    },
    {
        "dataset_id": 1,
        "query": "SELECT age_bucket, SUM(weights) as total FROM digital_insights GROUP BY age_bucket",
        "label": "Age Distribution"
    },
    {
        "dataset_id": 1,
        "query": "SELECT app_name, SUM(weights) as total FROM digital_insights GROUP BY app_name LIMIT 10",
        "label": "Top Apps"
    }
])
```

**Problems:**
- Waits for all 3 queries to finish
- Returns one large combined response
- If query 3 takes 30 seconds, queries 1 and 2 wait too

### ✅ NEW WAY (Recommended)

```python
# Call these separately - they execute in parallel automatically!

query_dataset(
    dataset_id=1,
    query="SELECT gender, SUM(weights) as total FROM digital_insights GROUP BY gender"
)

query_dataset(
    dataset_id=1,
    query="SELECT age_bucket, SUM(weights) as total FROM digital_insights GROUP BY age_bucket"
)

query_dataset(
    dataset_id=1,
    query="SELECT app_name, SUM(weights) as total FROM digital_insights GROUP BY app_name LIMIT 10"
)
```

**Benefits:**
- ✅ Each query returns **immediately** when done
- ✅ Fast queries don't wait for slow ones
- ✅ **Streaming results** - see data as it arrives
- ✅ Failed queries don't block successful ones
- ✅ Better user experience
- ✅ Natural parallelism handled by LLM client (ChatGPT/Claude)

## How It Works

When you call `query_dataset()` multiple times:

1. **LLM client handles parallelism**: ChatGPT/Claude automatically executes multiple tool calls concurrently
2. **Independent execution**: Each query runs in its own thread/connection
3. **Immediate responses**: Results stream back as soon as each query completes
4. **No blocking**: Fast queries (1s) return before slow queries (30s)

### Example Timeline

**OLD WAY (execute_multi_query):**
```
Time: 0s ─────────────────────────────────────────────────────────> 30s
      [Query 1: 1s] [Query 2: 5s] [Query 3: 30s] → ALL RETURN AT 36s
```

**NEW WAY (multiple query_dataset):**
```
Time: 0s ─────────────────────────────────────────────────────────> 30s
      [Query 1: 1s] ✅ RETURNS AT 1s
      [Query 2: 5s] ─────────> ✅ RETURNS AT 5s
      [Query 3: 30s] ──────────────────────────────────────> ✅ RETURNS AT 30s
```

## Migration Examples

### Example 1: Simple Multi-Query Analysis

**Before:**
```python
execute_multi_query(queries=[
    {"dataset_id": 1, "query": "SELECT gender, SUM(weights) FROM digital_insights GROUP BY gender", "label": "Gender"},
    {"dataset_id": 1, "query": "SELECT nccs_class, SUM(weights) FROM digital_insights GROUP BY nccs_class", "label": "NCCS"}
])
```

**After:**
```python
query_dataset(1, "SELECT gender, SUM(weights) FROM digital_insights GROUP BY gender")
query_dataset(1, "SELECT nccs_class, SUM(weights) FROM digital_insights GROUP BY nccs_class")
```

### Example 2: Cross-Dataset Analysis

**Before:**
```python
execute_multi_query(queries=[
    {"dataset_id": 1, "query": "SELECT COUNT(*) FROM digital_insights", "label": "Dataset 1 Count"},
    {"dataset_id": 2, "query": "SELECT COUNT(*) FROM users", "label": "Dataset 2 Count"}
])
```

**After:**
```python
query_dataset(1, "SELECT COUNT(*) FROM digital_insights")
query_dataset(2, "SELECT COUNT(*) FROM users")
```

### Example 3: Complex Multi-Dimensional Analysis

**Before:**
```python
execute_multi_query(queries=[
    {"dataset_id": 1, "query": "SELECT gender, age_bucket, SUM(weights) FROM digital_insights GROUP BY gender, age_bucket"},
    {"dataset_id": 1, "query": "SELECT state_grp, app_name, SUM(weights) FROM digital_insights GROUP BY state_grp, app_name LIMIT 50"},
    {"dataset_id": 1, "query": "SELECT day_of_week, event_time_range, SUM(duration_sum) FROM digital_insights GROUP BY day_of_week, event_time_range"}
])
```

**After:**
```python
query_dataset(1, "SELECT gender, age_bucket, SUM(weights) FROM digital_insights GROUP BY gender, age_bucket")
query_dataset(1, "SELECT state_grp, app_name, SUM(weights) FROM digital_insights GROUP BY state_grp, app_name LIMIT 50")
query_dataset(1, "SELECT day_of_week, event_time_range, SUM(duration_sum) FROM digital_insights GROUP BY day_of_week, event_time_range")
```

## For LLM Prompts

When asking ChatGPT/Claude to run multiple queries, use language like:

✅ **Good prompts:**
- "Run these 3 queries in parallel and show me the results"
- "Execute these queries simultaneously"
- "Query the database for gender, age, and location distributions"

❌ **Avoid:**
- "Use execute_multi_query to run these queries" (deprecated tool)
- "Combine these queries into one call" (not needed)

## Technical Details

### Connection Pooling

Each `query_dataset()` call uses connection pooling for optimal performance:
- Min 2 connections per dataset
- Max 10 concurrent queries per dataset
- Automatic connection reuse
- 5-minute idle timeout

### Error Handling

With multiple `query_dataset()` calls:
- Failed queries return error messages independently
- Successful queries return results immediately
- No cascading failures
- Better debugging (see exactly which query failed)

### Performance Comparison

| Scenario | Old Way (execute_multi_query) | New Way (multiple query_dataset) |
|----------|-------------------------------|----------------------------------|
| 3 queries (1s, 5s, 30s) | 36s total, all return together | 1s, 5s, 30s - stream as they finish |
| 1 query fails | Entire batch may fail | Only that query fails |
| User experience | Wait for everything | See results immediately |
| Token efficiency | One large response | Smaller streaming responses |

## Backward Compatibility

`execute_multi_query()` is still available but deprecated. It will:
- Show a deprecation warning in the tool description
- Continue to work as before
- Be removed in a future major version

**Recommendation:** Migrate to multiple `query_dataset()` calls now.

## Questions?

**Q: Will calling query_dataset() multiple times be slower?**
A: No! The LLM client (ChatGPT/Claude) handles parallelism automatically. It's actually faster because results stream back immediately.

**Q: How many queries can I run in parallel?**
A: The LLM client typically handles 5-10 concurrent tool calls. Each query runs independently.

**Q: What if I need to combine results?**
A: The LLM will receive all results and can combine/analyze them in its response. You don't need to combine them manually.

**Q: Can I still use execute_multi_query()?**
A: Yes, but it's deprecated. It will be removed in a future version. Please migrate to multiple `query_dataset()` calls.

## Summary

✅ **Do this:**
```python
query_dataset(1, "SELECT ...")
query_dataset(1, "SELECT ...")
query_dataset(1, "SELECT ...")
```

❌ **Don't do this:**
```python
execute_multi_query(queries=[...])  # Deprecated
```

**Benefits:**
- 🚀 Faster results (streaming)
- ✅ Better error handling
- 📊 Cleaner responses
- 💪 More reliable
- 🎯 Better user experience

---

**Last Updated:** October 22, 2025  
**Status:** execute_multi_query() deprecated, multiple query_dataset() calls recommended

