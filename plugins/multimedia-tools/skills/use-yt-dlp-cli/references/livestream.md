# Live Streams

## Detect live status

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

$YT -j --skip-download URL | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('live_status'), d.get('was_live'))
"
```

`live_status` values: `not_live`, `is_live`, `is_upcoming`, `post_live`, `was_live`.

## Wait for a scheduled stream and start recording when it goes live

```bash
$YT --wait-for-video 30-120 --live-from-start \
    -o "/tmp/stream/%(title)s.%(ext)s" URL
```

`--wait-for-video 30-120` polls every 30–120 seconds until the stream starts.
`--live-from-start` rewinds to the beginning of the stream once live.

## Download a stream from the start (already live)

```bash
$YT --live-from-start \
    -o "/tmp/stream/%(title)s.%(ext)s" URL
```

## Download a past livestream (VOD)

Same as a normal video download. `live_status` will be `was_live`.

## Partial file playback while downloading

`--hls-use-mpegts` (default for live) allows opening the partial file in a media player while the download is in progress.

## Members-only / private streams

Require `--cookies-from-browser firefox` (or another browser). Never bake cookies into a script.

## Common errors

### `--wait-for-video` never completes

`--wait-for-video MIN[-MAX]` is a **polling interval**, not a total-time bound. If the creator keeps rescheduling (or cancels without unlisting), yt-dlp will log `[wait] Remaining time until next attempt: ...` forever. There is no built-in max-wait flag.

Detection and recovery:

```bash
# Re-probe the scheduled time without disturbing the waiter
$YT -j --skip-download URL | python3 -c "
import json,sys,datetime
d=json.load(sys.stdin)
print('live_status:', d.get('live_status'))
ts=d.get('release_timestamp')
if ts:
    print('scheduled:', datetime.datetime.fromtimestamp(ts))
"

# Bound total wait time at the shell level (e.g. give up after 4 h)
timeout 4h $YT --wait-for-video 30-120 --live-from-start -o "..." URL
```

If `live_status` stays `is_upcoming` past the scheduled time by more than the polling interval, or flips back to `is_upcoming` from `not_live`, the stream was postponed. Abort and re-schedule the job against the new `release_timestamp`.

### Stream goes private or members-only mid-wait

yt-dlp exits non-zero with one of:

- `ERROR: [youtube] <id>: Private video. Sign in if you've been granted access to this video`
- `ERROR: [youtube] <id>: Join this channel to get access to members-only content`
- `ERROR: [youtube] <id>: Video unavailable`

No recovery without credentials. Verify with a cookie-less `-J` probe — if `availability` is `subscriber_only` or `needs_auth`, re-run with `--cookies-from-browser firefox`. If the creator has fully privated the video, there is no recovery; wait for them to make it public again.

### Recording interrupted mid-stream

A partially-downloaded livestream leaves these files next to the output template:

- `<name>.f<fmt>.mp4` / `<name>.f<fmt>.m4a` — per-format video and audio fragments (before merge)
- `<name>.f<fmt>.mp4.part` — in-flight fragment buffer
- `<name>.ytdl` — yt-dlp resume state (fragment index, URL, headers)

Resume safely:

```bash
$YT --continue --no-overwrites --live-from-start \
    -o "/tmp/stream/%(title)s.%(ext)s" URL
```

Discard and restart when:

- yt-dlp logs `ERROR: Unable to download ...m3u8` or `HTTP Error 404` on resume — the live HLS manifest has rolled off and the segments no longer exist at the CDN. Delete the `.part` / `.ytdl` / `.f*` files and re-extract against the `was_live` VOD once YouTube publishes it (`live_status == 'was_live'`).
- The `.ytdl` file references a format ID that no longer appears in `$YT -F URL` — the stream switched manifests. Same remedy: delete and restart.

### `--live-from-start` not supported

Only works for YouTube, Twitch, and TVer (upstream yt-dlp `--help`). Other extractors silently fall back to downloading from the current time. Confirm with `$YT --help | grep -A2 live-from-start` before relying on rewind for a new site.
