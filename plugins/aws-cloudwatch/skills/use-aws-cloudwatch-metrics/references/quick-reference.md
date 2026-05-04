# Quick Reference

CloudWatch metrics hard limits, retention tiers, and alarm-configuration cheat sheets. Use this file as a lookup during design or troubleshooting.

---

## Hard Limits

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

---

## Metric Retention

| Storage resolution | Retention period |
|---|---|
| 1 second (high-resolution) | 3 hours |
| 60 seconds (1 minute) | 15 days |
| 300 seconds (5 minutes) | 63 days |
| 3600 seconds (1 hour) | 455 days (~15 months) |

Data published at 1-second resolution automatically rolls up to 60-second, then to 5-minute, then to 1-hour as the data ages.

---

## Alarm Missing-Data Treatment Cheat Sheet

| TreatMissingData | Alarm fires on gap? | Use when... |
|---|---|---|
| `notBreaching` | No — missing = OK | Metric only emitted on errors (ThrottledRequests, DLQ messages) |
| `breaching` | Yes — missing = fault | Health-check metric that must always report (heartbeat) |
| `ignore` | State unchanged | Metric is intermittent; avoid flapping between OK and ALARM |
| `missing` (default) | INSUFFICIENT_DATA | Resource may legitimately go away (stopped instance, scaled-down group) |

---

## Alarm States

| State | Meaning |
|---|---|
| `OK` | Metric within threshold |
| `ALARM` | Metric breached threshold (and M-of-N satisfied) |
| `INSUFFICIENT_DATA` | Not enough data points to evaluate |

---

## StorageResolution Values

| Value | Resolution | Alarm period options | Use for |
|---|---|---|---|
| `60` (default) | 1 minute | 60s, 5m, 15m, 1h, ... | Standard application metrics |
| `1` | 1 second | 10s, 30s, 60s, ... | Latency-sensitive alerting; 10s/30s alarms cost more |

---

## PutMetricData Timestamp Constraints

| Data age | Availability after publication |
|---|---|
| Last 24 hours | Available within 2 minutes |
| 3–24 hours old | Available within 2 hours |
| 24 hours – 2 weeks old | Available within 48 hours |
| Older than 2 weeks | Rejected (InvalidParameterValue) |
| More than 2 hours in the future | Rejected |
