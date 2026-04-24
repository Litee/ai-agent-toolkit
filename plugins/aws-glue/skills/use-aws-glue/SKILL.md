---
name: use-aws-glue
description: "Use when writing, configuring, debugging, or monitoring AWS Glue ETL jobs. Triggers on AWS Glue, Glue job, GlueVersion, WorkerType, DPU right-sizing, Glue CloudWatch metrics, Glue observability metrics, groupFiles, coalesce Parquet, Glue Flex jobs, Spark UI, Glue timeout, MaxConcurrentRuns, Glue OOM, exit code 137, no space left on device, YARN container killed, or straggler tasks. For PySpark patterns, see pyspark:use-pyspark. To monitor a running job, see aws-glue:watch-aws-glue-job."
---

# Use AWS Glue

Best practices and anti-patterns for AWS Glue ETL jobs. Apply these before writing or modifying any Glue job script or configuration.

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

### 2. Not setting a job timeout — the default is 48 hours

Glue jobs default to `Timeout: 2880` minutes (48 hours). A runaway job — infinite loop, stuck waiting on a throttled API, deadlocked executor — will consume DPUs for two full days before Glue kills it. The bill arrives before you notice.

**Fix:** Always set `--timeout` (in minutes) on every `create-job` and `update-job` call.

- **Short jobs (under ~2 hours expected runtime):** Use 2–3× the expected runtime as a safety margin. For ad-hoc jobs with unknown runtime, 60–120 minutes is a sane conservative default.
- **Long jobs (several hours or more):** Be conservative — set the timeout to `2880` (the 48-hour maximum). A job that times out at 20 hours because you set the limit to 24 is a catastrophic waste of compute. The cost of extra headroom is negligible compared to losing an entire long run.

```bash
# Set timeout at job creation
aws glue create-job \
  --name "$JOB_NAME" \
  --timeout 120 \
  ...

# Or override per run (takes precedence over job-level timeout)
aws glue start-job-run \
  --job-name "$JOB_NAME" \
  --timeout 90 \
  ...
```

---

### 3. Ignoring `MaxConcurrentRuns` — causes silent queuing or "max exceeded" failures

The default `MaxConcurrentRuns` is `1`. Submitting a second run while one is active fails with `ConcurrentRunsExceededException`. This is especially confusing when the previous run appears to have completed in the console but is still in a transitional state internally.

**Fix:** Be explicit about concurrency. For ad-hoc jobs meant to run one-at-a-time, leave it at `1` (the default) but catch the exception and wait. For jobs designed for parallel execution, set it deliberately via `ExecutionProperty`:

```bash
aws glue create-job \
  --name "$JOB_NAME" \
  --execution-property '{"MaxConcurrentRuns": 3}' \
  ...
```

When polling for job completion and you hit `Max concurrent runs exceeded`, wait 30–60 seconds and check `get-job-runs` to see if the previous run is still in `RUNNING` or `STOPPING` state before retrying.

---

### 4. Attaching a Glue job to a VPC without S3/Glue VPC endpoints

When a Glue job runs inside a VPC subnet, it needs to reach S3 (for data and the script) and the Glue service API. Without a route to these services, the job hangs on connection attempts and eventually fails with `Unable to execute HTTP request... connect timed out` or `Error: Could not find S3 endpoint or NAT gateway for subnetId`.

**Fix:** Before submitting a VPC-attached job, verify that the subnet has one of the following:
- **S3 gateway endpoint** in the VPC route table (free, recommended)
- **NAT gateway** in the VPC (costs money, but covers all public AWS endpoints)

```bash
# Check whether S3 VPC endpoint exists in the target VPC
aws ec2 describe-vpc-endpoints \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=service-name,Values=com.amazonaws.$REGION.s3" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State]' --output table
```

If no endpoint exists and no NAT gateway is present, add an S3 gateway endpoint to the VPC before running the job.

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

### 5. Monitor running Glue jobs

After submitting a job, monitor it continuously until it reaches a terminal state.

**Preferred: use the `aws-glue:watch-aws-glue-job` skill (if available)**

Check your loaded plugin list. If `aws-glue:watch-aws-glue-job` is available, invoke it — it launches a continuous background watcher that polls the job, prints status updates, and notifies you on completion. This is more responsive than periodic crons and does not consume cron slots.

**Fallback: cron-based polling (if no watcher skill is available)**

Register a cron with `CronCreate` to poll job status at regular intervals. Tear it down as soon as the job reaches a terminal state.

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

### 13. Handle the small files problem on read with `groupFiles`

Reading thousands of small S3 files (< 128 MB each) makes each file a separate Spark partition. With enough files this causes: (a) driver OOM from tracking too many tasks, (b) excessive task scheduling overhead, (c) slow overall throughput. This is common after days of incremental appends produce many tiny objects.

**Fix:** Set `groupFiles` and `groupSize` options to coalesce small files into larger partitions at read time:

```python
from awsglue.context import GlueContext

glueContext = GlueContext(SparkContext.getOrCreate())

# When reading from the Glue Data Catalog
dyf = glueContext.create_dynamic_frame.from_catalog(
    database="my_db",
    table_name="my_table",
    additional_options={
        "groupFiles": "inPartition",   # group files within a partition prefix
        "groupSize": "134217728",      # 128 MB target group size in bytes
    }
)

# When reading directly from S3
dyf = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={
        "paths": ["s3://my-bucket/my-prefix/"],
        "groupFiles": "inPartition",
        "groupSize": "134217728",
    },
    format="parquet",
)
```

`groupFiles` values: `"inPartition"` (groups within a partition key prefix, safe for partitioned datasets) or `"none"` (default, no grouping).

**When NOT to use:** If your files are already large (> 128 MB each), grouping adds overhead with no benefit.

---

### 14. Coalesce output to avoid the small files problem on write

Default Spark output partitioning often produces hundreds or thousands of tiny Parquet files. This degrades downstream Athena, Redshift Spectrum, and S3 Select performance significantly — each file requires a separate S3 GET, and query planners struggle with too many small row groups.

**Fix:** Reduce output partition count before writing. Target 128 MB–1 GB per output file.

```python
# coalesce: fewer partitions, no full shuffle — use when reducing partition count
df.coalesce(10).write.parquet("s3://my-bucket/output/")

# repartition: full shuffle — use when you also need to partition by a key
df.repartition(10, "partition_col").write \
  .partitionBy("partition_col") \
  .parquet("s3://my-bucket/output/")
```

**Rule of thumb:** `output_file_count = total_data_size_bytes / target_file_size_bytes`. For 10 GB output targeting 256 MB files: `10 GB / 256 MB ≈ 40` partitions.

Use `coalesce` when only reducing partition count (avoids the shuffle cost of `repartition`). Use `repartition` when also re-keying data for `partitionBy`.

---

### 15. Use Flex execution for non-urgent batch jobs (~34% cost savings)

Glue Flex jobs run on spare Glue capacity. They cost ~34% less than standard jobs but may wait in a queue before starting, and may be restarted mid-run if capacity is reclaimed.

**When to use:** Nightly/weekly batch loads, historical backfills, dev/test runs — any job where a delay of minutes to an hour is acceptable and idempotency makes restarts safe.

**When NOT to use:** Real-time or near-real-time pipelines, jobs with a strict delivery SLA, or jobs without idempotent writes.

```bash
aws glue create-job \
  --name "$JOB_NAME" \
  --execution-class FLEX \
  --worker-type G.1X \
  --number-of-workers 10 \
  ...
```

Note: Flex is only available for Glue ETL jobs (not streaming). Not available for G.025X worker type.

---

### 16. Enable the Spark UI for post-mortem debugging

The Spark web UI exposes stage-level DAG execution, task distribution, shuffle read/write sizes, GC pressure, and executor time breakdowns. This is far more detailed than CloudWatch metrics alone and is essential for diagnosing stragglers, data skew, and OOM causes.

Glue backs up Spark event logs to S3 every 30 seconds, so you can view the UI during a run or after completion.

```bash
# Add to DefaultArguments at job creation
aws glue create-job \
  --name "$JOB_NAME" \
  --default-arguments '{
    "--enable-spark-ui": "true",
    "--spark-event-logs-path": "s3://my-bucket/spark-ui-logs/"
  }' \
  ...
```

After the job runs, view the UI in the Glue Studio console (job run → **Run Details** → **Spark UI**), or spin up a local Spark history server pointing at the same S3 path:

```bash
# Local Spark history server (requires Spark installed locally)
SPARK_NO_DAEMONIZE=true spark-class org.apache.spark.deploy.history.HistoryServer \
  -Dspark.history.fs.logDirectory=s3://my-bucket/spark-ui-logs/
```

---

## Troubleshooting

Quick reference for common Glue job failures. Check CloudWatch logs first (`/aws-glue/jobs/error` for driver errors, `/aws-glue/jobs/output` for driver stdout).

| Error / Symptom | Likely Cause | Fix |
|---|---|---|
| `Command failed with exit code 137` | OOM — YARN killed the container for exceeding memory | Scale up worker type (G.1X → G.2X). Check `glue.ALL.jvm.heap.usage` metric. Reduce partition size or avoid `collect()` / `toPandas()` on the driver. |
| `Command failed with exit code 1` | Unhandled Python exception in the script | Check `/aws-glue/jobs/error` log stream for the traceback. Common causes: import error, bad S3 path, schema mismatch, missing argument. |
| `Container killed by YARN for exceeding memory limits` | Executor OOM from large partitions, skewed joins, or too much data collected to the driver | Repartition data, avoid `collect()`, use `groupFiles`/`groupSize` for small-file input, or scale up worker type. |
| `No space left on device` | Local disk full from shuffle spill | Enable S3 shuffle (`--write-shuffle-files-to-s3 true`, `--write-shuffle-spills-to-s3 true`). See Best Practice #11. |
| `Unable to execute HTTP request... connect timed out` | VPC networking: no S3 gateway endpoint or NAT gateway in the subnet | Add an S3 gateway VPC endpoint to the subnet's route table. See Anti-Pattern #4. |
| Job enters `TIMEOUT` state | Job ran past the `Timeout` setting (default 2880 min / 48 hours if unset) | Set a tighter `--timeout` on the job or per-run. See Anti-Pattern #2. |
| Job runs for hours with no progress / straggler task | Data skew causing one task to process most of the data | Enable Spark UI to inspect task distribution. Use `groupFiles` for small-file inputs. Repartition skewed keys with salting (see `pyspark:use-pyspark` skill). |
| `ConcurrentRunsExceededException: Max concurrent runs exceeded` | A previous run is still active or in a transitional state | Check `aws glue get-job-runs` for runs in `RUNNING` or `STOPPING` state. Wait for completion or increase `MaxConcurrentRuns`. See Anti-Pattern #3. |
| `ThrottlingException` on Glue API calls | Polling too frequently or too many concurrent API calls | Use exponential backoff. Poll at 5 min then every 10–60 min (see Best Practice #5), not every few seconds. |
| CloudWatch output logs missing for short jobs | Jobs completing in < ~2 min may not flush the log stream | Use pyarrow footer metadata (Best Practice #1) or post-write `spark.read.parquet().count()` for verification. See Best Practice #2. |
| `Error: Could not find S3 endpoint or NAT gateway for subnetId` | VPC job has no route to S3 | Same as `connect timed out` — add an S3 gateway endpoint. See Anti-Pattern #4. |

---

## When to Load Reference Files

| Reference file | Load when... |
|---|---|
| `${SKILL_DIR}/references/cloudwatch-metrics.md` | Debugging job performance, checking JVM heap or spill metrics, setting up CloudWatch metric queries with the required `Name=Type,Value=gauge` dimension |
| `${SKILL_DIR}/references/api-call-tracker.md` | Writing a Glue job that calls external APIs (SageMaker, DynamoDB, REST) and needs per-operation latency and success/failure tracking |

---

> For generic PySpark coding patterns (import conventions, anti-patterns, style guide, join hygiene, AQE tuning, broadcast joins, shuffle partitions), see the `pyspark:use-pyspark` skill.
