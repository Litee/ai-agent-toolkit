# Anti-Patterns

The following are the most common mistakes made when publishing, querying, or alarming on Amazon CloudWatch metrics. Each one explains what not to do, why it fails, and the correct fix with code. Read these before designing a new metric pipeline or debugging an existing one.

---

## 1. Unbounded dimension cardinality — the silent cost explosion

Each unique combination of dimension values creates a separate, billable metric. Using high-cardinality values such as `RequestId`, `UserId`, `SessionId`, or `TraceId` as dimensions causes a combinatorial explosion of metrics.

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

## 2. Calling PutMetricData in a tight loop — throttling and cost waste

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

## 3. Using high-resolution metrics (StorageResolution=1) when you don't need sub-minute granularity

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

## 4. Using GetMetricStatistics for bulk or multi-metric queries

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

## 5. Wrong missing-data treatment on alarms — false positives or silent failures

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

## 6. Not using M-of-N evaluation — single transient spike triggers alarm

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

## 7. Publishing metrics without a Unit — breaks percentile statistics

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

## 8. Using SEARCH() or FILL() in metric math alarms

`SEARCH()` returns an array of time series that can change over time — an alarm based on it may be monitoring different metrics month to month. `FILL()` can cause alarms to get stuck in ALARM or OK state when the underlying metric is published with delay. Neither is safe in alarm expressions.

**What NOT to do:**

```
# BAD: alarm on a SEARCH expression
SEARCH('{MyService} MetricName="ErrorRate"', 'Average')
```

**Fix:** Always reference explicit, stable metric IDs in alarm expressions. If you need to alarm on a sum across multiple instances, create a composite alarm or an explicit metric math expression referencing fixed `MetricStat` entries.
