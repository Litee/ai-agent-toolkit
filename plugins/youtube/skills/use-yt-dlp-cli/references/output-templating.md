# Output Filename Templating

## Basic syntax

```bash
-o "TEMPLATE"
# %(FIELD)s  — string field
# %(FIELD)d  — integer field
# %(FIELD>FORMAT)s  — date formatting (strftime)
```

## Common templates

```bash
# Video ID only
-o "/tmp/yt/%(id)s.%(ext)s"

# Title + ID (title truncated to 80 chars)
-o "/tmp/yt/%(title).80s [%(id)s].%(ext)s"

# Upload date + title
-o "/tmp/yt/%(upload_date>%Y-%m-%d)s %(title).60s.%(ext)s"

# Playlist index + title
-o "/tmp/yt/%(playlist_index)03d %(title).60s.%(ext)s"

# Channel subfolder
-o "/tmp/yt/%(uploader)s/%(upload_date>%Y-%m-%d)s %(title).60s.%(ext)s"

# Chapter title (use with --split-chapters)
-o "chapter:/tmp/chapters/%(section_number)03d %(section_title)s.%(ext)s"
```

## Per-artifact type paths

```bash
# Send video, thumbnail, and subtitle to different dirs
-o "video:/tmp/video/%(id)s.%(ext)s" \
-o "thumbnail:/tmp/thumbs/%(id)s.%(ext)s" \
-o "subtitle:/tmp/subs/%(id)s.%(ext)s"
```

Type prefixes: `video`, `audio`, `thumbnail`, `subtitle`, `description`, `infojson`, `pl_video`, `pl_thumbnail`, `pl_description`, `pl_infojson`, `chapter`, `playlist`.

## Base directory shorthand

```bash
-P "/tmp/yt" -o "%(id)s.%(ext)s"
# Equivalent to -o "/tmp/yt/%(id)s.%(ext)s"

# Per-type base dir
-P "thumbnail:/tmp/thumbs" -P "video:/tmp/video" -o "%(id)s.%(ext)s"
```

## Conditional and truncation

```bash
# Prefix playlist index only if present
-o "%(playlist_index&{} - |)s%(title)s.%(ext)s"

# Truncate title to 80 chars
-o "%(title).80s.%(ext)s"
```

## Unavailable field placeholder

```bash
--output-na-placeholder "NA"
# Fields that are null render as "NA" instead of "NA"
```
