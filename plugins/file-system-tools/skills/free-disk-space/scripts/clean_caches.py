#!/usr/bin/env python3
"""
clean_caches.py — Report disk usage and optionally clean development caches.

Covers three types of targets:
  cli     — package manager CLIs with built-in clean commands (npm, pip, yarn,
            pnpm, go, brew, rustup, docker)
  dir     — cache directories with no CLI support, cleaned via directory removal
            (claude-code-debug, maven, gradle, jetbrains, xcode, vscode)
  scan    — directories discovered by recursive scan under --scan-root
            (node_modules)

Normal workflow:
    python3 clean_caches.py          # Step 1: report all sizes (safe, no deletion)
    python3 clean_caches.py --apply  # Step 2: run full cleanup

Special cases (restrict to specific targets):
    python3 clean_caches.py --target npm gradle          # report only
    python3 clean_caches.py --apply --target npm gradle  # clean only those targets

Scan targets (require --scan-root):
    python3 clean_caches.py --target node_modules --scan-root ~/projects
    python3 clean_caches.py --apply --target node_modules --scan-root ~/projects
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

PROGRESS_INTERVAL_SECS = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_dir_size(path: Path) -> int:
    """Return total size of directory in bytes. Returns 0 if path does not exist."""
    if not path.exists():
        return 0
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_size(size_bytes: float) -> str:
    """Format byte count as human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def which(cmd: str) -> bool:
    """Return True if cmd is available on PATH."""
    return shutil.which(cmd) is not None


def run_cli(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a CLI command, streaming output unless capture=True."""
    return subprocess.run(
        args,
        capture_output=capture,
        text=True,
    )


def disk_free(path: str = "/") -> int:
    """Return free bytes on the filesystem containing path."""
    try:
        st = shutil.disk_usage(path)
        return st.free
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Progress heartbeat
# ---------------------------------------------------------------------------

class ProgressPrinter:
    """Prints a 'still running' message every PROGRESS_INTERVAL_SECS seconds."""

    def __init__(self, label: str) -> None:
        self._label = label
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(PROGRESS_INTERVAL_SECS):
            elapsed = int(time.monotonic() - self._start_time)
            print(f"  [still running: {self._label} ({elapsed}s elapsed)]", flush=True)


# ---------------------------------------------------------------------------
# Target definitions
# ---------------------------------------------------------------------------

def build_cli_targets() -> list[dict]:
    """
    CLI-based targets: package managers with their own clean commands.
    Each entry: name, description, cmd (availability check binary), clean_cmd (list).
    """
    is_mac = platform.system() == "Darwin"

    targets = [
        {
            # https://docs.npmjs.com/cli/commands/npm-cache
            "name": "npm",
            "description": "npm cache (~/.npm)",
            "cmd": "npm",
            "size_paths": [Path.home() / ".npm"],
            "clean_cmds": [["npm", "cache", "clean", "--force"]],
        },
        {
            # https://pip.pypa.io/en/stable/cli/pip_cache/
            "name": "pip",
            "description": "pip cache (~/.cache/pip or ~/Library/Caches/pip)",
            "cmd": "pip",
            "size_paths": [
                Path.home() / "Library" / "Caches" / "pip" if is_mac
                else Path.home() / ".cache" / "pip"
            ],
            "clean_cmds": [["pip", "cache", "purge"]],
        },
        {
            # https://classic.yarnpkg.com/en/docs/cli/cache/
            "name": "yarn",
            "description": "Yarn cache",
            "cmd": "yarn",
            "size_paths": [],  # yarn reports its own cache location
            "clean_cmds": [["yarn", "cache", "clean"]],
        },
        {
            # https://pnpm.io/cli/store
            "name": "pnpm",
            "description": "pnpm store",
            "cmd": "pnpm",
            "size_paths": [],
            "clean_cmds": [["pnpm", "store", "prune"]],
        },
        {
            # https://pkg.go.dev/cmd/go#hdr-Remove_cached_files
            "name": "go",
            "description": "Go build and module caches (~/.cache/go)",
            "cmd": "go",
            "size_paths": [
                Path.home() / "Library" / "Caches" / "go" if is_mac
                else Path.home() / ".cache" / "go"
            ],
            "clean_cmds": [
                ["go", "clean", "-cache"],
                ["go", "clean", "-modcache"],
            ],
        },
        {
            # https://docs.brew.sh/Manpage#cleanup-options-formulaecask-
            "name": "brew",
            "description": "Homebrew cache (~/Library/Caches/Homebrew)",
            "cmd": "brew",
            "size_paths": [Path.home() / "Library" / "Caches" / "Homebrew"],
            "clean_cmds": [["brew", "cleanup", "--prune=all"]],
        },
        {
            # https://rust-lang.github.io/rustup/concepts/toolchains.html
            "name": "rustup",
            "description": "Unused Rust toolchains (~/.rustup/toolchains)",
            "cmd": "rustup",
            "size_paths": [Path.home() / ".rustup" / "toolchains"],
            "clean_cmds": None,  # interactive: list and remove manually
            "list_cmd": ["rustup", "toolchain", "list"],
            "manual_note": (
                "Run `rustup toolchain list` and remove unused toolchains with "
                "`rustup toolchain remove <name>`"
            ),
        },
        {
            # https://docs.docker.com/engine/manage-resources/pruning/
            "name": "docker",
            "description": "Docker stopped containers, dangling images, build cache",
            "cmd": "docker",
            "size_paths": [],
            "clean_cmds": [["docker", "system", "prune", "--force"]],
        },
    ]
    return targets


def build_dir_targets() -> list[dict]:
    """
    Directory-based targets: caches with no CLI, removed directly.
    Each entry: name, description, paths (list of Path).
    """
    home = Path.home()
    is_mac = platform.system() == "Darwin"

    targets = [
        {
            # https://docs.anthropic.com/en/docs/claude-code/settings
            "name": "claude-code-debug",
            "description": "Claude Code debug logs (~/.claude/debug)",
            "paths": [home / ".claude" / "debug"],
        },
        {
            # https://maven.apache.org/guides/introduction/introduction-to-repositories.html
            "name": "maven",
            "description": "Maven local repository (~/.m2/repository)",
            "paths": [home / ".m2" / "repository"],
        },
        {
            # https://docs.gradle.org/current/userguide/directory_layout.html#dir:gradle_user_home
            "name": "gradle",
            "description": "Gradle caches and wrapper distributions",
            "paths": [
                home / ".gradle" / "caches",
                home / ".gradle" / "wrapper" / "dists",
            ],
        },
    ]

    if is_mac:
        targets += [
            {
                # https://www.jetbrains.com/help/idea/directories-used-by-the-ide-to-store-settings-caches-plugins-and-logs.html
                "name": "jetbrains",
                "description": "JetBrains IDE caches (~/Library/Caches/JetBrains)",
                "paths": [home / "Library" / "Caches" / "JetBrains"],
            },
            {
                # https://developer.apple.com/documentation/xcode/build-system
                "name": "xcode",
                "description": "Xcode DerivedData (build intermediates)",
                "paths": [
                    home / "Library" / "Developer" / "Xcode" / "DerivedData",
                ],
            },
            {
                # https://code.visualstudio.com/docs/editor/extension-marketplace#_where-are-extensions-installed
                "name": "vscode",
                "description": "VSCode Cache, CachedData, CachedExtensions",
                "paths": [
                    home / "Library" / "Application Support" / "Code" / "Cache",
                    home / "Library" / "Application Support" / "Code" / "CachedData",
                    home / "Library" / "Application Support" / "Code" / "CachedExtensions",
                ],
            },
        ]
    else:
        targets += [
            {
                # https://www.jetbrains.com/help/idea/directories-used-by-the-ide-to-store-settings-caches-plugins-and-logs.html
                "name": "jetbrains",
                "description": "JetBrains IDE caches (~/.cache/JetBrains)",
                "paths": [home / ".cache" / "JetBrains"],
            },
            {
                # https://code.visualstudio.com/docs/editor/extension-marketplace#_where-are-extensions-installed
                "name": "vscode",
                "description": "VSCode cache (~/.config/Code/Cache, ~/.config/Code/CachedData)",
                "paths": [
                    home / ".config" / "Code" / "Cache",
                    home / ".config" / "Code" / "CachedData",
                    home / ".config" / "Code" / "CachedExtensions",
                ],
            },
        ]

    return targets


def build_scan_targets() -> list[dict]:
    """
    Scan-based targets: directories discovered by recursive scan under --scan-root.
    Each entry: name, description, pattern (the directory name to match).
    """
    return [
        {
            "name": "node_modules",
            "description": "npm/yarn/pnpm dependency directories (recursive scan under --scan-root)",
            "pattern": "node_modules",
        },
    ]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    cli_rows: list[tuple],
    dir_rows: list[tuple],
    scan_rows: list[tuple],
    free_before: int,
) -> None:
    # scan_rows tuples: (name, description, total_size, found_dirs_list)
    scan_summary_rows = [(name, desc, size, None) for name, desc, size, _ in scan_rows]
    all_rows = cli_rows + dir_rows + scan_summary_rows
    if not all_rows:
        print("No targets found.")
        return

    name_col = max(len(r[0]) for r in all_rows) + 2
    size_col = 12
    sep = "-" * (name_col + size_col + 4 + 50)

    total = sum(r[2] for r in all_rows)

    print(f"{'Target':<{name_col}} {'Size':>{size_col}}  Description")
    print(sep)

    if cli_rows:
        print("  [CLI-managed caches]")
        for name, desc, size, extra in cli_rows:
            not_installed = isinstance(extra, str) and extra == "not installed"
            manual_note = isinstance(extra, str) and extra not in ("not installed", "")
            size_str = "not installed" if not_installed else format_size(size)
            print(f"{name:<{name_col}} {size_str:>{size_col}}  {desc}")
            if manual_note:
                print(f"{'':<{name_col + size_col + 4}}  NOTE: {extra}")

    if dir_rows:
        print("  [Directory caches]")
        for name, desc, size, _ in dir_rows:
            marker = " (not found)" if size == 0 else ""
            print(f"{name:<{name_col}} {format_size(size):>{size_col}}  {desc}{marker}")

    if scan_rows:
        print("  [Scan targets]")
        for name, desc, size, found_dirs in scan_rows:
            count = len(found_dirs)
            suffix = f" ({count} found)" if count else " (none found)"
            print(f"{name:<{name_col}} {format_size(size):>{size_col}}  {desc}{suffix}")
            for d in found_dirs:
                indent = "    "
                print(f"{indent}{format_size(d['size_bytes']):>{size_col - len(indent)}}  {d['path']}")

    print(sep)
    print(f"{'TOTAL':<{name_col}} {format_size(total):>{size_col}}")
    print(f"\nCurrent free disk space: {format_size(free_before)}")
    print()


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def measure_cli_rows(targets: list[dict]) -> list[tuple]:
    rows = []
    for t in targets:
        if not which(t["cmd"]):
            rows.append((t["name"], t["description"], 0, "not installed"))
            continue
        size = sum(get_dir_size(p) for p in t.get("size_paths", []) if p.exists())
        manual_note = t.get("manual_note", "")
        rows.append((t["name"], t["description"], size, manual_note))
    return rows


def measure_dir_rows(targets: list[dict]) -> list[tuple]:
    rows = []
    for t in targets:
        size = sum(get_dir_size(p) for p in t["paths"])
        rows.append((t["name"], t["description"], size, t["paths"]))
    return rows


def _import_scanner():
    """Import scan functions from sibling scan_bloat.py script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from scan_bloat import dir_size, scan_tree, ProgressPrinter as ScanProgress
    return dir_size, scan_tree, ScanProgress


def measure_scan_rows(targets: list[dict], scan_root: str) -> list[tuple]:
    """
    Scan for directories matching scan targets under scan_root.
    Returns list of tuples: (name, description, total_size, found_dirs)
    where found_dirs is a list of {"path": str, "size_bytes": int, ...}.
    """
    _, scan_tree_fn, ScanProgress = _import_scanner()

    errors: list = []
    progress = ScanProgress()
    progress.start()
    try:
        results = scan_tree_fn(scan_root, False, progress, errors)
    finally:
        progress.stop()

    if errors:
        for e in errors:
            print(f"  WARNING: scan error at {e['path']}: {e['error']}", file=sys.stderr)

    rows = []
    for t in targets:
        matched = [r for r in results if r["type"] == t["pattern"]]
        matched.sort(key=lambda r: r["size_bytes"], reverse=True)
        total_size = sum(r["size_bytes"] for r in matched)
        rows.append((t["name"], t["description"], total_size, matched))
    return rows


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def clean_cli_target(t: dict) -> bool:
    """Run clean commands for a CLI target. Returns True on success."""
    if t.get("clean_cmds") is None:
        # manual-only target (e.g. rustup)
        print(f"  NOTE: {t.get('manual_note', 'manual cleanup required')}")
        return True

    ok = True
    for cmd in t["clean_cmds"]:
        print(f"  $ {' '.join(cmd)}")
        result = run_cli(cmd)
        if result.returncode != 0:
            print(f"  WARNING: command exited with code {result.returncode}", file=sys.stderr)
            ok = False
    return ok


def clean_dir_target(t: dict) -> int:
    """Remove cache directories. Returns bytes freed."""
    freed = 0
    for path in t["paths"]:
        if not path.exists():
            continue
        size = get_dir_size(path)
        try:
            shutil.rmtree(path)
            freed += size
            print(f"  Deleted: {path} ({format_size(size)})")
        except (OSError, PermissionError) as exc:
            print(f"  ERROR deleting {path}: {exc}", file=sys.stderr)
    return freed


def clean_scan_target(found_dirs: list[dict]) -> int:
    """Remove scanned directories. Returns bytes freed."""
    freed = 0
    for entry in found_dirs:
        path = entry["path"]
        size = entry["size_bytes"]
        try:
            shutil.rmtree(path)
            freed += size
            print(f"  Deleted: {path} ({format_size(size)})")
        except (OSError, PermissionError) as exc:
            print(f"  ERROR deleting {path}: {exc}", file=sys.stderr)
    return freed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report disk usage and optionally clean development caches.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually run cleanups (default: report sizes only, no deletion).",
    )
    parser.add_argument(
        "--target",
        nargs="+",
        metavar="TARGET",
        help="Restrict to specific targets (e.g. --target npm gradle). "
             "Omit to report or clean everything.",
    )
    parser.add_argument(
        "--scan-root",
        metavar="PATH",
        help="Root directory for scan-based targets (e.g. node_modules). "
             "Required when --target includes scan targets like 'node_modules'.",
    )
    args = parser.parse_args()

    all_cli = build_cli_targets()
    all_dir = build_dir_targets()
    all_scan = build_scan_targets()
    all_names = [t["name"] for t in all_cli + all_dir + all_scan]

    if args.target:
        unknown = set(args.target) - set(all_names)
        if unknown:
            print(f"Unknown targets: {', '.join(sorted(unknown))}", file=sys.stderr)
            print(f"Available: {', '.join(all_names)}", file=sys.stderr)
            sys.exit(1)
        cli_targets = [t for t in all_cli if t["name"] in args.target]
        dir_targets = [t for t in all_dir if t["name"] in args.target]
        scan_targets = [t for t in all_scan if t["name"] in args.target]
    else:
        cli_targets = all_cli
        dir_targets = all_dir
        scan_targets = []  # opt-in only: require explicit --target

    if scan_targets and not args.scan_root:
        scan_names = [t["name"] for t in scan_targets]
        print(
            f"Error: --scan-root is required when targeting: {', '.join(scan_names)}",
            file=sys.stderr,
        )
        print("Example: --scan-root ~/projects", file=sys.stderr)
        sys.exit(1)

    print()
    if args.apply:
        print("Mode: APPLY — cleanups will be executed")
    else:
        print("Mode: REPORT ONLY — no files will be deleted (pass --apply to clean)")
    print()

    free_before = disk_free()

    print("Measuring cache sizes...")
    progress = ProgressPrinter("measuring")
    progress.start()
    cli_rows = measure_cli_rows(cli_targets)
    dir_rows = measure_dir_rows(dir_targets)
    progress.stop()
    print()

    scan_rows: list[tuple] = []
    if scan_targets:
        scan_root = os.path.realpath(args.scan_root)
        if not os.path.isdir(scan_root):
            print(f"Error: --scan-root {args.scan_root!r} is not a directory", file=sys.stderr)
            sys.exit(1)
        print(f"Scanning {scan_root} for scan targets...")
        scan_rows = measure_scan_rows(scan_targets, scan_root)
        print()

    print_report(cli_rows, dir_rows, scan_rows, free_before)

    if not args.apply:
        print("Run with --apply to clean everything above.")
        return

    # --- CLI cleanups ---
    cli_by_name = {t["name"]: t for t in cli_targets}
    for name, _, size, extra in cli_rows:
        if isinstance(extra, str) and extra in ("not installed", "not available"):
            print(f"Skipping {name}: {extra}")
            continue
        t = cli_by_name[name]
        print(f"\nCleaning {name}...")
        progress = ProgressPrinter(name)
        progress.start()
        clean_cli_target(t)
        progress.stop()

    # --- Directory cleanups ---
    dir_by_name = {t["name"]: t for t in dir_targets}
    freed_dirs = 0
    for row in dir_rows:
        name, size = row[0], row[2]
        if size == 0:
            print(f"\nSkipping {name}: not found")
            continue
        t = dir_by_name[name]
        print(f"\nCleaning {name} ({format_size(size)})...")
        progress = ProgressPrinter(name)
        progress.start()
        freed_dirs += clean_dir_target(t)
        progress.stop()

    # --- Scan cleanups ---
    freed_scan = 0
    for name, _, size, found_dirs in scan_rows:
        if not found_dirs:
            print(f"\nSkipping {name}: none found")
            continue
        print(f"\nCleaning {name} ({format_size(size)}, {len(found_dirs)} directories)...")
        progress = ProgressPrinter(name)
        progress.start()
        freed_scan += clean_scan_target(found_dirs)
        progress.stop()

    free_after = disk_free()
    print(f"\nDone.")
    print(f"  Free disk space before: {format_size(free_before)}")
    print(f"  Free disk space after:  {format_size(free_after)}")
    if freed_dirs:
        print(f"  Freed (directories):    {format_size(freed_dirs)}")
    if freed_scan:
        print(f"  Freed (scan targets):   {format_size(freed_scan)}")


if __name__ == "__main__":
    main()
