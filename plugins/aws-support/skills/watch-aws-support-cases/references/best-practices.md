# AWS Support Case Best Practices

## Case Status Lifecycle

AWS Support cases move through the following statuses:

| Status | Description |
|--------|-------------|
| `unassigned` | Case submitted, not yet picked up by a support engineer |
| `work-in-progress` | Engineer is actively working the case |
| `opened` | Case open and being tracked |
| `pending-customer-action` | AWS is waiting for a response, clarification, or action from you |
| `pending-amazon-action` | You have responded; AWS is working on it |
| `resolved` | AWS has resolved the issue and closed the case |
| `closed` | Case is closed (no further updates expected) |

**Terminal statuses**: `resolved`, `closed` — the watcher stops generating events for these.

**Customer action tip**: When a case reaches `pending-customer-action`, replying promptly
avoids the case being auto-closed after an inactivity period (typically 5–7 days).

---

## Severity Levels and Expected Response Times

| Severity Code | Name | Initial Response |
|--------------|------|------------------|
| `critical` | Critical | 15 minutes (Enterprise only, 24/7) |
| `urgent` | Urgent / Production system down | 1 hour (Business/Enterprise, 24/7) |
| `high` | High / Production system impaired | 4 hours |
| `normal` | Normal / Non-critical | 12 hours |
| `low` | Low / General question | 24 hours |

Response times are SLA targets for the **first** response. Follow-up times vary.

Severity can be changed after case creation via the AWS Console or API. A severity escalation
(`normal` -> `urgent`) will trigger a `severity_changed` event in the watcher.

---

## Useful AWS CLI Commands

### List open support cases

```bash
aws support describe-cases \
    --include-resolved-cases false \
    --profile my-profile \
    --region us-east-1
```

### Describe a specific case with communications

```bash
aws support describe-cases \
    --case-id-list case-123456-2026-abcd \
    --include-communications \
    --include-resolved-cases true \
    --profile my-profile \
    --region us-east-1
```

### Fetch all communications for a case

```bash
aws support describe-communications \
    --case-id case-123456-2026-abcd \
    --profile my-profile \
    --region us-east-1
```

### Add a reply to a case

```bash
aws support add-communication-to-case \
    --case-id case-123456-2026-abcd \
    --communication-body "Here is the additional information you requested..." \
    --profile my-profile \
    --region us-east-1
```

### Resolve a case

```bash
aws support resolve-case \
    --case-id case-123456-2026-abcd \
    --profile my-profile \
    --region us-east-1
```

A resolved case can be **reopened** by adding a new communication to it within 14 days.
After 14 days you need to open a new case.

### List available severity levels (for your support plan)

```bash
aws support describe-severity-levels \
    --language en \
    --profile my-profile \
    --region us-east-1
```

### Create a new support case

```bash
aws support create-case \
    --subject "ELB health check failing after recent deployment" \
    --service-code "elastic-load-balancing" \
    --severity-code "high" \
    --category-code "general-guidance" \
    --communication-body "Description of the issue..." \
    --language "en" \
    --issue-type "technical" \
    --profile my-profile \
    --region us-east-1
```

To find valid `--service-code` and `--category-code` values:

```bash
aws support describe-services --profile my-profile --region us-east-1
```

---

## Rate Limiting

The AWS Support API has modest rate limits:

- `DescribeCases`: ~1 request/second
- `DescribeCommunications`: ~1 request/second

The watcher's default poll interval of **300 seconds** is well within these limits even when
watching dozens of cases (all case IDs are batched into a single `describe-cases` call per
poll cycle).

If you hit `ThrottlingException`, the watcher automatically doubles the poll interval (capped
at 3600s) and retries.

---

## Credential Requirements

The following IAM permissions are required:

```json
{
  "Effect": "Allow",
  "Action": [
    "support:DescribeCases",
    "support:DescribeCommunications",
    "support:DescribeSeverityLevels"
  ],
  "Resource": "*"
}
```

For `--all-open` (auto-discovery), no additional permissions are needed — `DescribeCases`
without `caseIdList` returns all cases.

**Support plan requirement**: AWS Support API calls (other than `DescribeSeverityLevels`)
require a **Business or Enterprise** support plan. Accounts on Basic or Developer plans
receive `SubscriptionRequiredException`. This is an account-level plan requirement, not an
IAM permission issue. Remediation: upgrade to Business or Enterprise Support, or switch to an AWS account with the required support plan.

---

## Regional Note

The AWS Support API endpoint is **global but hosted in `us-east-1`**:

```
https://support.us-east-1.amazonaws.com
```

All API calls must target `us-east-1` regardless of where your resources are located.
The watcher always uses the `us-east-1` endpoint internally. Passing `--region ap-southeast-1`
will trigger a warning but the watcher will still call the `us-east-1` endpoint correctly.

---

## Case ID Format

AWS Support case IDs follow this format:

```
case-<account-id-prefix>-<year>-<hex-suffix>
```

Example: `case-123456-2026-abcd1234`

The **display ID** (shown in the AWS Console URL and email subjects) is a numeric string like
`1234567890`. The watcher tracks using the full `caseId` from the API but displays the
`displayId` in event output for readability.

---

## Best Practices

1. **Provide context early**: The more detail in the initial case, the faster the first response.
   Attach logs, error messages, resource IDs, and timestamps upfront.

2. **Reply promptly to `pending-customer-action`**: Cases with no customer response may be
   auto-closed. The watcher will alert you when this status is set.

3. **Escalate appropriately**: If a case is taking longer than the SLA, you can increase
   severity or request escalation via the Console. A severity change will trigger a
   `severity_changed` event.

4. **Use case references**: When opening related cases, reference the original case ID in
   the description to help support engineers see the context.

5. **Poll interval**: 300s (5 minutes) is the recommended default. AWS support engineers
   typically do not respond faster than this. Lower values (min 60s) are available but
   unnecessary for normal use.
