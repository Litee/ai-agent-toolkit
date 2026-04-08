---
name: watch-aws-quota-requests
description: >
  Monitor AWS Service Quotas increase requests for status changes. Use when tracking quota
  increase requests, waiting for quota approvals, or monitoring pending quota changes across
  regions. Two delivery modes: long-poll-with-exit (background, exits on change, re-launch
  in a loop) and cmux-keystrokes (continuous, sends events to CC surface). Triggers on
  "watch quota request", "monitor service quota", "track quota increase", "quota approval
  status", "watch quota status", "notify when quota approved", or any request to monitor
  AWS Service Quotas requests.
---

# AWS Service Quota Request Watcher

Background monitor for AWS Service Quotas change requests. No daemon required. Persists
baseline state across launches via watcher-id so it never re-delivers already-seen changes.

## Prerequisites

- Python 3.10+ with `boto3` installed (activate `.venv` if present)
- AWS credentials configured (`--profile` recommended)
- IAM permissions: `servicequotas:GetRequestedServiceQuotaChange`,
  `servicequotas:ListRequestedServiceQuotaChanges`
- **cmux** optional (required for `cmux-keystrokes` mode only)

## Overview

Quota increase requests are processed over hours or days. Synchronous polling in a
10-minute Bash tool call is impractical.

This skill solves it two ways:

| Environment | Approach |
|-------------|----------|
| **long-poll-with-exit** (default) | Watcher runs in the background via `run_in_background: true`. Exits the moment a status change is detected, printing JSON to stdout. LLM reads the output, re-launches with the same `--watcher-id`, then processes events. Minimal monitoring gap. |
| **cmux-keystrokes** | Watcher runs in a visible split. On every status change, sends a keystroke to the CC surface, waking the LLM to act. Runs indefinitely until max-runtime or signal. |

Note: Service Quota requests are **per-region** (unlike Support which is global). Always
specify `--region` to ensure you are querying the correct endpoint. Omitting `--region`
uses the profile's default region.

---

## Quick Start with cmux

### 1. Identify your surface and workspace

```bash
cmux identify --json
# Use caller.surface_ref (NOT focused.surface_ref — focused drifts as you switch tabs)
# Example: {"caller": {"surface_ref": "surface:80", "workspace_ref": "workspace:47"}, ...}
```

### 2. Create a visible split and launch the watcher

```bash
# Step 1: create split — outputs the new surface ref directly
NEW_SURFACE=$(cmux new-split right | awk '{print $2}')

# Step 2: run the watcher in the split
cmux send --surface "$NEW_SURFACE" "source /path/to/.venv/bin/activate && \
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py watch \
    --request-ids req-abc123 req-def456 \
    --profile myprofile \
    --region us-east-1 \
    --mode cmux-keystrokes \
    --cmux-surface surface:80\n"
```

The watcher:
- Polls the Service Quotas API every 10 minutes (configurable)
- Sends a keystroke to `--cmux-surface` on every status change
- Runs for up to 24 hours, then sends a timeout message and exits

**Example messages delivered to CC:**
```
[QuotaRequest] req-abc123 (Amazon EC2: 'Running On-Demand Standard instances') | CASE_OPENED -> APPROVED (10:05 UTC)
[QuotaRequest] req-def456 (AWS Lambda: 'Concurrent executions') | PENDING -> CASE_OPENED (11:32 UTC)
```

### 3. Optional cmux flags

```bash
    --cmux-notify        # Desktop notification on each status change
    --cmux-status        # Sidebar status badge
    --poll-interval-seconds 300   # Override poll interval (min 60, max 3600)
    --keep-watcher-running        # Keep the watcher split open after exit (default: auto-close after 3s)
```

### 4. Stopping the watcher early

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py stop --watcher-id a1b2c3d4
```

Or list live watchers first:

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py stop --list
```

The watcher split also accepts Ctrl+C directly.

---

## Quick Start without cmux (long-poll-with-exit)

Use `run_in_background: true` on the Bash tool call (no `&` needed).

### First launch

```bash
# Seeds baseline from current state; starts watching.
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py watch \
    --request-ids req-abc123 \
    --profile myprofile \
    --region us-east-1
```

### On receiving output

The watcher exits when a status change is detected and prints JSON:

```json
{
  "events": [
    {
      "request_id": "req-abc123",
      "event_type": "status_changed",
      "summary": "Status: CASE_OPENED -> APPROVED",
      "formatted": "[QuotaRequest] req-abc123 (Amazon EC2: 'Running On-Demand Standard instances') | CASE_OPENED -> APPROVED (10:05 UTC)",
      "details": {
        "service_name": "Amazon EC2",
        "quota_name": "Running On-Demand Standard instances",
        "desired_value": 256.0,
        "previous_status": "CASE_OPENED",
        "new_status": "APPROVED"
      }
    }
  ],
  "watcher_id": "a1b2c3d4",
  "instruction": "Re-launch the watcher FIRST, then process events.\npython3 /path/watch_quota_requests.py watch --request-ids req-abc123 --profile myprofile --watcher-id a1b2c3d4"
}
```

**Important: re-launch BEFORE processing events.** This minimises the gap when no watcher
is running. The `instruction` field shows the exact command.

### Resume after restart

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py watch \
    --request-ids req-abc123 \
    --profile myprofile \
    --watcher-id a1b2c3d4
```

---

## Watch All Pending Requests

Use `--all-pending` to discover and watch every quota request with `PENDING` or
`CASE_OPENED` status, without needing to know the IDs upfront:

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py watch \
    --all-pending \
    --profile myprofile \
    --region us-east-1
```

The watcher prints all discovered request IDs at startup. On the next launch (via
`--watcher-id`), pass the specific IDs if you want to narrow the scope — or use
`--all-pending` again to re-discover.

---

## Session Resilience

After a session restart, check what was being monitored and resume.

### Discover tracked watchers

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py status --list
```

Output example:
```
WATCHER ID   MODE                   REQUESTS STATUS             LAST POLL                 PID
a1b2c3d4     long-poll-with-exit    2        WATCHER_STOPPED    2026-04-08T10:05:00+00:00 PID 12345 (dead)
```

### Re-launch a dead watcher

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py watch \
    --request-ids req-abc123 req-def456 \
    --profile myprofile \
    --watcher-id a1b2c3d4
```

### Inspect a specific watcher

```bash
python3 ${SKILL_DIR}/scripts/watch_quota_requests.py status --watcher-id a1b2c3d4
```

---

## cmux Surface Delivery

The watcher sends keystrokes to `--cmux-surface`, optionally using `--cmux-workspace` for cross-workspace delivery. If the surface is unreachable (e.g. session restarted), the watcher exits with a clear error message and restart command. To resume, get fresh refs via `cmux identify --json` and re-launch with the new `--cmux-surface` and `--cmux-workspace` values.

---

## AWS Profile Configuration

Use `--profile` to specify which AWS credentials profile to use.

Prefer `--profile` over environment variables (`AWS_PROFILE`) — it is explicit, auditable,
and eliminates the risk of accidentally querying with wrong credentials.

**Credential refresh:** The watcher recreates its boto3 session on every poll, so
short-lived credentials (STS/SSO) are refreshed automatically as long as the underlying
profile handles refresh.

**Regional note:** Service Quota requests are per-region. A request submitted in `us-west-2`
will not appear when querying `us-east-1`. Always pass `--region` explicitly.

If the watcher exits with `CREDENTIAL_EXPIRED`:
1. Refresh credentials (`aws sso login`, `aws-vault`, etc.)
2. Re-launch with the same `--watcher-id`

---

## Script Parameters

### `watch` — Start watcher

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--request-ids` | yes (unless `--all-pending`) | — | One or more quota request IDs |
| `--all-pending` | yes (unless `--request-ids`) | — | Watch all PENDING/CASE_OPENED requests |
| `--profile` | yes | — | AWS credentials profile |
| `--region` | no | profile default | AWS region (quotas are per-region) |
| `--mode` | no | `long-poll-with-exit` | `long-poll-with-exit` or `cmux-keystrokes` |
| `--poll-interval-seconds` | no | 600 | Poll frequency: min 60, max 3600 |
| `--watcher-id` | no | auto-generated | 8-char hex; pass to resume a previous run |
| `--max-runtime-hours` | no | 24 | Max runtime before watcher exits requesting restart |
| `--cmux-surface` | required for cmux mode | — | cmux surface ref of CC session (e.g. `surface:80`) |
| `--cmux-workspace` | no | auto-detected | cmux workspace ref; auto-detected via `cmux identify` |
| `--cmux-notify` | no | off | Enable desktop notifications |
| `--cmux-status` | no | off | Enable cmux sidebar status badge |
| `--keep-watcher-running` | no | off | Keep watcher split open after exit (default: auto-close after 3s) |

State file: `~/.claude/plugin-data/aws-query-tools/watch-aws-quota-requests/watcher-<id>.json`

### `status` — Show watcher state

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | no | Show a specific watcher's state file |
| `--list` | no | List all tracked watchers (default if no flags) |

### `stop` — Stop a running watcher

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | yes (unless `--list`) | Watcher ID to stop (sends SIGTERM) |
| `--list` | no | List live watchers (does not stop anything) |

---

## Resources

### scripts/watch_quota_requests.py

Main script with three subcommands:
- `watch`: Polling monitor. Seeds baselines on first launch. Exits on change (long-poll)
  or sends keystrokes continuously (cmux). Handles throttling, credential expiry, and
  24-hour timeout. Removes terminal-state requests from the watch list automatically.
- `status`: Read-only state inspection. Lists all tracked watchers or shows a specific one.
- `stop`: Sends SIGTERM to a running watcher PID from its state file.

State files: `~/.claude/plugin-data/aws-query-tools/watch-aws-quota-requests/`
(auto-cleaned after 30 days)

### references/best-practices.md

Load when:
- Finding quota request IDs or service/quota codes
- Requesting a quota increase via CLI
- Understanding the quota request status lifecycle
- Looking up common quota codes (EC2, Lambda, ELB, VPC)
- Troubleshooting `CASE_CLOSED` vs `DENIED` vs `NOT_APPROVED`
