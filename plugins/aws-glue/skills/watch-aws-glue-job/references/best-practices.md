# AWS Glue Job Best Practices

Reference for common Glue job patterns, troubleshooting, and operational guidance.

---

## Job Run States

| State | Meaning |
|-------|---------|
| `STARTING` | Job is being allocated — DPU provisioning, driver/executor startup |
| `RUNNING` | Job is executing |
| `STOPPING` | Stop was requested, graceful shutdown in progress |
| `STOPPED` | Job was manually stopped |
| `SUCCEEDED` | Job completed successfully |
| `FAILED` | Job failed — check `ErrorMessage` in the run details |
| `ERROR` | Infrastructure error (different from job logic failure) |
| `TIMEOUT` | Job exceeded the configured `Timeout` limit (default 2880 min = 48h) |
| `WAITING` | Job is in queue behind other concurrent runs |

**Typical flow:** `STARTING` → `RUNNING` → `SUCCEEDED` (or `FAILED`)

`STARTING` can take 2–5 minutes for Glue 3.0+. This is normal — Spark cluster is provisioning.

---

## Common Errors and Fixes

### OutOfMemoryError / Java heap space

**Symptom:** `FAILED` with `ErrorMessage: OutOfMemoryError: Java heap space`

**Cause:** Data skew — most partitions finish quickly but a few have millions of rows.

**Fix:**
1. Increase `--executor-memory` via job argument `--conf spark.executor.memory=8g`
2. Repartition the hot partition: `df.repartition(200, hot_column)`
3. Add salting to skewed join keys
4. Switch to G.2X or G.4X workers

### ConcurrentRunsExceededException

**Symptom:** `start_job_run` throws `ConcurrentRunsExceededException`

**Cause:** The job's `MaxConcurrentRuns` setting is already at capacity.

**Fix:** Either wait for the running instance to complete, or increase `MaxConcurrentRuns` in the job definition (Glue Console → Job → Edit → Advanced properties).

To find the active run ID:
```python
response = glue.get_job_runs(JobName=job_name, MaxResults=1)
active_run = response['JobRuns'][0]
print(active_run['Id'])  # pass this to watch-job --run-id
```

### S3 Access Denied

**Symptom:** Job fails with `AccessDeniedException` on S3 paths

**Fix:** The Glue IAM role needs `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the input/output buckets. Glue uses the job's associated IAM role, not the caller's credentials.

### Script Not Found

**Symptom:** `FAILED` immediately with `ScriptLocation ... not found`

**Fix:** The `--script-location` S3 path is wrong or the script wasn't uploaded before `start_job_run`. Re-upload the PySpark script to S3 and verify the path.

### Timeout

**Symptom:** Job hits `TIMEOUT` state

**Cause:** Job exceeded the `Timeout` setting (minutes). Default is 2880 (48 hours).

**Fix:**
- Increase `Timeout` in the job definition, or
- Optimize the job to run faster (add partitions, fix skew, reduce shuffle)

---

## Worker Types and Sizing

| Worker Type | vCPU | Memory | Use Case |
|-------------|------|--------|----------|
| G.1X | 4 | 16 GB | Light transformations, small datasets |
| G.2X | 8 | 32 GB | Standard ETL, medium datasets |
| G.4X | 16 | 64 GB | Memory-intensive, large shuffles |
| G.8X | 32 | 128 GB | Very large datasets, complex aggregations |
| G.025X | 2 | 4 GB | Micro-batch streaming, low-cost batch |

**Rule of thumb:** Start with G.2X. If you see OOM errors or excessive spill-to-disk, move to G.4X. If the job is I/O-bound and memory is fine, more workers with G.1X is cheaper than fewer G.4X.

**DPU-seconds** (reported by `check-status`): `DPU-seconds = workers × DPU-per-worker × elapsed_seconds`. Used for billing. G.2X = 2 DPU, G.4X = 4 DPU.

---

## Job Bookmarks

Job bookmarks let Glue track which data has already been processed, enabling incremental loads.

```python
# Enable in start_job_run arguments
glue.start_job_run(
    JobName=job_name,
    Arguments={'--job-bookmark-option': 'job-bookmark-enable'}
)
```

**To reset a bookmark** (reprocess all data):
```bash
aws glue reset-job-bookmark --job-name my-job --profile my-profile
```

Or pass `'--job-bookmark-option': 'job-bookmark-reset'` in the run arguments.

---

## Credential Handling in Long Jobs

For jobs running 4+ hours, AWS temporary credentials inside the Glue job itself may expire (STS tokens from assumed roles typically last 1–12 hours).

**If the job script uses STS/assume-role internally:** Refresh credentials inside the Spark driver periodically. The monitor's `GlueJobClient` recreates its boto3 session per call, which handles the calling side. The Glue job's IAM role (used by executors) is managed by Glue and doesn't expire during the run.

**The `CREDENTIAL_EXPIRED` monitor state** means the *monitor script's* credentials expired, not the Glue job itself. The job may still be running. After refreshing AWS credentials:
```bash
# Re-launch the monitor
glue_job.py watch-job --job-name <name> --run-id <id> --profile <profile> --surface-id <surface>
```

---

## Getting the Run ID

After submitting a Glue job, get the run ID from the API response:
```python
response = glue.start_job_run(JobName=job_name, Arguments={...})
run_id = response['JobRunId']  # e.g. jr_abc1234567890abc
```

Or find it in the Glue Console under the job's Run history tab.

---

## Useful AWS CLI Commands

```bash
# Get current status of a run
aws glue get-job-run --job-name my-job --run-id jr_abc123 \
    --query 'JobRun.[JobRunState,ExecutionTime,ErrorMessage]' \
    --profile my-profile

# List recent runs
aws glue get-job-runs --job-name my-job --max-results 5 \
    --query 'JobRuns[*].[Id,JobRunState,StartedOn,ExecutionTime]' \
    --profile my-profile

# Stop a running job
aws glue batch-stop-job-run --job-name my-job --job-run-ids jr_abc123 \
    --profile my-profile

# Get CloudWatch log groups for a job
aws logs describe-log-groups --log-group-name-prefix /aws-glue/jobs \
    --profile my-profile
```

---

## CloudWatch Logs

Glue writes driver and executor logs to CloudWatch under `/aws-glue/jobs/`:

| Log Group | Contents |
|-----------|----------|
| `/aws-glue/jobs/output` | stdout from PySpark driver (print statements) |
| `/aws-glue/jobs/error` | stderr, exceptions, stack traces |
| `/aws-glue/jobs/logs-v2` | Combined driver + executor logs (Glue 3.0+) |

**Log stream names** include the job run ID, making it easy to correlate with a specific run.

Use the `query-aws-cloudwatch-logs-insights` skill to query these logs:
```bash
query-cloudwatch-logs.py \
    --query 'fields @timestamp, @message | filter @message like /Exception/' \
    --log-groups '/aws-glue/jobs/error' \
    --start-time '2h' \
    --profile my-profile
```
