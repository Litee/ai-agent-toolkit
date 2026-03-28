#!/usr/bin/env python3
"""Issue tracker watcher — background poll-and-exit model.

Polls the skill issue tracker JSON files on disk. Prints a heartbeat every
poll cycle. On the first change detected (or on timeout), prints the change
details and re-launch instructions, then exits.

Designed for Claude Code's run_in_background Bash mode — the LLM launches
this script in the background and re-launches it after each notification.

Usage:
    python3 watch_issues.py [options]

State is persisted to a JSON file so no events are missed between runs.
If the state file is fresh (< 24h), the previous snapshot is used as the
baseline and any changes since the last run are reported on the first poll.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_STATE_DIR = os.path.expanduser(
    "~/.claude/plugin-data/local-skill-issues-tracker/use-local-skills-issue-tracker"
)
STATE_MAX_AGE_HOURS = 24.0


def _version_from_path(path: str) -> str:
    """Derive semver from the plugin cache path, e.g. .../1.1.0/skills/..."""
    m = re.search(r"/(\d+\.\d+\.\d+)/skills/", path)
    return m.group(1) if m else "unknown"


_VERSION = _version_from_path(__file__)

_ISSUE_FNAME_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.json$")

POLL_INTERVAL_DEFAULT = 300
POLL_INTERVAL_MIN = 10
POLL_INTERVAL_MAX = 3600


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    """Short UTC timestamp for log lines."""
    return datetime.now(timezone.utc).strftime("%H:%M:%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _script_path() -> str:
    """Absolute path of this script, resolved through symlinks."""
    return str(Path(sys.argv[0]).resolve())


# ---------------------------------------------------------------------------
# Filesystem scan
# ---------------------------------------------------------------------------

def _scan_issue_files(db_root: str) -> dict:
    """Scan all issue JSON files under db_root.

    Returns {file_path: {"mtime_ns": int, "issue_id": str, "status": str,
                          "title": str, "description": str,
                          "comments": list, "skill": str}}
    """
    snapshot = {}
    db_path = Path(db_root)
    if not db_path.is_dir():
        return snapshot

    for skill_dir in sorted(db_path.iterdir()):
        if not skill_dir.is_dir():
            continue
        for f in sorted(skill_dir.iterdir()):
            if not _ISSUE_FNAME_RE.match(f.name):
                continue
            try:
                stat = f.stat()
                issue = json.loads(f.read_text(encoding="utf-8"))
                snapshot[str(f)] = {
                    "mtime_ns": stat.st_mtime_ns,
                    "issue_id": issue.get("id", ""),
                    "status": issue.get("status", ""),
                    "title": issue.get("title", ""),
                    "description": issue.get("description", ""),
                    "comments": issue.get("comments", []),
                    "skill": issue.get("skill", ""),
                }
            except (OSError, json.JSONDecodeError) as exc:
                print(f"[{_ts()}] WARN: Could not read {f.name}: {exc}", flush=True)
    return snapshot


def _format_status_summary(snapshot: dict) -> str:
    """Format issue counts as 'N open, M in_progress, K done'."""
    counts: dict = {}
    for info in snapshot.values():
        s = info.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    order = ["open", "in_progress", "done", "wont_fix"]
    parts = []
    for s in order:
        if s in counts:
            parts.append(f"{counts[s]} {s}")
    for s in sorted(counts):
        if s not in order:
            parts.append(f"{counts[s]} {s}")
    return ", ".join(parts) if parts else "0 issues"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state(state_path: str) -> Optional[dict]:
    """Load persisted snapshot from disk.

    Returns the snapshot dict if the state file exists and is younger than
    STATE_MAX_AGE_HOURS, otherwise None.
    """
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts_str = data.get("timestamp", "")
        if not ts_str:
            return None
        saved_at = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - saved_at).total_seconds() / 3600.0
        if age_hours > STATE_MAX_AGE_HOURS:
            return None
        return data.get("snapshot")
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _state_path(state_dir: str, watcher_id: str) -> str:
    """Return the state file path for this watcher instance.

    Uses the first 8 hex chars of SHA-256(watcher_id) as the filename
    discriminator so each distinct watcher_id (i.e. session CWD) has its own
    independent state file.
    """
    hex8 = hashlib.sha256(watcher_id.encode()).hexdigest()[:8]
    return os.path.join(state_dir, f"state-{hex8}.json")


def _save_state(state_path: str, snapshot: dict) -> None:
    """Atomically write snapshot + timestamp to state file.

    Uses a PID-suffixed tmp path to avoid collisions when two instances of
    the same watcher_id are briefly both alive (old not yet dead, new starting).
    """
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    tmp = f"{state_path}.{os.getpid()}.tmp"
    data = {"timestamp": _now_iso(), "snapshot": snapshot}
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, state_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Instance guard — PID file to prevent duplicate watchers
# ---------------------------------------------------------------------------

def _pid_file_path(state_dir: str, watcher_id: str) -> str:
    """Return the PID file path for this watcher instance."""
    hex8 = hashlib.sha256(watcher_id.encode()).hexdigest()[:8]
    return os.path.join(state_dir, f"watcher-{hex8}.pid")


def _check_instance_guard(state_dir: str, watcher_id: str) -> None:
    """Exit with an error if another process with watcher_id is already running.

    Reads the PID file. If the PID is alive, prints an error to stderr and
    exits with code 1. If the PID file is stale (process not found), execution
    continues normally — the caller writes a fresh PID file after this returns.

    os.kill(pid, 0) semantics:
      - Succeeds (no exception)  → process exists, treat as alive.
      - ProcessLookupError       → no such process, stale PID.
      - PermissionError          → process exists but not owned by us, treat as alive.
    """
    pid_path = _pid_file_path(state_dir, watcher_id)
    if not os.path.exists(pid_path):
        return
    try:
        with open(pid_path, "r") as f:
            pid = int(f.read().strip())
    except (ValueError, OSError):
        return  # Unreadable or malformed — treat as stale, overwrite later.
    try:
        os.kill(pid, 0)
        # Process is alive — abort.
        print(
            f"[Issue Watcher] ERROR: watcher '{watcher_id}' is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
    except ProcessLookupError:
        return  # Stale PID — process is gone, continue.
    except PermissionError:
        # Process exists but owned by another user — treat as alive.
        print(
            f"[Issue Watcher] ERROR: watcher '{watcher_id}' is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


def _write_pid_file(state_dir: str, watcher_id: str) -> None:
    """Write current PID to the PID file. Fatal on OSError."""
    pid_path = _pid_file_path(state_dir, watcher_id)
    os.makedirs(state_dir, exist_ok=True)
    try:
        with open(pid_path, "w") as f:
            f.write(str(os.getpid()))
    except OSError as e:
        print(
            f"[Issue Watcher] FATAL: failed to write PID file {pid_path}: {e}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)


def _remove_pid_file(state_dir: str, watcher_id: str) -> None:
    """Remove the PID file on clean exit."""
    try:
        pid_path = _pid_file_path(state_dir, watcher_id)
        if os.path.exists(pid_path):
            os.unlink(pid_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def _diff_snapshots(old: dict, new: dict) -> list:
    """Compare two snapshots and return a list of human-readable change strings."""
    notifications = []

    old_paths = set(old.keys())
    new_paths = set(new.keys())

    for path in new_paths - old_paths:
        info = new[path]
        notifications.append(
            f"New issue #{info['issue_id']} for '{info['skill']}': "
            f"\"{info['title']}\" (status: {info['status']})"
        )

    for path in old_paths - new_paths:
        fname = os.path.basename(path)
        notifications.append(f"Issue file removed: {fname}")

    for path in old_paths & new_paths:
        o = old[path]
        n = new[path]
        if n["mtime_ns"] == o["mtime_ns"]:
            continue
        if n["status"] != o["status"]:
            notifications.append(
                f"Issue #{n['issue_id']} ('{n['skill']}') "
                f"status changed: {o['status']} -> {n['status']}"
            )
        old_count = len(o["comments"])
        new_count = len(n["comments"])
        if new_count > old_count:
            for c in n["comments"][old_count:]:
                text = c.get("text", "")
                preview = text[:80] + ("..." if len(text) > 80 else "")
                notifications.append(
                    f"New comment on issue #{n['issue_id']} "
                    f"('{n['skill']}'): \"{preview}\""
                )
        if new_count < old_count:
            notifications.append(
                f"Issue #{n['issue_id']} ('{n['skill']}') — comment removed"
            )
        if n["description"] != o["description"]:
            notifications.append(
                f"Issue #{n['issue_id']} ('{n['skill']}') — description updated"
            )
        if n["title"] != o["title"]:
            notifications.append(
                f"Issue #{n['issue_id']} ('{n['skill']}') — "
                f"title changed to \"{n['title']}\""
            )

    return notifications


def _changed_paths(old: dict, new: dict) -> set:
    """Return file paths that have been added or modified (not removed)."""
    old_paths = set(old.keys())
    new_paths = set(new.keys())
    added = new_paths - old_paths
    modified = {
        p for p in old_paths & new_paths
        if new[p]["mtime_ns"] != old[p]["mtime_ns"]
    }
    return added | modified


# ---------------------------------------------------------------------------
# Output: change notification
# ---------------------------------------------------------------------------

def _build_relaunch_cmd(
    db_root: str,
    poll_interval: int,
    max_runtime_hours: float,
    state_dir: str,
    watcher_id: str,
) -> str:
    """Build a shell-safe re-launch command with all non-default args made explicit."""
    cmd = f"python3 {shlex.quote(_script_path())}"
    # --db-root is always required, so always include it
    cmd += f" --db-root {shlex.quote(db_root)}"
    if poll_interval != POLL_INTERVAL_DEFAULT:
        cmd += f" --poll-interval {poll_interval}"
    if max_runtime_hours != 24.0:
        cmd += f" --max-runtime-hours {max_runtime_hours}"
    if state_dir != DEFAULT_STATE_DIR:
        cmd += f" --state-dir {shlex.quote(state_dir)}"
    # Always include --watcher-id: re-launch may occur from a different CWD
    cmd += f" --watcher-id {shlex.quote(watcher_id)}"
    return cmd


def _print_changes_and_instructions(
    notifications: list,
    old_snapshot: dict,
    new_snapshot: dict,
    relaunch_cmd: str,
) -> None:
    SEP = "=" * 64
    print(SEP, flush=True)
    print("ISSUE TRACKER UPDATE DETECTED", flush=True)
    print(SEP, flush=True)
    print(flush=True)

    for i, note in enumerate(notifications, 1):
        print(f"[Change {i}] {note}", flush=True)

    # Full issue data for changed/new issues
    changed = _changed_paths(old_snapshot, new_snapshot)
    if changed:
        print(flush=True)
        print(SEP, flush=True)
        print("FULL ISSUE DETAILS", flush=True)
        print(SEP, flush=True)
        for path in sorted(changed):
            info = new_snapshot.get(path)
            if info:
                try:
                    raw = Path(path).read_text(encoding="utf-8")
                    issue_json = json.dumps(json.loads(raw), indent=2)
                except (OSError, json.JSONDecodeError):
                    issue_json = json.dumps(info, indent=2)
                print(flush=True)
                print(f"--- {os.path.basename(path)} ---", flush=True)
                print(issue_json, flush=True)

    print(flush=True)
    print(SEP, flush=True)
    print("ACTION REQUIRED", flush=True)
    print(SEP, flush=True)
    print(flush=True)
    print("1. FIRST — Re-launch the watcher in background mode to avoid missing", flush=True)
    print("   events while you work on the changes below:", flush=True)
    print(flush=True)
    print(f"   {relaunch_cmd}", flush=True)
    print(flush=True)
    print("2. THEN — Process the changes listed above.", flush=True)
    print(flush=True)
    print(SEP, flush=True)


def _print_timeout_instructions(max_runtime_hours: float, relaunch_cmd: str) -> None:
    SEP = "=" * 64
    print(flush=True)
    print(SEP, flush=True)
    print(f"WATCHER TIMEOUT ({max_runtime_hours}h max runtime reached)", flush=True)
    print(SEP, flush=True)
    print(flush=True)
    print("Re-launch the watcher if you still need monitoring:", flush=True)
    print(flush=True)
    print(f"   {relaunch_cmd}", flush=True)
    print(flush=True)
    print(SEP, flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="watch_issues.py",
        description=(
            "Poll the skill issue tracker and exit on the first change detected.\n"
            "Designed for Claude Code run_in_background mode: the LLM re-launches\n"
            "this script after each notification."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s --db-root /path/to/tracker\n"
            "  %(prog)s --db-root /path/to/tracker --poll-interval 60\n"
        ),
    )
    parser.add_argument(
        "--db-root",
        required=True,
        metavar="PATH",
        help="Root directory of the issue tracker",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=POLL_INTERVAL_DEFAULT,
        metavar="SECONDS",
        help=f"Poll interval in seconds (default: {POLL_INTERVAL_DEFAULT}, "
             f"range: {POLL_INTERVAL_MIN}–{POLL_INTERVAL_MAX})",
    )
    parser.add_argument(
        "--max-runtime-hours",
        type=float,
        default=24.0,
        metavar="HOURS",
        help="Hard timeout in hours before the watcher exits (default: 24)",
    )
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        metavar="PATH",
        help=f"Directory for the persistent state file (default: {DEFAULT_STATE_DIR})",
    )
    parser.add_argument(
        "--watcher-id",
        default=None,
        metavar="ID",
        help=(
            "Stable identifier for this watcher instance. Determines the state file name "
            "so concurrent watchers in different sessions don't share state. "
            "Defaults to the current working directory. Always included in the re-launch "
            "command printed on exit."
        ),
    )
    args = parser.parse_args()

    if not (POLL_INTERVAL_MIN <= args.poll_interval <= POLL_INTERVAL_MAX):
        print(
            f"Error: --poll-interval must be between {POLL_INTERVAL_MIN} "
            f"and {POLL_INTERVAL_MAX}.",
            file=sys.stderr,
        )
        sys.exit(1)

    db_root = os.path.expanduser(args.db_root)
    state_dir = os.path.expanduser(args.state_dir)
    watcher_id = args.watcher_id if args.watcher_id is not None else os.getcwd()
    spath = _state_path(state_dir, watcher_id)
    max_runtime_seconds = int(args.max_runtime_hours * 3600)

    relaunch_cmd = _build_relaunch_cmd(
        db_root, args.poll_interval, args.max_runtime_hours, state_dir, watcher_id,
    )

    # --- Load or initialise baseline snapshot ---
    baseline = _load_state(spath)
    current = _scan_issue_files(db_root)

    if baseline is None:
        # No usable prior state — initialise
        try:
            _save_state(spath, current)
        except OSError as e:
            print(f"[{_ts()}] WARN: failed to write state: {e}", flush=True)
        baseline = current
        print(
            f"[{_ts()}] Issue watcher v{_VERSION} — initialised state ({len(current)} issues). "
            f"Polling every {args.poll_interval}s.",
            flush=True,
        )
    else:
        # Check for changes that happened while the watcher was not running
        pending = _diff_snapshots(baseline, current)
        if pending:
            print(
                f"[{_ts()}] {len(pending)} change(s) detected since last run.",
                flush=True,
            )
            try:
                _save_state(spath, current)
            except OSError as e:
                print(f"[{_ts()}] WARN: failed to write state: {e}", flush=True)
            _print_changes_and_instructions(pending, baseline, current, relaunch_cmd)
            sys.exit(0)
        else:
            print(
                f"[{_ts()}] Issue watcher v{_VERSION} — resuming from saved state ({len(current)} issues). "
                f"Polling every {args.poll_interval}s.",
                flush=True,
            )

    # --- Instance guard + signal handling ---
    # KNOWN: non-atomic TOCTOU gap between _check_instance_guard and _write_pid_file.
    # In practice this watcher is re-launched sequentially, making a race extremely unlikely.
    _check_instance_guard(state_dir, watcher_id)

    running = [True]
    received_signal = [""]

    def _handle_signal(signum, _frame):
        running[0] = False
        received_signal[0] = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Write PID file after instance guard check and signal handler setup.
    _write_pid_file(state_dir, watcher_id)

    # --- Poll loop ---
    started_at = time.monotonic()
    poll_count = 0
    snapshot = current

    try:
        while running[0]:
            time.sleep(args.poll_interval)

            if not running[0]:
                break

            elapsed = time.monotonic() - started_at
            if elapsed > max_runtime_seconds:
                _remove_pid_file(state_dir, watcher_id)
                _print_timeout_instructions(args.max_runtime_hours, relaunch_cmd)
                sys.exit(0)

            poll_count += 1
            new_snapshot = _scan_issue_files(db_root)
            notifications = _diff_snapshots(snapshot, new_snapshot)
            status_summary = _format_status_summary(new_snapshot)

            if notifications:
                try:
                    _save_state(spath, new_snapshot)
                except OSError as e:
                    print(f"[{_ts()}] WARN: failed to write state: {e}", flush=True)
                print(
                    f"[{_ts()}] poll #{poll_count} | {status_summary} | "
                    f"{len(notifications)} change(s)",
                    flush=True,
                )
                _remove_pid_file(state_dir, watcher_id)
                _print_changes_and_instructions(
                    notifications, snapshot, new_snapshot, relaunch_cmd,
                )
                sys.exit(0)
            else:
                print(
                    f"[{_ts()}] Issue watcher v{_VERSION} | poll #{poll_count} | {status_summary} | no changes",
                    flush=True,
                )
                snapshot = new_snapshot

        # Exited via signal
        sig = received_signal[0] or "unknown"
        _remove_pid_file(state_dir, watcher_id)
        print(
            f"[{_ts()}] Issue watcher v{_VERSION} — exiting ({sig}).\n"
            f"Re-launch via Bash tool with run_in_background=true:\n"
            f"   {relaunch_cmd}",
            flush=True,
        )
    finally:
        _remove_pid_file(state_dir, watcher_id)


if __name__ == "__main__":
    main()
