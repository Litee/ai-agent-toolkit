# ffmpeg Audio Conversion - Detailed Parameter Reference

This document provides comprehensive documentation for audio conversion parameters supported by the convert-audio skill.

## Table of Contents

1. [Output Formats and Codecs](#output-formats-and-codecs)
2. [Bitrate Parameter](#bitrate-parameter)
3. [Channels Parameter](#channels-parameter)
4. [Sample Rate Parameter](#sample-rate-parameter)
5. [Tempo Parameter](#tempo-parameter)
6. [Metadata Parameters](#metadata-parameters)
7. [Format-Specific Recommendations](#format-specific-recommendations)
8. [Quality Guidelines](#quality-guidelines)
9. [Advanced Topics](#advanced-topics)

---

## Output Formats and Codecs

ffmpeg automatically selects the appropriate codec based on the output file extension. Here are the common formats:

### MP3 (.mp3)
- **Codec**: libmp3lame
- **Typical Use**: General purpose, widely compatible
- **Bitrate Range**: 8k to 320k
- **Recommended**: 128k (standard), 192k (good), 320k (maximum)
- **Compression**: Lossy

### WAV (.wav)
- **Codec**: PCM (uncompressed)
- **Typical Use**: Professional audio, editing
- **Bitrate**: N/A (uncompressed)
- **File Size**: Large (no compression)
- **Compression**: None (lossless)

### AAC (.aac, .m4a)
- **Codec**: aac
- **Typical Use**: Apple devices, modern applications, streaming
- **Bitrate Range**: 8k to 512k
- **Recommended**: 128k (standard), 256k (high quality)
- **Compression**: Lossy, more efficient than MP3

### FLAC (.flac)
- **Codec**: flac
- **Typical Use**: Lossless archival, audiophile applications
- **Bitrate**: N/A (lossless compression)
- **File Size**: ~50% of WAV
- **Compression**: Lossless

### Opus (.opus)
- **Codec**: libopus
- **Typical Use**: VoIP, low-latency streaming, podcasts
- **Bitrate Range**: 6k to 510k
- **Recommended**: 64k (voice), 128k (music)
- **Compression**: Lossy, very efficient

### Ogg Vorbis (.ogg)
- **Codec**: vorbis
- **Typical Use**: Open-source applications, gaming
- **Bitrate Range**: 45k to 500k
- **Recommended**: 128k (standard), 192k (good)
- **Compression**: Lossy

---

## Bitrate Parameter

The `-b:a` parameter controls the output audio bitrate, which directly affects quality and file size.

### Syntax
```bash
-b:a <value>
```

### Format
- Value must include `k` suffix (e.g., `128k`, `320k`)
- Do NOT use: `128`, `128kbps`, `128000`
- Correct format: `128k`

### Common Values

| Bitrate | Quality | Use Case |
|---------|---------|----------|
| 32k     | Very Low | Voice-only, minimal quality |
| 64k     | Low | Podcasts, voice recordings |
| 96k     | Acceptable | Low-bandwidth streaming |
| 128k    | Standard | General purpose, music |
| 192k    | Good | High-quality music |
| 256k    | High | Professional music, AAC |
| 320k    | Maximum | Best quality MP3 |

### Notes
- Higher bitrate = better quality + larger file
- Diminishing returns above 192k for MP3
- Lossless formats (WAV, FLAC) don't use bitrate parameter
- AAC at 256k ≈ MP3 at 320k in quality

---

## Channels Parameter

The `-ac` parameter controls the number of audio channels in the output.

### Syntax
```bash
-ac <number>
```

### Values
- `1` - Mono (single channel)
- `2` - Stereo (left and right channels)
- Higher values (5.1, 7.1) - Surround sound (rare for conversion)

### Default Behavior
If `-ac` is not specified, ffmpeg preserves the input channel count.

### When to Use

#### Convert to Mono (`-ac 1`)
- Voice recordings (podcasts, audiobooks, interviews)
- Reduces file size by ~50%
- Suitable when spatial audio is not needed
- **Example**: `ffmpeg -n -i input.mp3 -b:a 64k -ac 1 output.mp3`

#### Convert to Stereo (`-ac 2`)
- Music and songs
- Spatial audio, sound effects
- Maintains left/right channel separation
- **Example**: `ffmpeg -n -i input.wav -b:a 192k -ac 2 output.mp3`

### Conversion Behavior
- **Stereo → Mono**: ffmpeg mixes both channels (averages left and right)
- **Mono → Stereo**: ffmpeg duplicates the single channel to both left and right

---

## Sample Rate Parameter

The `-ar` parameter controls the audio sample rate (frequency) in Hz.

### Syntax
```bash
-ar <value>
```

### Common Values

| Sample Rate | Name | Use Case |
|-------------|------|----------|
| 8000        | 8 kHz | Telephone quality |
| 11025       | 11.025 kHz | Low quality |
| 22050       | 22.05 kHz | Half CD quality |
| 44100       | 44.1 kHz | CD quality (standard) |
| 48000       | 48 kHz | DVD, professional |
| 96000       | 96 kHz | High-resolution audio |

### Default Behavior
If `-ar` is not specified, ffmpeg preserves the input sample rate.

### When to Use

#### Keep Standard Rate (44100)
- Most common for music and general audio
- Widely compatible
- **Example**: `ffmpeg -n -i input.wav -b:a 192k -ar 44100 output.mp3`

#### Use Higher Rate (48000)
- Professional video production
- DVD audio standards
- Recording studio work
- **Example**: `ffmpeg -n -i input.wav -b:a 256k -ar 48000 output.wav`

#### Use Lower Rate (22050)
- Reduce file size for voice
- Low-bandwidth applications
- **Example**: `ffmpeg -n -i input.mp3 -b:a 64k -ar 22050 output.mp3`

### Notes
- Higher sample rate = better high-frequency response + larger file
- Human hearing limit: ~20 kHz (44.1 kHz Nyquist = 22.05 kHz max frequency)
- Upsampling (increasing rate) doesn't improve quality
- Downsampling (decreasing rate) may lose high frequencies

---

## Tempo Parameter

The `-af "atempo=<value>"` parameter controls playback speed without changing pitch.

### Syntax
```bash
-af "atempo=<value>"
```

### Value Range
- Minimum: 0.5 (half speed, 50%)
- Maximum: 2.0 (double speed, 200%)
- Default: 1.0 (normal speed, no change)

### Common Values

| Tempo | Speed | Use Case |
|-------|-------|----------|
| 0.5   | 50%   | Slow down for learning, analysis |
| 0.75  | 75%   | Slightly slower playback |
| 1.0   | 100%  | Normal speed (no change) |
| 1.25  | 125%  | Slightly faster |
| 1.5   | 150%  | 1.5x speed (common for podcasts) |
| 2.0   | 200%  | Double speed |

### Basic Usage
```bash
# Speed up to 1.5x
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=1.5" output.mp3

# Slow down to 75%
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=0.75" output.mp3
```

### Extreme Speeds (Chaining)

For speeds outside the 0.5-2.0 range, chain multiple `atempo` filters:

#### 4x Speed (2.0 × 2.0)
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=2.0,atempo=2.0" output.mp3
```

#### 0.25x Speed (0.5 × 0.5)
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=0.5,atempo=0.5" output.mp3
```

#### 3x Speed (1.5 × 2.0)
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=1.5,atempo=2.0" output.mp3
```

### Important Notes
- Tempo adjustment affects duration only (not pitch)
- Faster playback = shorter duration
- Slower playback = longer duration
- Audio quality is preserved (pitch remains the same)
- Cannot exceed 0.5-2.0 range per atempo filter (chain for extreme speeds)

---

## Metadata Parameters

The `-metadata` parameter allows you to embed metadata tags (like title, artist, album) into audio files.

### Syntax
```bash
-metadata key="value"
```

### Format Support

Different audio formats support different metadata standards:

| Format | Metadata Type | Support Level |
|--------|---------------|---------------|
| MP3    | ID3v2 tags    | Full support |
| AAC/M4A | iTunes-style  | Full support |
| FLAC   | Vorbis comments | Full support |
| Opus   | Vorbis comments | Full support |
| Ogg    | Vorbis comments | Full support |
| WAV    | BWF metadata  | Limited support |

### Common Metadata Tags

| Tag | Description | Example Usage |
|-----|-------------|---------------|
| `title` | Track/song title | `-metadata title="My Song"` |
| `artist` | Artist/performer name | `-metadata artist="John Doe"` |
| `album` | Album name | `-metadata album="Greatest Hits"` |
| `album_artist` | Album artist (if different from track artist) | `-metadata album_artist="Various Artists"` |
| `date` | Release year (YYYY format) | `-metadata date="2024"` |
| `genre` | Music genre | `-metadata genre="Rock"` |
| `track` | Track number | `-metadata track="3"` or `-metadata track="3/12"` |
| `disc` | Disc number | `-metadata disc="1"` or `-metadata disc="1/2"` |
| `comment` | Comments or notes | `-metadata comment="Remastered version"` |
| `composer` | Music composer | `-metadata composer="Jane Smith"` |
| `publisher` | Record label/publisher | `-metadata publisher="XYZ Records"` |
| `copyright` | Copyright information | `-metadata copyright="© 2024"` |
| `language` | Language code (ISO 639-2) | `-metadata language="eng"` |
| `encoded_by` | Software/person who encoded | `-metadata encoded_by="ffmpeg"` |

### Additional Tags

| Tag | Description | Example Usage |
|-----|-------------|---------------|
| `description` | Description or subtitle | `-metadata description="Live version"` |
| `lyrics` | Song lyrics (full text) | `-metadata lyrics="Lyrics text here"` |
| `conductor` | Orchestra conductor | `-metadata conductor="John Williams"` |
| `remixer` | Remix artist | `-metadata remixer="DJ Name"` |
| `bpm` | Beats per minute | `-metadata bpm="120"` |
| `www` | Related website URL | `-metadata www="https://example.com"` |

### Basic Usage Examples

#### Single Metadata Tag
```bash
ffmpeg -n -i input.wav -b:a 192k -metadata title="My Song" output.mp3
```

#### Multiple Metadata Tags
```bash
ffmpeg -n -i input.wav -b:a 192k \
  -metadata title="Song Title" \
  -metadata artist="Artist Name" \
  -metadata album="Album Name" \
  output.mp3
```

#### Complete Music Track Metadata
```bash
ffmpeg -n -i input.wav -b:a 320k \
  -metadata title="Track Name" \
  -metadata artist="Artist Name" \
  -metadata album="Album Name" \
  -metadata album_artist="Album Artist" \
  -metadata date="2024" \
  -metadata genre="Rock" \
  -metadata track="3/12" \
  -metadata disc="1/1" \
  -metadata composer="Composer Name" \
  -metadata copyright="© 2024" \
  output.mp3
```

#### Podcast Episode Metadata
```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 \
  -metadata title="Episode 42: AI Best Practices" \
  -metadata artist="Tech Podcast" \
  -metadata album="Season 2" \
  -metadata date="2024" \
  -metadata genre="Podcast" \
  -metadata track="42" \
  -metadata comment="Discussion about AI coding practices" \
  output.mp3
```

#### Audiobook Chapter Metadata
```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 \
  -metadata title="Chapter 5: The Journey Begins" \
  -metadata artist="Author Name" \
  -metadata album="Book Title" \
  -metadata genre="Audiobook" \
  -metadata track="5/20" \
  -metadata comment="Chapter 5 of 20" \
  output.mp3
```

### Best Practices

#### 1. Always Quote Values
Metadata values should always be quoted, especially if they contain spaces or special characters:
```bash
# Correct
-metadata title="My Song Title"

# Incorrect (will fail with spaces)
-metadata title=My Song Title
```

#### 2. Escape Special Characters
Use backslash escaping for quotes within values:
```bash
-metadata comment="Artist's \"Greatest\" Hit"
```

#### 3. Year Format
Use 4-digit year format (YYYY) for the `date` field:
```bash
# Correct
-metadata date="2024"

# Avoid
-metadata date="24"
```

#### 4. Track Number Format
Track numbers can use simple or fraction format:
```bash
# Simple format
-metadata track="3"

# Fraction format (track 3 of 12 total)
-metadata track="3/12"
```

#### 5. Language Codes
Use ISO 639-2 three-letter language codes:
```bash
-metadata language="eng"  # English
-metadata language="spa"  # Spanish
-metadata language="fra"  # French
```

### Advanced Metadata Operations

#### Preserve Existing Metadata
To copy metadata from input file to output file:
```bash
ffmpeg -n -i input.mp3 -b:a 192k -map_metadata 0 output.mp3
```

The `-map_metadata 0` copies all metadata from the input file (stream 0).

#### Clear All Metadata
To remove all metadata from the output file:
```bash
ffmpeg -n -i input.mp3 -b:a 192k -map_metadata -1 output.mp3
```

The `-map_metadata -1` strips all metadata.

#### Combine Preservation and New Tags
Copy existing metadata and add/override specific tags:
```bash
ffmpeg -n -i input.mp3 -b:a 192k \
  -map_metadata 0 \
  -metadata title="New Title" \
  -metadata date="2024" \
  output.mp3
```

This copies all existing metadata but overrides `title` and `date`.

### Viewing Metadata

To view metadata in an existing audio file:
```bash
ffmpeg -i input.mp3
```

This displays file information including all metadata tags.

For detailed metadata only:
```bash
ffmpeg -i input.mp3 -f ffmetadata -
```

### Common Use Cases

#### Music Library Organization
```bash
# Standard music track with full metadata
ffmpeg -n -i input.wav -b:a 320k \
  -metadata title="Track Title" \
  -metadata artist="Artist Name" \
  -metadata album="Album Name" \
  -metadata date="2024" \
  -metadata genre="Pop" \
  -metadata track="7/15" \
  output.mp3
```

#### Podcast Production
```bash
# Podcast episode with descriptive metadata
ffmpeg -n -i input.wav -b:a 64k -ac 1 \
  -metadata title="Ep. 100: Special Episode" \
  -metadata artist="Podcast Name" \
  -metadata album="Season 5" \
  -metadata genre="Podcast" \
  -metadata date="2024" \
  -metadata comment="Celebrating 100 episodes" \
  output.mp3
```

#### Voice Recordings
```bash
# Interview or voice memo
ffmpeg -n -i input.wav -b:a 64k -ac 1 \
  -metadata title="Interview with John Doe" \
  -metadata artist="Interviewer Name" \
  -metadata date="2024" \
  -metadata genre="Speech" \
  -metadata comment="Recorded at conference" \
  output.mp3
```

### Important Notes

1. **Metadata is optional**: If you don't specify any `-metadata` flags, the output may preserve existing metadata or have none
2. **No validation**: ffmpeg doesn't validate metadata values; any text is accepted
3. **UTF-8 support**: Unicode characters are supported in ID3v2 tags
4. **Character limits**: While most fields support long text, keeping values under 255 characters is recommended for compatibility
5. **Format compatibility**: Not all metadata tags work with all formats; MP3, AAC, and FLAC have the best support
6. **Multiple values**: You can specify the same tag multiple times, but typically the last value wins
7. **Case sensitive**: Tag names are case-sensitive (`title` not `Title`)

---

## Format-Specific Recommendations

### For Podcasts and Voice
**Format**: MP3 or AAC
**Settings**: Mono, lower bitrate, standard sample rate
```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 -ar 44100 output.mp3
```

### For Music (Lossy)
**Format**: MP3 or AAC
**Settings**: Stereo, higher bitrate, standard sample rate
```bash
ffmpeg -n -i input.wav -b:a 192k -ac 2 -ar 44100 output.mp3
```

### For Music (Lossless)
**Format**: FLAC
**Settings**: Stereo, high sample rate
```bash
ffmpeg -n -i input.wav -ar 48000 -ac 2 output.flac
```

### For Audiobooks
**Format**: MP3 or AAC
**Settings**: Mono, low bitrate, standard sample rate, possibly faster tempo
```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 -ar 44100 -af "atempo=1.25" output.mp3
```

### For Web Streaming
**Format**: AAC or Opus
**Settings**: Optimized for bandwidth
```bash
ffmpeg -n -i input.wav -b:a 128k -ac 2 -ar 48000 output.m4a
```

---

## Quality Guidelines

### By Bitrate (MP3)

| Bitrate | Quality Level | File Size (per min) | Recommended For |
|---------|---------------|---------------------|-----------------|
| 32k     | Very Low      | ~240 KB             | Voice-only, minimal |
| 64k     | Low           | ~480 KB             | Podcasts, speech |
| 96k     | Acceptable    | ~720 KB             | Low-quality music |
| 128k    | Standard      | ~960 KB             | General music |
| 192k    | Good          | ~1.4 MB             | High-quality music |
| 256k    | High          | ~1.9 MB             | Professional music |
| 320k    | Maximum       | ~2.4 MB             | Highest quality MP3 |

### By Format (Comparative Quality)

| Format | Quality Type | Typical Bitrate | File Size | Best For |
|--------|--------------|-----------------|-----------|----------|
| MP3    | Lossy        | 128k-320k       | Medium    | General use |
| AAC    | Lossy        | 128k-256k       | Medium    | Modern devices |
| Opus   | Lossy        | 64k-128k        | Small     | Voice, streaming |
| Ogg    | Lossy        | 128k-192k       | Medium    | Open-source |
| WAV    | Lossless     | N/A             | Large     | Professional |
| FLAC   | Lossless     | N/A             | Medium    | Archival |

---

## Advanced Topics

### Checking Input File Properties

Before conversion, examine the input file properties:

```bash
ffmpeg -i input.mp3
```

This displays:
- Current format and codec
- Bitrate
- Sample rate
- Number of channels
- Duration

### Conversion Best Practices

1. **Never upconvert quality**: Converting low bitrate to high bitrate doesn't improve quality
2. **Match or reduce quality**: Only convert to same or lower bitrate
3. **Preserve lossless**: If input is lossless (WAV, FLAC), use lossless output or high bitrate
4. **Consider use case**: Optimize for intended use (voice vs. music vs. archival)
5. **Test output**: Listen to converted file to verify quality

### Understanding Lossless vs. Lossy

**Lossless Formats** (WAV, FLAC):
- Preserve original audio data completely
- Larger file sizes
- Perfect for editing, archival
- Don't use bitrate parameter

**Lossy Formats** (MP3, AAC, Opus, Ogg):
- Compress by removing inaudible data
- Smaller file sizes
- Good enough for listening
- Use bitrate parameter for quality control

### File Size Estimation

Approximate file size calculation:
```
File Size (MB) = (Bitrate in kbps × Duration in seconds) / 8000
```

**Example**: 192kbps, 5-minute song
```
File Size = (192 × 300) / 8000 = 7.2 MB
```

### Common Mistakes

1. **Forgetting the `-n` flag**: Always use `-n` to prevent overwrite
2. **Wrong bitrate format**: Use `128k`, not `128` or `128kbps`
3. **Upconverting quality**: Converting 128k MP3 to 320k doesn't improve quality
4. **Extreme tempo without chaining**: Use multiple atempo filters for speeds outside 0.5-2.0
5. **Unnecessary parameters**: Don't specify channels or sample rate if you want to keep the input values

---

## Quick Reference Commands

### Basic Conversion
```bash
ffmpeg -n -i input.wav -b:a 192k output.mp3
```

### Mono Voice (Podcast)
```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 -ar 44100 output.mp3
```

### High-Quality Music
```bash
ffmpeg -n -i input.wav -b:a 320k -ac 2 -ar 48000 output.mp3
```

### Fast Playback (1.5x)
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=1.5" output.mp3
```

### Lossless Conversion
```bash
ffmpeg -n -i input.wav -ar 48000 output.flac
```

### Complete Conversion (All Parameters)
```bash
ffmpeg -n -i input.wav -b:a 192k -ac 2 -ar 44100 -af "atempo=1.25" output.mp3
```

### With Metadata
```bash
ffmpeg -n -i input.wav -b:a 192k -metadata title="My Song" -metadata artist="Artist Name" output.mp3
```

### Complete with Metadata and Audio Parameters
```bash
ffmpeg -n -i input.wav -b:a 192k -ac 2 -ar 44100 -af "atempo=1.25" -metadata title="Fast Version" -metadata artist="Artist Name" -metadata album="Remixes" output.mp3
```

---

## Additional Resources

- ffmpeg Official Documentation: https://ffmpeg.org/documentation.html
- ffmpeg Audio Filters: https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters
- Audio Codec Comparison: Various online resources for format comparison

---

## Summary

- **Bitrate** (`-b:a`): Controls quality and file size (128k, 192k, 320k)
- **Channels** (`-ac`): Mono (1) or Stereo (2), defaults to input
- **Sample Rate** (`-ar`): Frequency in Hz (44100, 48000), defaults to input
- **Tempo** (`-af "atempo="`): Speed adjustment (0.5-2.0), chain for extreme speeds
- **Metadata** (`-metadata key="value"`): Optional tags for title, artist, album, etc. (can be repeated)
- **Format**: Auto-detected from output file extension
- **Overwrite**: Always use `-n` flag to prevent overwriting existing files

This reference provides the foundation for understanding audio conversion parameters. Refer back to SKILL.md for workflow instructions and common examples.
