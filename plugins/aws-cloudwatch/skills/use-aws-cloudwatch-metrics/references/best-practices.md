# Best Practices

Twelve practices covering namespace and dimension design, EMF publication, batching, throttling, querying, alarm configuration, composite alarms, metric math, sparse-metric handling, the CloudWatch Agent with StatsD, Metric Streams, and Contributor Insights. Apply these when designing or reviewing any CloudWatch metrics pipeline.

---

## 1. Design namespaces and dimensions before writing code

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

## 2. Use EMF (Embedded Metric Format) for Lambda and containerised services

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

## 3. Batch PutMetricData calls — max 1,000 metrics per request

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

## 4. Handle PutMetricData throttling with exponential backoff

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

## 5. Use GetMetricData for all programmatic metric retrieval

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

## 6. Set alarms with correct evaluation configuration

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

## 7. Use composite alarms to reduce alert noise

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

## 8. Use metric math for derived metrics instead of publishing extra metrics

Instead of publishing `ErrorRate` as a separate metric (which is billed as an additional custom metric), compute it on read using metric math. This also makes the derived value always consistent with the underlying counts.

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

## 9. Publish zero values for sparse metrics — alarms depend on it

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

## 10. Use the CloudWatch Agent with StatsD for EC2/on-premises workloads

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

## 11. Prefer Metric Streams over polling for external monitoring systems

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

## 12. Use Contributor Insights for high-cardinality investigation (not for alerts)

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
