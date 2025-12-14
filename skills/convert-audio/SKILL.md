---
name: convert-audio
description: Convert audio files between formats using ffmpeg. Use when converting audio formats (MP3, WAV, AAC, FLAC, Opus, OGG), adjusting bitrate/quality, changing sample rate/channels, or modifying playback speed.
dependencies: ffmpeg
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

3. **Output Bitrate** (required)
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

### Example 7: Convert to Different Format with Quality
Convert MP3 to FLAC (lossless) with specific sample rate:

```bash
ffmpeg -n -i input.mp3 -ar 48000 output.flac
```
*Note: FLAC is lossless, so bitrate is not specified*

### Example 8: Slow Down Audio
Convert and slow down to 75% speed:

```bash
ffmpeg -n -i input.mp3 -b:a 192k -af "atempo=0.75" output.mp3
```

### Example 9: Basic Metadata (Title and Artist)
Convert WAV to MP3 with title and artist metadata:

```bash
ffmpeg -n -i input.wav -b:a 192k -metadata title="My Song" -metadata artist="John Doe" output.mp3
```

### Example 10: Complete Album Metadata
Convert to MP3 with comprehensive album metadata:

```bash
ffmpeg -n -i input.wav -b:a 320k -metadata title="Track Name" -metadata artist="Artist Name" -metadata album="Album Name" -metadata date="2024" -metadata genre="Rock" -metadata track="3/12" output.mp3
```

### Example 11: Podcast Episode Metadata
Convert to mono MP3 optimized for podcasts with metadata:

```bash
ffmpeg -n -i input.wav -b:a 64k -ac 1 -metadata title="Episode 42: AI Best Practices" -metadata artist="Tech Podcast" -metadata album="Season 2" -metadata date="2024" -metadata genre="Podcast" -metadata comment="Discussion about AI coding practices" output.mp3
```

### Example 12: Combined Parameters with Metadata
Convert with all parameters including speed adjustment and metadata:

```bash
ffmpeg -n -i input.wav -b:a 192k -ac 2 -ar 44100 -af "atempo=1.25" -metadata title="Fast Version" -metadata artist="Artist Name" -metadata album="Remixes" output.mp3
```

## Workflow Instructions

### Step 1: Validate Prerequisites
```bash
which ffmpeg
```

If ffmpeg is not found, ask the user for permission to install it.

### Step 2: Validate Input File
```bash
ls -lh <input_file>
```

Confirm the input file exists and display its size.

### Step 3: Check Output File Conflict
```bash
ls <output_file> 2>/dev/null
```

If the output file exists, inform the user and ask them to:
- Provide a different output filename
- Delete the existing file
- Move the existing file

### Step 4: Construct ffmpeg Command

Based on user requirements, build the command:
1. Start with: `ffmpeg -n -i <input_file>`
2. Add required bitrate: `-b:a <bitrate>`
3. Add optional audio parameters if specified:
   - `-ac <channels>` (if user wants to change channels)
   - `-ar <sample_rate>` (if user wants to change sample rate)
   - `-af "atempo=<tempo>"` (if user wants to change speed)
4. Add optional metadata tags if specified:
   - `-metadata title="value"` (for track title)
   - `-metadata artist="value"` (for artist name)
   - Additional `-metadata key="value"` flags as needed
5. End with: `<output_file>`

### Step 5: Execute Conversion
Run the constructed ffmpeg command.

### Step 6: Verify Output
```bash
ls -lh <output_file>
```

Confirm the output file was created and display its size.

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

## Metadata Guidelines

### Supported Formats

- **MP3**: Full ID3v2 tag support
- **AAC/M4A**: Supports iTunes-style metadata (similar tags)
- **FLAC**: Supports Vorbis comments (same tag names work)
- **Opus/OGG**: Supports Vorbis comments
- **WAV**: Limited metadata support (use BWF metadata)

### Best Practices

1. **Quote Values**: Always quote metadata values to handle spaces and special characters
   ```bash
   -metadata title="My Song Title"
   ```

2. **Escape Special Characters**: Use backslash escaping for quotes within values
   ```bash
   -metadata comment="Artist's \"Greatest\" Hit"
   ```

3. **Preserve Existing Metadata**: To copy metadata from input to output:
   ```bash
   ffmpeg -n -i input.mp3 -b:a 192k -map_metadata 0 output.mp3
   ```

4. **Clear All Metadata**: To remove all metadata:
   ```bash
   ffmpeg -n -i input.mp3 -b:a 192k -map_metadata -1 output.mp3
   ```

5. **Year Format**: Use YYYY format for date field (e.g., "2024", not "24")

6. **Track Numbers**: Can use simple format "3" or fraction format "3/12" (track 3 of 12 total)

### Common Metadata Patterns

#### For Music Files
```bash
-metadata title="Song Title" -metadata artist="Artist Name" -metadata album="Album Name" -metadata date="2024" -metadata genre="Rock" -metadata track="3"
```

#### For Podcasts
```bash
-metadata title="Episode Title" -metadata artist="Podcast Name" -metadata album="Season/Series" -metadata genre="Podcast" -metadata date="2024" -metadata comment="Episode description"
```

#### For Audiobooks
```bash
-metadata title="Chapter Title" -metadata artist="Author Name" -metadata album="Book Title" -metadata genre="Audiobook" -metadata track="5" -metadata comment="Chapter 5"
```

### All Supported Metadata Tags

| Tag | Description | Example |
|-----|-------------|---------|
| `title` | Track/song title | "My Song" |
| `artist` | Artist/performer name | "John Doe" |
| `album` | Album name | "Greatest Hits" |
| `album_artist` | Album artist (if different) | "Various Artists" |
| `date` | Release year (YYYY) | "2024" |
| `genre` | Music genre | "Rock" |
| `track` | Track number | "3" or "3/12" |
| `disc` | Disc number | "1" or "1/2" |
| `comment` | Comments or notes | "Remastered" |
| `composer` | Music composer | "Jane Smith" |
| `publisher` | Record label/publisher | "XYZ Records" |
| `copyright` | Copyright information | "© 2024" |
| `language` | Language code | "eng" |
| `encoded_by` | Encoder software/person | "ffmpeg" |
| `description` | Description or subtitle | "Live version" |
| `lyrics` | Song lyrics | "Full lyrics text" |
| `conductor` | Orchestra conductor | "John Williams" |
| `bpm` | Beats per minute | "120" |

## Reference Documentation

For detailed parameter documentation, see:
- `references/ffmpeg-parameters.md` - Comprehensive parameter reference

## Summary

- Always check ffmpeg installation first
- Validate input file exists
- Always use `-n` flag (no overwrite)
- Bitrate is required for most formats
- Channels and sample rate default to input values
- Tempo must be between 0.5 and 2.0 (chain for extreme speeds)
- Metadata tags are optional and can be added with `-metadata key="value"`
- Let the user handle output file conflicts
