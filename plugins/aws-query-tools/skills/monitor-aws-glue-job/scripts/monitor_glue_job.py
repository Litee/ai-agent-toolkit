#!/usr/bin/env python3
"""
AWS Glue Job Monitor

Monitor long-running AWS Glue jobs with background state-change notifications.
With cmux, sends keystrokes to the Claude Code terminal on state changes.
Without cmux, prints current status for use with team agent polling.

Usage:
    # Background monitoring in a visible cmux split (recommended)
    glue_job.py watch-job --job-name my-etl --run-id jr_abc123 \\
        --profile my-aws-profile --surface-id surface:1

    # Check current status
    glue_job.py check-status --job-name my-etl --run-id jr_abc123 --profile my-aws-profile

    # List all tracked jobs
    glue_job.py check-status --list

    # Stop a running monitor
    glue_job.py stop-monitor --job-name my-etl --run-id jr_abc123
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# Glue terminal states
TERMINAL_STATES = {'SUCCEEDED', 'FAILED', 'STOPPED', 'ERROR', 'TIMEOUT'}


def _fmt_count(n: float) -> str:
    """Format a large integer count for display (1.4M, 823K, etc.)."""
    n = int(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)

# State file directory
STATE_DIR = Path.home() / '.claude' / 'plugin-data' / 'aws-query-tools' / 'monitor-aws-glue-job'


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def ts() -> str:
    """Short UTC timestamp for log lines."""
    return datetime.now(timezone.utc).strftime('%H:%M:%SZ')


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
# GlueJobClient
# ---------------------------------------------------------------------------

class GlueJobClient:
    """Thin boto3 wrapper for Glue job status queries."""

    def __init__(self, profile: str, region: Optional[str] = None):
        self.profile = profile
        self.region = region

    def _client(self):
        import boto3
        kwargs = {'profile_name': self.profile}
        if self.region:
            kwargs['region_name'] = self.region
        session = boto3.Session(**kwargs)
        return session.client('glue')

    def get_job_run(self, job_name: str, run_id: str) -> dict:
        """Fetch current job run details. Recreates session each call for credential refresh."""
        client = self._client()
        try:
            return client.get_job_run(JobName=job_name, RunId=run_id)['JobRun']
        except client.exceptions.EntityNotFoundException:
            # GetJobRun can return EntityNotFoundException for runs on jobs that were
            # deleted and recreated with the same name. GetJobRuns is not affected.
            runs = client.get_job_runs(JobName=job_name)['JobRuns']
            for run in runs:
                if run['Id'] == run_id:
                    return run
            raise  # truly not found


# ---------------------------------------------------------------------------
# CloudWatchMetrics
# ---------------------------------------------------------------------------

class CloudWatchMetrics:
    """Fetches Glue job CloudWatch metrics in a single get_metric_data call.

    Metrics are published with ~1-2 min lag. We look back 10 min to ensure
    we always get the latest available data point despite the lag.

    All metrics require Glue 2.0+ Spark jobs with CloudWatch metrics enabled.
    Returns an empty dict silently if metrics are unavailable (old Glue version,
    metrics disabled, job just started and no data yet).
    """

    # (query_id, metric_name, extra_dimensions, statistic)
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
        """Returns dict of metric values (most recent data point each), or {} on failure."""
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
                                {'Name': 'JobName',   'Value': job_name},
                                {'Name': 'JobRunId',  'Value': run_id},
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
                    results[result['Id']] = values[0]  # most recent data point

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
        """Format fetched metrics into a compact display string."""
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
# GlueMonitorState
# ---------------------------------------------------------------------------

class GlueMonitorState:
    """Manages persistent state file for a Glue job monitor."""

    def __init__(self, job_name: str, run_id: str):
        self.job_name = job_name
        self.run_id = run_id
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        safe_job = job_name.replace('/', '_').replace(' ', '_')
        safe_run = run_id.replace('/', '_')
        self.path = STATE_DIR / f"{safe_job}-{safe_run}.json"

    def read(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {}

    def write(self, **kwargs):
        """Atomically update state file. Uses a PID-unique tmp to avoid
        collisions when multiple monitors track the same job (e.g. during testing)."""
        current = self.read()
        current.update(kwargs)
        tmp = self.path.with_name(self.path.stem + f'.{os.getpid()}.tmp')
        tmp.write_text(json.dumps(current, indent=2))
        os.replace(tmp, self.path)

    def is_monitor_alive(self) -> bool:
        state = self.read()
        pid = state.get('monitor_pid')
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    @classmethod
    def list_all(cls) -> list:
        """Return all state files, cleaning up those older than 30 days."""
        if not STATE_DIR.exists():
            return []
        results = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for p in sorted(STATE_DIR.glob('*.json')):
            try:
                data = json.loads(p.read_text())
                started = data.get('started_at', '')
                if started:
                    started_dt = datetime.fromisoformat(started)
                    if started_dt < cutoff:
                        p.unlink()
                        continue
                results.append(data)
            except Exception:
                pass
        return results


# ---------------------------------------------------------------------------
# CmuxBridge
# ---------------------------------------------------------------------------

class CmuxBridge:
    """Sends keystrokes and optional notifications to cmux surfaces.

    Fallback chain when original surface is unreachable:
      1. Try stored surface_id
      2. Scan stored workspace for a Claude Code surface (title match + optional CWD match)
      3. Scan all workspaces for a Claude Code surface
      4. Print notification to own stdout (visible in the watcher split) + desktop notify
    """

    def __init__(
        self,
        surface_id: str,
        workspace_ref: Optional[str] = None,
        cc_cwd: Optional[str] = None,
        enable_notify: bool = False,
        enable_status: bool = False,
        state: Optional['GlueMonitorState'] = None,
    ):
        self.surface_id = surface_id
        self.workspace_ref = workspace_ref
        self.cc_cwd = cc_cwd
        self.enable_notify = enable_notify
        self.enable_status = enable_status
        self._state = state  # for persisting re-discovered surface_id

    def _run(self, cmd: list, timeout: int = 5) -> bool:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return result.returncode == 0
        except Exception:
            return False

    def _run_output(self, cmd: list, timeout: int = 5) -> Optional[str]:
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
            if result.returncode == 0:
                return result.stdout.decode()
            return None
        except Exception:
            return None

    # --- Surface discovery ---

    def _extract_refs(self, text: str, prefix: str) -> list[str]:
        """Extract all refs like 'pane:12' or 'surface:80' from cmux output."""
        return re.findall(rf'{prefix}:\d+', text)

    def _get_all_workspace_refs(self) -> list[str]:
        out = self._run_output(['cmux', 'list-workspaces'])
        if not out:
            return []
        refs = self._extract_refs(out, 'workspace')
        # Put stored workspace first so it's tried before others
        if self.workspace_ref and self.workspace_ref in refs:
            refs.remove(self.workspace_ref)
            refs.insert(0, self.workspace_ref)
        return refs

    def _get_pane_refs(self, workspace_ref: Optional[str] = None) -> list[str]:
        """List panes, preferring a specific workspace if provided."""
        if workspace_ref:
            out = self._run_output(['cmux', 'list-panes', '--workspace', workspace_ref])
            if out:
                return self._extract_refs(out, 'pane')
        # Fall back to listing panes in current context
        out = self._run_output(['cmux', 'list-panes'])
        return self._extract_refs(out, 'pane') if out else []

    def _get_surface_lines(self, pane_ref: str, workspace_ref: Optional[str] = None) -> list[str]:
        cmd = ['cmux', 'list-pane-surfaces', '--pane', pane_ref]
        if workspace_ref:
            cmd += ['--workspace', workspace_ref]
        out = self._run_output(cmd)
        # Retry with workspace if cross-workspace pane lookup failed
        if not out and not workspace_ref:
            return []
        return out.splitlines() if out else []

    def _is_claude_surface(self, surface_line: str) -> bool:
        """Check if a surface title line looks like a Claude Code session."""
        lower = surface_line.lower()
        return 'claude' in lower

    def _surface_cwd_matches(self, surface_ref: str) -> bool:
        """Check if the shell prompt in the surface contains the expected CWD."""
        if not self.cc_cwd:
            return True  # no hint — accept any CC surface
        out = self._run_output(['cmux', 'read-screen', '--surface', surface_ref, '--lines', '4'])
        return bool(out and self.cc_cwd in out)

    def _find_claude_surface(self, workspace_refs: list[str]) -> Optional[tuple[str, str]]:
        """Scan workspaces for a Claude Code surface.

        Returns (surface_ref, workspace_ref) of the best match, or None.
        Collects all title-matching CC surfaces, then prefers a CWD match as tiebreaker.
        workspace_ref is needed for cross-workspace sends.
        """
        candidates: list[tuple[str, str]] = []  # (surface_ref, workspace_ref)

        for ws_ref in workspace_refs:
            pane_refs = self._get_pane_refs(ws_ref)
            if not pane_refs:
                pane_refs = self._get_pane_refs()
            for pane_ref in pane_refs:
                for line in self._get_surface_lines(pane_ref, workspace_ref=ws_ref):
                    surf_refs = self._extract_refs(line, 'surface')
                    if not surf_refs:
                        continue
                    surf_ref = surf_refs[0]
                    if surf_ref == self.surface_id and ws_ref == self.workspace_ref:
                        continue  # already tried: same surface, same workspace
                    if self._is_claude_surface(line):
                        candidates.append((surf_ref, ws_ref))

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        # Multiple CC surfaces — prefer CWD match, fall back to first found
        for surf_ref, ws_ref in candidates:
            if self._surface_cwd_matches(surf_ref):
                return surf_ref, ws_ref
        return candidates[0]

    # --- Delivery ---

    def _send(self, surface_ref: str, message: str, workspace_ref: Optional[str] = None) -> bool:
        """Send keystrokes to a surface, trying with workspace if plain send fails."""
        if self._run(['cmux', 'send', '--surface', surface_ref, message + '\n']):
            return True
        # Cross-workspace send requires --workspace flag
        if workspace_ref:
            return self._run(['cmux', 'send', '--surface', surface_ref,
                              '--workspace', workspace_ref, message + '\n'])
        return False

    def _find_surface_workspace(self, surface_id: str) -> Optional[str]:
        """Find which workspace a known surface_id has moved to.

        Used when the stored surface is unreachable in its stored workspace.
        Returns the workspace_ref where it was found, or None.
        """
        for ws_ref in self._get_all_workspace_refs():
            pane_refs = self._get_pane_refs(ws_ref)
            for pane_ref in pane_refs:
                for line in self._get_surface_lines(pane_ref, workspace_ref=ws_ref):
                    if surface_id in line:
                        return ws_ref
        return None

    def send_to_claude(self, message: str) -> bool:
        """Send text as keystrokes to the Claude Code surface.

        Fallback chain:
          1. Direct send to stored surface_id (works if same workspace)
          2. Locate stored surface_id in other workspaces (surface moved), retry with --workspace
          3. Scan all workspaces for any CC surface (title match + CWD tiebreaker)
          4. Print to own terminal + desktop notify
        """
        # 1. Try direct send
        if self._send(self.surface_id, message, self.workspace_ref):
            print(f"[{ts()}] OK: Delivered to {self.surface_id}", flush=True)
            return True

        # 2. Surface might have moved — find its new workspace and retry
        print(f"[{ts()}] WARN: {self.surface_id} unreachable. Locating it across workspaces...", flush=True)
        new_ws = self._find_surface_workspace(self.surface_id)
        if new_ws and new_ws != self.workspace_ref:
            if self._send(self.surface_id, message, new_ws):
                print(f"[{ts()}] OK: Delivered to {self.surface_id} (relocated to {new_ws})", flush=True)
                self._update_surface(self.surface_id)  # update stored workspace
                # Also persist new workspace
                if self._state:
                    self._state.write(workspace_ref=new_ws)
                self.workspace_ref = new_ws
                return True

        # 3. Stored surface gone entirely — scan for any CC surface
        print(f"[{ts()}] WARN: {self.surface_id} not found anywhere. Scanning for any Claude Code session...", flush=True)
        result = self._find_claude_surface(self._get_all_workspace_refs())
        if result:
            surf, ws = result
            if self._send(surf, message, ws):
                print(f"[{ts()}] OK: Delivered to {surf} in {ws} (original surface gone)", flush=True)
                self._update_surface(surf)
                return True

        # 4. Give up on keystrokes — print visibly in own terminal + desktop notify
        hint = ""
        if self._state:
            hint = (
                f"\n[{ts()}] HINT: Run 'glue_job.py check-status "
                f"--job-name {self._state.job_name} "
                f"--run-id {self._state.run_id} --profile <profile>' to see current state."
            )
        print(
            f"\n[{ts()}] WARN: No Claude Code surface found anywhere. Delivery failed.\n"
            f"{'='*60}\n"
            f"NOTIFICATION: {message}\n"
            f"{'='*60}{hint}\n",
            flush=True,
        )
        # Always send desktop notify on delivery failure regardless of --cmux-notify setting
        self._run(['cmux', 'notify', '--title', 'Glue monitor (surface lost)', '--body', message], timeout=5)
        return False

    def _update_surface(self, new_surface_id: str):
        """Persist re-discovered surface ID so subsequent notifications go there directly."""
        self.surface_id = new_surface_id
        if self._state:
            self._state.write(surface_id=new_surface_id)

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
# GlueJobMonitor
# ---------------------------------------------------------------------------

class GlueJobMonitor:
    """Polling loop that monitors a Glue job and notifies on state changes."""

    def __init__(
        self,
        client: GlueJobClient,
        state: GlueMonitorState,
        bridge: CmuxBridge,
        poll_interval: int,
        cw_metrics: Optional['CloudWatchMetrics'] = None,
    ):
        self.client = client
        self.state = state
        self.bridge = bridge
        self.poll_interval = poll_interval
        self.cw_metrics = cw_metrics
        self._running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, _signum, _frame):
        self._running = False

    def _print_startup_summary(self, job_name: str, run_id: str, run: dict):
        """Print a human-friendly job summary visible in the watcher split."""
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

    def run(self, job_name: str, run_id: str):
        started_at = datetime.now(timezone.utc)
        status_key = f"glue-{run_id[:8]}"

        self.state.write(
            monitor_pid=os.getpid(),
            started_at=now_iso(),
            current_state='WATCHING',
            previous_state=None,
            state_history=[],
            error_message=None,
        )

        previous_state = None
        consecutive_credential_errors = 0
        consecutive_poll_errors = 0
        printed_summary = False
        num_workers = 0

        while self._running:
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

            # 24-hour hard timeout
            if elapsed > 86400:
                msg = (
                    f"Glue job '{job_name}' (run {run_id}) monitor timed out "
                    f"after 24 hours. Last known state: {previous_state}. "
                    f"Use check-status to verify current state."
                )
                self.state.write(current_state='MONITOR_TIMEOUT', error_message='24h timeout')
                self.bridge.send_to_claude(msg)
                self.bridge.notify('Glue monitor timeout', msg)
                self.bridge.clear_status(status_key)
                return

            try:
                run = self.client.get_job_run(job_name, run_id)
                consecutive_credential_errors = 0
                consecutive_poll_errors = 0
            except Exception as e:
                err_str = str(e)
                if 'ExpiredToken' in err_str or 'InvalidClientTokenId' in err_str:
                    consecutive_credential_errors += 1
                    if consecutive_credential_errors >= 2:
                        msg = (
                            f"Glue job '{job_name}' (run {run_id}) monitor stopped: "
                            f"AWS credentials expired. Refresh credentials and re-launch "
                            f"watch-job with the same run ID."
                        )
                        self.state.write(current_state='CREDENTIAL_EXPIRED', error_message=err_str)
                        self.bridge.send_to_claude(msg)
                        self.bridge.clear_status(status_key)
                        return
                    time.sleep(30)
                    continue
                else:
                    consecutive_poll_errors += 1
                    print(f"[{ts()}] WARN: Poll error #{consecutive_poll_errors} (will retry): {e}", flush=True)
                    if consecutive_poll_errors >= 3:
                        msg = (
                            f"Glue watcher: '{job_name}' ({run_id}) — POLL ERROR after "
                            f"{consecutive_poll_errors} consecutive failures.\n"
                            f"Last error: {e}\n"
                            f"Monitor is retrying but may need intervention."
                        )
                        self.bridge.send_to_claude(msg)
                        consecutive_poll_errors = 0  # reset after surfacing, keep retrying
                    time.sleep(self.poll_interval)
                    continue

            current_state = run.get('JobRunState', 'UNKNOWN')
            exec_time = run.get('ExecutionTime', 0)
            error_msg = run.get('ErrorMessage', '')
            dpu_seconds = run.get('DPUSeconds', 0)

            # Print rich summary once on first successful poll
            if not printed_summary:
                num_workers = run.get('NumberOfWorkers', 0)
                self._print_startup_summary(job_name, run_id, run)
                if self.cw_metrics:
                    print(
                        "Poll columns: state | exec time | DPU-s (if reported)"
                        " | cpu: workers avg / driver | heap: all workers"
                        " | rec: cumulative read / written | exec: active/total",
                        flush=True,
                    )
                    print(flush=True)
                printed_summary = True

            # Fetch CloudWatch metrics if enabled
            cw_str = ''
            if self.cw_metrics:
                cw_data = self.cw_metrics.fetch(job_name, run_id)
                cw_str = CloudWatchMetrics.format(cw_data, num_workers)
                if cw_str:
                    cw_str = ' | ' + cw_str

            # Per-poll log line
            dpu_str = f" | DPU-s: {int(dpu_seconds):,}" if dpu_seconds else ""
            print(f"[{ts()}] {current_state} | exec: {format_elapsed(exec_time)}{dpu_str}{cw_str}", flush=True)

            self.state.write(
                current_state=current_state,
                previous_state=previous_state,
                last_poll_at=now_iso(),
                execution_time_seconds=exec_time,
                error_message=error_msg or None,
            )

            if current_state != previous_state:
                # State changed — append to history
                existing = self.state.read().get('state_history', [])
                existing.append({'state': current_state, 'at': now_iso()})
                self.state.write(state_history=existing)

                # Always prefer job's actual execution time from the API over monitor elapsed.
                # Monitor elapsed is ~0s on first observation and only reflects how long
                # this particular monitor process has been running, not the job's total runtime.
                elapsed_fmt = format_elapsed(exec_time) if exec_time else format_elapsed(elapsed)

                if current_state in TERMINAL_STATES:
                    if current_state == 'SUCCEEDED':
                        dpu_info = f" DPU-seconds: {int(dpu_seconds)}." if dpu_seconds else ""
                        msg = (
                            f"Glue job '{job_name}' (run {run_id}) SUCCEEDED "
                            f"after {elapsed_fmt}.{dpu_info}"
                        )
                        self.bridge.set_status(status_key, 'SUCCEEDED', color='#196F3D')
                        self.bridge.notify(f"Glue: {job_name}", msg)
                    else:
                        error_info = f" Error: {error_msg}" if error_msg else ""
                        msg = (
                            f"Glue job '{job_name}' (run {run_id}) {current_state} "
                            f"after {elapsed_fmt}.{error_info}"
                        )
                        self.bridge.set_status(status_key, current_state, color='#B71C1C')
                        self.bridge.notify(f"Glue: {job_name}", msg)

                    prev_label = f"{previous_state} -> " if previous_state else ""
                    print(f"[{ts()}] STATE CHANGE: {prev_label}{current_state} after {elapsed_fmt}", flush=True)
                    print(f"[{ts()}] Delivering notification...", flush=True)
                    self.bridge.send_to_claude(msg)
                    self.bridge.clear_status(status_key)
                    return

                else:
                    prev_label = f"{previous_state} -> " if previous_state else ""
                    msg = (
                        f"Glue job '{job_name}' (run {run_id}) state changed: "
                        f"{prev_label}{current_state}. Elapsed: {elapsed_fmt}."
                    )
                    print(f"[{ts()}] STATE CHANGE: {prev_label}{current_state}. Elapsed: {elapsed_fmt}", flush=True)
                    print(f"[{ts()}] Delivering notification...", flush=True)
                    self.bridge.send_to_claude(msg)
                    self.bridge.set_status(status_key, current_state)
                    self.bridge.notify(f"Glue: {job_name}", msg)

                previous_state = current_state

            if not self._running:
                break

            time.sleep(self.poll_interval)

        # Clean exit (signal received)
        print(f"[{ts()}] Monitor stopped (signal received).", flush=True)
        self.state.write(current_state='MONITOR_STOPPED')
        self.bridge.clear_status(status_key)


# ---------------------------------------------------------------------------
# Subcommand: watch-job
# ---------------------------------------------------------------------------

def _detect_own_surface() -> Optional[str]:
    """Detect the surface this process is running in via cmux identify."""
    try:
        result = subprocess.run(
            ['cmux', 'identify', '--json'],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # Use caller.surface_ref — the surface running this process.
            # focused.surface_ref is the currently active tab and drifts as the user switches.
            return data.get('caller', {}).get('surface_ref')
    except Exception:
        pass
    return os.environ.get('CMUX_SURFACE_ID')


def _detect_workspace_ref() -> Optional[str]:
    """Auto-detect the workspace this process is running in via cmux identify."""
    try:
        result = subprocess.run(
            ['cmux', 'identify', '--json'],
            capture_output=True, timeout=5,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('caller', {}).get('workspace_ref')
    except Exception:
        pass
    return os.environ.get('CMUX_WORKSPACE_ID')


def cmd_watch_job(args):
    """Background monitor — requires cmux surface-id."""
    if not args.surface_id:
        print(
            "Error: --surface-id is required for watch-job.\n"
            "\n"
            "Get your surface ID from the cmux SessionStart hook output:\n"
            "  Surface ID: surface:1\n"
            "\n"
            "Without cmux, use check-status for a one-shot status check and\n"
            "set up a team agent with CronCreate for background polling.\n"
            "See the 'Team Agent Monitoring' section in SKILL.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    poll_interval = args.poll_interval_seconds
    if poll_interval < 60:
        print("Error: --poll-interval-seconds must be at least 60.", file=sys.stderr)
        sys.exit(1)
    if poll_interval > 3600:
        print("Error: --poll-interval-seconds must be at most 3600.", file=sys.stderr)
        sys.exit(1)

    workspace_ref = args.workspace_ref or _detect_workspace_ref()

    client = GlueJobClient(profile=args.profile, region=args.region)
    cw_metrics = None if args.no_cloudwatch_metrics else CloudWatchMetrics(profile=args.profile, region=args.region)
    state = GlueMonitorState(args.job_name, args.run_id)
    bridge = CmuxBridge(
        surface_id=args.surface_id,
        workspace_ref=workspace_ref,
        cc_cwd=args.cc_cwd,
        enable_notify=args.cmux_notify,
        enable_status=args.cmux_status,
        state=state,
    )

    # Persist launch args for session resilience
    state.write(
        job_name=args.job_name,
        job_run_id=args.run_id,
        profile=args.profile,
        region=args.region,
        surface_id=args.surface_id,
        workspace_ref=workspace_ref,
        cc_cwd=args.cc_cwd,
        poll_interval_seconds=poll_interval,
        started_at=now_iso(),
    )

    # Detect own surface so we can auto-close the watcher split on exit.
    own_surface_id = None
    if not args.keep_watcher_running:
        own_surface_id = _detect_own_surface()

    print(f"Glue monitor: '{args.job_name}' run {args.run_id}", flush=True)
    cw_label = "disabled (--no-cloudwatch-metrics)" if args.no_cloudwatch_metrics else "enabled"
    print(f"Poll: every {poll_interval}s | Surface: {args.surface_id} | Workspace: {workspace_ref} | CW metrics: {cw_label}", flush=True)
    if args.cc_cwd:
        print(f"CC CWD hint: {args.cc_cwd}", flush=True)
    if own_surface_id:
        print(f"Watcher split: {own_surface_id} (will auto-close on exit; use --keep-watcher-running to prevent)", flush=True)
    print(f"State file: {state.path}", flush=True)
    print(flush=True)

    monitor = GlueJobMonitor(client, state, bridge, poll_interval, cw_metrics=cw_metrics)
    try:
        monitor.run(args.job_name, args.run_id)
    finally:
        if own_surface_id:
            # Small delay so the user can see the final log line before the split closes.
            time.sleep(3)
            subprocess.run(['cmux', 'close-surface', '--surface', own_surface_id],
                           capture_output=True, timeout=5)


# ---------------------------------------------------------------------------
# Subcommand: check-status
# ---------------------------------------------------------------------------

def cmd_check_status(args):
    """One-shot status check or list all tracked jobs."""
    if args.list:
        _print_job_list()
        return

    if not args.job_name or not args.run_id:
        print("Error: --job-name and --run-id are required (or use --list).", file=sys.stderr)
        sys.exit(1)

    if not args.profile:
        print("Error: --profile is required.", file=sys.stderr)
        sys.exit(1)

    state = GlueMonitorState(args.job_name, args.run_id)
    state_data = state.read()

    try:
        import boto3  # noqa: F401
    except ImportError:
        print("Error: boto3 is required. Install it with: pip install boto3", file=sys.stderr)
        sys.exit(1)

    try:
        client = GlueJobClient(profile=args.profile, region=args.region)
        run = client.get_job_run(args.job_name, args.run_id)
    except Exception as e:
        print(f"Error fetching job status: {e}", file=sys.stderr)
        if state_data:
            print("\nLast known state from cache:")
            _print_state(state_data)
        sys.exit(1)

    current_state = run.get('JobRunState', 'UNKNOWN')
    exec_time = run.get('ExecutionTime', 0)
    error_msg = run.get('ErrorMessage', '')
    dpu_seconds = run.get('DPUSeconds', 0)
    started_on = run.get('StartedOn')

    elapsed_fmt = format_elapsed(exec_time) if exec_time else 'N/A'

    print(f"Job:        {args.job_name}")
    print(f"Run ID:     {args.run_id}")
    print(f"State:      {current_state}")
    print(f"Elapsed:    {elapsed_fmt}")
    if dpu_seconds:
        print(f"DPU-secs:  {int(dpu_seconds)}")
    if error_msg:
        print(f"Error:     {error_msg}")
    if started_on:
        print(f"Started:   {started_on.isoformat() if hasattr(started_on, 'isoformat') else started_on}")

    if state_data:
        pid = state_data.get('monitor_pid')
        if pid:
            alive = state.is_monitor_alive()
            status = 'alive' if alive else 'dead'
            print(f"\nMonitor:    PID {pid} ({status})")
            if not alive and current_state not in TERMINAL_STATES:
                print(
                    f"  Warning: Monitor is not running but job is still active.\n"
                    f"  Re-launch: glue_job.py watch-job "
                    f"--job-name {args.job_name} --run-id {args.run_id} "
                    f"--profile {args.profile} --surface-id <surface-id>"
                )
        print(f"State file: {state.path}")

    if current_state in TERMINAL_STATES:
        print(f"\n{'✓' if current_state == 'SUCCEEDED' else '✗'} Job {current_state.lower()}.")


# ---------------------------------------------------------------------------
# Subcommand: stop-monitor
# ---------------------------------------------------------------------------

def cmd_stop_monitor(args):
    """Stop a running background monitor by sending SIGTERM to its PID."""
    if args.list:
        jobs = GlueMonitorState.list_all()
        if not jobs:
            print("No tracked Glue jobs found.")
            return
        alive = [j for j in jobs if _pid_alive(j.get('monitor_pid'))]
        if not alive:
            print("No live monitors found.")
            _print_job_list()
            return
        print("Live monitors:")
        for j in alive:
            print(f"  {j.get('job_name')}  run={j.get('job_run_id')}  pid={j.get('monitor_pid')}")
        return

    if not args.job_name or not args.run_id:
        print("Error: --job-name and --run-id are required (or use --list).", file=sys.stderr)
        sys.exit(1)

    state = GlueMonitorState(args.job_name, args.run_id)
    data = state.read()
    if not data:
        print(f"No state file found for {args.job_name} / {args.run_id}", file=sys.stderr)
        sys.exit(1)

    pid = data.get('monitor_pid')
    if not pid:
        print("No monitor PID in state file.", file=sys.stderr)
        sys.exit(1)

    if not _pid_alive(pid):
        print(f"PID {pid} is not running (already stopped).")
        state.write(current_state='MONITOR_STOPPED')
        return

    os.kill(pid, signal.SIGTERM)
    state.write(current_state='MONITOR_STOPPED')
    print(f"Sent SIGTERM to PID {pid}. Monitor stopping.")


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, PermissionError, ValueError):
        return False


def _print_job_list():
    jobs = GlueMonitorState.list_all()
    if not jobs:
        print("No tracked Glue jobs found.")
        print(f"State directory: {STATE_DIR}")
        return

    print(f"{'JOB NAME':<30} {'RUN ID':<20} {'STATE':<12} {'LAST POLL':<25} {'MONITOR'}")
    print("-" * 110)
    for j in jobs:
        job_name = j.get('job_name', '?')[:29]
        run_id = j.get('job_run_id', '?')[:19]
        state_str = j.get('current_state', '?')[:11]
        last_poll = j.get('last_poll_at', '?')[:24]
        pid = j.get('monitor_pid')
        if pid:
            monitor = f"PID {pid} ({'alive' if _pid_alive(pid) else 'dead'})"
        else:
            monitor = "none"
        print(f"{job_name:<30} {run_id:<20} {state_str:<12} {last_poll:<25} {monitor}")


def _print_state(data: dict):
    for k, v in data.items():
        print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Monitor AWS Glue job execution with background state-change notifications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch job in a visible cmux split (see SKILL.md for split launch pattern)
  glue_job.py watch-job --job-name my-etl --run-id jr_abc123 \\
      --profile my-profile --surface-id surface:1

  # Check current status
  glue_job.py check-status --job-name my-etl --run-id jr_abc123 --profile my-profile

  # List all tracked jobs
  glue_job.py check-status --list

  # Stop a running monitor
  glue_job.py stop-monitor --job-name my-etl --run-id jr_abc123
        """,
    )

    subparsers = parser.add_subparsers(dest='subcommand', metavar='SUBCOMMAND')
    subparsers.required = True

    # --- watch-job ---
    p_watch = subparsers.add_parser(
        'watch-job',
        help='Start monitor (run in a cmux split — see SKILL.md)',
    )
    p_watch.add_argument('--job-name', required=True, help='Glue job name')
    p_watch.add_argument('--run-id', required=True, help='Glue job run ID (e.g. jr_abc123)')
    p_watch.add_argument('--profile', required=True, help='AWS profile name')
    p_watch.add_argument('--region', help='AWS region (uses profile default if not set)')
    p_watch.add_argument(
        '--surface-id',
        required=True,
        help='cmux surface ID of the Claude Code session to notify (e.g. surface:80). '
             'Find it via: cmux identify --json',
    )
    p_watch.add_argument(
        '--workspace-ref',
        help='cmux workspace ref (e.g. workspace:47). Auto-detected if not provided.',
    )
    p_watch.add_argument(
        '--cc-cwd',
        help='Working directory of the Claude Code session (e.g. /path/to/project). '
             'Used to disambiguate when multiple Claude Code sessions are running. '
             'The monitor checks the shell prompt in candidate surfaces for this path.',
    )
    p_watch.add_argument(
        '--poll-interval-seconds',
        type=int,
        default=300,
        metavar='SECONDS',
        help='Seconds between status polls. Min 60, max 3600. Default: 300',
    )
    p_watch.add_argument(
        '--no-cloudwatch-metrics',
        action='store_true',
        help='Disable CloudWatch metrics in poll output (default: enabled). '
             'Requires Glue 2.0+ Spark jobs with CW metrics enabled.',
    )
    p_watch.add_argument(
        '--keep-watcher-running',
        action='store_true',
        help='Keep the watcher split open after the monitor exits (default: auto-close)',
    )
    p_watch.add_argument(
        '--cmux-notify',
        action='store_true',
        help='Enable desktop notifications via cmux on state changes',
    )
    p_watch.add_argument(
        '--cmux-status',
        action='store_true',
        help='Enable sidebar status updates via cmux',
    )

    # --- check-status ---
    p_check = subparsers.add_parser(
        'check-status',
        help='Check current Glue job status or list all tracked jobs',
    )
    p_check.add_argument('--job-name', help='Glue job name')
    p_check.add_argument('--run-id', help='Glue job run ID')
    p_check.add_argument('--profile', help='AWS profile name')
    p_check.add_argument('--region', help='AWS region (uses profile default if not set)')
    p_check.add_argument(
        '--list',
        action='store_true',
        help='List all tracked jobs from local state files',
    )

    # --- stop-monitor ---
    p_stop = subparsers.add_parser(
        'stop-monitor',
        help='Stop a running background monitor',
    )
    p_stop.add_argument('--job-name', help='Glue job name')
    p_stop.add_argument('--run-id', help='Glue job run ID')
    p_stop.add_argument(
        '--list',
        action='store_true',
        help='List live monitors (does not stop anything)',
    )

    args = parser.parse_args()

    if args.subcommand == 'watch-job':
        cmd_watch_job(args)
    elif args.subcommand == 'check-status':
        cmd_check_status(args)
    elif args.subcommand == 'stop-monitor':
        cmd_stop_monitor(args)


if __name__ == '__main__':
    main()
