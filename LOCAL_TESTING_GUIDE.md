# Local Testing Guide - MCP Analytics Server

## 🎯 Current Setup

**Server Status:** ✅ Running locally on port 8000

**Public URL:** https://8000-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/mcp

**Dataset:** digital_insights (839,077 records)

## 🧪 Core Functions Test Results

All core functions have been tested and are working:

- ✅ Database Connection: PASS
- ✅ Dataset Connection: PASS (839,077 records)
- ✅ Schema Query: PASS (5 tables found)
- ✅ Weighted Query: PASS (weights column working correctly)
- ✅ Metadata Table: PASS (metadata_text column exists)

## 🔗 How to Test with ChatGPT

### Option 1: ChatGPT Desktop (Recommended)

1. Open ChatGPT Desktop
2. Go to **Settings → Integrations → MCP Servers**
3. Click **"Add Server"**
4. Configure:
   - **Name:** MCP Analytics (Local Test)
   - **URL:** `https://8000-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/mcp`
   - **Transport:** HTTP (Server-Sent Events)
5. Click **"Save"**
6. Test the connection

### Option 2: Claude Desktop

1. Open Claude Desktop
2. Go to **Settings → Developer → MCP Servers**
3. Add configuration:
```json
{
  "mcp-analytics-local": {
    "url": "https://8000-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/mcp",
    "transport": "sse"
  }
}
```
4. Restart Claude Desktop
5. Test the connection

## 🛠️ Available MCP Tools to Test

### 1. list_available_datasets()
```
Test: "List all available datasets"
Expected: Should return 1 dataset (digital_insights)
```

### 2. get_dataset_schema(dataset_id=1)
```
Test: "Show me the schema for dataset ID 1"
Expected: Should return table structure with columns and types
```

### 3. get_context(level=0)
```
Test: "Get context level 0"
Expected: Should return basic overview (minimal tokens)
```

### 4. get_context(level=2, dataset_id=1)
```
Test: "Get context level 2 for dataset 1"
Expected: Should return schema + metadata + weighting instructions
```

### 5. get_dataset_sample(dataset_id=1, table_name='digital_insights', limit=5)
```
Test: "Show me 5 sample rows from digital_insights"
Expected: Should return 5 rows of data
```

### 6. query_dataset(dataset_id=1, query='SELECT COUNT(*) as total FROM digital_insights')
```
Test: "Count total records in digital_insights"
Expected: Should return 839,077
```

### 7. query_dataset with weighting
```
Test: "Show gender distribution with weights from digital_insights"
Expected: Should return weighted counts using SUM(weights)
```

### 8. execute_multi_query()
```
Test: "Run multiple queries: 1) total count, 2) gender distribution"
Expected: Should execute both queries in parallel and return combined results
```

## ✅ What to Verify

### 1. Basic Connectivity
- [ ] MCP server responds to tool calls
- [ ] No connection errors
- [ ] Tools are discoverable by ChatGPT/Claude

### 2. Data Accuracy
- [ ] Total count is 839,077
- [ ] Gender distribution shows correct weighted counts
- [ ] Sample data looks reasonable

### 3. Weighting Functionality
- [ ] Queries with `apply_weights=True` use SUM(weights) not COUNT(*)
- [ ] Weighting instructions are included in responses
- [ ] NCCS merging works (if applicable)

### 4. Performance
- [ ] Queries execute within reasonable time (<5 seconds)
- [ ] Parallel queries work correctly
- [ ] No timeout errors

### 5. Token Efficiency
- [ ] Responses are in Markdown format (not JSON)
- [ ] Progressive context loading works (level 0 is minimal, level 3 is full)
- [ ] 5-row limit is enforced for raw data queries

## 🐛 Known Issues

1. **MCP Protocol Requirement:** The endpoint requires proper MCP client headers. Direct HTTP testing will fail - you MUST use ChatGPT or Claude Desktop.

2. **First Request Delay:** The first request may take 2-3 seconds as the server initializes connections.

3. **Table Name:** The table is called `digital_insights`, not `respondents`. Make sure queries use the correct table name.

4. **Weight Column:** The weight column is called `weights` (plural), not `weight` (singular).

## 📊 Sample Test Queries

### Test 1: Simple Count
```sql
SELECT COUNT(*) as total FROM digital_insights
```
Expected: 839,077

### Test 2: Gender Distribution (Unweighted)
```sql
SELECT gender, COUNT(*) as count 
FROM digital_insights 
GROUP BY gender
```
Expected: Female: 105,976 | Male: 733,101

### Test 3: Gender Distribution (Weighted)
```sql
SELECT gender, COUNT(*) as count, SUM(weights) as weighted_count
FROM digital_insights 
GROUP BY gender
```
Expected: Female: ~1,993,406 | Male: ~3,289,362

### Test 4: Age Distribution
```sql
SELECT age, COUNT(*) as count
FROM digital_insights
GROUP BY age
ORDER BY age
LIMIT 10
```

## 🔄 Server Management

### Check Server Status
```bash
ps aux | grep "python3.11 server.py"
```

### View Server Logs
```bash
tail -f /home/ubuntu/new-mcp-server/server.log
```

### Restart Server (if needed)
```bash
# Kill existing server
lsof -ti:8000 | xargs -r kill -9

# Start new server
cd /home/ubuntu/new-mcp-server
nohup python3.11 server.py > server.log 2>&1 &
```

## 📝 Testing Checklist

Before deploying to Render, verify:

- [ ] All 6 MCP tools work correctly
- [ ] Weighting calculations are accurate
- [ ] Parallel queries execute successfully
- [ ] No errors in server logs
- [ ] Token efficiency is working (Markdown responses)
- [ ] Progressive context loading works
- [ ] 5-row limit is enforced

## 🎉 Next Steps

Once you're satisfied with local testing:

1. ✅ Confirm all tests passed
2. 📦 Deploy to Render using the Blueprint
3. 🔧 Set environment variables on Render
4. 🧪 Test the production deployment
5. 🤖 Generate AI metadata for the dataset
6. 🔗 Connect ChatGPT to the production endpoint

---

**Questions or Issues?**

Check the server logs or run the core functions test again:
```bash
cd /home/ubuntu/new-mcp-server
python3.11 test_core_functions.py
```

