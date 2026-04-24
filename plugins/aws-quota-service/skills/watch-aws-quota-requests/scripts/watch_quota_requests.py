#!/usr/bin/env python3
"""
AWS Service Quota Request Watcher

Monitor AWS Service Quotas increase requests for status changes.
Two delivery modes:
  long-poll-with-exit   Poll until a quota request status changes, print JSON, exit 0.
                        Run in background. Re-launch after processing output.
  cmux-keystrokes       Poll and send change events as keystrokes to a CC surface.
                        Runs continuously until max-runtime or signal.

State persisted at:
  ~/.claude/plugin-data/aws-quota-service/watch-aws-quota-requests/

Usage:
    # Long-poll mode (no cmux required)
    watch_quota_requests.py watch --request-ids req-abc123 --profile myprofile

    # cmux mode
    watch_quota_requests.py watch --request-ids req-abc123 \\
        --profile myprofile --mode cmux-keystrokes --cmux-surface surface:80

    # Discover and watch all pending requests
    watch_quota_requests.py watch --all-pending --profile myprofile

    # Check status of running watchers
    watch_quota_requests.py status --list

    # Stop a watcher
    watch_quota_requests.py stop --watcher-id a1b2c3d4
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
import random
import fcntl

_WATCHER_SEND_LOCK = '/tmp/watcher_send.lock'


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = (
    Path.home()
    / '.claude'
    / 'plugin-data'
    / 'aws-quota-service'
    / 'watch-aws-quota-requests'
)

TERMINAL_STATUSES = {'APPROVED', 'DENIED', 'CASE_CLOSED', 'NOT_APPROVED'}
PENDING_STATUSES = {'PENDING', 'CASE_OPENED'}

_HEARTBEAT_INTERVAL = 300  # 5 minutes in seconds
_VERSION_CHECK_INTERVAL = 3600  # 1 hour in seconds


def _version_from_path(path: str) -> str:
    m = re.search(r'/(\d+\.\d+\.\d+)/skills/', path)
    return m.group(1) if m else 'unknown'


_VERSION = _version_from_path(__file__)
_ver = lambda: f"v{_VERSION}" if _VERSION != 'unknown' else "(unknown version)"
_WATCHER_NAME = "Quota Watcher"

_INSTALLED_PLUGINS_PATH = Path.home() / '.claude' / 'plugins' / 'installed_plugins.json'


def _plugin_identity_from_path(path: str):
    m = re.search(r'/cache/([^/]+)/([^/]+)/\d+\.\d+\.\d+/skills/', path)
    return (m.group(1), m.group(2)) if m else ('', '')


_MARKETPLACE_NAME, _PLUGIN_NAME = _plugin_identity_from_path(__file__)


def _parse_semver(version: str) -> tuple:
    try:
        parts = version.split('.')
        return tuple(int(p) for p in parts[:3])
    except (ValueError, TypeError):
        return (0, 0, 0)


def _check_version_drift() -> None:
    """Check installed_plugins.json for a newer version. Warn to stderr if found."""
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
            f"[{ts()}] [Quota Watcher {_ver()}] WARNING: Running version {_VERSION} but "
            f"version {best_version} is installed. Restart the watcher by invoking the "
            f"'watch-aws-quota-requests' skill.",
            file=sys.stderr, flush=True,
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def ts() -> str:
    return datetime.now(timezone.utc).strftime('%H:%M UTC')


def _pfx() -> str:
    return f"[{_WATCHER_NAME} {_ver()}] ({ts()})"


# ---------------------------------------------------------------------------
# Instance guard — PID file to prevent duplicate watchers
# ---------------------------------------------------------------------------

def _pid_file_path(watcher_id: str) -> Path:
    return STATE_DIR / f"watcher-{watcher_id}.pid"


def _check_instance_guard(watcher_id: str) -> None:
    """Exit with error if another process with this watcher_id is already running."""
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
            f"[Quota Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
    except ProcessLookupError:
        return  # stale PID file — safe to proceed
    except PermissionError:
        print(
            f"[Quota Watcher] ERROR: watcher {watcher_id} is already running (PID {pid}).\n"
            f"  PID file: {pid_path}\n"
            f"  To force a restart: kill {pid} && rm {pid_path}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


def _write_pid_file(watcher_id: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _pid_file_path(watcher_id).write_text(str(os.getpid()))
    except OSError as e:
        print(
            f"[Quota Watcher] FATAL: failed to write PID file: {e}",
            file=sys.stderr, flush=True,
        )
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
# ServiceQuotaClient
# ---------------------------------------------------------------------------

class ServiceQuotaClient:
    """Thin boto3 wrapper for Service Quotas API queries."""

    def __init__(self, profile: str, region: Optional[str] = None):
        self.profile = profile
        self.region = region

    def _client(self):
        """Recreates session each call for credential refresh."""
        import boto3
        kwargs = {'profile_name': self.profile}
        if self.region:
            kwargs['region_name'] = self.region
        session = boto3.Session(**kwargs)
        return session.client('service-quotas')

    def get_requested_change(self, request_id: str) -> dict:
        """Fetch current state of a single quota change request."""
        client = self._client()
        return client.get_requested_service_quota_change(
            RequestId=request_id,
        )['RequestedQuota']

    def list_pending_changes(self) -> list:
        """List all quota change requests with PENDING or CASE_OPENED status.

        Uses list_requested_service_quota_changes with NextToken pagination.
        """
        client = self._client()
        results = []
        kwargs: dict = {}
        while True:
            try:
                resp = client.list_requested_service_quota_changes(**kwargs)
            except Exception:
                # Some older SDK versions only have the by-service variant;
                # fall through to an empty list — caller handles the error.
                raise
            for req in resp.get('RequestedQuotas', []):
                if req.get('Status') in PENDING_STATUSES:
                    results.append(req)
            token = resp.get('NextToken')
            if not token:
                break
            kwargs = {'NextToken': token}
        return results


# ---------------------------------------------------------------------------
# WatcherState
# ---------------------------------------------------------------------------

class WatcherState:
    """Manages persistent state file for a quota request watcher."""

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

    def write(self, **kwargs):
        """Atomically update state file. Merges kwargs into current state."""
        current = self.read()
        current.update(kwargs)
        tmp = self.path.with_name(self.path.stem + f'.{os.getpid()}.tmp')
        try:
            tmp.write_text(json.dumps(current, indent=2))
            os.replace(tmp, self.path)
        except Exception:
            try:
                tmp.unlink()
            except Exception:
                pass
            raise

    def is_alive(self) -> bool:
        state = self.read()
        pid = state.get('monitor_pid')
        if not pid:
            return False
        return _pid_alive(pid)

    @classmethod
    def list_all(cls) -> list:
        """Return all state files, cleaning up those older than 30 days."""
        if not STATE_DIR.exists():
            return []
        results = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        for p in sorted(STATE_DIR.glob('state-*.json')):
            try:
                data = json.loads(p.read_text())
                started = data.get('started_at', '')
                if started:
                    started_dt = datetime.fromisoformat(started)
                    if started_dt.tzinfo is None:
                        started_dt = started_dt.replace(tzinfo=timezone.utc)
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
        message = message.replace('\r', ' ').replace('\n', ' ')
        payload = message + '\n'
        attempts = [['cmux', 'send', '--surface', self.surface_id, payload]]
        if self.workspace_ref:
            attempts.append(['cmux', 'send', '--surface', self.surface_id,
                             '--workspace', self.workspace_ref, payload])
        with open(_WATCHER_SEND_LOCK, 'w') as _lock_fh:
            fcntl.flock(_lock_fh, fcntl.LOCK_EX)
            try:
                for attempt in range(3):
                    for cmd in attempts:
                        if self._run(cmd):
                            return True
                    if attempt < 2:
                        print(f"[{ts()}] WARN: cmux send failed (attempt {attempt + 1}/3), retrying in 3s ...",
                              file=sys.stderr, flush=True)
                        time.sleep(3)
                print(f"[{ts()}] ERROR: cmux send failed after 3 attempts.", file=sys.stderr, flush=True)
            finally:
                fcntl.flock(_lock_fh, fcntl.LOCK_UN)
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
        """Send text as a keystroke line to the tmux pane. Retries up to 2 times."""
        message = message.replace('\r', ' ').replace('\n', ' ')
        cmd = ['tmux', 'send-keys', '-t', self.tmux_pane, message + '\n', 'Enter']
        with open(_WATCHER_SEND_LOCK, 'w') as _lock_fh:
            fcntl.flock(_lock_fh, fcntl.LOCK_EX)
            try:
                for attempt in range(3):
                    if self._run(cmd):
                        return True
                    if attempt < 2:
                        print(
                            f"[{ts()}] WARN: tmux send-keys failed (attempt {attempt + 1}/3), "
                            f"retrying in 3s ...",
                            file=sys.stderr, flush=True,
                        )
                        time.sleep(3)
                print(
                    f"[{ts()}] ERROR: tmux send-keys failed after 3 attempts. Pane: {self.tmux_pane!r}.",
                    file=sys.stderr, flush=True,
                )
            finally:
                fcntl.flock(_lock_fh, fcntl.LOCK_UN)
        return False

    def notify(self, title: str, body: str):
        self._run(['tmux', 'display-message', '-t', self.tmux_pane, f"{title}: {body}"])

    def set_status(self, *_a, **_kw) -> None:
        pass  # no-op: tmux has no sidebar status

    def clear_status(self, *_a, **_kw) -> None:
        pass  # no-op


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
# QuotaRequestWatcher — polling loop
# ---------------------------------------------------------------------------

class QuotaRequestWatcher:
    """Polling loop that monitors quota change requests and notifies on status changes."""

    def __init__(
        self,
        client: ServiceQuotaClient,
        state: WatcherState,
        bridge: Optional[CmuxBridge | TmuxBridge],
        mode: str,
        poll_interval: int,
        max_runtime_hours: int,
        watcher_id: str,
    ):
        self.client = client
        self.state = state
        self.bridge = bridge
        self.mode = mode
        self.poll_interval = poll_interval
        self.max_runtime_seconds = max_runtime_hours * 3600
        self.watcher_id = watcher_id
        self._running = True
        self._received_signal = ''
        self._cred_notified = False
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        if mode in ('cmux-keystrokes', 'tmux-keystrokes'):
            signal.signal(signal.SIGUSR1, self._handle_sigusr1)

    def _handle_signal(self, signum: int, _: object) -> None:
        self._running = False
        self._received_signal = signal.Signals(signum).name

    def _handle_sigusr1(self, *_: object) -> None:
        """Handle SIGUSR1 from Claude Code background task manager (exit code 0, not 144)."""
        print(f"[{ts()}] Received SIGUSR1 — exiting cleanly.", file=sys.stderr, flush=True)
        _remove_pid_file(self.watcher_id)
        sys.exit(0)

    def _snapshot(self, req: dict) -> dict:
        """Build a baseline snapshot dict from a quota request API response."""
        last_updated = req.get('LastUpdated', '')
        if hasattr(last_updated, 'isoformat'):
            last_updated = last_updated.isoformat()
        created = req.get('Created', '')
        if hasattr(created, 'isoformat'):
            created = created.isoformat()
        return {
            'service_code': req.get('ServiceCode', ''),
            'service_name': req.get('ServiceName', ''),
            'quota_code': req.get('QuotaCode', ''),
            'quota_name': req.get('QuotaName', ''),
            'desired_value': req.get('DesiredValue'),
            'status': req.get('Status', ''),
            'case_id': req.get('CaseId', ''),
            'created': str(created),
            'last_updated': str(last_updated),
        }

    def _seed_baselines(self, request_ids: list) -> dict:
        """Fetch current state for all request IDs and store as baselines.

        Returns the baselines dict (keyed by request_id).
        Does not emit any events — first launch establishes ground truth.
        """
        existing = self.state.read().get('requests', {})
        baselines = dict(existing)

        for req_id in request_ids:
            if req_id in baselines:
                continue  # already seeded from a previous run
            try:
                req = self.client.get_requested_change(req_id)
                baselines[req_id] = self._snapshot(req)
                snap = baselines[req_id]
                print(
                    f"[{ts()}] Seeded {req_id}: "
                    f"{snap['service_name']} / {snap['quota_name']} "
                    f"| desired={snap['desired_value']} | status={snap['status']}",
                    file=sys.stderr, flush=True,
                )
            except Exception as e:
                print(f"[{ts()}] WARN: Could not seed {req_id}: {e}", file=sys.stderr, flush=True)

        self.state.write(requests=baselines)
        return baselines

    def _detect_changes(self, req_id: str, baseline: dict, req: dict) -> list:
        """Compare current request state against baseline; return list of events."""
        events = []
        current = self._snapshot(req)
        ts_str = ts()

        if current['status'] != baseline.get('status', ''):
            old_status = baseline.get('status', '?')
            new_status = current['status']
            service_code = current['service_code'] or baseline.get('service_code', '?')
            service_name = current['service_name'] or baseline.get('service_name', '?')
            quota_name = current['quota_name'] or baseline.get('quota_name', '?')
            desired = current.get('desired_value')

            summary = (
                f"Quota request for '{quota_name}' ({service_name}): "
                f"{old_status} -> {new_status}"
            )
            formatted = (
                f"[Quota] {req_id} | {service_code.upper()} / {quota_name}: "
                f"{old_status} -> {new_status} ({ts_str})"
            )

            events.append({
                'request_id': req_id,
                'event_type': 'status_changed',
                'summary': summary,
                'formatted': formatted,
                'service_code': service_code,
                'quota_name': quota_name,
                'desired_value': desired,
                'new_status': new_status,
            })

        return events

    def run(self, request_ids: list):
        """Main poll loop."""
        started_at = datetime.now(timezone.utc)
        last_heartbeat = time.monotonic()
        last_version_check = time.monotonic()
        consecutive_credential_errors = 0
        consecutive_poll_errors = 0

        self.state.write(
            monitor_pid=os.getpid(),
            started_at=now_iso(),
            mode=self.mode,
            request_ids=request_ids,
            poll_interval_seconds=self.poll_interval,
        )

        # Seed baselines (no-op for already-seeded IDs)
        baselines = self._seed_baselines(request_ids)

        # Track which IDs are still active (non-terminal)
        active_ids = [
            rid for rid in request_ids
            if baselines.get(rid, {}).get('status', '') not in TERMINAL_STATUSES
        ]

        print(
            f"[{ts()}] Quota Request Watcher {_ver()} | ID: {self.watcher_id} | "
            f"Watching {len(active_ids)} active request(s) | poll={self.poll_interval}s",
            file=sys.stderr, flush=True,
        )

        while self._running and active_ids:
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()

            # Hard timeout
            if elapsed > self.max_runtime_seconds:
                self._handle_timeout(active_ids)
                return

            time.sleep(self.poll_interval)

            if not self._running:
                break

            # Poll each active request
            all_events = []
            ids_to_remove = []

            for req_id in list(active_ids):
                try:
                    req = self.client.get_requested_change(req_id)
                    if consecutive_credential_errors > 0:
                        if self._cred_notified and self.mode in ('cmux-keystrokes', 'tmux-keystrokes') and self.bridge:
                            self.bridge.send_to_claude(
                                f"{_pfx()} Credentials recovered — resuming normal polling."
                            )
                        self._cred_notified = False
                    consecutive_credential_errors = 0
                    consecutive_poll_errors = 0
                except Exception as e:
                    err_str = str(e)

                    if any(k in err_str for k in ('ExpiredToken', 'InvalidClientTokenId',
                                                   'ExpiredTokenException', 'AuthFailure',
                                                   'TokenExpiredException', 'NotAuthorizedException',
                                                   'InvalidSignatureException')):
                        consecutive_credential_errors += 1
                        print(
                            f"[{ts()}] Credential error #{consecutive_credential_errors} for {req_id}: {e}",
                            file=sys.stderr, flush=True,
                        )
                        if consecutive_credential_errors >= 5 and not self._cred_notified:
                            msg = (
                                f"{_pfx()} {consecutive_credential_errors} consecutive "
                                f"AWS credential errors. Please re-authenticate your AWS credentials. "
                                f"Watcher will auto-recover when credentials are refreshed."
                            )
                            if self.mode in ('cmux-keystrokes', 'tmux-keystrokes') and self.bridge:
                                self.bridge.send_to_claude(msg)
                            else:
                                print(f"[{ts()}] WARN: {msg}", file=sys.stderr, flush=True)
                            self._cred_notified = True
                        time.sleep(min(60 * consecutive_credential_errors, 3600))
                        continue

                    if any(k in err_str for k in ('ThrottlingException', 'Throttling',
                                                   'TooManyRequestsException')):
                        print(
                            f"[{ts()}] WARN: Throttled — applying jittered backoff.",
                            file=sys.stderr, flush=True,
                        )
                        self.poll_interval = _throttle_sleep(self.poll_interval)
                        continue

                    if any(k in err_str for k in ('NoSuchResourceException', 'NoSuchResource')):
                        print(
                            f"[{ts()}] WARN: Request ID {req_id} not found — removing from watch list.",
                            file=sys.stderr, flush=True,
                        )
                        ids_to_remove.append(req_id)
                        continue

                    consecutive_poll_errors += 1
                    print(
                        f"[{ts()}] WARN: Poll error #{consecutive_poll_errors} for {req_id}: {e}",
                        file=sys.stderr, flush=True,
                    )
                    if consecutive_poll_errors >= 3:
                        warn_msg = (
                            f"{_pfx()} {req_id} — {consecutive_poll_errors} consecutive "
                            f"poll errors. Last: {str(e)[:100]}. Monitor retrying."
                        )
                        if self.mode == 'cmux-keystrokes' and self.bridge:
                            self.bridge.send_to_claude(warn_msg)
                        else:
                            print(f"[{ts()}] PROMINENT WARN: {warn_msg}", file=sys.stderr, flush=True)
                        consecutive_poll_errors = 0  # reset after surfacing, keep retrying
                    continue

                baseline = baselines.get(req_id, {})
                events = self._detect_changes(req_id, baseline, req)

                if events:
                    all_events.extend(events)
                    baselines[req_id] = self._snapshot(req)
                    self.state.write(requests=baselines)
                    # If terminal — schedule removal after delivering event
                    if baselines[req_id]['status'] in TERMINAL_STATUSES:
                        ids_to_remove.append(req_id)

            # Remove finished / not-found IDs
            for rid in ids_to_remove:
                if rid in active_ids:
                    active_ids.remove(rid)
                    print(
                        f"[{ts()}] {rid} reached terminal status: "
                        f"{baselines.get(rid, {}).get('status', '?')}",
                        file=sys.stderr, flush=True,
                    )

            # Deliver events
            if all_events:
                self.state.write(last_poll_at=now_iso(), last_event_at=now_iso())
                delivered = self._deliver_events(all_events, active_ids)
                if not delivered:
                    restart_cmd = self._build_restart_cmd(active_ids)
                    if isinstance(self.bridge, TmuxBridge):
                        pane = self.bridge.tmux_pane if self.bridge else '?'
                        print(
                            f"tmux pane {pane} unreachable. Check pane ID and re-launch:\n"
                            f"  {restart_cmd}",
                            file=sys.stderr, flush=True,
                        )
                    else:
                        surface_id = self.bridge.surface_id if self.bridge else '?'
                        print(
                            f"Surface {surface_id} unreachable. Get fresh refs via `cmux identify --json` and re-launch:\n"
                            f"  {restart_cmd}",
                            file=sys.stderr, flush=True,
                        )
                    _remove_pid_file(self.watcher_id)
                    sys.exit(1)
                # long-poll-with-exit exits after first delivery
                if self.mode == 'long-poll-with-exit':
                    _remove_pid_file(self.watcher_id)
                    return
            else:
                self.state.write(last_poll_at=now_iso())

            # Heartbeat every 5 minutes
            now_mono = time.monotonic()
            if now_mono - last_heartbeat >= _HEARTBEAT_INTERVAL:
                print(
                    f"[{ts()}] Watching {len(active_ids)} request(s) -- no changes "
                    f"(poll_interval={self.poll_interval}s)",
                    file=sys.stderr, flush=True,
                )
                last_heartbeat = now_mono

            # Hourly version drift check
            if now_mono - last_version_check >= _VERSION_CHECK_INTERVAL:
                _check_version_drift()
                last_version_check = now_mono

        # All requests reached terminal state or signal received
        if not active_ids:
            done_msg = (
                f"{_pfx()} All watched requests reached terminal status. "
                f"Watcher {self.watcher_id} exiting."
            )
            print(done_msg, file=sys.stderr, flush=True)
            if self.mode == 'cmux-keystrokes' and self.bridge:
                self.bridge.send_to_claude(done_msg)
        else:
            sig = self._received_signal or 'signal'
            restart_cmd = self._build_restart_cmd(active_ids)
            print(
                f"[Quota Watcher {_ver()}] Exiting ({sig}).\n"
                f"Re-launch:\n  {restart_cmd}",
                file=sys.stderr, flush=True,
            )

        self.state.write(current_status='WATCHER_STOPPED')
        _remove_pid_file(self.watcher_id)

    def _build_restart_cmd(self, remaining_ids: list) -> str:
        """Build a minimal re-launch command string."""
        import shlex
        ids_str = ' '.join(remaining_ids)
        cmd = (
            f"python3 {shlex.quote(__file__)} watch "
            f"--request-ids {ids_str} "
            f"--profile {shlex.quote(self.client.profile)} "
            f"--watcher-id {self.watcher_id} "
            f"--mode {self.mode} "
            f"--poll-interval-seconds {self.poll_interval}"
        )
        if self.client.region:
            cmd += f" --region {shlex.quote(self.client.region)}"
        if self.mode == 'cmux-keystrokes' and self.bridge and isinstance(self.bridge, CmuxBridge):
            cmd += f" --cmux-surface {shlex.quote(self.bridge.surface_id)}"
            if self.bridge.workspace_ref:
                cmd += f" --cmux-workspace {shlex.quote(self.bridge.workspace_ref)}"
        elif self.mode == 'tmux-keystrokes' and self.bridge and isinstance(self.bridge, TmuxBridge):
            cmd += f" --tmux-pane {shlex.quote(self.bridge.tmux_pane)}"
        socket_path = os.environ.get('CMUX_SOCKET_PATH', '')
        if socket_path:
            cmd = f'CMUX_SOCKET_PATH={shlex.quote(socket_path)} {cmd}'
        return cmd

    def _deliver_events(self, events: list, remaining_ids: list) -> bool:
        """Deliver events in the appropriate mode.

        Returns True on success (or long-poll-with-exit mode), False if cmux delivery fails.
        """
        if self.mode == 'long-poll-with-exit':
            restart_cmd = self._build_restart_cmd(remaining_ids or [e['request_id'] for e in events])
            output = {
                'events': events,
                'watcher_id': self.watcher_id,
                'instruction': (
                    f"Re-launch the watcher FIRST, then process events.\n{restart_cmd}"
                ),
            }
            print(json.dumps(output, indent=2))
            sys.stdout.flush()
            return True

        elif self.mode == 'cmux-keystrokes' and self.bridge:
            for event in events:
                if not self.bridge.send_to_claude(event['formatted']):
                    return False
                if self.bridge.enable_notify:
                    self.bridge.notify(
                        f"Quota {event['request_id'][:12]}",
                        event['summary'],
                    )
                status_key = f"quota-{event['request_id'][:8]}"
                new_status = event.get('new_status', '')
                if new_status == 'APPROVED':
                    self.bridge.set_status(status_key, 'APPROVED', color='#196F3D')
                elif new_status in ('DENIED', 'CASE_CLOSED', 'NOT_APPROVED'):
                    self.bridge.set_status(status_key, new_status, color='#B71C1C')
                elif new_status:
                    self.bridge.set_status(status_key, new_status)
        elif self.mode == 'tmux-keystrokes' and self.bridge:
            for event in events:
                if not self.bridge.send_to_claude(event['formatted']):
                    return False
        return True

    def _handle_timeout(self, active_ids: list):
        """Handle max-runtime expiry."""
        restart_cmd = self._build_restart_cmd(active_ids)
        timeout_msg = (
            f"{_pfx()} Timed out after "
            f"{self.max_runtime_seconds // 3600}h. "
            f"Still watching: {', '.join(active_ids)}. Re-launch: {restart_cmd}"
        )
        print(f"[{ts()}] TIMEOUT: {timeout_msg}", file=sys.stderr, flush=True)
        self.state.write(current_status='TIMEOUT')
        _remove_pid_file(self.watcher_id)

        if self.mode == 'long-poll-with-exit':
            print(json.dumps({
                'error': 'MAX_RUNTIME_EXCEEDED',
                'message': timeout_msg,
                'watcher_id': self.watcher_id,
                'instruction': f"Re-launch the watcher:\n{restart_cmd}",
            }))
            sys.exit(0)
        else:
            if self.bridge:
                self.bridge.send_to_claude(timeout_msg)


# ---------------------------------------------------------------------------
# Surface / workspace detection helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Subcommand: watch
# ---------------------------------------------------------------------------

def cmd_watch(args):
    poll_interval = args.poll_interval_seconds
    if poll_interval < 60:
        print("Error: --poll-interval-seconds must be at least 60.", file=sys.stderr)
        sys.exit(1)
    if poll_interval > 3600:
        print("Error: --poll-interval-seconds must be at most 3600.", file=sys.stderr)
        sys.exit(1)

    mode = args.mode
    watcher_id = args.watcher_id or os.urandom(4).hex()

    # Instance guard (only when resuming an existing watcher-id)
    if args.watcher_id:
        _check_instance_guard(watcher_id)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_pid_file(watcher_id)

    client = ServiceQuotaClient(profile=args.profile, region=args.region)

    # Discover request IDs if --all-pending
    if args.all_pending:
        print(f"[{ts()}] Discovering pending quota change requests...", file=sys.stderr, flush=True)
        try:
            pending = client.list_pending_changes()
        except Exception as e:
            err_str = str(e)
            _remove_pid_file(watcher_id)
            if any(k in err_str for k in ('ExpiredToken', 'InvalidClientTokenId', 'ExpiredTokenException')):
                print(json.dumps({
                    'error': 'CREDENTIAL_EXPIRED',
                    'message': err_str,
                    'watcher_id': watcher_id,
                    'instruction': "Refresh credentials then re-launch with --all-pending.",
                }))
                sys.exit(2)
            print(f"Error discovering pending requests: {e}", file=sys.stderr)
            sys.exit(1)

        request_ids = [r['Id'] for r in pending if r.get('Id')]
        if not request_ids:
            print("No pending quota change requests found (PENDING or CASE_OPENED).", file=sys.stderr)
            _remove_pid_file(watcher_id)
            sys.exit(0)
        print(
            f"[{ts()}] Found {len(request_ids)} pending request(s): {', '.join(request_ids)}",
            file=sys.stderr, flush=True,
        )
    else:
        request_ids = args.request_ids

    state = WatcherState(watcher_id)

    # Set up bridge
    bridge = None

    if mode == 'cmux-keystrokes':
        if not args.cmux_surface:
            print(
                "Error: --cmux-surface is required for --mode cmux-keystrokes.",
                file=sys.stderr,
            )
            _remove_pid_file(watcher_id)
            sys.exit(1)
        workspace_ref = args.cmux_workspace or _detect_workspace_ref()
        bridge = CmuxBridge(
            surface_id=args.cmux_surface,
            workspace_ref=workspace_ref,
            enable_notify=args.cmux_notify,
            enable_status=args.cmux_status,
        )

        state.write(
            watcher_id=watcher_id,
            profile=args.profile,
            region=args.region or '',
            mode=mode,
            surface_id=args.cmux_surface,
            workspace_ref=workspace_ref,
            poll_interval_seconds=poll_interval,
            started_at=now_iso(),
        )
    elif mode == 'tmux-keystrokes':
        if not args.tmux_pane:
            print(
                "Error: --tmux-pane is required for --mode tmux-keystrokes.",
                file=sys.stderr,
            )
            _remove_pid_file(watcher_id)
            sys.exit(1)
        bridge = TmuxBridge(tmux_pane=args.tmux_pane)

        state.write(
            watcher_id=watcher_id,
            profile=args.profile,
            region=args.region or '',
            mode=mode,
            surface_id=None,
            workspace_ref=None,
            tmux_pane=args.tmux_pane,
            poll_interval_seconds=poll_interval,
            started_at=now_iso(),
        )
    else:
        state.write(
            watcher_id=watcher_id,
            profile=args.profile,
            region=args.region or '',
            mode=mode,
            surface_id=None,
            workspace_ref=None,
            poll_interval_seconds=poll_interval,
            started_at=now_iso(),
        )

    # Startup banner
    print(f"Quota Request Watcher {_ver()} | ID: {watcher_id}", file=sys.stderr, flush=True)
    print(
        f"Mode: {mode} | Poll: {poll_interval}s | "
        f"Max runtime: {args.max_runtime_hours}h | "
        f"Region: {args.region or 'profile default'}",
        file=sys.stderr,
        flush=True,
    )
    print(f"Watching {len(request_ids)} request(s): {', '.join(request_ids)}", file=sys.stderr, flush=True)
    print(f"State file: {state.path}", file=sys.stderr, flush=True)
    if mode == 'cmux-keystrokes':
        print(f"Target surface: {args.cmux_surface}", file=sys.stderr, flush=True)
    elif mode == 'tmux-keystrokes':
        print(f"Target tmux pane: {args.tmux_pane}", file=sys.stderr, flush=True)
    print(file=sys.stderr, flush=True)

    watcher = QuotaRequestWatcher(
        client=client,
        state=state,
        bridge=bridge,
        mode=mode,
        poll_interval=poll_interval,
        max_runtime_hours=args.max_runtime_hours,
        watcher_id=watcher_id,
    )

    watcher.run(request_ids)


# ---------------------------------------------------------------------------
# Subcommand: status
# ---------------------------------------------------------------------------

def cmd_status(args):
    """Print watcher state (specific watcher or list all)."""
    if args.watcher_id:
        state = WatcherState(args.watcher_id)
        data = state.read()
        if not data:
            print(f"No state file found for watcher ID: {args.watcher_id}")
            sys.exit(1)
        _print_watcher_detail(data)
        return

    # Default: list all
    watchers = WatcherState.list_all()
    if not watchers:
        print("No tracked quota request watchers found.")
        print(f"State directory: {STATE_DIR}")
        return

    print(f"{'WATCHER ID':<12} {'MODE':<22} {'REQS':<5} {'LAST POLL':<22} {'PID'}")
    print("-" * 80)
    for w in watchers:
        wid = w.get('watcher_id', '?')[:11]
        wmode = w.get('mode', '?')[:21]
        reqs = len(w.get('request_ids', []))
        last_poll = (w.get('last_poll_at', 'never') or 'never')[:21]
        pid = w.get('monitor_pid')
        pid_str = f"PID {pid} ({'alive' if _pid_alive(pid) else 'dead'})" if pid else "none"
        print(f"{wid:<12} {wmode:<22} {reqs:<5} {last_poll:<22} {pid_str}")
        for rid in w.get('request_ids', [])[:3]:
            snap = w.get('requests', {}).get(rid, {})
            qname = snap.get('quota_name', rid)[:40]
            status = snap.get('status', '?')
            print(f"  {rid} | {qname} | {status}")
        if len(w.get('request_ids', [])) > 3:
            print(f"  ... and {len(w.get('request_ids', [])) - 3} more")


def _print_watcher_detail(data: dict):
    print(f"Watcher ID:    {data.get('watcher_id', '?')}")
    print(f"Mode:          {data.get('mode', '?')}")
    print(f"Profile:       {data.get('profile', '?')}")
    print(f"Region:        {data.get('region') or 'profile default'}")
    print(f"Poll interval: {data.get('poll_interval_seconds', '?')}s")
    print(f"Started at:    {data.get('started_at', '?')}")
    print(f"Last poll:     {data.get('last_poll_at', 'never')}")
    pid = data.get('monitor_pid')
    if pid:
        alive = _pid_alive(pid)
        print(f"PID:           {pid} ({'alive' if alive else 'dead'})")
    request_ids = data.get('request_ids', [])
    print(f"Request IDs:   {', '.join(request_ids) or 'none'}")
    requests = data.get('requests', {})
    if requests:
        print("Request state:")
        for req_id, snap in requests.items():
            print(
                f"  {req_id}: {snap.get('service_name', '?')} / {snap.get('quota_name', '?')} "
                f"| desired={snap.get('desired_value', '?')} | status={snap.get('status', '?')}"
            )


# ---------------------------------------------------------------------------
# Subcommand: stop
# ---------------------------------------------------------------------------

def cmd_stop(args):
    """Stop a running watcher by sending SIGTERM to its PID."""
    if args.list:
        watchers = WatcherState.list_all()
        if not watchers:
            print("No tracked quota request watchers found.")
            return
        alive = [w for w in watchers if _pid_alive(w.get('monitor_pid'))]
        if not alive:
            print("No live watchers found.")
            return
        print("Live watchers:")
        for w in alive:
            print(
                f"  {w.get('watcher_id')}  mode={w.get('mode')}  "
                f"pid={w.get('monitor_pid')}  requests={w.get('request_ids', [])}"
            )
        return

    if not args.watcher_id:
        print("Error: --watcher-id is required (or use --list).", file=sys.stderr)
        sys.exit(1)

    state = WatcherState(args.watcher_id)
    data = state.read()
    if not data:
        print(f"No state file found for watcher ID: {args.watcher_id}", file=sys.stderr)
        sys.exit(1)

    pid = data.get('monitor_pid')
    if not pid:
        print("No watcher PID in state file.", file=sys.stderr)
        sys.exit(1)

    if not _pid_alive(pid):
        print(f"PID {pid} is not running (already stopped).")
        state.write(current_status='WATCHER_STOPPED')
        return

    os.kill(pid, signal.SIGTERM)
    state.write(current_status='WATCHER_STOPPED')
    print(f"Sent SIGTERM to PID {pid}. Watcher stopping.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Monitor AWS Service Quotas change requests for status changes.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch specific requests in long-poll-with-exit mode (default)
  watch_quota_requests.py watch --request-ids req-abc123 req-def456 --profile myprofile

  # Watch all pending requests
  watch_quota_requests.py watch --all-pending --profile myprofile

  # Resume a watcher after session restart
  watch_quota_requests.py watch --request-ids req-abc123 --profile myprofile --watcher-id a1b2c3d4

  # cmux-keystrokes mode (sends keystrokes on change)
  watch_quota_requests.py watch --request-ids req-abc123 --profile myprofile \\
      --mode cmux-keystrokes --cmux-surface surface:80

  # tmux-keystrokes mode (sends keystrokes to a tmux pane)
  watch_quota_requests.py watch --request-ids req-abc123 --profile myprofile \\
      --mode tmux-keystrokes --tmux-pane %0

  # List all tracked watchers
  watch_quota_requests.py status --list

  # Show specific watcher detail
  watch_quota_requests.py status --watcher-id a1b2c3d4

  # Stop a running watcher
  watch_quota_requests.py stop --watcher-id a1b2c3d4
        """,
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {_VERSION}')

    subparsers = parser.add_subparsers(dest='subcommand', metavar='SUBCOMMAND')
    subparsers.required = True

    # --- watch ---
    p_watch = subparsers.add_parser(
        'watch',
        help='Start quota request watcher',
    )
    id_group = p_watch.add_mutually_exclusive_group()
    id_group.add_argument(
        '--request-ids',
        nargs='+',
        metavar='REQUEST_ID',
        help='One or more AWS Service Quotas request IDs to watch.',
    )
    id_group.add_argument(
        '--all-pending',
        action='store_true',
        help='Discover and watch all non-terminal quota requests (PENDING or CASE_OPENED).',
    )
    p_watch.add_argument('--profile', required=True, help='AWS credentials profile')
    p_watch.add_argument('--region', default=None, help='AWS region (uses profile default if not set)')
    p_watch.add_argument(
        '--mode',
        choices=['long-poll-with-exit', 'cmux-keystrokes', 'tmux-keystrokes'],
        default='long-poll-with-exit',
        help='Delivery mode (default: long-poll-with-exit)',
    )
    p_watch.add_argument(
        '--poll-interval-seconds',
        type=int,
        default=600,
        metavar='SECONDS',
        help='Seconds between polls. Min 60, max 3600. Default: 600',
    )
    p_watch.add_argument(
        '--watcher-id',
        default='',
        help='8-char hex watcher ID. Auto-generated if omitted. Pass to resume a previous run.',
    )
    p_watch.add_argument(
        '--max-runtime-hours',
        type=int,
        default=24,
        metavar='HOURS',
        help='Maximum runtime before watcher exits and requests restart. Default: 24',
    )
    p_watch.add_argument(
        '--cmux-surface',
        default=None,
        help='cmux surface ref of the Claude Code session to notify (e.g. surface:80). '
             'Required for --mode cmux-keystrokes. Get from: cmux identify --json -> caller.surface_ref',
    )
    p_watch.add_argument(
        '--cmux-workspace',
        default=None,
        help='cmux workspace ref (e.g. workspace:47). Auto-detected via cmux identify if omitted.',
    )
    p_watch.add_argument(
        '--cmux-notify',
        action='store_true',
        help='Enable desktop notifications via cmux on status changes (cmux-keystrokes mode only)',
    )
    p_watch.add_argument(
        '--cmux-status',
        action='store_true',
        help='Enable cmux sidebar status badge updates (cmux-keystrokes mode only)',
    )
    p_watch.add_argument(
        '--tmux-pane',
        default=None,
        help='tmux pane ID to send keystrokes to (e.g. %%0). '
             'Required for --mode tmux-keystrokes. '
             "Get from: tmux display-message -p '#{pane_id}' or $TMUX_PANE",
    )
    # --- status ---
    p_status = subparsers.add_parser(
        'status',
        help='Show watcher state or list all tracked watchers',
    )
    p_status.add_argument(
        '--watcher-id',
        default='',
        help='Show specific watcher state file',
    )
    p_status.add_argument(
        '--list',
        action='store_true',
        help='List all tracked watchers (default if no flags)',
    )

    # --- stop ---
    p_stop = subparsers.add_parser(
        'stop',
        help='Stop a running quota request watcher',
    )
    p_stop.add_argument(
        '--watcher-id',
        default='',
        help='Watcher ID to stop (sends SIGTERM)',
    )
    p_stop.add_argument(
        '--list',
        action='store_true',
        help='List live watchers (does not stop anything)',
    )

    args = parser.parse_args()

    if _VERSION == 'unknown':
        print(
            "[Quota Watcher] WARNING: Running from source (version unknown). "
            "Version drift checks will be disabled.",
            file=sys.stderr, flush=True,
        )

    if args.subcommand == 'watch':
        cmd_watch(args)
    elif args.subcommand == 'status':
        cmd_status(args)
    elif args.subcommand == 'stop':
        cmd_stop(args)


if __name__ == '__main__':
    main()
