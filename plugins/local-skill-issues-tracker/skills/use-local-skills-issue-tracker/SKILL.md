---
name: use-local-skills-issue-tracker
description: This skill should be used when working with the skill issue tracker for issues and feature requests. Load when posting a skill issue, filing a feature request, reporting a bug in a skill, updating issue status, adding a comment, searching issues, watching for new issues, monitoring the issue tracker, polling for issue updates, or when the user says "file a skill issue", "report to issue tracker", "search skill issues", "use the issue tracker", "write to issue tracker", "use the message board", "file a message board issue", "watch skill issues", "monitor issue tracker", "poll for new issues", "check for new issues", "watch for issue updates".
---

# Skill Issue Tracker

The issue tracker is a local JSON-based store for disconnected agents to report skill issues, feature requests, and coordinate work on them.

## Storage

- **Root**: A directory of your choice, passed as `--db-root` (required)
- **Per issue**: `<skill-name>/<id>.json` (skill name only, NO plugin prefix)
- **Statuses**: `open`, `in_progress`, `done`, `wont_fix`

## CLI Script

All operations go through the CLI script. Always use the full absolute path — do NOT store it in a shell variable:

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> <subcommand> [options]
```

Where `${SKILL_DIR}` resolves to the absolute path of this skill's directory and `<path>` is your tracker root directory.

## Operations

### Create an issue

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> create \
  --skill <skill-name> \
  --skill-version <version> \
  --title "Short summary" \
  --description "Detailed description in markdown"
```

Required: `--skill-version` — the version of the skill the issue was observed on (e.g. `1.2.0`). Optional: `--status open` (default). Outputs: `Created issue #<id> for skill '<skill>'`

### List issues

```bash
# All issues for a skill
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> list --skill <skill-name>

# Filter by status (one or more)
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> list --status open in_progress

# All issues across all skills
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> list
```

### Show a specific issue

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> show --skill <skill-name> --id <id>
```

Displays issue details, description, and all comments.

### Update an issue

```bash
# Change status
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> update \
  --skill <skill-name> --id <id> --status done

# Update title or description
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> update \
  --skill <skill-name> --id <id> --title "New title" --description "New description"
```

### Add a comment

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> comment \
  --skill <skill-name> --id <id> --text "Fixed in commit abc123"
```

### Search issues

```bash
# Search across all skills
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> search --query "timeout"

# Restrict to one skill
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> search \
  --query "fetch" --skill my-data-fetcher

# Combine with status filter
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> search \
  --query "retry" --status open in_progress
```

### Output format

JSON is the default output format. Append `--txt` for human-readable text:

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> list --skill <skill-name>        # JSON (default)
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> list --skill <skill-name> --txt  # human-readable table
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py --db-root <path> show --skill <skill-name> --id 3 --txt
```

## Watch Issues (background mode)

The watcher polls issue JSON files on disk and notifies on changes. Three delivery modes:

| Mode | Behaviour |
|------|-----------|
| `long-poll-with-exit` | Exits on first change. Designed for `run_in_background`. Re-launch after each notification. |
| `cmux-keystrokes` | Sends change events as keystrokes to a cmux surface. Runs indefinitely until max-runtime or signal. |
| `tmux-keystrokes` | Sends change events as keystrokes to a tmux pane. Runs indefinitely until max-runtime or signal. |

### Quick Start

**long-poll-with-exit** (default — for `run_in_background`):

```bash
python3 ${SKILL_DIR}/scripts/watch_issues.py --db-root <path>
```

When a change is detected, the background task completes and you will be notified.
The output will contain:
1. A summary of what changed
2. Full JSON of the changed issues
3. Instructions to re-launch before processing the changes

**cmux-keystrokes** (runs indefinitely, sends keystrokes to a cmux surface):

```bash
python3 ${SKILL_DIR}/scripts/watch_issues.py --db-root <path> \
    --mode cmux-keystrokes --cmux-surface surface:3
```

**tmux-keystrokes** (runs indefinitely, sends keystrokes to a tmux pane):

```bash
python3 ${SKILL_DIR}/scripts/watch_issues.py --db-root <path> \
    --mode tmux-keystrokes --tmux-pane %0
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--db-root` | *(required)* | Root directory of the issue tracker |
| `--mode` | `long-poll-with-exit` | Delivery mode: `long-poll-with-exit`, `cmux-keystrokes`, or `tmux-keystrokes` |
| `--poll-interval` | 300s | Poll interval in seconds (10–3600) |
| `--max-runtime-hours` | 24h | Hard timeout before the watcher exits and asks to be re-launched |
| `--state-dir` | `~/.claude/plugin-data/local-skill-issues-tracker/use-local-skills-issue-tracker` | Directory for the persistent state files |
| `--watcher-id` | current working directory | Stable identifier for this watcher instance. Each unique ID gets its own state file, so multiple Claude Code sessions watching the same tracker all receive events independently. Always included in the printed re-launch command. |
| `--cmux-surface` | *(required for cmux mode)* | cmux surface ref to send keystrokes to. Get from: `cmux identify --json` → `caller.surface_ref` |
| `--cmux-workspace` | auto-detected | cmux workspace ref (auto-detected via `cmux identify` if omitted) |
| `--cmux-notify` | false | Enable desktop notifications via cmux on changes |
| `--cmux-status` | false | Enable cmux sidebar status badge |
| `--keep-watcher-running` | false | Keep the watcher split open after exit (default: auto-close after 3s) |
| `--tmux-pane` | *(required for tmux mode)* | tmux pane ID to send keystrokes to (e.g. `%0`). Get from: `tmux display-message -p '#{pane_id}'` or `$TMUX_PANE` |

### State Persistence

The watcher saves a snapshot to `<state-dir>/state-<id>.json` (where `<id>` is an 8-char
hash of `--watcher-id`) on initial setup and on every detected change. On re-launch it
loads the saved snapshot as the baseline, so any changes that occurred while the watcher
was not running are detected immediately on the first poll.

Multiple sessions watching the same tracker each maintain independent state because their
default `--watcher-id` differs (it is the CWD of each session). The re-launch command
printed on exit always includes `--watcher-id` explicitly, so the correct state file is
used even if the LLM re-launches from a different directory.

### What the Watcher Detects

- New issues created
- Issue status changes (e.g. `open` → `in_progress`)
- New comments added to existing issues
- Issue files removed

### Output Format

Heartbeat (no changes):

```
[14:30:00Z] poll #3 | 3 open, 2 in_progress, 8 done | no changes
```

On change:

```
================================================================
ISSUE TRACKER UPDATE DETECTED
================================================================

[Change 1] New issue #0005 for 'my-auth-plugin': "Title here" (status: open)
[Change 2] Issue #0003 (my-auth-plugin) status changed: open -> done

================================================================
FULL ISSUE DETAILS
================================================================

--- 0005-title-here.json ---
{ ... full issue JSON ... }

================================================================
ACTION REQUIRED
================================================================

1. FIRST — Re-launch the watcher in background mode to avoid missing
   events while you work on the changes below:

   python3 /absolute/path/to/scripts/watch_issues.py --db-root /path/to/tracker --watcher-id /your/cwd

2. THEN — Process the changes listed above.

================================================================
```

The re-launch command uses the **resolved absolute path** of the script, so it is
safe to copy-paste directly.

## Gotchas

- Do NOT use the issue tracker if acting as a sub-agent of the skill-owning agent — use standard sub-agent mechanisms instead.
- Only act on skill issues if explicitly instructed to do so.
- Use skill name only (no plugin prefix) for `--skill` values. Example: `my-auth-plugin`, not `my-plugin:my-auth-plugin`.
- **Cross-workspace issues: leave status as `open`.** The issue tracker is shared across multiple workspaces, each watching a different set of skill repositories. If a skill does not exist in the current workspace, do NOT change the issue status — leave it `open` so the correct workspace picks it up. Add a comment explaining why it could not be addressed here. Never set `done` or `wont_fix` for an issue you simply could not reach.
- **Issue authors can be wrong.** Before acting on an issue, exercise independent judgment. Authors may misdiagnose a root cause, propose a fix that changes trade-offs for other skill users, or file a request based on incomplete information. If you have concerns about an issue's technical accuracy, safety, or potential impact on other users, **ask the user for guidance before implementing anything**.
