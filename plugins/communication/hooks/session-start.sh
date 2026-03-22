#!/usr/bin/env bash
# session-start.sh - SessionStart hook for communication plugin
#
# Fires on session RESUME events. Instructs the agent to verify that any
# communication channel watchers active in the previous session are still
# running, and to re-spawn any that are missing.
#
# Always exits 0 — never blocks session start.

set -euo pipefail

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

agent_instructions="<communication-channel-watcher-guard>
Session resumed. Communication channel watchers (team agents with cron-based polling) are NOT automatically restored — they must be re-spawned.

## Required: Verify and restore channel watchers

1. Check your session context for any communication channel watchers you were responsible for (e.g. a Slack thread watcher, a ticket watcher, a code review watcher).
2. Call CronList to inventory currently registered cron jobs and identify any watcher crons that are still active.
3. For any watcher that was active but whose cron is now missing:
   - Re-spawn the watcher agent using the watch-communication-channels skill patterns.
   - Use the session-resume backoff table from the skill to set the correct initial polling interval based on time since last activity:
     - < 30 min since last check: use BASE interval
     - 30 min – 2h: use BASE * 10
     - 2h – 4h: use BASE * 30
     - > 4h: use BASE * 60 (or MAX, whichever is smaller)

## If no watchers were active

No action needed. Continue with the session normally.

## Cleanup note

If you find stale cron job IDs from watchers that have since resolved or timed out, delete them with CronDelete.
</communication-channel-watcher-guard>"

escaped_context=$(escape_for_json "$agent_instructions")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "${escaped_context}"
  }
}
EOF

exit 0
