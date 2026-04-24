---
name: convert-vtt-to-text
description: Use when converting WebVTT caption/subtitle files (.vtt) to deduplicated plaintext, stripping inline formatting tags, dropping cue headers, and collapsing the overlapping-cue repetition that auto-generated captions produce. Optionally prefix each line with [HH:MM:SS]. Triggers on "convert vtt", "vtt to text", "webvtt to plaintext", "dedupe captions", "extract transcript from vtt", "captions to text", "strip vtt tags", "subtitle to text".
---

# Convert VTT to Text

Convert a WebVTT (`.vtt`) subtitle/caption file to clean, deduplicated plaintext using `scripts/vtt_to_text.py`.

## Purpose

WebVTT auto-generated captions (from video platforms, HLS streams, browser capture) commonly repeat the same line across several overlapping cue windows. Feeding a raw `.vtt` file to an LLM inflates token count by 3–5× and degrades readability. This script parses the file, strips inline tags (`<c>`, `<i>`, timestamps embedded in text), and deduplicates cues, emitting each unique line exactly once.

## When to use

- Any `.vtt` file where you want readable plaintext
- Post-processing auto-generated captions before feeding to an LLM or summarizer
- Extracting a timestamped transcript for search/indexing

## When NOT to use

- SRT, ASS, SSA, or other subtitle formats — this script only handles WebVTT
- Translation or re-timing — this is a format conversion only
- If you need the raw cue structure (start/end times per segment) — use the `.vtt` file directly

## Usage

```bash
# Basic: deduplicated plaintext on stdout
python3 ${SKILL_DIR}/scripts/vtt_to_text.py INPUT.vtt

# With timestamps: each line prefixed with [HH:MM:SS]
python3 ${SKILL_DIR}/scripts/vtt_to_text.py INPUT.vtt --keep-timestamps

# Redirect to file (zsh-safe)
python3 ${SKILL_DIR}/scripts/vtt_to_text.py INPUT.vtt >| /tmp/transcript.txt
python3 ${SKILL_DIR}/scripts/vtt_to_text.py INPUT.vtt --keep-timestamps >| /tmp/transcript_ts.txt
```

**No external dependencies** — stdlib only (`argparse`, `re`, `sys`). Works with any Python 3.10+.

## Getting VTT files

- **yt-dlp**: `yt-dlp --skip-download --write-auto-subs --sub-format vtt --sub-langs en -o /tmp/%(id)s URL`
- **ffmpeg**: `ffmpeg -i INPUT.mkv -map 0:s:0 -c:s webvtt /tmp/subs.vtt`
- **Browser**: DevTools → Network → filter `.vtt` → Save response body

## Anti-patterns

- **Don't feed raw `.vtt` to an LLM** — cue overlap multiplies token count several times over; always run through this script first.
- **Don't use on SRT** — the script will silently treat SRT numeric cue IDs and `-->` lines as VTT; output will be garbled.

## Exit codes and errors

| Situation | Behavior |
|-----------|----------|
| File not found | Prints `ERROR: file not found: <path>` to stderr; exits 1 |
| Success | Plaintext on stdout; exits 0 |
| Empty VTT / no cues | Empty output on stdout; exits 0 |
