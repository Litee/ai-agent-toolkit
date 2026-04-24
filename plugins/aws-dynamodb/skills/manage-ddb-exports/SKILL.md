---
name: manage-ddb-exports
description: "Use when asked to 'export a DynamoDB table', 'dump DDB to S3', 'convert DDB export to Parquet', 'share DDB data with another account', or 'do a DDB table dump'. Guides the full lifecycle: exporting DDB tables to S3 via ExportTableToPointInTime, converting DynamoDB JSON to Parquet, filtering exported data, and sharing datasets cross-account with scoped S3 bucket policies."
---

# manage-ddb-exports — DynamoDB Export Lifecycle

> Found major gaps or factual errors in this skill? Report it via the `local-skill-issues-tracker:use-local-skills-issue-tracker` skill (if available).

## Overview

This skill covers the full lifecycle of exporting DynamoDB tables to S3, converting formats, filtering, and sharing data cross-account. The four phases are:

1. **Export** — snapshot the table to S3 via `ExportTableToPointInTime`
2. **Convert** — flatten DynamoDB JSON to Parquet for analysis
3. **Filter** — apply predicates after export (cannot filter during export)
4. **Share** — grant cross-account access scoped to the exact S3 prefix

---

## Phase 1: Export DDB Table to S3

Use `ExportTableToPointInTime` (preferred — consistent, no table capacity impact):

```bash
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:<region>:<account>:table/<TableName> \
  --s3-bucket <bucket> \
  --s3-prefix <project-level-prefix>/<run-level-prefix>/ \
  --export-format DYNAMODB_JSON \
  --profile <aws-profile>
```

`--export-format` options: `DYNAMODB_JSON` (default) or `ION`.

Example:
```
s3://my-bucket/ddb-exports/my-table/
```

DynamoDB automatically writes the export under `<prefix>/AWSDynamoDB/<export-id>/data/` — do not include this subdirectory in the prefix you supply.

### Monitor Export Status

```bash
aws dynamodb describe-export \
  --export-arn <arn-from-export-command> \
  --profile <aws-profile>
# Poll until ExportStatus = COMPLETED (can take minutes to hours for large tables)
```

For large tables (100M+ items) that can take 1–3 hours, use a cron task (every 30 minutes) to poll `describe-export` rather than polling in a tight loop.

---

## Phase 2: Format Conversion (DDB JSON → Parquet)

DDB JSON export nests all values with type descriptors:

```json
{"Item": {"id": {"S": "abc"}, "count": {"N": "42"}, "active": {"BOOL": true}}}
```

Flatten before analysis. The type descriptors are: `S` (string), `N` (number as string), `B` (binary/base64), `BOOL`, `NULL`, `L` (list), `M` (map), `SS`/`NS`/`BS` (sets).

**Important:** Numbers are exported as strings in DDB JSON — cast to numeric types after flattening.

### Option A: AWS Glue Job (preferred for large tables)

Use the `aws-glue:use-aws-glue` skill. Apply `DynamicFrame` with `unnest_ddb_json` transform or write custom flattening logic that maps DDB type descriptors to flat columns.

### Option B: PySpark Locally (small tables, <1 GB)

Use the `pyspark:use-pyspark` skill with `boto3` to read from S3. Flatten the nested DDB JSON structure into a flat schema before writing to Parquet.

---

## Phase 3: Filtering

Filtering happens **after** export — there is no way to filter during the export itself.

Options:
- **Athena** (see `aws-athena:query-aws-athena` skill): query the Parquet directly in S3 without moving data
- **Glue job with pushdown predicates**: filter during the DDB JSON → Parquet conversion step

Common filter patterns:

```sql
-- By partition key range
WHERE pk >= 'a' AND pk < 'b'

-- By attribute presence
WHERE attribute IS NOT NULL

-- Random 1% sample
WHERE rand() < 0.01
```

---

## Phase 4: Cross-Account Sharing

Grant access scoped to the exact prefix — never the whole bucket.

```json
{
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::<target-account>:root"},
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": [
    "arn:aws:s3:::<bucket>/<prefix>/*",
    "arn:aws:s3:::<bucket>"
  ],
  "Condition": {
    "StringLike": {
      "s3:prefix": "<prefix>/*"
    }
  }
}
```

`ListBucket` requires the bucket-level ARN (`arn:aws:s3:::<bucket>`) but must be scoped with a `Condition` on `s3:prefix` — otherwise it grants list access to the entire bucket.

---

## Gotchas

- DDB exports are point-in-time snapshots, NOT immediately consistent — the export timestamp is in the `describe-export` response; record it for downstream consumers.
- The `AWSDynamoDB/<export-id>/data/` subdirectory is created automatically by DynamoDB — do not include it in the prefix you pass to the export command.
- Numbers are exported as strings in DDB JSON (`"N": "42"`) — always cast to numeric types after flattening; analysis tools will not cast implicitly.
- Large table exports (100M+ items) can take 1–3 hours — use a cron task (every 30 minutes) to poll `describe-export` rather than polling in a tight loop.
- Cross-account `ListBucket` requires both the bucket ARN and a `Condition` block to scope to the prefix — the bucket ARN alone grants list access to the whole bucket.
- DDB JSON type descriptors (`S`, `N`, `B`, `BOOL`, `NULL`, `L`, `M`, `SS`, `NS`, `BS`) must all be handled in flattening logic; missing a type causes silent data loss for attributes of that type.

---

## Error Handling

Check `ExportStatus` in the `describe-export` response. A status of `FAILED` means the export did not complete — the `FailureCode` and `FailureMessage` fields contain the root cause.

Common failure modes and remediation:

| Failure | Symptom / FailureCode | Fix |
|---|---|---|
| S3 write permission | `S3NoSuchBucket` or `AccessDenied` | Verify the DynamoDB service principal (`dynamodb.amazonaws.com`) has `s3:PutObject` on the destination bucket/prefix |
| KMS key access | `KMSKeyAccessDenied` | Grant `kms:GenerateDataKey` and `kms:Decrypt` to the DynamoDB service principal on the CMK |
| Throttling / internal error | `INTERNAL_SERVER_ERROR` | Retry the export — transient AWS-side errors are rare but do occur; back off and retry |
| Invalid export time | `PointInTimeRecoveryUnavailable` | The requested export time falls outside the PITR window (35 days max); choose a more recent timestamp or enable PITR first |
| Insufficient S3 capacity / large object limit | Export stalls or partial data | Ensure the S3 bucket has no object-count or storage-class restrictions; check S3 bucket policy for `Deny` conditions |

Retry strategy for transient failures:

```bash
# Re-issue the same export command with a fresh timestamp
aws dynamodb export-table-to-point-in-time \
  --table-arn <arn> \
  --s3-bucket <bucket> \
  --s3-prefix <prefix>/ \
  --export-format DYNAMODB_JSON \
  --profile <aws-profile>
```

There is no in-place retry — each call creates a new export job. Clean up any partial output from the failed export before consuming downstream to avoid mixing partial and complete data.

---

## Related Skills

- `aws-glue:use-aws-glue` — submit and manage AWS Glue PySpark jobs for large-scale format conversion
- `pyspark:use-pyspark` — PySpark patterns for local/small-scale conversion
- `aws-athena:query-aws-athena` — query exported Parquet directly in S3 without moving data
