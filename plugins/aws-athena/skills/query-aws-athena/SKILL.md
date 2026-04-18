---
name: query-aws-athena
description: Use when running SQL queries against AWS Athena, querying data stored in S3, downloading large Athena result sets, running parallel Athena queries, or optimizing complex queries with CTEs. Triggers on "run Athena query", "query S3 data", "Athena SQL", "query data in AWS", "Athena results", "download Athena output", "Athena timeout", "large Athena result", or any request to execute or optimize AWS Athena queries.
---

# Query AWS Athena

## Prerequisites

- Python 3 with `boto3` installed
- AWS account with Athena and S3 access
- AWS credentials configured (environment variables, `~/.aws/credentials`, or instance profile)

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
${SKILL_DIR}/scripts/query_athena.py \
    --query "SELECT * FROM my_table LIMIT 100" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --region us-east-1 \
    --profile my-aws-profile
```

The script automatically:
- Executes the query
- Waits for completion
- Downloads results from S3 (avoiding pagination issues)
- Saves results locally

### Execute Query from File

For complex queries, store them in a file and reference it:

```bash
${SKILL_DIR}/scripts/query_athena.py \
    --query-file query.sql \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --output-file results.csv \
    --profile my-aws-profile
```

### Execute Without Downloading

To only execute the query without downloading results:

```bash
${SKILL_DIR}/scripts/query_athena.py \
    --query "SELECT * FROM my_table" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --no-download \
    --profile my-aws-profile
```

## AWS Profile Configuration

Use the `--profile` parameter to specify which AWS credentials profile to use:

```bash
${SKILL_DIR}/scripts/query_athena.py \
    --query "SELECT * FROM my_table LIMIT 100" \
    --database my_database \
    --output-location s3://my-bucket/athena-results/ \
    --region us-east-1 \
    --profile my-aws-profile
```

**Prefer `--profile` over environment variables** like `AWS_PROFILE` because:
- Explicit and visible in command history
- No risk of accidentally using wrong credentials from shell environment
- Easier to audit and reproduce queries

The `--profile` parameter is optional. Omit it when running on EC2 instances, Lambda functions, ECS tasks, or any environment that provides credentials via an IAM instance/task role — boto3 will automatically pick up the ambient credentials.

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

## Script Parameters

### Required Parameters
- `--query` or `--query-file`: SQL query string or path to a `.sql` file
- `--database`: Athena database name
- `--output-location`: S3 URI for query results (e.g., `s3://my-bucket/athena-results/`)

### Optional Parameters
- `--profile`: AWS credentials profile name. Omit when running with instance/task role credentials (EC2, Lambda, ECS).
- `--output-file`: Local file path to save downloaded results (auto-generated if not specified)
- `--format`: Output format (default: `csv`; only `csv` is supported — Athena writes CSV to S3)
- `--region`: AWS region (uses profile default if not specified)
- `--no-download`: Execute query but skip downloading results from S3

Run `${SKILL_DIR}/scripts/query_athena.py --help` for the full parameter list.

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
- Specify output format (only csv is supported)
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
- Downloads results as CSV (Athena writes CSV to S3)

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

## Error Handling

### Common Query Failures

**InvalidRequestException**
Athena rejects the query before execution. Causes include syntax errors, referencing non-existent databases or tables, and unsupported SQL constructs. Fix the SQL and re-run.

**AccessDeniedException / insufficient permissions**
The caller lacks `athena:StartQueryExecution`, `s3:PutObject` on the output bucket, or `glue:GetTable` for the data catalog. Check IAM policies and ensure the output S3 bucket allows writes from the executing principal.

**S3 output location missing or inaccessible**
Athena cannot write results if the `--output-location` bucket does not exist or the principal has no write access. Verify the bucket exists and the IAM policy grants `s3:PutObject` and `s3:GetBucketLocation` on that prefix.

**Query timeout**
Long-running queries can exceed Athena's default 30-minute timeout. Partition-prune with `WHERE` clauses, use CTEs to avoid repeated scans, or split into smaller parallel queries.

### Checking Query Status

If `query_athena.py` exits before results are downloaded (e.g. a timeout or SIGINT), retrieve the `QueryExecutionId` printed at script start and check status manually:

```bash
aws athena get-query-execution \
    --query-execution-id <QueryExecutionId> \
    --region us-east-1 \
    --profile my-aws-profile
```

The `Status.State` field will be `SUCCEEDED`, `FAILED`, or `CANCELLED`. For `FAILED`, `Status.AthenaError.ErrorMessage` contains the root cause.

### Retry Guidance

- **Transient API errors** (ThrottlingException, InternalServerException): retry with exponential backoff; Athena has per-account concurrency limits.
- **FAILED queries**: do not retry blindly — read the error message first. Syntax and permission errors will not resolve on their own.
- **Succeeded but no local file**: the query output is still in S3 at `--output-location/<QueryExecutionId>.csv`; download it with `aws s3 cp`.

## Summary

When working with AWS Athena:

1. **Use the provided script** to execute queries and download results from S3
2. **Consider parallel execution** for independent queries to reduce total execution time
3. **Structure complex queries with CTEs** to avoid repeated subquery execution
4. **Load reference files** as needed for detailed patterns and examples

These practices ensure efficient, cost-effective, and maintainable Athena operations.
