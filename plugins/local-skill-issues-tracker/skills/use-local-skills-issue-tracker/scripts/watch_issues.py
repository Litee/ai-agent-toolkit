#!/usr/bin/env python3
"""Issue tracker watcher — poll-and-notify model.

Polls the skill issue tracker JSON files on disk. On change detected:
  long-poll-with-exit  Print change details and re-launch instructions, then exit.
                       Designed for Claude Code run_in_background mode.
  cmux-keystrokes      Send changes as keystrokes to a cmux surface. Runs indefinitely.
  tmux-keystrokes      Send changes as keystrokes to a tmux pane. Runs indefinitely.

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
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_STATE_DIR = os.path.expanduser(
    "~/.claude/plugin-data/local-skill-issues-tracker/use-local-skills-issue-tracker"
)
STATE_MAX_AGE_HOURS = 24.0
_HEARTBEAT_INTERVAL = 300  # 5 minutes (keystrokes modes)


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
# CmuxBridge
# ---------------------------------------------------------------------------

class CmuxBridge:
    """Sends keystrokes and optional notifications to cmux surfaces."""

    def __init__(
        self,
        surface_id: str,
        workspace_ref: Optional[str] = None,
        enable_notify: bool = False,
        enable_status: bool = False,
    ):
        self.surface_id = surface_id
        self.workspace_ref = workspace_ref
        self.enable_notify = enable_notify
        self.enable_status = enable_status

    def _run(self, cmd: list, timeout: int = 5) -> bool:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return result.returncode == 0
        except Exception:
            return False

    def send_to_claude(self, message: str) -> bool:
        """Send text as keystrokes to the Claude Code surface.

        Tries direct send first, then with --workspace flag.
        Returns True on success, False on failure (caller should exit).
        """
        if self._run(['cmux', 'send', '--surface', self.surface_id, message + '\n']):
            return True
        if self.workspace_ref:
            if self._run(['cmux', 'send', '--surface', self.surface_id,
                         '--workspace', self.workspace_ref, message + '\n']):
                return True
        return False

    def notify(self, title: str, body: str):
        if not self.enable_notify:
            return
        self._run(['cmux', 'notify', '--title', title, '--body', body])

    def set_status(self, key: str, value: str, color: Optional[str] = None):
        if not self.enable_status:
            return
        cmd = ['cmux', 'set-status', key, value]
        if color:
            cmd += ['--color', color]
        self._run(cmd)

    def clear_status(self, key: str):
        if not self.enable_status:
            return
        self._run(['cmux', 'clear-status', key])


# ---------------------------------------------------------------------------
# TmuxBridge
# ---------------------------------------------------------------------------

class TmuxBridge:
    """Sends keystrokes to a tmux pane. No-ops for cmux-specific features."""

    def __init__(self, tmux_pane: str):
        self.tmux_pane = tmux_pane
        self.enable_notify = False
        self.enable_status = False

    def _run(self, cmd: list, timeout: int = 5) -> bool:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return result.returncode == 0
        except Exception:
            return False

    def send_to_claude(self, message: str) -> bool:
        """Send text as a keystroke line to the tmux pane. Retries up to 10 times."""
        cmd = ['tmux', 'send-keys', '-t', self.tmux_pane, message + '\n', 'Enter']
        for attempt in range(11):
            if self._run(cmd):
                return True
            if attempt < 10:
                print(
                    f"[{_ts()}] WARN: tmux send-keys failed (attempt {attempt + 1}/11), "
                    f"retrying in 3s ...",
                    file=sys.stderr, flush=True,
                )
                time.sleep(3)
        print(
            f"[{_ts()}] ERROR: tmux send-keys failed after 11 attempts. Pane: {self.tmux_pane!r}.",
            file=sys.stderr, flush=True,
        )
        return False

    def notify(self, title: str, body: str):
        self._run(['tmux', 'display-message', '-t', self.tmux_pane, f"{title}: {body}"])

    def set_status(self, *_a, **_kw) -> None:
        pass  # no-op: tmux has no sidebar status

    def clear_status(self, *_a, **_kw) -> None:
        pass  # no-op


# ---------------------------------------------------------------------------
# cmux detection helpers
# ---------------------------------------------------------------------------

def _detect_own_surface() -> Optional[str]:
    try:
        result = subprocess.run(['cmux', 'identify', '--json'], capture_output=True, timeout=5)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('caller', {}).get('surface_ref')
    except Exception:
        pass
    return os.environ.get('CMUX_SURFACE_ID')


def _detect_workspace_ref() -> Optional[str]:
    try:
        result = subprocess.run(['cmux', 'identify', '--json'], capture_output=True, timeout=5)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('caller', {}).get('workspace_ref')
    except Exception:
        pass
    return os.environ.get('CMUX_WORKSPACE_ID')


# ---------------------------------------------------------------------------
# Filesystem scan
# ---------------------------------------------------------------------------

def _scan_issue_files(db_root: str) -> dict:
    """Scan all issue JSON files under db_root.

    Returns {file_path: {"mtime_ns": int, "issue_id": str, "status": str,
                          "title": str, "description": str,
                          "comments": list, "skill": str, "skill_version": str}}
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
                    "skill_version": issue.get("skill_version", ""),
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
    """Exit with an error if another process with watcher_id is already running."""
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

def _it_prefix() -> str:
    """Return '[Local Issue Tracker vX.Y.Z]' using the watcher's own version."""
    return f"[Local Issue Tracker v{_VERSION}]" if _VERSION and _VERSION != "unknown" else "[Local Issue Tracker]"


def _diff_snapshots(old: dict, new: dict) -> list:
    """Compare two snapshots and return a list of human-readable change strings.

    Each entry is prefixed with '[Local Issue Tracker vX.Y.Z]' so callers can forward
    lines verbatim. The version is the watcher's own version, not the skill version.
    """
    notifications = []
    pfx = _it_prefix()

    old_paths = set(old.keys())
    new_paths = set(new.keys())

    for path in new_paths - old_paths:
        info = new[path]
        notifications.append(
            f"{pfx} New issue #{info['issue_id']} for '{info['skill']}': "
            f"\"{info['title']}\" (status: {info['status']})"
        )

    for path in old_paths - new_paths:
        fname = os.path.basename(path)
        notifications.append(f"[Local Issue Tracker] Issue file removed: {fname}")

    for path in old_paths & new_paths:
        o = old[path]
        n = new[path]
        if n["mtime_ns"] == o["mtime_ns"]:
            continue
        if n["status"] != o["status"]:
            notifications.append(
                f"{pfx} Issue #{n['issue_id']} ('{n['skill']}') "
                f"status changed: {o['status']} -> {n['status']}"
            )
        old_count = len(o["comments"])
        new_count = len(n["comments"])
        if new_count > old_count:
            for c in n["comments"][old_count:]:
                text = c.get("text", "")
                preview = text[:80] + ("..." if len(text) > 80 else "")
                notifications.append(
                    f"{pfx} New comment on issue #{n['issue_id']} "
                    f"('{n['skill']}'): \"{preview}\""
                )
        if new_count < old_count:
            notifications.append(
                f"{pfx} Issue #{n['issue_id']} ('{n['skill']}') — comment removed"
            )
        if n["description"] != o["description"]:
            notifications.append(
                f"{pfx} Issue #{n['issue_id']} ('{n['skill']}') — description updated"
            )
        if n["title"] != o["title"]:
            notifications.append(
                f"{pfx} Issue #{n['issue_id']} ('{n['skill']}') — "
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
    mode: str = "long-poll-with-exit",
    cmux_surface: Optional[str] = None,
    cmux_workspace: Optional[str] = None,
    cmux_notify: bool = False,
    cmux_status: bool = False,
    keep_watcher_running: bool = False,
    tmux_pane: Optional[str] = None,
) -> str:
    """Build a shell-safe re-launch command with all non-default args made explicit."""
    cmd = f"python3 {shlex.quote(_script_path())}"
    # --db-root is always required
    cmd += f" --db-root {shlex.quote(db_root)}"
    if poll_interval != POLL_INTERVAL_DEFAULT:
        cmd += f" --poll-interval {poll_interval}"
    if max_runtime_hours != 24.0:
        cmd += f" --max-runtime-hours {max_runtime_hours}"
    if state_dir != DEFAULT_STATE_DIR:
        cmd += f" --state-dir {shlex.quote(state_dir)}"
    # Always include --watcher-id: re-launch may occur from a different CWD
    cmd += f" --watcher-id {shlex.quote(watcher_id)}"
    if mode != "long-poll-with-exit":
        cmd += f" --mode {shlex.quote(mode)}"
    if cmux_surface:
        cmd += f" --cmux-surface {shlex.quote(cmux_surface)}"
    if cmux_workspace:
        cmd += f" --cmux-workspace {shlex.quote(cmux_workspace)}"
    if cmux_notify:
        cmd += " --cmux-notify"
    if cmux_status:
        cmd += " --cmux-status"
    if keep_watcher_running:
        cmd += " --keep-watcher-running"
    if tmux_pane:
        cmd += f" --tmux-pane {shlex.quote(tmux_pane)}"
    socket_path = os.environ.get('CMUX_SOCKET_PATH', '')
    if socket_path:
        cmd = f'CMUX_SOCKET_PATH={shlex.quote(socket_path)} {cmd}'
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


def _deliver_via_bridge(
    bridge,
    notifications: list,
    surface_label: str,
    relaunch_cmd: str,
    state_dir: str,
    watcher_id: str,
) -> bool:
    """Send each notification line via bridge. Returns False if bridge becomes unreachable."""
    for note in notifications:
        if not bridge.send_to_claude(note):
            print(
                f"{surface_label} unreachable. Re-launch:\n  {relaunch_cmd}",
                file=sys.stderr, flush=True,
            )
            _remove_pid_file(state_dir, watcher_id)
            return False
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="watch_issues.py",
        description=(
            "Poll the skill issue tracker and deliver change notifications.\n\n"
            "Modes:\n"
            "  long-poll-with-exit  Exit on first change (for run_in_background).\n"
            "  cmux-keystrokes      Send changes as keystrokes to a cmux surface.\n"
            "  tmux-keystrokes      Send changes as keystrokes to a tmux pane."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s --db-root /path/to/tracker\n"
            "  %(prog)s --db-root /path/to/tracker --mode cmux-keystrokes"
            " --cmux-surface surface:3\n"
            "  %(prog)s --db-root /path/to/tracker --mode tmux-keystrokes --tmux-pane %%0\n"
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
    parser.add_argument(
        "--mode",
        choices=["long-poll-with-exit", "cmux-keystrokes", "tmux-keystrokes"],
        default="long-poll-with-exit",
        help="Delivery mode (default: long-poll-with-exit)",
    )

    # cmux-only flags
    cmux_group = parser.add_argument_group(
        "cmux flags (only valid with --mode cmux-keystrokes)"
    )
    cmux_group.add_argument(
        "--cmux-surface",
        metavar="SURFACE_REF",
        help="cmux surface ref of the CC session (required for cmux mode). "
             "Get from: cmux identify --json -> caller.surface_ref",
    )
    cmux_group.add_argument(
        "--cmux-workspace",
        metavar="WORKSPACE_REF",
        help="cmux workspace ref (auto-detected via cmux identify if omitted)",
    )
    cmux_group.add_argument(
        "--cmux-notify",
        action="store_true",
        help="Enable desktop notifications via cmux on changes",
    )
    cmux_group.add_argument(
        "--cmux-status",
        action="store_true",
        help="Enable cmux sidebar status badge",
    )
    cmux_group.add_argument(
        "--keep-watcher-running",
        action="store_true",
        help="Keep the watcher split open after exit (default: auto-close after 3s)",
    )

    # tmux-only flags
    tmux_group = parser.add_argument_group(
        "tmux flags (only valid with --mode tmux-keystrokes)"
    )
    tmux_group.add_argument(
        "--tmux-pane",
        metavar="PANE_ID",
        help="tmux pane ID to send keystrokes to (e.g. %%0). Required for tmux mode. "
             "Get from: tmux display-message -p '#{pane_id}' or $TMUX_PANE",
    )

    args = parser.parse_args()

    if not (POLL_INTERVAL_MIN <= args.poll_interval <= POLL_INTERVAL_MAX):
        print(
            f"Error: --poll-interval must be between {POLL_INTERVAL_MIN} "
            f"and {POLL_INTERVAL_MAX}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Mode-specific validation
    if args.mode == "cmux-keystrokes" and not args.cmux_surface:
        print("Error: --cmux-surface is required when --mode cmux-keystrokes.", file=sys.stderr)
        sys.exit(1)
    if args.mode == "tmux-keystrokes" and not args.tmux_pane:
        print("Error: --tmux-pane is required when --mode tmux-keystrokes.", file=sys.stderr)
        sys.exit(1)

    db_root = os.path.expanduser(args.db_root)
    state_dir = os.path.expanduser(args.state_dir)
    watcher_id = args.watcher_id if args.watcher_id is not None else os.getcwd()
    spath = _state_path(state_dir, watcher_id)
    max_runtime_seconds = int(args.max_runtime_hours * 3600)
    mode = args.mode

    # Resolve cmux workspace for cmux mode
    cmux_workspace = None
    if mode == "cmux-keystrokes":
        cmux_workspace = args.cmux_workspace or _detect_workspace_ref()

    relaunch_cmd = _build_relaunch_cmd(
        db_root, args.poll_interval, args.max_runtime_hours, state_dir, watcher_id,
        mode=mode,
        cmux_surface=args.cmux_surface,
        cmux_workspace=cmux_workspace,
        cmux_notify=args.cmux_notify,
        cmux_status=args.cmux_status,
        keep_watcher_running=args.keep_watcher_running,
        tmux_pane=args.tmux_pane,
    )

    # --- Load or initialise baseline snapshot ---
    baseline = _load_state(spath)
    current = _scan_issue_files(db_root)
    startup_pending: list = []

    if baseline is None:
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
        startup_pending = _diff_snapshots(baseline, current)
        if startup_pending:
            print(
                f"[{_ts()}] {len(startup_pending)} change(s) detected since last run.",
                flush=True,
            )
            try:
                _save_state(spath, current)
            except OSError as e:
                print(f"[{_ts()}] WARN: failed to write state: {e}", flush=True)
            if mode == "long-poll-with-exit":
                _print_changes_and_instructions(startup_pending, baseline, current, relaunch_cmd)
                sys.exit(0)
            # keystrokes modes: fall through to bridge setup, then deliver startup_pending
        else:
            print(
                f"[{_ts()}] Issue watcher v{_VERSION} — resuming from saved state "
                f"({len(current)} issues). Polling every {args.poll_interval}s.",
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

    # SIGUSR1 for keystrokes modes — exit cleanly (exit code 0, not 144)
    if mode in ("cmux-keystrokes", "tmux-keystrokes"):
        def _handle_sigusr1(_signum, _frame):
            """Handle SIGUSR1 from Claude Code background task manager."""
            print(f"[{_ts()}] Received SIGUSR1 — exiting cleanly.", file=sys.stderr, flush=True)
            _remove_pid_file(state_dir, watcher_id)
            sys.exit(0)
        signal.signal(signal.SIGUSR1, _handle_sigusr1)

    _write_pid_file(state_dir, watcher_id)

    # --- Bridge setup ---
    bridge = None
    own_surface_id = None
    surface_label = ""

    if mode == "cmux-keystrokes":
        bridge = CmuxBridge(
            surface_id=args.cmux_surface,
            workspace_ref=cmux_workspace,
            enable_notify=args.cmux_notify,
            enable_status=args.cmux_status,
        )
        surface_label = f"Surface {args.cmux_surface}"
        if not args.keep_watcher_running:
            own_surface_id = _detect_own_surface()
        if own_surface_id:
            print(
                f"[{_ts()}] Watcher split: {own_surface_id} "
                f"(auto-close on exit; use --keep-watcher-running to prevent)",
                file=sys.stderr, flush=True,
            )
        # Send startup confirmation
        if not bridge.send_to_claude(
            f"[Issue Watcher v{_VERSION}] Started. ID: {watcher_id} | DB: {db_root}"
        ):
            print(
                f"Surface {args.cmux_surface} unreachable. "
                f"Get fresh refs via `cmux identify --json` and re-launch:\n"
                f"  {relaunch_cmd}",
                file=sys.stderr, flush=True,
            )
            _remove_pid_file(state_dir, watcher_id)
            sys.exit(1)
        # Deliver any changes detected at startup
        if startup_pending:
            if not _deliver_via_bridge(
                bridge, startup_pending, surface_label, relaunch_cmd, state_dir, watcher_id
            ):
                sys.exit(1)

    elif mode == "tmux-keystrokes":
        bridge = TmuxBridge(tmux_pane=args.tmux_pane)
        surface_label = f"tmux pane {args.tmux_pane}"
        # Send startup confirmation
        if not bridge.send_to_claude(
            f"[Issue Watcher v{_VERSION}] Started. ID: {watcher_id} | DB: {db_root}"
        ):
            print(
                f"tmux pane {args.tmux_pane} unreachable. "
                f"Check pane ID and re-launch:\n"
                f"  {relaunch_cmd}",
                file=sys.stderr, flush=True,
            )
            _remove_pid_file(state_dir, watcher_id)
            sys.exit(1)
        # Deliver any changes detected at startup
        if startup_pending:
            if not _deliver_via_bridge(
                bridge, startup_pending, surface_label, relaunch_cmd, state_dir, watcher_id
            ):
                sys.exit(1)

    # --- Poll loop ---
    started_at = time.monotonic()
    poll_count = 0
    snapshot = current
    last_heartbeat = time.monotonic()

    try:
        while running[0]:
            time.sleep(args.poll_interval)

            if not running[0]:
                break

            elapsed = time.monotonic() - started_at
            if elapsed > max_runtime_seconds:
                _remove_pid_file(state_dir, watcher_id)
                if mode == "long-poll-with-exit":
                    _print_timeout_instructions(args.max_runtime_hours, relaunch_cmd)
                else:
                    msg = (
                        f"[Issue Watcher v{_VERSION}] Max runtime ({args.max_runtime_hours}h) "
                        f"reached. Re-launch: {relaunch_cmd}"
                    )
                    if bridge:
                        bridge.send_to_claude(msg)
                    print(msg, file=sys.stderr, flush=True)
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

                if mode == "long-poll-with-exit":
                    _remove_pid_file(state_dir, watcher_id)
                    _print_changes_and_instructions(
                        notifications, snapshot, new_snapshot, relaunch_cmd,
                    )
                    sys.exit(0)
                else:
                    # Deliver via bridge, continue running
                    if not _deliver_via_bridge(
                        bridge, notifications, surface_label, relaunch_cmd,
                        state_dir, watcher_id,
                    ):
                        sys.exit(1)
                    snapshot = new_snapshot
            else:
                if mode == "long-poll-with-exit":
                    print(
                        f"[{_ts()}] Issue watcher v{_VERSION} | poll #{poll_count} | "
                        f"{status_summary} | no changes",
                        flush=True,
                    )
                else:
                    # Heartbeat every 5 minutes in keystrokes modes
                    now_mono = time.monotonic()
                    if now_mono - last_heartbeat >= _HEARTBEAT_INTERVAL:
                        print(
                            f"[{_ts()}] Issue watcher v{_VERSION} | poll #{poll_count} | "
                            f"{status_summary} | no changes",
                            flush=True,
                        )
                        last_heartbeat = now_mono
                snapshot = new_snapshot

        # Exited via signal
        sig = received_signal[0] or "unknown"
        _remove_pid_file(state_dir, watcher_id)
        if mode in ("cmux-keystrokes", "tmux-keystrokes") and bridge:
            bridge.send_to_claude(
                f"[Issue Watcher v{_VERSION}] Exiting ({sig}). Re-launch: {relaunch_cmd}"
            )
        print(
            f"[{_ts()}] Issue watcher v{_VERSION} — exiting ({sig}).\n"
            f"Re-launch via Bash tool with run_in_background=true:\n"
            f"   {relaunch_cmd}",
            flush=True,
        )
    finally:
        _remove_pid_file(state_dir, watcher_id)
        if own_surface_id:
            time.sleep(3)
            subprocess.run(
                ['cmux', 'close-surface', '--surface', own_surface_id],
                capture_output=True, timeout=5,
            )


if __name__ == "__main__":
    main()
