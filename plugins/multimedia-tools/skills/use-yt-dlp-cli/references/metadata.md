# Extracting Per-Video Metadata JSON

## Canonical invocation

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Single video — pretty JSON to stdout
$YT -j --skip-download "https://www.youtube.com/watch?v=xxxxxxxxxxx"

# Multiple / playlist — one JSON per line
$YT -j --skip-download "https://www.youtube.com/playlist?list=PLxxxxxxxx"

# Entire playlist as one blob
$YT -J --skip-download "https://www.youtube.com/playlist?list=PLxxxxxxxx"
```

## Print specific fields without parsing JSON

```bash
# Tab-separated id, title, duration
$YT --skip-download --print "%(id)s\t%(title)s\t%(duration)s" URL

# Upload date formatted
$YT --skip-download --print "%(upload_date>%Y-%m-%d)s  %(title)s" URL

# Write one field per line to a file
$YT --skip-download --print-to-file "%(id)s" /tmp/ids.txt URL
```

## Full field list for a YouTube VOD

`id`, `title`, `fulltitle`, `description`, `duration`, `view_count`, `like_count`, `comment_count`, `channel`, `channel_id`, `channel_url`, `channel_follower_count`, `channel_is_verified`, `uploader`, `uploader_id`, `uploader_url`, `upload_date` (YYYYMMDD), `timestamp`, `release_timestamp`, `availability`, `age_limit`, `live_status`, `was_live`, `categories`, `tags`, `thumbnails`, `chapters` (list of `{start_time, end_time, title}`), `automatic_captions` (dict by lang), `subtitles` (dict by lang), `formats`, `heatmap`, `playable_in_embed`, `webpage_url`, `extractor`.

## Save info.json sidecars without downloading media

```bash
$YT --skip-download --write-info-json -o "/tmp/meta/%(id)s" URL
# Writes /tmp/meta/<id>.info.json
```

## Common errors

- `live_status: is_live` — metadata for live streams is incomplete. Retry after stream ends.
- Fields missing / null — normal; parse defensively. Flat extraction returns fewer fields than `-j`.
