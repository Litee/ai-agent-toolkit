---
name: query-aws-athena
description: This skill should be used when working with AWS Athena queries, including executing queries, downloading results, optimizing query performance, or structuring complex queries. Use when querying data in Athena, handling large result sets, running parallel queries, or using Common Table Expressions (CTEs) for query optimization.
version: 1.0.0
dependencies:
  - python3
  - boto3
---

# Query AWS Athena

## Overview

This skill provides best practices, tools, and guidance for working with AWS Athena efficiently. It helps execute queries, download results from S3, run queries in parallel, and structure complex queries using Common Table Expressions (CTEs) to optimize performance and avoid repeated subquery execution.

## Core Best Practices

Follow these three essential best practices when working with AWS Athena:

1. **Download results from S3** instead of using the Athena query results API (avoids pagination)
2. **Run queries in parallel** when working with independent queries
3. **Use Common Table Expressions (CTEs)** to avoid repeated subquery execution

For detailed explanations and implementation guidance, read the `references/best-practices.md` file.

## Quick Start

### Execute Query and Download Results

Use the provided script to execute Athena queries and automatically download results from S3:

```bash
python3 scripts/query_athena.py \
    --query "SELECT * FROM my_table LIMIT 100" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/
```

The script automatically:
- Executes the query
- Waits for completion
- Downloads results from S3 (avoiding pagination issues)
- Saves results locally

### Execute Query from File

For complex queries, store them in a file and reference it:

```bash
python3 scripts/query_athena.py \
    --query-file query.sql \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --output-file results.csv
```

### Execute Without Downloading

To only execute the query without downloading results:

```bash
python3 scripts/query_athena.py \
    --query "SELECT * FROM my_table" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --no-download
```

## AWS Profile Configuration

Use the `--profile` parameter to specify which AWS credentials profile to use:

```bash
python3 scripts/query_athena.py \
    --query "SELECT * FROM my_table LIMIT 100" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --profile my-aws-profile
```

**Prefer `--profile` over environment variables** like `AWS_PROFILE` because:
- Explicit and visible in command history
- No risk of accidentally using wrong credentials from shell environment
- Easier to audit and reproduce queries

The `--profile` parameter is required to ensure explicit AWS credential selection.

## Running Queries in Parallel

When working with multiple independent queries, consider running them in parallel to reduce total execution time.

**When to use parallel execution:**
- Multiple independent queries that don't depend on each other's results
- Querying different tables or databases simultaneously
- Running the same query across multiple time partitions
- Batch processing workflows with independent data sources

**When NOT to use parallel execution:**
- Queries that depend on results from other queries (use sequential execution)
- Queries that might exceed Athena query concurrency limits
- Very simple, fast queries where overhead outweighs benefits

**Implementation approaches:**
- Use Python's `concurrent.futures.ThreadPoolExecutor` for parallel execution
- Use async/await patterns with `asyncio`
- Run multiple AWS CLI commands in background processes

Refer to `references/best-practices.md` for detailed parallel execution patterns and examples.

## Optimizing Queries with CTEs

Common Table Expressions (CTEs) help avoid repeated subquery execution and improve query readability. Structure CTEs from simple to complex, with fundamental transformations first.

**When to use CTEs:**
- The same subquery is referenced multiple times in a query
- Building complex queries with multiple transformation stages
- Improving query readability and maintainability
- Working with hierarchical or recursive data

**Basic pattern:**
```sql
WITH
    -- Stage 1: Basic data extraction
    raw_data AS (
        SELECT ...
        FROM table
        WHERE date_partition >= '2025-01-01'
    ),

    -- Stage 2: Transformations
    transformed_data AS (
        SELECT ...
        FROM raw_data
        WHERE ...
    )

-- Final query
SELECT *
FROM transformed_data;
```

For comprehensive CTE patterns, examples, and best practices, read the `references/cte-examples.md` file. It includes:
- Pattern 1: Avoiding repeated subqueries
- Pattern 2: Multi-stage data transformation
- Pattern 3: Reusing the same CTE multiple times
- Pattern 4: Self-joins made easier
- Pattern 5: Window functions with CTEs
- Pattern 6: Filtering after aggregation
- Pattern 7: Complex joins simplified
- Pattern 8: Pivot-like operations
- Pattern 9: Recursive CTEs (hierarchical data)
- Pattern 10: Data quality checks

## Workflow

### 1. Planning the Query

Before executing, consider:
- Can this be split into multiple independent queries for parallel execution?
- Does the query have repeated subqueries that can be converted to CTEs?
- What is the expected result set size?

### 2. Structuring the Query

For complex queries:
- Start with CTEs for repeated transformations
- Structure CTEs from simple to complex
- Add descriptive names and comments
- Apply filters early to reduce data volume

### 3. Executing the Query

Use the `query_athena.py` script:
- Execute with automatic S3 download (recommended)
- Specify output format (csv, json, parquet)
- Set appropriate AWS region if needed

### 4. Handling Results

Results are automatically downloaded from S3:
- No pagination handling needed
- Direct file access for large result sets
- Results available in specified format

## Resources

### scripts/

**query_athena.py**: Execute Athena queries and download results from S3

The script provides a complete workflow for querying Athena:
- Executes queries with proper error handling
- Waits for query completion
- Downloads results directly from S3 (avoiding pagination)
- Supports multiple output formats (csv, json, parquet)

### references/

**best-practices.md**: Detailed explanation of the three AWS Athena best practices
- Why download from S3 instead of using query results API
- When and how to run queries in parallel
- How to use CTEs to avoid repeated subquery execution
- Implementation examples and code patterns

**cte-examples.md**: Comprehensive CTE patterns and examples
- 10 practical CTE patterns with real-world examples
- Best practices for naming, structuring, and optimizing CTEs
- Performance tips and guidance on when to use CTEs vs. subqueries
- Recursive CTE examples for hierarchical data

## Loading Reference Files

Load reference files based on the task at hand:

**For general Athena work**: Read `references/best-practices.md` to understand the three core guidelines

**For query optimization**: Read `references/cte-examples.md` to find relevant CTE patterns and examples

**For script usage**: The script includes comprehensive help text accessible via `--help` flag

## Summary

When working with AWS Athena:

1. **Use the provided script** to execute queries and download results from S3
2. **Consider parallel execution** for independent queries to reduce total execution time
3. **Structure complex queries with CTEs** to avoid repeated subquery execution
4. **Load reference files** as needed for detailed patterns and examples

These practices ensure efficient, cost-effective, and maintainable Athena operations.
