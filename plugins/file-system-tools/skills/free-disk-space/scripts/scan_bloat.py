#!/usr/bin/env python3
"""
scan_bloat.py — Scan a directory tree for known bloat directories.

Finds virtual environments, dependency caches, and build tool caches.
Reports full paths and sizes. Does not delete anything.

Usage:
    python3 scan_bloat.py --path ~/projects --output results.json
    python3 scan_bloat.py --path ~/projects --human
    python3 scan_bloat.py --path ~/projects --output results.json --human --min-size 100M
    python3 scan_bloat.py --path ~/projects --same-filesystem
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone


BLOAT_PATTERNS = frozenset([
    "node_modules",
    ".venv",
    "venv",
    ".virtualenv",
    ".next",
    ".nuxt",
    ".tox",
    ".turbo",
])

PROGRESS_INTERVAL_SECS = 2


def parse_size(value: str) -> int:
    """Parse a human size string (e.g. '100M', '1G') into bytes."""
    value = value.strip()
    suffixes = {
        "k": 1024, "kb": 1024,
        "m": 1024**2, "mb": 1024**2,
        "g": 1024**3, "gb": 1024**3,
        "t": 1024**4, "tb": 1024**4,
    }
    lower = value.lower()
    for suffix, multiplier in sorted(suffixes.items(), key=lambda x: -len(x[0])):
        if lower.endswith(suffix):
            try:
                return int(float(value[: -len(suffix)]) * multiplier)
            except ValueError:
                raise argparse.ArgumentTypeError(f"Invalid size: {value!r}")
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid size: {value!r}")


def format_size(size_bytes: float) -> str:
    """Format byte count as human-readable string.
    Copied from clean_caches.py for standalone use.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


class ProgressPrinter:
    """Prints a live count to stderr every PROGRESS_INTERVAL_SECS seconds."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._count = 0
        self._lock = threading.Lock()
        self._start_time: float = 0.0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def increment(self) -> None:
        with self._lock:
            self._count += 1

    def start(self) -> None:
        self._start_time = time.monotonic()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(PROGRESS_INTERVAL_SECS):
            with self._lock:
                count = self._count
            elapsed = int(time.monotonic() - self._start_time)
            print(f"  [scanning... found {count} directories ({elapsed}s elapsed)]",
                  file=sys.stderr, flush=True)


def dir_size(path: str) -> int:
    """Return total size of directory in bytes using os.scandir() for speed."""
    total = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        else:
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


def scan_tree(
    root: str,
    same_filesystem: bool,
    progress: ProgressPrinter,
    errors: list,
) -> list:
    """
    Walk the directory tree rooted at root, finding all BLOAT_PATTERNS directories.

    Returns a list of dicts: {path, type, size_bytes, size_human}.
    Populates errors list with {path, error} for permission errors.
    Does not descend into matched directories (prunes nested matches).
    """
    results = []
    visited = set()  # (dev, ino) pairs for cycle detection

    try:
        root_stat = os.stat(root)
    except OSError as exc:
        errors.append({"path": root, "error": str(exc)})
        return results

    root_dev = root_stat.st_dev
    visited.add((root_stat.st_dev, root_stat.st_ino))

    # Stack holds directory paths to visit
    stack = [root]

    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except PermissionError as exc:
            errors.append({"path": current, "error": str(exc)})
            continue
        except OSError as exc:
            errors.append({"path": current, "error": str(exc)})
            continue

        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            # Note: is_dir(follow_symlinks=False) already excludes symlinks to dirs;
            # non-symlink dirs pass through here.

            try:
                st = entry.stat(follow_symlinks=False)
            except OSError:
                continue

            # Skip .git early (large, never contains bloat we care about)
            if entry.name == ".git":
                continue

            # Enforce same-filesystem boundary before recording inode
            if same_filesystem and st.st_dev != root_dev:
                continue

            inode_key = (st.st_dev, st.st_ino)
            if inode_key in visited:
                continue  # cycle detected
            visited.add(inode_key)

            if entry.name in BLOAT_PATTERNS:
                # Found a bloat directory — measure it, do NOT descend
                size = dir_size(entry.path)
                progress.increment()
                results.append({
                    "path": entry.path,
                    "type": entry.name,
                    "size_bytes": size,
                    "size_human": format_size(size),
                })
            else:
                # Regular directory — push onto stack to continue traversal
                stack.append(entry.path)

    return results


def build_output(
    root: str,
    scan_start: datetime,
    scan_end: datetime,
    results: list,
    errors: list,
    args,
) -> dict:
    """Build the JSON output dict."""
    # Apply min-size filter
    filtered = results
    if args.min_size:
        filtered = [r for r in results if r["size_bytes"] >= args.min_size]

    # Sort
    if args.sort == "size":
        filtered.sort(key=lambda r: r["size_bytes"], reverse=True)
    else:
        filtered.sort(key=lambda r: r["path"])

    # Summary
    total_bytes = sum(r["size_bytes"] for r in filtered)
    largest = max(filtered, key=lambda r: r["size_bytes"]) if filtered else None

    def _utc_z(dt: datetime) -> str:
        """Format datetime as ISO 8601 with Z suffix (e.g. 2026-03-14T15:30:00Z)."""
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "scan_root": root,
        "scan_start": _utc_z(scan_start),
        "scan_end": _utc_z(scan_end),
        "parameters": {
            "min_size_bytes": args.min_size,
            "sort": args.sort,
            "same_filesystem": args.same_filesystem,
        },
        "directories": filtered,
        "errors": errors,
        "summary": {
            "total_count": len(filtered),
            "total_bytes": total_bytes,
            "total_human": format_size(total_bytes),
            "largest_path": largest["path"] if largest else None,
            "largest_bytes": largest["size_bytes"] if largest else None,
            "skipped_permission_errors": len(errors),
        },
    }


def print_human(output: dict) -> None:
    """Print a human-readable summary table to stdout."""
    dirs = output["directories"]
    summary = output["summary"]

    if not dirs:
        print("No bloat directories found.")
        return

    # Column widths
    max_path = max(len(r["path"]) for r in dirs)
    max_type = max(len(r["type"]) for r in dirs)
    path_w = max(max_path, 4)
    type_w = max(max_type, 4)
    size_w = 12

    header = f"  {'PATH':<{path_w}}  {'TYPE':<{type_w}}  {'SIZE':>{size_w}}"
    print()
    print(header)
    print("  " + "-" * (path_w + type_w + size_w + 4))
    for r in dirs:
        print(f"  {r['path']:<{path_w}}  {r['type']:<{type_w}}  {r['size_human']:>{size_w}}")

    print()
    print(f"  Found:   {summary['total_count']} directories")
    print(f"  Total:   {summary['total_human']}")
    if summary["largest_path"]:
        print(f"  Largest: {summary['largest_path']} ({format_size(summary['largest_bytes'])})")
    if output["errors"]:
        print(f"  Errors:  {len(output['errors'])} paths skipped (permission denied)")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan a directory tree for known bloat directories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--path", required=True, help="Root directory to scan")
    parser.add_argument("--output", help="Write JSON results to this file (default: stdout)")
    parser.add_argument("--human", action="store_true", help="Print human-readable table to stdout")
    parser.add_argument(
        "--sort",
        choices=["size", "name"],
        default="size",
        help="Sort results by size (desc) or name (asc) [default: size]",
    )
    parser.add_argument(
        "--min-size",
        type=parse_size,
        metavar="SIZE",
        help="Exclude directories smaller than SIZE (e.g. 10M, 1G)",
    )
    parser.add_argument(
        "--same-filesystem",
        action="store_true",
        help="Do not cross filesystem boundaries (avoids NFS/network mounts)",
    )
    args = parser.parse_args()

    root = os.path.realpath(args.path)
    if not os.path.isdir(root):
        print(f"Error: --path {args.path!r} is not a directory or does not exist", file=sys.stderr)
        sys.exit(1)

    errors: list = []
    progress = ProgressPrinter()
    scan_start = datetime.now(timezone.utc)

    print(f"Scanning {root}...", file=sys.stderr)
    progress.start()
    try:
        results = scan_tree(root, args.same_filesystem, progress, errors)
    finally:
        progress.stop()

    scan_end = datetime.now(timezone.utc)
    output = build_output(root, scan_start, scan_end, results, errors, args)

    # Determine output mode:
    # --output only     → JSON to file, nothing to stdout
    # --human only      → human table to stdout, no JSON
    # --output + --human → JSON to file, human table to stdout
    # neither           → JSON to stdout
    emit_json = args.output is not None or not args.human
    emit_human = args.human

    if emit_human:
        print_human(output)

    if emit_json:
        json_str = json.dumps(output, indent=2)
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_str)
                f.write("\n")
            print(
                f"Results written to {args.output} "
                f"({output['summary']['total_count']} directories, "
                f"{output['summary']['total_human']})",
                file=sys.stderr,
            )
        else:
            print(json_str)


if __name__ == "__main__":
    main()
