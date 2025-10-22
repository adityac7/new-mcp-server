# PostgreSQL Function Compatibility Guide

## Common SQL Function Errors and Solutions

This guide helps LLMs write PostgreSQL-compatible queries by providing alternatives for common SQL functions that may cause errors.

---

## 🔢 Math & Rounding Functions

### ROUND() - Type Casting Required

**❌ ERROR:**
```sql
SELECT ROUND(avg_value, 2) FROM table;
-- Error: function round(double precision, integer) does not exist
```

**✅ SOLUTION:**
```sql
-- Cast to numeric first
SELECT ROUND(avg_value::numeric, 2) FROM table;

-- Or use CAST
SELECT ROUND(CAST(avg_value AS numeric), 2) FROM table;
```

**Why:** PostgreSQL's `ROUND()` requires `numeric` type, not `double precision`.

### TRUNCATE() vs TRUNC()

**❌ ERROR:**
```sql
SELECT TRUNCATE(value, 2) FROM table;
-- TRUNCATE is for table operations, not numbers
```

**✅ SOLUTION:**
```sql
SELECT TRUNC(value::numeric, 2) FROM table;
```

### CEILING() and FLOOR()

**✅ WORKS:**
```sql
SELECT CEILING(value) FROM table;  -- Round up
SELECT FLOOR(value) FROM table;    -- Round down
```

---

## 📅 Date & Time Functions

### DATEADD() → Use Interval

**❌ ERROR:**
```sql
SELECT DATEADD(day, 7, date_column) FROM table;
-- DATEADD doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
-- Add days
SELECT date_column + INTERVAL '7 days' FROM table;

-- Add months
SELECT date_column + INTERVAL '3 months' FROM table;

-- Add years
SELECT date_column + INTERVAL '1 year' FROM table;

-- Subtract
SELECT date_column - INTERVAL '7 days' FROM table;
```

### DATEDIFF() → Use Date Subtraction

**❌ ERROR:**
```sql
SELECT DATEDIFF(day, start_date, end_date) FROM table;
-- DATEDIFF doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
-- Days difference
SELECT (end_date - start_date) AS days_diff FROM table;

-- Years difference
SELECT DATE_PART('year', AGE(end_date, start_date)) FROM table;

-- Months difference
SELECT (DATE_PART('year', AGE(end_date, start_date)) * 12 + 
        DATE_PART('month', AGE(end_date, start_date))) FROM table;
```

### GETDATE() → Use NOW() or CURRENT_DATE

**❌ ERROR:**
```sql
SELECT GETDATE();
-- GETDATE doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
SELECT NOW();                    -- Current timestamp with timezone
SELECT CURRENT_TIMESTAMP;        -- Same as NOW()
SELECT CURRENT_DATE;             -- Current date only
SELECT CURRENT_TIME;             -- Current time only
```

### FORMAT() for Dates → Use TO_CHAR()

**❌ ERROR:**
```sql
SELECT FORMAT(date_column, 'YYYY-MM-DD') FROM table;
```

**✅ SOLUTION:**
```sql
SELECT TO_CHAR(date_column, 'YYYY-MM-DD') FROM table;
SELECT TO_CHAR(date_column, 'Mon DD, YYYY') FROM table;
SELECT TO_CHAR(date_column, 'Day, Month DD, YYYY') FROM table;
```

---

## 🔤 String Functions

### CONCAT_WS() - Concat with Separator

**✅ WORKS in PostgreSQL:**
```sql
SELECT CONCAT_WS(', ', first_name, last_name) FROM users;
```

### GROUP_CONCAT() → Use STRING_AGG()

**❌ ERROR:**
```sql
SELECT GROUP_CONCAT(name, ', ') FROM table GROUP BY category;
-- GROUP_CONCAT doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
SELECT STRING_AGG(name, ', ') FROM table GROUP BY category;

-- With ORDER BY
SELECT STRING_AGG(name, ', ' ORDER BY name) FROM table GROUP BY category;
```

### LEN() → Use LENGTH()

**❌ ERROR:**
```sql
SELECT LEN(column_name) FROM table;
-- LEN doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
SELECT LENGTH(column_name) FROM table;
SELECT CHAR_LENGTH(column_name) FROM table;  -- Same as LENGTH
```

### SUBSTRING() - Different Syntax

**✅ PostgreSQL Syntax:**
```sql
-- Extract substring starting at position 1, length 5
SELECT SUBSTRING(column_name FROM 1 FOR 5) FROM table;

-- Or use standard SQL syntax
SELECT SUBSTRING(column_name, 1, 5) FROM table;
```

---

## 🔢 Aggregate Functions

### STDEV() → Use STDDEV()

**❌ ERROR:**
```sql
SELECT STDEV(value) FROM table;
-- STDEV doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
SELECT STDDEV(value) FROM table;           -- Sample standard deviation
SELECT STDDEV_POP(value) FROM table;       -- Population standard deviation
SELECT STDDEV_SAMP(value) FROM table;      -- Sample standard deviation (same as STDDEV)
```

### VARIANCE() Functions

**✅ WORKS:**
```sql
SELECT VARIANCE(value) FROM table;         -- Sample variance
SELECT VAR_POP(value) FROM table;          -- Population variance
SELECT VAR_SAMP(value) FROM table;         -- Sample variance
```

---

## 🎯 Conditional Functions

### ISNULL() → Use COALESCE() or IS NULL

**❌ ERROR:**
```sql
SELECT ISNULL(column_name, 0) FROM table;
-- ISNULL doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
-- Replace NULL with default value
SELECT COALESCE(column_name, 0) FROM table;

-- Check if NULL
SELECT column_name IS NULL FROM table;
SELECT column_name IS NOT NULL FROM table;
```

### IIF() → Use CASE WHEN

**❌ ERROR:**
```sql
SELECT IIF(age > 18, 'Adult', 'Minor') FROM users;
-- IIF doesn't exist in PostgreSQL
```

**✅ SOLUTION:**
```sql
SELECT CASE 
    WHEN age > 18 THEN 'Adult' 
    ELSE 'Minor' 
END FROM users;

-- Or use CASE with multiple conditions
SELECT CASE 
    WHEN age < 13 THEN 'Child'
    WHEN age < 18 THEN 'Teen'
    ELSE 'Adult'
END FROM users;
```

---

## 📊 Type Casting

### CAST() vs :: Operator

**Both work in PostgreSQL:**
```sql
-- Using CAST (SQL standard)
SELECT CAST(column_name AS integer) FROM table;
SELECT CAST(column_name AS numeric) FROM table;
SELECT CAST(column_name AS text) FROM table;

-- Using :: operator (PostgreSQL shorthand)
SELECT column_name::integer FROM table;
SELECT column_name::numeric FROM table;
SELECT column_name::text FROM table;
```

**Common casts:**
```sql
-- String to number
SELECT '123'::integer;
SELECT '123.45'::numeric;
SELECT '123.45'::double precision;

-- Number to string
SELECT 123::text;

-- Date/time conversions
SELECT '2024-01-01'::date;
SELECT '2024-01-01 12:00:00'::timestamp;
```

---

## 🔍 Pattern Matching

### LIKE vs ILIKE

**✅ WORKS:**
```sql
-- Case-sensitive
SELECT * FROM table WHERE column_name LIKE '%search%';

-- Case-insensitive (PostgreSQL specific)
SELECT * FROM table WHERE column_name ILIKE '%search%';
```

### Regular Expressions

**✅ PostgreSQL Regex:**
```sql
-- Match regex (case-sensitive)
SELECT * FROM table WHERE column_name ~ '^[A-Z]';

-- Match regex (case-insensitive)
SELECT * FROM table WHERE column_name ~* '^[a-z]';

-- Not match
SELECT * FROM table WHERE column_name !~ '^[A-Z]';
```

---

## 💡 Best Practices for LLMs

### 1. Always Cast for ROUND()
```sql
-- ❌ BAD
SELECT ROUND(avg_value, 2)

-- ✅ GOOD
SELECT ROUND(avg_value::numeric, 2)
```

### 2. Use COALESCE() for NULL handling
```sql
-- ❌ BAD
SELECT ISNULL(column, 0)

-- ✅ GOOD
SELECT COALESCE(column, 0)
```

### 3. Use Interval for Date Math
```sql
-- ❌ BAD
SELECT DATEADD(day, 7, date_column)

-- ✅ GOOD
SELECT date_column + INTERVAL '7 days'
```

### 4. Use STRING_AGG() for Concatenation
```sql
-- ❌ BAD
SELECT GROUP_CONCAT(name, ', ')

-- ✅ GOOD
SELECT STRING_AGG(name, ', ')
```

### 5. Use CASE WHEN for Conditionals
```sql
-- ❌ BAD
SELECT IIF(condition, 'Yes', 'No')

-- ✅ GOOD
SELECT CASE WHEN condition THEN 'Yes' ELSE 'No' END
```

---

## 📋 Quick Reference Table

| SQL Server / MySQL | PostgreSQL | Notes |
|-------------------|------------|-------|
| `ROUND(value, 2)` | `ROUND(value::numeric, 2)` | Cast to numeric |
| `DATEADD(day, 7, date)` | `date + INTERVAL '7 days'` | Use interval |
| `DATEDIFF(day, d1, d2)` | `(d2 - d1)` | Direct subtraction |
| `GETDATE()` | `NOW()` or `CURRENT_DATE` | Current timestamp |
| `GROUP_CONCAT(col, ',')` | `STRING_AGG(col, ',')` | String aggregation |
| `LEN(col)` | `LENGTH(col)` | String length |
| `ISNULL(col, 0)` | `COALESCE(col, 0)` | NULL handling |
| `IIF(cond, a, b)` | `CASE WHEN cond THEN a ELSE b END` | Conditional |
| `STDEV(col)` | `STDDEV(col)` | Standard deviation |
| `TOP 10` | `LIMIT 10` | Row limiting |

---

## 🚀 Common Query Patterns

### Weighted Aggregation with Rounding
```sql
SELECT 
    gender,
    ROUND(SUM(weights)::numeric, 2) as total_population,
    ROUND(AVG(age)::numeric, 1) as avg_age
FROM digital_insights
GROUP BY gender;
```

### Date Range with Intervals
```sql
SELECT *
FROM digital_insights
WHERE event_date >= CURRENT_DATE - INTERVAL '30 days'
  AND event_date < CURRENT_DATE;
```

### String Aggregation with Ordering
```sql
SELECT 
    category,
    STRING_AGG(app_name, ', ' ORDER BY app_name) as apps
FROM digital_insights
GROUP BY category;
```

### Conditional Aggregation
```sql
SELECT 
    gender,
    SUM(CASE WHEN age < 18 THEN weights ELSE 0 END) as youth_population,
    SUM(CASE WHEN age >= 18 THEN weights ELSE 0 END) as adult_population
FROM digital_insights
GROUP BY gender;
```

---

## 🎓 Learning Resources

- **Official PostgreSQL Docs**: https://www.postgresql.org/docs/current/functions.html
- **Date/Time Functions**: https://www.postgresql.org/docs/current/functions-datetime.html
- **String Functions**: https://www.postgresql.org/docs/current/functions-string.html
- **Aggregate Functions**: https://www.postgresql.org/docs/current/functions-aggregate.html

---

**Last Updated:** October 22, 2025  
**PostgreSQL Version:** 16+  
**Purpose:** Guide LLMs to write PostgreSQL-compatible queries

