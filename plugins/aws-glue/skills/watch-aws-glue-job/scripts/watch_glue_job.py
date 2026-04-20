#!/usr/bin/env python3
"""
AWS Glue Job Watcher

Monitor long-running AWS Glue jobs with background state-change notifications.

Three delivery modes:
  long-poll-with-exit    Poll Glue API until state changes, print JSON, exit 0.
                         Run in background. Re-launch after processing output.
  cmux-keystrokes        Poll and send state changes as keystrokes to a CC surface.
                         Runs indefinitely until killed.
  tmux-keystrokes        Same as cmux-keystrokes but uses tmux send-keys.

State persisted at: ~/.claude/plugin-data/aws-glue/watch-aws-glue-job/
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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TERMINAL_STATES = {'SUCCEEDED', 'FAILED', 'STOPPED', 'ERROR', 'TIMEOUT'}
STATE_DIR = Path.home() / '.claude' / 'plugin-data' / 'aws-glue' / 'watch-aws-glue-job'
_HEARTBEAT_INTERVAL = 300
_VERSION_CHECK_INTERVAL = 3600


def _version_from_path(path: str) -> str:
    m = _re.search(r'/(\d+\.\d+\.\d+)/skills/', path)
    return m.group(1) if m else 'unknown'


_VERSION = _version_from_path(__file__)
_ver = lambda: f"v{_VERSION}" if _VERSION != 'unknown' else "(unknown version)"
_WATCHER_NAME = "Glue Job Watcher"

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
            f"[{ts()}] [{_WATCHER_NAME} {_ver()}] WARNING: Running version {_VERSION} but "
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


def _fmt_count(n: float) -> str:
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


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
            f"[{_WATCHER_NAME}] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)
    except ProcessLookupError:
        return
    except PermissionError:
        print(
            f"[{_WATCHER_NAME}] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
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
        print(f"[{_WATCHER_NAME}] FATAL: failed to write PID file: {e}", file=sys.stderr, flush=True)
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
    """Sleep with jitter on throttle, then return doubled poll interval (capped at 3600s)."""
    sleep_time = 3.5 * 60 + random.uniform(-30, 30)
    print(
        f"[{ts()}] Throttle cool-down: sleeping {sleep_time:.0f}s then doubling interval.",
        file=sys.stderr, flush=True,
    )
    time.sleep(sleep_time)
    return min(poll_interval * 2, 3600)


# ---------------------------------------------------------------------------
# GlueJobClient
# ---------------------------------------------------------------------------

class GlueJobClient:
    def __init__(self, profile: str, region: Optional[str] = None):
        self.profile = profile
        self.region = region

    def _client(self):
        import boto3
        kwargs = {'profile_name': self.profile}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.Session(**kwargs).client('glue')

    def get_job_run(self, job_name: str, run_id: str) -> dict:
        client = self._client()
        try:
            return client.get_job_run(JobName=job_name, RunId=run_id)['JobRun']
        except client.exceptions.EntityNotFoundException:
            paginator = client.get_paginator('get_job_runs')
            for page in paginator.paginate(JobName=job_name):
                for run in page['JobRuns']:
                    if run['Id'] == run_id:
                        return run
            raise


# ---------------------------------------------------------------------------
# CloudWatchMetrics
# ---------------------------------------------------------------------------

class CloudWatchMetrics:
    _QUERIES = [
        ('cpu_all',  'glue.ALL.system.cpuSystemLoad',
         [{'Name': 'Type', 'Value': 'gauge'}, {'Name': 'groupName', 'Value': 'WorkerMetrics'}],
         'Average'),
        ('cpu_driver', 'glue.driver.system.cpuSystemLoad',
         [{'Name': 'Type', 'Value': 'gauge'}, {'Name': 'groupName', 'Value': 'WorkerMetrics'}],
         'Average'),
        ('heap',     'glue.ALL.jvm.heap.usage',
         [{'Name': 'Type', 'Value': 'gauge'}, {'Name': 'groupName', 'Value': 'WorkerMetrics'}],
         'Average'),
        ('rec_read', 'glue.driver.aggregate.recordsRead',
         [{'Name': 'Type', 'Value': 'count'}, {'Name': 'groupName', 'Value': 'JobMetrics'}],
         'Sum'),
        ('rec_write', 'glue.driver.aggregate.recordsWritten',
         [{'Name': 'Type', 'Value': 'count'}, {'Name': 'groupName', 'Value': 'JobMetrics'}],
         'Sum'),
        ('executors', 'glue.driver.ExecutorAllocationManager.executors.numberAllExecutors',
         [{'Name': 'Type', 'Value': 'gauge'}, {'Name': 'groupName', 'Value': 'JobMetrics'}],
         'Average'),
    ]

    def __init__(self, profile: str, region: Optional[str] = None):
        self.profile = profile
        self.region = region
        self._no_data_warned = False

    def _client(self):
        import boto3
        kwargs = {'profile_name': self.profile}
        if self.region:
            kwargs['region_name'] = self.region
        return boto3.Session(**kwargs).client('cloudwatch')

    def fetch(self, job_name: str, run_id: str) -> dict:
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(minutes=10)
            queries = []
            for qid, metric_name, extra_dims, stat in self._QUERIES:
                queries.append({
                    'Id': qid,
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'Glue',
                            'MetricName': metric_name,
                            'Dimensions': [
                                {'Name': 'JobName',  'Value': job_name},
                                {'Name': 'JobRunId', 'Value': run_id},
                            ] + extra_dims,
                        },
                        'Period': 300,
                        'Stat': stat,
                    },
                    'ReturnData': True,
                })
            response = self._client().get_metric_data(
                MetricDataQueries=queries,
                StartTime=start_time,
                EndTime=end_time,
            )
            results = {}
            for result in response.get('MetricDataResults', []):
                values = result.get('Values', [])
                if values:
                    results[result['Id']] = values[0]
            if not results and not self._no_data_warned:
                self._no_data_warned = True
                print(
                    f"[{ts()}] INFO: No CloudWatch metrics yet "
                    f"(may appear after ~2 min; use --no-cloudwatch-metrics to suppress)",
                    flush=True,
                )
            return results
        except Exception as e:
            if not self._no_data_warned:
                self._no_data_warned = True
                print(f"[{ts()}] WARN: CloudWatch metrics unavailable: {e}", flush=True)
            return {}

    @staticmethod
    def format(metrics: dict, num_workers: int = 0) -> str:
        if not metrics:
            return ''
        parts = []
        cpu_all = metrics.get('cpu_all')
        cpu_driver = metrics.get('cpu_driver')
        if cpu_all is not None or cpu_driver is not None:
            cpu_parts = []
            if cpu_all    is not None: cpu_parts.append(f"workers: {int(cpu_all * 100)}%")
            if cpu_driver is not None: cpu_parts.append(f"driver: {int(cpu_driver * 100)}%")
            parts.append(f"cpu: {' / '.join(cpu_parts)}")
        heap = metrics.get('heap')
        if heap is not None:
            pct = int(heap * 100)
            warn = ' ⚠' if pct >= 85 else ''
            parts.append(f"heap: {pct}%{warn}")
        rec_read  = metrics.get('rec_read')
        rec_write = metrics.get('rec_write')
        if rec_read is not None or rec_write is not None:
            rec_parts = []
            if rec_read  is not None: rec_parts.append(f"{_fmt_count(rec_read)} in")
            if rec_write is not None: rec_parts.append(f"{_fmt_count(rec_write)} out")
            parts.append(f"rec: {' / '.join(rec_parts)}")
        executors = metrics.get('executors')
        if executors is not None:
            exec_str = str(int(executors))
            if num_workers:
                exec_str += f"/{num_workers}"
            parts.append(f"exec: {exec_str}")
        return ' | '.join(parts)


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
        pass  # no-op: tmux has no sidebar status

    def clear_status(self, *_a, **_kw) -> None:
        pass  # no-op


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
    job_name: str,
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
    no_cloudwatch_metrics: bool = False,
    tmux_pane: Optional[str] = None,
) -> str:
    parts = [f"python3 {shlex.quote(script_path)}", "watch"]
    parts.append(f"--job-name {shlex.quote(job_name)}")
    parts.append(f"--run-id {shlex.quote(run_id)}")
    parts.append(f"--profile {shlex.quote(profile)}")
    if region:
        parts.append(f"--region {shlex.quote(region)}")
    parts.append(f"--mode {shlex.quote(mode)}")
    parts.append(f"--poll-interval-seconds {poll_interval}")
    parts.append(f"--watcher-id {shlex.quote(watcher_id)}")
    parts.append(f"--max-runtime-hours {max_runtime_hours}")
    if no_cloudwatch_metrics:
        parts.append("--no-cloudwatch-metrics")
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


def _print_startup_summary(job_name: str, run_id: str, run: dict):
    state = run.get('JobRunState', 'UNKNOWN')
    started_on = run.get('StartedOn')
    exec_time = run.get('ExecutionTime', 0)
    worker_type = run.get('WorkerType', '')
    num_workers = run.get('NumberOfWorkers', '')
    glue_version = run.get('GlueVersion', '')
    log_group = run.get('LogGroupName', '/aws-glue/jobs/output')
    arguments = run.get('Arguments', {})
    attempt = run.get('Attempt', 0)

    print('=' * 60, flush=True)
    print(f"Job:        {job_name}", flush=True)
    print(f"Run:        {run_id}", flush=True)
    print(f"State:      {state}", flush=True)

    workers_str = ''
    if num_workers and worker_type:
        workers_str = f"{num_workers}x {worker_type}"
    elif worker_type:
        workers_str = worker_type
    if glue_version:
        workers_str += f"  (Glue {glue_version})" if workers_str else f"Glue {glue_version}"
    if workers_str:
        print(f"Workers:    {workers_str}", flush=True)

    if started_on:
        started_str = started_on.strftime('%Y-%m-%d %H:%M:%S UTC') if hasattr(started_on, 'strftime') else str(started_on)
        ago = f"  ({format_elapsed(exec_time)} ago)" if exec_time else ''
        print(f"Started:    {started_str}{ago}", flush=True)

    if attempt:
        print(f"Attempt:    {attempt}", flush=True)

    print(f"Log group:  {log_group}", flush=True)

    if arguments:
        print("Arguments:", flush=True)
        for k, v in sorted(arguments.items()):
            print(f"  {k} = {v}", flush=True)

    print('=' * 60, flush=True)
    print(flush=True)


# ---------------------------------------------------------------------------
# Core polling loop (shared by all modes)
# ---------------------------------------------------------------------------

def _poll_loop(
    args,
    mode: str,
    watcher_id: str,
    job_name: str,
    run_id: str,
    profile: str,
    region: Optional[str],
    poll_interval: int,
    max_runtime_hours: int,
    restart_cmd: str,
    bridge: Optional[CmuxBridge | TmuxBridge],
    state: WatcherState,
    cw_metrics: Optional[CloudWatchMetrics],
    initial_previous_state: Optional[str] = None,
):
    client = GlueJobClient(profile=profile, region=region)
    status_key = f"glue-{watcher_id[:6]}"

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
    num_workers = 0
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
                    f"[{_WATCHER_NAME} {_ver()}] Max runtime ({max_runtime_hours}h) reached. "
                    f"Last known state: {previous_state}. Re-launch: {restart_cmd}"
                )
                if bridge:
                    bridge.send_to_claude(msg)
                    bridge.clear_status(status_key)
                else:
                    print(msg, file=sys.stderr, flush=True)
                break

            try:
                run = client.get_job_run(job_name, run_id)
                if consecutive_cred_errors > 0 and cred_notified:
                    recovery_msg = f"[{_WATCHER_NAME} {_ver()}] AWS credentials recovered — resuming."
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
                            f"[{_WATCHER_NAME} {_ver()}] {consecutive_cred_errors} consecutive "
                            f"AWS credential errors. Please re-authenticate your AWS credentials. "
                            f"Watcher will auto-recover when credentials are refreshed."
                        )
                        if bridge:
                            bridge.send_to_claude(msg)
                            bridge.notify(_WATCHER_NAME, "Credentials expired")
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
                        os.path.abspath(__file__), mode, job_name, run_id,
                        watcher_id, profile, region, poll_interval,
                        surface_ref=getattr(args, 'cmux_surface', None),
                        workspace_ref=getattr(args, 'cmux_workspace', None),
                        cmux_notify=getattr(args, 'cmux_notify', False),
                        cmux_status=getattr(args, 'cmux_status', False),
                        max_runtime_hours=max_runtime_hours,
                        no_cloudwatch_metrics=getattr(args, 'no_cloudwatch_metrics', False),
                        tmux_pane=getattr(args, 'tmux_pane', None),
                    )
                    state.update(poll_interval_seconds=poll_interval, launch_command=restart_cmd)
                    continue

                consecutive_poll_errors += 1
                print(f"[{ts()}] WARN: Poll error #{consecutive_poll_errors}: {e}", file=sys.stderr, flush=True)
                if bridge and consecutive_poll_errors >= 3:
                    bridge.send_to_claude(
                        f"[{_WATCHER_NAME} {_ver()}] {consecutive_poll_errors} consecutive poll errors. "
                        f"Last: {str(e)[:80]}. Still watching."
                    )
                    consecutive_poll_errors = 0
                time.sleep(poll_interval)
                continue

            current_state = run.get('JobRunState', 'UNKNOWN')
            exec_time = run.get('ExecutionTime', 0)
            error_msg = run.get('ErrorMessage', '')
            dpu_seconds = run.get('DPUSeconds', 0)

            if not printed_summary:
                num_workers = run.get('NumberOfWorkers', 0)
                _print_startup_summary(job_name, run_id, run)
                if cw_metrics:
                    print(
                        "Poll columns: state | exec time | DPU-s (if reported)"
                        " | cpu: workers avg / driver | heap: all workers"
                        " | rec: cumulative read / written | exec: active/total",
                        flush=True,
                    )
                    print(flush=True)
                printed_summary = True

            cw_str = ''
            if cw_metrics:
                cw_data = cw_metrics.fetch(job_name, run_id)
                cw_str = CloudWatchMetrics.format(cw_data, num_workers)
                if cw_str:
                    cw_str = ' | ' + cw_str

            dpu_str = f" | DPU-s: {int(dpu_seconds):,}" if dpu_seconds else ""
            print(f"[{ts()}] {current_state} | exec: {format_elapsed(exec_time)}{dpu_str}{cw_str}", flush=True)

            state.update(
                current_state=current_state,
                previous_state=previous_state,
                last_poll_at=now_iso(),
                execution_time_seconds=exec_time,
                error_message=error_msg or None,
            )

            if current_state != previous_state:
                elapsed_fmt = format_elapsed(exec_time) if exec_time else format_elapsed(elapsed_total)

                if current_state in TERMINAL_STATES:
                    prefix = f"[{_WATCHER_NAME} {_ver()}]"
                    if current_state == 'SUCCEEDED':
                        dpu_info = f" DPU-seconds: {int(dpu_seconds)}." if dpu_seconds else ""
                        notification = (
                            f"{prefix} {job_name} ({run_id}) | "
                            f"{previous_state or '?'} -> {current_state} ({ts()}). "
                            f"Elapsed: {elapsed_fmt}.{dpu_info}"
                        )
                    else:
                        error_info = f" Error: {error_msg}" if error_msg else ""
                        notification = (
                            f"{prefix} {job_name} ({run_id}) | "
                            f"{previous_state or '?'} -> {current_state} ({ts()}). "
                            f"Elapsed: {elapsed_fmt}.{error_info}"
                        )

                    print(f"[{ts()}] STATE CHANGE: {previous_state} -> {current_state} after {elapsed_fmt}", flush=True)

                    if mode == 'long-poll-with-exit':
                        output = {
                            'events': [{
                                'job_name': job_name,
                                'run_id': run_id,
                                'event_type': 'state_changed',
                                'previous_state': previous_state,
                                'new_state': current_state,
                                'summary': f"Glue job '{job_name}' (run {run_id}) state changed: {previous_state} -> {current_state}. Elapsed: {elapsed_fmt}.",
                                'formatted': notification,
                                'execution_time_seconds': exec_time,
                                'dpu_seconds': dpu_seconds,
                                'error_message': error_msg,
                            }],
                            'watcher_id': watcher_id,
                            'instruction': f"Re-launch the watcher FIRST, then process events.\n{restart_cmd}",
                        }
                        _remove_pid_file(watcher_id)
                        print(json.dumps(output, indent=2))
                        sys.exit(0)
                    else:
                        if bridge:
                            bridge.set_status(status_key, current_state,
                                              color='#196F3D' if current_state == 'SUCCEEDED' else '#B71C1C')
                            bridge.send_to_claude(notification)
                            bridge.notify(f"Glue: {job_name}", notification)
                            bridge.clear_status(status_key)
                        return

                else:
                    prev_label = f"{previous_state} -> " if previous_state else ""
                    notification = (
                        f"[{_WATCHER_NAME} {_ver()}] {job_name} ({run_id}) | "
                        f"{prev_label}{current_state} ({ts()})"
                    )
                    print(f"[{ts()}] STATE CHANGE: {prev_label}{current_state}. Elapsed: {elapsed_fmt}", flush=True)

                    if mode == 'long-poll-with-exit':
                        output = {
                            'events': [{
                                'job_name': job_name,
                                'run_id': run_id,
                                'event_type': 'state_changed',
                                'previous_state': previous_state,
                                'new_state': current_state,
                                'summary': f"Glue job '{job_name}' (run {run_id}) state changed: {prev_label}{current_state}. Elapsed: {elapsed_fmt}.",
                                'formatted': notification,
                                'execution_time_seconds': exec_time,
                                'dpu_seconds': dpu_seconds,
                                'error_message': error_msg,
                            }],
                            'watcher_id': watcher_id,
                            'instruction': f"Re-launch the watcher FIRST, then process events.\n{restart_cmd}",
                        }
                        _remove_pid_file(watcher_id)
                        print(json.dumps(output, indent=2))
                        sys.exit(0)
                    else:
                        if bridge:
                            if previous_state is not None:
                                bridge.send_to_claude(notification)
                            bridge.set_status(status_key, current_state)
                            bridge.notify(f"Glue: {job_name}", notification)

                previous_state = current_state

            if not running[0]:
                break

            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{ts()}] Watching '{job_name}' -- state: {current_state} (poll_interval={poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now
            if now - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now

        sig = received_signal[0] or 'timeout'
        print(
            f"[{_WATCHER_NAME} {_ver()}] Exiting ({sig}).\n"
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

    job_name = args.job_name
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
        script_path, mode, job_name, run_id, watcher_id, profile, region, poll_interval,
        surface_ref=surface_ref,
        workspace_ref=workspace_ref,
        cmux_notify=getattr(args, 'cmux_notify', False),
        cmux_status=getattr(args, 'cmux_status', False),
        max_runtime_hours=max_runtime_hours,
        no_cloudwatch_metrics=args.no_cloudwatch_metrics,
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
        'job_name': job_name,
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

    cw_metrics = None if args.no_cloudwatch_metrics else CloudWatchMetrics(profile=profile, region=region)

    print(
        f"[{_WATCHER_NAME} {_ver()}] ID: {watcher_id} | Mode: {mode} | "
        f"Job: {job_name} | Run: {run_id} | Poll: {poll_interval}s",
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
        if not bridge.send_to_claude(f"[{_WATCHER_NAME} {_ver()}] Started. ID: {watcher_id} | Job: {job_name} | Run: {run_id[:12]}"):
            print(
                f"Surface {surface_ref} unreachable. Get fresh refs via `cmux identify --json` and re-launch:\n"
                f"  {restart_cmd}",
                file=sys.stderr, flush=True,
            )
            sys.exit(1)

    elif mode == 'tmux-keystrokes':
        assert tmux_pane is not None
        bridge = TmuxBridge(tmux_pane=tmux_pane)
        if not bridge.send_to_claude(f"[{_WATCHER_NAME} {_ver()}] Started. ID: {watcher_id} | Job: {job_name} | Run: {run_id[:12]}"):
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
            job_name=job_name,
            run_id=run_id,
            profile=profile,
            region=region,
            poll_interval=poll_interval,
            max_runtime_hours=max_runtime_hours,
            restart_cmd=restart_cmd,
            bridge=bridge,
            state=state,
            cw_metrics=cw_metrics,
            initial_previous_state=saved.get('current_state'),
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
    # One-shot live API check
    if args.job_name and args.run_id:
        if not args.profile:
            print("Error: --profile is required for live API check.", file=sys.stderr)
            sys.exit(1)
        try:
            client = GlueJobClient(profile=args.profile, region=args.region)
            run = client.get_job_run(args.job_name, args.run_id)
        except Exception as e:
            print(f"Error fetching job status: {e}", file=sys.stderr)
            sys.exit(1)
        current_state = run.get('JobRunState', 'UNKNOWN')
        exec_time = run.get('ExecutionTime', 0)
        error_msg = run.get('ErrorMessage', '')
        dpu_seconds = run.get('DPUSeconds', 0)
        started_on = run.get('StartedOn')
        print(f"Job:        {args.job_name}")
        print(f"Run ID:     {args.run_id}")
        print(f"State:      {current_state}")
        print(f"Elapsed:    {format_elapsed(exec_time) if exec_time else 'N/A'}")
        if dpu_seconds:
            print(f"DPU-secs:   {int(dpu_seconds):,}")
        if error_msg:
            print(f"Error:      {error_msg}")
        if started_on:
            print(f"Started:    {started_on.isoformat() if hasattr(started_on, 'isoformat') else started_on}")
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

    print(f"{'WATCHER ID':<12} {'MODE':<22} {'JOB':<28} {'STATE':<12} {'LAST POLL':<22} {'PID'}")
    print("-" * 110)
    for data in all_states:
        wid = data.get('watcher_id', '?')[:11]
        mode = data.get('mode', '?')[:21]
        job = data.get('job_name', '?')[:27]
        current_state = data.get('current_state', 'watching')[:11]
        last_poll = data.get('last_poll_at', 'never')[:21]
        pid = data.get('monitor_pid')
        pid_str = f"{pid} ({'alive' if _pid_alive(pid) else 'dead'})" if pid else "none"
        print(f"{wid:<12} {mode:<22} {job:<28} {current_state:<12} {last_poll:<22} {pid_str}")
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
            print(f"  {d.get('watcher_id', '?')}  pid={d.get('monitor_pid', '?')}  job={d.get('job_name', '?')}")
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
        description='AWS Glue Job Watcher — monitors job execution for state changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch job (long-poll-with-exit, background)
  watch_glue_job.py watch --job-name my-etl --run-id jr_abc123 --profile my-profile

  # Watch job in cmux split
  watch_glue_job.py watch --job-name my-etl --run-id jr_abc123 --profile my-profile \\
      --mode cmux-keystrokes --cmux-surface surface:80

  # Watch job via tmux
  watch_glue_job.py watch --job-name my-etl --run-id jr_abc123 --profile my-profile \\
      --mode tmux-keystrokes --tmux-pane main:0.0

  # Check watcher state
  watch_glue_job.py status --list

  # One-shot live status check
  watch_glue_job.py status --job-name my-etl --run-id jr_abc123 --profile my-profile

  # Stop a watcher
  watch_glue_job.py stop --watcher-id a1b2c3d4
        """,
    )

    sub = parser.add_subparsers(dest='command', required=True)

    # ---- watch ----
    p_watch = sub.add_parser('watch', help='Start watching a Glue job run')
    p_watch.add_argument('--job-name', required=True, help='Glue job name')
    p_watch.add_argument('--run-id', required=True, help='Glue job run ID (e.g. jr_abc123)')
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
    p_watch.add_argument(
        '--no-cloudwatch-metrics', action='store_true',
        help='Disable CloudWatch metrics in poll output (default: enabled). '
             'Requires Glue 2.0+ Spark jobs with CW metrics enabled.',
    )

    cmux_group = p_watch.add_argument_group('cmux flags (only valid with --mode cmux-keystrokes)')
    cmux_group.add_argument(
        '--cmux-surface', metavar='SURFACE_REF',
        help='cmux surface ref of the CC session (required for cmux mode). '
             'Get from: cmux identify --json -> caller.surface_ref',
    )
    cmux_group.add_argument(
        '--cmux-workspace', metavar='WORKSPACE_REF',
        help='cmux workspace ref (auto-detected if omitted)',
    )
    cmux_group.add_argument(
        '--cmux-notify', action='store_true',
        help='Enable desktop notifications via cmux on state changes',
    )
    cmux_group.add_argument(
        '--cmux-status', action='store_true',
        help='Enable cmux sidebar status badge',
    )
    tmux_group = p_watch.add_argument_group('tmux flags (only valid with --mode tmux-keystrokes)')
    tmux_group.add_argument(
        '--tmux-pane', metavar='PANE_ID',
        help='tmux pane target (e.g. main:0.0). Required for tmux mode.',
    )

    # ---- status ----
    p_status = sub.add_parser('status', help='Show watcher state or one-shot live check')
    p_status.add_argument('--watcher-id', default='', help='Show state for a specific watcher ID')
    p_status.add_argument('--list', action='store_true', help='List all tracked watchers')
    p_status.add_argument('--job-name', help='Glue job name (for live API check)')
    p_status.add_argument('--run-id', help='Glue run ID (for live API check)')
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
            f"[{_WATCHER_NAME}] WARNING: Running from source (version unknown). "
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
