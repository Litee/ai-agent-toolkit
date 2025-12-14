# CloudWatch Log Insights Best Practices

Comprehensive guide for optimizing CloudWatch Log Insights queries, managing costs, and improving query performance.

## Query Optimization Techniques

### 1. Filter Early and Often

Place filter conditions as early as possible in the query to reduce the amount of data processed:

**Good**:
```
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

**Bad**:
```
fields @timestamp, @message
| stats count() by bin(5m)
| filter @message like /ERROR/
```

The first example filters data before aggregation, reducing computation.

### 2. Use Specific Field Selections

Only select fields you actually need rather than using wildcards or selecting all fields:

**Good**:
```
fields @timestamp, requestId, duration, statusCode
| filter statusCode >= 400
```

**Bad**:
```
fields @*
| filter statusCode >= 400
```

Selecting specific fields reduces data transfer and improves performance.

### 3. Limit Result Sets Appropriately

Use the `limit` clause to cap result counts when you don't need all matching records:

```
fields @timestamp, @message
| filter level = "ERROR"
| limit 100
```

The default limit is 10,000, but setting a lower limit improves query speed.

### 4. Use Aggregations Over Large Result Sets

When analyzing trends or patterns, use aggregation functions rather than fetching all individual records:

**Good**:
```
stats count() as errorCount by bin(1h), errorType
| sort errorCount desc
```

**Bad**:
```
fields @timestamp, errorType
| filter level = "ERROR"
```

Aggregations are computed in CloudWatch and return compact results.

### 5. Optimize Regular Expressions

Use simple string matching when possible instead of complex regex patterns:

**Fast**:
```
filter @message like /ERROR/
```

**Slower**:
```
filter @message =~ /^.*ERROR.*$/
```

**Fastest (when exact match works)**:
```
filter level = "ERROR"
```

**Case-insensitive matching**:
```
filter @message like /(?i)error/  # Matches ERROR, Error, error, etc.
```

Use the `(?i)` flag for case-insensitive regex matching when log data has inconsistent casing.

### 6. Use Pattern Analysis for Root Cause Investigation

The `pattern` keyword automatically groups similar log entries, replacing variable fields with `<*>` placeholders:

**Good - Finding recurring errors**:
```
fields @timestamp, @message
| filter @message like /(?i)error/
| pattern @message
```

**Output fields generated**:
- `@pattern`: Shared text structure with `<*>` for variable parts (e.g., request IDs, timestamps)
- `@ratio`: Proportion of matching events (0.50 = 50% of filtered logs match this pattern)
- `@sampleCount`: Count of events matching this pattern
- `@severityLabel`: Log level classification (Error, Warning, Info, Debug)

**Benefits**:
- Reduces thousands of similar log lines into recognizable patterns
- Surfaces meaningful error messages by filtering out noise
- Accelerates root cause analysis during production incidents

### 7. Structure Queries for Time-Series Analysis

When analyzing trends over time, structure queries with proper binning:

**Good - Time-series with appropriate binning**:
```
filter @message like /ERROR/
| stats count() as errorCount by bin(5m)
| sort @timestamp desc
```

**Good - Composition analysis**:
```
stats count() as events by bin(15m), level
| sort @timestamp desc
```

**Best Practices**:
- Use appropriate time bins (5m, 15m, 1h) based on your time range
- Shorter time ranges (< 1 hour) → 1m or 5m bins
- Medium time ranges (1-24 hours) → 15m or 1h bins
- Longer time ranges (> 1 day) → 1h or 1d bins
- Always sort results for consistent output

## Time Range Selection Guidance

### Principle: Smaller is Better

Narrower time ranges improve query performance and reduce costs. Only query the time period you need.

### Recommended Time Ranges by Use Case

**Real-time Troubleshooting**: 15 minutes to 1 hour
```bash
--start-time '15m' --end-time 'now'
--start-time '1h' --end-time 'now'
```

**Recent Analysis**: 1-24 hours
```bash
--start-time 'last-hour'
--start-time 'last-24h'
```

**Daily Reports**: 24 hours (specific day)
```bash
--start-time '2025-12-05T00:00:00Z' --end-time '2025-12-06T00:00:00Z'
```

**Weekly Analysis**: 7 days maximum
```bash
--start-time 'last-week' --end-time 'now'
```

**Historical Investigation**: Use specific date ranges, not open-ended
```bash
--start-time '2025-11-01T00:00:00Z' --end-time '2025-11-30T23:59:59Z'
```

### Time Range Trade-offs

| Range | Speed | Cost | Use Case |
|-------|-------|------|----------|
| < 1 hour | Fast | Low | Real-time debugging |
| 1-6 hours | Medium | Low | Recent issue investigation |
| 6-24 hours | Medium | Medium | Daily analysis |
| 1-7 days | Slow | Medium-High | Weekly reports |
| > 7 days | Very Slow | High | Historical analysis (use carefully) |

### Avoid Open-Ended Ranges

Never query without an end time or with very large ranges unless absolutely necessary:

**Bad**:
```bash
--start-time '2024-01-01T00:00:00Z' --end-time 'now'  # Too broad!
```

**Good**:
```bash
--start-time '2025-12-05T00:00:00Z' --end-time '2025-12-06T00:00:00Z'
```

## Log Group Selection Strategies

### 1. Query the Minimum Number of Log Groups

Only include log groups that contain relevant data:

**Focused**:
```bash
--log-groups '/aws/lambda/payment-service'
```

**Too Broad**:
```bash
--log-groups '/aws/lambda/*'  # Queries ALL Lambda functions
```

### 2. Use Wildcards Strategically

Wildcards are powerful but can query more data than needed:

**Good - Specific prefix**:
```bash
--log-groups '/aws/lambda/prod-api-*'  # Only production API functions
```

**Less Efficient**:
```bash
--log-groups '/aws/lambda/prod-*'  # All production functions
```

### 3. CloudWatch Service Limits

CloudWatch Logs Insights has several important service limits to consider:

**Query Limits**:
- **Maximum 20 log groups per query**
  - The script automatically limits to first 20 if more are matched
  - Use specific patterns to stay under this limit
- **Maximum 10 concurrent queries per account** (includes dashboard queries)
  - If you hit this limit, wait for queries to complete or cancel unneeded queries
  - Consider scheduling queries to avoid concurrent execution

**Query Results**:
- Default limit: 10,000 records returned
- Use `limit` clause to reduce further
- Results cached for fast re-query within a time window

**Saved Queries**:
- **Maximum 1,000 saved queries per region per account**
- Each query can be up to 10,000 characters
- Regularly clean up unused queries to stay within limit

**Subscription Filters**:
- Maximum 2 subscription filters per log group
- Use for real-time streaming to Lambda, Kinesis, or Firehose

**Best Practices for Limits**:
- Monitor query usage across your team
- Cancel long-running queries that are no longer needed
- Use specific log group patterns to stay under 20 log groups
- Clean up saved queries periodically

### 4. Separate Queries for Different Services

When analyzing multiple unrelated services, run separate queries:

**Better**: Two separate queries
```bash
# Query 1: API logs
--log-groups '/aws/lambda/api-*'

# Query 2: Worker logs
--log-groups '/aws/lambda/worker-*'
```

**Worse**: Single large query
```bash
--log-groups '/aws/lambda/api-*,/aws/lambda/worker-*'
```

Separate queries are easier to optimize and understand.

## Cost Optimization Tips

### Understanding CloudWatch Costs

CloudWatch charges apply at multiple levels:

**Log Insights Query Charges**: $0.005 per GB of log data scanned
- Failed queries: Partial or no charges
- Manually cancelled queries: Only charged for data scanned before cancellation
- This encourages experimentation and query refinement

**Log Storage Classes**:
- **Standard class**: $0.50/GB ingested, $0.03/GB/month stored
  - Full feature access (subscription filters, Contributor Insights)
  - Best for frequently queried logs
- **Infrequent-Access class**: $0.285/GB ingested, $0.01/GB/month stored
  - Limited features (no subscription filters, query via Log Insights only)
  - Best for logs accessed less than once per month
  - Can reduce storage costs by ~50%

**Data Analysis**:
- CloudWatch Contributor Insights: $0.30 per GB analyzed

### 1. Reduce Data Scanned

The most effective cost optimization is scanning less data:

- Use narrower time ranges
- Query fewer log groups
- Filter early in queries
- Use specific field selections

### 2. Estimate Before Running

Before running expensive queries, estimate data volume:

**Check log group size**:
```bash
aws logs describe-log-groups \
  --log-group-name-prefix '/aws/lambda/' \
  --query 'logGroups[*].[logGroupName,storedBytes]'
```

**Calculate approximate cost**:
- Stored bytes ÷ 1,073,741,824 = GB
- GB × $0.005 = Cost per full scan

### 3. Cache and Reuse Results

For repetitive analysis:
- Save query results to files
- Reuse results for multiple analyses
- Build dashboards instead of repeated queries

### 4. Write Aggregation Queries for Large Datasets

When analyzing large datasets, use aggregation queries instead of fetching raw records:

**Inefficient** (returns thousands of records, processes all data):
```
fields @timestamp, @message, level, requestId
| filter level = "ERROR"
```

**Efficient** (returns compact summary, reduces data transfer):
```
filter level = "ERROR"
| stats count() as errorCount by bin(1h), requestId
| sort errorCount desc
```

The aggregated query processes the same data but returns far fewer records, reducing query time and data transfer costs.

## Query Syntax Reference

### Common Operations

#### Field Selection
```
fields @timestamp, @message, level
fields @timestamp, @message, user.id, user.name  # Nested fields
```

#### Filtering
```
filter level = "ERROR"
filter statusCode >= 400
filter @message like /timeout/
filter duration > 1000
filter ispresent(errorCode)  # Field exists
filter not ispresent(successCode)  # Field doesn't exist
```

#### Parsing
```
parse @message "[*] *" as level, msg
parse @message "duration: * ms" as duration
parse @message /(?<method>\w+) (?<path>\/\S+)/ as method, path
```

#### Statistics
```
stats count() by level
stats avg(duration) by bin(5m)
stats max(memory), min(memory), avg(memory)
stats count(*) as total, sum(bytes) as totalBytes
stats pct(duration, 50) as p50, pct(duration, 99) as p99
```

#### Sorting
```
sort @timestamp desc
sort duration desc
sort count() desc  # When using stats
```

#### Limiting
```
limit 100
```

### Advanced Patterns

#### Multiple Filters with AND/OR
```
fields @timestamp, @message
| filter (level = "ERROR" or level = "WARN")
    and service = "payment"
```

#### Conditional Aggregations
```
stats count() as total,
      count(level = "ERROR") as errors,
      count(level = "WARN") as warnings
by bin(5m)
```

#### Field Transformation
```
fields @timestamp, duration / 1000 as durationSeconds
| filter durationSeconds > 5
```

#### Nested Field Access
```
fields @timestamp, user.id, user.email, request.headers.userAgent
```

### Service-Specific Query Patterns

#### Lambda-Specific Patterns

**Find Expensive Invocations**:
```
filter @type = "REPORT"
| fields @requestId, @billedDuration
| sort @billedDuration desc
| limit 20
```

**Latency Percentiles**:
```
filter @type = "REPORT"
| stats avg(@duration) as avgDuration,
        pct(@duration, 50) as p50,
        pct(@duration, 95) as p95,
        pct(@duration, 99) as p99
  by bin(5m)
```

**Cold Start Analysis**:
```
filter @type = "REPORT"
| filter @message like /Init Duration/
| parse @message /Init Duration: (?<initDuration>[\d.]+) ms/
| stats count() as coldStarts,
        avg(initDuration) as avgInitMs,
        max(initDuration) as maxInitMs
```

**Cold Start Percentage Over Time**:
```
filter @type = "REPORT"
| stats sum(strcontains(@message, "Init Duration")) / count(*) * 100
  as coldStartPercentage,
  avg(@duration) as avgDuration
  by bin(5m)
```

**Memory Utilization Analysis**:
```
filter @type = "REPORT"
| stats max(@memorySize / 1048576) as provisionedMB,
        avg(@maxMemoryUsed / 1048576) as avgUsedMB,
        max(@maxMemoryUsed / 1048576) as peakUsedMB,
        provisionedMB - peakUsedMB as overProvisionedMB
```

**Detect Over-Provisioned Memory**:
```
filter @type = "REPORT"
| stats max(@memorySize / 1024 / 1024) as provisonedMemoryMB,
        min(@maxMemoryUsed / 1024 / 1024) as smallestMemoryRequestMB,
        avg(@maxMemoryUsed / 1024 / 1024) as avgMemoryUsedMB,
        max(@maxMemoryUsed / 1024 / 1024) as maxMemoryUsedMB,
        provisonedMemoryMB - maxMemoryUsedMB as overProvisionedMB
```

#### API Gateway Patterns

**Non-2xx Response Tracking**:
```
fields @timestamp, @message, @requestId, @duration, @xrayTraceId
| filter @message like /tatus: 4/ or @message like /tatus: 5/
| sort @timestamp desc
| limit 100
```

**Response Status Code Distribution**:
```
filter @message like /tatus:/
| parse @message /tatus: (?<statusCode>\d+)/
| stats count() as requestCount by statusCode
| sort requestCount desc
```

**Top Traffic Sources by IP**:
```
stats count() as requestCount by ip
| sort requestCount desc
| limit 10
```

**Latency Analysis by Endpoint**:
```
parse @message /(?<method>\w+) (?<path>\/\S+)/
| stats avg(@duration) as avgLatency,
        pct(@duration, 95) as p95Latency,
        count() as requests
  by method, path
| sort avgLatency desc
```

#### String Functions Reference

**strcontains**: Boolean check for substring
```
filter strcontains(@message, "ERROR")
| stats count() as errorCount
```

**strlen**: String length
```
fields @timestamp, @message, strlen(@message) as messageLength
| filter messageLength > 1000
```

**Using strcontains in aggregations**:
```
filter @type = "REPORT"
| stats count() as total,
        sum(strcontains(@message, "Init Duration")) as coldStarts,
        coldStarts / total * 100 as coldStartPercent
  by bin(1h)
```

## Performance Tuning

### Query Execution Patterns

**Pattern 1: Broad to Specific**
1. Start with a narrow time range and broad filter
2. Examine results
3. Refine filter to be more specific
4. Expand time range if needed

**Pattern 2: Sample Before Full Query**
1. Add `limit 10` to quickly see data format
2. Develop and test parsing/filtering logic
3. Remove limit for full query

**Pattern 3: Iterative Refinement**
1. Start with basic field selection and simple filter
2. Verify results match expectations
3. Add parsing, aggregations, or additional filters
4. Test each addition before proceeding

### Common Performance Issues

**Issue**: Query times out
**Solutions**:
- Reduce time range
- Add more specific filters
- Query fewer log groups
- Simplify regex patterns

**Issue**: Too many results returned
**Solutions**:
- Add filters to narrow results
- Use aggregations instead of raw records
- Reduce time range
- Add limit clause

**Issue**: Query returns no results
**Solutions**:
- Verify log group names are correct
- Check time range includes relevant data
- Verify filter conditions match actual log format
- Use `describe_log_groups` to confirm log group existence

## Common Anti-Patterns and Mistakes

Understanding what NOT to do is just as important as knowing best practices. Here are common mistakes to avoid:

### 1. Using Wrong Null Check Syntax

**Mistake**:
```
filter myField is not null  # WRONG - doesn't work as expected in CloudWatch Logs Insights
```

**Correct**:
```
filter myField != ''
filter ispresent(myField)
```

The `is not null` syntax doesn't work in CloudWatch Logs Insights. Use `!= ''` for empty string checks or `ispresent()` to verify field existence.

### 2. Not Filtering Before Aggregation

**Mistake** (processes all data before filtering):
```
fields @timestamp, @message
| stats count() by bin(5m)
| filter @message like /ERROR/  # Filter AFTER stats - inefficient!
```

**Correct** (filters first, reducing computation):
```
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

Always filter data as early as possible to reduce the amount of data processed by subsequent operations.

### 3. Overly Broad Regex Patterns

**Mistake**:
```
filter @message =~ /^.*ERROR.*$/  # Unnecessary anchors and wildcards
```

**Correct**:
```
filter @message like /ERROR/
```

Simple patterns are faster and more readable. Only use complex regex when necessary.

### 4. Querying All Fields When Not Needed

**Mistake**:
```
fields @*  # Selects everything - slow and expensive
```

**Correct**:
```
fields @timestamp, requestId, duration, statusCode  # Only what's needed
```

Selecting all fields with `@*` increases data transfer and processing time. Be explicit about which fields you need.

### 5. Missing Limit on Exploratory Queries

**Mistake** (may return 10,000 records):
```
fields @timestamp, @message
| filter level = "ERROR"
```

**Better** (test with small sample first):
```
fields @timestamp, @message
| filter level = "ERROR"
| limit 10
```

During exploration, use `limit` to quickly verify your query works before processing large result sets.

### 6. Inconsistent Naming in Filters

**Mistake**: Using case-sensitive filters on inconsistent log data:
```
filter level = "ERROR"  # Misses "Error", "error", "ERR"
```

**Correct**: Use case-insensitive patterns:
```
filter @message like /(?i)error/
```

Log data often has inconsistent casing. Use case-insensitive regex patterns with `(?i)` when needed.

### 7. Querying Too Many Log Groups

**Mistake**:
```bash
--log-groups '/aws/lambda/*'  # Queries ALL Lambda functions!
```

**Correct**:
```bash
--log-groups '/aws/lambda/prod-api-*'  # Specific prefix
```

Broad wildcards scan more data than necessary, increasing costs and query time. Be as specific as possible.

### 8. Not Using Aggregations for Large Datasets

**Mistake** (returns thousands of raw records):
```
fields @timestamp, errorType
| filter level = "ERROR"
```

**Correct** (returns compact summary):
```
stats count() as errorCount by errorType
| sort errorCount desc
```

When analyzing patterns or trends, aggregations return compact, actionable results instead of overwhelming raw data.

### 9. Ignoring Query Timeout Warnings

**Mistake**: Running the same slow query repeatedly without optimization.

**Correct**: If a query times out:
- Reduce the time range significantly
- Add more specific filters
- Query fewer log groups
- Break into smaller time chunks
- Simplify complex regex patterns

### 10. Forgetting to Account for Failed Queries in Cost Estimates

**Good News**: Failed queries in CloudWatch Logs Insights incur partial or no charges. Manually cancelled queries only charge for data scanned up to the cancellation point. This encourages experimentation and query refinement.

## Error Troubleshooting

### Log Group Not Found

**Error**: `ResourceNotFoundException: Log group not found`

**Causes**:
- Typo in log group name
- Log group doesn't exist in specified region
- Insufficient IAM permissions

**Solutions**:
- Verify log group name exactly matches
- Check correct AWS region is specified
- Confirm IAM permissions include `logs:DescribeLogGroups` and `logs:StartQuery`

### Malformed Query

**Error**: `MalformedQueryException` or `InvalidParameterException`

**Common Causes**:
- Missing pipe `|` between operations
- Invalid field names (typos or wrong format)
- Incorrect aggregation syntax
- Unterminated strings or regex patterns

**Solutions**:
- Check query syntax carefully
- Test with simpler query first
- Verify field names exist in logs
- Use query examples as templates

### Rate Limiting

**Error**: `LimitExceededException`

**Causes**:
- Too many concurrent queries
- Query rate exceeds service limits

**Solutions**:
- Wait and retry
- Reduce concurrent query count
- Implement exponential backoff
- Contact AWS support to request limit increase

### Query Timeout

**Error**: Query status shows `Timeout`

**Causes**:
- Query too complex for time range
- Too much data being scanned
- Very large log groups

**Solutions**:
- Reduce time range significantly
- Add more specific filters
- Query fewer log groups
- Break query into smaller time chunks

## Security and Access Control

### IAM Permissions Required

Minimum permissions for querying:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:GetQueryResults",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

### Restrict Log Group Access

Limit access to specific log groups:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:StartQuery",
        "logs:GetQueryResults"
      ],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/prod-*"
    }
  ]
}
```

### Data Sensitivity

**Remember**:
- CloudWatch Logs may contain sensitive data (PII, credentials, etc.)
- Query results inherit sensitivity of source logs
- Use appropriate file permissions when saving results
- Consider data retention policies when storing results

## Monitoring and Alerting

### When to Use Queries vs. Metric Filters vs. Alarms

**Use Queries for**:
- Ad-hoc investigation
- Historical analysis
- Complex pattern detection
- Data export and reporting

**Use Metric Filters for**:
- Real-time metric extraction
- Cost-effective monitoring
- Simple pattern counting
- Dashboard metrics

**Use CloudWatch Alarms for**:
- Automated alerting
- Threshold-based notifications
- Proactive monitoring
- Incident response triggers

### Best Practice: Combine All Three

1. **Metric Filters**: Extract key metrics continuously (e.g., error count, latency)
2. **Alarms**: Alert on metric threshold violations
3. **Queries**: Investigate when alarms trigger, perform deep analysis

This approach balances cost, responsiveness, and investigative capability.
