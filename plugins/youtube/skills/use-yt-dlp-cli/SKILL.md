---
name: use-yt-dlp-cli
description: "Use when driving the yt-dlp CLI against YouTube — downloading videos/audio, clipping by timestamp, enumerating channels/playlists/search results, fetching captions/transcripts, pulling comments, splitting by chapters, waiting for livestreams, or building JSONL corpora. Not for YouTube Data API v3 workflows (channel statistics, trending, comment trees, subscriber counts, playlist mutations) — use `youtube-knowledge` instead. Not for non-YouTube platforms."
---

# use-yt-dlp-cli

> Found major gaps or factual errors in this skill? Report it via the `use-local-skills-issue-tracker` skill (if available).

Drive the `yt-dlp` CLI or Python library against YouTube. Covers downloading, enumerating channels/playlists/search, metadata extraction, captions, comments, chapters, clipping, and live streams.

## Setup

```bash
# Install once into shared venv
python3 -m venv /tmp/yt-tools-venv
/tmp/yt-tools-venv/bin/pip install -U yt-dlp
```

Always invoke via `/tmp/yt-tools-venv/bin/yt-dlp`. If that path is absent, fall back to `shutil.which("yt-dlp")`. Check that `ffmpeg` is on PATH — required for format merging, audio extraction, and clipping.

## Which Reference to Load

Read the relevant `${SKILL_DIR}/references/` file before writing any yt-dlp command. Pick the one that matches the task:

| Task | Reference |
|---|---|
| Download video or audio file | `${SKILL_DIR}/references/download.md` |
| List videos from channel / playlist / handle / search | `${SKILL_DIR}/references/enumerate.md` |
| Extract metadata JSON without downloading | `${SKILL_DIR}/references/metadata.md` |
| Fetch captions / transcripts | `${SKILL_DIR}/references/captions.md` |
| Cut a clip by timestamp or chapter | `${SKILL_DIR}/references/clips.md` |
| Get comments | `${SKILL_DIR}/references/comments.md` |
| Wait for / record a livestream | `${SKILL_DIR}/references/livestream.md` |
| Batch over many URLs or IDs | `${SKILL_DIR}/references/batch.md` |
| Customize output filenames | `${SKILL_DIR}/references/output-templating.md` |

## URL Shapes yt-dlp Accepts for YouTube

All of these work as input URLs:

```
https://www.youtube.com/@Handle              # all uploads (videos + shorts + streams)
https://www.youtube.com/@Handle/videos       # videos only
https://www.youtube.com/@Handle/shorts
https://www.youtube.com/@Handle/streams
https://www.youtube.com/@Handle/playlists
https://www.youtube.com/@Handle/community
https://www.youtube.com/c/Name
https://www.youtube.com/user/LegacyName
https://www.youtube.com/channel/UCxxxxxxxxx  # canonical channel ID
https://www.youtube.com/watch?v=xxxxxxxxxxx
https://youtu.be/xxxxxxxxxxx
https://www.youtube.com/playlist?list=xxxxx
https://www.youtube.com/shorts/xxxxxxxxxxx
https://www.youtube.com/@Handle/search?query=term  # channel-scoped search
ytsearch:query                               # first result
ytsearch25:query                             # 25 results
```

Bare channel URL enumerates all uploads (videos + shorts + streams). Append `/videos` to restrict to videos only.

`ytsearchdateN:query` is NOT supported by yt-dlp — it raises `Unable to handle request: Unsupported url scheme: "ytsearchdateN"`. For date-filtered search, enumerate with `ytsearchN:` and filter `upload_date`/`timestamp` in a second full-extraction pass (see `${SKILL_DIR}/references/enumerate.md` → Date-filtered search).

## yt-dlp vs youtube-knowledge (Data API v3)

Use yt-dlp for: read-only access to individual videos, channels, playlists, transcripts, comments, metadata.

Use `youtube-knowledge` (Data API v3) for: channel-aggregate statistics, region trending, durable comment pagination at scale, playlist/caption writes, rich search filters (`videoDuration`, `videoCaption`, `publishedAfter`, geo-radius), real-time subscriber counts.

## Universal Flags

Always add to scripted invocations:
- `--no-warnings --quiet` — suppress noise
- `--ignore-errors` — continue on per-item failures in batch
- `--no-check-certificate` — inside Amazon corp network only
- `--sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20` — for large enumerations (100+ items)
- `--sleep-subtitles 5` — sleep between subtitle file fetches; add this for caption-heavy runs (`--sleep-interval` does not cover subtitle downloads)
- `--js-runtimes node` — required for large playlists (500+ videos); without it, YouTube's JS-based pagination silently truncates enumeration to ~100 entries

## Gotchas

- **Version drift:** YouTube changes internals frequently. First debugging step: `/tmp/yt-tools-venv/bin/pip install -U yt-dlp`.
- **Flat extraction:** `extract_flat=True` is fast but omits description, chapters, tags, and like_count. Use full extraction (`-j`) when those fields matter.
- **VTT plaintext conversion:** Auto-generated VTT has overlapping cue windows and inline tags. This skill downloads raw VTT only — run `convert-vtt-to-text` for plaintext. See `${SKILL_DIR}/references/captions.md`.
- **Corpus mode caption status:** Each `corpus.jsonl` row written by `dump_corpus.py --mode captions` carries a `captions_status` field: `ok`, `partial`, `none`, `language_mismatch`, `download_failed`, `extraction_failed`, or `timeout`. Only transient errors (`extraction_failed`, `timeout`) feed the adaptive throttle and are listed in `failed.txt` for retry on rerun. `download_failed` means the probe confirmed captions exist but the download produced nothing (CDN gap / private endpoint) — not a rate-limit signal, URL goes to `processed.txt`. Captionless videos (`none`) also write to `processed.txt` and are never retried. Pass `--only-captioned` to skip writing rows for videos with no captions entirely.
- **Clipping slop:** `--download-sections` cuts to the nearest keyframe (~0.5–2 s). Add `--force-keyframes-at-cuts` for frame-accurate cuts (requires re-encode).
- **Subscriber count:** `channel_follower_count` is the rounded public value, never real-time.
- **Auth:** Pass `--cookies-from-browser firefox` for age-gated or members-only content. Never use `--cookies-from-browser` in a batch script — it reads the live profile, which YouTube may rotate during the run. For long-running batch jobs, prefer a static Netscape-format cookies.txt: open a private/incognito browser window, log in to youtube.com, export cookies immediately using a browser extension, close the window, then pass the file with `--cookies cookies.txt`.
