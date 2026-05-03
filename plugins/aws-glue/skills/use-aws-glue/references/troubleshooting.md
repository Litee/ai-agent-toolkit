# Glue Job Troubleshooting

Quick reference for common AWS Glue job failures. Check CloudWatch logs first (`/aws-glue/jobs/error` for driver errors, `/aws-glue/jobs/output` for driver stdout).

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
