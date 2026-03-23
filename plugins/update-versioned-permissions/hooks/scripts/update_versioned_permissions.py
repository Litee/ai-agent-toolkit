#!/usr/bin/env python3
"""
Hook script that runs at SessionStart to auto-clone versioned plugin path entries
in Claude Code permissions when plugins have been upgraded to newer versions.

For each permission entry containing a versioned plugin path like:
  /plugins/cache/{marketplace}/{plugin_name}/{old_version}/...
it adds a new entry with the currently installed version if not already present.

This is additive-only — it never removes existing entries.
Also updates statusLine.command to the latest installed version if stale.
"""

import sys
import os
import re
import json
import fcntl
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field


VERSION_PATH_RE = re.compile(r'/plugins/cache/([^/]+)/([^/]+)/([^/]+)/')


@dataclass
class UpdateReport:
    """Report of permission entries added during the update."""
    # Maps (marketplace, plugin_name): list of (old_version, new_version) tuples
    added: dict = field(default_factory=dict)
    status_line_updated: tuple = field(default=None)  # (old_version, new_version, plugin_key)

    @property
    def total_added(self) -> int:
        return sum(len(pairs) for pairs in self.added.values())

    def record_add(self, marketplace: str, plugin_name: str, old_ver: str, new_ver: str) -> None:
        key = f"{plugin_name}@{marketplace}"
        if key not in self.added:
            self.added[key] = []
        pair = (old_ver, new_ver)
        if pair not in self.added[key]:
            self.added[key].append(pair)

    def print_summary(self) -> None:
        if self.total_added == 0 and self.status_line_updated is None:
            return

        parts = []
        for plugin_key, pairs in sorted(self.added.items()):
            # Collapse multiple version bumps to unique old→new pairs
            for old_ver, new_ver in pairs:
                parts.append(f"{plugin_key} ({old_ver}→{new_ver})")

        if self.status_line_updated:
            old_ver, new_ver, plugin_key = self.status_line_updated
            parts.append(f"statusLine {plugin_key} ({old_ver}→{new_ver})")

        if parts:
            if self.total_added > 0:
                print(f"Versioned permissions updated: added {self.total_added} entries for {', '.join(parts)}")
            else:
                print(f"Versioned permissions updated: {'; '.join(parts)}")


def build_version_map(installed_plugins_path: Path) -> dict:
    """
    Build a map of {(marketplace, plugin_name): list_of_install_entries}
    where each entry has 'version' and 'lastUpdated'.

    A plugin can appear multiple times (user scope + project scope at different versions).
    """
    version_map = {}

    try:
        with open(installed_plugins_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading installed_plugins.json: {e}", file=sys.stderr)
        return version_map

    plugins = data.get('plugins', {})
    for plugin_key, entries in plugins.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            install_path = entry.get('installPath', '')
            match = VERSION_PATH_RE.search(install_path + '/')
            if not match:
                continue
            marketplace = match.group(1)
            plugin_name = match.group(2)
            version = match.group(3)
            key = (marketplace, plugin_name)
            if key not in version_map:
                version_map[key] = []
            version_map[key].append({
                'version': version,
                'lastUpdated': entry.get('lastUpdated', ''),
            })

    return version_map


def parse_semver(version_str: str):
    """
    Parse a semver string into a tuple of ints for comparison.
    Returns None if it's not a valid semver (e.g. a git SHA).
    """
    parts = version_str.split('.')
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def get_latest_version(entries: list) -> str:
    """
    Given a list of install entries (each with 'version' and 'lastUpdated'),
    return the version string of the latest one.

    For semver versions: pick the highest semver.
    For non-semver (git SHAs etc.): pick the one with the most recent lastUpdated.
    Falls back to lastUpdated ordering if semver parsing fails for any entry.
    """
    if not entries:
        return None

    # Try semver comparison
    semver_entries = [(parse_semver(e['version']), e) for e in entries]
    if all(sv is not None for sv, _ in semver_entries):
        best = max(semver_entries, key=lambda x: x[0])
        return best[1]['version']

    # Fall back to lastUpdated
    try:
        best = max(entries, key=lambda e: e.get('lastUpdated', ''))
        return best['version']
    except (KeyError, TypeError):
        return entries[-1]['version']


def clone_versioned_entries(entries: list, version_map: dict, report: UpdateReport) -> tuple:
    """
    For each entry in the list, check if it contains a versioned plugin path.
    If so, add new entries for any installed versions that differ from the embedded one.

    Returns (new_entries_list, changed: bool).
    """
    existing_set = set(entries)
    additions = []

    for entry in list(entries):
        if not isinstance(entry, str):
            continue
        match = VERSION_PATH_RE.search(entry)
        if not match:
            continue
        marketplace = match.group(1)
        plugin_name = match.group(2)
        embedded_version = match.group(3)
        key = (marketplace, plugin_name)

        installed_entries = version_map.get(key)
        if not installed_entries:
            continue

        for install_entry in installed_entries:
            current_version = install_entry['version']
            if current_version == embedded_version:
                continue
            new_entry = entry.replace(
                f'/plugins/cache/{marketplace}/{plugin_name}/{embedded_version}/',
                f'/plugins/cache/{marketplace}/{plugin_name}/{current_version}/',
            )
            if new_entry not in existing_set and new_entry not in additions:
                additions.append(new_entry)
                existing_set.add(new_entry)
                report.record_add(marketplace, plugin_name, embedded_version, current_version)

    if additions:
        return entries + additions, True
    return entries, False


def update_status_line(settings_data: dict, version_map: dict, report: UpdateReport) -> bool:
    """
    If settings_data has a statusLine.command containing a versioned plugin path,
    update it to the latest installed version.

    Returns True if a change was made.
    """
    status_line = settings_data.get('statusLine')
    if not isinstance(status_line, dict):
        return False

    command = status_line.get('command')
    if not isinstance(command, str):
        return False

    match = VERSION_PATH_RE.search(command)
    if not match:
        return False

    marketplace = match.group(1)
    plugin_name = match.group(2)
    embedded_version = match.group(3)
    key = (marketplace, plugin_name)

    installed_entries = version_map.get(key)
    if not installed_entries:
        return False

    latest_version = get_latest_version(installed_entries)
    if latest_version == embedded_version:
        return False

    new_command = command.replace(
        f'/plugins/cache/{marketplace}/{plugin_name}/{embedded_version}/',
        f'/plugins/cache/{marketplace}/{plugin_name}/{latest_version}/',
    )
    settings_data['statusLine']['command'] = new_command
    report.status_line_updated = (embedded_version, latest_version, f"{plugin_name}@{marketplace}")
    return True


def acquire_lock(lock_file_path: Path, timeout_seconds: float = 2.0) -> object:
    """
    Acquire an exclusive flock on the lock file, with a timeout.
    Returns the open file object if successful, None if timed out.
    """
    import time
    import errno

    lock_file = open(lock_file_path, 'w', encoding='utf-8')
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_file
        except OSError as e:
            if e.errno not in (errno.EACCES, errno.EAGAIN):
                lock_file.close()
                raise
            if time.monotonic() >= deadline:
                lock_file.close()
                return None
            time.sleep(0.05)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Auto-clone versioned plugin path entries in Claude Code permissions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Update permissions (normal operation)
  %(prog)s --dry-run          # Preview changes without writing
        """
    )
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help='Preview changes without modifying settings file',
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()

    home = Path.home()
    installed_plugins_path = home / '.claude' / 'plugins' / 'installed_plugins.json'
    settings_path = home / '.claude' / 'settings.json'
    lock_path = home / '.claude' / 'settings.json.lock'

    # Exit silently if files don't exist
    if not installed_plugins_path.exists():
        sys.exit(0)
    if not settings_path.exists():
        sys.exit(0)

    # Build version map from installed_plugins.json
    version_map = build_version_map(installed_plugins_path)
    if not version_map:
        sys.exit(0)

    # Load settings.json
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"settings.json is malformed, skipping: {e}", file=sys.stderr)
        sys.exit(0)
    except OSError as e:
        print(f"Could not read settings.json: {e}", file=sys.stderr)
        sys.exit(0)

    report = UpdateReport()
    changed = False

    # Process permissions.allow
    permissions = settings_data.setdefault('permissions', {})
    allow_list = permissions.get('allow', [])
    new_allow, allow_changed = clone_versioned_entries(allow_list, version_map, report)
    if allow_changed:
        permissions['allow'] = sorted(new_allow)
        changed = True

    # Process permissions.deny
    deny_list = permissions.get('deny', [])
    new_deny, deny_changed = clone_versioned_entries(deny_list, version_map, report)
    if deny_changed:
        permissions['deny'] = sorted(new_deny)
        changed = True

    # Update statusLine.command
    if update_status_line(settings_data, version_map, report):
        changed = True

    if not changed:
        sys.exit(0)

    if args.dry_run:
        report.print_summary()
        sys.exit(0)

    # Acquire lock and write atomically
    lock_file = acquire_lock(lock_path)
    if lock_file is None:
        print("Could not acquire lock on settings.json within 2s, skipping update", file=sys.stderr)
        sys.exit(0)

    try:
        # Sort allow/deny that were already updated above
        # (sorted() was already applied; ensure deny was sorted too)
        if deny_changed and 'deny' in permissions:
            permissions['deny'] = sorted(permissions['deny'])

        tmp_path = settings_path.with_suffix('.json.tmp')
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
                f.write('\n')
            os.replace(tmp_path, settings_path)
        except OSError as e:
            print(f"Failed to write settings.json: {e}", file=sys.stderr)
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            sys.exit(0)
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

    report.print_summary()


if __name__ == '__main__':
    main()
