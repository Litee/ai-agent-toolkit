# Troubleshooting

The CLI (`skill_issues_cli.py`) is a thin wrapper around JSON files under `--db-root`. Failures come from the filesystem, malformed JSON, or a wrong `--skill` / `--id` value — not from network or auth.

## Common failures

| Error | Cause | Handling |
|-------|-------|----------|
| `FileNotFoundError: <db-root>/issues` or `No such file or directory` | `--db-root` path does not exist, or the directory was moved | Verify the path with `ls <db-root>`. If the tracker was relocated, pass the new path. If it was never created, `mkdir -p <db-root>/issues <db-root>/skills` — the CLI then bootstraps on the next write. |
| `json.decoder.JSONDecodeError: Expecting value` | An issue file on disk is corrupted (truncated write from a crash mid-save, manual edit with a syntax error) | Identify the offender: `python3 -c "import json,glob; [json.load(open(f)) for f in glob.glob('<db-root>/issues/*/*.json')]"` — the first failing file is the culprit. Restore it from your shell's file history (e.g. Time Machine) or delete the file and re-create the issue with `create`. |
| `Issue not found: <id>` on `comment` / `update` / `show` | `--id` does not exist for that skill, or the skill name is wrong | List valid IDs: `list --skill <skill>`. IDs are 4-digit zero-padded strings (`0001`), not integers — pass as a string. If the skill directory itself is missing, the CLI prints `No issues for skill '<name>'`. |
| `Skill not found: <name>` | Skill directory does not exist under `<db-root>/skills/` | Run `list` with no filter to see all known skills. Use the skill name only — no plugin prefix. |
| `Permission denied` writing to `<db-root>` | Tracker on a read-only mount or wrong UID | `ls -ld <db-root>` to check ownership. The CLI does not fall back to a different location — fix the permission or pass `--db-root` pointing to a writable directory. |

## Partial-write recovery

The CLI uses plain `open(path, "w") + json.dump`, which is NOT atomic. A crash or power loss during a write can leave an issue file truncated — you will see the `JSONDecodeError` above on the next access. Recover the affected file from shell history / Time Machine, or delete it and re-create the issue.

## Escalation path

If the CLI exits with a non-zero code and the cause is unclear, re-run the exact command wrapped in `python3 -u ... 2>&1 | tee /tmp/issue-cli.log` for a full traceback. Never set status to `done` or `wont_fix` when the underlying cause is a CLI failure rather than an intentional decision — leave the issue in its current state and escalate to the user.
