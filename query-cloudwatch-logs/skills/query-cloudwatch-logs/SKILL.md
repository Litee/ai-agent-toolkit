---
name: query-cloudwatch-logs
description: This skill should be used when querying AWS CloudWatch Log Insights, including executing queries, monitoring query progress with real-time updates, handling different time formats, and saving results in various output formats. Use when analyzing CloudWatch logs, investigating errors or patterns, or generating reports from log data.
dependencies:
  - python3
  - boto3
---

# Query CloudWatch Logs

## Overview

Execute CloudWatch Log Insights queries with real-time progress tracking, flexible time handling, and multiple output formats. This skill provides a comprehensive Python script that handles query execution, status monitoring with 30-second updates, and result formatting.

## Core Best Practices

Before executing queries, follow these key practices:

1. **Time Range Selection** - Use appropriate time ranges to balance query performance and data coverage. Shorter ranges execute faster and cost less.

2. **Log Group Specification** - Validate log groups exist before querying. Support wildcard patterns for querying multiple log groups.

3. **Query Optimization** - Structure queries efficiently with filters early in the query to reduce data scanned.

4. **Progress Monitoring** - Track query execution with periodic status updates showing records scanned, matched, and data volume.

5. **Result Management** - Choose appropriate output formats (JSON, CSV, table) based on downstream usage.

## Quick Start

### Basic Error Search
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @message | filter @message like /ERROR/' \
  --log-groups '/aws/lambda/my-function' \
  --start-time '1h' \
  --end-time 'now' \
  --format csv
```

### Statistics Aggregation
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'stats count() by bin(5m) | sort bin(5m) desc' \
  --log-groups '/aws/ecs/my-service' \
  --start-time '2025-12-05T00:00:00Z' \
  --end-time '2025-12-05T23:59:59Z' \
  --output-file 'hourly_stats.json' \
  --format json
```

### Multiple Log Groups with Wildcards
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @log, @message | filter level = "ERROR"' \
  --log-groups '/aws/lambda/prod-*' \
  --start-time 'last-24h' \
  --update-interval 60
```

## AWS Profile Configuration

Use the `--profile` parameter to specify which AWS credentials profile to use:

```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @message | filter @message like /ERROR/' \
  --log-groups '/aws/lambda/my-function' \
  --start-time '1h' \
  --profile my-aws-profile
```

**Prefer `--profile` over environment variables** like `AWS_PROFILE` because:
- Explicit and visible in command history
- No risk of accidentally using wrong credentials from shell environment
- Easier to audit and reproduce queries

The `--profile` parameter is required to ensure explicit AWS credential selection.

## Workflow

### 1. Query Preparation

**Define the Query Goal**: Clearly identify what information to extract from logs.

**Select Log Groups**: Specify log groups to query:
- Single log group: `/aws/lambda/my-function`
- Multiple log groups: `/aws/lambda/func1,/aws/lambda/func2`
- Wildcard patterns: `/aws/lambda/prod-*`

**Choose Time Range**: Select appropriate time bounds using various formats:
- **Relative**: `1h`, `2d`, `30m`, `now`
- **Named**: `last-hour`, `last-24h`, `last-week`, `yesterday`, `today`
- **ISO 8601**: `2025-12-05T10:00:00Z`
- **Unix milliseconds**: `1733395200000`

**Write the Query**: Structure CloudWatch Insights query with fields, filters, and aggregations.

For complex queries, use `--query-file` to load from a file:
```bash
./scripts/query_cloudwatch_logs.py \
  --query-file 'complex_analysis.txt' \
  --log-groups '/aws/ecs/production' \
  --start-time 'yesterday' \
  --end-time 'today'
```

### 2. Query Execution

**Execute with Script**: Run the query using the Python script with appropriate parameters.

**Monitor Progress**: The script provides real-time updates every 30 seconds (configurable) showing:
- Elapsed time in readable format (e.g., "2m 15s")
- Query status (Scheduled, Running, Complete, Failed)
- Records scanned and matched
- Data volume processed in MB

Example output during execution:
```
Executing query across 3 log group(s)...
Time range: 1h to now
Query ID: 8f0a2b3c-4d5e-6f7g-8h9i-0j1k2l3m4n5o
Waiting for query to complete...
[30s] Status: Running
  → Scanned: 125,432 records (45.21 MB)
  → Matched: 342 records
[1m 0s] Status: Running
  → Scanned: 287,654 records (103.45 MB)
  → Matched: 1,023 records
[1m 32s] Status: Complete
  → Scanned: 352,189 records (127.89 MB)
  → Matched: 1,456 records
✓ Query completed successfully in 1m 32s
```

**Adjust Update Interval**: Modify status update frequency using `--update-interval`:
```bash
--update-interval 60  # Update every 60 seconds for longer queries
```

### 3. Result Handling

**Choose Output Format**:
- **table** (default): Human-readable aligned columns, good for terminal viewing
- **csv**: Comma-separated values, good for spreadsheet import
- **json**: Structured JSON, good for programmatic processing

**Specify Output File**: Save results to a file:
```bash
--output-file 'query_results.csv' --format csv
```

Or let the script auto-generate a filename based on query ID:
```bash
--format json  # Creates: cloudwatch_logs_results_8f0a2b3c.json
```

**Handle Metadata Fields**: CloudWatch includes metadata fields like `@timestamp`, `@message`, `@logStream`, `@log`. These appear first in results. To exclude them:
```bash
--exclude-metadata
```

### 4. Error Handling

The script provides clear error messages for common issues:

**Log Group Not Found**:
```
✗ Error: Log group not found: /aws/lambda/non-existent
Please verify the log group exists and you have permissions to access it.
```

**Invalid Query Syntax**:
```
✗ Error: Invalid query syntax: MalformedQueryException
```

**Time Range Errors**:
```
✗ Error: Start time must be before end time
Start: 2025-12-05T10:00:00Z (1733400000000)
End: 2025-12-05T09:00:00Z (1733396400000)
```

**Rate Limiting**:
```
✗ API rate limit exceeded. Please wait and try again.
```

## Script Parameters

### Required Parameters
- `--query` or `--query-file`: The Log Insights query (inline or from file)
- `--log-groups`: Comma-separated log groups or patterns
- `--start-time`: Query start time (various formats supported)
- `--profile`: AWS profile name (required)

### Optional Parameters
- `--end-time`: Query end time (default: `now`)
- `--output-file`: Output file path (auto-generated if not specified)
- `--format`: Output format - `table`, `csv`, or `json` (default: `table`)
- `--limit`: Maximum results to return (default: 10000)
- `--region`: AWS region (uses default if not specified)
- `--update-interval`: Status update interval in seconds (default: 30)
- `--exclude-metadata`: Exclude CloudWatch metadata fields

## Advanced Usage

### Query from File with Custom Updates
```bash
./scripts/query_cloudwatch_logs.py \
  --query-file 'analysis/error_patterns.txt' \
  --log-groups '/aws/lambda/prod-api,/aws/lambda/prod-worker' \
  --start-time '2025-12-01T00:00:00Z' \
  --end-time '2025-12-02T00:00:00Z' \
  --output-file 'reports/december_errors.csv' \
  --format csv \
  --limit 50000 \
  --update-interval 60 \
  --region us-east-1 \
  --profile production
```

### Wildcard Log Groups for Microservices
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @log, level, message | filter level = "WARN" or level = "ERROR"' \
  --log-groups '/aws/ecs/prod-*' \
  --start-time 'last-week' \
  --format json
```

### Table Output for Terminal Viewing
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'stats count() as total by level | sort total desc' \
  --log-groups '/aws/lambda/my-function' \
  --start-time 'last-24h' \
  --format table
```

## Resources

### scripts/query_cloudwatch_logs.py
Main Python script for executing CloudWatch Log Insights queries with progress tracking. Features include:
- Flexible time format parsing (ISO 8601, relative, named, Unix timestamps)
- Log group validation with wildcard expansion
- 30-second progress updates with statistics
- Multiple output formats (JSON, CSV, table)
- Comprehensive error handling
- AWS credential chain support

The script can be executed directly and requires boto3.

### references/
Detailed documentation for CloudWatch Log Insights best practices and query examples:

**Load when**:
- Writing complex queries requiring optimization guidance
- Needing query pattern examples for specific use cases
- Requiring cost optimization strategies
- Seeking query syntax reference

**best-practices.md**: Query optimization techniques, time range selection guidance, log group strategies, and cost optimization tips.

**query-examples.md**: Common query patterns including error searches, latency analysis, statistical aggregations, field parsing, and multi-log group queries.

## Loading Reference Files

Load reference files based on the current task:

**Load `references/best-practices.md` when**:
- Optimizing query performance
- Selecting appropriate time ranges
- Planning cost-effective queries
- Structuring efficient queries

**Load `references/query-examples.md` when**:
- Writing queries for specific use cases (errors, latency, patterns)
- Needing examples of field extraction or parsing
- Creating statistical aggregations
- Working with multi-log group queries

Both reference files provide detailed guidance without cluttering this main skill document.
