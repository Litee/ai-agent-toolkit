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

### 3. CloudWatch Limits

- Maximum 20 log groups per query
- The script automatically limits to first 20 if more are matched
- Use specific patterns to stay under this limit

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

CloudWatch Log Insights charges $0.005 per GB of log data scanned.

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

### 4. Use CloudWatch Alarms for Monitoring

Instead of periodic queries, set up CloudWatch Alarms with metric filters for automatic monitoring. This is more cost-effective for continuous monitoring.

### 5. Aggregate Before Exporting

When exporting data, aggregate first to reduce data volume:

**Expensive**:
```
fields @timestamp, @message, level, requestId
```

**More Efficient**:
```
stats count() by bin(1h), level
```

The aggregated version returns much less data.

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
