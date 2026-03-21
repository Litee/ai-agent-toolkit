---
name: convert-audio
description: Convert audio files between formats using ffmpeg. Use when converting audio formats (MP3, WAV, AAC, FLAC, Opus, OGG), adjusting bitrate/quality, changing sample rate/channels, modifying playback speed, or adding/editing audio metadata (ID3 tags, title, artist, album). Triggers on "convert audio", "change audio format", "compress audio", "adjust bitrate", "audio metadata tags", "add ID3 tags", "change playback speed", or any request to process an audio file with ffmpeg.
---

# Audio Conversion Skill

## Purpose

This skill guides you to convert audio files between different formats and adjust audio parameters using ffmpeg directly. Use this skill when users need to:

- Convert audio files between formats (MP3, WAV, AAC, FLAC, Opus, OGG, etc.)
- Adjust audio bitrate or quality
- Change sample rate (frequency) or number of channels
- Modify playback speed (tempo)
- Perform single-file audio conversions with explicit parameter control

## Prerequisites

### Check ffmpeg Installation

**ALWAYS check if ffmpeg is installed before attempting conversion:**

```bash
which ffmpeg
```

If ffmpeg is not installed, **ask the user for explicit permission** before installing it.

### Installation Instructions (only with user permission)

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install ffmpeg
```

**Other Linux:**
```bash
sudo yum install ffmpeg  # RHEL/CentOS
```

## Core Parameters

### Required Parameters

1. **Input Audio File Path** (required)
   - Path to the source audio file
   - Validate that the file exists before conversion

2. **Output Audio File Path** (required)
   - Path for the converted audio file
   - **IMPORTANT**: Always use `-n` flag to prevent overwriting existing files
   - If the output file exists, the user must handle the conflict (rename, delete, etc.)

3. **Output Bitrate** (required for lossy formats; omit for lossless like FLAC/WAV)
   - Specify the target bitrate explicitly
   - Format: `128k`, `192k`, `256k`, `320k`, etc.
   - Higher bitrate = better quality, larger file size
   - Common values:
     - `64k` - Low quality, voice-optimized
     - `128k` - Standard quality
     - `192k` - Good quality
     - `256k` - High quality
     - `320k` - Maximum quality (MP3)

### Optional Parameters

4. **Output Format** (default: MP3)
   - Determined by output file extension
   - Supported formats: `.mp3`, `.wav`, `.aac`, `.m4a`, `.flac`, `.opus`, `.ogg`
   - ffmpeg auto-detects format from extension

5. **Number of Channels** (default: keep input)
   - `-ac 1` - Mono
   - `-ac 2` - Stereo
   - If not specified, ffmpeg preserves input channel count

6. **Audio Frequency / Sample Rate** (default: keep input)
   - `-ar 44100` - CD quality (44.1 kHz)
   - `-ar 48000` - DVD/professional quality (48 kHz)
   - `-ar 22050` - Half of CD quality
   - If not specified, ffmpeg preserves input sample rate

7. **Tempo Factor** (default: 1.0)
   - Uses the `atempo` audio filter
   - Range: 0.5 to 2.0 (outside this range requires chaining)
   - `0.5` - Half speed (50%)
   - `1.0` - Normal speed (no change)
   - `1.5` - 1.5x speed (150%)
   - `2.0` - Double speed (200%)
   - **Note**: Changing tempo affects duration but not pitch

8. **Metadata Tags** (default: none)
   - Optional metadata to embed in the output audio file
   - Supports standard ID3v2 tags for MP3 and equivalent tags for other formats
   - Specify using `-metadata key="value"` for each tag
   - Multiple metadata tags can be combined in a single command
   - Common tags:
     - `-metadata title="Song Title"` - Track/song title
     - `-metadata artist="Artist Name"` - Artist/performer name
     - `-metadata album="Album Name"` - Album name
     - `-metadata date="2024"` - Release year (YYYY format)
     - `-metadata genre="Genre"` - Music genre
     - `-metadata track="3"` - Track number (can use "3/12" format)
     - `-metadata comment="Comments"` - Comments or notes
   - Additional supported tags: `album_artist`, `composer`, `publisher`, `copyright`, `language`, `encoded_by`, `disc`, `bpm`
   - If not specified, no metadata is added (or existing metadata may be preserved)

## Overwrite Policy

**CRITICAL**: Always include the `-n` flag in ffmpeg commands to prevent overwriting existing files.

- If the output file already exists, ffmpeg will exit with an error
- The user is responsible for handling file conflicts (rename, delete, move)
- Never use `-y` (auto-overwrite) flag

## Command Construction

### Basic Template

```bash
ffmpeg -n -i <input_file> -b:a <bitrate> [-ac <channels>] [-ar <sample_rate>] [-af "atempo=<tempo>"] [-metadata key="value"] <output_file>
```

### Parameter Order

1. `-n` - No overwrite flag (always first after ffmpeg)
2. `-i <input_file>` - Input file
3. `-b:a <bitrate>` - Output bitrate
4. `-ac <channels>` - Number of channels (optional)
5. `-ar <sample_rate>` - Sample rate (optional)
6. `-af "atempo=<tempo>"` - Tempo adjustment (optional)
7. `-metadata key="value"` - Metadata tags (optional, can be repeated)
8. `<output_file>` - Output file path

## Common Examples

### Example 1: Basic Format Conversion
Convert WAV to MP3 with 192k bitrate:

```bash
ffmpeg -n -i input.wav -b:a 192k output.mp3
```

### Example 2: Change Bitrate Only
Convert MP3 to lower bitrate MP3:

```bash
ffmpeg -n -i input.mp3 -b:a 128k output.mp3
```

### Example 3: Convert to Mono with Specific Sample Rate
Convert stereo to mono, 44.1kHz, 128k bitrate:

```bash
ffmpeg -n -i input.mp3 -b:a 128k -ac 1 -ar 44100 output.mp3
```

### Example 4: Adjust Playback Speed
Convert and increase speed to 1.25x:

```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=1.25" output.mp3
```

### Example 5: Convert to High-Quality AAC
Convert to AAC format with high bitrate:

```bash
ffmpeg -n -i input.mp3 -b:a 256k output.m4a
```

### Example 6: Combined Parameters
Convert to mono, 48kHz, 1.5x speed, 192k bitrate:

```bash
ffmpeg -n -i input.wav -b:a 192k -ac 1 -ar 48000 -af "atempo=1.5" output.mp3
```

For lossless conversion, metadata tagging, and complex combined-parameter examples, see `references/advanced-examples.md`.

## Workflow

1. **Validate Prerequisites** — `which ffmpeg`; ask user for permission before installing
2. **Validate Input File** — `ls -lh <input_file>`
3. **Check Output Conflict** — if `<output_file>` exists, ask user to rename/delete/move it
4. **Construct Command** — use template: `ffmpeg -n -i <input> [-b:a <bitrate>] [-ac <ch>] [-ar <rate>] [-af "atempo=<n>"] [-metadata key="value" ...] <output>`
5. **Execute** — run the command
6. **Verify** — `ls -lh <output_file>`

## Error Handling

### Common Errors

1. **Output file exists**
   - Error: `File 'output.mp3' already exists. Exiting.`
   - Solution: User must rename, delete, or move the existing file

2. **Input file not found**
   - Error: `No such file or directory`
   - Solution: Verify the input file path is correct

3. **ffmpeg not installed**
   - Error: `command not found: ffmpeg`
   - Solution: Ask user for permission to install ffmpeg

4. **Invalid bitrate format**
   - Error: Various ffmpeg errors
   - Solution: Use format like `128k`, `192k`, not `128` or `128kbps`

5. **Invalid tempo value**
   - Error: `Value must be in range [0.5, 2.0]`
   - Solution: Use tempo between 0.5 and 2.0, or chain multiple atempo filters for extreme speeds

6. **Unsupported format**
   - Error: `Unable to find a suitable output format`
   - Solution: Check the output file extension is supported

## Advanced: Chaining Tempo for Extreme Speeds

For tempo factors outside 0.5-2.0 range, chain multiple atempo filters:

**Example: 4x speed (2.0 × 2.0)**
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=2.0,atempo=2.0" output.mp3
```

**Example: 0.25x speed (0.5 × 0.5)**
```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=0.5,atempo=0.5" output.mp3
```

## Reference Documentation

- **`references/advanced-examples.md`** — Examples 7–12: lossless conversion, slow-down, metadata tagging (podcast, album, combined), full metadata tag table, preserve/clear metadata commands
- **`references/ffmpeg-parameters.md`** — Full codec details, format-specific support, and advanced ffmpeg options

## Summary

- Always check ffmpeg installation first
- Validate input file exists
- Always use `-n` flag (no overwrite)
- Bitrate is required for most formats
- Channels and sample rate default to input values
- Tempo must be between 0.5 and 2.0 (chain for extreme speeds)
- Metadata tags are optional and can be added with `-metadata key="value"`
- Let the user handle output file conflicts
