#!/usr/bin/env bash
# session-start.sh - SessionStart hook for cron-restoration-guard
#
# Fires on session RESUME events. Instructs the agent to verify that any
# cron jobs expected from the previous session are still registered, and
# to re-register any that are missing.
#
# Always exits 0 — never blocks session start.

set -euo pipefail
# Guarantee exit 0 — never block session start, even on unexpected errors.
trap 'exit 0' ERR

# Escape a string for embedding in a JSON value.
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

agent_instructions="<cron-restoration-guard>
Session resumed. Cron jobs registered in the previous session are NOT automatically restored — they must be re-registered.

## Required: Verify and restore cron jobs

1. Call CronList to inventory all currently registered cron jobs.
2. Compare the list against any cron jobs you were responsible for registering in this session context (e.g. session expiry warnings from session-guard, or any other recurring tasks you set up).
3. If expected cron jobs are missing, re-register them now by following the original instructions from the relevant plugin or context (e.g. re-read the session-guard SessionStart output to determine the correct schedule and register accordingly).

## Cleanup note

If you find stale cron job IDs from a prior session (jobs that already fired or are no longer relevant), delete them with CronDelete.

## How to interpret CronList output

- If CronList returns jobs you recognize as yours from this session context, they are already registered — no action needed.
- If CronList returns an empty list or does not contain expected jobs, re-register the missing ones.
- Do not re-register a job that already exists — check the list first.
</cron-restoration-guard>"

escaped_context=$(escape_for_json "$agent_instructions")

# Print JSON using printf to safely interpolate the escaped context
# without relying on heredoc variable expansion (which could execute
# $() or backticks embedded in the string in future edits).
printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "${escaped_context}"

exit 0
