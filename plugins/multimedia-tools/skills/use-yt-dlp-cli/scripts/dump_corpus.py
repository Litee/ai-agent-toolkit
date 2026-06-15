#!/usr/bin/env python3
"""Build a JSONL corpus from a list of YouTube URLs.

Accepts channels, playlists, /@handle, /channel/UC…, ytsearch…, bare video IDs —
anything yt-dlp understands. Three modes:
  flat     — fast flat-playlist extraction (limited fields)
  full     — full per-video metadata via -j (all fields, slower)
  captions — flat metadata + raw VTT text per video (use 'convert-vtt-to-text' skill for plaintext)

Usage:
    python3 dump_corpus.py --urls-file FILE --mode flat --output-dir DIR [--limit N]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter, deque
from pathlib import Path
import yt_dlp


def _fmt_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Adaptive delay constants
# ---------------------------------------------------------------------------

_MAX_DELAY_SECS = 3600.0           # 1 hour hard ceiling

_SLOWDOWN_WINDOW = 10              # short window, reacts fast
_SLOWDOWN_MIN_SAMPLES = 5          # start evaluating once half-full
_SLOWDOWN_ERROR_RATE = 0.05        # >5% errors → grow delay
_SLOWDOWN_FACTOR = 1.5

_SPEEDUP_WINDOW = 100              # long window, reacts slow
_SPEEDUP_ERROR_RATE = 0.01         # <1% errors → shrink delay (effectively 0/100 samples)
_SPEEDUP_FACTOR = 0.9


class AdaptiveDelay:
    """Two-window adaptive request throttle.

    Backs off quickly on errors (short window) and recovers
    conservatively after sustained clean operation (long window).
    """

    def __init__(self, baseline: float) -> None:
        self.baseline = baseline
        self.delay = baseline
        self._short: "deque[bool]" = deque(maxlen=_SLOWDOWN_WINDOW)
        self._long: "deque[bool]" = deque(maxlen=_SPEEDUP_WINDOW)

    def record(self, ok: bool) -> None:
        self._short.append(ok)
        self._long.append(ok)

        # Slowdown check — fires fast, any error rate above threshold in last 10.
        if len(self._short) >= _SLOWDOWN_MIN_SAMPLES:
            short_errors = sum(1 for x in self._short if not x)
            if short_errors / len(self._short) > _SLOWDOWN_ERROR_RATE:
                self.delay = min(self.delay * _SLOWDOWN_FACTOR, _MAX_DELAY_SECS)
                return  # don't evaluate speedup on the same sample

        # Speedup check — requires full long window, resets on trigger.
        if len(self._long) == _SPEEDUP_WINDOW:
            long_errors = sum(1 for x in self._long if not x)
            if long_errors / _SPEEDUP_WINDOW < _SPEEDUP_ERROR_RATE and self.delay > self.baseline:
                self.delay = max(self.baseline, self.delay * _SPEEDUP_FACTOR)
                self._long.clear()

    def sleep(self) -> None:
        time.sleep(self.delay)


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

def _is_valid_url(raw: str) -> bool:
    return (
        "youtube.com/" in raw
        or "youtu.be/" in raw
        or raw.startswith("ytsearch")
    )


def _load_urls(urls_file: Path) -> tuple[list[str], list[str]]:
    """Return (valid_urls, skipped_lines)."""
    valid: list[str] = []
    skipped: list[str] = []
    for line in urls_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if _is_valid_url(line):
            valid.append(line)
        else:
            skipped.append(line)
    # Deduplicate preserving order.
    valid = list(dict.fromkeys(valid))
    return valid, skipped


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_processed(processed_file: Path) -> set[str]:
    if not processed_file.exists():
        return set()
    return set(line for line in processed_file.read_text().splitlines() if line)


def _append_line(path: Path, line: str) -> None:
    with path.open("a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Extraction modes
# ---------------------------------------------------------------------------

def _detect_yt_dlp() -> str:
    venv_bin = Path("/tmp/yt-tools-venv/bin/yt-dlp")
    if venv_bin.exists():
        return str(venv_bin)
    import shutil
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise RuntimeError(
        "yt-dlp not found. Install: python3 -m venv /tmp/yt-tools-venv && "
        "/tmp/yt-tools-venv/bin/pip install yt-dlp"
    )


def _fetch_flat(url: str) -> list[dict]:
    """Flat extraction — fast, limited fields."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "lazy_playlist": True,
        "skip_download": True,
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise RuntimeError("extract_info returned None")

    entries = []
    raw_entries = info.get("entries") or []
    # Single video (not a playlist) comes back directly.
    if not raw_entries and info.get("id"):
        raw_entries = [info]
    for entry in raw_entries:
        if not entry or not entry.get("id"):
            continue
        record = dict(entry)
        record.setdefault("source_url", url)
        record.setdefault("url", f"https://www.youtube.com/watch?v={entry['id']}")
        entries.append(record)
    return entries


def _fetch_full(url: str) -> list[dict]:
    """Full per-video metadata via dump-json."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise RuntimeError("extract_info returned None")

    entries = []
    raw_entries = info.get("entries") or []
    if not raw_entries and info.get("id"):
        raw_entries = [info]
    for entry in raw_entries:
        if not entry or not entry.get("id"):
            continue
        record = dict(entry)
        record.setdefault("source_url", url)
        entries.append(record)
    return entries


def _probe_video_captions(
    video_id: str,
    yt_dlp_bin: str,
) -> tuple:
    """Probe a video's caption metadata without downloading.

    Returns (info_dict, error_reason):
      - (info_dict, "")           — success: rc == 0 and stdout is parseable JSON
      - (None, "extraction_failed:<first line of stderr>")  — rc != 0 or JSON parse failed
      - (None, "timeout")         — TimeoutExpired
    """
    cmd = [
        yt_dlp_bin,
        "-J",
        "--skip-download",
        "--no-warnings",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "timeout"

    if result.returncode != 0:
        stderr_lines = [l for l in result.stderr.splitlines() if l.strip()]
        first_err = stderr_lines[0] if stderr_lines else "unknown error"
        # Strip "ERROR: " prefix if present
        if first_err.startswith("ERROR: "):
            first_err = first_err[len("ERROR: "):]
        return None, f"extraction_failed:{first_err}"

    try:
        info_dict = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return None, f"extraction_failed:JSON parse error: {e}"

    return info_dict, ""


def _fetch_captions_for_entry(
    video_id: str,
    sub_langs: str,
    yt_dlp_bin: str,
) -> tuple:
    """Download captions for one video ID.

    Returns (caps_by_lang, status, had_transient_error, available_langs) where:
      - caps_by_lang          — dict of lang -> raw VTT text (may be empty)
      - status                — one of: "ok", "partial", "none", "language_mismatch",
                                "download_failed", "extraction_failed", "timeout"
      - had_transient_error   — True ONLY for "extraction_failed" and "timeout" statuses;
                                "download_failed" is False (probe succeeded, not a rate-limit)
      - available_langs       — sorted list of lang codes available on the video
                                (union of subtitles + automatic_captions keys) when
                                status is "language_mismatch", else []
    """
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,20}", video_id):
        return {}, "extraction_failed", True, []

    # Step 1: probe caption metadata
    info_dict, probe_error = _probe_video_captions(video_id, yt_dlp_bin)

    # Step 2: handle probe failure
    if info_dict is None:
        if probe_error.startswith("extraction_failed"):
            status = "extraction_failed"
        else:
            status = "timeout"
        return {}, status, True, []

    # Step 3: parse available captions from probe result
    subtitles = info_dict.get("subtitles") or {}
    automatic_captions = info_dict.get("automatic_captions") or {}

    # Step 4: build requested lang list
    requested = [lang.strip() for lang in sub_langs.split(",") if lang.strip()]

    # Step 5: determine which requested langs are available
    langs_to_download: set[str] = set()
    for lang in requested:
        if lang in subtitles or lang in automatic_captions:
            langs_to_download.add(lang)

    # Step 6: handle no downloadable langs
    if not langs_to_download:
        all_available = set(subtitles.keys()) | set(automatic_captions.keys())
        if not subtitles and not automatic_captions:
            return {}, "none", False, []
        else:
            # Either dict is non-empty but none match requested langs
            return {}, "language_mismatch", False, sorted(all_available)

    # Step 7: download VTT for langs_to_download in a single yt-dlp call
    caps_by_lang: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="yt-caps-", dir="/tmp") as tmp_str:
        tmp_dir = Path(tmp_str)
        sub_langs_arg = ",".join(sorted(langs_to_download))
        cmd = [
            yt_dlp_bin,
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", sub_langs_arg,
            "--sub-format", "vtt",
            "--no-warnings",
            "--quiet",
            "-o", str(tmp_dir / "%(id)s"),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return {}, "timeout", True, []

        for lang in langs_to_download:
            candidates = list(tmp_dir.glob(f"{video_id}.{lang}.*"))
            if candidates:
                caps_by_lang[lang] = candidates[0].read_text(encoding="utf-8", errors="replace")

    # Step 8: determine final status
    if not caps_by_lang:
        # Probe confirmed captions exist but download produced nothing (CDN gap, private endpoint).
        # Not a rate-limit signal — probe succeeded. Do not feed the throttle.
        return {}, "download_failed", False, []
    elif len(caps_by_lang) == len(langs_to_download):
        status = "ok"
    else:
        status = "partial"

    return caps_by_lang, status, False, []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a JSONL corpus from YouTube URLs."
    )
    parser.add_argument("--urls-file", required=True, type=Path)
    parser.add_argument(
        "--mode", choices=["flat", "full", "captions"], default="flat"
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sub-langs", default="en")
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Process at most N entries (after checkpoint filtering). Must be >= 1.",
    )
    parser.add_argument(
        "--only-captioned", action="store_true",
        help="Skip writing corpus rows for videos with captions_status 'none'.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")

    os.makedirs(args.output_dir, exist_ok=True)
    corpus_file = args.output_dir / "corpus.jsonl"
    processed_file = args.output_dir / "processed.txt"
    failed_file = args.output_dir / "failed.txt"
    skipped_file = args.output_dir / "skipped.txt"

    urls, skipped = _load_urls(args.urls_file)
    for s in skipped:
        print(f"  [skip] not a YouTube URL: {s}", file=sys.stderr)
        _append_line(skipped_file, s)

    print(f"Loaded {len(urls)} valid URLs ({len(skipped)} skipped)", file=sys.stderr)

    processed = set() if args.force else _load_processed(processed_file)
    remaining = [u for u in urls if u not in processed]
    print(f"Already processed: {len(processed)}, remaining: {len(remaining)}", file=sys.stderr)

    if args.limit is not None:
        remaining = remaining[: args.limit]
        print(f"[--limit] capped at {len(remaining)}", file=sys.stderr)

    if not remaining:
        print("Nothing to do.", file=sys.stderr)
        return

    yt_dlp_bin = None
    if args.mode == "captions":
        try:
            yt_dlp_bin = _detect_yt_dlp()
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    throttle = AdaptiveDelay(args.request_delay)
    elapsed_times: list[float] = []

    for i, url in enumerate(remaining, 1):
        label = f"[{i}/{len(remaining)}]"
        print(f"{label} {url} ...", end=" ", flush=True, file=sys.stderr)
        ok = True
        t0 = time.monotonic()
        try:
            if args.mode == "flat":
                entries = _fetch_flat(url)
            elif args.mode == "full":
                entries = _fetch_full(url)
            else:  # captions
                entries = _fetch_flat(url)

            if args.mode == "captions":
                if not entries:
                    ok = False  # zero entries = likely silent throttle
                has_transient = not entries  # empty batch = silent throttle, must retry
                for entry in entries:
                    vid = entry.get("id")
                    if vid:
                        caps, cap_status, cap_transient, available_langs = _fetch_captions_for_entry(
                            vid, args.sub_langs, yt_dlp_bin  # type: ignore[arg-type]
                        )
                        if cap_transient:
                            ok = False
                            has_transient = True
                        entry["captions_status"] = cap_status
                        if caps:
                            entry["captions_vtt"] = caps
                        if available_langs:
                            entry["captions_available_langs"] = available_langs

                with corpus_file.open("a") as f:
                    for entry in entries:
                        if args.only_captioned and entry.get("captions_status") == "none":
                            continue
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                if has_transient:
                    _append_line(failed_file, f"{url}\tCaptions extraction failed")
                else:
                    _append_line(processed_file, url)
            else:
                with corpus_file.open("a") as f:
                    for entry in entries:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

                _append_line(processed_file, url)

            elapsed_times.append(time.monotonic() - t0)
            remaining_after = len(remaining) - i
            avg = sum(elapsed_times) / len(elapsed_times)
            eta = avg * remaining_after + throttle.delay * remaining_after
            eta_str = f" | ETA {_fmt_eta(eta)}" if remaining_after else ""
            if args.mode == "captions":
                counts = Counter(e.get("captions_status", "?") for e in entries)
                status_summary = " ".join(
                    f"caps={s}×{n}" if n > 1 else f"caps={s}"
                    for s, n in sorted(counts.items())
                )
                print(f"{len(entries)} entries | {status_summary}{eta_str}", file=sys.stderr)
            else:
                print(f"{len(entries)} entries{eta_str}", file=sys.stderr)
        except Exception as e:
            ok = False
            elapsed_times.append(time.monotonic() - t0)
            msg = str(e).replace("\n", " ")
            print(f"ERROR: {msg}", file=sys.stderr)
            _append_line(failed_file, f"{url}\t{msg}")

        prev = throttle.delay
        throttle.record(ok)
        if throttle.delay != prev:
            print(
                f"[throttle] {prev:.1f}s → {throttle.delay:.1f}s",
                file=sys.stderr,
            )

        if i < len(remaining):
            throttle.sleep()

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
