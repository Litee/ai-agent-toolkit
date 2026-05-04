# Troubleshooting `sync_safe_commands.py`

Load this reference when `sync_safe_commands.py` fails, when `~/.claude/settings.json` is malformed, or when investigating backup/write issues.

This runbook covers the failure modes you may hit when running `sync_safe_commands.py`. Each item lists symptom, likely cause, and remediation.

### `~/.claude/settings.json` missing

**Symptom:** Script prints `📝 Creating new settings file at ~/.claude/settings.json` and proceeds. **Diagnosis:** Expected on a fresh Claude Code install, or after the directory was wiped — **not** an error.

**Remediation:** No action required — the sync script auto-creates `~/.claude/` (via `mkdir -p`) and writes a fresh `settings.json` containing just the `permissions.allow` entries. If you'd rather pre-seed it:

```bash
mkdir -p ~/.claude && echo '{"permissions": {"allow": []}}' > ~/.claude/settings.json
```

### Malformed JSON in `~/.claude/settings.json`

**Symptom:** Script exits with `❌ Error reading settings file: ...` and a JSON decode error (line/column). **Diagnosis:** Manual edit, a prior failed/interrupted write, or a third-party tool left the file corrupt.

**Remediation:** (i) pinpoint the syntax error with `jq . ~/.claude/settings.json`; (ii) restore from the backup produced by the last successful sync with `cp ~/.claude/settings.json.bak ~/.claude/settings.json`; (iii) if no backup exists, hand-fix the JSON or reset to an empty scaffold:

```bash
echo '{"permissions": {"allow": []}}' > ~/.claude/settings.json
```

### Backup write fails (disk full / permission denied)

**Symptom:** Script prints `⚠️  Warning: Could not create backup: ...` (e.g. `PermissionError`, `No space left on device`) but **continues** and still writes `settings.json`. **Diagnosis:** `~/.claude/` is owned by a different user (often after a `sudo` misstep), the filesystem is read-only, or the disk is full.

**Remediation:** Because the backup failure is non-fatal, `settings.json` itself may already have been modified — and if the subsequent write then also fails, the file can be left partially written (see the next item). Investigate before re-running; the script is idempotent:

```bash
ls -la ~/.claude/              # check ownership + perms
sudo chown -R $USER ~/.claude/ # fix ownership if needed
df -h ~                        # verify free space
```

### Settings.json partially written (script interrupted mid-write)

**Symptom:** `settings.json` is suspiciously short or truncated; Claude Code reports schema errors on startup; `jq . ~/.claude/settings.json` fails. **Diagnosis:** The script uses an **in-place write** (open-for-write then `json.dump`), not a write-temp-then-rename pattern, so a process kill (or crash, or power loss) mid-`json.dump` can truncate the live file. No stray `*.tmp` file is produced.

**Remediation:** Restore from the backup written at the start of the run, then re-run the sync. If no backup exists (first run ever, or the backup step itself failed earlier), fall back to the empty-scaffold reset shown under "Malformed JSON".

```bash
cp ~/.claude/settings.json.bak ~/.claude/settings.json
```

### Schema-version mismatch (future-proofing)

**Symptom:** Claude Code reports an unknown top-level key, rejects `permissions.allow`, or fails validation after a Claude Code upgrade. **Diagnosis:** Claude Code updated its `settings.json` schema and the sync script hasn't caught up. The script only reads/writes `permissions.allow` and preserves other top-level keys, so corruption risk is low — but a schema rename (e.g. `permissions` → something else) would make newly written entries inert.

**Remediation:** Manually merge the keys required by the current Claude Code version, or update this skill via its upstream repo. Always keep a backup (`cp ~/.claude/settings.json ~/.claude/settings.json.bak`) before editing by hand.

Before running the sync script, ensure `~/.claude/settings.json` is either absent or parses with `jq . ~/.claude/settings.json`; this prevents all of the above failure modes.
