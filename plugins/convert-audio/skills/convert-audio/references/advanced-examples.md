# Advanced Audio Conversion Examples

Load this file when the user needs format-specific conversions, metadata tagging examples, or complex combined parameter scenarios.

## Example 7: Convert to Different Format (Lossless)

Convert MP3 to FLAC (lossless) with specific sample rate:

```bash
ffmpeg -n -i input.mp3 -ar 48000 output.flac
```

*FLAC is lossless — bitrate is not applicable*

## Example 8: Slow Down Audio

Slow down to 75% speed:

```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=0.75" output.mp3
```

## Example 9: Basic Metadata (Title and Artist)

Convert WAV to MP3 with title and artist metadata:

```bash
ffmpeg -n -i input.wav -b:a 192k -metadata title="My Song" -metadata artist="John Doe" output.mp3
```

## Example 10: Complete Album Metadata

Convert to MP3 with comprehensive album metadata:

```bash
ffmpeg -n -i input.wav -b:a 320k \
  -metadata title="Track Name" \
  -metadata artist="Artist Name" \
  -metadata album="Album Name" \
  -metadata date="2024" \
  -metadata genre="Rock" \
  -metadata track="3/12" \
  output.mp3
```

## Example 11: Podcast Episode Metadata

Convert to mono MP3 optimized for podcasts with metadata:

```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 \
  -metadata title="Episode 42: AI Best Practices" \
  -metadata artist="Tech Podcast" \
  -metadata album="Season 2" \
  -metadata date="2024" \
  -metadata genre="Podcast" \
  -metadata comment="Discussion about AI coding practices" \
  output.mp3
```

## Example 12: Combined Parameters with Metadata

Convert with all parameters including speed adjustment and metadata:

```bash
ffmpeg -n -i input.wav -b:a 192k -ac 2 -ar 44100 -af "atempo=1.25" \
  -metadata title="Fast Version" \
  -metadata artist="Artist Name" \
  -metadata album="Remixes" \
  output.mp3
```

## Metadata Tag Reference

Use `-metadata key="value"` for each tag:

| Tag | Description | Example |
|-----|-------------|---------|
| `title` | Track title | `"Song Title"` |
| `artist` | Performer | `"Artist Name"` |
| `album` | Album name | `"Album Name"` |
| `date` | Release year | `"2024"` |
| `genre` | Music genre | `"Rock"` |
| `track` | Track number | `"3"` or `"3/12"` |
| `comment` | Notes | `"Any text"` |
| `album_artist` | Album artist | `"Various Artists"` |
| `composer` | Composer | `"Composer Name"` |
| `publisher` | Publisher | `"Label Name"` |
| `disc` | Disc number | `"1"` |

**Preserve existing metadata:**
```bash
ffmpeg -n -i input.mp3 -b:a 192k -map_metadata 0 output.mp3
```

**Clear all metadata:**
```bash
ffmpeg -n -i input.mp3 -b:a 192k -map_metadata -1 output.mp3
```

For full codec details and format-specific parameters, see `references/ffmpeg-parameters.md`.
