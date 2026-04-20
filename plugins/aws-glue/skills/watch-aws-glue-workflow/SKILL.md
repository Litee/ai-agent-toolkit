---
name: watch-aws-glue-workflow
description: >
  Monitor AWS Glue workflow execution for state changes and per-node (job/crawler) progress
  with background notifications. Use when watching a Glue workflow that orchestrates multiple
  jobs, checking workflow status, or setting up background workflow monitoring. Supports three
  modes: background long-poll-with-exit (re-launch in loop, no cmux/tmux needed),
  cmux-keystrokes (background task, sends keystrokes to Claude Code terminal), and
  tmux-keystrokes (no cmux dependency). Triggers on "watch glue workflow", "monitor glue
  workflow", "check workflow status", "glue workflow finished", or any request to track an
  AWS Glue workflow run.
---

# AWS Glue Workflow Watcher

## Prerequisites

- Python 3 with `boto3` installed (activate `.venv` if present)
- AWS account with Glue access
- AWS credentials configured (`--profile` recommended)
- **cmux** — optional, required only for `cmux-keystrokes` mode
- **tmux** — optional, required only for `tmux-keystrokes` mode

## Overview

AWS Glue Workflows orchestrate multiple jobs and crawlers into a DAG. Each workflow run can
last minutes to hours. The LLM Bash tool has a 10-minute timeout, making synchronous polling
impractical.

This skill solves it three ways:

| Environment | Approach |
|-------------|----------|
| **No cmux/tmux** (default) | `watch --mode long-poll-with-exit`. Runs in background, exits with JSON on any state change or node failure. Re-launch in a loop after processing output. |
| **cmux** (recommended) | `watch --mode cmux-keystrokes` runs as a background task. On every state change, it sends a keystroke to the Claude Code terminal, waking the LLM to act. Poll output goes to the background task log — no cmux split needed. |
| **tmux** | `watch --mode tmux-keystrokes` — same as cmux-keystrokes but uses `tmux send-keys`. No cmux dependency. Requires `--tmux-pane`. |

This skill monitors existing workflow runs. Use the AWS CLI or `use-aws-glue` to start a
workflow: `aws glue start-workflow-run --name <workflow-name>`.

### Difference from watch-aws-glue-job

| | watch-aws-glue-job | watch-aws-glue-workflow |
|---|---|---|
| Target | Single job run | Workflow run (many jobs/crawlers) |
| API | `get_job_run` | `get_workflow_run` (with graph) |
| Terminal states | SUCCEEDED / FAILED / STOPPED / ERROR / TIMEOUT | COMPLETED / STOPPED / ERROR |
| CloudWatch metrics | Yes (per-job CPU, heap, records) | No (no workflow-level equivalent) |
| Node tracking | N/A | Per-node state table in poll output |
| Early exit | Terminal job state | Terminal workflow state OR any node failure |

---

## Quick Start without cmux

### Background long-poll-with-exit

Run in background using `run_in_background: true` (never use `&` or `nohup`):

```bash
# Start the workflow and capture the run ID
RUN_ID=$(aws glue start-workflow-run --name my-workflow \
  --profile my-aws-profile --query 'RunId' --output text)

# Launch watcher
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py watch \
    --workflow-name my-workflow \
    --run-id "$RUN_ID" \
    --profile my-aws-profile
```

When state changes (or a node fails), the watcher prints JSON to stdout and exits 0:

```json
{
  "events": [
    {
      "workflow_name": "my-workflow",
      "run_id": "wr_abc1234567890abc",
      "event_type": "workflow_terminal",
      "previous_state": "RUNNING",
      "new_state": "COMPLETED",
      "summary": "[Glue Workflow Watcher ...] my-workflow (wr_abc12345) | RUNNING -> COMPLETED (10:45 UTC). Elapsed: 42m 15s. Actions: 8 ok / 0 fail / 8 total.",
      "elapsed_seconds": 2535,
      "stats": {"TotalActions": 8, "SucceededActions": 8, "FailedActions": 0, ...},
      "nodes": [{"name": "etl-job-1", "type": "JOB", "state": "SUCCEEDED"}, ...],
      "failed_nodes": []
    }
  ],
  "watcher_id": "a1b2c3d4",
  "instruction": "Re-launch the watcher FIRST, then process events.\npython3 ..."
}
```

**event_type values:**
- `workflow_terminal` — workflow reached COMPLETED / STOPPED / ERROR
- `state_changed` — intermediate workflow-level state transition (e.g. RUNNING → ...)
- `node_transition` — a job or crawler changed state (e.g. RUNNING → SUCCEEDED); multiple events may appear in one output if several nodes transitioned in the same poll
- `node_failure` — a job or crawler entered FAILED / ERROR / TIMEOUT

In `long-poll-with-exit` mode, the watcher exits as soon as any event is produced (workflow state change, any node transition, or node failure). Re-launch it immediately before processing to avoid missing the next event.

In `cmux-keystrokes` / `tmux-keystrokes` mode, each event is sent as a separate keystroke and the watcher continues running until the workflow reaches a terminal state.

**Important:** Always re-launch the watcher before processing events to avoid missing state
changes that arrive while you're processing the previous output.

---

## Quick Start with tmux

### 1. Find your tmux pane

```bash
tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index} #{pane_title}"
```

### 2. Launch the watcher

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py watch \
    --workflow-name my-workflow \
    --run-id wr_abc1234567890abc \
    --profile my-aws-profile \
    --mode tmux-keystrokes \
    --tmux-pane main:0.0
```

---

## Quick Start with cmux

### 1. Get your surface and workspace refs

```bash
CMUX_INFO=$(cmux identify --json)
SURFACE_REF=$(echo "$CMUX_INFO" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['caller']['surface_ref'])")
WORKSPACE_REF=$(echo "$CMUX_INFO" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['caller']['workspace_ref'])")
```

Always use `caller.surface_ref` — not `focused.surface_ref`, which drifts as you switch tabs.

### 2. Launch the watcher in background

Use `run_in_background: true` on the Bash tool call:

```bash
CMUX_SOCKET_PATH="$HOME/Library/Application Support/cmux/cmux.sock" \
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py watch \
    --workflow-name my-workflow \
    --run-id wr_abc1234567890abc \
    --profile my-aws-profile \
    --mode cmux-keystrokes \
    --cmux-surface "$SURFACE_REF" \
    --cmux-workspace "$WORKSPACE_REF"
```

**Example poll output (in background task log):**
```
[10:05 UTC] RUNNING | actions: 8 total / 3 running / 4 ok / 0 fail | nodes: RUNNING:3 | SUCCEEDED:4 | PENDING:1
```

**Example keystrokes received:**
```
[Glue Workflow Watcher v1.x.x] my-workflow (wr_abc12345) | RUNNING -> COMPLETED (10:45 UTC)
[Glue Workflow Watcher v1.x.x] my-workflow (wr_abc12345) | NODE FAILURE (10:20 UTC): etl-job-3. Workflow state: RUNNING. Elapsed: 15m.
```

### 3. Optional flags

```bash
    --cmux-notify                # Desktop notification on each state change
    --cmux-status                # Sidebar status badge (key: glue-wf-<watcher-id-prefix>)
    --poll-interval-seconds 60   # Override poll interval (min 60, max 3600)
    --max-runtime-hours 48       # Override 24h default
```

### 4. Stopping the watcher early

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py stop --list
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py stop --watcher-id a1b2c3d4
```

---

## Session Resilience

After a session restart, check what watchers are running:

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py status --list
```

Output example:
```
WATCHER ID   MODE                   WORKFLOW                      STATE        LAST POLL              PID
a1b2c3d4     long-poll-with-exit    my-workflow                   RUNNING      2026-04-20T10:05:00Z   12345 (dead)
  launch: python3 /path/watch_glue_workflow.py watch --workflow-name my-workflow --run-id wr_abc123 --watcher-id a1b2c3d4
```

If the watcher PID is dead but the workflow is still running, re-launch using the `launch`
command from the status output.

### One-shot status check (no active watcher needed)

```bash
python3 ${SKILL_DIR}/scripts/watch_glue_workflow.py status \
    --workflow-name my-workflow \
    --run-id wr_abc1234567890abc \
    --profile my-aws-profile
```

Output:
```
Workflow:   my-workflow
Run ID:     wr_abc1234567890abc
State:      RUNNING
Started:    2026-04-20T10:00:00+00:00
Actions:    8 total | 3 running | 4 ok | 0 fail

Nodes (8):
  etl-job-1   JOB      SUCCEEDED
  etl-job-2   JOB      SUCCEEDED
  etl-job-3   JOB      RUNNING
  crawl-step  CRAWLER  RUNNING
```

---

## Workflow Run IDs

To get a workflow run ID for an in-progress or recent run:

```bash
# Get the most recent run ID
aws glue get-workflow-runs --name my-workflow \
  --profile my-aws-profile \
  --query 'Runs[0].WorkflowRunId' --output text

# Start a workflow and capture the run ID immediately
RUN_ID=$(aws glue start-workflow-run --name my-workflow \
  --profile my-aws-profile --query 'RunId' --output text)
```

---

## AWS Profile Configuration

Use `--profile` to specify which AWS credentials profile to use.

**Credential refresh:** The watcher recreates its boto3 session on every poll, so short-lived
credentials (STS/SSO) are refreshed automatically.

**Credential errors:** The watcher never exits on credential errors. It backs off linearly
(`min(60 * consecutive_errors, 3600)` seconds) and keeps retrying. After 5 consecutive
failures it notifies via the bridge (cmux/tmux) or logs to stderr (long-poll). When
credentials recover, it sends a "Credentials recovered" message and resumes normally.

---

## Script Parameters

### `watch` — Start Watching

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--workflow-name` | yes | — | Glue workflow name |
| `--run-id` | yes | — | Glue workflow run ID (e.g. `wr_abc123`) |
| `--profile` | yes | — | AWS credentials profile |
| `--region` | no | profile default | AWS region |
| `--mode` | no | `long-poll-with-exit` | `long-poll-with-exit`, `cmux-keystrokes`, or `tmux-keystrokes` |
| `--poll-interval-seconds` | no | `300` | Poll frequency: min 60, max 3600 |
| `--watcher-id` | no | auto-generated | Reuse existing state from a previous run |
| `--max-runtime-hours` | no | `24` | Max runtime before auto-exit |
| `--cmux-surface` | cmux only | — | cmux surface ref of the CC session to notify |
| `--cmux-workspace` | no | auto-detected | cmux workspace ref |
| `--cmux-notify` | no | off | Enable desktop notifications |
| `--cmux-status` | no | off | Enable cmux sidebar status badge |
| `--tmux-pane` | tmux only | — | tmux pane target (e.g. `main:0.0`) |

State file: `~/.claude/plugin-data/aws-glue/watch-aws-glue-workflow/state-<watcher-id>.json`
PID file: `~/.claude/plugin-data/aws-glue/watch-aws-glue-workflow/watcher-<watcher-id>.pid`

### `status` — Show Watcher State or One-Shot API Check

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | no | Show full state for a specific watcher ID |
| `--list` | no | List all tracked watchers |
| `--workflow-name` | no | Glue workflow name (for live API check) |
| `--run-id` | no | Glue workflow run ID (for live API check) |
| `--profile` | no | AWS profile (required for live API check) |
| `--region` | no | AWS region |

### `stop` — Stop a Running Watcher

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--watcher-id` | yes (unless `--list`) | Watcher ID to stop |
| `--list` | no | List live watchers without stopping |

---

## Resources

### scripts/watch_glue_workflow.py

Main script with three subcommands:
- `watch`: Polling watcher. Supports `long-poll-with-exit` (background JSON output, exits on
  state change or node failure), `cmux-keystrokes`, and `tmux-keystrokes`. Tracks per-node
  job/crawler state on every poll. Resilient credential handling (linear backoff, no forced
  exit). SIGUSR1 causes clean shutdown in continuous modes.
- `status`: Read-only state inspection. Show one watcher, list all, or one-shot live API check.
- `stop`: Send SIGTERM to a live watcher PID.

State files: `~/.claude/plugin-data/aws-glue/watch-aws-glue-workflow/` (auto-cleaned after 30 days)
