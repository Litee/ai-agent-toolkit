# Troubleshooting

`cmux` commands are generally well-behaved, but several failure modes are worth a structured response:

| Scenario | Cause | Handling |
|----------|-------|----------|
| `cmux: command not found` outside cmux terminals | Caller is not inside a cmux-spawned shell (no `CMUX_WORKSPACE_ID`) | Detection section already covers this: check `CMUX_WORKSPACE_ID` first. If unset, do NOT run any `cmux` command. If set but the binary is missing, fall back to `/Applications/cmux.app/Contents/Resources/bin/cmux`. If that is also missing, escalate — cmux.app is not installed. |
| `Error: invalid_params: Surface is not a terminal` | Target surface was created via `new-surface` or `new-pane --type terminal`, or the ref is stale after a workspace restart | Do NOT retry the same ref. Refresh context: `cmux identify --json` and `cmux tree --workspace <ref> --json`. Use `new-split <direction>` to create a usable terminal instead. |
| `cmux send` exits 0 but input landed on the wrong surface | Invalid surface ref; cmux silently falls back to the focused surface | Always pre-validate: `cmux tree --workspace <ref> --json | jq -r '.windows[].workspaces[].panes[].surfaces[].ref'` and confirm the target ref is present before sending. |
| `cmux read-screen` returns empty or stale output | Surface has not rendered yet after a fresh `send`; or the surface is paused | Sleep 0.5-1s after `send` before `read-screen`. For longer-running commands, poll with an explicit timeout rather than tight-looping. |
| `new-split` lands in the wrong workspace | Called without `--workspace` (splits into the focused workspace, not the caller's) | Always pass `--workspace <caller.workspace_ref>`. See Known Gotchas below for the focus-retention quirk — you must `select-workspace` before every `new-split`, not just the first. |
| `cmux browser navigate` times out on load | Target URL is slow, blocked, or returns an error status | Use `browser wait --load-state complete` with a reasonable `--timeout-ms`. For local HTTP servers, confirm the server is listening first with `lsof -ti:<port>` before `navigate`. |
| Non-zero exit from any `cmux` command | Workspace destroyed mid-operation; stale surface ref; cmux.app crashed | Do NOT blindly retry. Re-run `cmux identify --json` — if it also fails, cmux itself is down: escalate to the user. Otherwise, refresh the surface/workspace refs and retry once. |

**Don't-own-it rule.** If any `send` / `send-key` / `read-screen` call fails on a surface you did NOT create, stop and escalate — the user may be actively typing. Silently retrying on someone else's surface is never correct recovery.

**Clean-up on failure.** If you created a surface/workspace and a downstream step failed, close your created resources before returning control to the user (`cmux close-surface <ref>`, `cmux close-workspace <ref>`). Leaving orphan panes around is a footgun for the next session.
