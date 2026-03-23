---
name: query-aws-glue
description: Monitor AWS Glue job execution with visible split-terminal output and
  smart state-change notifications. Use when watching long-running Glue jobs, checking
  Glue job status, or setting up background Glue job monitoring. With cmux, runs in
  a visible split pane and sends keystrokes to wake the LLM on state changes. Without
  cmux, supports team agent polling via CronCreate. Triggers on "watch glue job",
  "monitor glue run", "check glue status", "glue job finished", "background glue
  monitor", or any request to track an AWS Glue job run.
---

# Query AWS Glue

## Prerequisites

- Python 3 with `boto3` installed (activate `.venv` if present)
- AWS account with Glue access
- AWS credentials configured (profile recommended)
- **cmux** recommended for `watch-job` monitoring

## Overview

AWS Glue jobs run for minutes to hours. The LLM Bash tool has a 10-minute timeout,
making synchronous polling impractical for long jobs.

This skill solves it two ways:

| Environment | Approach |
|-------------|----------|
| **cmux** (recommended) | `watch-job` runs in a visible terminal split. On every state change, it sends a keystroke message to the Claude Code terminal, waking the LLM to act. Poll output is visible in the split — no tokens consumed watching it. |
| **No cmux** | `check-status` for one-shot queries. Spawn a team agent with `CronCreate` for background polling. |

This skill monitors existing jobs. Use other skills (e.g. `use-aws-glue`) for job submission.

---

## Quick Start with cmux

### 1. Identify your surface and workspace

```bash
cmux identify --json
# Use caller.surface_ref (NOT focused.surface_ref — focused changes as you switch tabs)
# caller.surface_ref is always the surface that spawned the current process (your CC session)
# Example: {"caller": {"surface_ref": "surface:80", "workspace_ref": "workspace:47"}, ...}
```

### 2. Create a visible split and launch the monitor

Open a downward split for the watcher output, then send the watch-job command to it:

```bash
# Step 1: create split — outputs the new surface ref directly
# Use "right" (side-by-side) to preserve vertical height; "down" for stacked layout
NEW_SURFACE=$(cmux new-split right | awk '{print $2}')

# Step 2: run watch-job in the split
cmux send --surface "$NEW_SURFACE" "source /path/to/.venv/bin/activate && \
python3 ${SKILL_DIR}/scripts/monitor_glue_job.py watch-job \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile \
    --surface-id surface:80 \
    --cc-cwd /path/to/project\n"
```

The monitor:
- Polls Glue every 5 minutes (configurable via `--poll-interval-seconds`)
- Prints a timestamped status line on every poll (visible in the split)
- Sends a keystroke to `--surface-id` on every state change
- Runs for up to 24 hours, then sends a final timeout message

**Example output in the watcher split:**
```
Glue monitor: 'my-etl-job' run jr_abc123...
Poll: every 300s | Surface: surface:80 | Workspace: workspace:47

[10:00:01Z] RUNNING (job exec: 14m 2s)
[10:05:01Z] RUNNING (job exec: 19m 2s)
...
[11:42:01Z] STATE CHANGE: RUNNING -> SUCCEEDED after 1h 42m
[11:42:01Z] Delivering notification...
[11:42:01Z] OK: Delivered to surface:80
```

**Example messages the LLM will receive:**
```
Glue job 'my-etl-job' (run jr_abc123) state changed: STARTING -> RUNNING. Elapsed: 2m 15s.
Glue job 'my-etl-job' (run jr_abc123) SUCCEEDED after 1h 42m. DPU-seconds: 7440.
Glue job 'my-etl-job' (run jr_abc123) FAILED after 23m. Error: OutOfMemoryError: Java heap space
```

### 3. Optional flags

```bash
    --no-cloudwatch-metrics      # Disable CW metrics (default: enabled; requires Glue 2.0+ Spark)
    --cmux-notify                # Desktop notification on each state change
    --cmux-status                # Sidebar status badge (key: glue-<run-id-prefix>)
    --poll-interval-seconds 60   # Override poll interval (min 60, max 3600)
    --keep-watcher-running       # Keep the watcher split open after exit (default: auto-close after 3s)
```

### 4. Stopping the monitor early

From any Claude Code session:
```bash
python3 ${SKILL_DIR}/scripts/monitor_glue_job.py stop-monitor \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc
```

Or list live monitors first:
```bash
python3 ${SKILL_DIR}/scripts/monitor_glue_job.py stop-monitor --list
```

The watcher split also accepts Ctrl+C directly.

---

## Quick Start without cmux

### One-shot status check

```bash
${SKILL_DIR}/scripts/monitor_glue_job.py check-status \
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
DPU-secs:  3024
Started:   2026-03-23T10:00:00+00:00
```

### Team Agent Monitoring (background polling without cmux)

For background polling, spawn a **team agent** (not a sub-agent) that uses `CronCreate`.
This keeps the primary session focused on other work.

**Step 1:** Create a team agent from the main session:
```
Agent(
    name="glue-watcher",
    team_name="my-team",
    prompt="Watch Glue job 'my-etl-job' run 'jr_abc123'. ..."
)
```

**Step 2:** Inside the team agent, use this CronCreate template:

```
Check Glue job 'my-etl-job' run 'jr_abc123'.
Last known state: RUNNING. Last check: 2026-03-23T10:05:00Z.

Run: ${SKILL_DIR}/scripts/monitor_glue_job.py check-status \
    --job-name my-etl-job --run-id jr_abc123 --profile my-aws-profile

If state changed from RUNNING:
  - SendMessage to main agent with new state, elapsed time, and error if any
  - If terminal state (SUCCEEDED/FAILED/STOPPED/ERROR/TIMEOUT): CronDelete this job, done
  - If non-terminal state: CronDelete, re-create at same interval with updated state

If no change: CronDelete, re-create with updated LAST_CHECK_ISO=now

ALWAYS embed current state and UTC time when re-creating the cron.
Stop after 24 hours total from watch start.
```

**Why team agents, not sub-agents?** Polling in the primary session burns context window on every cron tick. A dedicated team agent accumulates all Glue status communication, keeping the primary agent's session clean. See `watch-communication-channels` skill for full team agent polling patterns.

---

## Session Resilience

After a session restart, check what's being monitored and pick up where you left off.

### Discover tracked jobs

```bash
${SKILL_DIR}/scripts/monitor_glue_job.py check-status --list
```

Output example:
```
JOB NAME                       RUN ID               STATE        LAST POLL                 MONITOR
my-etl-job                     jr_abc1234567890abc  RUNNING      2026-03-23T10:05:00+00:00 PID 12345 (dead)
```

### Re-launch a monitor whose process died

If the monitor PID is dead but the job is still running, create a new split and re-launch:
```bash
NEW_SURFACE=$(cmux new-split right | awk '{print $2}')
cmux send --surface "$NEW_SURFACE" "python3 ${SKILL_DIR}/scripts/monitor_glue_job.py watch-job \
    --job-name my-etl-job \
    --run-id jr_abc1234567890abc \
    --profile my-aws-profile \
    --surface-id <your-surface-id>\n"
```

The state file at `~/.claude/plugin-data/aws-query-tools/query-aws-glue/` preserves all history.

### Team agent mode: session resume

After session restart with team agent polling:
1. Recall job name and run ID from conversation history
2. Run `check-status` to get current state (live API call)
3. Spawn a new watcher agent using the current state as the baseline

---

## cmux Fallback Chain

When a state change occurs, the monitor tries to notify you in this order:

1. **Send keystrokes to stored `--surface-id`** — the normal path
2. **Scan stored workspace** for surfaces with "Claude Code" in their title; optionally match `--cc-cwd` against the shell prompt to disambiguate multiple CC sessions
3. **Scan all workspaces** for a Claude Code surface
4. **If no surface found**: print the notification prominently to the watcher split's own terminal, fire a desktop `cmux notify` unconditionally, and write to the state file

The re-discovered surface is persisted to the state file so subsequent notifications go there directly.

**`--cc-cwd` tip:** Pass the absolute working directory of the Claude Code session (e.g. `/Volumes/workplace/myproject`). The monitor checks `cmux read-screen` on candidate surfaces for this path in the shell prompt. With multiple CC sessions open, this prevents delivery to the wrong one.

---

## AWS Profile Configuration

Use the `--profile` parameter to specify which AWS credentials profile to use.

**Prefer `--profile` over environment variables** (`AWS_PROFILE`) because:
- Explicit and visible in command history
- No risk of accidentally using wrong credentials
- Easier to audit

**Credential refresh:** The monitor recreates its boto3 session on every poll, so short-lived credentials (STS/SSO) are refreshed automatically as long as the underlying profile refreshes them (e.g. aws-vault, aws sso login).

If the monitor exits with state `CREDENTIAL_EXPIRED`:
1. Refresh credentials (`mwinit`, `aws sso login`, etc.)
2. Re-launch `watch-job` with the same `--run-id`

---

## Script Parameters

### `watch-job` — Monitor (runs in a cmux split)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--job-name` | yes | — | Glue job name |
| `--run-id` | yes | — | Glue job run ID (e.g. `jr_abc123`) |
| `--profile` | yes | — | AWS credentials profile |
| `--surface-id` | yes | — | cmux surface ID of the Claude Code session to notify |
| `--region` | no | profile default | AWS region |
| `--workspace-ref` | no | auto-detected | cmux workspace ref; auto-detected via `cmux identify` |
| `--cc-cwd` | no | — | Working directory of the CC session (for multi-session disambiguation) |
| `--poll-interval-seconds` | no | 300 | Poll frequency: min 60, max 3600 |
| `--no-cloudwatch-metrics` | no | off | Disable CloudWatch metrics (default: enabled; requires Glue 2.0+ Spark) |
| `--keep-watcher-running` | no | off | Keep the watcher split open after exit (default: auto-close after 3s) |
| `--cmux-notify` | no | off | Enable desktop notifications |
| `--cmux-status` | no | off | Enable cmux sidebar status badge |

State file: `~/.claude/plugin-data/aws-query-tools/query-aws-glue/<job>-<run-id>.json`

### `check-status` — Status Query

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--job-name` | yes (unless `--list`) | Glue job name |
| `--run-id` | yes (unless `--list`) | Glue job run ID |
| `--profile` | yes (unless `--list`) | AWS credentials profile |
| `--region` | no | AWS region |
| `--list` | no | List all tracked jobs from state files |

### `stop-monitor` — Stop a Running Monitor

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--job-name` | yes (unless `--list`) | Glue job name |
| `--run-id` | yes (unless `--list`) | Glue job run ID |
| `--list` | no | List live monitors (does not stop anything) |

---

## Resources

### scripts/monitor_glue_job.py

Main script with three subcommands:
- `watch-job`: Polling monitor. Runs in a visible cmux split. Sends keystrokes on state change. Fallback chain scans all workspaces for a Claude Code surface. 24-hour hard timeout.
- `check-status`: Synchronous status query. Shows state, elapsed time, error, DPU-seconds. Lists all tracked jobs.
- `stop-monitor`: Sends SIGTERM to a running monitor PID from the state file.

State files: `~/.claude/plugin-data/aws-query-tools/query-aws-glue/` (auto-cleaned after 30 days)

### references/best-practices.md

Load when:
- Diagnosing a failed job (error messages, common causes)
- Selecting worker types or sizing
- Working with job bookmarks
- Querying Glue CloudWatch logs
- Looking up useful AWS CLI commands for Glue
