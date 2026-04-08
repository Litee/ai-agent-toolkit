### 1. Monitor key CloudWatch metrics during job runs

Enable metrics with `--enable-metrics true` in job `DefaultArguments`. Key metrics to watch:

| Metric | What it tells you | Action threshold |
|--------|-------------------|-----------------|
| `glue.ALL.jvm.heap.usage` | Executor heap % | >80% sustained → OOM risk, upgrade worker type |
| `glue.ALL.system.cpuSystemLoad` | CPU utilization | Very low + slow job → I/O-bound or skew; very high + no throughput → skew |
| `glue.driver.aggregate.bytesRead` | Total input bytes | Compare vs expected; low = partition pruning not working |
| `glue.ALL.s3.filesystem.read_bytes` / `write_bytes` | S3 I/O rate | Flat line → stalled on S3; consider parallelism or partitioning |
| `glue.driver.aggregate.shuffleBytesWritten` | Shuffle output volume | Unexpectedly large → missing filter pushdown or Cartesian join |
| `glue.ALL.spillBytesToDisk` | Disk spill | Any non-zero → memory pressure; see use-pyspark anti-pattern #5 |

```bash
# Check heap usage for a running job
# NOTE: Name=Type,Value=gauge is REQUIRED — omitting it returns empty Datapoints
aws cloudwatch get-metric-statistics \
  --namespace Glue \
  --metric-name "glue.ALL.jvm.heap.usage" \
  --dimensions \
    Name=JobName,Value="$JOB_NAME" \
    Name=JobRunId,Value="$RUN_ID" \
    Name=Type,Value=gauge \
  --start-time "$(date -u -v-10M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 60 --statistics Average
```

> **`Name=Type,Value=gauge` is required for all Glue CloudWatch metrics.** Without this third dimension, `get-metric-statistics` always returns empty `Datapoints` — even when `list-metrics` confirms the metric exists. Add it to every metric query.

---

### 2. Use Glue Observability metrics (Glue 4.0+) for deeper diagnostics

Glue 4.0+ provides pre-built CloudWatch dashboards via Observability metrics:
- ETL data movement: bytes read/written broken down by source and sink
- Job timeline with stage-level breakdown
- Executor utilisation and GC pressure over time

Enable with `--enable-observability-metrics true` in job `DefaultArguments`. View in the Glue Studio console under the job run's **Metrics** tab — no manual CloudWatch dashboard setup required.

Use Observability metrics as the first stop for root-cause analysis. They surface bottlenecks (slow stages, high GC, spill) without needing to configure a separate Spark history server.
