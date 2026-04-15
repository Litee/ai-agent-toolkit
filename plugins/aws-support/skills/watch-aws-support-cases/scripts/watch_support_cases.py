#!/usr/bin/env python3
"""
AWS Support Case Watcher

Monitor AWS Support cases for status changes, severity changes, and new communications.

Two delivery modes:
  long-poll-with-exit    Poll Support API until changes detected, print JSON, exit 0.
                         Run in background. Re-launch after processing output.
  cmux-keystrokes        Poll and send change events as keystrokes to a CC surface.
                         Runs indefinitely until killed.

State persisted at: ~/.claude/plugin-data/aws-support/watch-aws-support-cases/

Requires Business or Enterprise AWS support plan (SubscriptionRequiredException on Basic/Developer).
Support API is global but endpoint is us-east-1 only.
"""

import argparse
import json
import os
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
import random


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = Path.home() / '.claude' / 'plugin-data' / 'aws-support' / 'watch-aws-support-cases'
_HEARTBEAT_INTERVAL = 300   # 5 minutes
_VERSION_CHECK_INTERVAL = 3600  # 1 hour

# AWS Support case terminal statuses
TERMINAL_STATUSES = {'resolved', 'closed'}


def _version_from_path(path: str) -> str:
    m = _re.search(r'/(\d+\.\d+\.\d+)/skills/', path)
    return m.group(1) if m else 'unknown'


_VERSION = _version_from_path(__file__)

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
            f"[{_ts()}] [Support Watcher v{_VERSION}] WARNING: Running version {_VERSION} but "
            f"version {best_version} is installed. Restart to pick up the newer version.",
            file=sys.stderr, flush=True,
        )


def _ts() -> str:
    return datetime.now(timezone.utc).strftime('%H:%M UTC')


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Instance guard
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
            f"[Support Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)
    except ProcessLookupError:
        return
    except PermissionError:
        print(
            f"[Support Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)


def _write_pid_file(watcher_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    pid_path = _pid_file_path(watcher_id)
    try:
        pid_path.write_text(str(os.getpid()))
    except OSError as e:
        print(f"[Support Watcher] FATAL: failed to write PID file {pid_path}: {e}", file=sys.stderr, flush=True)
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


# ---------------------------------------------------------------------------
# SupportClient
# ---------------------------------------------------------------------------

class SupportClient:
    """Thin boto3 wrapper for AWS Support API (us-east-1 only)."""

    def __init__(self, profile: str, region: str = 'us-east-1'):
        self.profile = profile
        self.region = region

    def _client(self):
        import boto3
        session = boto3.Session(profile_name=self.profile, region_name=self.region)
        return session.client('support', region_name='us-east-1')

    def describe_cases(self, case_ids: list[str], include_resolved: bool = True) -> list[dict]:
        """Describe one or more cases by ID.

        The AWS Support DescribeCases API does not support pagination when caseIdList is
        specified (InvalidParameterCombinationException). Batches into groups of 10 (API max).
        """
        client = self._client()
        results = []
        for i in range(0, len(case_ids), 10):
            batch = case_ids[i:i + 10]
            resp = client.describe_cases(
                caseIdList=batch,
                includeResolvedCases=include_resolved,
                includeCommunications=True,
            )
            results.extend(resp.get('cases', []))
        return results

    def describe_communications(self, case_id: str) -> list[dict]:
        """Fetch all communications for a case. Paginates automatically."""
        client = self._client()
        results = []
        kwargs: dict = {'caseId': case_id, 'maxResults': 100}
        while True:
            resp = client.describe_communications(**kwargs)
            results.extend(resp.get('communications', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        return results

    def list_open_cases(self) -> list[dict]:
        """List all non-terminal cases. Used for --all-open."""
        client = self._client()
        results = []
        kwargs: dict = {
            'includeResolvedCases': False,
            'includeCommunications': True,
            'maxResults': 100,
        }
        while True:
            resp = client.describe_cases(**kwargs)
            results.extend(resp.get('cases', []))
            next_token = resp.get('nextToken')
            if not next_token:
                break
            kwargs['nextToken'] = next_token
        return results


# ---------------------------------------------------------------------------
# WatcherState
# ---------------------------------------------------------------------------

class WatcherState:
    """Read/write watcher state atomically to STATE_DIR/state-<watcher_id>.json."""

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
    def list_all(cls) -> list[dict]:
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


def _make_watcher_id() -> str:
    return os.urandom(4).hex()


# ---------------------------------------------------------------------------
# Change detection helpers
# ---------------------------------------------------------------------------

def _extract_comm_count(case: dict) -> int:
    comms = case.get('recentCommunications', {})
    if isinstance(comms, dict):
        return len(comms.get('communications', []))
    return 0


def _extract_last_comm_time(case: dict) -> str:
    comms = case.get('recentCommunications', {})
    if isinstance(comms, dict):
        comm_list = comms.get('communications', [])
        times = [c.get('timeCreated', '') for c in comm_list if c.get('timeCreated')]
        return max(times) if times else ''
    return ''


def _snapshot_case(case: dict) -> dict:
    """Build a baseline snapshot from a describe_cases result."""
    return {
        'display_id': case.get('displayId', ''),
        'subject': case.get('subject', ''),
        'status': case.get('status', ''),
        'severity_code': case.get('severityCode', ''),
        'communication_count': _extract_comm_count(case),
        'last_communication_time': _extract_last_comm_time(case),
    }


def _detect_case_changes(case_id: str, case: dict, baseline: dict) -> list[dict]:
    """Compare current case state against baseline. Returns list of event dicts."""
    events = []
    ts_str = _ts()

    current_status = case.get('status', '')
    current_severity = case.get('severityCode', '')
    current_comm_count = _extract_comm_count(case)
    current_last_comm = _extract_last_comm_time(case)
    display_id = case.get('displayId', case_id)
    subject = case.get('subject', '')

    # Status change
    old_status = baseline.get('status', '')
    if current_status != old_status:
        events.append({
            'case_id': case_id,
            'display_id': display_id,
            'event_type': 'status_changed',
            'summary': f"Case #{display_id} status changed: {old_status} -> {current_status}",
            'formatted': f"[Support] #{display_id} | status: {old_status} -> {current_status} ({ts_str})",
            'subject': subject,
        })

    # Severity change
    old_severity = baseline.get('severity_code', '')
    if current_severity != old_severity:
        events.append({
            'case_id': case_id,
            'display_id': display_id,
            'event_type': 'severity_changed',
            'summary': f"Case #{display_id} severity changed: {old_severity} -> {current_severity}",
            'formatted': f"[Support] #{display_id} | severity: {old_severity} -> {current_severity} ({ts_str})",
            'subject': subject,
        })

    # New communication
    old_comm_count = baseline.get('communication_count', 0)
    old_last_comm = baseline.get('last_communication_time', '')
    new_comm = (
        current_comm_count > old_comm_count
        or (current_last_comm and current_last_comm > old_last_comm)
    )
    if new_comm:
        new_count = current_comm_count - old_comm_count
        count_str = f"{new_count} new" if new_count > 0 else "new"
        events.append({
            'case_id': case_id,
            'display_id': display_id,
            'event_type': 'new_communication',
            'summary': f"Case #{display_id} has {count_str} communication(s)",
            'formatted': f"[Support] #{display_id} | {count_str} communication(s) ({ts_str})",
            'subject': subject,
        })

    return events


# ---------------------------------------------------------------------------
# SupportPoller
# ---------------------------------------------------------------------------

class SupportPoller:
    """Polls AWS Support cases for changes against stored baselines."""

    def __init__(self, client: SupportClient):
        self.client = client

    def seed_baselines(self, case_ids: list[str], existing: dict) -> dict:
        """Seed baselines for cases not yet tracked. Returns updated baselines dict."""
        baselines = dict(existing)
        to_seed = [cid for cid in case_ids if cid not in baselines]
        if not to_seed:
            return baselines
        cases = self.client.describe_cases(to_seed, include_resolved=True)
        for case in cases:
            cid = case.get('caseId', '')
            if cid:
                baselines[cid] = _snapshot_case(case)
        return baselines

    def fetch_all_changes(self, case_ids: list[str], baselines: dict) -> tuple[list[dict], dict]:
        """Poll all cases for changes. Returns (events, updated_baselines)."""
        cases = self.client.describe_cases(case_ids, include_resolved=True)
        events = []
        new_baselines = dict(baselines)
        for case in cases:
            cid = case.get('caseId', '')
            if not cid:
                continue
            baseline = new_baselines.get(cid, {})
            case_events = _detect_case_changes(cid, case, baseline)
            events.extend(case_events)
            new_baselines[cid] = _snapshot_case(case)
        return events, new_baselines


# ---------------------------------------------------------------------------
# CmuxBridge
# ---------------------------------------------------------------------------

class CmuxBridge:
    """Sends keystrokes and optional notifications to cmux surfaces.

    On delivery failure, prints a restart message and exits — no fallback scanning.
    """

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


def _build_restart_command(
    script_path: str,
    mode: str,
    case_ids: list[str],
    all_open: bool,
    watcher_id: str,
    profile: str,
    region: str,
    poll_interval: int,
    surface_ref: Optional[str] = None,
    workspace_ref: Optional[str] = None,
    cmux_notify: bool = False,
    cmux_status: bool = False,
    max_runtime_hours: int = 24,
    tmux_pane: Optional[str] = None,
) -> str:
    parts = [f"python3 {shlex.quote(script_path)}", "watch"]
    if all_open:
        parts.append("--all-open")
    elif case_ids:
        parts.append("--case-ids " + " ".join(shlex.quote(c) for c in case_ids))
    parts.append(f"--profile {shlex.quote(profile)}")
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


def _case_summary(case_ids: list[str], max_show: int = 3) -> str:
    total = len(case_ids)
    shown = ', '.join(case_ids[:max_show])
    if total <= max_show:
        return shown
    return f"{shown} (+ {total - max_show} more)"


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


def _is_subscription_error(e: Exception) -> bool:
    err_str = str(e)
    return 'SubscriptionRequiredException' in err_str


def _throttle_sleep(poll_interval: int) -> int:
    """Sleep with jitter on throttle, then return doubled poll interval (capped at 3600s)."""
    sleep_time = 3.5 * 60 + random.uniform(-30, 30)
    print(
        f"[{_ts()}] Throttle cool-down: sleeping {sleep_time:.0f}s then doubling interval.",
        file=sys.stderr, flush=True,
    )
    time.sleep(sleep_time)
    return min(poll_interval * 2, 3600)


# ---------------------------------------------------------------------------
# Subcommand: watch (long-poll-with-exit)
# ---------------------------------------------------------------------------

def _run_long_poll_with_exit(args, case_ids: list[str], all_open: bool):
    poll_interval = args.poll_interval_seconds
    watcher_id = args.watcher_id or _make_watcher_id()
    script_path = os.path.abspath(__file__)
    profile = args.profile
    region = args.region
    max_runtime_hours = args.max_runtime_hours

    restart_cmd = _build_restart_command(
        script_path, 'long-poll-with-exit', case_ids, all_open,
        watcher_id, profile, region, poll_interval,
        max_runtime_hours=max_runtime_hours,
    )

    _check_instance_guard(watcher_id)

    state = WatcherState(watcher_id)
    saved = state.read()
    baselines = saved.get('baselines', {})

    client = SupportClient(profile=profile, region=region)
    poller = SupportPoller(client)

    # Seed baselines on first run
    needs_seed = any(cid not in baselines for cid in case_ids)
    if needs_seed:
        print(f"[{_ts()}] Seeding baseline state for {len(case_ids)} case(s)...", file=sys.stderr, flush=True)
        try:
            baselines = poller.seed_baselines(case_ids, baselines)
        except Exception as e:
            if _is_subscription_error(e):
                print(
                    f"[{_ts()}] ERROR: SubscriptionRequiredException — AWS Support API requires "
                    f"Business or Enterprise support plan. Basic/Developer plans are not supported.",
                    file=sys.stderr, flush=True,
                )
                sys.exit(1)
            print(f"[{_ts()}] WARN: seed failed: {e}. Continuing with empty baselines.", file=sys.stderr, flush=True)

    state.write({
        'watcher_id': watcher_id,
        'mode': 'long-poll-with-exit',
        'started_at': saved.get('started_at', _now_iso()),
        'last_poll_at': _now_iso(),
        'monitor_pid': os.getpid(),
        'profile': profile,
        'region': region,
        'case_ids': case_ids,
        'all_open': all_open,
        'poll_interval_seconds': poll_interval,
        'surface_id': None,
        'workspace_ref': None,
        'baselines': baselines,
        'launch_command': restart_cmd,
        'max_runtime_hours': max_runtime_hours,
    })

    print(
        f"[Support Watcher v{_VERSION}] ID: {watcher_id} | Mode: long-poll-with-exit | "
        f"Cases: {_case_summary(case_ids)} | Poll: {poll_interval}s",
        file=sys.stderr, flush=True,
    )
    print(f"Re-launch command:\n  {restart_cmd}", file=sys.stderr, flush=True)
    print("Watching for AWS Support case changes...", file=sys.stderr, flush=True)

    running = [True]
    received_signal = ['']

    def _handle_signal(signum, _):
        running[0] = False
        received_signal[0] = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _write_pid_file(watcher_id)

    started_at = time.monotonic()
    consecutive_cred_errors = 0
    consecutive_poll_errors = 0
    last_heartbeat = time.monotonic()
    last_version_check = time.monotonic()
    max_runtime_seconds = max_runtime_hours * 3600

    try:
        while running[0]:
            time.sleep(poll_interval)

            if not running[0]:
                break

            # Hard timeout
            if time.monotonic() - started_at > max_runtime_seconds:
                print(
                    f"[{_ts()}] Max runtime ({max_runtime_hours}h) reached. Exiting.\n"
                    f"Re-launch: {restart_cmd}",
                    file=sys.stderr, flush=True,
                )
                break

            # Refresh case list if --all-open
            if all_open:
                try:
                    open_cases = client.list_open_cases()
                    case_ids = [c['caseId'] for c in open_cases if c.get('caseId')]
                    new_baselines = poller.seed_baselines(case_ids, baselines)
                    baselines = new_baselines
                    state.update(case_ids=case_ids, baselines=baselines)
                except Exception as e:
                    print(f"[{_ts()}] WARN: could not refresh open cases: {e}", file=sys.stderr, flush=True)

            if not case_ids:
                print(f"[{_ts()}] No cases to watch (--all-open returned empty). Retrying next poll.", file=sys.stderr, flush=True)
                continue

            try:
                new_evts, new_baselines = poller.fetch_all_changes(case_ids, baselines)
                consecutive_cred_errors = 0
                consecutive_poll_errors = 0
            except Exception as e:
                if _is_subscription_error(e):
                    output = {
                        'error': 'SUBSCRIPTION_REQUIRED',
                        'message': 'AWS Support API requires Business or Enterprise support plan.',
                        'watcher_id': watcher_id,
                        'instruction': f"Upgrade support plan, then re-launch:\n{restart_cmd}",
                    }
                    _remove_pid_file(watcher_id)
                    print(json.dumps(output, indent=2))
                    sys.exit(1)

                if _is_credential_error(e):
                    consecutive_cred_errors += 1
                    print(
                        f"[{_ts()}] Credential error #{consecutive_cred_errors}: {e}",
                        file=sys.stderr, flush=True,
                    )
                    if consecutive_cred_errors >= 5:
                        print(
                            f"[{_ts()}] WARN: {consecutive_cred_errors} consecutive credential errors. "
                            f"Please re-authenticate your AWS credentials. "
                            f"Watcher will auto-recover when credentials are refreshed.",
                            file=sys.stderr, flush=True,
                        )
                    time.sleep(min(60 * consecutive_cred_errors, 3600))
                    continue

                if _is_throttle_error(e):
                    print(f"[{_ts()}] Throttled. Applying jittered backoff.", file=sys.stderr, flush=True)
                    poll_interval = _throttle_sleep(poll_interval)
                    restart_cmd = _build_restart_command(
                        script_path, 'long-poll-with-exit', case_ids, all_open,
                        watcher_id, profile, region, poll_interval,
                        max_runtime_hours=max_runtime_hours,
                    )
                    state.update(poll_interval_seconds=poll_interval, launch_command=restart_cmd)
                    continue

                consecutive_poll_errors += 1
                print(f"[{_ts()}] WARN: Poll error #{consecutive_poll_errors}: {e}", file=sys.stderr, flush=True)
                continue

            baselines = new_baselines
            state.update(
                last_poll_at=_now_iso(),
                baselines=baselines,
                case_ids=case_ids,
            )

            if new_evts:
                output = {
                    'events': new_evts,
                    'watcher_id': watcher_id,
                    'instruction': (
                        f"Re-launch the watcher FIRST, then process events.\n"
                        f"{restart_cmd}"
                    ),
                }
                _remove_pid_file(watcher_id)
                print(json.dumps(output, indent=2))
                sys.exit(0)

            # Heartbeat
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{_ts()}] Watching {len(case_ids)} case(s) -- no changes (poll_interval={poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now

            if now - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now

        sig = received_signal[0] or 'timeout'
        print(
            f"[Support Watcher v{_VERSION}] Exiting ({sig}).\n"
            f"Re-launch:\n  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
    finally:
        _remove_pid_file(watcher_id)


# ---------------------------------------------------------------------------
# Subcommand: watch (cmux-keystrokes)
# ---------------------------------------------------------------------------

def _run_cmux_keystrokes(args, case_ids: list[str], all_open: bool):
    poll_interval = args.poll_interval_seconds
    watcher_id = args.watcher_id or _make_watcher_id()
    script_path = os.path.abspath(__file__)
    profile = args.profile
    region = args.region
    max_runtime_hours = args.max_runtime_hours
    surface_ref = args.cmux_surface
    workspace_ref = args.cmux_workspace or _detect_workspace_ref()

    restart_cmd = _build_restart_command(
        script_path, 'cmux-keystrokes', case_ids, all_open,
        watcher_id, profile, region, poll_interval,
        surface_ref=surface_ref, workspace_ref=workspace_ref,
        cmux_notify=args.cmux_notify,
        cmux_status=args.cmux_status,
        max_runtime_hours=max_runtime_hours,
    )

    _check_instance_guard(watcher_id)

    state = WatcherState(watcher_id)
    saved = state.read()
    baselines = saved.get('baselines', {})

    client = SupportClient(profile=profile, region=region)
    poller = SupportPoller(client)
    bridge = CmuxBridge(
        surface_id=surface_ref,
        workspace_ref=workspace_ref,
        enable_notify=args.cmux_notify,
        enable_status=args.cmux_status,
    )

    # Seed baselines
    needs_seed = any(cid not in baselines for cid in case_ids)
    if needs_seed:
        print(f"[{_ts()}] Seeding baseline state...", file=sys.stderr, flush=True)
        try:
            baselines = poller.seed_baselines(case_ids, baselines)
        except Exception as e:
            if _is_subscription_error(e):
                print(
                    f"[{_ts()}] ERROR: SubscriptionRequiredException — Business/Enterprise support plan required.",
                    file=sys.stderr, flush=True,
                )
                sys.exit(1)
            print(f"[{_ts()}] WARN: seed failed: {e}. Continuing with empty baselines.", file=sys.stderr, flush=True)

    state.write({
        'watcher_id': watcher_id,
        'mode': 'cmux-keystrokes',
        'started_at': saved.get('started_at', _now_iso()),
        'last_poll_at': _now_iso(),
        'monitor_pid': os.getpid(),
        'profile': profile,
        'region': region,
        'case_ids': case_ids,
        'all_open': all_open,
        'poll_interval_seconds': poll_interval,
        'surface_id': surface_ref,
        'workspace_ref': workspace_ref,
        'baselines': baselines,
        'launch_command': restart_cmd,
        'max_runtime_hours': max_runtime_hours,
    })

    print(
        f"[Support Watcher v{_VERSION}] ID: {watcher_id} | Mode: cmux-keystrokes | "
        f"Cases: {_case_summary(case_ids)} | Poll: {poll_interval}s | Surface: {surface_ref}",
        file=sys.stderr, flush=True,
    )
    print(f"Re-launch:\n  {restart_cmd}", file=sys.stderr, flush=True)

    # Send startup confirmation
    summary = _case_summary(case_ids)
    if not bridge.send_to_claude(f"[Support Watcher v{_VERSION}] Started. ID: {watcher_id} | Watching: {summary}"):
        print(
            f"Surface {surface_ref} unreachable. Get fresh refs via `cmux identify --json` and re-launch:\n"
            f"  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)

    running = [True]
    received_signal = ['']

    def _handle_signal(signum, _):
        running[0] = False
        received_signal[0] = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    def _handle_sigusr1(_signum, _frame):
        """Handle SIGUSR1 from Claude Code background task manager (exit code 0, not 144)."""
        print(f"[{_ts()}] Received SIGUSR1 — exiting cleanly.", file=sys.stderr, flush=True)
        _remove_pid_file(watcher_id)
        sys.exit(0)
    signal.signal(signal.SIGUSR1, _handle_sigusr1)

    _write_pid_file(watcher_id)

    started_at = time.monotonic()
    consecutive_cred_errors = 0
    consecutive_poll_errors = 0
    cred_notified = False
    last_heartbeat = time.monotonic()
    last_version_check = time.monotonic()
    max_runtime_seconds = max_runtime_hours * 3600
    status_key = f"support-{watcher_id[:6]}"

    try:
        while running[0]:
            time.sleep(poll_interval)

            if not running[0]:
                break

            if time.monotonic() - started_at > max_runtime_seconds:
                msg = (
                    f"[Support Watcher v{_VERSION}] Max runtime ({max_runtime_hours}h) reached. "
                    f"Re-launch: {restart_cmd}"
                )
                bridge.send_to_claude(msg)
                bridge.clear_status(status_key)
                break

            # Refresh case list if --all-open
            if all_open:
                try:
                    open_cases = client.list_open_cases()
                    case_ids = [c['caseId'] for c in open_cases if c.get('caseId')]
                    baselines = poller.seed_baselines(case_ids, baselines)
                    state.update(case_ids=case_ids, baselines=baselines)
                except Exception as e:
                    print(f"[{_ts()}] WARN: could not refresh open cases: {e}", file=sys.stderr, flush=True)

            if not case_ids:
                print(f"[{_ts()}] No cases to watch. Retrying next poll.", file=sys.stderr, flush=True)
                continue

            try:
                new_evts, new_baselines = poller.fetch_all_changes(case_ids, baselines)
                consecutive_cred_errors = 0
                consecutive_poll_errors = 0
                if cred_notified:
                    bridge.send_to_claude(f"[Support Watcher v{_VERSION}] Credentials recovered — resuming.")
                    cred_notified = False
            except Exception as e:
                if _is_subscription_error(e):
                    msg = "[Support Watcher] SubscriptionRequiredException — Business/Enterprise support plan required."
                    bridge.send_to_claude(msg)
                    bridge.clear_status(status_key)
                    break

                if _is_credential_error(e):
                    consecutive_cred_errors += 1
                    print(
                        f"[{_ts()}] Credential error #{consecutive_cred_errors}: {e}",
                        file=sys.stderr, flush=True,
                    )
                    if consecutive_cred_errors >= 5 and not cred_notified:
                        msg = (
                            f"[Support Watcher v{_VERSION}] {consecutive_cred_errors} consecutive "
                            f"AWS credential errors. Please re-authenticate your AWS credentials. "
                            f"Watcher will auto-recover when credentials are refreshed."
                        )
                        bridge.send_to_claude(msg)
                        bridge.notify("Support Watcher", "Credentials expired")
                        bridge.clear_status(status_key)
                        cred_notified = True
                    time.sleep(min(60 * consecutive_cred_errors, 3600))
                    continue

                if _is_throttle_error(e):
                    print(f"[{_ts()}] Throttled. Applying jittered backoff.", file=sys.stderr, flush=True)
                    poll_interval = _throttle_sleep(poll_interval)
                    restart_cmd = _build_restart_command(
                        script_path, 'cmux-keystrokes', case_ids, all_open,
                        watcher_id, profile, region, poll_interval,
                        surface_ref=surface_ref, workspace_ref=workspace_ref,
                        cmux_notify=args.cmux_notify,
                        cmux_status=args.cmux_status,
                        max_runtime_hours=max_runtime_hours,
                    )
                    state.update(poll_interval_seconds=poll_interval, launch_command=restart_cmd)
                    continue

                consecutive_poll_errors += 1
                print(f"[{_ts()}] WARN: Poll error #{consecutive_poll_errors}: {e}", file=sys.stderr, flush=True)
                if consecutive_poll_errors >= 3:
                    msg = (
                        f"[Support Watcher v{_VERSION}] {consecutive_poll_errors} consecutive poll errors. "
                        f"Last: {str(e)[:80]}. Still watching."
                    )
                    bridge.send_to_claude(msg)
                    consecutive_poll_errors = 0
                continue

            baselines = new_baselines
            state.update(last_poll_at=_now_iso(), baselines=baselines, case_ids=case_ids)

            for evt in new_evts:
                bridge.set_status(status_key, evt['event_type'])
                formatted = evt.get('formatted', '')
                subject = evt.get('subject', '')
                if subject:
                    parts = formatted.rsplit('(', 1)
                    if len(parts) == 2:
                        formatted = f"{parts[0].rstrip()} ('{subject[:40]}') ({parts[1]}"
                if not bridge.send_to_claude(formatted):
                    print(
                        f"Surface {surface_ref} unreachable. Get fresh refs via `cmux identify --json` and re-launch:\n"
                        f"  {restart_cmd}",
                        file=sys.stderr, flush=True,
                    )
                    _remove_pid_file(watcher_id)
                    bridge.clear_status(status_key)
                    sys.exit(1)

            # Heartbeat
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{_ts()}] Watching {len(case_ids)} case(s) -- no changes (poll_interval={poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now

            if now - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now

        sig = received_signal[0] or 'timeout'
        bridge.clear_status(status_key)
        print(
            f"[Support Watcher v{_VERSION}] Exiting ({sig}).\n"
            f"Re-launch:\n  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
    finally:
        _remove_pid_file(watcher_id)


# ---------------------------------------------------------------------------
# Subcommand: watch (tmux-keystrokes)
# ---------------------------------------------------------------------------

def _run_tmux_keystrokes(args, case_ids: list[str], all_open: bool):
    poll_interval = args.poll_interval_seconds
    watcher_id = args.watcher_id or _make_watcher_id()
    script_path = os.path.abspath(__file__)
    profile = args.profile
    region = args.region
    max_runtime_hours = args.max_runtime_hours
    tmux_pane = args.tmux_pane

    restart_cmd = _build_restart_command(
        script_path, 'tmux-keystrokes', case_ids, all_open,
        watcher_id, profile, region, poll_interval,
        tmux_pane=tmux_pane,
        max_runtime_hours=max_runtime_hours,
    )

    _check_instance_guard(watcher_id)

    state = WatcherState(watcher_id)
    saved = state.read()
    baselines = saved.get('baselines', {})

    client = SupportClient(profile=profile, region=region)
    poller = SupportPoller(client)
    bridge = TmuxBridge(tmux_pane=tmux_pane)

    # Seed baselines
    needs_seed = any(cid not in baselines for cid in case_ids)
    if needs_seed:
        print(f"[{_ts()}] Seeding baseline state...", file=sys.stderr, flush=True)
        try:
            baselines = poller.seed_baselines(case_ids, baselines)
        except Exception as e:
            if _is_subscription_error(e):
                print(
                    f"[{_ts()}] ERROR: SubscriptionRequiredException — Business/Enterprise support plan required.",
                    file=sys.stderr, flush=True,
                )
                sys.exit(1)
            print(f"[{_ts()}] WARN: seed failed: {e}. Continuing with empty baselines.", file=sys.stderr, flush=True)

    state.write({
        'watcher_id': watcher_id,
        'mode': 'tmux-keystrokes',
        'started_at': saved.get('started_at', _now_iso()),
        'last_poll_at': _now_iso(),
        'monitor_pid': os.getpid(),
        'profile': profile,
        'region': region,
        'case_ids': case_ids,
        'all_open': all_open,
        'poll_interval_seconds': poll_interval,
        'surface_id': None,
        'workspace_ref': None,
        'tmux_pane': tmux_pane,
        'baselines': baselines,
        'launch_command': restart_cmd,
        'max_runtime_hours': max_runtime_hours,
    })

    print(
        f"[Support Watcher v{_VERSION}] ID: {watcher_id} | Mode: tmux-keystrokes | "
        f"Cases: {_case_summary(case_ids)} | Poll: {poll_interval}s | Pane: {tmux_pane}",
        file=sys.stderr, flush=True,
    )
    print(f"Re-launch:\n  {restart_cmd}", file=sys.stderr, flush=True)

    # Send startup confirmation
    summary = _case_summary(case_ids)
    if not bridge.send_to_claude(f"[Support Watcher v{_VERSION}] Started. ID: {watcher_id} | Watching: {summary}"):
        print(
            f"tmux pane {tmux_pane} unreachable. Check pane ID and re-launch:\n"
            f"  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
        sys.exit(1)

    running = [True]
    received_signal = ['']

    def _handle_signal(signum, _):
        running[0] = False
        received_signal[0] = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    def _handle_sigusr1(_signum, _frame):
        """Handle SIGUSR1 from Claude Code background task manager (exit code 0, not 144)."""
        print(f"[{_ts()}] Received SIGUSR1 — exiting cleanly.", file=sys.stderr, flush=True)
        _remove_pid_file(watcher_id)
        sys.exit(0)
    signal.signal(signal.SIGUSR1, _handle_sigusr1)

    _write_pid_file(watcher_id)

    started_at = time.monotonic()
    consecutive_cred_errors = 0
    consecutive_poll_errors = 0
    cred_notified = False
    last_heartbeat = time.monotonic()
    last_version_check = time.monotonic()
    max_runtime_seconds = max_runtime_hours * 3600

    try:
        while running[0]:
            time.sleep(poll_interval)

            if not running[0]:
                break

            if time.monotonic() - started_at > max_runtime_seconds:
                msg = (
                    f"[Support Watcher v{_VERSION}] Max runtime ({max_runtime_hours}h) reached. "
                    f"Re-launch: {restart_cmd}"
                )
                bridge.send_to_claude(msg)
                break

            # Refresh case list if --all-open
            if all_open:
                try:
                    open_cases = client.list_open_cases()
                    case_ids = [c['caseId'] for c in open_cases if c.get('caseId')]
                    baselines = poller.seed_baselines(case_ids, baselines)
                    state.update(case_ids=case_ids, baselines=baselines)
                except Exception as e:
                    print(f"[{_ts()}] WARN: could not refresh open cases: {e}", file=sys.stderr, flush=True)

            if not case_ids:
                print(f"[{_ts()}] No cases to watch. Retrying next poll.", file=sys.stderr, flush=True)
                continue

            try:
                new_evts, new_baselines = poller.fetch_all_changes(case_ids, baselines)
                if consecutive_cred_errors > 0 and cred_notified:
                    bridge.send_to_claude(f"[Support Watcher v{_VERSION}] Credentials recovered — resuming.")
                    cred_notified = False
                consecutive_cred_errors = 0
                consecutive_poll_errors = 0
            except Exception as e:
                if _is_subscription_error(e):
                    msg = "[Support Watcher] SubscriptionRequiredException — Business/Enterprise support plan required."
                    bridge.send_to_claude(msg)
                    break

                if _is_credential_error(e):
                    consecutive_cred_errors += 1
                    print(
                        f"[{_ts()}] Credential error #{consecutive_cred_errors}: {e}",
                        file=sys.stderr, flush=True,
                    )
                    if consecutive_cred_errors >= 5 and not cred_notified:
                        msg = (
                            f"[Support Watcher v{_VERSION}] {consecutive_cred_errors} consecutive "
                            f"AWS credential errors. Please re-authenticate your AWS credentials. "
                            f"Watcher will auto-recover when credentials are refreshed."
                        )
                        bridge.send_to_claude(msg)
                        bridge.notify("Support Watcher", "Credentials expired")
                        cred_notified = True
                    time.sleep(min(60 * consecutive_cred_errors, 3600))
                    continue

                if _is_throttle_error(e):
                    print(f"[{_ts()}] Throttled. Applying jittered backoff.", file=sys.stderr, flush=True)
                    poll_interval = _throttle_sleep(poll_interval)
                    restart_cmd = _build_restart_command(
                        script_path, 'tmux-keystrokes', case_ids, all_open,
                        watcher_id, profile, region, poll_interval,
                        tmux_pane=tmux_pane,
                        max_runtime_hours=max_runtime_hours,
                    )
                    state.update(poll_interval_seconds=poll_interval, launch_command=restart_cmd)
                    continue

                consecutive_poll_errors += 1
                print(f"[{_ts()}] WARN: Poll error #{consecutive_poll_errors}: {e}", file=sys.stderr, flush=True)
                if consecutive_poll_errors >= 3:
                    msg = (
                        f"[Support Watcher v{_VERSION}] {consecutive_poll_errors} consecutive poll errors. "
                        f"Last: {str(e)[:80]}. Still watching."
                    )
                    bridge.send_to_claude(msg)
                    consecutive_poll_errors = 0
                continue

            baselines = new_baselines
            state.update(last_poll_at=_now_iso(), baselines=baselines, case_ids=case_ids)

            for evt in new_evts:
                formatted = evt.get('formatted', '')
                subject = evt.get('subject', '')
                if subject:
                    parts = formatted.rsplit('(', 1)
                    if len(parts) == 2:
                        formatted = f"{parts[0].rstrip()} ('{subject[:40]}') ({parts[1]}"
                if not bridge.send_to_claude(formatted):
                    print(
                        f"tmux pane {tmux_pane} unreachable. Check pane ID and re-launch:\n"
                        f"  {restart_cmd}",
                        file=sys.stderr, flush=True,
                    )
                    _remove_pid_file(watcher_id)
                    sys.exit(1)

            # Heartbeat
            now = time.monotonic()
            if now - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{_ts()}] Watching {len(case_ids)} case(s) -- no changes (poll_interval={poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now

            if now - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now

        sig = received_signal[0] or 'timeout'
        print(
            f"[Support Watcher v{_VERSION}] Exiting ({sig}).\n"
            f"Re-launch:\n  {restart_cmd}",
            file=sys.stderr, flush=True,
        )
    finally:
        _remove_pid_file(watcher_id)


# ---------------------------------------------------------------------------
# Subcommand: watch (dispatch)
# ---------------------------------------------------------------------------

def cmd_watch(args):
    # Validate poll interval
    if args.poll_interval_seconds < 60:
        print("Error: --poll-interval-seconds must be at least 60.", file=sys.stderr)
        sys.exit(1)
    if args.poll_interval_seconds > 3600:
        print("Error: --poll-interval-seconds must be at most 3600.", file=sys.stderr)
        sys.exit(1)

    # Warn about non-us-east-1 region
    if args.region != 'us-east-1':
        print(
            f"[{_ts()}] WARN: --region {args.region} specified, but the Support API endpoint "
            f"is us-east-1 only regardless of resource region. Proceeding.",
            file=sys.stderr, flush=True,
        )

    # cmux-mode validation
    if args.mode == 'cmux-keystrokes' and not args.cmux_surface:
        print("Error: --cmux-surface is required when --mode cmux-keystrokes.", file=sys.stderr)
        sys.exit(1)

    # tmux-mode validation
    if args.mode == 'tmux-keystrokes' and not args.tmux_pane:
        print("Error: --tmux-pane is required when --mode tmux-keystrokes.", file=sys.stderr)
        sys.exit(1)

    # Resolve case IDs
    all_open = args.all_open
    if all_open:
        # Discover open cases now
        print(f"[{_ts()}] Discovering all open cases...", file=sys.stderr, flush=True)
        try:
            client = SupportClient(profile=args.profile, region=args.region)
            open_cases = client.list_open_cases()
            case_ids = [c['caseId'] for c in open_cases if c.get('caseId')]
        except Exception as e:
            if _is_subscription_error(e):
                print(
                    "Error: SubscriptionRequiredException — AWS Support API requires "
                    "Business or Enterprise support plan.",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"Error discovering open cases: {e}", file=sys.stderr)
            sys.exit(1)
        if not case_ids:
            print("No open cases found. Nothing to watch.", file=sys.stderr)
            sys.exit(0)
        print(f"[{_ts()}] Found {len(case_ids)} open case(s): {_case_summary(case_ids)}", file=sys.stderr, flush=True)
    else:
        case_ids = args.case_ids or []
        if not case_ids:
            print("Error: --case-ids or --all-open is required.", file=sys.stderr)
            sys.exit(1)

    try:
        if args.mode == 'long-poll-with-exit':
            _run_long_poll_with_exit(args, case_ids, all_open)
        elif args.mode == 'cmux-keystrokes':
            _run_cmux_keystrokes(args, case_ids, all_open)
        else:
            _run_tmux_keystrokes(args, case_ids, all_open)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[{_ts()}] FATAL: {exc}\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args):
    if args.watcher_id:
        state = WatcherState(args.watcher_id)
        data = state.read()
        if not data:
            print(f"No state file found for watcher-id: {args.watcher_id}", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(data, indent=2))
        return

    # List all
    all_states = WatcherState.list_all()
    if not all_states:
        print("No state files found.")
        print(f"State directory: {STATE_DIR}")
        return

    print(f"{'WATCHER ID':<12} {'MODE':<22} {'CASES':<6} {'STATUS':<10} {'LAST POLL':<22} {'PID'}")
    print("-" * 95)
    for data in all_states:
        wid = data.get('watcher_id', '?')[:11]
        mode = data.get('mode', '?')[:21]
        case_ids = data.get('case_ids', [])
        n_cases = str(len(case_ids))
        last_poll = data.get('last_poll_at', 'never')[:21]
        pid = data.get('monitor_pid')
        if pid:
            alive_str = 'alive' if _pid_alive(pid) else 'dead'
            pid_str = f"{pid} ({alive_str})"
        else:
            pid_str = "none"
        all_open_flag = " (--all-open)" if data.get('all_open') else ""
        print(f"{wid:<12} {mode:<22} {n_cases:<6} {'watching':<10} {last_poll:<22} {pid_str}{all_open_flag}")
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
            wid = d.get('watcher_id', '?')
            pid = d.get('monitor_pid', '?')
            cases = d.get('case_ids', [])
            print(f"  {wid}  pid={pid}  cases={_case_summary(cases)}")
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
        description='AWS Support Case Watcher — monitors cases for status, severity, and communication changes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch specific cases (long-poll-with-exit, background)
  watch_support_cases.py watch --case-ids case-123456-2026-abcd --profile my-profile

  # Watch all open cases in cmux split
  watch_support_cases.py watch --all-open --profile my-profile \\
      --mode cmux-keystrokes --cmux-surface surface:80

  # Check watcher state
  watch_support_cases.py status --list

  # Stop a watcher
  watch_support_cases.py stop --watcher-id a1b2c3d4
        """,
    )

    sub = parser.add_subparsers(dest='command', required=True)

    # ---- watch ----
    p_watch = sub.add_parser('watch', help='Start watching AWS Support cases')

    # Case selection (mutually exclusive)
    case_group = p_watch.add_mutually_exclusive_group()
    case_group.add_argument(
        '--case-ids', nargs='+', metavar='CASE_ID',
        help='Case IDs to watch (e.g. case-123456-2026-abcd)',
    )
    case_group.add_argument(
        '--all-open', action='store_true',
        help='Auto-discover and watch all non-terminal cases',
    )

    p_watch.add_argument('--profile', required=True, help='AWS credentials profile')
    p_watch.add_argument(
        '--region', default='us-east-1',
        help='AWS region (default: us-east-1; Support API is global but us-east-1 endpoint only)',
    )
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

    # cmux-only flags
    cmux_group = p_watch.add_argument_group('cmux flags (only valid with --mode cmux-keystrokes)')
    cmux_group.add_argument(
        '--cmux-surface', metavar='SURFACE_REF',
        help='cmux surface ref of the CC session (required for cmux mode). '
             'Get from: cmux identify --json -> caller.surface_ref',
    )
    cmux_group.add_argument(
        '--cmux-workspace', metavar='WORKSPACE_REF',
        help='cmux workspace ref (auto-detected via cmux identify if omitted)',
    )
    cmux_group.add_argument(
        '--cmux-notify', action='store_true',
        help='Enable desktop notifications via cmux on changes',
    )
    cmux_group.add_argument(
        '--cmux-status', action='store_true',
        help='Enable cmux sidebar status badge',
    )

    # tmux-only flags
    tmux_group = p_watch.add_argument_group('tmux flags (only valid with --mode tmux-keystrokes)')
    tmux_group.add_argument(
        '--tmux-pane', metavar='PANE_ID',
        help="tmux pane ID to send keystrokes to (e.g. %%0). Required for tmux mode. "
             "Get from: tmux display-message -p '#{pane_id}' or $TMUX_PANE",
    )

    # ---- status ----
    p_status = sub.add_parser('status', help='Show watcher state or list all watchers')
    p_status.add_argument(
        '--watcher-id', default='',
        help='Show state for a specific watcher ID',
    )
    p_status.add_argument(
        '--list', action='store_true',
        help='List all tracked watchers (default if no --watcher-id given)',
    )

    # ---- stop ----
    p_stop = sub.add_parser('stop', help='Stop a running watcher')
    p_stop.add_argument(
        '--watcher-id', default='',
        help='Watcher ID to stop',
    )
    p_stop.add_argument(
        '--list', action='store_true',
        help='List live watchers without stopping',
    )

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if _VERSION == 'unknown':
        print(
            "[Support Watcher] WARNING: Running from source (version unknown). "
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
