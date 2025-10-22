# Quick Reference - MCP Analytics Server Testing

## 🔗 URLs

### MCP Endpoint (for ChatGPT)
```
https://8000-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/mcp
```

### UI Dashboard
```
https://8501-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/ui/
```

### API Documentation
```
https://8501-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/docs
```

---

## 🧪 What to Test

### 1. First Call - Dataset Discovery
**Ask ChatGPT:** "What datasets are available?"

**Expected Response Should Include:**
- ✅ Dataset name: **digital_insights**
- ✅ Row count: **839,077 records**
- ✅ Table count: **1 table**
- ✅ Metadata status: **✅ (available)**
- ✅ Strategic overview of the dataset
- ✅ Next steps guidance
- ✅ Analysis guidelines for executives

### 2. Second Call - Schema Details
**Ask ChatGPT:** "Show me the schema for digital_insights"

**Expected Response Should Include:**
- ✅ All 18 columns with types
- ✅ AI-generated business descriptions for each column
- ✅ Analysis guidelines (PhD-level, executive audience)
- ✅ Best practices for strategic analysis
- ✅ Usage instructions

### 3. Third Call - Data Query
**Ask ChatGPT:** "What's the gender distribution in the data?"

**Expected Response Should Include:**
- ✅ Query results in table format
- ✅ Analysis reminder about audience
- ✅ Strategic insights (not just data)
- ✅ Actionable recommendations
- ✅ Business implications

### 4. Fourth Call - Complex Analysis
**Ask ChatGPT:** "Analyze user engagement by age group and gender. Provide recommendations for media spend allocation."

**Expected Response Should Include:**
- ✅ Multi-dimensional analysis
- ✅ Tables and/or visualization suggestions
- ✅ PhD-level insights
- ✅ Strategic recommendations for media spend
- ✅ Ecommerce strategy implications
- ✅ Actionable takeaways

---

## ✅ Success Checklist

- [ ] ChatGPT connects to MCP endpoint successfully
- [ ] First response shows rich dataset information (not just name)
- [ ] Metadata includes AI-generated column descriptions
- [ ] Responses include analysis guidelines for executives
- [ ] Query results are formatted as tables (not JSON)
- [ ] ChatGPT provides strategic insights, not just data
- [ ] Recommendations are actionable for brand managers
- [ ] Weighted queries work correctly (SUM(weights))
- [ ] No errors in server logs
- [ ] UI dashboard shows query logs

---

## 🎯 Key Improvements to Validate

### Before vs After

| Feature | Before | After (Now) |
|---------|--------|-------------|
| Dataset info | Name only | Name + 839K rows + 1 table + ✅ metadata |
| Column descriptions | None | AI-generated business context |
| Analysis guidance | None | PhD-level instructions |
| Audience context | Generic | Senior executives |
| Response format | Basic | Rich markdown with emojis |
| Strategic focus | None | Media spend + ecommerce |

---

## 🚨 What to Watch For

### Potential Issues:
1. **Connection errors**: MCP endpoint not responding
2. **Missing metadata**: Columns show "No description"
3. **Generic responses**: ChatGPT doesn't follow analysis guidelines
4. **JSON responses**: Data returned as JSON instead of tables
5. **No strategic insights**: Just data, no recommendations
6. **Weighting errors**: Queries don't use SUM(weights) correctly

### How to Debug:
```bash
# Check server logs
tail -f /home/ubuntu/new-mcp-server/server.log

# Check if server is running
ps aux | grep "python3.11 server.py"

# Test core functions
cd /home/ubuntu/new-mcp-server
python3.11 test_core_functions.py

# View query logs in UI
Open: https://8501-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/ui/logs
```

---

## 📊 Expected Workflow

```
User: "What datasets are available?"
  ↓
ChatGPT calls: list_available_datasets()
  ↓
Response: Rich dataset info + metadata status + next steps
  ↓
User: "Show me the digital_insights schema"
  ↓
ChatGPT calls: get_dataset_schema(dataset_id=1)
  ↓
Response: All columns + AI descriptions + analysis guidelines
  ↓
User: "Analyze gender distribution"
  ↓
ChatGPT calls: query_dataset(dataset_id=1, query="SELECT gender, SUM(weights)...")
  ↓
Response: Results table + strategic insights + recommendations
  ↓
User: "Compare by age and gender"
  ↓
ChatGPT calls: execute_multi_query() with multiple queries
  ↓
Response: Combined analysis + strategic recommendations
```

---

## 💡 Sample Questions to Test

### Basic Queries:
1. "What datasets are available?"
2. "Show me the schema for digital_insights"
3. "Give me 5 sample rows from digital_insights"

### Strategic Analysis:
4. "What's the gender distribution? Provide strategic insights."
5. "Analyze app usage by age group. Recommend media spend allocation."
6. "Compare CTV vs mobile engagement. What should we prioritize?"
7. "Which demographic segments have highest engagement? How should we target them?"

### Complex Multi-Query:
8. "Analyze user behavior across age, gender, and platform. Provide comprehensive ecommerce strategy recommendations."

---

## 🎉 Success Indicators

You'll know it's working when:

1. ✅ **First response is informative** - Not just "1 dataset available"
2. ✅ **Metadata is rich** - Column descriptions explain business meaning
3. ✅ **Analysis is strategic** - Focus on business outcomes
4. ✅ **Format is professional** - Tables, not JSON
5. ✅ **Recommendations are actionable** - Clear next steps
6. ✅ **Queries are accurate** - ChatGPT writes correct SQL
7. ✅ **Weighting works** - Uses SUM(weights) for aggregations

---

## 📞 Need Help?

1. Check `IMPROVEMENTS_SUMMARY.md` for detailed explanation
2. Check `LOCAL_TESTING_GUIDE.md` for setup instructions
3. View server logs: `tail -f /home/ubuntu/new-mcp-server/server.log`
4. View UI dashboard: https://8501-i7gbmtz3p5iufyckvz436-d5ea8055.manus-asia.computer/ui/

---

**Ready to test!** 🚀

Connect ChatGPT to the MCP endpoint and start with "What datasets are available?"

