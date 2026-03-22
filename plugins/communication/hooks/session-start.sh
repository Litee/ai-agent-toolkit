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
Session resumed. If you were watching any communication channels before this session ended, load the watch-communication-channels skill and follow its Session Resume Recovery section.
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
