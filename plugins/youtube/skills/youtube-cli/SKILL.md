---
name: youtube-cli
description: >
  Use when listing videos from a YouTube channel or playlist (with filters),
  listing playlists for a channel, fetching full video metadata, or downloading
  captions/transcripts as VTT files. Invokes scripts/youtube-cli which uses
  yt-dlp as a Python library with local caching. Triggers on: list channel
  videos, get video metadata, fetch captions, list playlists, filter videos
  by date/views/duration/title, YouTube channel scraping, transcript download.
  Not for downloading video/audio files — use use-yt-dlp-cli for that.
---

# youtube-cli

A thin CLI wrapper around yt-dlp's Python library for enumerating and inspecting
YouTube content without downloading media. All four subcommands use yt-dlp in
library mode (`import yt_dlp`) — never subprocess.

---

## Prerequisites

No manual setup needed. On first run the script automatically creates a venv at
`/tmp/youtube-cli-venv`, installs `yt-dlp` into it, and re-executes itself inside
that venv. Subsequent runs skip straight to execution.

To force a reinstall / upgrade, delete the venv:

```bash
rm -rf /tmp/youtube-cli-venv
```

The script itself has no other dependencies beyond the Python standard library.

All invocations below use `${SKILL_DIR}/scripts/youtube-cli`, where `${SKILL_DIR}`
resolves at runtime to this skill's root directory. Do not substitute a relative
or hardcoded path.

---

## Subcommands

### `list-videos` — enumerate videos from a channel or playlist

```bash
# All recent videos from a channel (fast flat mode)
${SKILL_DIR}/scripts/youtube-cli list-videos "https://www.youtube.com/@SomeChannel"

# Shorts tab, on/after a date, minimum 10 k views, save to file
# NOTE: --min-views triggers full extraction (slower — one fetch per video)
${SKILL_DIR}/scripts/youtube-cli list-videos "https://www.youtube.com/@SomeChannel" \
  --type shorts \
  --after 2025-05-01 \
  --min-views 10000 \
  --output videos.jsonl

# Playlist — first 50
${SKILL_DIR}/scripts/youtube-cli list-videos "https://www.youtube.com/playlist?list=PLxxxxxxxx" \
  --limit 50

# Duration filter (triggers full extraction — slower)
${SKILL_DIR}/scripts/youtube-cli list-videos "https://www.youtube.com/@SomeChannel" \
  --min-duration 600 \
  --max-duration 1800 \
  --limit 20
```

### `list-playlists` — enumerate playlists for a channel

```bash
${SKILL_DIR}/scripts/youtube-cli list-playlists "https://www.youtube.com/@SomeChannel"

${SKILL_DIR}/scripts/youtube-cli list-playlists "https://www.youtube.com/@SomeChannel" \
  --output playlists.jsonl
```

### `get-metadata` — fetch full video metadata

```bash
# By video ID
${SKILL_DIR}/scripts/youtube-cli get-metadata dQw4w9WgXcQ

# By URL
${SKILL_DIR}/scripts/youtube-cli get-metadata "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Save to file
${SKILL_DIR}/scripts/youtube-cli get-metadata dQw4w9WgXcQ --output meta.json
```

### `get-captions` — download captions as VTT

```bash
# English captions (manual first, auto-generated fallback)
${SKILL_DIR}/scripts/youtube-cli get-captions dQw4w9WgXcQ --output-dir /tmp/caps

# Spanish
${SKILL_DIR}/scripts/youtube-cli get-captions dQw4w9WgXcQ --lang es --output-dir /tmp/caps

# Skip cache
${SKILL_DIR}/scripts/youtube-cli --no-cache get-captions dQw4w9WgXcQ --output-dir /tmp/caps
```

---

## Global flags

| Flag | Default | Description |
|------|---------|-------------|
| `--no-cache` | off | Bypass cache for both reads and writes |

---

## `list-videos` filter reference

| Flag | Type | Description |
|------|------|-------------|
| `--after YYYY-MM-DD` | date | Include only videos published on/after this date |
| `--before YYYY-MM-DD` | date | Include only videos published on/before this date |
| `--limit N` | int | Stop after N matching results |
| `--type {videos,shorts,streams,all}` | enum | Channel tab to enumerate (default: `videos`; ignored for playlist URLs) |
| `--min-views N` | int | Minimum view count — triggers full extraction |
| `--min-duration SEC` | float | Minimum duration in seconds — triggers full extraction |
| `--max-duration SEC` | float | Maximum duration in seconds — triggers full extraction |
| `--output FILE` | path | Write JSONL output here instead of stdout |

---

## Output shapes

### `list-videos` — JSONL, one object per line

```json
{
  "id": "xxxxxxxxxxx",
  "url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
  "title": "Video Title",
  "duration": 312,
  "view_count": 45000,
  "upload_date": null,
  "timestamp": 1746057600,
  "channel_url": "https://www.youtube.com/@SomeChannel",
  "live_status": "not_live",
  "availability": "public",
  "thumbnails": [{"url": "...", "width": 1280, "height": 720}]
}
```

`upload_date` is always `null` in flat mode. `timestamp` is populated when the
channel tab supports `approximate_date` (rounded to the day).

### `list-playlists` — JSONL, one object per line

```json
{
  "id": "PLxxxxxxxxxxxxxxxx",
  "url": "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx",
  "title": "Playlist Title",
  "playlist_count": 42,
  "thumbnails": [{"url": "...", "width": 640, "height": 360}],
  "channel_url": "https://www.youtube.com/@SomeChannel"
}
```

### `get-metadata` — pretty-printed JSON (stdout or `--output FILE`)

Full yt-dlp info dict with all available fields: `id`, `title`, `fulltitle`,
`description`, `duration`, `view_count`, `like_count`, `comment_count`,
`channel`, `channel_id`, `channel_url`, `upload_date`, `timestamp`,
`categories`, `tags`, `thumbnails`, `chapters`, `automatic_captions`,
`subtitles`, `formats`, `heatmap`, `webpage_url`, and more.

### `get-captions` — VTT file + result JSON to stdout

The VTT is written to `<output-dir>/<video_id>.<lang>.vtt`.
Result JSON printed to stdout:

```json
{"video_id": "xxxxxxxxxxx", "path": "/tmp/caps/xxxxxxxxxxx.en.vtt", "lang": "en"}
```

---

## Cache behaviour

Cache lives under `~/.cache/youtube-cli/`.

| Subcommand | Cache key | Location |
|------------|-----------|----------|
| `get-metadata` | `<video_id>` | `metadata/<video_id>.json` |
| `get-captions` | `<video_id>.<lang>` | `captions/<video_id>.<lang>.vtt` |

- **Cache hit**: data returned immediately, yt-dlp not called.
- **Cache write**: only after successful fetch.
- **`--no-cache`**: skips both read and write.
- `list-videos` and `list-playlists` are **not cached** (listings change frequently).
- On cache hit for `get-captions`, the VTT is copied to `--output-dir`.

---

## Gotchas

### Flat mode null fields
In flat mode (`list-videos` without duration filters), `upload_date` is always
`null`. Date filters use `timestamp` (populated by `approximate_date`, rounded
to the day). If a video has `timestamp: null`, it is excluded by date filters.

### `approximate_date` populated on playlist URLs
Playlist entries carry a `timestamp` (via `approximate_date`, rounded to the
day), so `--after`/`--before` date filters work on playlist URLs as well as
channel tab URLs. Individual entries with `timestamp: null` are still excluded
by date filters.

### Full extraction slowness + 500 cap
`--min-duration`, `--max-duration`, or `--min-views` disables flat mode and
fetches each video individually. This is **much slower** — one network
round-trip per video. A hard cap of 500 is applied if `--limit` is not set. A
warning naming the triggering flag(s) is printed to stderr.

### VTT is raw
Downloaded VTT files contain overlapping cue windows and inline tag noise from
YouTube's auto-captioning. Use the **`convert-vtt-to-text`** skill to convert
to clean plaintext before passing to an LLM or text index.

### 429 rate limits
YouTube rate limits aggressive enumeration. If you hit 429s, wait a few minutes
before retrying. For large channel traversals, add delays between runs.

### Empty VTT = PO Token enforcement
If VTT files are produced but have 0 bytes, YouTube's Proof of Origin Token
(POT) enforcement is blocking the download. Try:

```bash
# Pass extractor args via yt-dlp (if calling directly)
--extractor-args "youtube:player_client=tv,mweb"
```

Or install the POT provider plugin:

```bash
pip install bgutil-ytdlp-pot-provider
```

> As of this writing yt-dlp's extractor internals change frequently. The working
> `player_client` values and POT requirements shift between YouTube and yt-dlp
> releases — if these workarounds stop helping, upgrade yt-dlp (`pip install -U
> yt-dlp`) and check its changelog / issue tracker for the current guidance.

### `--type` ignored for playlist URLs
When a playlist URL is passed to `list-videos`, `--type` has no effect and a
warning is printed to stderr. The `--type` flag only applies to channel URLs.

### `--type all` — bare channel URL
`--type all` uses the bare channel URL (no tab suffix), which returns a mix of
content types from the channel's default view.

### When a fetch fails
yt-dlp can fail for reasons outside this script's control. Handle these cases:

- **yt-dlp raises / network error**: the subcommand exits non-zero and prints the
  error to stderr; nothing is cached. Check connectivity, then retry. Always
  inspect the exit code rather than assuming output is valid.
- **Video unavailable / private / deleted / age-restricted / region-blocked**:
  `get-metadata` and `get-captions` cannot extract these. Expect an error or an
  empty result — verify the video is publicly viewable before retrying.
- **No captions for the requested language**: `get-captions` tries manual
  captions first, then auto-generated. If neither exists for `--lang`, no VTT is
  written. Try a different `--lang` or confirm captions exist on the video.
- **Empty / null result**: when a listing or metadata fetch yields nothing,
  treat it as "no data" rather than success — re-check the URL/ID and flags
  before re-running. Do not assume an empty file means the content is empty.

---

## Related Skills

- **`use-yt-dlp-cli`** — downloads video/audio, searches YouTube, fetches
  comments, scrapes other platforms. Use when you need media files, search
  results, or platforms other than YouTube.
- **`convert-vtt-to-text`** — converts raw VTT caption files (as produced by
  `get-captions`) to deduplicated plaintext, optionally with timestamps.
