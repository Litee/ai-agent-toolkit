#!/usr/bin/env bash
# Detects whether the current session is running inside cmux.
# If not in cmux, exits silently. If in cmux, prints session context.

if [ -z "$CMUX_WORKSPACE_ID" ]; then
  echo "cmux not detected: session is not running inside cmux. cmux skill will be unavailable."
  exit 0
fi

echo "cmux session detected:"
echo "  Workspace ID: $CMUX_WORKSPACE_ID"
echo "  Surface ID:   $CMUX_SURFACE_ID"
echo "  Socket Path:  $CMUX_SOCKET_PATH"

if command -v cmux &>/dev/null; then
  IDENTIFY=$(cmux identify --json 2>/dev/null)
  if [ $? -eq 0 ] && [ -n "$IDENTIFY" ]; then
    echo "  Identify:     $IDENTIFY"
  fi

  echo ""
  echo "- You MUST use \`cmux\` skill to publish status updates and progress, if you are running a job that may take longer than 10 minutes. If user starts a new task after that, you MUST reset status update and progress."
fi
