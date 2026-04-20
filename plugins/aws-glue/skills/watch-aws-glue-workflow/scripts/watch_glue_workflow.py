#!/usr/bin/env python3
"""
AWS Glue Workflow Watcher

Monitor long-running AWS Glue workflow executions with background notifications.
Tracks overall workflow state plus per-node (job/crawler) progress.

Three delivery modes:
  long-poll-with-exit    Poll until workflow reaches terminal state or a node fails.
                         Run in background. Re-launch after processing output.
  cmux-keystrokes        Poll and send state changes as keystrokes to a CC surface.
  tmux-keystrokes        Same as cmux-keystrokes but uses tmux send-keys.

State persisted at: ~/.claude/plugin-data/aws-glue/watch-aws-glue-workflow/
"""

import argparse
import json
import os
import random
import re as _re
import shlex
import signal
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Workflow-level terminal states
TERMINAL_STATES = {'COMPLETED', 'STOPPED', 'ERROR'}

# Node-level states that indicate failure (triggers early exit in long-poll mode)
NODE_FAILURE_STATES = {'FAILED', 'ERROR', 'TIMEOUT'}

STATE_DIR = Path.home() / '.claude' / 'plugin-data' / 'aws-glue' / 'watch-aws-glue-workflow'
_HEARTBEAT_INTERVAL = 300
_VERSION_CHECK_INTERVAL = 3600


def _version_from_path(path: str) -> str:
    m = _re.search(r'/(\d+\.\d+\.\d+)/skills/', path)
    return m.group(1) if m else 'unknown'


_VERSION = _version_from_path(__file__)
_ver = lambda: f"v{_VERSION}" if _VERSION != 'unknown' else "(unknown version)"

_INSTALLED_PLUGINS_PATH = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'


def _plugin_identity_from_path(path: str):
    m = _re.search(r'/cache/([^/]+)/([^/]+)/\d+\.\d+\.\d+/skills/', path)
    return (m.group(1), m.group(2)) if m else ('', '')


_MARKETPLACE_NAME, _PLUGIN_NAME = _plugin_identity_from_path(__file__)


def _parse_semver(version: str) -> tuple:
    try:
        parts = version.split('.')
        return tuple(int(p) for p in parts[:3])
    except (ValueError, TypeError):
        return (0, 0, 0)


def _check_version_drift() -> None:
    if not _PLUGIN_NAME or _VERSION == 'unknown':
        return
    try:
        raw = _INSTALLED_PLUGINS_PATH.read_text()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return
    key = f"{_PLUGIN_NAME}@{_MARKETPLACE_NAME}"
    entries = data.get('plugins', {}).get(key) or data.get(key)
    if not isinstance(entries, list) or not entries:
        return
    best_version = _VERSION
    best_tuple = _parse_semver(_VERSION)
    for entry in entries:
        v = entry.get('version', '')
        vt = _parse_semver(v)
        if vt > best_tuple:
            best_version = v
            best_tuple = vt
    if best_tuple > _parse_semver(_VERSION):
        print(
            f"[{ts()}] [Glue Workflow Watcher {_ver()}] WARNING: Running version {_VERSION} but "
            f"version {best_version} is installed. Restart to pick up the newer version.",
            file=sys.stderr, flush=True,
        )


def ts() -> str:
    return datetime.now(timezone.utc).strftime('%H:%M UTC')


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def format_elapsed(seconds: float) -> str:
    seconds = int(seconds)
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"
    elif seconds >= 60:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"
    return f"{seconds}s"


# ---------------------------------------------------------------------------
# Instance guard / PID file
# ---------------------------------------------------------------------------

def _pid_file_path(watcher_id: str) -> Path:
    return STATE_DIR / f"watcher-{watcher_id}.pid"


def _check_instance_guard(watcher_id: str) -> None:
    pid_path = _pid_file_path(watcher_id)
    if not pid_path.exists():
        return
    try:
        pid = int(pid_path.read_text().strip())
    except (ValueError, OSError):
        return
    try:
        os.kill(pid, 0)
        print(
            f"[Glue Workflow Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)
    except ProcessLookupError:
        return
    except PermissionError:
        print(
            f"[Glue Workflow Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)


def _write_pid_file(watcher_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _pid_file_path(watcher_id).write_text(str(os.getpid()))
    except OSError as e:
        print(f"[Glue Workflow Watcher] FATAL: failed to write PID file: {e}", file=sys.stderr, flush=True)
        sys.exit(1)


def _remove_pid_file(watcher_id: str) -> None:
    try:
        _pid_file_path(watcher_id).unlink(missing_ok=True)
    except OSError:
        pass


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, PermissionError, ValueError):
        return False


def _make_watcher_id() -> str:
    return os.urandom(4).hex()


# ---------------------------------------------------------------------------
# Throttle backoff helper
# ---------------------------------------------------------------------------

def _throttle_sleep(poll_interval: int) -> int:
    sleep_time = 3.5 * 60 + random.uniform(-30, 30)
    print(
        f"[{ts()}] Throttle cool-down: sleeping {sleep_time:.0f}s then doubling interval.",
        file=sys.stderr, flush=True,
    )
    time.sleep(sleep_time)
    return min(poll_interval * 2, 3600)


# ---------------------------------------------------------------------------
# GlueWorkflowClient
# ---------------------------------------------------------------------------

class GlueWorkflowClient:
    def __init__(self, profile: str, region: Optional[str] = None):
        self.profile = profile
        self.region = region

    def _client(self):
        import boto3
        kwargs = {'profile_name': self.profile}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.Session(**kwargs).client('glue')

    def get_workflow_run(self, workflow_name: str, run_id: str) -> dict:
        client = self._client()
        return client.get_workflow_run(
            Name=workflow_name,
            RunId=run_id,
            IncludeGraph=True,
        )['Run']


# ---------------------------------------------------------------------------
# Node parsing helpers
# ---------------------------------------------------------------------------

def _extract_nodes(run: dict) -> list[dict]:
    """Return list of {name, type, state} for all job/crawler nodes."""
    graph = run.get('Graph') or {}
    nodes = graph.get('Nodes') or []
    result = []
    for node in nodes:
        node_type = node.get('Type', '')
        if node_type == 'TRIGGER':
            continue
        name = node.get('Name', '?')
        state = 'PENDING'
        if node_type == 'JOB':
            runs = (node.get('JobDetails') or {}).get('JobRuns') or []
            if runs:
                # Most recent run is first
                state = runs[0].get('JobRunState', 'PENDING')
        elif node_type == 'CRAWLER':
            crawls = (node.get('CrawlerDetails') or {}).get('Crawls') or []
            if crawls:
                state = crawls[0].get('Status', 'PENDING')
        result.append({'name': name, 'type': node_type, 'state': state})
    return result


def _nodes_summary(nodes: list[dict]) -> str:
    """Format a compact one-line summary of node states."""
    if not nodes:
        return ''
    state_counts: dict[str, int] = {}
    for n in nodes:
        s = n['state']
        state_counts[s] = state_counts.get(s, 0) + 1
    parts = []
    for state in ('RUNNING', 'SUCCEEDED', 'COMPLETED', 'FAILED', 'ERROR', 'TIMEOUT',
                  'STARTING', 'WAITING', 'STOPPED', 'PENDING'):
        count = state_counts.pop(state, 0)
        if count:
            parts.append(f"{state}:{count}")
    for state, count in sorted(state_counts.items()):
        parts.append(f"{state}:{count}")
    return ' | '.join(parts)


def _format_nodes_table(nodes: list[dict]) -> str:
    """Format nodes as a compact table string."""
    if not nodes:
        return '  (no job/crawler nodes)'
    lines = []
    max_name = max(len(n['name']) for n in nodes)
    max_type = max(len(n['type']) for n in nodes)
    for n in nodes:
        lines.append(f"  {n['name']:<{max_name}}  {n['type']:<{max_type}}  {n['state']}")
    return '\n'.join(lines)


def _find_failed_nodes(nodes: list[dict]) -> list[dict]:
    return [n for n in nodes if n['state'] in NODE_FAILURE_STATES]


# ---------------------------------------------------------------------------
# WatcherState
# ---------------------------------------------------------------------------

class WatcherState:
    def __init__(self, watcher_id: str):
        self.watcher_id = watcher_id
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = STATE_DIR / f"state-{watcher_id}.json"

    def read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return {}

    def write(self, data: dict):
        tmp = self.path.with_suffix(f'.{os.getpid()}.tmp')
        try:
            tmp.write_text(json.dumps(data, indent=2))
            os.replace(tmp, self.path)
        except Exception:
            try:
                tmp.unlink()
            except Exception:
                pass
            raise

    def update(self, **kwargs):
        data = self.read()
        data.update(kwargs)
        self.write(data)

    @classmethod
    def list_all(cls) -> list:
        if not STATE_DIR.exists():
            return []
        results = []
        for p in sorted(STATE_DIR.glob('state-*.json')):
            try:
                data = json.loads(p.read_text())
                results.append(data)
            except Exception:
                pass
        return results


# ---------------------------------------------------------------------------
# CmuxBridge
# ---------------------------------------------------------------------------

class CmuxBridge:
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
        cmd = ['tmux', 'send-keys', '-t', self.tmux_pane, message + '\n', 'Enter']
        for attempt in range(11):
            if self._run(cmd):
                return True
            if attempt < 10:
                print(
                    f"[{ts()}] WARN: tmux send-keys failed (attempt {attempt + 1}/11), "
                    f"retrying in 3s ...",
                    file=sys.stderr, flush=True,
                )
                time.sleep(3)
        print(
            f"[{ts()}] ERROR: tmux send-keys failed after 11 attempts. Pane: {self.tmux_pane!r}.",
            file=sys.stderr, flush=True,
        )
        return False

    def notify(self, title: str, body: str):
        self._run(['tmux', 'display-message', '-t', self.tmux_pane, f"{title}: {body}"])

    def set_status(self, *_a, **_kw) -> None:
        pass

    def clear_status(self, *_a, **_kw) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_workspace_ref() -> Optional[str]:
    try:
        result = subprocess.run(['cmux', 'identify', '--json'], capture_output=True, timeout=5)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('caller', {}).get('workspace_ref')
    except Exception:
        pass
    return os.environ.get('CMUX_WORKSPACE_ID')


def _is_credential_error(e: Exception) -> bool:
    err_str = str(e)
    return any(k in err_str for k in (
        'ExpiredToken', 'InvalidClientTokenId', 'ExpiredTokenException',
        'TokenExpiredException', 'NotAuthorizedException', 'InvalidSignatureException',
    ))


def _is_throttle_error(e: Exception) -> bool:
    err_str = str(e)
    response = getattr(e, 'response', None)
    error_code = response.get('Error', {}).get('Code', '') if isinstance(response, dict) else ''
    return 'ThrottlingException' in err_str or 'Throttling' in err_str or error_code == 'ThrottlingException'


def _build_restart_command(
    script_path: str,
    mode: str,
    workflow_name: str,
    run_id: str,
    watcher_id: str,
    profile: str,
    region: Optional[str],
    poll_interval: int,
    surface_ref: Optional[str] = None,
    workspace_ref: Optional[str] = None,
    cmux_notify: bool = False,
    cmux_status: bool = False,
    max_runtime_hours: int = 24,
    tmux_pane: Optional[str] = None,
) -> str:
    parts = [f"python3 {shlex.quote(script_path)}", "watch"]
    parts.append(f"--workflow-name {shlex.quote(workflow_name)}")
    parts.append(f"--run-id {shlex.quote(run_id)}")
    parts.append(f"--profile {shlex.quote(profile)}")
    if region:
        parts.append(f"--region {shlex.quote(region)}")
    parts.append(f"--mode {shlex.quote(mode)}")
    parts.append(f"--poll-interval-seconds {poll_interval}")
    parts.append(f"--watcher-id {shlex.quote(watcher_id)}")
    parts.append(f"--max-runtime-hours {max_runtime_hours}")
    if surface_ref:
        parts.append(f"--cmux-surface {shlex.quote(surface_ref)}")
    if workspace_ref:
        parts.append(f"--cmux-workspace {shlex.quote(workspace_ref)}")
    if cmux_notify:
        parts.append("--cmux-notify")
    if cmux_status:
        parts.append("--cmux-status")
    if tmux_pane:
        parts.append(f"--tmux-pane {shlex.quote(tmux_pane)}")
    cmd = ' '.join(parts)
    socket_path = os.environ.get('CMUX_SOCKET_PATH', '')
    if socket_path:
        cmd = f'CMUX_SOCKET_PATH={shlex.quote(socket_path)} {cmd}'
    return cmd


def _print_startup_summary(workflow_name: str, run_id: str, run: dict, nodes: list[dict]):
    state = run.get('Status', 'UNKNOWN')
    started_on = run.get('StartedOn')
    stats = run.get('Statistics') or {}

    print('=' * 60, flush=True)
    print(f"Workflow:   {workflow_name}", flush=True)
    print(f"Run:        {run_id}", flush=True)
    print(f"State:      {state}", flush=True)

    if started_on:
        started_str = (
            started_on.strftime('%Y-%m-%d %H:%M:%S UTC')
            if hasattr(started_on, 'strftime') else str(started_on)
        )
        print(f"Started:    {started_str}", flush=True)

    if stats:
        total = stats.get('TotalActions', 0)
        running = stats.get('RunningActions', 0)
        succeeded = stats.get('SucceededActions', 0)
        failed = stats.get('FailedActions', 0) + stats.get('ErroredActions', 0)
        waiting = stats.get('WaitingActions', 0)
        print(
            f"Actions:    {total} total | {running} running | "
            f"{succeeded} succeeded | {failed} failed | {waiting} waiting",
            flush=True,
        )

    if nodes:
        print(f"\nNodes ({len(nodes)}):", flush=True)
        print(_format_nodes_table(nodes), flush=True)

    print('=' * 60, flush=True)
    print(flush=True)


# ---------------------------------------------------------------------------
# Core polling loop
# ---------------------------------------------------------------------------

def _poll_loop(
    args,
    mode: str,
    watcher_id: str,
    workflow_name: str,
    run_id: str,
    profile: str,
    region: Optional[str],
    poll_interval: int,
    max_runtime_hours: int,
    restart_cmd: str,
    bridge: Optional[CmuxBridge | TmuxBridge],
    state: WatcherState,
    initial_previous_state: Optional[str] = None,
    initial_prev_node_states: Optional[dict] = None,
):
    client = GlueWorkflowClient(profile=profile, region=region)
    status_key = f"glue-wf-{watcher_id[:6]}"

    running = [True]
    received_signal = ['']

    def _handle_signal(signum, _frame):
        running[0] = False
        received_signal[0] = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if mode in ('cmux-keystrokes', 'tmux-keystrokes'):
        def _handle_sigusr1(_signum, _frame):
            print(f"[{ts()}] Received SIGUSR1 — exiting cleanly.", file=sys.stderr, flush=True)
            _remove_pid_file(watcher_id)
            sys.exit(0)
        signal.signal(signal.SIGUSR1, _handle_sigusr1)

    _write_pid_file(watcher_id)

    started_at = time.monotonic()
    max_runtime_seconds = max_runtime_hours * 3600
    consecutive_cred_errors = 0
    consecutive_poll_errors = 0
    cred_notified = False
    last_heartbeat = time.monotonic()
    last_version_check = time.monotonic()
    printed_summary = False
    previous_state = initial_previous_state
    # dict[node_name, state] — tracks last-known per-node state to detect transitions
    prev_node_states: dict = dict(initial_prev_node_states) if initial_prev_node_states else {}
    first_poll = True

    try:
        while running[0]:
            if first_poll:
                first_poll = False
            else:
                time.sleep(poll_interval)

            if not running[0]:
                break

            elapsed_total = time.monotonic() - started_at
            if elapsed_total > max_runtime_seconds:
                msg = (
                    f"[Glue Workflow Watcher {_ver()}] Max runtime ({max_runtime_hours}h) reached. "
                    f"Last known state: {previous_state}. Re-launch: {restart_cmd}"
                )
                if bridge:
                    bridge.send_to_claude(msg)
                    bridge.clear_status(status_key)
                else:
                    print(msg, file=sys.stderr, flush=True)
                break

            try:
                run = client.get_workflow_run(workflow_name, run_id)
                if consecutive_cred_errors > 0 and cred_notified:
                    recovery_msg = f"[Glue Workflow Watcher {_ver()}] AWS credentials recovered — resuming."
                    if bridge:
                        bridge.send_to_claude(recovery_msg)
                    else:
                        print(f"[{ts()}] {recovery_msg}", file=sys.stderr, flush=True)
                    cred_notified = False
                consecutive_cred_errors = 0
                consecutive_poll_errors = 0
            except Exception as e:
                if _is_credential_error(e):
                    consecutive_cred_errors += 1
                    print(
                        f"[{ts()}] Credential error #{consecutive_cred_errors}: {e}",
                        file=sys.stderr, flush=True,
                    )
                    if consecutive_cred_errors >= 5 and not cred_notified:
                        msg = (
                            f"[Glue Workflow Watcher {_ver()}] {consecutive_cred_errors} consecutive "
                            f"AWS credential errors. Please re-authenticate. "
                            f"Watcher will auto-recover when credentials are refreshed."
                        )
                        if bridge:
                            bridge.send_to_claude(msg)
                            bridge.notify("Glue Workflow Watcher", "Credentials expired")
                            bridge.clear_status(status_key)
                        else:
                            print(f"[{ts()}] WARN: {msg}", file=sys.stderr, flush=True)
                        cred_notified = True
                    time.sleep(min(60 * consecutive_cred_errors, 3600))
                    continue

                if _is_throttle_error(e):
                    print(f"[{ts()}] Throttled. Applying jittered backoff.", file=sys.stderr, flush=True)
                    poll_interval = _throttle_sleep(poll_interval)
                    restart_cmd = _build_restart_command(
                        os.path.abspath(__file__), mode, workflow_name, run_id,
                        watcher_id, profile, region, poll_interval,
                        surface_ref=getattr(args, 'cmux_surface', None),
                        workspace_ref=getattr(args, 'cmux_workspace', None),
                        cmux_notify=getattr(args, 'cmux_notify', False),
                        cmux_status=getattr(args, 'cmux_status', False),
                        max_runtime_hours=max_runtime_hours,
                        tmux_pane=getattr(args, 'tmux_pane', None),
                    )
                    state.update(poll_interval_seconds=poll_interval, launch_command=restart_cmd)
                    continue

                consecutive_poll_errors += 1
                print(f"[{ts()}] WARN: Poll error #{consecutive_poll_errors}: {e}", file=sys.stderr, flush=True)
                if bridge and consecutive_poll_errors >= 3:
                    bridge.send_to_claude(
                        f"[Glue Workflow Watcher {_ver()}] {consecutive_poll_errors} consecutive poll errors. "
                        f"Last: {str(e)[:80]}. Still watching."
                    )
                    consecutive_poll_errors = 0
                time.sleep(poll_interval)
                continue

            current_state = run.get('Status', 'UNKNOWN')
            nodes = _extract_nodes(run)
            stats = run.get('Statistics') or {}

            if not printed_summary:
                _print_startup_summary(workflow_name, run_id, run, nodes)
                print("Poll columns: workflow state | actions: total/running/succeeded/failed", flush=True)
                print(flush=True)
                printed_summary = True

            # Build stats line
            total = stats.get('TotalActions', 0)
            running_count = stats.get('RunningActions', 0)
            succeeded = stats.get('SucceededActions', 0)
            failed = stats.get('FailedActions', 0) + stats.get('ErroredActions', 0)
            nodes_line = _nodes_summary(nodes)
            stats_line = f"actions: {total} total / {running_count} running / {succeeded} ok / {failed} fail"
            print(f"[{ts()}] {current_state} | {stats_line} | nodes: {nodes_line}", flush=True)

            # Detect per-node transitions since last poll
            current_node_states = {n['name']: n['state'] for n in nodes}
            node_events = []
            if prev_node_states:
                for name, new_node_state in current_node_states.items():
                    old_node_state = prev_node_states.get(name)
                    if old_node_state is not None and old_node_state != new_node_state:
                        node_type = next((n['type'] for n in nodes if n['name'] == name), 'NODE')
                        node_events.append({
                            'name': name,
                            'type': node_type,
                            'previous_state': old_node_state,
                            'new_state': new_node_state,
                        })
            prev_node_states = current_node_states

            state.update(
                current_state=current_state,
                previous_state=previous_state,
                last_poll_at=now_iso(),
                stats=stats,
                node_states=current_node_states,
            )

            has_terminal = current_state in TERMINAL_STATES
            state_changed = current_state != previous_state
            failed_nodes = _find_failed_nodes(nodes)
            elapsed_fmt = format_elapsed(elapsed_total)
            prefix = f"[Glue Workflow Watcher {_ver()}]"

            # ----------------------------------------------------------------
            # Build the event list for this tick
            # ----------------------------------------------------------------
            events: list[dict] = []

            # Workflow-level state change event
            if state_changed:
                if has_terminal:
                    fail_info = ''
                    if failed_nodes:
                        fail_info = f" Failed nodes: {', '.join(n['name'] for n in failed_nodes)}."
                    summary = (
                        f"{prefix} {workflow_name} ({run_id[:12]}) | "
                        f"{previous_state or '?'} -> {current_state} ({ts()}). "
                        f"Elapsed: {elapsed_fmt}. "
                        f"Actions: {succeeded} ok / {failed} fail / {total} total.{fail_info}"
                    )
                    print(
                        f"[{ts()}] WORKFLOW TERMINAL: {previous_state} -> {current_state} "
                        f"after {elapsed_fmt}",
                        flush=True,
                    )
                else:
                    prev_label = f"{previous_state} -> " if previous_state else ""
                    summary = (
                        f"{prefix} {workflow_name} ({run_id[:12]}) | "
                        f"{prev_label}{current_state} ({ts()})"
                    )
                    print(f"[{ts()}] STATE CHANGE: {prev_label}{current_state}", flush=True)
                events.append({
                    'workflow_name': workflow_name,
                    'run_id': run_id,
                    'event_type': 'workflow_terminal' if has_terminal else 'state_changed',
                    'previous_state': previous_state,
                    'new_state': current_state,
                    'summary': summary,
                    'elapsed_seconds': int(elapsed_total),
                    'stats': stats,
                    'nodes': nodes,
                    'failed_nodes': failed_nodes,
                })
                previous_state = current_state

            # Per-node transition events
            for ne in node_events:
                node_summary = (
                    f"{prefix} {workflow_name} | node {ne['name']} ({ne['type']}) "
                    f"{ne['previous_state']} -> {ne['new_state']} ({ts()})"
                )
                is_failure = ne['new_state'] in NODE_FAILURE_STATES
                print(
                    f"[{ts()}] NODE {'FAILURE' if is_failure else 'TRANSITION'}: "
                    f"{ne['name']} {ne['previous_state']} -> {ne['new_state']}",
                    flush=True,
                )
                events.append({
                    'workflow_name': workflow_name,
                    'run_id': run_id,
                    'event_type': 'node_failure' if is_failure else 'node_transition',
                    'node_name': ne['name'],
                    'node_type': ne['type'],
                    'node_previous_state': ne['previous_state'],
                    'node_new_state': ne['new_state'],
                    'summary': node_summary,
                    'elapsed_seconds': int(elapsed_total),
                    'stats': stats,
                    'nodes': nodes,
                    'failed_nodes': [n for n in nodes if n['name'] == ne['name']] if is_failure else [],
                })

            # ----------------------------------------------------------------
            # Deliver events
            # ----------------------------------------------------------------
            if not events:
                pass  # nothing to deliver this tick

            elif mode == 'long-poll-with-exit':
                # Exit as soon as any event arrives so the LLM can act
                output = {
                    'events': events,
                    'watcher_id': watcher_id,
                    'instruction': f"Re-launch the watcher FIRST, then process events.\n{restart_cmd}",
                }
                _remove_pid_file(watcher_id)
                print(json.dumps(output, indent=2))
                sys.exit(0)

            else:
                # cmux / tmux: send each event as a keystroke, keep running
                for ev in events:
                    if bridge:
                        is_wf_terminal = ev['event_type'] == 'workflow_terminal'
                        color = None
                        if is_wf_terminal:
                            color = '#196F3D' if ev.get('new_state') == 'COMPLETED' else '#B71C1C'
                            bridge.set_status(status_key, ev['new_state'], color=color)
                        elif ev['event_type'] in ('node_failure',):
                            bridge.set_status(status_key, f"node-fail:{ev['node_name'][:10]}", color='#B71C1C')

                        # Only send keystrokes for non-initial state (skip startup "None -> RUNNING")
                        if ev['event_type'] != 'state_changed' or ev['previous_state'] is not None:
                            bridge.send_to_claude(ev['summary'])
                            bridge.notify(f"Glue Workflow: {workflow_name}", ev['summary'])

                        if is_wf_terminal:
                            bridge.clear_status(status_key)
                            return

            if not running[0]:
                break

            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{ts()}] Watching '{workflow_name}' -- state: {current_state} (poll_interval={poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now
            if now - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now

        sig = received_signal[0] or 'timeout'
        print(
            f"[Glue Workflow Watcher {_ver()}] Exiting ({sig}).\n"
            f"Re-launch:\n  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
        if bridge:
            bridge.clear_status(status_key)
    finally:
        _remove_pid_file(watcher_id)


# ---------------------------------------------------------------------------
# Subcommand: watch
# ---------------------------------------------------------------------------

def cmd_watch(args):
    if args.poll_interval_seconds < 60:
        print("Error: --poll-interval-seconds must be at least 60.", file=sys.stderr)
        sys.exit(1)
    if args.poll_interval_seconds > 3600:
        print("Error: --poll-interval-seconds must be at most 3600.", file=sys.stderr)
        sys.exit(1)

    mode = args.mode
    if mode == 'cmux-keystrokes' and not args.cmux_surface:
        print("Error: --cmux-surface is required when --mode cmux-keystrokes.", file=sys.stderr)
        sys.exit(1)
    if mode == 'tmux-keystrokes' and not args.tmux_pane:
        print("Error: --tmux-pane is required when --mode tmux-keystrokes.", file=sys.stderr)
        sys.exit(1)

    workflow_name = args.workflow_name
    run_id = args.run_id
    profile = args.profile
    region = args.region
    poll_interval = args.poll_interval_seconds
    max_runtime_hours = args.max_runtime_hours
    watcher_id = args.watcher_id or _make_watcher_id()
    script_path = os.path.abspath(__file__)

    surface_ref = getattr(args, 'cmux_surface', None)
    workspace_ref = getattr(args, 'cmux_workspace', None) or (
        _detect_workspace_ref() if mode == 'cmux-keystrokes' else None
    )
    tmux_pane = getattr(args, 'tmux_pane', None)

    restart_cmd = _build_restart_command(
        script_path, mode, workflow_name, run_id, watcher_id, profile, region, poll_interval,
        surface_ref=surface_ref,
        workspace_ref=workspace_ref,
        cmux_notify=getattr(args, 'cmux_notify', False),
        cmux_status=getattr(args, 'cmux_status', False),
        max_runtime_hours=max_runtime_hours,
        tmux_pane=tmux_pane,
    )

    _check_instance_guard(watcher_id)

    state = WatcherState(watcher_id)
    saved = state.read()

    state.write({
        'watcher_id': watcher_id,
        'mode': mode,
        'started_at': saved.get('started_at', now_iso()),
        'last_poll_at': now_iso(),
        'monitor_pid': os.getpid(),
        'workflow_name': workflow_name,
        'run_id': run_id,
        'profile': profile,
        'region': region,
        'poll_interval_seconds': poll_interval,
        'surface_id': surface_ref,
        'workspace_ref': workspace_ref,
        'tmux_pane': tmux_pane,
        'max_runtime_hours': max_runtime_hours,
        'launch_command': restart_cmd,
    })

    print(
        f"[Glue Workflow Watcher {_ver()}] ID: {watcher_id} | Mode: {mode} | "
        f"Workflow: {workflow_name} | Run: {run_id} | Poll: {poll_interval}s",
        file=sys.stderr, flush=True,
    )
    print(f"Re-launch command:\n  {restart_cmd}", file=sys.stderr, flush=True)
    print(f"State file: {state.path}", file=sys.stderr, flush=True)

    bridge: Optional[CmuxBridge | TmuxBridge] = None

    if mode == 'cmux-keystrokes':
        assert surface_ref is not None
        bridge = CmuxBridge(
            surface_id=surface_ref,
            workspace_ref=workspace_ref,
            enable_notify=args.cmux_notify,
            enable_status=args.cmux_status,
        )
        if not bridge.send_to_claude(
            f"[Glue Workflow Watcher {_ver()}] Started. ID: {watcher_id} | "
            f"Workflow: {workflow_name} | Run: {run_id[:12]}"
        ):
            print(
                f"Surface {surface_ref} unreachable. Get fresh refs via `cmux identify --json` and re-launch:\n"
                f"  {restart_cmd}",
                file=sys.stderr, flush=True,
            )
            sys.exit(1)

    elif mode == 'tmux-keystrokes':
        assert tmux_pane is not None
        bridge = TmuxBridge(tmux_pane=tmux_pane)
        if not bridge.send_to_claude(
            f"[Glue Workflow Watcher {_ver()}] Started. ID: {watcher_id} | "
            f"Workflow: {workflow_name} | Run: {run_id[:12]}"
        ):
            print(
                f"tmux pane {tmux_pane} unreachable. Check pane ID and re-launch:\n"
                f"  {restart_cmd}",
                file=sys.stderr, flush=True,
            )
            sys.exit(1)

    try:
        _poll_loop(
            args=args,
            mode=mode,
            watcher_id=watcher_id,
            workflow_name=workflow_name,
            run_id=run_id,
            profile=profile,
            region=region,
            poll_interval=poll_interval,
            max_runtime_hours=max_runtime_hours,
            restart_cmd=restart_cmd,
            bridge=bridge,
            state=state,
            initial_previous_state=saved.get('current_state'),
            initial_prev_node_states=saved.get('node_states'),
        )
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[{ts()}] FATAL: {exc}\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args):
    if args.workflow_name and args.run_id:
        if not args.profile:
            print("Error: --profile is required for live API check.", file=sys.stderr)
            sys.exit(1)
        try:
            client = GlueWorkflowClient(profile=args.profile, region=args.region)
            run = client.get_workflow_run(args.workflow_name, args.run_id)
        except Exception as e:
            print(f"Error fetching workflow status: {e}", file=sys.stderr)
            sys.exit(1)
        current_state = run.get('Status', 'UNKNOWN')
        started_on = run.get('StartedOn')
        stats = run.get('Statistics') or {}
        nodes = _extract_nodes(run)
        print(f"Workflow:   {args.workflow_name}")
        print(f"Run ID:     {args.run_id}")
        print(f"State:      {current_state}")
        if started_on:
            print(f"Started:    {started_on.isoformat() if hasattr(started_on, 'isoformat') else started_on}")
        if stats:
            total = stats.get('TotalActions', 0)
            running_count = stats.get('RunningActions', 0)
            succeeded = stats.get('SucceededActions', 0)
            failed = stats.get('FailedActions', 0) + stats.get('ErroredActions', 0)
            print(f"Actions:    {total} total | {running_count} running | {succeeded} ok | {failed} fail")
        if nodes:
            print(f"\nNodes ({len(nodes)}):")
            print(_format_nodes_table(nodes))
        return

    if args.watcher_id:
        state = WatcherState(args.watcher_id)
        data = state.read()
        if not data:
            print(f"No state file found for watcher-id: {args.watcher_id}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(data, indent=2))
        return

    all_states = WatcherState.list_all()
    if not all_states:
        print("No state files found.")
        print(f"State directory: {STATE_DIR}")
        return

    print(f"{'WATCHER ID':<12} {'MODE':<22} {'WORKFLOW':<28} {'STATE':<12} {'LAST POLL':<22} {'PID'}")
    print("-" * 110)
    for data in all_states:
        wid = data.get('watcher_id', '?')[:11]
        mode = data.get('mode', '?')[:21]
        wf = data.get('workflow_name', '?')[:27]
        current_state = data.get('current_state', 'watching')[:11]
        last_poll = data.get('last_poll_at', 'never')[:21]
        pid = data.get('monitor_pid')
        pid_str = f"{pid} ({'alive' if _pid_alive(pid) else 'dead'})" if pid else "none"
        print(f"{wid:<12} {mode:<22} {wf:<28} {current_state:<12} {last_poll:<22} {pid_str}")
        launch = data.get('launch_command', '')
        if launch:
            print(f"  launch: {launch[:90]}")


# ---------------------------------------------------------------------------
# Subcommand: stop
# ---------------------------------------------------------------------------

def cmd_stop(args):
    if args.list:
        all_states = WatcherState.list_all()
        if not all_states:
            print("No tracked watchers found.")
            return
        alive = [d for d in all_states if _pid_alive(d.get('monitor_pid'))]
        if not alive:
            print("No live watchers found.")
            return
        print("Live watchers:")
        for d in alive:
            print(f"  {d.get('watcher_id', '?')}  pid={d.get('monitor_pid', '?')}  workflow={d.get('workflow_name', '?')}")
        return

    if not args.watcher_id:
        print("Error: --watcher-id is required (or use --list).", file=sys.stderr)
        sys.exit(1)

    state = WatcherState(args.watcher_id)
    data = state.read()
    if not data:
        print(f"No state file found for watcher-id: {args.watcher_id}", file=sys.stderr)
        sys.exit(1)

    pid = data.get('monitor_pid')
    if not pid:
        print("No monitor PID in state file.", file=sys.stderr)
        sys.exit(1)

    if not _pid_alive(pid):
        print(f"PID {pid} is not running (already stopped).")
        return

    os.kill(int(pid), signal.SIGTERM)
    print(f"Sent SIGTERM to PID {pid}. Watcher {args.watcher_id} stopping.")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='AWS Glue Workflow Watcher — monitors workflow execution for state changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch workflow (long-poll-with-exit, background)
  watch_glue_workflow.py watch --workflow-name my-workflow --run-id wr_abc123 --profile my-profile

  # Watch workflow in cmux
  watch_glue_workflow.py watch --workflow-name my-workflow --run-id wr_abc123 --profile my-profile \\
      --mode cmux-keystrokes --cmux-surface surface:80

  # Watch workflow via tmux
  watch_glue_workflow.py watch --workflow-name my-workflow --run-id wr_abc123 --profile my-profile \\
      --mode tmux-keystrokes --tmux-pane main:0.0

  # Check watcher state
  watch_glue_workflow.py status --list

  # One-shot live status check
  watch_glue_workflow.py status --workflow-name my-workflow --run-id wr_abc123 --profile my-profile

  # Stop a watcher
  watch_glue_workflow.py stop --watcher-id a1b2c3d4
        """,
    )

    sub = parser.add_subparsers(dest='command', required=True)

    # ---- watch ----
    p_watch = sub.add_parser('watch', help='Start watching a Glue workflow run')
    p_watch.add_argument('--workflow-name', required=True, help='Glue workflow name')
    p_watch.add_argument('--run-id', required=True, help='Glue workflow run ID (e.g. wr_abc123)')
    p_watch.add_argument('--profile', required=True, help='AWS credentials profile')
    p_watch.add_argument('--region', help='AWS region (uses profile default if not set)')
    p_watch.add_argument(
        '--mode', choices=['long-poll-with-exit', 'cmux-keystrokes', 'tmux-keystrokes'],
        default='long-poll-with-exit',
        help='Delivery mode (default: long-poll-with-exit)',
    )
    p_watch.add_argument(
        '--poll-interval-seconds', type=int, default=300, metavar='SECONDS',
        help='Seconds between polls (default: 300, min: 60, max: 3600)',
    )
    p_watch.add_argument(
        '--watcher-id', default='',
        help='Watcher state ID (auto-generated on first run; pass on resume to reuse state)',
    )
    p_watch.add_argument(
        '--max-runtime-hours', type=int, default=24,
        help='Maximum runtime in hours before auto-exit (default: 24)',
    )

    cmux_group = p_watch.add_argument_group('cmux flags (only valid with --mode cmux-keystrokes)')
    cmux_group.add_argument(
        '--cmux-surface', metavar='SURFACE_REF',
        help='cmux surface ref of the CC session. Get from: cmux identify --json -> caller.surface_ref',
    )
    cmux_group.add_argument(
        '--cmux-workspace', metavar='WORKSPACE_REF',
        help='cmux workspace ref (auto-detected if omitted)',
    )
    cmux_group.add_argument('--cmux-notify', action='store_true',
                            help='Enable desktop notifications via cmux on state changes')
    cmux_group.add_argument('--cmux-status', action='store_true',
                            help='Enable cmux sidebar status badge')

    tmux_group = p_watch.add_argument_group('tmux flags (only valid with --mode tmux-keystrokes)')
    tmux_group.add_argument('--tmux-pane', metavar='PANE_ID',
                            help='tmux pane target (e.g. main:0.0). Required for tmux mode.')

    # ---- status ----
    p_status = sub.add_parser('status', help='Show watcher state or one-shot live check')
    p_status.add_argument('--watcher-id', default='', help='Show state for a specific watcher ID')
    p_status.add_argument('--list', action='store_true', help='List all tracked watchers')
    p_status.add_argument('--workflow-name', help='Glue workflow name (for live API check)')
    p_status.add_argument('--run-id', help='Glue workflow run ID (for live API check)')
    p_status.add_argument('--profile', help='AWS profile (required for live API check)')
    p_status.add_argument('--region', help='AWS region')

    # ---- stop ----
    p_stop = sub.add_parser('stop', help='Stop a running watcher')
    p_stop.add_argument('--watcher-id', default='', help='Watcher ID to stop')
    p_stop.add_argument('--list', action='store_true', help='List live watchers without stopping')

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if _VERSION == 'unknown':
        print(
            "[Glue Workflow Watcher] WARNING: Running from source (version unknown). "
            "Version drift checks disabled.",
            file=sys.stderr, flush=True,
        )

    if args.command == 'watch':
        cmd_watch(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'stop':
        cmd_stop(args)


if __name__ == '__main__':
    main()
