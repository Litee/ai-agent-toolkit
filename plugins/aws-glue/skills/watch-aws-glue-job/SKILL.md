---
name: watch-aws-glue-job
description: >
  Monitor AWS Glue job execution for state changes with background notifications.
  Use when watching long-running Glue jobs, checking Glue job status, or setting
  up background Glue job monitoring. Supports three modes: background long-poll-with-exit
  (re-launch in loop, no cmux/tmux needed), visible cmux split with keystroke notifications,
  and tmux-keystrokes (no cmux dependency). Includes CloudWatch metrics (CPU, heap, records,
  executors). Triggers on "watch glue job", "monitor glue run", "check glue status",
  "glue job finished", "background glue monitor", or any request to track an AWS Glue job run.
---

# AWS Glue Job Watcher

## Prerequisites

- Python 3 with `boto3` installed (activate `.venv` if present)
- AWS account with Glue access
- AWS credentials configured (`--profile` recommended)
- **cmux** — optional, required only for `cmux-keystrokes` mode
- **tmux** — optional, required only for `tmux-keystrokes` mode

## Overview

AWS Glue jobs run for minutes to hours. The LLM Bash tool has a 10-minute timeout,
making synchronous polling impractical for long jobs.

This skill solves it three ways:

| Environment | Approach |
|-------------|----------|
| **No cmux/tmux** (default) | `watch --mode long-poll-with-exit`. Runs in background, exits with JSON when the job state changes. Re-launch in a loop after processing output. |
| **cmux** (recommended) | `watch --mode cmux-keystrokes` runs in a visible terminal split. On every state change, it sends a keystroke message to the Claude Code terminal, waking the LLM to act. Poll output is visible in the split — no tokens consumed watching it. |
| **tmux** | `watch --mode tmux-keystrokes` — same as cmux-keystrokes but uses `tmux send-keys` for delivery. No cmux dependency. Requires `--tmux-pane` (e.g. `main:0.0`). |

This skill monitors existing job runs. Use other skills (e.g. `use-aws-glue`) for job submission.

---

## Quick Start without cmux

### Background long-poll-with-exit

Run in background using `run_in_background: true` (never use `&` or `nohup`):

```bash
# First launch — auto-generates a watcher ID
python3 ${SKILL_DIR}/scripts/watch_glue_job.py watch \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile
# Outputs: [Glue Watcher] ID: a1b2c3d4 | ...
# Prints exact re-launch command to stderr
```

When the job state changes, the watcher prints JSON to stdout and exits 0:

```json
{
  "events": [
    {
      "job_name": "my-etl-job",
      "run_id": "jr_abc1234567890abc",
      "event_type": "state_changed",
      "previous_state": "STARTING",
      "new_state": "RUNNING",
      "summary": "Glue job 'my-etl-job' (run jr_abc123) state changed: STARTING -> RUNNING. Elapsed: 2m 15s.",
      "formatted": "[Glue] my-etl-job (jr_abc12345) | STARTING -> RUNNING (10:05 UTC)",
      "execution_time_seconds": 135,
      "dpu_seconds": 0,
      "error_message": ""
    }
  ],
  "watcher_id": "a1b2c3d4",
  "instruction": "Re-launch the watcher FIRST, then process events.\npython3 ..."
}
```

**Important:** Always re-launch the watcher before processing events. This prevents missing
state changes that arrive while you're processing the previous output.

---

## Quick Start with tmux

### 1. Find your tmux pane

```bash
tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index} #{pane_title}"
# Identify the pane running Claude Code — e.g. main:0.0
```

### 2. Launch the watcher

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_job.py watch \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile \
    --mode tmux-keystrokes \
    --tmux-pane main:0.0
```

The watcher sends events directly to the specified tmux pane. No cmux needed.

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
python3 ${SKILL_DIR}/scripts/watch_glue_job.py watch \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile \
    --mode cmux-keystrokes \
    --cmux-surface surface:80\n"
```

The watcher:
- Polls Glue every 5 minutes (configurable via `--poll-interval-seconds`)
- Prints a timestamped status line with CloudWatch metrics on every poll (visible in the split)
- Sends a keystroke to `--cmux-surface` on every state change
- Runs for up to 24 hours (configurable via `--max-runtime-hours`)
- Auto-closes the watcher split on exit (unless `--keep-watcher-running`)

**Example poll output in the watcher split:**
```
[10:05 UTC] RUNNING | exec: 19m 2s | DPU-s: 1,140 | cpu: workers: 42% / driver: 8% | heap: 31% | rec: 12.4M in / 9.1M out | exec: 8/10
```

**Example messages the LLM will receive:**
```
[Glue] my-etl-job (jr_abc12345) | STARTING -> RUNNING (10:05 UTC)
[Glue] my-etl-job (jr_abc12345) | RUNNING -> SUCCEEDED (11:42 UTC)
[Glue Watcher] 5 consecutive AWS credential errors — backing off. Refresh credentials; watcher will recover automatically.
[Glue Watcher] AWS credentials recovered — resuming.
```

### 3. Optional flags

```bash
    --no-cloudwatch-metrics      # Disable CW metrics (default: enabled; requires Glue 2.0+ Spark)
    --cmux-notify                # Desktop notification on each state change
    --cmux-status                # Sidebar status badge (key: glue-<watcher-id-prefix>)
    --poll-interval-seconds 60   # Override poll interval (min 60, max 3600)
    --keep-watcher-running       # Keep the watcher split open after exit (default: auto-close after 3s)
    --max-runtime-hours 48       # Override 24h default
```

### 4. Stopping the watcher early

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_job.py stop --list
python3 ${SKILL_DIR}/scripts/watch_glue_job.py stop --watcher-id a1b2c3d4
```

Or send Ctrl+C directly to the watcher split.

---

## Session Resilience

After a session restart, check what watchers are running:

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_job.py status --list
```

Output example:
```
WATCHER ID   MODE                   JOB                           STATE        LAST POLL              PID
a1b2c3d4     long-poll-with-exit    my-etl-job                    RUNNING      2026-04-08T10:05:00Z   12345 (dead)
  launch: python3 /path/watch_glue_job.py watch --job-name my-etl-job --run-id jr_abc123 --watcher-id a1b2c3d4
```

If the watcher PID is dead but the job is still running, re-launch using the `launch` command
from the status output. Pass `--watcher-id` to reuse existing state.

### One-shot status check (no active watcher needed)

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_job.py status \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile
```

Output:
```
Job:        my-etl-job
Run ID:     jr_abc1234567890abc
State:      RUNNING
Elapsed:    42m 15s
DPU-secs:   3,024
Started:    2026-04-08T10:00:00+00:00
```

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

**Credential errors:** The watcher never exits on credential errors. It backs off linearly
(`min(60 * consecutive_errors, 3600)` seconds) and keeps retrying. After 5 consecutive
failures it notifies via the bridge (cmux/tmux) or logs to stderr (long-poll). When
credentials recover, it sends a "Credentials recovered" message and resumes normally.

---

## Script Parameters

### `watch` — Start Watching

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--job-name` | yes | — | Glue job name |
| `--run-id` | yes | — | Glue job run ID (e.g. `jr_abc123`) |
| `--profile` | yes | — | AWS credentials profile |
| `--region` | no | profile default | AWS region |
| `--mode` | no | `long-poll-with-exit` | `long-poll-with-exit`, `cmux-keystrokes`, or `tmux-keystrokes` |
| `--poll-interval-seconds` | no | `300` | Poll frequency: min 60, max 3600 |
| `--watcher-id` | no | auto-generated | Reuse existing state from a previous run |
| `--max-runtime-hours` | no | `24` | Max runtime before auto-exit |
| `--no-cloudwatch-metrics` | no | off | Disable CloudWatch metrics (requires Glue 2.0+ Spark) |
| `--cmux-surface` | cmux only | — | cmux surface ref of the CC session to notify |
| `--cmux-workspace` | no | auto-detected | cmux workspace ref |
| `--cmux-notify` | no | off | Enable desktop notifications |
| `--cmux-status` | no | off | Enable cmux sidebar status badge |
| `--keep-watcher-running` | no | off | Keep watcher split open after exit |
| `--tmux-pane` | tmux only | — | tmux pane target (e.g. `main:0.0`) |

State file: `~/.claude/plugin-data/aws-glue/watch-aws-glue-job/state-<watcher-id>.json`
PID file: `~/.claude/plugin-data/aws-glue/watch-aws-glue-job/watcher-<watcher-id>.pid`

### `status` — Show Watcher State or One-Shot API Check

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | no | Show full state for a specific watcher ID |
| `--list` | no | List all tracked watchers (default if no other args) |
| `--job-name` | no | Glue job name (for live API check) |
| `--run-id` | no | Glue run ID (for live API check) |
| `--profile` | no | AWS profile (required for live API check) |
| `--region` | no | AWS region |

### `stop` — Stop a Running Watcher

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | yes (unless `--list`) | Watcher ID to stop |
| `--list` | no | List live watchers without stopping |

---

## Resources

### scripts/watch_glue_job.py

Main script with three subcommands:
- `watch`: Polling watcher. Supports `long-poll-with-exit` (background JSON output, exits on
  state change), `cmux-keystrokes` (visible split with keystroke delivery), and
  `tmux-keystrokes` (no cmux dependency). Resilient credential handling (linear backoff, no
  forced exit). SIGUSR1 causes clean shutdown (exit 0) in continuous modes. CloudWatch metrics
  (CPU, heap, records, executors) on every poll. Configurable max runtime.
- `status`: Read-only state inspection. Show one watcher, list all, or one-shot live API check.
- `stop`: Send SIGTERM to a live watcher PID.

State files: `~/.claude/plugin-data/aws-glue/watch-aws-glue-job/` (auto-cleaned after 30 days)

### references/best-practices.md

Load when:
- Diagnosing a failed job (error messages, common causes)
- Selecting worker types or sizing
- Working with job bookmarks
- Querying Glue CloudWatch logs
- Looking up useful AWS CLI commands for Glue
