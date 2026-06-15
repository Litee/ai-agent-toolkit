# Batch Processing Many URLs or IDs

## Large playlist enumeration (500+ videos)

Pass a playlist URL directly to a download command and mid-run rate-limiting can truncate the enumeration with no recovery path. Separate enumeration from fetching:

**Step 1 — enumerate all IDs cheaply:**
```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp
$YT --flat-playlist --js-runtimes node \
    --print "%(id)s\t%(title)s" \
    "https://www.youtube.com/playlist?list=PLXXXXXXXXX" > /tmp/all_ids.tsv
# Convert to one URL per line for dump_corpus.py:
awk '{print "https://www.youtube.com/watch?v=" $1}' /tmp/all_ids.tsv > /tmp/all_urls.txt
```

**Step 2 — feed individual URLs to dump_corpus.py (resumable):**
```bash
$YTPY $SCRIPT --urls-file /tmp/all_urls.txt --mode captions --output-dir /tmp/corpus
```

`processed.txt` checkpoints each URL so re-runs skip already-fetched videos.

## yt-dlp native batch file

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# urls.txt: one URL per line; lines starting with # are comments
$YT --batch-file urls.txt \
    --ignore-errors \
    --download-archive /tmp/seen.txt \
    --sleep-interval 10 --max-sleep-interval 20 \
    -o "/tmp/output/%(id)s.%(ext)s"
```

## Corpus builder script (replaces fetch-youtube-channel-videos + fetch-youtube-video-transcripts)

Use `${SKILL_DIR}/scripts/dump_corpus.py` for JSONL corpus building. It accepts any yt-dlp-compatible URL — channels, playlists, `/channel/UC…`, search URLs, bare video IDs.

```bash
SCRIPT=${SKILL_DIR}/scripts/dump_corpus.py
YTPY=/tmp/yt-tools-venv/bin/python3

# Flat mode (fast, limited fields — equivalent to old fetch-youtube-channel-videos)
$YTPY $SCRIPT \
    --urls-file channels.txt \
    --mode flat \
    --output-dir /tmp/corpus

# Full metadata mode (slow, all fields including description/chapters/tags)
$YTPY $SCRIPT \
    --urls-file channels.txt \
    --mode full \
    --output-dir /tmp/corpus

# Captions mode (flat metadata + captions per video)
$YTPY $SCRIPT \
    --urls-file video_ids.txt \
    --mode captions \
    --sub-langs "en" \
    --output-dir /tmp/corpus
```

`corpus.jsonl` entries in `captions` mode carry `captions_vtt` (lang → raw VTT text). Run the `convert-vtt-to-text` skill downstream for plaintext.

### dump_corpus.py arguments

| Argument | Default | Description |
|---|---|---|
| `--urls-file FILE` | required | One URL/ID per line. Accepts any yt-dlp YouTube URL: channels, playlists, `/@handle`, `/channel/UC…`, `ytsearch…`, bare video IDs. Lines starting with `#` ignored. |
| `--mode {flat,full,captions}` | `flat` | Extraction depth |
| `--output-dir DIR` | required | Output directory (created if absent) |
| `--sub-langs LANGS` | `en` | Comma-separated language codes for captions mode |
| `--request-delay SECS` | `1.0` | Sleep between requests |
| `--force` | false | Re-fetch even if URL is in processed.txt |
| `--limit N` | (none) | Process at most N entries from the remaining set (after checkpoint filtering). Must be ≥ 1. |

### Output files

| File | Description |
|---|---|
| `corpus.jsonl` | One JSON record per video/entry, appended across runs. In `captions` mode, each entry carries a `captions_vtt` dict (lang → raw VTT text); convert with `convert-vtt-to-text`. |
| `processed.txt` | URLs successfully processed (checkpoint) |
| `failed.txt` | URLs that raised errors (tab-separated: url, error message) |
| `skipped.txt` | Lines that could not be parsed as a valid URL |

Re-running resumes from where it left off (processed.txt checkpoint). Use `--force` to re-fetch.

## Gotchas

- **`--download-archive` + `--skip-download`:** `--download-archive` marks videos as fully processed, which suppresses subtitle fetching too — not just the video download. Use `--no-overwrites` instead when you want to skip existing output files without blocking subtitle fetching.
- **`$()` capture breaks `--print` output:** Capturing yt-dlp output via `result=$(yt-dlp ... --print ...)` causes a BrokenPipeError — the subshell pipe closes before yt-dlp finishes, aborting the run before any output files are written. Redirect `--print` output directly to a file (`>> meta.tsv`) instead of capturing it.
- **`--quiet` suppresses `--print` output:** Without `--quiet`, yt-dlp emits per-byte progress lines to stdout that flood output buffers and can cause background tasks to be killed (SIGTERM/exit 144). Always add `--quiet --no-warnings` in batch loops. Note that `--quiet` also suppresses `--print` output — redirect print output explicitly to a file to preserve it.

## Rate limiting guidance

- Never parallelise across the same channel — yt-dlp's own serialisation respects rate limits.
- If you must parallelise, shard by channel, not by video.
- Use `--sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20` for large batches.
- On HTTP 429, stop and wait 10–30 minutes before retrying.
- **Datacenter IPs are pre-blocked:** AWS, GCP, and Azure IP ranges are pre-flagged by YouTube's WAF. Sleep settings alone cannot fix this. Residential rotating proxies (`--proxy`) or a SaaS transcript API are required for sustained server-side caption extraction.
- `dump_corpus.py` automatically adapts its request pacing based on error rates: it backs off quickly when errors are detected and recovers conservatively only after sustained clean operation. `--request-delay` sets the baseline (floor); the delay may grow up to 1 hour under sustained throttling. Delay changes are logged to stderr.
