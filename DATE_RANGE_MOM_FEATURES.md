# Date Range & MoM Analysis Features

## Overview

Added comprehensive date range tracking and Month-over-Month (MoM) analysis guidelines to the MCP Analytics Server.

---

## Features Implemented

### 1. **Date Range Tracking**

#### Database Changes
- Added `date_range` column to `datasets` table (VARCHAR(100))
- Added `date_column` column to `datasets` table (VARCHAR(100))
- Example: `date_range = "Jan 2018 - Dec 2025"`, `date_column = "date"`

#### Current Dataset
**digital_insights**:
- **Date Range**: Jan 2018 - Dec 2025
- **Date Column**: `date`
- **Data Distribution**: 99.89% from 2025 (838,124 rows)
- **Total Rows**: 839,077

#### Display in First Tool Call
Date range now appears in `list_available_datasets()`:

```markdown
| ID | Dataset Name | Date Range | Records | Metadata | Description |
|:---:|---|:---:|---:|:---:|---|
| 1 | **digital_insights** | Jan 2018 - Dec 2025 | 839,077 | ✅ | CTV and mobile analytics... |
```

---

### 2. **MoM (Month-over-Month) Analysis Guidelines**

#### Default Time Period
When multiple months of data are available:
- **Primary**: Last month
- **Comparison**: Last 3 months
- **Purpose**: Show trends and MoM changes

#### Guidelines Added
```markdown
**Time Period**: If multiple months available, analyze **last month + last 3 months** by default
- Show **MoM (Month-over-Month) trends** for all metrics
- Always include time period in reporting
```

#### Example Query Pattern
```sql
-- Last month
SELECT 
    gender,
    ROUND(SUM(weights)::numeric / 1000, 2) as population_thousands
FROM digital_insights
WHERE date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND date < DATE_TRUNC('month', CURRENT_DATE)
GROUP BY gender;

-- Last 3 months for MoM trend
SELECT 
    TO_CHAR(date, 'YYYY-MM') as month,
    gender,
    ROUND(SUM(weights)::numeric / 1000, 2) as population_thousands
FROM digital_insights
WHERE date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '3 months')
  AND date < DATE_TRUNC('month', CURRENT_DATE)
GROUP BY TO_CHAR(date, 'YYYY-MM'), gender
ORDER BY month, gender;
```

---

### 3. **Weight Scale Clarification**

#### Weight Definition
- **Scale**: 1 weight = 1,000 users
- **Example**: weight 0.456 = 456 users (not 0.456 users)

#### Cell Definition
**Cell** = Age × Gender × NCCS × Townclass × State
- Each user represents their cell population
- Weights are assigned per cell for representativeness

#### Updated Guidelines
```markdown
**Weighting**: ALWAYS use weighted aggregation (`SUM(weights)`) - weight users, not events
- **Weight Scale**: 1 weight = 1,000 users (e.g., weight 0.456 = 456 users)
- **Cell Definition**: Age × Gender × NCCS × Townclass × State
```

#### Reporting Format
```sql
-- Convert weights to thousands for readability
SELECT 
    gender,
    ROUND(SUM(weights)::numeric / 1000, 2) as population_thousands
FROM digital_insights
GROUP BY gender;
```

**Output**:
```
| gender | population_thousands |
|--------|---------------------|
| Male   | 425.67              |
| Female | 413.41              |
```

Interpretation: 425,670 males and 413,410 females in the population.

---

### 4. **Persona-Based Reporting**

#### Panel Data Context
- Data comes from a **sample representative population**
- Collected consentfully from smartphones/CTV
- Users carry weights representing their cell

#### Reporting Requirements
- Always report for **personas** (not absolute totals)
- Example: "Average per female user/day"
- Example: "Monthly aggregated usage per male user in NCCS A"

#### Updated Guidelines
```markdown
**Panel Data**: Report for personas (e.g., "average per female user/day", not absolute totals)
```

---

## Complete Guidelines in Schema Response

When LLM calls `get_dataset_schema()`, they see:

```markdown
## 📋 Analysis & Query Guidelines

**User Persona**: CMI team for large brands - provide insights like a seasoned brand manager

**Critical Rules**:
1. **Weighting**: ALWAYS use weighted aggregation (`SUM(weights)`) - weight users, not events
   - **Weight Scale**: 1 weight = 1,000 users (e.g., weight 0.456 = 456 users)
   - **Cell Definition**: Age × Gender × NCCS × Townclass × State
2. **Time Period**: If multiple months available, analyze **last month + last 3 months** by default
   - Show **MoM (Month-over-Month) trends** for all metrics
   - Always include time period in reporting
3. **Raw Data**: Limit to 5 rows maximum - use aggregation (GROUP BY) for larger datasets
4. **Panel Data**: Report for personas (e.g., "average per female user/day", not absolute totals)
5. **NCCS**: A+A1→A, C/D/E→C/D/E (auto-merged by system)
6. **Context**: Keep queries specific to avoid token overflow

**Response Style**:
- Detailed, actionable insights for brand managers
- Focus on media planning and ecommerce strategy
- Use tables/visualizations, less verbose, more analysis
- Provide comparative analysis and trends

**PostgreSQL Syntax**:
- ROUND: `ROUND(value::numeric, 2)`
- NULL: `COALESCE(column, 0)`
- String agg: `STRING_AGG(column, ', ')`
- Date math: `date + INTERVAL '7 days'`
```

---

## Future Dataset Additions

### Auto-Detection (To Be Implemented)
When adding new datasets, the system will:

1. **Detect date columns** automatically
   - Look for columns with 'date', 'time', 'created', 'updated' in name
   - Prefer `date`, `event_date`, `created_at` in that order

2. **Query date range**
   ```sql
   SELECT 
       MIN(date_column) as min_date,
       MAX(date_column) as max_date
   FROM table_name
   ```

3. **Validate date range**
   - Expected: 2018-2026
   - ⚠️ Flag if before 2018 (too old, likely error)
   - ⚠️ Flag if after 2026 (future, likely error)

4. **Check date format consistency**
   - Validate all dates are in proper format
   - Warn if inconsistencies found

5. **Prompt user**
   - Show detected date range
   - Ask to confirm or fix database
   - Options: "Add anyway" or "Fix database first"

### Date Range Anomalies

**Example from digital_insights**:
```
Date Distribution by Year:
============================================================
Year          Count          Percentage
------------------------------------------------------------
1970                     7           0.00%  ⚠️ Too old (Unix epoch default)
2008                    14           0.00%  ⚠️ Too old
2015                    33           0.00%  ⚠️ Too old
2017                    13           0.00%  ⚠️ Before expected range
2018                    45           0.01%  ✅ Valid
2019                   137           0.02%  ✅ Valid
2020                    30           0.00%  ✅ Valid
2021                    77           0.01%  ✅ Valid
2022                    43           0.01%  ✅ Valid
2023                   186           0.02%  ✅ Valid
2024                   368           0.04%  ✅ Valid
2025               838,124          99.89%  ✅ Valid (primary data)
```

**System would warn**:
- "⚠️ Found 67 rows with dates before 2018 (0.01%)"
- "⚠️ Found 7 rows with dates from 1970 (likely default values)"
- "✅ 99.99% of data is within expected range (2018-2026)"
- "Recommendation: Consider filtering out anomalous dates in queries"

---

## Implementation Details

### Files Modified

1. **`app/models.py`**
   - Added `date_range` and `date_column` to Dataset model

2. **`migrate_add_date_columns.py`**
   - Migration script to add columns to existing database
   - Updates digital_insights with date range

3. **`server.py`**
   - Updated `list_available_datasets()` to include date_range and date_column

4. **`app/services/response_formatter.py`**
   - Added date range column to dataset list table
   - Added MoM analysis guidelines
   - Added weight scale clarification
   - Added cell definition

### Database Schema

```sql
ALTER TABLE datasets 
ADD COLUMN date_range VARCHAR(100),
ADD COLUMN date_column VARCHAR(100);

UPDATE datasets 
SET date_range = 'Jan 2018 - Dec 2025',
    date_column = 'date'
WHERE id = 1;
```

---

## Testing

### Test Scenario 1: List Datasets
```
Tool: list_available_datasets()
```

**Expected Output**:
```markdown
| ID | Dataset Name | Date Range | Records | Metadata | Description |
|:---:|---|:---:|---:|:---:|---|
| 1 | **digital_insights** | Jan 2018 - Dec 2025 | 839,077 | ✅ | CTV and mobile... |
```

### Test Scenario 2: Get Schema
```
Tool: get_dataset_schema(1)
```

**Expected Output** (includes):
```markdown
**Time Period**: If multiple months available, analyze **last month + last 3 months** by default
- Show **MoM (Month-over-Month) trends** for all metrics
- Always include time period in reporting
```

### Test Scenario 3: MoM Analysis Query
```
Tool: query_dataset(1, "
SELECT 
    TO_CHAR(date, 'YYYY-MM') as month,
    gender,
    ROUND(SUM(weights)::numeric / 1000, 2) as population_k
FROM digital_insights
WHERE date >= '2025-09-01' AND date < '2025-12-01'
GROUP BY TO_CHAR(date, 'YYYY-MM'), gender
ORDER BY month, gender
")
```

**Expected Output**:
```markdown
| month   | gender | population_k |
|---------|--------|-------------|
| 2025-09 | Male   | 142.34      |
| 2025-09 | Female | 138.12      |
| 2025-10 | Male   | 141.89      |
| 2025-10 | Female | 137.98      |
| 2025-11 | Male   | 141.44      |
| 2025-11 | Female | 137.31      |
```

**LLM Analysis** (expected):
```
Month-over-Month Trends (Sep-Nov 2025):

Male Population:
- Sep: 142.34K
- Oct: 141.89K (-0.32% MoM)
- Nov: 141.44K (-0.32% MoM)

Female Population:
- Sep: 138.12K
- Oct: 137.98K (-0.10% MoM)
- Nov: 137.31K (-0.49% MoM)

Insights:
- Slight declining trend in both genders
- Female population showing steeper decline in Nov
- Overall stable population with minimal fluctuation
```

---

## Benefits

### 1. **Immediate Context**
- Date range visible from first tool call
- No need to query for date range separately
- LLM knows data availability upfront

### 2. **MoM Analysis by Default**
- Automatic trend analysis
- Insights into changes over time
- Better strategic decision-making

### 3. **Weight Clarity**
- Clear understanding of scale (1 = 1,000 users)
- Proper interpretation of weighted results
- Accurate population estimates

### 4. **Panel Data Understanding**
- Clear cell definition
- Proper persona-based reporting
- Avoids absolute total confusion

### 5. **Time Period Awareness**
- Always includes time context
- Prevents misleading aggregations
- Enables temporal comparisons

---

## Future Enhancements

### 1. **Auto-Detection for New Datasets**
- Implement date column detection
- Auto-populate date_range on dataset addition
- Validate date ranges automatically

### 2. **Date Format Validation**
- Check for inconsistent formats
- Warn users during upload
- Suggest standardization

### 3. **Anomaly Detection**
- Flag dates outside 2018-2026
- Identify default values (1970-01-01)
- Recommend data cleaning

### 4. **Dynamic Date Ranges**
- Update date_range periodically
- Detect new data additions
- Refresh metadata automatically

### 5. **Time Period Presets**
- "Last month"
- "Last quarter"
- "YoY comparison"
- "Custom range"

---

## Summary

✅ **Added** date_range and date_column to datasets  
✅ **Updated** digital_insights with "Jan 2018 - Dec 2025"  
✅ **Display** date range in first tool call  
✅ **Added** MoM analysis guidelines  
✅ **Clarified** weight scale (1 = 1,000 users)  
✅ **Defined** cell structure (Age × Gender × NCCS × Townclass × State)  
✅ **Emphasized** persona-based reporting  
✅ **Included** time period in all reporting  

**Result**: LLMs now have complete context from the start, understand MoM analysis requirements, and properly interpret weighted panel data.

---

**Last Updated:** October 22, 2025  
**Status:** Implemented and deployed  
**Migration:** Completed for digital_insights dataset

