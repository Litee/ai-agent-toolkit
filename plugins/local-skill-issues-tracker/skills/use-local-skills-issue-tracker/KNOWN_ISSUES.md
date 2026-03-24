# Known Issues

Issues identified during code review that are not yet fixed. Contributions welcome.

---

## CRITICAL

### KI-1: `_next_id()` race condition in concurrent `create` calls

**File:** `scripts/skill_issues_cli.py`, `_next_id()` (line ~105)

Two agents calling `create` for the same skill simultaneously will both scan the directory,
compute the same next ID, and one will silently overwrite the other's issue file.

**Impact:** Data loss in multi-agent environments.

**Workaround:** Avoid parallel `create` calls for the same skill. Sequential invocations
are safe.

**Fix direction:** Replace directory scan with an atomic counter file using `O_CREAT |
O_EXCL`, or use a lock file per skill directory.

---

### KI-2: Non-atomic write in `_save_issue()` (CLI)

**File:** `scripts/skill_issues_cli.py`, `_save_issue()` (line ~124)

`_save_issue()` writes directly to the target path with `open(path, "w")`. A crash or
interrupt mid-write produces a truncated/corrupt JSON file. Contrast with
`watch_issues.py`'s `_save_state()` which correctly uses write-to-tmp + `os.replace()`.

**Impact:** Corrupt issue file if the process is killed during a write.

**Fix direction:** Use the same `tmp + os.replace()` pattern as `_save_state()`.

---

### KI-3: Watcher reads mid-write CLI output

**File:** `scripts/watch_issues.py`, `_scan_issue_files()`

If `watch_issues.py` scans while `skill_issues_cli.py` is writing a file, it reads partial
JSON, skips the file with a warning, then on the next poll the file appears "new" — causing
a duplicate "new issue" notification.

**Impact:** Duplicate change notifications in rare timing windows.

**Workaround:** The duplicate is cosmetic — no data is lost. The issue is reported twice.

**Fix direction:** Atomic writes in the CLI (KI-2) eliminate the read-of-partial-write
window.

---

## HIGH

### KI-4: Title rename produces phantom "new issue" + "file removed" events

**File:** `scripts/watch_issues.py`, `_diff_snapshots()`

`skill_issues_cli.py update --title` renames the issue file (slug changes). The watcher
diffs by file path, so it sees: old path "removed" + new path "added" — and reports a
phantom new issue plus a phantom file removal instead of a "title changed" event.

**Impact:** Confusing watcher output when issue titles are updated.

**Fix direction:** Track issues by `issue_id` field rather than file path in the snapshot.

---

## MEDIUM

### KI-5: SHA-256 truncated to 8 hex chars for state file discrimination

**File:** `scripts/watch_issues.py`, `_state_path()` (line ~143)

`--watcher-id` is hashed and truncated to 8 hex chars (32 bits). Birthday collision
probability reaches ~50% at ~65,000 distinct watcher IDs on one machine. A collision
causes two sessions to share a state file and one will miss events.

**Impact:** Negligible for typical use (single user, few sessions).

**Fix direction:** Increase to 16 hex chars (64 bits), or use the full hash.

---

### KI-6: `--skill` parameter allows path traversal

**File:** `scripts/skill_issues_cli.py`, `_skill_dir()` (line ~64)

`--skill` is joined directly into a path with no validation. A value like `../../etc`
resolves outside the DB root.

**Impact:** An agent could read/write arbitrary JSON files on disk.

**Fix direction:** Validate that `skill` contains no path separators before joining.

---

### KI-7: Orphaned `.tmp` state files from SIGKILL

**File:** `scripts/watch_issues.py`, `_save_state()`

If the watcher is killed with SIGKILL during a `_save_state()` call, the PID-suffixed
`.tmp` file is never cleaned up and accumulates in the state directory.

**Impact:** Gradual accumulation of orphan files; harmless otherwise.

**Fix direction:** Clean up stale `.tmp` files (older than N hours) on startup.

---

### KI-8: Same `--watcher-id` launched twice both report the same change

**File:** `scripts/watch_issues.py`, poll loop

If a user accidentally launches two watcher instances with the same `--watcher-id`, both
read the same state file and both detect and report the same event.

**Impact:** Duplicate notifications; no data loss.

**Workaround:** Each session should use a distinct `--watcher-id` (the default CWD is
usually sufficient).

---

## LOW

### KI-9: Issue ID overflows at 10,000

**File:** `scripts/skill_issues_cli.py`, `ID_WIDTH = 4` (line ~37)

Issue IDs are zero-padded to 4 digits. `_ISSUE_FNAME_RE` matches exactly `\d{4}`, so
issue #10000 is silently invisible to all list/show/update operations and the watcher.

**Impact:** Silent failure after 9,999 issues per skill. Very unlikely in practice.

**Fix direction:** Increase `ID_WIDTH` and update the regex to `\d{4,}`.

---

### KI-10: TOCTOU on issue file re-read in change output

**File:** `scripts/watch_issues.py`, `_print_changes_and_instructions()` (line ~291)

After detecting a change, the output function re-reads the issue file from disk. The file
could have changed again or been deleted between the scan and the re-read. The fallback
(line ~294) handles this gracefully by printing snapshot data instead.

**Impact:** Change output may show slightly stale data in rare cases.

---

### KI-11: Global mutable state in CLI

**File:** `scripts/skill_issues_cli.py`, `_db_root_path` (line ~57)

A module-level global is set in `main()`. This makes the module non-reusable as a library
without monkeypatching.

**Impact:** None for CLI usage.

---

### KI-12: Empty string cannot clear title or description

**File:** `scripts/skill_issues_cli.py`, `cmd_update()` (line ~264)

`if args.title:` and `if args.description:` are falsy for empty strings. Passing
`--title ""` or `--description ""` silently does nothing.

**Impact:** Cannot clear a title or description via the CLI.
