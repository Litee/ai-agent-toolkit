# CloudWatch Log Insights Query Examples

Comprehensive collection of query patterns for common use cases including error analysis, performance monitoring, security investigation, and operational insights.

## Error Detection and Analysis

### Find All Errors in Time Range

```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

**Usage**:
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @message | filter @message like /ERROR/' \
  --log-groups '/aws/lambda/my-function' \
  --start-time '1h' \
  --format csv
```

### Count Errors by Type

```
fields @timestamp, @message
| filter level = "ERROR"
| parse @message "*Exception: *" as errorType, errorMsg
| stats count() as errorCount by errorType
| sort errorCount desc
```

### Errors with Stack Traces

```
fields @timestamp, @message, @logStream
| filter @message like /ERROR/
| filter @message like /at /
| limit 50
```

### Error Rate Over Time

```
filter level = "ERROR"
| stats count() as errors by bin(5m)
| sort bin(5m) desc
```

**Use for**: Creating error trend visualizations, identifying error spikes.

## Performance and Latency Analysis

### Find Slow Requests (Duration > Threshold)

```
fields @timestamp, requestId, duration, path
| filter duration > 1000
| sort duration desc
| limit 100
```

**For Lambda functions**:
```
fields @timestamp, @message
| filter @type = "REPORT"
| parse @message "Duration: * ms" as duration
| filter duration > 3000
| stats count() as slowRequests
```

### Calculate Percentiles

```
filter @type = "REPORT"
| parse @message "Duration: * ms" as duration
| stats pct(duration, 50) as p50,
        pct(duration, 90) as p90,
        pct(duration, 95) as p95,
        pct(duration, 99) as p99
```

**Usage**:
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'filter @type = "REPORT" | parse @message "Duration: * ms" as duration | stats pct(duration, 50) as p50, pct(duration, 99) as p99' \
  --log-groups '/aws/lambda/api-function' \
  --start-time 'last-24h' \
  --format json
```

### Average Response Time by Endpoint

```
fields @timestamp, path, duration
| stats avg(duration) as avgDuration,
        max(duration) as maxDuration,
        count() as requestCount
by path
| sort avgDuration desc
```

### Memory Usage Analysis (Lambda)

```
filter @type = "REPORT"
| parse @message "Max Memory Used: * MB" as memUsed
| stats avg(memUsed) as avgMem,
        max(memUsed) as maxMem,
        min(memUsed) as minMem
```

## Request and Traffic Analysis

### Count Requests by HTTP Status Code

```
fields @timestamp, status
| stats count() as requests by status
| sort requests desc
```

### 4xx and 5xx Error Analysis

```
fields @timestamp, status, path, method
| filter status >= 400
| stats count() as errorCount by status, path
| sort errorCount desc
```

### Top 10 Most Frequently Accessed Endpoints

```
fields @timestamp, path, method
| stats count() as hits by path, method
| sort hits desc
| limit 10
```

### Requests by User Agent

```
fields @timestamp, userAgent
| stats count() as requests by userAgent
| sort requests desc
| limit 20
```

### Traffic Over Time (5-minute bins)

```
stats count() as requests by bin(5m)
| sort bin(5m) asc
```

## Security and Access Monitoring

### Failed Authentication Attempts

```
fields @timestamp, @message, srcIp, username
| filter @message like /authentication failed/
    or @message like /invalid credentials/
    or @message like /login failed/
| stats count() as attempts by srcIp, username
| sort attempts desc
```

**Usage**:
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @message, srcIp | filter @message like /failed/ | stats count() by srcIp | sort count() desc' \
  --log-groups '/aws/ecs/auth-service' \
  --start-time 'last-hour' \
  --format table
```

### Identify Potential Brute Force Attacks

```
fields @timestamp, srcIp, username
| filter @message like /login failed/
| stats count() as failedAttempts by srcIp
| filter failedAttempts > 10
| sort failedAttempts desc
```

### Track Admin Actions

```
fields @timestamp, username, action, resource
| filter userRole = "admin"
| sort @timestamp desc
```

### Unauthorized Access Attempts (403)

```
fields @timestamp, status, path, srcIp, method
| filter status = 403
| stats count() as denials by srcIp, path
| sort denials desc
```

### Detect SQL Injection Attempts

```
fields @timestamp, @message, path, srcIp
| filter @message like /SELECT.*FROM/
    or @message like /UNION.*SELECT/
    or @message like /DROP TABLE/
| sort @timestamp desc
```

## Application-Specific Patterns

### Lambda Cold Starts

```
filter @type = "REPORT"
| filter @message like /Init Duration/
| parse @message "Init Duration: * ms" as initDuration
| stats count() as coldStarts,
        avg(initDuration) as avgInitDuration
by bin(1h)
```

### Lambda Function Errors

```
filter @type = "ERROR"
| fields @timestamp, @message, @logStream
| sort @timestamp desc
| limit 100
```

### ECS Task Health

```
fields @timestamp, taskId, status, healthStatus
| filter healthStatus != "HEALTHY"
| stats count() by taskId, healthStatus
```

### API Gateway Requests

```
fields @timestamp, requestId, status, ip, path
| filter path like /\/api\/v1\//
| stats count() as requests,
        avg(responseTime) as avgResponseTime
by path
| sort requests desc
```

## Field Extraction and Parsing

### Extract JSON Fields

```
fields @timestamp, @message
| parse @message /\{.*\}/ as jsonPayload
| parse jsonPayload '"userId":"*"' as userId
| parse jsonPayload '"action":"*"' as action
| stats count() by userId, action
```

### Parse Custom Log Format

```
parse @message "[*] [*] *" as timestamp, level, message
| filter level = "ERROR" or level = "WARN"
| stats count() by level
```

### Extract Key-Value Pairs

```
parse @message "user=*, action=*, status=*" as user, action, status
| filter status = "failed"
| stats count() by user, action
```

### Parse Multiple Patterns

```
fields @timestamp, @message
| parse @message "Error: * at line *" as errorMsg, lineNum
  or @message "Exception: *" as errorMsg
| filter ispresent(errorMsg)
```

## Structured Logging Queries

### Query JSON Logs

```
fields @timestamp, level, message, userId, requestId, duration
| filter level = "ERROR"
| sort @timestamp desc
```

### Nested Field Access

```
fields @timestamp, user.id, user.email, request.method, request.path
| filter request.method = "POST"
| stats count() by user.email
```

### Filter by Nested Field

```
fields @timestamp, @message, metadata.service, metadata.environment
| filter metadata.environment = "production"
    and metadata.service = "payment"
```

## Statistical Aggregations

### Multiple Aggregations

```
stats count() as total,
      count(level = "ERROR") as errors,
      count(level = "WARN") as warnings,
      count(level = "INFO") as info
by bin(10m)
```

### Conditional Counting

```
stats count() as totalRequests,
      count(duration > 1000) as slowRequests,
      count(status >= 400) as errorRequests
by bin(5m)
```

### Ratio Calculations

```
stats count() as total,
      count(status >= 400) as errors
| fields total, errors, errors * 100.0 / total as errorRate
```

### Min, Max, Average

```
fields duration, memory, cpuUsage
| stats min(duration) as minDuration,
        max(duration) as maxDuration,
        avg(duration) as avgDuration,
        avg(memory) as avgMemory,
        max(cpuUsage) as maxCpu
by bin(15m)
```

## Multi-Log Group Queries

### Aggregate Across Multiple Services

```
fields @timestamp, @log, level
| filter level = "ERROR"
| stats count() as errors by @log
| sort errors desc
```

**Usage**:
```bash
./scripts/query_cloudwatch_logs.py \
  --query 'fields @timestamp, @log | filter @message like /ERROR/ | stats count() by @log' \
  --log-groups '/aws/lambda/service-a,/aws/lambda/service-b,/aws/lambda/service-c' \
  --start-time '1h' \
  --format csv
```

### Compare Performance Across Functions

```
filter @type = "REPORT"
| parse @message "Duration: * ms" as duration
| stats avg(duration) as avgDuration,
        count() as invocations
by @log
| sort avgDuration desc
```

### Error Distribution Across Services

```
fields @timestamp, @log, @message
| filter level = "ERROR"
| parse @message "*Exception" as exceptionType
| stats count() as errorCount by @log, exceptionType
| sort errorCount desc
```

## Time-Series Analysis

### Hourly Request Volume

```
stats count() as requests by bin(1h)
| sort bin(1h) asc
```

### Daily Active Users

```
fields @timestamp, userId
| stats count_distinct(userId) as activeUsers by bin(1d)
```

### Compare Current vs Previous Period

```
fields @timestamp, requestId
| stats count() as currentRequests by bin(1h)
| sort bin(1h) asc
```

Run twice with different time ranges and compare results.

### Detect Anomalies (Spike Detection)

```
stats count() as requests by bin(5m)
| sort bin(5m) asc
```

Export and analyze for values > 2 standard deviations from mean.

## Debugging and Troubleshooting

### Trace Specific Request ID

```
fields @timestamp, @message, @logStream
| filter requestId = "abc123-def456-ghi789"
| sort @timestamp asc
```

### Find Correlation Between Events

```
fields @timestamp, @message, requestId, userId
| filter userId = "user123"
| filter @timestamp >= 1733395200000 and @timestamp <= 1733398800000
| sort @timestamp asc
```

### Identify Timeout Events

```
fields @timestamp, @message, requestId, duration
| filter @message like /timeout/
    or @message like /timed out/
    or duration > 30000
| sort @timestamp desc
```

### Database Query Failures

```
fields @timestamp, @message, queryType, errorCode
| filter @message like /database/ and @message like /error/
| parse @message "Query: *" as query
| stats count() by errorCode, queryType
```

## Business Metrics

### Transaction Volume

```
fields @timestamp, transactionType, amount
| filter transactionType = "payment"
| stats count() as transactions,
        sum(amount) as totalAmount
by bin(1h)
```

### Successful vs Failed Transactions

```
fields @timestamp, transactionId, status
| stats count(status = "success") as successful,
        count(status = "failed") as failed,
        count() as total
by bin(10m)
```

### User Actions

```
fields @timestamp, userId, action
| filter action in ["login", "purchase", "logout"]
| stats count() as actionCount by action, bin(1h)
```

### Conversion Funnel

```
fields @timestamp, userId, event
| filter event in ["viewed_product", "added_to_cart", "completed_purchase"]
| stats count_distinct(userId) by event
```

## Advanced Patterns

### Windowed Aggregations

```
fields @timestamp, metric
| stats avg(metric) as avgMetric by bin(5m)
| sort bin(5m) asc
```

### Combine Multiple Filters

```
fields @timestamp, @message, level, service, environment
| filter (level = "ERROR" or level = "CRITICAL")
    and environment = "production"
    and service in ["api", "worker", "scheduler"]
| stats count() by service, level
```

### Coalesce Missing Fields

```
fields @timestamp,
       coalesce(requestId, "-") as reqId,
       coalesce(userId, "anonymous") as user
| stats count() by user
```

### Dynamic Field Selection

```
fields @timestamp, @message
| parse @message '"level":"*"' as level
| parse @message '"message":"*"' as msg
| filter ispresent(level) and level in ["ERROR", "WARN"]
```

## Template Queries for Common Scenarios

### Daily Error Report

```
filter level = "ERROR"
| stats count() as errorCount,
        count_distinct(@logStream) as affectedStreams
by bin(1h), errorType
| sort bin(1h) asc
```

### Slow Query Report

```
fields @timestamp, query, duration
| filter duration > 1000
| stats count() as slowQueries,
        avg(duration) as avgDuration,
        max(duration) as maxDuration
by query
| sort slowQueries desc
| limit 20
```

### Security Audit Log

```
fields @timestamp, userId, action, resource, srcIp
| filter action in ["create", "update", "delete"]
    and resource like /sensitive/
| sort @timestamp desc
```

### Performance Dashboard Query

```
filter @type = "REPORT"
| parse @message "Duration: * ms" as duration
| parse @message "Memory Size: * MB" as memSize
| stats avg(duration) as avgDuration,
        pct(duration, 99) as p99Duration,
        avg(memSize) as avgMemory,
        count() as invocations
by bin(5m)
```

## Query Optimization Examples

### Before Optimization

```
fields @timestamp, @message, level, requestId, userId, path
| stats count() by path
| filter level = "ERROR"
```

### After Optimization

```
filter level = "ERROR"
| stats count() by path
```

**Improvement**: Filter early, select only needed fields, reduce data scanned.

### Complex Pattern - Before

```
fields @timestamp, @message
| parse @message /(\d{4}-\d{2}-\d{2}).*ERROR.*user:(\d+)/ as date, userId
| stats count() by userId
```

### Complex Pattern - After

```
fields @timestamp, @message
| filter @message like /ERROR/
| parse @message "user:*" as userId
| stats count() by userId
```

**Improvement**: Simple string match before complex parsing, simpler regex.

## Usage Tips

### Testing Queries

Start with a short time range and `limit 10` to test query logic:
```
fields @timestamp, @message
| filter @message like /ERROR/
| limit 10
```

Once verified, remove limit and expand time range.

### Incremental Development

Build queries incrementally:

1. **Step 1**: Select fields
   ```
   fields @timestamp, @message
   ```

2. **Step 2**: Add filter
   ```
   fields @timestamp, @message
   | filter level = "ERROR"
   ```

3. **Step 3**: Add parsing
   ```
   fields @timestamp, @message
   | filter level = "ERROR"
   | parse @message "*Exception: *" as errorType, errorMsg
   ```

4. **Step 4**: Add aggregation
   ```
   fields @timestamp, @message
   | filter level = "ERROR"
   | parse @message "*Exception: *" as errorType, errorMsg
   | stats count() by errorType
   ```

### Saving Complex Queries

Save complex queries to files for reuse:

**File: `error_analysis.txt`**
```
fields @timestamp, @message, level, requestId
| filter level = "ERROR"
| parse @message '"errorCode":"*"' as errorCode
| parse @message '"message":"*"' as errorMsg
| stats count() as errorCount by errorCode
| sort errorCount desc
```

**Usage**:
```bash
./scripts/query_cloudwatch_logs.py \
  --query-file 'error_analysis.txt' \
  --log-groups '/aws/lambda/my-function' \
  --start-time 'last-24h' \
  --format csv
```
