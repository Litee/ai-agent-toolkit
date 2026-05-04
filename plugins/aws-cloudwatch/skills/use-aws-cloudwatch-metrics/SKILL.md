---
name: use-aws-cloudwatch-metrics
description: "Use when publishing, querying, designing, or troubleshooting Amazon CloudWatch custom metrics. Triggers on PutMetricData, GetMetricData, EMF, CloudWatch alarms, metric math, dimension cardinality, high-resolution metrics, metric streams, Contributor Insights, CloudWatch cost optimization, PutMetricData throttling, M-of-N alarms, missing data treatment, or CloudWatch agent StatsD. For log analysis, use aws-cloudwatch:query-aws-cloudwatch-logs-insights."
---

# Use AWS CloudWatch Metrics

Best practices and anti-patterns for publishing, querying, and designing monitoring with Amazon CloudWatch custom metrics. Apply these before writing any code that touches CloudWatch metrics.

**Scope:** This skill covers CloudWatch *metrics* only — namespaces, dimensions, PutMetricData, GetMetricData, EMF, alarms, metric math. For log analysis (CloudWatch Logs Insights), use the `query-aws-cloudwatch-logs-insights` skill instead.

## Purpose

CloudWatch metrics look simple on the surface — publish a number, view a chart, attach an alarm — but almost every design decision is permanent: namespaces and dimensions cannot be renamed, metric names cannot be migrated, and poor cardinality choices or the wrong alarm configuration show up as runaway bills or missed incidents months later.

This skill captures the decisions that matter: how to shape namespaces and dimensions, when to publish via EMF versus PutMetricData, how to query efficiently with GetMetricData, how to configure alarm evaluation and missing-data treatment correctly, and how to avoid the common traps (unbounded cardinality, tight-loop publishing, SEARCH in alarms, missing units).

Depth is split across three reference files so the main SKILL.md stays short. Read the pointer sections below and load the reference you need for the task at hand.

## When to Use This Skill

- Designing a new CloudWatch namespace, metric, or dimension scheme
- Publishing custom metrics from Lambda, containers, EC2, or on-premises workloads
- Choosing between EMF, PutMetricData, the CloudWatch Agent (StatsD), or Metric Streams
- Writing or debugging `GetMetricData` queries, metric math, and pagination
- Configuring alarms: statistic, period, evaluation window, M-of-N, missing-data treatment
- Designing composite alarms to reduce page noise
- Investigating high-cardinality problems (Contributor Insights)
- Diagnosing PutMetricData throttling, missing metrics, or broken percentile statistics
- Estimating or reducing CloudWatch bills driven by custom metrics, high-resolution metrics, or alarm counts

## Core Workflow

**1. Decide where metrics are coming from.**

- **Lambda or containers:** emit EMF (structured JSON to stdout). No API calls, no SDK dependency, no throttling risk. See `${SKILL_DIR}/references/best-practices.md` §2.
- **EC2 or on-premises long-running process:** run the CloudWatch Agent with StatsD; the agent buffers and aggregates locally. See `${SKILL_DIR}/references/best-practices.md` §10.
- **Short-lived script or batch job:** call `PutMetricData` directly, but batch up to 1,000 metrics per request.

**2. Lock namespace and dimension design up front** (it is permanent):

```python
# Template — same shape everywhere
STANDARD_DIMS = [
    {'Name': 'Environment', 'Value': 'prod'},
    {'Name': 'ServiceName', 'Value': 'payment-service'},
]
```

Rules: namespace format `CompanyName/ServiceName` (never `AWS/`); every dimension must be low-cardinality (< ~20 distinct values — never `RequestId`, `UserId`, `TraceId`); always publish the same dimension set together; always include `Unit`. Details in `${SKILL_DIR}/references/best-practices.md` §1 and `${SKILL_DIR}/references/anti-patterns.md` §1, §7.

**3. Publish with batching and a Unit.**

```python
cloudwatch.put_metric_data(
    Namespace='MyService',
    MetricData=[{
        'MetricName': 'Latency',
        'Value': 120.5,
        'Unit': 'Milliseconds',           # required — omitting breaks percentiles
        'StorageResolution': 60,          # default; use 1 only for sub-minute alarms
        'Dimensions': [
            {'Name': 'Environment', 'Value': 'prod'},
            {'Name': 'Operation',   'Value': 'GetUser'},
        ],
    }]
)
```

For high-throughput publishers, pre-aggregate in-process with statistic sets (Sum/Min/Max/SampleCount) and emit once per minute. Statistic sets cannot produce percentiles — use the `Values`/`Counts` fields (up to 150 samples) if p99 is required. See `${SKILL_DIR}/references/anti-patterns.md` §2.

**4. Query with `GetMetricData`, never `GetMetricStatistics`.** One call handles up to 500 metric queries, supports metric math, and paginates cleanly:

```python
queries = [
    {'Id': 'errors',   'MetricStat': {...}, 'ReturnData': False},
    {'Id': 'requests', 'MetricStat': {...}, 'ReturnData': False},
    {'Id': 'error_rate',
     'Expression': 'IF(requests > 0, errors / requests * 100, 0)',
     'ReturnData': True},
]
```

Full pagination wrapper and metric-math function reference in `${SKILL_DIR}/references/best-practices.md` §5 and §8.

**5. Design alarms with four correct settings simultaneously:**

- **Statistic & Period** that match how the metric is emitted
- **M-of-N** via `EvaluationPeriods` + `DatapointsToAlarm` (e.g., `5` and `3`) so a single transient spike cannot page
- **TreatMissingData** chosen based on what absence of data actually means (see `${SKILL_DIR}/references/quick-reference.md` for the cheat sheet)
- For sparse error-only metrics: use `notBreaching`, and either publish zeros during healthy periods or widen `DatapointsToAlarm`

Never use `SEARCH()` or `FILL()` inside alarm expressions — both are unsafe. Use composite alarms (`ALARM(a) AND ALARM(b)`) to suppress noisy children. Details in `${SKILL_DIR}/references/anti-patterns.md` §5, §6, §8 and `${SKILL_DIR}/references/best-practices.md` §6, §7, §9.

## Anti-Patterns

The 8 most common CloudWatch metrics anti-patterns — unbounded cardinality, tight-loop `PutMetricData`, over-using high-resolution metrics, misuse of `GetMetricStatistics`, wrong missing-data treatment, single-sample alarms, missing `Unit`, and `SEARCH`/`FILL` in alarm expressions — are documented with full examples and fixes in `${SKILL_DIR}/references/anti-patterns.md`.

Quick titles for scanning:

1. Unbounded dimension cardinality
2. Calling `PutMetricData` in a tight loop
3. Using high-resolution metrics (`StorageResolution=1`) when not needed
4. Using `GetMetricStatistics` for bulk or multi-metric queries
5. Wrong missing-data treatment on alarms
6. Not using M-of-N evaluation
7. Publishing metrics without a `Unit`
8. Using `SEARCH()` or `FILL()` in metric math alarms

## Best Practices

Twelve best practices covering namespace and dimension design, EMF, batching, throttling, querying, alarms, composite alarms, metric math, sparse metrics, the CloudWatch Agent with StatsD, Metric Streams, and Contributor Insights are documented in `${SKILL_DIR}/references/best-practices.md`.

Quick titles for scanning:

1. Design namespaces and dimensions before writing code
2. Use EMF for Lambda and containerised services
3. Batch `PutMetricData` calls (max 1,000 metrics per request)
4. Handle `PutMetricData` throttling with exponential backoff
5. Use `GetMetricData` for all programmatic retrieval
6. Set alarms with correct evaluation configuration
7. Use composite alarms to reduce alert noise
8. Use metric math for derived metrics instead of extra publications
9. Publish zero values for sparse metrics
10. Use the CloudWatch Agent with StatsD on EC2/on-prem
11. Prefer Metric Streams over polling for external monitoring
12. Use Contributor Insights for high-cardinality investigation

## Quick Reference

Hard limits (TPS, payload sizes, dimension count limits, EMF sizes), metric retention tiers (1s → 60s → 5m → 1h rollups), the missing-data treatment cheat sheet, alarm states, `StorageResolution` values, and `PutMetricData` timestamp constraints are documented in `${SKILL_DIR}/references/quick-reference.md`.

## Pricing

CloudWatch metrics pricing has a few distinct components, independent of any specific rate:

- **Basic monitoring** for AWS services (EC2, Lambda, etc.) is included at no extra cost and reports at 5-minute granularity.
- **Detailed monitoring** (1-minute granularity for AWS service metrics such as EC2) is billed per instance over a monthly billing period.
- **Custom metrics** are billed per unique metric over a monthly billing period, with tiered volume discounts.
- **High-resolution alarms** (10-second or 30-second periods) are billed at a higher rate than standard 60-second alarms; standard alarms are billed per alarm over a monthly billing period.
- **`PutMetricData` and `GetMetricData`** are billed per 1,000 API requests (or per 1,000 metrics requested for `GetMetricData`).
- **Metric Streams** are billed per metric update streamed.
- **Contributor Insights** rules are billed per matched log event.
- **CloudWatch Logs** (used as the transport for EMF) is billed by GB ingested and by GB stored.

Rates change frequently and vary by region. Look up current prices at <https://aws.amazon.com/cloudwatch/pricing/> before making any budget or architecture decision that depends on them.

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

## Related Skills

- **`aws-cloudwatch:query-aws-cloudwatch-logs-insights`** — Run CloudWatch Logs Insights queries when you need log analysis instead of metric publishing/alarming.
