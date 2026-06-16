# Downloading Video and Audio

## Canonical invocations

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Best quality mp4 up to 1080p with embedded subs, chapters, thumbnail, metadata
$YT -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 \
    --embed-subs --embed-thumbnail --embed-metadata --embed-chapters \
    -o "/tmp/yt/%(title).80s [%(id)s].%(ext)s" \
    "https://www.youtube.com/watch?v=xxxxxxxxxxx"

# Audio only — mp3
$YT -x --audio-format mp3 --audio-quality 0 \
    --embed-thumbnail --embed-metadata \
    -o "/tmp/yt/%(title).80s.%(ext)s" URL

# Audio only — m4a (no re-encode, faster)
$YT -f "ba" --remux-video m4a \
    -o "/tmp/yt/%(title).80s.%(ext)s" URL
```

## Format selection cheat-sheet

```bash
# Best video+audio in any container
-f "bv*+ba/b"

# Best video+audio, prefer h264
-S "codec:h264" -f "bv*+ba/b"

# Exactly 720p
-f "bv*[height=720]+ba/b"

# Worst quality (for testing)
-f "wv+wa/w"

# List all available formats
$YT -F URL
```

## Common flags

| Flag | Effect |
|---|---|
| `--merge-output-format mp4` | Container for merged video+audio |
| `--remux-video mp4` | Fast container swap, no re-encode |
| `--recode-video mp4` | Re-encode (slow, guarantees container) |
| `--write-thumbnail` | Save thumbnail as separate file |
| `--embed-thumbnail` | Embed thumbnail in file |
| `--embed-subs` | Embed subtitles (mp4/mkv/webm) |
| `--embed-metadata` | Embed title/uploader/date etc. |
| `--embed-chapters` | Embed chapter markers |
| `--write-info-json` | Save metadata sidecar |

## Common errors

- `ffmpeg not found` — install ffmpeg and ensure it is on PATH.
- `requested format not available` — use `-F` to see what is available, adjust `-f`.
- `merge output format not supported` — use `--merge-output-format mkv` as fallback.
