#!/usr/bin/env python3
"""Convert a WebVTT file to deduplicated plaintext.

Usage:
    vtt_to_text.py INPUT.vtt [--keep-timestamps]

Reads INPUT.vtt, deduplicates overlapping cue lines (common in auto-generated
YouTube captions), and writes clean text to stdout.

With --keep-timestamps, each line is prefixed with [HH:MM:SS].
"""

import argparse
import re
import sys


_TIMESTAMP_LINE_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}"
)
_INLINE_TAG_RE = re.compile(r"<[^>]+>")
_CUE_TIMESTAMP_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.\d{3}\s+-->")


def _parse_cue_start(timestamp_line: str) -> str | None:
    """Extract HH:MM:SS from a cue timestamp line, or None."""
    m = _CUE_TIMESTAMP_RE.match(timestamp_line.strip())
    if m:
        return f"{m.group(1)}:{m.group(2)}:{m.group(3)}"
    return None


def vtt_to_text(vtt_text: str, keep_timestamps: bool = False) -> str:
    """Convert VTT caption string to deduplicated plaintext."""
    lines = vtt_text.splitlines()
    seen: set[str] = set()
    output: list[str] = []

    in_header = True
    current_cue_start: str | None = None

    for line in lines:
        if in_header:
            if line.strip() == "" or _TIMESTAMP_LINE_RE.match(line.strip()):
                in_header = False
            else:
                continue

        if _TIMESTAMP_LINE_RE.match(line.strip()):
            current_cue_start = _parse_cue_start(line)
            continue

        if not line.strip():
            continue

        clean = _INLINE_TAG_RE.sub("", line).strip()

        if not clean or clean.isdigit():
            continue

        if clean not in seen:
            seen.add(clean)
            if keep_timestamps and current_cue_start:
                output.append(f"[{current_cue_start}] {clean}")
            else:
                output.append(clean)

    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a WebVTT file to deduplicated plaintext."
    )
    parser.add_argument("input", metavar="INPUT.vtt", help="Path to input VTT file.")
    parser.add_argument(
        "--keep-timestamps",
        action="store_true",
        help="Prefix each line with [HH:MM:SS] from the cue start time.",
    )
    args = parser.parse_args()

    try:
        with open(args.input, encoding="utf-8") as fh:
            vtt_text = fh.read()
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(vtt_to_text(vtt_text, keep_timestamps=args.keep_timestamps))


if __name__ == "__main__":
    main()
