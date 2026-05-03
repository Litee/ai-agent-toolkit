---
name: use-pyspark
description: "Use when writing, debugging, or reviewing PySpark scripts and Spark DataFrame transformations. Triggers on PySpark, MapType schema, data skew, shuffle spill, broadcast join, AQE, shuffle partitions, Python UDFs, F.col, window frame, PySpark import aliases, type hints, Spark anti-patterns, partition pruning, or Parquet compression. For AWS Glue-specific practices (job config, worker types, CloudWatch metrics), see aws-glue:use-aws-glue."
---

# Use PySpark

Best practices and anti-patterns for PySpark and Spark DataFrames. Apply these before writing or modifying any PySpark script.

## Anti-Patterns

### 1. Spark JSON inference on dynamic-key maps causes driver OOM

`spark.read.json()` with schema inference treats every JSON object as a struct, making each unique key a field name. If a response has one key per query hash (e.g., `"54c55d70"`), and you're reading 82K records each with different keys, Spark tries to merge 100K+ field names on the driver — exhausting heap after hours of work.

**Fix:** Use an explicit `MapType(StringType(), ...)` schema for any JSON object with dynamic keys:

```python
from pyspark.sql.types import (
    StructType, StructField, StringType, ArrayType, MapType
)

# Example: response.results is a map from hash -> list of structs
result_item_schema = StructType([
    StructField("id", StringType()),
    StructField("score", StringType()),
])
schema = StructType([
    StructField("response", StructType([
        StructField("results", MapType(StringType(), ArrayType(result_item_schema)))
    ]))
])
df = spark.read.schema(schema).json("s3://bucket/prefix/")
```

Providing an explicit schema skips the inference pass (which reads the full input to sample types) and avoids OOM/driver failures on large or deeply nested JSON, typically turning a failing or very long-running job into one bounded by the actual read/parse cost.

---

### 2. `df.count()` before `df.write()` doubles runtime

`df.count()` forces a full materialisation of the DataFrame — a complete extra scan of the input. For large datasets this doubles or triples runtime.

**Fix:** Write first, then verify row count post-job using pyarrow Parquet footer metadata or a post-write `spark.read.parquet().count()`. Skip the in-job count entirely when possible.

```python
# BAD — full extra scan before write
n = df.count()
df.write.parquet(output_path)

# GOOD — write first, verify post-job externally
df.write.parquet(output_path)
# Post-job: verify via pyarrow footer (no data download)
```

---

### 3. Python UDFs cause per-row serialization overhead

`pyspark.sql.functions` (built-in) run natively in the JVM. Python UDFs (`@udf`) force data to cross from the JVM into the Python process and back for every row — often 2–10x slower. `@pandas_udf` (Arrow-based) is much faster but still has batch serialization cost.

**Fix:** Prefer built-in `pyspark.sql.functions` for all transformations. If you must write a UDF, use `@pandas_udf` with Arrow instead of a row-level `@udf`.

```python
from pyspark.sql import functions as F
from pyspark.sql.functions import pandas_udf
import pandas as pd

# BAD — row-level Python UDF, serialization per row
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

@udf(StringType())
def slow_upper(s):
    return s.upper() if s else None

df.withColumn("upper", slow_upper("col"))

# GOOD — built-in function, pure JVM
df.withColumn("upper", F.upper("col"))

# ACCEPTABLE — pandas UDF if custom logic is unavoidable
@pandas_udf(StringType())
def fast_custom(s: pd.Series) -> pd.Series:
    return s.str.upper()

df.withColumn("upper", fast_custom("col"))
```

---

### 4. Not handling data skew causes straggler tasks

When key distribution is uneven, some partitions get orders of magnitude more data than others. One executor takes 10x longer than the rest, and the whole stage blocks waiting for it.

**Signs:** A stage shows most tasks completing in seconds while one task runs for minutes; CPU utilization is nearly zero on most workers while one is pegged at 100%.

**Fix options:**
- **AQE skew join** (Spark 3.2+ with AQE enabled): Spark automatically splits skewed partitions at runtime.
- **Broadcast join** for small-side DataFrames (see best practice #4).
- **Salting:** Add a random suffix to the skewed key, join/aggregate, then strip it.

```python
# Enable AQE skew join
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Salting example for a heavily skewed groupBy key
import pyspark.sql.functions as F

SALT_FACTOR = 50
df_salted = df.withColumn("salted_key",
    F.concat(F.col("key"), F.lit("_"), (F.rand() * SALT_FACTOR).cast("int")))
df_agg = (df_salted
    .groupBy("salted_key")
    .agg(F.sum("value").alias("partial_sum")))
# strip trailing salt suffix (split would break keys that contain underscores)
df_result = (df_agg
    .withColumn("key", F.regexp_replace(F.col("salted_key"), r"_\d+$", ""))
    .groupBy("key")
    .agg(F.sum("partial_sum").alias("total")))
```

---

### 5. Shuffle spill to disk due to insufficient executor memory

When shuffle data exceeds executor memory, Spark spills to disk — dramatically slowing the job.

**Signs:** Spark UI shows non-zero "Shuffle Spill (Disk)" in stage metrics.

**Fix options (in order of preference):**
1. Filter data earlier to reduce shuffle volume before the problematic stage.
2. Tune `spark.sql.shuffle.partitions` — see best practice #5.
3. Increase executor memory (upgrade worker type or increase memory allocation).

---

### 6. Direct dataframe column access (`df.colA`) breaks on special characters and prevents reuse

Accessing columns via `df.colA` or `df["colA"]` couples expressions to the dataframe variable name, fails on column names with spaces or special characters, and prevents defining reusable transform functions.

```python
# bad — coupled to variable name, breaks with renamed df
df = df.select(F.lower(df.colA), F.upper(df2.colB))

# good — always use F.col() or bare string (Spark 3.0+)
df = df.select(F.lower(F.col("colA")), F.upper(F.col("colB")))
df = df.select(F.lower("colA"), F.upper("colB"))  # Spark 3.0+
```

**Exception:** Use `df.colA` only to disambiguate columns from two DataFrames with the same name in a join condition.

---

### 7. Complex logical operations crammed into a single filter/when

Nesting more than 3 boolean expressions inside a single `.filter()` or `F.when()` makes the logic opaque and untestable.

```python
# bad — unreadable, impossible to unit test intermediate conditions
F.when(
    (F.col("status") == "Delivered") | (((F.datediff("delivery_date", "current_date") < 0) &
    ((F.col("registration") != "") | (F.col("operator") != "")))),
    "In Service")

# good — extract conditions into named variables
is_delivered = F.col("status") == "Delivered"
delivery_passed = F.datediff("delivery_date", "current_date") < 0
has_registration = F.col("registration") != ""
has_operator = F.col("operator") != ""
is_active = has_registration | has_operator

F.when(is_delivered | (delivery_passed & is_active), "In Service")
```

Limit to **3 expressions maximum** inside a single filter or when. Extract more into named variables.

---

### 8. Using `.dropDuplicates()` or `.distinct()` to paper over bad joins

Adding `.dropDuplicates()` after a join that produces unexpected duplicates masks the root cause — usually a non-unique join key or the wrong join type. It adds CPU overhead and hides correctness bugs.

```python
# bad — masks the real problem
result = df.join(lookup, "id", how="left").dropDuplicates()

# good — diagnose first: is the join key unique in lookup?
assert lookup.groupBy("id").count().filter("count > 1").count() == 0, "lookup key not unique"
result = df.join(lookup, "id", how="left")
```

If duplicates are expected (fan-out join), document it explicitly and handle them intentionally — don't silently deduplicate.

---

### 9. Window functions without explicit frame specification

When you define a window with `orderBy` but no frame, Spark generates an implicit rolling frame (unbounded preceding to current row). This is rarely what you want and produces non-deterministic or incorrect results for aggregate functions.

```python
# bad — implicit, unpredictable frame
w = W.partitionBy("key").orderBy("ts")
df.withColumn("total", F.sum("val").over(w))  # rolling sum, not partition sum

# good — always specify rowsBetween or rangeBetween
w_partition = W.partitionBy("key").rowsBetween(W.unboundedPreceding, W.unboundedFollowing)
w_rolling   = W.partitionBy("key").orderBy("ts").rowsBetween(W.unboundedPreceding, 0)
```

For `F.first()` / `F.last()` / `F.lead()` / `F.lag()` — handle nulls explicitly:

```python
F.first("val", ignorenulls=True).over(w_partition)
F.last("val",  ignorenulls=True).over(w_partition)
```

Also: **never use `W.partitionBy()` with no arguments** — it forces all data into a single partition. Use `df.agg()` instead.

**`rowsBetween` vs `rangeBetween`**: `rowsBetween` counts physical rows (position-based); `rangeBetween` uses the numeric value of the `ORDER BY` column (value-based). For date/time rolling windows, cast your timestamp to a Unix epoch long and use `rangeBetween` with the appropriate interval in seconds — `rowsBetween` on sparse data gives a wrong window (7 preceding _rows_, not 7 preceding _days_).

```python
# rowsBetween — 7 preceding physical rows regardless of time gap
w_rows = W.partitionBy("key").orderBy("ts").rowsBetween(-6, 0)

# rangeBetween — all rows within the last 7 days (86400s × 7)
w_range = W.partitionBy("key").orderBy(F.col("ts").cast("long")).rangeBetween(-6 * 86400, 0)
```

---

### 10. Using `withColumnRenamed()` instead of `select` with aliases

`withColumnRenamed()` is implicit — it doesn't document which columns survive into the output. Using `select` with `.alias()` serves as an explicit schema contract for both inputs and outputs.

```python
# bad — opaque, doesn't show what columns are in the output
df = df.withColumnRenamed("src_col", "dst_col")

# good — explicit schema contract
df = df.select(
    "id",
    "timestamp",
    F.col("src_col").alias("dst_col"),
    F.col("raw_count").cast("long"),
)
```

Rules for `select`-as-contract:
- Keep it simple: max **one** `pyspark.sql.functions` call per selected column, plus an optional `.alias()`
- If more than **3** function calls are needed in the same select, extract the logic into a helper function
- For complex expressions, `withColumn()` is still fine — this rule applies to schema-defining selects only

---

## Best Practices

### 1. Use partitions for large datasets

Many datasets are extremely large. Always leverage partition pruning when reading partitioned data — push filter predicates down so Spark only reads the relevant partitions, not the whole dataset.

```python
# BAD — full scan of all partitions
df = spark.read.parquet("s3://bucket/data/")

# GOOD — pruned to only the partitions you need
df = spark.read.parquet("s3://bucket/data/").filter("year = '2024' AND month = '03'")
# Or pass partition filters at read time for Hive-style partitions
df = spark.read.parquet("s3://bucket/data/year=2024/month=03/")
```

When writing, partition by the columns most commonly used in downstream filters.

---

### 2. Compress Spark outputs

Always compress output files unless explicitly told otherwise. Uncompressed outputs are much larger on storage and slower to read downstream.

```python
# Parquet — snappy is the default and recommended
df.write.option("compression", "snappy").parquet(output_path)

# CSV or JSON — gzip
df.write.option("compression", "gzip").csv(output_path)
```

Snappy is preferred for Parquet (good compression ratio, splittable, fast). Gzip for text formats when compatibility is needed.

---

### 3. Enable Adaptive Query Execution (AQE)

AQE (available in Spark 3.0+, enabled by default in Spark 3.2+) rewrites query plans at runtime based on actual data statistics gathered during execution. Key benefits:

- **Coalesces shuffle partitions:** Merges small post-shuffle partitions into fewer, larger ones — eliminates thousands of tiny tasks.
- **Converts sort-merge joins to broadcast joins:** If one side turns out to be small at runtime, AQE switches the join strategy automatically.
- **Handles skew joins:** Splits oversized partitions before the join.

```python
# Spark 3.0/3.1 — must enable explicitly
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

# Spark 3.2+ — already on by default; verify with:
print(spark.conf.get("spark.sql.adaptive.enabled"))  # "true"
```

---

### 4. Use broadcast joins for small-to-large table joins

When one side of a join fits in executor memory, broadcast it to every worker — eliminates the full shuffle entirely.

```python
from pyspark.sql.functions import broadcast

# Explicit broadcast hint (recommended — don't rely on auto-threshold alone)
result = df_large.join(broadcast(df_small), "key")

# Raise the auto-broadcast threshold if your "small" table is between 10MB and 200MB
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", str(200 * 1024 * 1024))  # 200MB
```

**Never broadcast the large side** — it causes OOM on every executor simultaneously.

---

### 5. Tune shuffle partitions to match data volume

Default `spark.sql.shuffle.partitions=200` is rarely right.

- **Too few** → each partition is huge → OOM or disk spill
- **Too many** → thousands of tiny tasks → scheduling overhead, slow stage completion

Rule of thumb: target **128–256 MB per partition** after the shuffle. Divide your estimated shuffle output size by 200 MB to get a starting number.

With AQE enabled, set the value high and let `coalescePartitions` merge small ones automatically:

```python
# Set high; AQE will coalesce down to the right number at runtime
spark.conf.set("spark.sql.shuffle.partitions", "800")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", str(256 * 1024 * 1024))
```

Without AQE, profile first and set manually based on your data volume.

---

### 6. Use standard PySpark import aliases

Always use these canonical aliases — they are the de facto standard across the PySpark ecosystem and prevent accidental shadowing of Python builtins (`sum`, `max`, `min`, `round`):

```python
from pyspark.sql import functions as F   # F.col(), F.when(), F.sum(), ...
from pyspark.sql import types as T       # T.StringType(), T.LongType(), ...
from pyspark.sql import Window as W      # W.partitionBy(), W.orderBy(), ...
```

**Never** import individual functions directly:

```python
# bad — shadows Python builtins, hard to grep, creates import sprawl
from pyspark.sql.functions import col, when, sum, max, round
```

---

### 7. Add type hints to all PySpark transform functions

Type hints on PySpark functions improve IDE autocompletion, enable static type checking (mypy/pyright), and document the schema contract for reviewers. Use `pyspark.sql.DataFrame` for DataFrame parameters and return types.

```python
from pyspark.sql import DataFrame
import pyspark.sql.functions as F

# bad — no type information, opaque contract
def clean_urls(df, base_url):
    return df.withColumn("url", F.concat(F.lit(base_url), F.col("path")))

# good — explicit contract, IDE-friendly
def clean_urls(df: DataFrame, base_url: str) -> DataFrame:
    return df.withColumn("url", F.concat(F.lit(base_url), F.col("path")))
```

For `pandas_udf` functions, annotate the Series types:

```python
import pandas as pd
from pyspark.sql.functions import pandas_udf

@pandas_udf("string")
def normalize(s: pd.Series) -> pd.Series:
    return s.str.strip().str.lower()
```

---

### 8. Limit method chain length and use parentheses for multi-line

Chains longer than **5 statements** are hard to read, hard to debug (you can't inspect intermediate results), and make test extraction in IDEs painful. Break them into named intermediate DataFrames.

```python
# bad — 7-statement chain, can't inspect intermediate state
result = (
    df
    .filter(F.col("status") == "active")
    .withColumn("score", F.col("raw") / F.col("total"))
    .join(lookup, "id", how="left")
    .withColumn("label", F.when(F.col("score") > 0.5, "high").otherwise("low"))
    .select("id", "score", "label", "region")
    .filter(F.col("region").isNotNull())
    .dropDuplicates(["id"])
)

# good — broken at logical boundaries
filtered = df.filter(F.col("status") == "active")

scored = filtered.withColumn("score", F.col("raw") / F.col("total"))

enriched = (
    scored
    .join(lookup, "id", how="left")
    .withColumn("label", F.when(F.col("score") > 0.5, "high").otherwise("low"))
)

result = enriched.select("id", "score", "label", "region").filter(F.col("region").isNotNull())
```

Always use parentheses `()` for multi-line expressions — never backslashes:

```python
# bad
df = df.filter(F.col("a") == 1)\
    .select("a", "b")

# good
df = (
    df
    .filter(F.col("a") == 1)
    .select("a", "b")
)
```

---

### 9. Join hygiene: always specify `how=`, use DataFrame aliases, select before joining

Four rules that prevent the most common join bugs:

1. **Always specify `how=` explicitly**, even for inner joins — makes intent obvious at a glance.
2. **Avoid right joins** — swap operand order and use `left` instead; left join semantics are universally understood.
3. **Alias DataFrames** when they have overlapping column names — don't rename all columns individually.
4. **Select only the needed columns before joining** — eliminates ambiguous column errors and reduces shuffle size.

```python
# bad — implicit inner, no aliasing, overlapping columns cause ambiguity
result = flights.join(parking, on="flight_code")

# good
flights = flights.alias("flights")
parking = parking.select("flight_code", "total_time").alias("parking")  # pre-select
result = flights.join(parking, on="flight_code", how="left")
result = result.select(
    F.col("flights.start_time").alias("flight_start"),
    F.col("flights.end_time").alias("flight_end"),
    F.col("parking.total_time").alias("parking_total_time"),
)
```

---

### 10. Use `F.lit(None)` for missing/empty columns — never empty strings or "NA"

Empty strings (`""`) and sentinel strings (`"NA"`, `"N/A"`, `"null"`) pollute downstream filters and force consumers to check multiple null representations.

```python
# bad — ambiguous, downstream must check for "" and None
df = df.withColumn("region", F.lit(""))
df = df.withColumn("region", F.lit("NA"))  # "NA" could mean "North America"

# good — unambiguous null, isNull() / isNotNull() just works
df = df.withColumn("region", F.lit(None).cast("string"))
```

---

## Troubleshooting Job Failures

When a Spark job is actively failing, do not guess — classify the failure first, then jump to the matching row below.

### Step 1 — Pull the diagnostic signals

Before changing anything, gather three sources:

- **Driver log** — stdout/stderr of the `spark-submit` process or driver pod. Surfaces the top-level exception, GC warnings (`GC overhead limit exceeded`), and shuffle-spill notices. This is almost always where the root exception first appears.
- **Executor logs** — reachable from Spark UI → **Executors** tab → `stderr` link per executor, or from the cluster log aggregator: `yarn logs -applicationId <id>` on YARN, the cluster UI on EMR, the driver/executor log panes on Glue, or the cluster log UI on Databricks.
- **Spark UI** — lives on driver port `4040` while the job is running, or in the Spark History Server post-mortem. Key tabs and columns:
  - **Jobs** / **Stages** — stage duration histogram highlights stragglers; max vs median task time exposes skew.
  - **Stages → offending stage → Task Metrics** — `Input Size` and `Shuffle Read` max-vs-median ratios diagnose data skew; `Spill (Memory)` and `Spill (Disk)` diagnose shuffle spill.
  - **Executors** — `GC Time` column flags memory pressure; `Failed Tasks` and `stderr` link per executor.
  - **Storage** — confirms whether a `.cache()` actually fit in memory.

### Step 2 — Classify by symptom

| Symptom | Likely cause | Remediation |
|---|---|---|
| Driver exits with `java.lang.OutOfMemoryError: Java heap space` or `GC overhead limit exceeded`; no executor errors visible | Driver OOM from `.collect()`, broadcast of a too-large table, or JSON schema inference over wide schemas | See **Anti-Pattern #1** (JSON inference). Remove `.collect()` calls; cap broadcast size with `spark.sql.autoBroadcastJoinThreshold`; raise `spark.driver.memory` only as a last resort |
| Executor `ExecutorLostFailure` with `Container killed by YARN for exceeding memory limits` (or the EMR/Glue/Databricks equivalent) | Executor OOM from shuffle spill, an oversized partition, or a memory-hungry UDF | Raise `spark.executor.memory` or `spark.executor.memoryOverhead`; see **Anti-Pattern #5** (shuffle spill); replace Python UDFs with native expressions (**Anti-Pattern #3**); enable AQE (**Best Practice #3**) to coalesce partitions |
| Job hangs on one stage with 99% of tasks complete for a long time | Data skew — a few tasks handle disproportionately large partitions | Spark UI → **Stages** → offending stage → **Task Metrics**: compare max vs median `Input Size` / `Shuffle Read`. See **Anti-Pattern #4** (skew); salt the skewed keys or enable AQE skew join (`spark.sql.adaptive.skewJoin.enabled=true`) |
| Stage shows large `Spill (Disk)` values on the Executors/Stages tab | Insufficient executor memory for the current shuffle partition count | See **Anti-Pattern #5** (spill); raise executor memory or increase `spark.sql.shuffle.partitions`; enable AQE so it coalesces partitions adaptively |
| Repeated `FetchFailedException` during shuffle | Executor crash or network issue during shuffle fetch | Usually downstream of an earlier executor OOM — check prior stages and per-executor `stderr`. If the network is genuinely flaky, raise `spark.network.timeout` and `spark.shuffle.io.retryWait` |
| Job times out with no obvious exception in logs | Shuffle stuck or driver-heavy coordination | Spark UI → **Jobs** → active job → **Stages**: if one stage has been "running" with 0 tasks completing, it is likely a stuck fetch (see row above) or a CPU-starved driver. Enable AQE (`spark.sql.adaptive.enabled=true`), which often rescues stuck plans |
| Serialization error mentioning `PythonUDFRunner` or `PickleException` | Non-picklable closure inside a Python UDF | See **Anti-Pattern #3**. Rewrite as a native expression or a Pandas UDF; avoid referencing `self` or large modules from within a UDF closure |
| `AnalysisException: cannot resolve column` | Typo or special-character column name | See **Anti-Pattern #6**. Switch `df.colA` access to `F.col("col_a")` and verify with `df.printSchema()` |

### Step 3 — Quick recovery attempts, in order

1. **Enable AQE** if it isn't already: `.config("spark.sql.adaptive.enabled", "true")` plus `.config("spark.sql.adaptive.skewJoin.enabled", "true")`. This rescues a surprising number of failures with no code change.
2. **Re-run with 2–4x more executor memory.** A cheap diagnostic — if the job succeeds, the failure is memory-bound and you can go hunt the real cause (spill, skew, UDF) instead of fighting it blind.
3. **Sample the input**: re-run the pipeline with `df.limit(100_000)` inserted early to bisect which transform is actually expensive.
4. **`git log` on the script and Spark config.** If the job used to succeed, the regression almost always traces to an innocuous-looking change — a new column, a broadcast that silently crossed the threshold, a UDF added, or a shuffle-partitions override.

For deeper reading on the Spark UI, metrics, and memory tuning, see the official Spark docs linked under **External References** below.

---

## External References

- [Palantir PySpark Style Guide](https://github.com/palantir/pyspark-style-guide) — opinionated, community-endorsed PySpark coding conventions (1k+ stars)
- [HyperShotgun PySpark Style Guide](https://hypershotgun.com/posts/01_pyspark_style/pyspark_style.html) — editorial expansion of the Palantir guide with import conventions and formatting

---

## Related Skills

- **`aws-glue:use-aws-glue`** — AWS Glue-specific practices (job configuration, worker types, CloudWatch metrics, S3 shuffle, API call tracking, cron monitoring) that build on these PySpark patterns.
