---
name: use-aws-glue
description: "This skill should be used when writing, configuring, debugging, or monitoring AWS Glue ETL jobs. Triggers on AWS Glue, Glue job, glue update-job, GlueVersion, WorkerType, NumberOfWorkers, Glue CloudWatch metrics, Glue observability metrics, Glue job monitoring, S3 shuffle in Glue, worker type sizing, DPU right-sizing, G.025X, G.1X, G.2X, G.4X, G.8X, Parquet row count verification via pyarrow, Glue CloudWatch logs, /aws-glue/jobs/output, ApiCallTracker, Glue job naming, Glue cron monitor, Glue best practices, Glue anti-patterns, enable-metrics, enable-observability-metrics, or Glue job progress reporting. For generic PySpark coding patterns (style, anti-patterns, joins, AQE, broadcast joins, shuffle partitions), see the use-pyspark skill."
---

# Use AWS Glue

Best practices and anti-patterns for AWS Glue ETL jobs, distilled from real sessions. Apply these before writing or modifying any Glue job script or configuration.

## Anti-Patterns

### 1. `aws glue update-job` resets all unspecified settings

`update-job` does a full replacement, not a partial patch. If you pass only `--job-update Command=...` to update the script path, every other field — `GlueVersion`, `WorkerType`, `NumberOfWorkers`, `DefaultArguments` — silently resets to defaults (`GlueVersion=0.9`, `WorkerType=null`).

**Fix:** Always re-specify the full job config on every `update-job` call. Fetch the current config first and merge your change into it:

```bash
# Fetch current config, apply change, re-submit in full
aws glue get-job --job-name my-job --query 'Job' --output json > /tmp/job.json
# Edit /tmp/job.json as needed, then:
aws glue update-job --job-name my-job --job-update file:///tmp/job.json
```

---

## Best Practices

### 1. Verify Parquet row counts via pyarrow footer (no data download)

pyarrow can read only the Parquet file footer to get row counts — no data is downloaded.

**Note:** `AWS_PROFILE` env var does NOT work with pyarrow's `S3FileSystem` — credentials must be passed explicitly.

```python
import boto3
import pyarrow.parquet as pq
import pyarrow.fs as fs

session = boto3.Session()
creds = session.get_credentials().get_frozen_credentials()
s3fs = fs.S3FileSystem(
    access_key=creds.access_key,
    secret_key=creds.secret_key,
    session_token=creds.token,
    region='us-east-1',
)
meta = pq.read_metadata('my-bucket/path/to/file.parquet', filesystem=s3fs)
print(meta.num_rows)  # reads only the footer — no data downloaded
```

For a partitioned dataset (multiple Parquet files), use `pq.read_metadata` on each file or `pq.ParquetDataset` with `use_legacy_dataset=False`.

---

### 2. Glue CloudWatch output logs may not appear for fast jobs

Jobs that complete in under ~2 minutes often do not create a log stream in `/aws-glue/jobs/output`. The log group exists but the stream is missing.

**Fix:** Use pyarrow footer metadata (Best Practice #1) or a post-write `spark.read.parquet().count()` for output verification instead of relying on CloudWatch logs for fast jobs.

---

### 3. Verify S3 input and output paths exist before submitting

Check that both the input and output S3 paths are accessible before creating and submitting a Glue job. A typo in a path causes a silent failure or an unhelpful error deep into a long job run.

```bash
aws s3 ls s3://my-bucket/input/prefix/
aws s3 ls s3://my-bucket/output/prefix/
```

If the output prefix doesn't exist yet, that's fine — Glue will create it. The important check is that the bucket exists and credentials can reach it.

---

### 4. Prefix ad-hoc job names with `$USER` and a timestamp

For ad-hoc Glue jobs (not IaC-managed), use the pattern `$USER-YYYYMMDDTHHmmss-<job-description>`:

- `$USER` prefix makes it obvious who launched the job at a glance in the console.
- Second-precision UTC timestamp prevents name collisions when re-running the same job.

```bash
JOB_NAME="$(whoami)-$(date -u +%Y%m%dT%H%M%S)-my-enrichment-job"
aws glue create-job --name "$JOB_NAME" ...
```

This convention does **not** apply to jobs managed via IaC (Terraform, CloudFormation, etc.) — those have their own naming scheme.

---

### 5. Monitor running Glue jobs with cron tasks

After submitting a job, register a cron with `CronCreate` to poll its status at regular intervals. Tear it down as soon as the job reaches a terminal state.

**Use a two-phase polling strategy:**
1. **First poll at 5 minutes** — catches launch failures early (bad script path, missing IAM role, wrong arguments) before investing time in longer waits.
2. **Subsequent polls every 10–60 minutes** — choose an interval proportional to the expected job runtime. Polling more frequently generates unnecessary API calls with no actionable signal.

```bash
# Submit the job and capture the run ID
RUN_ID=$(aws glue start-job-run --job-name "$JOB_NAME" \
  --query 'JobRunId' --output text)

# Register a cron to poll every 15 minutes (adjust based on expected runtime)
# (replace CronCreate call with the tool invocation in your agent)
# CronCreate label="glue-monitor-$JOB_NAME" schedule="every 15 minutes" command:
aws glue get-job-run \
  --job-name "$JOB_NAME" \
  --run-id "$RUN_ID" \
  --query 'JobRun.[JobRunState,ExecutionTime,ErrorMessage]' \
  --output text
```

In your agent workflow:
1. Call `CronCreate` with label `glue-monitor-<job-name>`, schedule at **5 minutes** for the first poll to catch launch failures.
2. After the first poll confirms the job is running, re-register the cron at an interval proportional to expected runtime (10–60 min range).
3. In each cron callback, check `JobRunState`. On `SUCCEEDED` or `FAILED`/`ERROR`/`TIMEOUT`, call `CronDelete` to remove the cron.
4. Log or surface the state and elapsed `ExecutionTime` each tick.

---

### 6. Emit per-worker progress to CloudWatch every 60 seconds

For jobs where workers run user code in a loop, log a progress line every 60 seconds so you can track throughput without waiting for the job to finish. Use a daemon thread alongside the main processing loop — it adds negligible overhead.

```python
import threading, time, logging

logger = logging.getLogger(__name__)

def _progress_reporter(counter, total, stop_event, interval=60):
    """Daemon thread: logs progress every `interval` seconds."""
    start = time.time()
    while not stop_event.wait(interval):
        done = counter.value  # SparkContext accumulator or a threading.Value
        pct = done / total * 100 if total else 0
        elapsed = time.time() - start
        tps = done / elapsed if elapsed else 0
        logger.info(
            f"[progress] processed={done}/{total} ({pct:.1f}%) "
            f"elapsed={elapsed:.0f}s tps={tps:.1f}"
        )

# Usage in your Glue script
from pyspark.context import SparkContext
sc = SparkContext.getOrCreate()
processed = sc.accumulator(0)
total_records = input_df.count()  # only if cheap; omit if too costly

stop_evt = threading.Event()
reporter = threading.Thread(
    target=_progress_reporter,
    args=(processed, total_records, stop_evt),
    daemon=True,
)
reporter.start()

# In your processing UDF / mapPartitions, increment the accumulator:
#   processed.add(batch_size)

# After write completes:
stop_evt.set()
```

**`logger.info()` vs `print(flush=True)` in executors:** The daemon thread above runs on the **driver** — `logger.info()` works there. However, Python `logger.info()` calls inside **executor processes** (`mapPartitions`, `mapInPandas`, `pandas_udf`) do **not** appear in CloudWatch log streams. Use `print(..., flush=True)` for any logging you need inside executor-side code. These appear in the executor's cell log stream under `/aws-glue/jobs/error` with prefix `[stdout writer for /usr/bin/python3]`.

**When to skip:** For pure `df.write()` calls with no user-code loop (e.g., a simple read-transform-write pipeline), there is no natural place to inject progress — Spark controls execution entirely. Skip the reporter thread in that case and rely on the CloudWatch Glue metrics dashboard or post-job statistics (see Best Practice #8). For jobs that call external APIs, also add per-operation metrics (see #12).

---

### 7. Use cmux for a visible progress bar while monitoring

When running inside a cmux session (`CMUX_WORKSPACE_ID` is set), mirror the cron poll results into the cmux sidebar for a visual progress bar. See the `cmux` skill for the full API.

```bash
# Check whether we're inside cmux
if [ -n "$CMUX_WORKSPACE_ID" ]; then
  cmux set-status glue-job "RUNNING" --icon spinner --color "#1565C0"
  cmux set-progress 0.0 --label "Glue job submitted"
fi

# On each cron tick, update progress from ExecutionTime / expected duration:
ELAPSED=$(aws glue get-job-run --job-name "$JOB_NAME" --run-id "$RUN_ID" \
  --query 'JobRun.ExecutionTime' --output text)
EXPECTED=600  # seconds; adjust per job
FRAC=$(echo "scale=2; $ELAPSED / $EXPECTED" | bc)

if [ -n "$CMUX_WORKSPACE_ID" ]; then
  cmux set-progress "$FRAC" --label "Elapsed ${ELAPSED}s / ~${EXPECTED}s"
fi

# On terminal state:
if [ -n "$CMUX_WORKSPACE_ID" ]; then
  cmux set-progress 1.0 --label "SUCCEEDED"
  cmux set-status glue-job "Done" --icon checkmark --color "#196F3D"
  cmux clear-progress
  cmux notify --title "Glue job done" --body "$JOB_NAME finished"
fi
```

---

### 8. Print per-worker statistics at job completion

At the end of the job, log a summary of key metrics per executor so you can spot stragglers, failure hotspots, or TPS outliers. Collect stats via Spark accumulators during processing, then emit a formatted summary before the script exits.

```python
from pyspark.context import SparkContext
import time, logging

logger = logging.getLogger(__name__)
sc = SparkContext.getOrCreate()

# Declare accumulators at job start
total_processed = sc.accumulator(0)
total_failures  = sc.accumulator(0)
job_start       = time.time()

# In your mapPartitions / UDF, update them:
#   total_processed.add(n_ok)
#   total_failures.add(n_err)

# --- After df.write() completes ---
elapsed   = time.time() - job_start
processed = total_processed.value
failures  = total_failures.value
tps       = processed / elapsed if elapsed else 0
fail_pct  = failures / (processed + failures) * 100 if (processed + failures) else 0

logger.info(
    "\n=== Glue Job Summary ===\n"
    f"  Total processed : {processed:,}\n"
    f"  Total failures  : {failures:,}  ({fail_pct:.2f}%)\n"
    f"  Elapsed (s)     : {elapsed:.1f}\n"
    f"  Throughput (TPS): {tps:.1f}\n"
    "========================"
)
```

For per-executor breakdowns, use `sc.statusTracker()` or push per-partition counters to a list accumulator (type `AccumulatorParam` subclass) if you need finer granularity. The summary above is sufficient for most ad-hoc jobs. For jobs that call external APIs, complement this with per-operation latency and success/failure tracking (see #12).

---

### 9. Choose the right worker type and right-size DPUs

Worker types and their memory/vCPU:

| Worker type | vCPU | Memory | Use case |
|-------------|------|--------|----------|
| G.025X | 2 | 4 GB | Micro/dev jobs |
| G.1X | 4 | 16 GB | Standard (default) |
| G.2X | 8 | 32 GB | Memory-intensive transforms |
| G.4X | 16 | 64 GB | Heavy aggregations/joins |
| G.8X | 32 | 128 GB | Large-scale ML/compute |

**Guidance:**
- Start with G.1X and the minimum number of workers. Profile with CloudWatch metrics first.
- Scale up worker **type** before scaling out worker **count** — vertical scaling is cheaper per unit of work.
- Enable auto-scaling to avoid paying for idle executors:

```bash
aws glue create-job \
  --name "$JOB_NAME" \
  --number-of-workers 20 \
  --default-arguments '{"--enable-auto-scaling": "true"}' \
  ...
```

With auto-scaling, `NumberOfWorkers` becomes the maximum; Glue scales down workers that have been idle.

---

### 10. Monitor CloudWatch and Observability metrics

Enable metrics via `--enable-metrics true`. Key metrics: JVM heap, CPU load, bytes read, shuffle bytes, spill-to-disk. Glue 4.0+ also supports Observability metrics dashboards via `--enable-observability-metrics true`.

Load `${SKILL_DIR}/references/cloudwatch-metrics.md` for the full metric table, CLI query syntax with the required `Name=Type,Value=gauge` dimension, and Observability metrics setup.

---

### 11. Enable S3 shuffle for shuffle-heavy jobs

Default Spark shuffle writes intermediate data to local EBS disk on each worker. For jobs with large shuffles, this disk can fill up or cause spill-related slowdowns.

S3 shuffle offloads all shuffle data to S3 — effectively unlimited capacity at the cost of slightly higher per-read latency.

```bash
# Add to job DefaultArguments
"--write-shuffle-files-to-s3": "true",
"--write-shuffle-spills-to-s3": "true"
```

Best for: jobs with large aggregations or wide joins where `glue.ALL.spillBytesToDisk` is non-zero, or where upgrading worker type just to get more disk would be wasteful.

---

### 12. Track per-API-operation metrics (ApiCallTracker)

For Glue jobs that call external services (SageMaker, DynamoDB, REST), use a thread-safe `ApiCallTracker` class that logs per-operation TPS, success/failure counts, and p50/p99 latency every 5 minutes and at partition end. Integrate via `mapPartitions`.

Load `${SKILL_DIR}/references/api-call-tracker.md` for the full `ApiCallTracker` implementation and `mapPartitions` integration example.

---

## When to Load Reference Files

| Reference file | Load when... |
|---|---|
| `${SKILL_DIR}/references/cloudwatch-metrics.md` | Debugging job performance, checking JVM heap or spill metrics, setting up CloudWatch metric queries with the required `Name=Type,Value=gauge` dimension |
| `${SKILL_DIR}/references/api-call-tracker.md` | Writing a Glue job that calls external APIs (SageMaker, DynamoDB, REST) and needs per-operation latency and success/failure tracking |

---

> For generic PySpark coding patterns (import conventions, anti-patterns, style guide, join hygiene, AQE tuning, broadcast joins, shuffle partitions), see the `use-pyspark` skill.
