# AWS Athena Best Practices

## Overview

This document contains essential best practices for working with AWS Athena to ensure efficient, cost-effective, and reliable query operations.

## Best Practice 1: Download Results from S3 Instead of Using Athena Query Results API

**Guideline**: Download results from S3 instead of using the Athena query results API. This way you don't have to worry about pagination.

**Why This Matters**:
- The Athena query results API has pagination limits (1000 rows per page)
- For large result sets, pagination requires multiple API calls
- Downloading directly from S3 is simpler, faster, and more reliable
- S3 downloads avoid the complexity of handling pagination logic

**Implementation**:
1. Execute the Athena query with `start_query_execution()`
2. Wait for query completion using `get_query_execution()`
3. Retrieve the S3 output location from the query execution details
4. Download the results file directly from S3 using `s3.download_file()`

**Example Workflow**:
```python
# Execute query
response = athena.start_query_execution(
    QueryString=query,
    QueryExecutionContext={'Database': database},
    ResultConfiguration={'OutputLocation': 's3://bucket/path/'}
)

# Get S3 location
execution = athena.get_query_execution(QueryExecutionId=query_id)
s3_location = execution['QueryExecution']['ResultConfiguration']['OutputLocation']

# Download from S3 (no pagination needed!)
s3.download_file(bucket, key, local_file)
```

**Use the provided script**: The `query_athena.py` script implements this pattern automatically.

---

## Best Practice 2: Consider Running Queries in Parallel

**Guideline**: Consider running queries in parallel whenever it makes sense.

**Why This Matters**:
- Athena supports concurrent query execution
- Independent queries can run simultaneously, reducing total execution time
- Parallel execution is especially beneficial for:
  - Multiple independent analytics queries
  - Queries on different tables or partitions
  - Batch processing workflows

**When to Use Parallel Execution**:
- ✓ Multiple independent queries that don't depend on each other's results
- ✓ Querying different tables or databases simultaneously
- ✓ Running the same query across multiple time partitions
- ✓ Batch ETL operations with independent data sources

**When NOT to Use Parallel Execution**:
- ✗ Queries that depend on results from other queries (use sequential execution)
- ✗ Queries that might exceed your Athena query concurrency limits
- ✗ Very simple, fast queries where overhead outweighs benefits

**Implementation Strategies**:

### Strategy 1: Python Threading
```python
import concurrent.futures

queries = [query1, query2, query3]

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(execute_query, q) for q in queries]
    results = [f.result() for f in futures]
```

### Strategy 2: Async/Await (Python 3.7+)
```python
import asyncio

async def execute_multiple_queries(queries):
    tasks = [execute_query_async(q) for q in queries]
    return await asyncio.gather(*tasks)
```

### Strategy 3: Multiple AWS CLI Commands
```bash
# Start multiple queries in background
aws athena start-query-execution --query-string "$QUERY1" ... &
aws athena start-query-execution --query-string "$QUERY2" ... &
aws athena start-query-execution --query-string "$QUERY3" ... &
wait
```

**Important Considerations**:
- Monitor your AWS Athena query concurrency limits (default: 20-25 concurrent queries per account)
- Consider cost implications (queries run in parallel still consume resources)
- Implement proper error handling for each parallel query
- Use query execution IDs to track and manage parallel executions

---

## Best Practice 3: Use Common Table Expressions (CTEs) to Avoid Repeated Subquery Execution

**Guideline**: Use Common Table Expressions to reference the same data transformation multiple times within a query, avoiding repeated subquery execution. Structure them from simple to complex, with fundamental transformations first.

**Why This Matters**:
- CTEs improve query performance by computing transformations once
- Without CTEs, repeated subqueries are executed multiple times
- CTEs make queries more readable and maintainable
- Athena optimizes CTE execution by caching intermediate results

**Problem: Repeated Subqueries**
```sql
-- BAD: This subquery is executed THREE times
SELECT
    (SELECT COUNT(*) FROM users WHERE active = true) as active_users,
    (SELECT COUNT(*) FROM users WHERE active = true) /
    (SELECT COUNT(*) FROM users WHERE active = true) * 100 as percentage
FROM dual;
```

**Solution: Use CTEs**
```sql
-- GOOD: Subquery is executed ONCE
WITH active_user_count AS (
    SELECT COUNT(*) as count
    FROM users
    WHERE active = true
)
SELECT
    count as active_users,
    count / count * 100 as percentage
FROM active_user_count;
```

**Structuring CTEs: Simple to Complex**

Structure CTEs from fundamental transformations first, building up to more complex operations:

```sql
-- Layer 1: Basic data extraction
WITH raw_events AS (
    SELECT
        user_id,
        event_type,
        timestamp,
        session_id
    FROM events
    WHERE date_partition >= '2025-01-01'
),

-- Layer 2: Initial transformations
user_sessions AS (
    SELECT
        user_id,
        session_id,
        COUNT(*) as event_count,
        MIN(timestamp) as session_start,
        MAX(timestamp) as session_end
    FROM raw_events
    GROUP BY user_id, session_id
),

-- Layer 3: Derived metrics
session_metrics AS (
    SELECT
        user_id,
        session_id,
        event_count,
        TIMESTAMP_DIFF(session_end, session_start, SECOND) as duration_seconds
    FROM user_sessions
    WHERE event_count > 1  -- Filter out single-event sessions
),

-- Layer 4: Final aggregation
user_summary AS (
    SELECT
        user_id,
        COUNT(DISTINCT session_id) as total_sessions,
        AVG(duration_seconds) as avg_session_duration,
        SUM(event_count) as total_events
    FROM session_metrics
    GROUP BY user_id
)

-- Final query uses the CTEs
SELECT
    user_id,
    total_sessions,
    avg_session_duration,
    total_events,
    total_events / total_sessions as avg_events_per_session
FROM user_summary
WHERE total_sessions >= 5
ORDER BY avg_session_duration DESC
LIMIT 100;
```

**CTE Best Practices**:

1. **Name CTEs Descriptively**: Use clear names that indicate what the CTE contains
   - Good: `active_users`, `session_metrics`, `daily_aggregates`
   - Bad: `temp1`, `cte2`, `data`

2. **Structure from Simple to Complex**: Build up complexity layer by layer
   - Start with data extraction
   - Then apply filters and transformations
   - Finally perform aggregations and calculations

3. **Reuse CTEs**: Reference the same CTE multiple times to avoid recomputation
```sql
WITH user_counts AS (
    SELECT status, COUNT(*) as count
    FROM users
    GROUP BY status
)
SELECT
    (SELECT count FROM user_counts WHERE status = 'active') as active,
    (SELECT count FROM user_counts WHERE status = 'inactive') as inactive,
    (SELECT count FROM user_counts WHERE status = 'pending') as pending;
```

4. **Document Complex CTEs**: Add comments to explain the purpose of each CTE
```sql
WITH
    -- Extract all user events from the last 30 days
    recent_events AS (...),

    -- Calculate engagement scores based on event frequency
    engagement_scores AS (...)
```

5. **Use CTEs for Recursive Queries**: Athena supports recursive CTEs for hierarchical data
```sql
WITH RECURSIVE hierarchy AS (
    SELECT id, name, parent_id, 1 as level
    FROM categories
    WHERE parent_id IS NULL

    UNION ALL

    SELECT c.id, c.name, c.parent_id, h.level + 1
    FROM categories c
    JOIN hierarchy h ON c.parent_id = h.id
)
SELECT * FROM hierarchy;
```

**Performance Comparison**:
- Without CTEs: Same subquery executed N times = N × query cost
- With CTEs: Subquery executed once, results cached = 1 × query cost
- For complex queries with multiple references, CTEs can provide 2-10x performance improvement

---

## Summary

Apply these three best practices consistently when working with AWS Athena:

1. **Download from S3**: Avoid pagination issues by downloading results directly from S3
2. **Parallel Execution**: Run independent queries in parallel to reduce total execution time
3. **Use CTEs**: Structure queries with CTEs to avoid repeated subquery execution and improve readability

These practices will help ensure efficient, cost-effective, and maintainable Athena operations.
