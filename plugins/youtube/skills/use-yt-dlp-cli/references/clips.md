# Extracting Clips and Splitting by Chapter

## Clip by timestamp

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Cut 00:30 to 02:15 (cuts to nearest keyframe — up to ~2 s slop)
$YT --download-sections "*00:30-02:15" \
    -o "/tmp/clip.%(ext)s" URL

# Frame-accurate cut (re-encodes — slower)
$YT --download-sections "*00:30-02:15" --force-keyframes-at-cuts \
    -o "/tmp/clip.%(ext)s" URL

# Multiple sections
$YT --download-sections "*00:30-02:15" --download-sections "*10:00-12:30" \
    -o "/tmp/clip%(section_number)s.%(ext)s" URL
```

## Split video into one file per chapter

```bash
# Creates one file per chapter using chapter title in filename
$YT --split-chapters \
    -o "chapter:%(section_title)s.%(ext)s" \
    -o "/tmp/chapters/%(title)s/%(section_number)03d %(section_title)s.%(ext)s" \
    URL
```

## Remove chapters by name pattern

```bash
# Remove sponsor segments (requires re-encode if not keyframe-aligned)
$YT --remove-chapters "Sponsor" URL
```

## SponsorBlock integration

```bash
# Mark sponsor/intro/outro segments in file without removing
$YT --sponsorblock-mark "sponsor,intro,outro" URL

# Remove sponsor segments entirely
$YT --sponsorblock-remove "sponsor,selfpromo,interaction" URL
```

SponsorBlock categories: `sponsor`, `intro`, `outro`, `selfpromo`, `preview`, `filler`, `interaction`, `music_offtopic`, `hook`, `poi_highlight`, `chapter`.

## Common errors

- `ffmpeg not found` — required for all clip/split operations.
- `chapter data not available` — video has no chapter markers. Use timestamp sections instead.
