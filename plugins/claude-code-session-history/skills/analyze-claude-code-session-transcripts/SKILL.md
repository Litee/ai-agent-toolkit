---
name: analyze-claude-code-session-transcripts
description: "Use when asked to 'analyze session logs', 'read session transcripts', 'find recurring patterns in sessions', 'identify skill gaps from usage', 'what have I been doing in Claude Code', or 'analyze my Claude Code history'."
---

# analyze-claude-code-session-transcripts

> Found major gaps or factual errors in this skill? Report it via the `local-skill-issues-tracker:use-local-skills-issue-tracker` skill (if available).

Reads and analyzes Claude Code session JSONL transcripts to identify patterns, skill gaps, agent failure modes, and improvement opportunities.

## Prerequisites

- Python 3 with `json`, `glob`, and `os` stdlib modules
- Read access to `~/.claude/projects/` (created automatically when Claude Code is first run)
- If `~/.claude/projects/` does not exist, Claude Code has not yet been used — there are no transcripts to analyze

## Storage Location

Claude Code stores session transcripts at:

```
~/.claude/projects/<encoded-project-path>/<session-uuid>.jsonl
```

The project path encodes `/` as `-` (e.g. `/home/alice/myproject` → `-home-alice-myproject`).

Each session produces:
- `<uuid>.jsonl` — main conversation transcript (top-level)
- `<uuid>/subagents/agent-<id>.jsonl` — sub-agent transcripts (ignore for user message analysis)

## Find Sessions by Working Directory

### Quick lookup (encoded-path glob)

Claude Code encodes the working directory into the project-directory name by replacing every `/` with `-`. Use this to narrow candidates:

```bash
DIR=/path/to/your/project
ENCODED=$(printf '%s' "$DIR" | tr '/' '-')
ls ~/.claude/projects/"$ENCODED"/*.jsonl 2>/dev/null
```

### Encoding caveat

The encoding is lossy — treat the result above as a **candidate set, not a confirmed match**:

- `/` and a literal `-` in the path both encode to `-`, so `/foo/bar-baz` and `/foo-bar/baz` map to the same encoded name.
- `/.` encodes to `--`, which also matches a path component beginning with `-` (e.g. `/.claude` and `/-claude` are indistinguishable from the directory name alone).

For any path containing `/.` or `-`, verify with the `cwd` field (see below).

### Authoritative lookup (cwd field)

Most non-metadata entries (`progress`, `assistant`, `user`, `system`) carry a `cwd` field with the real absolute working directory. Use it to confirm or reject candidates:

```python
import json, glob, os

def sessions_for_cwd(target_cwd):
    """Return JSONL paths whose session started in target_cwd."""
    encoded = target_cwd.replace('/', '-')
    candidates = glob.glob(os.path.expanduser(f'~/.claude/projects/{encoded}/*.jsonl'))
    matches = []
    for path in candidates:
        with open(path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if 'cwd' in entry:
                    if entry['cwd'] == target_cwd:
                        matches.append(path)
                    break  # first cwd-bearing entry identifies the session's home dir
    return matches
```

Only the first `cwd`-bearing entry is checked because a session is filed under the directory where it *started*; subsequent `cd` calls within the session don't change the filing directory.

If you need sessions that *ever touched* a directory (not just started there), scan all entries and omit the `break`.

To search across all projects when you are unsure of the exact path (e.g. `/foo/bar` vs `/foo-bar`), widen the glob to `~/.claude/projects/*/*.jsonl` and rely entirely on the `cwd` filter.

## JSONL Format

Each line is a JSON object. Entry types:

| Type | Description |
|---|---|
| `"type": "user"` | User message. Extract `message.content` (may be string or array of `{type: "text", text: "..."}` blocks) |
| `"type": "assistant"` | Assistant response |
| `"type": "attachment"` | Hook outputs, tool results (not user messages) |
| `"type": "permission-mode"` | Metadata — skip |
| `"type": "file-history-snapshot"` | Metadata — skip |
| `"type": "last-prompt"` | Metadata — skip |

## Extraction Recipe

The `*.jsonl` glob matches only top-level files, so sub-agent transcripts (stored under `<uuid>/subagents/`) are automatically excluded — no basename filtering needed.

```python
import json, glob, os

def extract_user_messages(project_dir, max_chars=500):
    results = []
    for path in glob.glob(os.path.join(project_dir, '*.jsonl')):
        with open(path) as f:
            session_msgs = []
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get('type') != 'user':
                    continue
                msg = entry.get('message', {})
                content = msg.get('content', '') if isinstance(msg, dict) else msg
                if isinstance(content, list):
                    content = ' '.join(b.get('text', '') for b in content
                                       if isinstance(b, dict) and b.get('type') == 'text')
                content = content.strip()
                # Skip empty approvals and interrupt markers
                if len(content) > 10 and not content.startswith('[Request interrupted'):
                    session_msgs.append(content[:max_chars])
            if session_msgs:
                results.append({'session': os.path.basename(path), 'messages': session_msgs})
    return results
```

**If no sessions survive filtering** (all content ≤10 chars or all interrupt markers), the project directory likely contains only background/automated sessions. Try a neighboring project directory or lower `max_chars`.

**For 10MB+ sessions** where the Read tool times out, extract with Bash:
```bash
python3 -c "
import json, sys
for line in open(sys.argv[1]):
    try:
        e = json.loads(line)
    except: continue
    if e.get('type') == 'user':
        c = e.get('message', {}).get('content', '')
        if isinstance(c, list): c = ' '.join(b.get('text','') for b in c if isinstance(b,dict))
        if len(c.strip()) > 10: print(c.strip()[:500])
" ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl
```

## Analysis Patterns

- **Skill gap detection**: recurring tasks the user does manually that have no skill (≥3 sessions = pattern)
- **Agent failure patterns**: messages like "Stop", "No, not that", "Wrong", "You missed" indicate agent correction
- **Context waste**: very long sessions (>5MB) on simple tasks = skill or instruction gap
- **Skill effectiveness**: does the user invoke a skill and then immediately correct the agent? = skill needs improvement

## Sub-Agent Dispatch for Large Volumes

When analyzing many sessions, group by project or date range and dispatch one sub-agent per group:

- Each agent extracts and summarizes patterns from its sessions
- Primary agent deduplicates: same pattern found by N agents = frequency N, not N separate findings
- Minimum frequency threshold: ≥2 sessions for "pattern", ≥5 sessions for "strong candidate for skill"

## Output Format

For each identified pattern:

```
Pattern: <descriptive name>
Frequency: <count> sessions
Evidence: <2-3 example user messages>
Suggested action: <new skill | improve existing skill X | add to CLAUDE.md | no action>
```

## Gotchas

- Sub-agent transcripts live under `<uuid>/subagents/` subdirectories — the top-level `*.jsonl` glob excludes them automatically
- Most `"type": "user"` entries are empty strings (tool approval clicks) — filter `len(content) > 10`
- `[Request interrupted by user for tool use]` messages are UI artifacts, not real requests — skip them
- Hook output messages appear as `"type": "attachment"` not `"type": "user"`
- Very large sessions (10MB+) may time out the Read tool — use the Bash one-liner in the Extraction Recipe section above

## See Also

- `skill-management:review-skill` — quality-review skills identified as candidates for improvement
- `skill-management:evaluate-skills-with-synthetic-tasks` — test skills using synthetic tasks to verify they work as expected
- `local-skill-issues-tracker:use-local-skills-issue-tracker` — file bugs and feature requests for skills identified as needing improvement
