---
name: watch-aws-support-cases
description: >
  Monitor AWS Support cases for status changes, severity changes, and new communications.
  Use when watching open support cases, tracking case resolution, or getting notified about
  AWS support replies. Supports two modes: background long-poll-with-exit (re-launch in loop)
  and visible cmux split with keystroke notifications. Requires Business or Enterprise AWS
  support plan. Triggers on "watch support case", "monitor AWS support", "track support ticket",
  "notify on support reply", "watch case status", "support case update", or any request to
  monitor AWS Support cases.
---

# AWS Support Case Watcher

## Prerequisites

- Python 3 with `boto3` installed (activate `.venv` if present)
- AWS account with **Business or Enterprise** support plan
  - `SubscriptionRequiredException` is raised on Basic and Developer plans
- AWS credentials configured (`--profile` recommended)
- **cmux** — optional, required only for `cmux-keystrokes` mode

## Overview

AWS Support cases can stay open for hours to days. The LLM Bash tool has a 10-minute timeout,
making synchronous polling impractical for ongoing case monitoring.

This skill solves it two ways:

| Environment | Approach |
|-------------|----------|
| **cmux** (recommended) | `watch --mode cmux-keystrokes` runs in a visible terminal split. On every change, it sends a keystroke message to the Claude Code terminal, waking the LLM to act. Poll output is visible in the split — no tokens consumed watching it. |
| **No cmux** | `watch --mode long-poll-with-exit` (default). Runs in background, exits with JSON when changes are detected. Re-launch in a loop after processing output. Or use a team agent with `CronCreate` for hands-off polling. |

The Support API is global but its endpoint is `us-east-1` only — the `--region` flag is
accepted for completeness but the client always calls `us-east-1`.

---

## Quick Start with cmux

### 1. Identify your surface and workspace

```bash
cmux identify --json
# Use caller.surface_ref (NOT focused.surface_ref — focused changes as you switch tabs)
# Example: {"caller": {"surface_ref": "surface:80", "workspace_ref": "workspace:47"}, ...}
```

### 2. Create a visible split and launch the watcher

```bash
# Step 1: create a side-by-side split
NEW_SURFACE=$(cmux new-split right | awk '{print $2}')

# Step 2: send the watch command to the split
cmux send --surface "$NEW_SURFACE" "source /path/to/.venv/bin/activate && \
python3 ${SKILL_DIR}/scripts/watch_support_cases.py watch \
    --case-ids case-123456-2026-abcd \
    --profile my-aws-profile \
    --mode cmux-keystrokes \
    --cmux-surface surface:80\n"
```

The watcher:
- Polls every 5 minutes (configurable via `--poll-interval-seconds`)
- Prints a timestamped heartbeat every 5 minutes (visible in the split)
- Sends a keystroke to `--cmux-surface` on every status, severity, or communication change
- Runs for up to 24 hours (configurable via `--max-runtime-hours`)
- Auto-closes the watcher split on exit (unless `--keep-watcher-running`)

**Example messages the LLM will receive:**
```
[Support] #1234567890 ('ELB health check failing') status: opened -> pending-customer-action (10:05 UTC)
[Support] #1234567890 ('ELB health check failing') new 1 communication(s) (10:42 UTC)
[Support Watcher v1.0.0] 2 consecutive AWS credential errors. Refresh credentials, then re-launch: ...
```

### 3. Optional flags

```bash
    --cmux-notify                # Desktop notification on each change
    --cmux-status                # Sidebar status badge
    --poll-interval-seconds 60   # Override poll interval (min 60, max 3600)
    --keep-watcher-running       # Keep split open after exit
    --max-runtime-hours 48       # Override 24h default
```

### 4. Stopping the watcher early

```bash
python3 ${SKILL_DIR}/scripts/watch_support_cases.py stop --list
python3 ${SKILL_DIR}/scripts/watch_support_cases.py stop --watcher-id a1b2c3d4
```

Or send Ctrl+C directly to the watcher split.

---

## Quick Start without cmux

### Background long-poll-with-exit

Run in background using `run_in_background: true` (never use `&` or `nohup`):

```bash
# First launch — generates a watcher ID
python3 ${SKILL_DIR}/scripts/watch_support_cases.py watch \
    --case-ids case-123456-2026-abcd \
    --profile my-aws-profile
# Outputs: [Support Watcher] ID: a1b2c3d4 | ...
# Prints exact re-launch command to stderr
```

When changes are detected, the watcher prints JSON to stdout and exits 0:

```json
{
  "events": [
    {
      "case_id": "case-123456-2026-abcd",
      "display_id": "1234567890",
      "event_type": "status_changed",
      "summary": "Case #1234567890 status changed: opened -> pending-customer-action",
      "formatted": "[Support] #1234567890 | status: opened -> pending-customer-action (10:05 UTC)",
      "subject": "ELB health check failing"
    }
  ],
  "watcher_id": "a1b2c3d4",
  "instruction": "Re-launch the watcher FIRST, then process events.\npython3 ..."
}
```

**Important:** Always re-launch the watcher before processing events. This prevents missing
changes that arrive while you're processing the previous batch.

### Credential expiry (exit code 2)

```json
{
  "error": "CREDENTIAL_EXPIRED",
  "message": "2 consecutive AWS credential errors. Refresh credentials and re-launch.",
  "watcher_id": "a1b2c3d4",
  "instruction": "Refresh credentials, then re-launch: python3 ..."
}
```

### Team Agent Monitoring (hands-off background polling)

For fully autonomous background polling, spawn a **team agent** with `CronCreate`:

```
Check AWS Support case case-123456-2026-abcd for changes.
Last known status: opened. Watcher ID: a1b2c3d4.

Run:
  python3 ${SKILL_DIR}/scripts/watch_support_cases.py watch \
      --case-ids case-123456-2026-abcd \
      --profile my-profile \
      --watcher-id a1b2c3d4

If events returned (exit 0):
  - Re-launch the watcher FIRST (as the instruction says)
  - SendMessage to main agent with event summary
  - If status is resolved/closed: CronDelete this job, done
  - Otherwise: CronDelete, re-create at same interval with updated state

If no output (still polling): CronDelete, re-create with same watcher-id
Stop after 7 days total.
```

---

## Watching All Open Cases

Use `--all-open` to auto-discover all non-terminal cases and watch them together:

```bash
python3 ${SKILL_DIR}/scripts/watch_support_cases.py watch \
    --all-open \
    --profile my-aws-profile
```

The watcher re-discovers open cases on every poll, so newly opened cases are picked up
automatically. Cases that reach resolved/closed status stop generating events.

---

## Session Resilience

After a session restart, check what watchers are running:

```bash
python3 ${SKILL_DIR}/scripts/watch_support_cases.py status --list
```

Output example:
```
WATCHER ID   MODE                   CASES  STATUS     LAST POLL              PID
a1b2c3d4     long-poll-with-exit    2      watching   2026-04-08T10:05:00Z   12345 (dead)
  launch: python3 /path/watch_support_cases.py watch --case-ids ... --watcher-id a1b2c3d4
```

If the watcher PID is dead but cases are still open, re-launch using the `launch` command
from the status output. Pass `--watcher-id` to reuse existing baseline state and avoid
re-detecting changes that already happened.

---

## cmux Surface Delivery

The watcher sends keystrokes to `--cmux-surface`, optionally using `--cmux-workspace` for cross-workspace delivery. If the surface is unreachable (e.g. session restarted), the watcher exits with a clear error message and restart command. To resume, get fresh refs via `cmux identify --json` and re-launch with the new `--cmux-surface` and `--cmux-workspace` values.

---

## AWS Profile Configuration

Use `--profile` to specify which AWS credentials profile to use.

**Prefer `--profile` over environment variables** (`AWS_PROFILE`) because:
- Explicit and visible in command history
- No risk of accidentally using wrong credentials

**Credential refresh:** The watcher recreates its boto3 session on every poll, so short-lived
credentials (STS/SSO) are refreshed automatically as long as the underlying profile refreshes
them (e.g. `aws-vault`, `aws sso login`).

If exit code 2 (CREDENTIAL_EXPIRED):
1. Refresh credentials
2. Re-launch using the `instruction` field in the JSON output

---

## Script Parameters

### `watch` — Start Watching

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--case-ids` | yes* | — | Case IDs to watch (e.g. `case-123456-2026-abcd`) |
| `--all-open` | yes* | — | Auto-discover all non-terminal cases |
| `--profile` | yes | — | AWS credentials profile |
| `--region` | no | `us-east-1` | AWS region (Support API uses us-east-1 regardless) |
| `--mode` | no | `long-poll-with-exit` | `long-poll-with-exit` or `cmux-keystrokes` |
| `--poll-interval-seconds` | no | `300` | Poll frequency: min 60, max 3600 |
| `--watcher-id` | no | auto-generated | Reuse existing state from a previous run |
| `--max-runtime-hours` | no | `24` | Max runtime before auto-exit |
| `--cmux-surface` | cmux only | — | cmux surface ref of the CC session to notify |
| `--cmux-workspace` | no | auto-detected | cmux workspace ref |
| `--cmux-notify` | no | off | Enable desktop notifications |
| `--cmux-status` | no | off | Enable cmux sidebar status badge |
| `--keep-watcher-running` | no | off | Keep watcher split open after exit |

\* Exactly one of `--case-ids` or `--all-open` is required.

State file: `~/.claude/plugin-data/aws-query-tools/watch-aws-support-cases/state-<watcher-id>.json`
PID file: `~/.claude/plugin-data/aws-query-tools/watch-aws-support-cases/watcher-<watcher-id>.pid`

### `status` — Show Watcher State

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | no | Show full state for a specific watcher |
| `--list` | no | List all tracked watchers (default if no `--watcher-id`) |

### `stop` — Stop a Running Watcher

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | yes (unless `--list`) | Watcher ID to stop |
| `--list` | no | List live watchers without stopping |

---

## Resources

### scripts/watch_support_cases.py

Main script with three subcommands:
- `watch`: Polling watcher. Supports `long-poll-with-exit` (background JSON output) and `cmux-keystrokes` (visible split with keystroke delivery). Full cmux fallback chain. Configurable max runtime.
- `status`: Read-only state inspection. Show one watcher or list all.
- `stop`: Send SIGTERM to a live watcher PID.

### references/best-practices.md

Load when:
- Looking up AWS Support case status lifecycle
- Checking severity levels and expected response times
- Finding useful AWS CLI commands for Support cases
- Diagnosing `SubscriptionRequiredException` or rate limiting
