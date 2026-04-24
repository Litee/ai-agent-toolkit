---
name: use-aws-cloudwatch-metrics
description: "Use when publishing, querying, designing, or troubleshooting Amazon CloudWatch custom metrics. Triggers on PutMetricData, GetMetricData, EMF, CloudWatch alarms, metric math, dimension cardinality, high-resolution metrics, metric streams, Contributor Insights, CloudWatch cost optimization, PutMetricData throttling, M-of-N alarms, missing data treatment, or CloudWatch agent StatsD. For log analysis, use aws-cloudwatch:query-aws-cloudwatch-logs-insights."
---

# Use AWS CloudWatch Metrics

Best practices and anti-patterns for publishing, querying, and designing monitoring with Amazon CloudWatch custom metrics. Apply these before writing any code that touches CloudWatch metrics.

**Scope:** This skill covers CloudWatch *metrics* only — namespaces, dimensions, PutMetricData, GetMetricData, EMF, alarms, metric math. For log analysis (CloudWatch Logs Insights), use the `query-aws-cloudwatch-logs-insights` skill instead.

---

## Anti-Patterns

### 1. Unbounded dimension cardinality — the silent cost explosion

Each unique combination of dimension values creates a separate, billable metric ($0.30/metric/month). Using high-cardinality values such as `RequestId`, `UserId`, `SessionId`, or `TraceId` as dimensions causes a combinatorial explosion of metrics.

**What NOT to do:**

```python
# BAD: Each unique requestId = 1 new billable metric forever
cloudwatch.put_metric_data(
    Namespace='MyService',
    MetricData=[{
        'MetricName': 'Latency',
        'Value': 120.5,
        'Unit': 'Milliseconds',
        'Dimensions': [
            {'Name': 'RequestId', 'Value': request_id},  # NEVER do this
            {'Name': 'UserId',    'Value': user_id},     # NEVER do this
        ]
    }]
)
```

**Fix:** Dimensions must be low-cardinality, stable, and meaningful for aggregation. Good choices: `Environment`, `Region`, `ServiceName`, `Operation`, `StatusCode`, `InstanceType`.

```python
# GOOD: fixed set of dimensions — predictable metric count
cloudwatch.put_metric_data(
    Namespace='MyService',
    MetricData=[{
        'MetricName': 'Latency',
        'Value': 120.5,
        'Unit': 'Milliseconds',
        'Dimensions': [
            {'Name': 'Environment', 'Value': 'prod'},
            {'Name': 'Operation',   'Value': 'GetUser'},
        ]
    }]
)
```

Rule of thumb: each dimension should have fewer than ~20 distinct values. If you need per-request tracing, use AWS X-Ray, not CloudWatch metrics.

---

### 2. Calling PutMetricData in a tight loop — throttling and cost waste

PutMetricData has a default limit of 500 TPS and charges per API request. Calling it once per event (e.g., on every Lambda invocation or every HTTP request) burns through quota and money.

**What NOT to do:**

```python
# BAD: one PutMetricData call per processed record
for record in records:
    process(record)
    cloudwatch.put_metric_data(
        Namespace='MyService',
        MetricData=[{'MetricName': 'ProcessedCount', 'Value': 1, ...}]
    )
```

**Fix — option A: batch up to 1,000 metrics per call:**

```python
import boto3
from typing import List

cloudwatch = boto3.client('cloudwatch')
BATCH_SIZE = 1000

def flush_metrics(batch: List[dict]) -> None:
    for i in range(0, len(batch), BATCH_SIZE):
        cloudwatch.put_metric_data(
            Namespace='MyService',
            MetricData=batch[i:i + BATCH_SIZE]
        )

metric_buffer = []
for record in records:
    process(record)
    metric_buffer.append({'MetricName': 'ProcessedCount', 'Value': 1,
                          'Unit': 'Count', 'StorageResolution': 60})

flush_metrics(metric_buffer)
```

**Fix — option B: use statistic sets to pre-aggregate at the source (cheapest):**

```python
import time

# Accumulate in-process, then emit one data point per minute
counters = {'success': 0, 'error': 0, 'latency_sum': 0.0, 'latency_count': 0,
            'latency_min': float('inf'), 'latency_max': 0.0}

def record_latency(ms: float, ok: bool) -> None:
    if ok:
        counters['success'] += 1
    else:
        counters['error'] += 1
    counters['latency_sum'] += ms
    counters['latency_count'] += 1
    counters['latency_min'] = min(counters['latency_min'], ms)
    counters['latency_max'] = max(counters['latency_max'], ms)

def emit_stats() -> None:
    n = counters['latency_count']
    if n == 0:
        return
    cloudwatch.put_metric_data(
        Namespace='MyService',
        MetricData=[
            {
                'MetricName': 'Latency',
                'Unit': 'Milliseconds',
                'StatisticValues': {
                    'SampleCount': n,
                    'Sum':         counters['latency_sum'],
                    'Minimum':     counters['latency_min'],
                    'Maximum':     counters['latency_max'],
                },
                'Dimensions': [{'Name': 'Environment', 'Value': 'prod'}],
            },
            {
                'MetricName': 'SuccessCount',
                'Value': counters['success'],
                'Unit': 'Count',
            },
        ]
    )
    counters.update({'success': 0, 'error': 0, 'latency_sum': 0.0,
                     'latency_count': 0, 'latency_min': float('inf'), 'latency_max': 0.0})
```

Note: statistic sets cannot produce percentile statistics. If you need p99, you must publish individual data points (up to 150 values per metric datum via the `Values`/`Counts` fields).

---

### 3. Using high-resolution metrics (StorageResolution=1) when you don't need sub-minute granularity

High-resolution metrics cost the same per API call but are billed as custom metrics at the same rate. The real cost is operational: high-resolution alarms (10s or 30s periods) incur higher charges than standard 60-second alarms. High-resolution data also retains only 3 hours at 1-second granularity before rolling up.

**What NOT to do:**

```python
# BAD: blindly using StorageResolution=1 for a metric checked once per hour
{
    'MetricName': 'DailyActiveUsers',
    'Value': 42000,
    'StorageResolution': 1,  # pointless — you'll never query at 1-second granularity
}
```

**Fix:** Use `StorageResolution=60` (or omit it — 60 is the default) unless you genuinely need sub-minute alarm sensitivity.

```python
# GOOD: only use StorageResolution=1 for latency-sensitive alerting
{
    'MetricName': 'P99Latency',
    'Value': response_time_ms,
    'Unit': 'Milliseconds',
    'StorageResolution': 1,  # justified: need 10s alarms to catch latency spikes fast
}
```

---

### 4. Using GetMetricStatistics for bulk or multi-metric queries

`GetMetricStatistics` is the legacy, single-metric API. It returns at most 1,440 data points per request and cannot do metric math. Using it in a loop to retrieve multiple metrics is expensive in API calls and slow.

**What NOT to do:**

```bash
# BAD: loop calling GetMetricStatistics per metric
for metric in ErrorCount SuccessCount Latency; do
  aws cloudwatch get-metric-statistics \
    --namespace MyService \
    --metric-name "$metric" \
    --start-time 2024-01-01T00:00:00Z \
    --end-time   2024-01-02T00:00:00Z \
    --period 300 \
    --statistics Sum Average
done
```

**Fix:** Use `GetMetricData` — it fetches up to 500 metrics in a single API call and supports metric math:

```bash
aws cloudwatch get-metric-data \
  --start-time 2024-01-01T00:00:00Z \
  --end-time   2024-01-02T00:00:00Z \
  --metric-data-queries '[
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {"Namespace":"MyService","MetricName":"ErrorCount"},
        "Period": 300, "Stat": "Sum"
      }
    },
    {
      "Id": "requests",
      "MetricStat": {
        "Metric": {"Namespace":"MyService","MetricName":"RequestCount"},
        "Period": 300, "Stat": "Sum"
      }
    },
    {
      "Id": "error_rate",
      "Expression": "errors / requests * 100",
      "Label": "ErrorRate%",
      "ReturnData": true
    }
  ]'
```

```python
# Python equivalent
import boto3

cloudwatch = boto3.client('cloudwatch')

response = cloudwatch.get_metric_data(
    StartTime='2024-01-01T00:00:00Z',
    EndTime='2024-01-02T00:00:00Z',
    MetricDataQueries=[
        {
            'Id': 'errors',
            'MetricStat': {
                'Metric': {'Namespace': 'MyService', 'MetricName': 'ErrorCount'},
                'Period': 300,
                'Stat': 'Sum',
            },
            'ReturnData': False,  # intermediate — hide from response
        },
        {
            'Id': 'requests',
            'MetricStat': {
                'Metric': {'Namespace': 'MyService', 'MetricName': 'RequestCount'},
                'Period': 300,
                'Stat': 'Sum',
            },
            'ReturnData': False,
        },
        {
            'Id': 'error_rate',
            'Expression': 'errors / requests * 100',
            'Label': 'ErrorRate%',
            'ReturnData': True,
        },
    ],
)

# Handle pagination
while 'NextToken' in response:
    response = cloudwatch.get_metric_data(
        StartTime='2024-01-01T00:00:00Z',
        EndTime='2024-01-02T00:00:00Z',
        MetricDataQueries=[...],
        NextToken=response['NextToken'],
    )
```

---

### 5. Wrong missing-data treatment on alarms — false positives or silent failures

CloudWatch alarms have four missing-data treatments. Choosing the wrong one is a common source of both false alarms and missed failures.

**What NOT to do:**

```python
# BAD: using 'breaching' for a metric that only reports when errors happen
# (e.g., ThrottledRequests — no data means no throttling, not "everything is on fire")
cloudwatch.put_metric_alarm(
    AlarmName='ThrottleAlert',
    MetricName='ThrottledRequests',
    Namespace='AWS/DynamoDB',
    TreatMissingData='breaching',  # WRONG: missing = no throttles, not a fire
    ...
)
```

**Fix — choose based on what absence of data means:**

| Scenario | Correct treatment | Rationale |
|---|---|---|
| Metric only emitted on errors (ThrottledRequests, DLQ depth) | `notBreaching` | No data = no errors |
| Health-check metric that should always report | `breaching` | No data = service is down |
| Alarm on instance that gets stopped/terminated | `missing` | Absence is expected; don't false-alarm |
| You need alarm state to hold steady during gaps | `ignore` | Prevents transient state flap |

```python
# CORRECT: ThrottledRequests only exists when there are throttles
cloudwatch.put_metric_alarm(
    AlarmName='DynamoDBThrottleAlert',
    MetricName='ThrottledRequests',
    Namespace='AWS/DynamoDB',
    Statistic='Sum',
    Period=60,
    EvaluationPeriods=3,
    DatapointsToAlarm=2,       # M-of-N: 2 out of 3 periods must breach
    Threshold=10,
    ComparisonOperator='GreaterThanThreshold',
    TreatMissingData='notBreaching',   # CORRECT
    Dimensions=[{'Name': 'TableName', 'Value': 'my-table'}],
)
```

---

### 6. Not using M-of-N evaluation — single transient spike triggers alarm

An alarm that evaluates `1 out of 1` period fires on any single data point exceeding the threshold. One network blip or one slow Lambda cold start triggers a page at 2 AM.

**What NOT to do:**

```python
# BAD: fires on a single data point — too noisy
cloudwatch.put_metric_alarm(
    AlarmName='LambdaErrorRate',
    EvaluationPeriods=1,    # only 1 period evaluated
    DatapointsToAlarm=1,    # alarm on 1 out of 1 — any single spike
    ...
)
```

**Fix:** Use M-of-N (DatapointsToAlarm < EvaluationPeriods) for sustained-problem detection:

```python
# GOOD: 3-out-of-5 — sustained errors, not a one-off spike
cloudwatch.put_metric_alarm(
    AlarmName='LambdaErrorRate',
    MetricName='Errors',
    Namespace='AWS/Lambda',
    Statistic='Sum',
    Period=60,
    EvaluationPeriods=5,     # look at last 5 periods (5 minutes)
    DatapointsToAlarm=3,     # alarm only if 3 of those 5 periods breach
    Threshold=5,
    ComparisonOperator='GreaterThanThreshold',
    TreatMissingData='notBreaching',
    Dimensions=[{'Name': 'FunctionName', 'Value': 'my-function'}],
)
```

---

### 7. Publishing metrics without a Unit — breaks percentile statistics

When you publish a metric without specifying `Unit`, CloudWatch stores it as `None`. If you later publish the same metric with a unit (e.g., `Milliseconds`), CloudWatch treats them as different data streams — your aggregations and percentiles will be silently wrong.

**What NOT to do:**

```python
# BAD: omitting Unit
{'MetricName': 'ResponseTime', 'Value': 150}
```

**Fix:** Always specify `Unit`:

```python
{'MetricName': 'ResponseTime', 'Value': 150, 'Unit': 'Milliseconds'}
```

Valid units: `Seconds`, `Microseconds`, `Milliseconds`, `Bytes`, `Kilobytes`, `Megabytes`, `Gigabytes`, `Terabytes`, `Bits`, `Kilobits`, `Megabits`, `Gigabits`, `Terabits`, `Percent`, `Count`, `Bytes/Second`, `Kilobytes/Second`, `Megabytes/Second`, `Gigabytes/Second`, `Terabytes/Second`, `Bits/Second`, `Kilobits/Second`, `Megabits/Second`, `Gigabits/Second`, `Terabits/Second`, `Count/Second`, `None`.

---

### 8. Using SEARCH() or FILL() in metric math alarms

`SEARCH()` returns an array of time series that can change over time — an alarm based on it may be monitoring different metrics month to month. `FILL()` can cause alarms to get stuck in ALARM or OK state when the underlying metric is published with delay. Neither is safe in alarm expressions.

**What NOT to do:**

```
# BAD: alarm on a SEARCH expression
SEARCH('{MyService} MetricName="ErrorRate"', 'Average')
```

**Fix:** Always reference explicit, stable metric IDs in alarm expressions. If you need to alarm on a sum across multiple instances, create a composite alarm or an explicit metric math expression referencing fixed `MetricStat` entries.

---

## Best Practices

### 1. Design namespaces and dimensions before writing code

Namespace and dimension design is permanent — changing them creates new metrics that lose all historical data.

**Namespace design rules:**
- Use `CompanyName/ServiceName` or `Product/Component` format (e.g., `MyOrg/PaymentService`). Never use the `AWS/` prefix — that is reserved.
- One namespace per service or team. Do not put all custom metrics in one monolithic namespace.
- Max 255 characters; allowed: alphanumeric, `.`, `-`, `_`, `/`, `#`, `:`, space.

**Dimension design rules:**
- Every dimension must be low-cardinality (< ~20 distinct values).
- Dimensions on the same metric must always be published together — partial dimension sets result in distinct, separate metrics.
- Use consistent casing across all publishers (e.g., always `Environment`, never sometimes `Env`).
- Suggested standard dimensions: `Environment` (prod/staging/dev), `Region`, `ServiceName`, `Operation`, `StatusCode`.

```python
# Template for consistent metric publication
STANDARD_DIMS = [
    {'Name': 'Environment', 'Value': 'prod'},
    {'Name': 'ServiceName', 'Value': 'payment-service'},
]

def make_metric(name: str, value: float, unit: str, extra_dims: list = None) -> dict:
    return {
        'MetricName': name,
        'Value': value,
        'Unit': unit,
        'StorageResolution': 60,
        'Dimensions': STANDARD_DIMS + (extra_dims or []),
    }
```

---

### 2. Use EMF (Embedded Metric Format) for Lambda and containerised services

EMF lets you emit metrics by writing structured JSON to stdout/stderr. No `PutMetricData` API calls, no SDK dependency for the metric path, no throttling risk. CloudWatch extracts metrics asynchronously from the logs.

**Lambda (no agent needed — Lambda flushes stdout to CloudWatch Logs automatically):**

```python
import json, time

def emit_emf(namespace: str, metrics: dict, dimensions: dict,
             storage_resolution: int = 60) -> None:
    """Write a single EMF log line to stdout."""
    metric_definitions = [
        {'Name': k, 'Unit': v['unit'], 'StorageResolution': storage_resolution}
        for k, v in metrics.items()
    ]
    payload = {
        '_aws': {
            'Timestamp': int(time.time() * 1000),
            'CloudWatchMetrics': [{
                'Namespace': namespace,
                'Dimensions': [list(dimensions.keys())],
                'Metrics': metric_definitions,
            }],
        },
        **dimensions,
        **{k: v['value'] for k, v in metrics.items()},
    }
    print(json.dumps(payload), flush=True)

# Usage
def handler(event, context):
    start = time.time()
    result = do_work(event)
    latency_ms = (time.time() - start) * 1000

    emit_emf(
        namespace='MyService',
        metrics={
            'Latency':      {'value': latency_ms, 'unit': 'Milliseconds'},
            'SuccessCount': {'value': 1,           'unit': 'Count'},
        },
        dimensions={'Environment': 'prod', 'Operation': event.get('action', 'unknown')},
    )
    return result
```

**Prefer the official EMF SDK for production use** (handles buffering, flushing, and edge cases):

```bash
pip install aws-embedded-metrics
```

```python
from aws_embedded_metrics import metric_scope

@metric_scope
def handler(event, context, metrics):
    metrics.set_namespace('MyService')
    metrics.set_dimensions({'Environment': 'prod'})
    metrics.put_metric('Latency', 120.5, 'Milliseconds')
    metrics.put_metric('Invocations', 1, 'Count')
    return {'statusCode': 200}
```

**EMF limits:** max 1 MB per log event; max 100 metric definitions per directive; max 30 dimensions per DimensionSet; metric values must be a number or array of up to 100 numbers.

---

### 3. Batch PutMetricData calls — max 1,000 metrics per request

```python
import boto3
from typing import Iterator

cloudwatch = boto3.client('cloudwatch')

def chunked(lst: list, size: int) -> Iterator[list]:
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def put_metrics(namespace: str, metric_data: list) -> None:
    """Publish metrics in batches of 1,000 (the API maximum)."""
    for batch in chunked(metric_data, 1000):
        cloudwatch.put_metric_data(Namespace=namespace, MetricData=batch)
```

```bash
# CLI: up to 20 metrics per --metric-data (practical CLI limit)
aws cloudwatch put-metric-data \
  --namespace 'MyService' \
  --metric-data \
    'MetricName=RequestCount,Value=1000,Unit=Count,Dimensions=[{Name=Environment,Value=prod}]' \
    'MetricName=ErrorCount,Value=5,Unit=Count,Dimensions=[{Name=Environment,Value=prod}]'
```

---

### 4. Handle PutMetricData throttling with exponential backoff

The default PutMetricData quota is 500 TPS (adjustable). Under burst load, calls may be throttled with `ThrottlingException`. Always wrap in retry logic with exponential backoff.

```python
import boto3
from botocore.config import Config

# botocore has built-in retry with exponential backoff — configure it explicitly
cloudwatch = boto3.client(
    'cloudwatch',
    config=Config(
        retries={
            'max_attempts': 10,
            'mode': 'adaptive',  # adaptive mode: respects Retry-After header
        }
    )
)
```

If you're already at the quota limit, request an increase via Service Quotas:

```bash
aws service-quotas request-service-quota-increase \
  --service-code monitoring \
  --quota-code L-5E141A5E \  # PutMetricData quota code
  --desired-value 2000
```

---

### 5. Use GetMetricData for all programmatic metric retrieval

Always prefer `GetMetricData` over `GetMetricStatistics`. It handles up to 500 metrics per request, supports metric math, paginates automatically, and is the only API to receive new CloudWatch features going forward.

```python
import boto3
from datetime import datetime, timezone, timedelta

cloudwatch = boto3.client('cloudwatch')

def get_metrics(queries: list, hours_back: int = 1, period: int = 60) -> dict:
    """Fetch metric data, handling pagination automatically."""
    end   = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours_back)

    results = {}
    kwargs = dict(StartTime=start, EndTime=end, MetricDataQueries=queries)

    while True:
        response = cloudwatch.get_metric_data(**kwargs)
        for r in response['MetricDataResults']:
            if r['Id'] not in results:
                results[r['Id']] = {'Timestamps': [], 'Values': []}
            results[r['Id']]['Timestamps'].extend(r['Timestamps'])
            results[r['Id']]['Values'].extend(r['Values'])
        if 'NextToken' not in response:
            break
        kwargs['NextToken'] = response['NextToken']

    return results

# Example queries
queries = [
    {
        'Id': 'm1',
        'MetricStat': {
            'Metric': {
                'Namespace': 'MyService',
                'MetricName': 'RequestCount',
                'Dimensions': [{'Name': 'Environment', 'Value': 'prod'}],
            },
            'Period': 60,
            'Stat': 'Sum',
        },
    },
    {
        'Id': 'm2',
        'MetricStat': {
            'Metric': {
                'Namespace': 'MyService',
                'MetricName': 'ErrorCount',
                'Dimensions': [{'Name': 'Environment', 'Value': 'prod'}],
            },
            'Period': 60,
            'Stat': 'Sum',
        },
        'ReturnData': False,  # used only in expression below
    },
    {
        'Id': 'error_rate',
        'Expression': 'm2 / m1 * 100',
        'Label': 'ErrorRate%',
        'ReturnData': True,
    },
]
data = get_metrics(queries, hours_back=24, period=300)
```

---

### 6. Set alarms with correct evaluation configuration

A well-configured alarm needs four things correct simultaneously: the right statistic, the right period, meaningful M-of-N values, and the right missing-data treatment.

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Error rate alarm: fire when error rate > 5% for 3 of the last 5 minutes
cloudwatch.put_metric_alarm(
    AlarmName='prod-payment-error-rate',
    AlarmDescription='Payment service error rate > 5% — see runbook #42',
    Namespace='MyService',
    MetricName='ErrorRate',
    Dimensions=[{'Name': 'Environment', 'Value': 'prod'},
                {'Name': 'ServiceName', 'Value': 'payment-service'}],
    Statistic='Average',
    Unit='Percent',
    Period=60,                      # 1-minute periods
    EvaluationPeriods=5,            # look at last 5 minutes
    DatapointsToAlarm=3,            # alarm if 3+ of those 5 minutes breach
    Threshold=5.0,
    ComparisonOperator='GreaterThanThreshold',
    TreatMissingData='notBreaching',
    AlarmActions=['arn:aws:sns:us-east-1:123456789012:alerts'],
    OKActions   =['arn:aws:sns:us-east-1:123456789012:alerts'],
)
```

```bash
# CLI equivalent
aws cloudwatch put-metric-alarm \
  --alarm-name prod-payment-error-rate \
  --namespace MyService \
  --metric-name ErrorRate \
  --dimensions Name=Environment,Value=prod Name=ServiceName,Value=payment-service \
  --statistic Average \
  --unit Percent \
  --period 60 \
  --evaluation-periods 5 \
  --datapoints-to-alarm 3 \
  --threshold 5.0 \
  --comparison-operator GreaterThanThreshold \
  --treat-missing-data notBreaching \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts \
  --ok-actions     arn:aws:sns:us-east-1:123456789012:alerts
```

---

### 7. Use composite alarms to reduce alert noise

Composite alarms combine the states of other alarms with AND/OR/NOT logic. Use them to suppress noisy child alarms and page only when multiple independent signals fire simultaneously.

```python
# Fire only when BOTH latency AND error rate are elevated
cloudwatch.put_composite_alarm(
    AlarmName='prod-payment-degraded',
    AlarmRule=(
        'ALARM("prod-payment-p99-latency") '
        'AND ALARM("prod-payment-error-rate")'
    ),
    AlarmDescription='Page only when both latency AND errors are elevated',
    AlarmActions=['arn:aws:sns:us-east-1:123456789012:pagerduty'],
)
```

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name prod-payment-degraded \
  --alarm-rule 'ALARM("prod-payment-p99-latency") AND ALARM("prod-payment-error-rate")' \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:pagerduty
```

Composite alarm rule functions: `ALARM(name)`, `OK(name)`, `INSUFFICIENT_DATA(name)`. Operators: `AND`, `OR`, `NOT`. Parentheses for grouping. Max rule expression length: 10,240 characters. Composite alarms cannot reference metrics directly — only other alarms.

---

### 8. Use metric math for derived metrics instead of publishing extra metrics

Instead of publishing `ErrorRate` as a separate metric (which costs $0.30/month), compute it on read using metric math. This also makes the derived value always consistent with the underlying counts.

```python
# Instead of storing ErrorRate separately, compute it from ErrorCount / RequestCount
queries = [
    {
        'Id': 'errors',
        'MetricStat': {
            'Metric': {'Namespace': 'MyService', 'MetricName': 'ErrorCount',
                       'Dimensions': [{'Name': 'Environment', 'Value': 'prod'}]},
            'Period': 300, 'Stat': 'Sum',
        },
        'ReturnData': False,
    },
    {
        'Id': 'requests',
        'MetricStat': {
            'Metric': {'Namespace': 'MyService', 'MetricName': 'RequestCount',
                       'Dimensions': [{'Name': 'Environment', 'Value': 'prod'}]},
            'Period': 300, 'Stat': 'Sum',
        },
        'ReturnData': False,
    },
    {
        'Id': 'error_rate',
        'Expression': 'IF(requests > 0, errors / requests * 100, 0)',
        'Label': 'ErrorRate%',
        'ReturnData': True,
    },
]
```

**Useful metric math functions:**

| Function | Example | Notes |
|---|---|---|
| `SEARCH()` | `SEARCH('{MyNS,Op} MetricName="Errors"', 'Sum')` | Returns all matching time series; NOT safe in alarms |
| `FILL(m, 0)` | `FILL(m1, 0)` | Fill missing points with 0; avoid in alarms |
| `METRICS()` | `SUM(METRICS("errors"))` | Sum all metrics with "errors" in their Id |
| `IF(cond,a,b)` | `IF(m1 > 100, 1, 0)` | Conditional; FALSE if value = 0 |
| `RATE(m)` | `RATE(m1)` | Per-second rate of change; avoid in alarms on sparse data |
| `PERIOD(m)` | `m1 / PERIOD(m1)` | Returns metric period in seconds |

---

### 9. Publish zero values for sparse metrics — alarms depend on it

If your code only calls `PutMetricData` when errors occur, the metric has no data during healthy periods. An alarm with `TreatMissingData=breaching` will fire incorrectly; with `notBreaching`, it will never know the difference between "healthy" and "nothing published."

The correct approach depends on your alarm strategy:

- **If using `notBreaching`:** publish 0 when healthy so your historical graph is complete and SLO calculations are accurate.
- **If you can't publish zeros** (e.g., serverless with no always-on process): use `TreatMissingData=notBreaching` AND set `DatapointsToAlarm` high enough that the first data point after a quiet period doesn't immediately alarm.

```python
def emit_health(errors: int, requests: int) -> None:
    cloudwatch.put_metric_data(
        Namespace='MyService',
        MetricData=[
            {'MetricName': 'ErrorCount',   'Value': errors,   'Unit': 'Count'},
            {'MetricName': 'RequestCount', 'Value': requests, 'Unit': 'Count'},
            # Always publish, even if errors=0 — keeps the metric stream active
        ]
    )
```

---

### 10. Use the CloudWatch Agent with StatsD for EC2/on-premises workloads

For long-running services on EC2 or on-premises, use the CloudWatch agent with StatsD instead of direct `PutMetricData` calls. The agent buffers metrics locally and aggregates them before sending, reducing API calls and handling transient connectivity issues automatically.

```json
// /opt/aws/amazon-cloudwatch-agent/etc/config.json
{
  "metrics": {
    "metrics_collected": {
      "statsd": {
        "service_address": ":8125",
        "metrics_collection_interval": 10,
        "metrics_aggregation_interval": 60
      }
    }
  }
}
```

```python
# In your application (using statsd library)
import statsd

client = statsd.StatsClient('localhost', 8125, prefix='MyService')

client.incr('requests')          # counter
client.incr('errors')            # counter
client.timing('latency', 120)    # timer (milliseconds)
client.gauge('queue_depth', 42)  # gauge
```

The agent aggregates over `metrics_aggregation_interval` (60s default) and publishes a single `PutMetricData` call per interval instead of one per metric event.

---

### 11. Prefer Metric Streams over polling for external monitoring systems

If you send CloudWatch metrics to Datadog, New Relic, Splunk, Elasticsearch, or a custom data warehouse, use Metric Streams (Kinesis Firehose) instead of polling via `GetMetricData`. Streams deliver metrics with seconds of latency and are billed per metric update rather than per API call.

```bash
# Create a metric stream to a Firehose delivery stream
aws cloudwatch put-metric-stream \
  --name prod-metrics-stream \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/metrics-to-s3 \
  --role-arn arn:aws:iam::123456789012:role/CloudWatchMetricsStreamRole \
  --output-format json \
  --include-filters '[{"Namespace":"MyService"},{"Namespace":"AWS/Lambda"}]'
```

Supported output formats: `json`, `opentelemetry1.0`, `opentelemetry0.7`. A stream can have include filters OR exclude filters, but not both. Third-party quick-setup available for Datadog, Dynatrace, Elastic, New Relic, Splunk, SumoLogic.

---

### 12. Use Contributor Insights for high-cardinality investigation (not for alerts)

When you need to identify the top contributors to a problem (e.g., which IP addresses are causing the most 4xx errors, which DynamoDB partition keys are getting throttled), use Contributor Insights. It analyzes log data and surfaces top-N contributors without the cost of per-contributor metrics.

Contributor Insights is appropriate for investigation and dashboards. It is not a replacement for alarms on aggregate metrics.

```bash
# Enable Contributor Insights for a DynamoDB table
aws cloudwatch put-insight-rule \
  --rule-name DynamoDB-ThrottledKeys \
  --rule-state ENABLED \
  --rule-definition '{
    "Schema": {"Name":"CloudWatchLogRule","Version":1},
    "LogGroupNames": ["/aws/dynamodb/table/my-table"],
    "LogFormat": "JSON",
    "Fields": {
      "1": "$.TableName",
      "2": "$.PartitionKey"
    },
    "Contribution": {
      "Keys": ["$.PartitionKey"],
      "ValueOf": "$.ThrottledRequestCount",
      "Filters": []
    },
    "AggregateOn": "Sum"
  }'
```

Limit: 100 Contributor Insights rules per account per region (adjustable). Billing is per matched log event.

---

## Quick Reference

### Hard Limits

| Limit | Value | Adjustable? |
|---|---|---|
| PutMetricData TPS | 500 | Yes |
| GetMetricData TPS | 500 | Yes |
| GetMetricStatistics TPS | 400 | Yes |
| Metrics per PutMetricData request | 1,000 | No |
| PutMetricData payload size | 40 KB (gzip recommended) | No |
| Dimensions per metric | 30 (150 with OpenTelemetry) | No |
| Values per metric datum (Values/Counts) | 150 | No |
| GetMetricData queries per request | 500 | No |
| GetMetricStatistics data points per request | 1,440 | No |
| EMF document size | 1 MB | No |
| EMF metric definitions per directive | 100 | No |
| Contributor Insights rules | 100 | Yes |

### Metric Retention

| Storage resolution | Retention period |
|---|---|
| 1 second (high-resolution) | 3 hours |
| 60 seconds (1 minute) | 15 days |
| 300 seconds (5 minutes) | 63 days |
| 3600 seconds (1 hour) | 455 days (~15 months) |

Data published at 1-second resolution automatically rolls up to 60-second, then to 5-minute, then to 1-hour as the data ages.

### Metric and Alarm Pricing (us-east-1, as of 2024)

| Resource | Cost |
|---|---|
| Custom metrics (first 10,000) | $0.30/metric/month |
| Custom metrics (next 240,000) | $0.09/metric/month |
| Custom metrics (next 750,000) | $0.02/metric/month |
| Standard alarm | ~$0.10/alarm/month |
| High-resolution alarm (10s or 30s) | ~$0.30/alarm/month |
| GetMetricData | $0.01 per 1,000 metrics requested |
| Contributor Insights | Per matched log event (see pricing page) |
| Metric Streams | Per metric update streamed |

*Pricing changes; always verify at [aws.amazon.com/cloudwatch/pricing](https://aws.amazon.com/cloudwatch/pricing/).*

### Alarm Missing-Data Treatment Cheat Sheet

| TreatMissingData | Alarm fires on gap? | Use when... |
|---|---|---|
| `notBreaching` | No — missing = OK | Metric only emitted on errors (ThrottledRequests, DLQ messages) |
| `breaching` | Yes — missing = fault | Health-check metric that must always report (heartbeat) |
| `ignore` | State unchanged | Metric is intermittent; avoid flapping between OK and ALARM |
| `missing` (default) | INSUFFICIENT_DATA | Resource may legitimately go away (stopped instance, scaled-down group) |

### Alarm States

| State | Meaning |
|---|---|
| `OK` | Metric within threshold |
| `ALARM` | Metric breached threshold (and M-of-N satisfied) |
| `INSUFFICIENT_DATA` | Not enough data points to evaluate |

### StorageResolution Values

| Value | Resolution | Alarm period options | Use for |
|---|---|---|---|
| `60` (default) | 1 minute | 60s, 5m, 15m, 1h, ... | Standard application metrics |
| `1` | 1 second | 10s, 30s, 60s, ... | Latency-sensitive alerting; 10s/30s alarms cost more |

### PutMetricData Timestamp Constraints

| Data age | Availability after publication |
|---|---|
| Last 24 hours | Available within 2 minutes |
| 3–24 hours old | Available within 2 hours |
| 24 hours – 2 weeks old | Available within 48 hours |
| Older than 2 weeks | Rejected (InvalidParameterValue) |
| More than 2 hours in the future | Rejected |

---

## References

- [PutMetricData API Reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)
- [GetMetricData API Reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html)
- [Embedded Metric Format Specification](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)
- [CloudWatch Metrics Concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)
- [Using Metric Math](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/using-metric-math.html)
- [Configuring Missing Data Treatment](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/alarms-and-missing-data.html)
- [Composite Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Create_Composite_Alarm.html)
- [Metric Streams](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Metric-Streams.html)
- [Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html)
- [CloudWatch Service Quotas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_limits.html)
- [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [EMF Python SDK](https://github.com/awslabs/aws-embedded-metrics-python)
