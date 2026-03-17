---
name: use-cmux
description: cmux Terminal Multiplexer — Agent Integration. Use when orchestrating terminal sessions, running parallel commands, monitoring output, reporting progress, opening browser panels for web automation or markdown preview, creating split panes, or taking screenshots inside cmux.
---

# cmux Terminal Multiplexer — Agent Integration

Use when orchestrating terminal sessions, running parallel commands, monitoring output, or reporting progress inside cmux. Works for Claude Code, Cursor, and Codex.

## Detection

Check for the `CMUX_WORKSPACE_ID` environment variable. If set, you are inside cmux and can use the `cmux` CLI. If unset, do NOT attempt any cmux commands.

The CLI binary is at `/Applications/cmux.app/Contents/Resources/bin/cmux` (also available as `cmux` on PATH inside cmux terminals).

Environment variables automatically set in cmux terminals:
- `CMUX_WORKSPACE_ID` — current workspace ref
- `CMUX_SURFACE_ID` — current surface ref
- `CMUX_SOCKET_PATH` — Unix socket path (usually `/tmp/cmux.sock`)

## Hierarchy

Window > Workspace (sidebar tab) > Pane (split region) > Surface (terminal tab in pane).

Use short refs: `workspace:1`, `pane:1`, `surface:2`.

## Core Commands

### Orientation

```bash
cmux identify --json              # get caller context (workspace/surface/pane refs)
cmux list-workspaces              # list all workspaces
cmux list-panes                   # list panes in current workspace
cmux list-pane-surfaces --pane <ref>  # list surfaces (tabs) in a pane
```

### Create Terminals

```bash
cmux new-workspace --command "cd /path && cmd"  # new workspace tab (does NOT switch to it)
cmux new-split <left|right|up|down>             # split current pane
cmux new-surface                                # new tab in current pane
cmux new-pane --direction <dir>                 # new pane
```

### Send Input / Read Output

```bash
cmux send --surface <ref> "text\n"          # send text to a surface (include \n for enter)
cmux send-key --surface <ref> <key>         # send key (enter, ctrl-c, etc.)
cmux read-screen --surface <ref> --lines <n>  # read terminal output (last n lines)
```

### Progress Reporting (shows in cmux sidebar)

```bash
cmux set-status <key> <value> --icon <name> --color <#hex>
cmux set-progress <0.0-1.0> --label "text"
cmux log --level <info|success|warning|error> --source "agent" -- "message"
cmux notify --title "Title" --body "Body"   # desktop notification
cmux clear-status <key>
cmux clear-progress
cmux clear-log
```

### Workspace Management

```bash
cmux rename-workspace "name"
cmux rename-tab --surface <ref> "name"
cmux close-surface --surface <ref>
cmux close-workspace --workspace <ref>
```

## Browser Panel Commands

cmux has a built-in browser engine. You can open web pages in splits/panes and interact with them programmatically — navigate, click, type, read DOM, take screenshots, etc.

For a full browser commands reference, load `${SKILL_DIR}/references/browser-commands.md`.

Key patterns:
- **Two-step open (reliable):** `open-split` then `navigate` with a small delay — `--url` on creation is unreliable
- **DOM:** `snapshot`, `get text/html/value/attr/count/box/styles`, `is visible/enabled/checked`
- **Interaction:** `click`, `dblclick`, `hover`, `fill`, `type`, `check`, `select`, `press`
- **Find:** `find role/text/label/placeholder/testid/first/nth`
- **Wait:** `wait <selector>`, `wait --text/--url/--load-state/--function`
- **Misc:** `eval`, `screenshot`, `console list`, `errors list`, `tab list/new`, `cookies`, `storage`, `viewport`, `network`

## Workflow Patterns

### Fan out into splits (parallel tasks in one workspace)

```bash
# Create splits for build and test
cmux new-split right
cmux send --surface surface:2 "npm run dev\n"

cmux new-split down
cmux send --surface surface:3 "npm test -- --watch\n"

# Report progress
cmux set-status build "Running" --icon hammer --color "#1565C0"

# ... do work ...

# Check results
cmux read-screen --surface surface:3 --lines 20
cmux set-status build "Done" --icon checkmark --color "#196F3D"
```

### Fan out into workspace tabs (isolated environments)

```bash
cmux new-workspace --command "cd ~/project/backend && npm run build"
cmux new-workspace --command "cd ~/project/frontend && npm run build"
```

### Run tests, read failures, fix, re-run

```bash
cmux new-split right
cmux send --surface surface:2 "npm test 2>&1\n"
# wait, then read output
cmux read-screen --surface surface:2 --lines 50
# fix code based on output, then re-run
cmux send --surface surface:2 "npm test 2>&1\n"
```

### Report progress throughout a task

```bash
cmux set-progress 0.0 --label "Starting build"
# ... step 1 ...
cmux set-progress 0.33 --label "Compiling"
# ... step 2 ...
cmux set-progress 0.66 --label "Running tests"
# ... step 3 ...
cmux set-progress 1.0 --label "Complete"
cmux clear-progress
cmux notify --title "Build Complete" --body "All tests passed"
```

### Open a website, inspect it, interact with it

```bash
# Open a browser panel in a split (two-step for reliability)
cmux browser surface:1 open-split --direction right
sleep 1 && cmux browser surface:2 navigate "https://example.com"
# Wait for it to load
cmux browser surface:2 wait --load-state networkidle
# Get a DOM snapshot to understand the page
cmux browser surface:2 snapshot --compact
# Find and click a button
cmux browser surface:2 click "button.submit"
# Read resulting text
cmux browser surface:2 get text ".result-message"
# Take a screenshot
cmux browser surface:2 screenshot --out /tmp/result.png
```

### Check a web app's state (e.g., verify a deploy)

```bash
cmux browser surface:1 open-split --direction right
sleep 1 && cmux browser surface:2 navigate "https://myapp.com"
cmux browser surface:2 wait --load-state networkidle
cmux browser surface:2 get title
cmux browser surface:2 eval "document.querySelector('.version')?.textContent"
cmux browser surface:2 console list    # check for errors
cmux browser surface:2 errors list
```

## Markdown Preview in Browser Panel

When the user asks to open/view/preview a `.md` file in cmux (e.g., "open foo.md on the right", "show the plan"), render it as styled HTML in a cmux browser panel. Do NOT use `less`, `cat`, or `file://` URLs.

### File naming

Derive the HTML filename from the source markdown filename:
- `/path/to/my-plan.md` → `/tmp/my-plan.html`
- Use `os.path.basename` and replace `.md` with `.html`

**Track which HTML file you created.** When the user asks to update/refresh the preview, or when you modify the source markdown, regenerate the **same HTML file** and `cmux browser <surface> reload`. Do not create a second HTML file with a different name.

### Steps

1. **Convert markdown to HTML** using `${SKILL_DIR}/scripts/md-to-html.py`. Write output to `/tmp/<basename>.html`:
   ```bash
   python3 ${SKILL_DIR}/scripts/md-to-html.py /path/to/file.md --dark
   ```
   The script prints the output filename so you can use it in the browser URL.
2. **Start a local HTTP server** (if not already running — check with `lsof -ti:18923`):
   ```bash
   python3 -m http.server 18923 --directory /tmp --bind 127.0.0.1 &>/dev/null &
   ```
3. **Open in cmux browser panel** using the direction the user requested:
   ```bash
   cmux browser <your-surface> open-split "http://127.0.0.1:18923/<basename>.html"
   ```

For the markdown-to-HTML conversion script, use `${SKILL_DIR}/scripts/md-to-html.py`.

### Defaults

- **Default to dark mode** (`--dark`). Only use light mode if the user explicitly asks for light mode.
- Use `open-split` with a direction matching the user's request (right, down, etc.). Default to `open-split` (which splits below).
- **When you modify the source markdown**, always regenerate the same HTML file and `cmux browser <surface> reload`. Never create a second HTML file.
- Reuse the same HTTP server port (18923) across previews. Before starting a new server, check: `lsof -ti:18923`. If already running, skip.

## Safety Rules

- **Never `cmux send` to surfaces you don't own** — the user may be typing in them
- **Always target surfaces you created** with `--surface <ref>`
- **Don't use focus/select commands** (`select-workspace`, `focus-pane`, etc.) unless the user explicitly asked — don't steal focus
- **Clean up when done** — close surfaces and workspaces you created
- **Use `identify --json` first** to understand your current context before creating new terminals
