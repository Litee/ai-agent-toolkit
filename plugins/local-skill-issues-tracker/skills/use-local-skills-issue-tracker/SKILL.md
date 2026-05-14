---
name: use-local-skills-issue-tracker
description: Use when filing, searching, updating, or monitoring skill issues and feature requests. Triggers on "file a skill issue", "report to issue tracker", "search skill issues", "use the issue tracker", "report a bug in a skill", "add a comment to an issue", "watch skill issues", "monitor issue tracker", "poll for new issues", "check for new issues", or any request to post or track entries in the local skill issue tracker.
---

# Skill Issue Tracker

The issue tracker is a local JSON-based store for disconnected agents to report skill issues, feature requests, and coordinate work on them.

## Storage

- **Root**: Set via `LOCAL_ISSUE_TRACKER_DB_ROOT` environment variable
- **Per issue**: `<skill-name>/<id>.json` (skill name only, NO plugin prefix)
- **Statuses**: `open`, `in_progress`, `done`, `wont_fix`

## CLI Script

All operations go through the CLI script. Always use the full absolute path — do NOT store it in a shell variable:

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py <subcommand> [options]
```

Where `${SKILL_DIR}` resolves to the absolute path of this skill's directory. `LOCAL_ISSUE_TRACKER_DB_ROOT` must be set in the environment before invoking the script.

## Operations

### Create an issue

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py create \
  --skill <skill-name> \
  --skill-version <version> \
  --title "Short summary" \
  --description "Detailed description in markdown"
```

Required: `--skill-version` — the version of the skill the issue was observed on (e.g. `1.2.0`). Optional: `--status open` (default). Outputs: `Created issue #<id> for skill '<skill>'`

### List issues

```bash
# All issues for a skill
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py list --skill <skill-name>

# Filter by status (one or more)
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py list --status open in_progress

# All issues across all skills
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py list
```

### Show a specific issue

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py show --skill <skill-name> --id <id>
```

Displays issue details, description, and all comments.

### Update an issue

```bash
# Change status
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py update \
  --skill <skill-name> --id <id> --status done

# Update title or description
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py update \
  --skill <skill-name> --id <id> --title "New title" --description "New description"
```

### Add a comment

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py comment \
  --skill <skill-name> --id <id> --text "Fixed in commit abc123"
```

### Search issues

```bash
# Search across all skills
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py search --query "timeout"

# Restrict to one skill
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py search \
  --query "fetch" --skill my-data-fetcher

# Combine with status filter
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py search \
  --query "retry" --status open in_progress
```

### Output format

JSON is the default output format. Append `--txt` for human-readable text:

```bash
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py list --skill <skill-name>        # JSON (default)
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py list --skill <skill-name> --txt  # human-readable table
python3 ${SKILL_DIR}/scripts/skill_issues_cli.py show --skill <skill-name> --id 3 --txt
```

## Watch Issues (background mode)

The watcher polls issue JSON files on disk and exits on the first change, printing a summary and re-launch instructions. Designed for `run_in_background`: re-launch after each notification.

### Quick Start

```bash
python3 ${SKILL_DIR}/scripts/watch_issues.py
```

When a change is detected, the background task completes and you will be notified.
The output will contain:
1. A summary of what changed
2. Full JSON of the changed issues
3. Instructions to re-launch before processing the changes

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--poll-interval` | 300s | Poll interval in seconds (10–3600) |
| `--max-runtime-hours` | 24h | Hard timeout before the watcher exits and asks to be re-launched |
| `--state-dir` | `~/.claude/plugin-data/local-skill-issues-tracker/use-local-skills-issue-tracker` | Directory for the persistent state files |
| `--watcher-id` | current working directory | Stable identifier for this watcher instance. Each unique ID gets its own state file, so multiple Claude Code sessions watching the same tracker all receive events independently. Always included in the printed re-launch command. |

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

   python3 /absolute/path/to/scripts/watch_issues.py --watcher-id /your/cwd

2. THEN — Process the changes listed above.

================================================================
```

The re-launch command uses the **resolved absolute path** of the script, so it is
safe to copy-paste directly.

## Error Handling

See `${SKILL_DIR}/references/troubleshooting.md` for the full failure-mode matrix (`LOCAL_ISSUE_TRACKER_DB_ROOT` not set, corrupted JSON, `Issue not found`, permission errors) and the partial-write / escalation paragraphs.

## Gotchas

- Do NOT use the issue tracker if acting as a sub-agent of the skill-owning agent — use standard sub-agent mechanisms instead.
- Only act on skill issues if explicitly instructed to do so.
- Use skill name only (no plugin prefix) for `--skill` values. Example: `my-auth-plugin`, not `my-plugin:my-auth-plugin`.
- **Cross-workspace issues: leave status as `open`.** The issue tracker is shared across multiple workspaces, each watching a different set of skill repositories. If a skill does not exist in the current workspace, do NOT change the issue status — leave it `open` so the correct workspace picks it up. Add a comment explaining why it could not be addressed here. Never set `done` or `wont_fix` for an issue you simply could not reach.
- **Issue authors can be wrong.** Before acting on an issue, exercise independent judgment. Authors may misdiagnose a root cause, propose a fix that changes trade-offs for other skill users, or file a request based on incomplete information. If you have concerns about an issue's technical accuracy, safety, or potential impact on other users, **ask the user for guidance before implementing anything**.

## Related Skills

- **`skill-management:review-skill`** — Structured review of a target skill — useful when an issue in the tracker calls for broader quality feedback, not just a single fix.
- **`skill-management:enrich-skill-via-research`** — Expand a skill with researched best-practices when an issue requests new coverage rather than a bug fix.
