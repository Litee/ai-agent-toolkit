---
name: generate-podcast-audio-local
description: Use when generating podcast audio locally using VibeVoice MLX on Apple Silicon. Triggers on "generate podcast audio locally", "local TTS", "VibeVoice MLX", "generate audio on Mac", "local podcast audio", or any request to turn a podcast script into audio using local ML inference.
---

# Podcast Audio Generator (MLX — Local Apple Silicon)

**Prerequisites**: Apple Silicon Mac (M1/M2/M3/M4), Python 3.10+, `uv`, `vibevoice-mlx` installed, `ffmpeg`/`ffprobe` (for loudness normalization and tempo analysis).

Convert formatted podcast scripts into high-quality audio using VibeVoice MLX — a local text-to-speech pipeline running entirely on Apple Silicon with no cloud infrastructure required.

## Single-Script Workflow

Unlike the AWS Bedrock version, this skill uses a **single script** — no infrastructure setup, no IAM roles, no EC2 instances. The script automatically clones `vibevoice-mlx`, installs dependencies, runs generation, and cleans up the temp directory.

```bash
python3 ${SKILL_DIR}/scripts/generate_podcast_audio.py \
  --script-path podcast_20251025143000.md \
  --speaker-names Alice Frank
```

**No `--voices-dir` needed** — the script uses bundled demo voices (Alice, Frank, Carter) by default. Override with `--voices-dir` if you have custom voices.

## Script Format

- Must use **"Speaker N:"** format for each line (e.g., `Speaker 1: Hello, welcome to...`)
- Maximum audio duration: **60 minutes** (1 hour) — enforced by the ML model
- Validate script length before generating to avoid wasted time

## Voice Files

- **Bundled voices** — the skill ships three demo voices, pre-normalized to the EBU R128 broadcast standard (integrated −23 LUFS, true peak −1 dBTP, 24 kHz):
  - **Alice** (woman), **Frank** (man), **Carter** (man)
  - No `--voices-dir` needed — these are used automatically, so a first run works out of the box.
- **Custom voices**: Use `--voices-dir /path/to/voices` to specify a custom directory.
- **Matching**: Voice names are matched case-insensitively against WAV filename stems (substring match)
- Voice files should be short reference clips (5-30 seconds work best)
- **New voices must be normalized first**: VibeVoice clones loudness along with timbre, so mismatched reference clips make one speaker louder than the other for the whole episode (the demo Alice clip is ~10 LU hotter than the male voices and clips at +0.1 dBTP). Run `scripts/normalize_voices.py` on any new voice directory to bring it to the same EBU R128 standard as the bundled voices:
  ```bash
  python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir /path/to/voices
  ```
- **Source**: the bundled voices come from the [vibevoice-community/VibeVoice](https://github.com/vibevoice-community/VibeVoice/tree/main/demo/voices) demo set (`en-Alice_woman.wav`, `en-Frank_man.wav`, `en-Carter_man.wav`), normalized to the standard above.

## Output Naming

Output files are saved to the **current working directory** with auto-generated names:
- Format: `{slugified-script-name}_{YYYYMMDDHHmmss}.wav`
- Example: `my-podcast_20260623192807.wav`
- The slug is lowercase with hyphens, timestamp is digits only

## Loudness Normalization (Output)

Generated audio is normalized to podcast delivery standards using a two-pass ffmpeg `loudnorm` (linear gain, no compression):
- **Target**: integrated −16 LUFS, true peak −1 dBTP (Apple Podcasts recommendation, the de facto podcast target)
- Override with `--target-lufs` / `--target-tp` (e.g. `--target-lufs -14` for Spotify/YouTube playback normalization)
- Disable with `--no-normalize-output`
- The final loudness and its deviation from target are reported after generation. Because `loudnorm` applies only linear gain, a result slightly under target (usually within the ±1 LU delivery QC tolerance) is expected when boosting would breach the true-peak ceiling.

## Execution Time

- **First run**: Downloads the model (~5GB) — adds significant initial delay
- **Subsequent runs**: Much faster, model is cached
- **Estimate formula**: `word_count * 0.03` minutes
  - Example: 2,000 words ≈ 60 minutes on M2 Pro
  - Example: 1,000 words ≈ 30 minutes on M2 Pro
- Faster on M3/M4 chips; slower on M1

## Automatic Cleanup

N/A — local execution, no remote resources to clean up.

## Required: Read Detailed Instructions First

Before using this skill, read [`references/generate-podcast-audio-local.md`](references/generate-podcast-audio-local.md) in full.

The reference contains essential information about:
- Complete parameter details, model options, and quantization settings
- Voice file preparation and naming conventions
- Tempo analysis and drift thresholds
- Troubleshooting guide for common issues
- Performance tips for faster generation

The information below is only a quick overview.

## Required Inputs

- **Script file**: Must follow the "Speaker N:" format for each line
  - **Duration Limit**: The ML model has a maximum limit of 60 minutes (1 hour) for audio generation
  - **Validation Required**: Before generating audio, validate the script duration and ask for user confirmation if it may exceed 60 minutes
- **Voice selection**: Voice names for each speaker; WAV voice files resolve from `--voices-dir`, the `LOCAL_TTS_VOICES_DIR` environment variable, or the bundled demo voices (Alice, Frank, Carter)
- **Voices directory** (optional): Path to a local directory with custom voice WAV files; if omitted, bundled demo voices are used
- **Speech tempo**: Track the speech_tempo value from script generation (default: 175 WPM)
  - Used for mandatory tempo analysis after audio generation
  - Needed to calculate drift and determine if speed adjustment is required
- **Model** (optional): Full model ID — `gafiatulin/vibevoice-7b-mlx` (default, higher quality) or `gafiatulin/vibevoice-1.5b-mlx` (faster)
- **Quantization** (optional): `4` (smallest, fastest) or `8` (default, balanced)
- **Seed** (optional): Random seed for reproducibility (default: `42`)

## Execution Time Estimates

**BEFORE running the Python script**, calculate execution time estimate:

```bash
# Count words in script
word_count=$(python3 ${SKILL_DIR}/scripts/calculate_podcast_metrics.py count-words --file script.md)

# Calculate estimate: word_count * 0.03 minutes
# Example: 2,000 words ≈ 60 minutes (2000 * 0.03)
```

### Communicate Expected Completion Time

After starting audio generation:
1. Calculate estimated completion time: `word_count * 0.03` minutes
2. Tell the user the expected completion time and clock time
3. Inform user they can ask for status after that time
4. Do not continuously poll — this wastes tokens

**Example message to user:**
```
✅ Audio generation started successfully!

📊 Execution Details:
   Word count: 2,000 words
   Estimated duration: ~60 minutes
   Expected completion: ~4:00 PM

⏰ You can ask me for status after 4:00 PM and I'll check the results.
```

## Workflow Overview

1. **Validate environment** — Check Python 3.10+, uv, git, ffprobe availability
2. **Clone vibevoice-mlx** — Script clones repo to temp dir, installs deps, cleans up after
3. **Verify voices** — Bundled demo voices (Alice, Frank, Carter) by default, or custom voices via `--voices-dir` (new voices should be normalized first with `scripts/normalize_voices.py`)
4. **Validate script** — Check format, count words/speakers
5. **Execute MLX** — Run `uv run vibevoice-mlx` with text that preserves `Speaker N:` prefixes (model uses them to assign voices to segments)
6. **Verify output** — Confirm WAV file exists and has reasonable size
7. **Loudness normalization** — Normalize output to podcast delivery standard (−16 LUFS / −1 dBTP by default); report achieved loudness vs target
8. **Tempo analysis** — Analyze speech rate using `ffprobe`, calculate drift percentage
9. **Metadata + Recommendations** — Extract metadata via sub-agent, display results, recommend speed adjustment if drift > 5%

### Output

- **WAV file**: High-quality uncompressed audio (always preserved)
- **Loudness normalization**: Output normalized to −16 LUFS / −1 dBTP (Apple Podcasts target) with reported deviation; overridable via `--target-lufs`/`--target-tp`
- **Tempo analysis report**: Actual vs. target WPM, drift percentage, speed factor
- **Metadata display**: Title, artist, and description extracted from script for audio conversion
- **Recommendation**: If drift > 5%, recommend using `convert-audio:convert-audio` skill with speed adjustment

## Bundled Resources

- **scripts/generate_podcast_audio.py** — Main audio generation script (auto-clones vibevoice-mlx, runs generation, cleans up)
- **scripts/normalize_voices.py** — Normalize new voice reference clips to EBU R128 (−23 LUFS / −1 dBTP, 24 kHz); bundled voices are already normalized, run only for new voices
- **scripts/calculate_podcast_metrics.py** — Word counting and duration calculations
- **references/generate-podcast-audio-local.md** — Complete usage guide

## Related Skills

- **`podcast-generation:generate-podcast-script`** — Generate the AI-powered podcast script that feeds into this audio pipeline.
- **`convert-audio:convert-audio`** — Convert the generated WAV to MP3, apply tempo adjustment when drift > 5%, and embed ID3 metadata tags.
