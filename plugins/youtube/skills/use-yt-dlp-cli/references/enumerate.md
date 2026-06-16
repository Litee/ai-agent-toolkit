# Enumerating Channels, Playlists, and Search Results

## Canonical invocation (flat, fast)

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Channel videos tab
$YT --flat-playlist -J "https://www.youtube.com/@Handle/videos" 2>/dev/null | python3 -c "
import json,sys
data=json.load(sys.stdin)
for e in data.get('entries',[]):
    print(json.dumps(e))
"

# Playlist
$YT --flat-playlist -J "https://www.youtube.com/playlist?list=PLxxxxxxxx" 2>/dev/null

# Canonical channel ID (was silently skipped by old skill)
$YT --flat-playlist -J "https://www.youtube.com/channel/UCxxxxxxxxx/videos"

# Search (25 results)
$YT --flat-playlist -J "ytsearch25:llm papers 2025"
```

## Common variations

```bash
# Only first 50 items
$YT --flat-playlist --playlist-items "1:50" -J URL

# Filter by upload date (channel/playlist URLs only — see caveat below for search)
$YT --flat-playlist --dateafter 20250101 --datebefore today -J URL

# Filter by view count (requires full extraction — no --flat-playlist)
$YT -j --skip-download --match-filters "view_count>100000" URL

# Fast approximate dates in flat mode (avoids per-video network round-trip)
$YT --flat-playlist --extractor-args "youtubetab:approximate_date" -J URL

# Resume across runs (skip already-seen IDs)
$YT --flat-playlist --download-archive /tmp/seen.txt URL

# Stop once archived IDs are encountered
$YT --flat-playlist --download-archive /tmp/seen.txt --break-on-existing URL

# Rate-limit safe for large channels
$YT --flat-playlist --sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20 -J URL
```

## Output shape (flat entry)

Each entry in `data["entries"]`:
```json
{
  "id": "xxxxxxxxxxx",
  "title": "Video Title",
  "url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
  "duration": 312,
  "view_count": 45000,
  "channel": "Channel Name",
  "channel_id": "UCxxxxxxxxx",
  "uploader": "Channel Name",
  "uploader_id": "@Handle",
  "thumbnails": [{"url": "...", "width": 1280, "height": 720}],
  "timestamp": null,
  "upload_date": null,
  "live_status": "not_live",
  "availability": "public"
}
```

Full description, tags, chapters, like_count are NOT present in flat mode. Use `${SKILL_DIR}/references/metadata.md` for full per-video extraction.

**`timestamp` and `upload_date` are `null` by default in flat mode** — for channel/playlist URLs, add `--extractor-args "youtubetab:approximate_date"` to populate `timestamp` (rounded to the day; `upload_date` stays `null`). For search (`ytsearchN:`), both fields are always `null` regardless of `approximate_date` — date data must come from a full-extraction pass (see *Date-filtered search* below).

## Date-filtered search

`--dateafter` / `--datebefore` do NOT work against `ytsearchN:` pseudo-URLs: the flags silently discard all entries because flat search entries carry no date. The old `ytsearchdateN:` scheme is also gone in current yt-dlp — it raises:

```
ERROR: Unable to handle request: Unsupported url scheme: "ytsearchdateN" (requests, urllib)
```

Use a two-pass workflow instead:

1. **Enumerate IDs** with `--flat-playlist -J "ytsearchN:query"`.
2. **Full-extract** each ID with `-j --skip-download` to get `timestamp` / `upload_date`.
3. **Filter client-side** by date.

Concrete pipeline:

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp
QUERY="llm papers 2025"
CUTOFF=20250101   # YYYYMMDD; keep entries on or after this date

# Pass 1: collect IDs
$YT --flat-playlist -J --no-warnings "ytsearch50:$QUERY" \
  | python3 -c 'import json,sys; [print(e["id"]) for e in json.load(sys.stdin)["entries"]]' \
  > /tmp/ids.txt

# Pass 2: full-extract + filter in one stream
awk '{print "https://www.youtube.com/watch?v=" $0}' /tmp/ids.txt \
  | $YT -j --skip-download --no-warnings --ignore-errors --batch-file - \
  | python3 -c "
import json, sys
cutoff = '$CUTOFF'
for line in sys.stdin:
    v = json.loads(line)
    if (v.get('upload_date') or '') >= cutoff:
        print(json.dumps({'id': v['id'], 'upload_date': v['upload_date'], 'title': v['title']}))
"
```

For large ID sets, replace the inline filter with `dump_corpus.py --mode full` and filter `corpus.jsonl` in a second step — pass 2 is where rate limits bite, so reuse the checkpointing.

## Gotchas

- **`--dateafter` silently no-ops in flat mode (channel/playlist URLs):** Even with `--extractor-args "youtubetab:approximate_date"`, `upload_date` stays `null` in flat entries — only `timestamp` is populated. Because `--dateafter` filters on `upload_date`, it silently discards all entries and returns the full listing unfiltered. Filter client-side by `timestamp` instead:
  ```python
  import datetime
  cutoff_ts = int((datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=N)).timestamp())
  recent = [e for e in entries if e.get('timestamp') and e['timestamp'] >= cutoff_ts]
  ```

- **`--playlist-items "1:N"` as a fetch cap for recent-video queries:** YouTube's `/videos` tab lists newest-first, so `--playlist-items "1:N"` stops enumeration after N entries and avoids downloading full channel history. Pair this with client-side `timestamp` filtering when you only want videos from the last K days. Tune N to the channel's posting cadence — too small misses videos within the window; too large wastes requests. When cadence is unknown, fetch more entries and filter client-side.

## Common errors

- `"entries": null` — channel has no public videos on that tab, or URL pattern not recognised. Check URL shape.
- `ExtractorError: youtube:approximate_date` not supported — upgrade yt-dlp.
- HTTP 429 — rate limited. Add sleep flags or pause and retry.
