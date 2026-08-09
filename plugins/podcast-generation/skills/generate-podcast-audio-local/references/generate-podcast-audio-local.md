# Generate Podcast Audio from Script (MLX — Local Apple Silicon)

Convert formatted podcast scripts into high-quality audio using VibeVoice MLX running entirely on your Apple Silicon Mac. No cloud infrastructure, no AWS account, no GPU instances — just local inference using Apple's MLX framework.

## Overview

VibeVoice MLX is a local text-to-speech pipeline that leverages Apple's MLX framework for efficient inference on Apple Silicon (M1/M2/M3/M4). It clones the VibeVoice repository and runs TTS generation locally, using the Mac's unified memory and Neural Engine.

### How It Differs from AWS Version

| Aspect | AWS Bedrock | MLX (Local) |
|--------|-------------|-------------|
| **Infrastructure** | EC2 GPU instance, S3, Step Functions | None — runs directly on your Mac |
| **Setup** | One-time AWS infrastructure setup required | Clone and install vibevoice-mlx once |
| **Cost** | ~$1.35/hr per run | Free (uses your hardware) |
| **Privacy** | Audio processed on remote EC2 | Entirely local, no data leaves your machine |
| **Speed** | Fast on g6.4xlarge GPU | Slower, depends on Mac chip (M2 Pro ~60 min for 2000 words) |
| **Hardware** | AWS provides GPU | Requires Apple Silicon Mac |
| **First run** | Installs dependencies on EC2 | Downloads model (~5GB) locally |
| **Cleanup** | Automatic EC2/S3 cleanup | N/A — no remote resources |

### When to Use Local vs. AWS

**Use MLX (Local) when:**
- You need privacy — audio must not leave your machine
- You want zero cost per generation
- You have an Apple Silicon Mac available
- You prefer simplicity — no AWS account or infrastructure needed

**Use AWS Bedrock when:**
- You need faster generation (GPU instances are quicker than CPU/Neural Engine)
- You don't have Apple Silicon hardware
- You're generating at scale and need parallel execution
- You have an AWS account and budget for ~$1.35 per run

## Prerequisites

### Hardware
- **Apple Silicon Mac**: M1, M2, M3, or M4 (any variant)
- **RAM**: 16GB recommended (8GB may work with quantized models)
- **Disk space**: ~10GB free (5GB for model, 5GB for temporary files)

### Software
- **Python 3.10+**: Verify with `python3 --version`
- **uv**: Python package manager. Install if needed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **ffmpeg / ffprobe**: Used for loudness normalization and tempo analysis. Install with `brew install ffmpeg`
- **vibevoice-mlx**: Clone and install the local MLX pipeline:
  ```bash
  git clone https://github.com/umputun/vibevoice-mlx.git
  cd vibevoice-mlx
  uv venv
  source .venv/bin/activate
  uv pip install -e .
  ```

### Verification Commands
```bash
# Verify Python version
python3 --version

# Verify uv
uv --version

# Verify ffprobe
ffprobe -version

# Verify vibevoice-mlx
cd vibevoice-mlx
source .venv/bin/activate
python3 -c "import mlx.core as mx; print('MLX available:', mx.metal.is_available())"
```

## Parameters

### generate_podcast_audio.py

- **--script-path** (required): Path to existing script file
- **--speaker-names** (required): Space-separated list of speaker voice names in order (first voice = Speaker 1, second = Speaker 2, etc.). Example: `Alice Frank`
- **--voices-dir** (optional): Path to a local directory containing custom voice WAV files (defaults to the bundled demo voices: Alice, Frank, Carter)
- **--target-lufs** (optional): Target integrated loudness for the output audio in LUFS (default: `-16`, Apple Podcasts recommendation). Use `-14` for Spotify/YouTube playback normalization
- **--target-tp** (optional): Target true peak for the output audio in dBTP (default: `-1`)
- **--normalize-output / --no-normalize-output** (optional): Normalize the generated audio to `--target-lufs`/`--target-tp`. **On by default**; use `--no-normalize-output` to skip
- **--model-size** (optional): Model size — `7b` (default, higher quality) or `1.5b` (faster, lower quality)
- **--quantization** (optional): Quantization bits — `4` (smallest, fastest) or `8` (default, balanced quality)
- **--diffusion** (optional): Enable diffusion for higher quality (adds ~30% generation time)
- **--output-dir** (optional): Local directory for audio output (defaults to current directory)
- **--verbose** (optional): Enable detailed progress output

### Model Options

| Option | Value | Description |
|--------|-------|-------------|
| Model size | `7b` (default) | 7-billion parameter model, highest quality |
| Model size | `1.5b` | 1.5-billion parameter model, faster generation |
| Quantization | `8` (default) | 8-bit quantization, balanced quality/speed |
| Quantization | `4` | 4-bit quantization, fastest, slight quality loss |
| Diffusion | Not set (default) | Standard generation |
| Diffusion | `--diffusion` | Enable diffusion, higher quality, ~30% slower |

**Recommended for speed**: `--model-size 1.5b --quantization 8 --diffusion`
**Recommended for quality**: `--model-size 7b --quantization 8` (no diffusion)
**Maximum speed**: `--model-size 1.5b --quantization 4`

### Voice File Naming Conventions

Voice files must be placed in the voices directory (`--voices-dir`, the `LOCAL_TTS_VOICES_DIR` environment variable, or the skill's bundled `assets/voices/`).

**Custom voice naming**: `{speaker_num}_{name}.wav`
- `speaker_num`: Must match the "Speaker N:" number in the script (1, 2, 3, etc.)
- `name`: Any descriptive name for the voice

**Examples:**
```
1_Alice.wav
2_Frank.wav
3_Sam.wav
```

**Bundled voices** (available without custom voice files — the skill works out of the box):
- **Alice** (woman), **Carter** (man), **Frank** (man)
- Sourced from the [vibevoice-community/VibeVoice](https://github.com/vibevoice-community/VibeVoice/tree/main/demo/voices) demo set (`en-Alice_woman.wav`, `en-Carter_man.wav`, `en-Frank_man.wav`)
- Pre-normalized to **EBU R128** (−23 LUFS integrated, −1 dBTP true peak) and resampled to 24 kHz, so all bundled voices sit at equal volume

**Custom voices must be normalized first**: VibeVoice clones loudness along with timbre — without matching levels, a loud reference makes that speaker louder for the whole episode (the demo Alice clip is ~10 LU hotter than the male voices and clips at +0.1 dBTP). New voice clips are brought to the same standard as the bundled voices with the bundled `scripts/normalize_voices.py`:

```bash
# normalize all WAVs in a directory in place
python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir /path/to/voices

# keep the originals, write normalized copies elsewhere
python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir /path/to/voices --output-dir /path/to/normalized

# normalize the skill's bundled assets/voices/ in place (no-op on the bundled voices)
python3 ${SKILL_DIR}/scripts/normalize_voices.py
```

It applies a two-pass ffmpeg `loudnorm` (linear gain, no compression) targeting **−23 LUFS integrated / −1 dBTP true peak** and resamples to 24 kHz, printing a before/after line per voice. The bundled demo voices are already normalized, so the script only needs to be run when new voices are added.

### Constraints
- Script file MUST use "Speaker N:" format for each line (where N is 1, 2, 3, etc.)
- **Maximum audio duration**: 60 minutes (1 hour) — enforced by the ML model
- Python 3.10+ required
- Apple Silicon Mac required (MLX does not support Intel Macs or other platforms)

## Steps

### 1. Verify Environment

Before generating audio, verify all prerequisites are met:

```bash
# Verify Python version
python3 --version
# Expected: Python 3.10 or higher

# Verify uv is installed
uv --version
# If not installed: curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify ffprobe is available (REQUIRED for tempo analysis)
ffprobe -version
# If not installed: brew install ffmpeg

# Verify vibevoice-mlx is installed
cd vibevoice-mlx
source .venv/bin/activate
python3 -c "import mlx.core as mx; print('MLX available:', mx.metal.is_available())"
# Expected: MLX available: True
```

If any prerequisite is missing, install it before proceeding.

### 2. Prepare Voice Files

**Using bundled voices** (no setup needed):
- Alice, Carter, Frank are available by default, pre-normalized to EBU R128

**Using custom voices**:
1. Record or obtain WAV voice samples (short 5-30 second clips work best)
2. Name each file `{speaker_num}_{name}.wav` (e.g., `1_Alice.wav`, `2_Frank.wav`)
3. Place all voice WAV files in the voices directory:
   ```bash
   mkdir -p ${SKILL_DIR}/assets/voices/
   cp /path/to/your/voices/*.wav ${SKILL_DIR}/assets/voices/
   ```
4. Verify files are in place:
   ```bash
   ls -la ${SKILL_DIR}/assets/voices/
   ```
5. Normalize the new voices to the EBU R128 standard before generating:
   ```bash
   python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir ${SKILL_DIR}/assets/voices/
   ```

**Tip:** For multi-speaker podcasts, using a mix of different male and female voices helps create distinct, engaging speaker identities.

### 3. Prepare Podcast Script

Ensure the script follows the "Speaker N:" format:

```markdown
Speaker 1: Hello, welcome to today's episode about artificial intelligence.
Speaker 2: Thanks for having me! AI is indeed a fascinating topic.
Speaker 1: Let's dive right in. What are the current trends in 2026?
```

**Validate script format:**
```bash
# Check that all lines start with "Speaker N:"
grep -v "^Speaker [0-9]" script.md
# Should return nothing (all non-empty lines should match the pattern)
```

**Estimate duration:**
```bash
# Count words (excluding "Speaker N:" prefixes)
word_count=$(python3 ${SKILL_DIR}/scripts/calculate_podcast_metrics.py count-words --file script.md)

# Estimate generation time
echo "Estimated time: $(echo "$word_count * 0.03" | bc) minutes"
```

**⚠️ Duration limit**: If estimated duration exceeds 60 minutes, ask the user for confirmation before proceeding. Options: split the script, reduce length, or proceed knowing it may fail.

### 4. Run Generation

Execute the audio generation script:

```bash
cd vibevoice-mlx
source .venv/bin/activate

python3 scripts/generate_podcast_audio.py \
  --script-path ~/podcasts/tech-podcast_20251025143000.md \
  --speaker-names Alice Frank \
  --voices-dir ${SKILL_DIR}/assets/voices/
```

**With custom model options:**
```bash
python3 scripts/generate_podcast_audio.py \
  --script-path ~/podcasts/tech-podcast_20251025143000.md \
  --speaker-names Alice Frank \
  --voices-dir ${SKILL_DIR}/assets/voices/ \
  --model-size 1.5b \
  --quantization 8 \
  --output-dir ~/podcasts/output_20251025143000/
```

**What happens during execution:**
1. Script format validation
2. Voice file discovery (bundled demo voices or custom)
3. Model loading (downloads ~5GB on first run, cached thereafter)
4. Audio generation via MLX inference
5. Output loudness-normalized to −16 LUFS / −1 dBTP (Apple Podcasts target) unless `--no-normalize-output`
6. WAV file output (normalized in place)

**First run note**: The model download (~5GB) happens on the first run and may take several minutes depending on your internet connection. Subsequent runs are much faster as the model is cached.

### 5. Analyze Tempo

After the WAV file is generated, analyze the speech tempo to determine if speed adjustment is needed.

#### Prerequisites

**Check for ffprobe availability:**
```bash
which ffprobe
```

If ffprobe is not available, install it: `brew install ffmpeg`. Tempo analysis requires ffprobe for accurate duration measurement.

#### Tempo Analysis Steps

**1. Count words in the original script:**
```bash
word_count=$(python3 ${SKILL_DIR}/scripts/calculate_podcast_metrics.py count-words --file script.md)
```

**2. Get audio duration using ffprobe:**
```bash
duration_seconds=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.wav)
```

**3. Calculate actual WPM:**
```
actual_wpm = (word_count / duration_seconds) * 60
```

**Example:**
- Word count: 2,625 words
- Duration: 900 seconds (15 minutes)
- Actual WPM: (2625 / 900) * 60 = 175 WPM

**4. Calculate speed adjustment factor:**
```
speed_factor = target_wpm / actual_wpm
```

**Example:**
- Actual WPM: 150 WPM
- Target WPM: 175 WPM
- Speed factor: 175 / 150 = 1.167x (need to speed up by 17%)

**5% Threshold:**
```
drift_percentage = abs(actual_wpm - target_wpm) / target_wpm * 100
if drift_percentage <= 5.0:
    # Skip speed adjustment - already close enough
```

#### Display Results to User

```
📊 Speech Tempo Analysis:
   Audio duration: {duration_seconds}s ({formatted_time})
   Word count: {word_count} words
   Actual speech rate: {actual_wpm:.1f} WPM
   Target speech rate: {target_wpm} WPM
   Required speed adjustment: {speed_factor:.2f}x
```

#### Pre-Conversion Sanity Check

**Before applying any speed adjustment, verify the expected outcome:**

1. **Expected new duration:**
   ```
   expected_duration = original_duration / speed_factor
   ```

2. **Expected new WPM:**
   ```
   expected_wpm = actual_wpm × speed_factor
   ```

3. **Sanity check**: If expected new WPM differs from target by more than 5%, stop and re-verify duration using ffprobe.

#### Drift Thresholds

| Drift | Action |
|-------|--------|
| ≤ 5% | No adjustment needed — audio quality is optimal |
| 5-30% | Recommend using `convert-audio:convert-audio` with speed adjustment |
| > 30% | Warn user — large adjustments may affect quality; let user decide |

### 6. Extract Metadata

After successful audio generation and tempo analysis, extract metadata using a Task sub-agent:

**Title Extraction:**
- Extract from script filename or content
- Ensure consistency with the podcast topic

**Artist Collection:**
- Extract persona names from the script
- Combine with voice names used during generation
- Format: "Persona (Voice name)", comma-separated

**Description Extraction:**
- Extract from script content or topic summary

**Display format:**
```
=== Podcast Metadata ===
Title: [Extracted title]
Artist: [Persona1 (Voice1 voice), Persona2 (Voice2 voice)]
Description: [Extracted description]
========================
```

### 7. Apply Speed Adjustment (If Needed)

If drift > 5%, recommend using the `convert-audio:convert-audio` skill:

**For 5-30% drift:**
```
⚙️ Tempo adjustment recommended:
   Actual: {actual_wpm:.1f} WPM
   Target: {target_wpm} WPM
   Drift: {drift_percentage:.1f}%
   Speed factor: {speed_factor:.2f}x

   Use convert-audio skill to convert the WAV to MP3 with speed adjustment.
```

**For > 30% drift:**
```
⚠️ WARNING: Large Speed Adjustment Required

Current speed: {actual_wpm:.1f} WPM
Target speed: {target_wpm} WPM
Drift: {drift_percentage:.1f}% (>30% threshold)
Required speed factor: {speed_factor:.2f}x

Large speed adjustments may noticeably affect audio quality.
Recommendations:
1. Accept the current speech rate (no adjustment needed)
2. Regenerate the podcast with adjusted script or TTS settings
3. Proceed with conversion anyway (audio quality may be affected)
```

## Tempo Analysis

### Word Count and Duration

Use the bundled `calculate_podcast_metrics.py` script for word counting:
```bash
python3 ${SKILL_DIR}/scripts/calculate_podcast_metrics.py count-words --file script.md
```

Use `ffprobe` for accurate audio duration:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.wav
```

### WPM Calculation

```
actual_wpm = (word_count / duration_seconds) * 60
drift_percentage = abs(actual_wpm - target_wpm) / target_wpm * 100
speed_factor = target_wpm / actual_wpm
```

### Drift Thresholds

- **≤ 5%**: No action needed — audio is within acceptable range
- **5-30%**: Recommend `convert-audio:convert-audio` with calculated speed factor
- **> 30%**: Warn the user; large adjustments may produce unnatural audio

## Loudness Normalization

Podcast platforms normalize playback against published loudness targets, so shipping un-normalized audio makes episodes sit at inconsistent levels relative to each other and to everything else in a listener's feed. This skill therefore normalizes both its inputs and its output.

### Reference Standards (Quick Reference)

| Standard | Integrated loudness | True peak | Used by |
|---|---|---|---|
| **−16 LUFS** | −16 | −1 dBTP | **Apple Podcasts** (de facto podcast target) |
| −14 LUFS | −14 | −1 dBTP | Spotify / YouTube playback normalization |
| −23 LUFS | −23 | −1 dBTP | EBU R128 broadcast (US equivalent: ATSC A/85 at −24 LKFS) |

All are measured with the same EBU R128 algorithm that ffmpeg implements (`loudnorm`).

### Inputs: reference voices

New reference voices must be prepared with the bundled `scripts/normalize_voices.py`, which loudness-matches every clip to **−23 LUFS / −1 dBTP** (EBU R128 broadcast standard) at 24 kHz with a two-pass ffmpeg `loudnorm`:

```bash
# pass 1: measure
ffmpeg -i voice.wav -af loudnorm=I=-23:TP=-1:LRA=7:print_format=json -f null -
# pass 2: apply measured values with linear gain
ffmpeg -i voice.wav -af loudnorm=I=-23:TP=-1:LRA=7:measured_I=...:measured_TP=...:measured_LRA=...:measured_thresh=...:offset=...:linear=true -ar 24000 out.wav
```

`linear=true` means pure gain — no compression, so the speech's dynamics are untouched. This matters because VibeVoice clones loudness along with timbre; mismatched references make one speaker audibly louder than the other for the whole episode. The bundled demo voices are already normalized, so this step applies only when adding new voices.

### Output: generated episode

The generated WAV is normalized to **−16 LUFS / −1 dBTP** (Apple Podcasts recommendation) by default, applied as a final two-pass `loudnorm` stage and reported in the run log (achieved loudness vs. target). Override with `--target-lufs` / `--target-tp`; disable with `--no-normalize-output`.

**QC note**: with `linear=true`, `loudnorm` will not apply gain that would breach the true-peak ceiling, so results can land slightly under target (typically within ±1 LU of it, e.g. −16.5 to −16.8 against a −16 target for typical sources). This deviation is reported in the run log rather than silently accepted. Switching to dynamic mode would hit the number more precisely but applies compression, which is usually the wrong trade for spoken word.

## Metadata Extraction

Use a Task sub-agent to extract metadata from the script file:

1. **Title**: Consistent with script filename and content
2. **Artist**: Persona names with voice names in parentheses, comma-separated
3. **Description**: Brief summary of the podcast episode

Display metadata in the standard format for use with the convert-audio skill.

## Troubleshooting

### MLX Not Installed or Not Available

**Symptom**: Import error for `mlx.core` or `MLX available: False`

**Solution:**
```bash
cd vibevoice-mlx
source .venv/bin/activate
uv pip install mlx
python3 -c "import mlx.core as mx; print(mx.metal.is_available())"
```

If `is_available()` returns `False`, verify you are on Apple Silicon:
```bash
uname -m
# Should return arm64
```

### Out of Memory

**Symptom**: Process crashes with memory error during model loading

**Solutions:**
1. **Reduce model size**: Use `--model-size 1.5b` instead of `7b`
2. **Increase quantization**: Use `--quantization 4` instead of `8`
3. **Close other applications**: Free up RAM before running
4. **Check available memory**:
   ```bash
   vm_stat | head -5
   ```

### Voice File Not Found

**Symptom**: Error about missing voice files for a speaker

**Solution:**
1. Verify voice files exist in the voices directory:
   ```bash
   ls -la ${SKILL_DIR}/assets/voices/
   ```
2. Check naming convention: `{speaker_num}_{name}.wav` or `{name}_{speaker_num}.wav`
3. Ensure speaker numbers match the "Speaker N:" format in the script
4. Verify the voices directory path is correct with `--voices-dir`

### Loudness Normalization Skipped

**Symptom**: Run log shows "output loudness normalization will be SKIPPED"

**Solution**: The script needs the full `ffmpeg` binary, not just `ffprobe`. Install it:
```bash
brew install ffmpeg
```
The generation still completes, but the output is left at its natural level.

### Voices Sound Different Volumes

**Symptom**: One speaker is noticeably louder than the other in the finished episode

**Solution**: The reference clips are not loudness-matched. VibeVoice clones loudness along with timbre, so a louder reference makes that speaker louder for the whole episode. Run the bundled normalizer on the voices directory before generating:
```bash
python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir ${SKILL_DIR}/assets/voices/
```
Then re-run generation.

### Model Download Slow or Failing

**Symptom**: Generation stalls during model download on first run

**Solutions:**
1. Check internet connection
2. Model is ~5GB — be patient on first run
3. If download fails, retry:
   ```bash
   rm -rf ~/.cache/vibevoice-mlx/models/*
   # Re-run generation to re-download
   ```
4. Verify disk space: `df -h /`

### Long Generation Times

**Symptom**: Generation takes much longer than expected

**Solutions:**
1. Use faster model: `--model gafiatulin/vibevoice-1.5b-mlx`
2. Use lower quantization: `--quantize 4`
3. Close other applications to free RAM
4. Consider the performance tips below

### Script Format Errors

**Symptom**: Script validation fails

**Solution:**
```bash
# Check script format
grep -v "^Speaker [0-9]" script.md
# All non-empty lines should start with "Speaker N:"
```

Fix any lines that don't match the expected format.

## Performance Tips

### First Run: Model Download

- The first run downloads the model (~5GB) — this is a one-time cost
- Subsequent runs load from cache and are much faster
- Model is cached by huggingface-hub in `~/.cache/huggingface/`

### Choose the Right Model

- **7b** (`gafiatulin/vibevoice-7b-mlx`): Highest quality, slower (~60 min for 2000 words on M2 Pro)
- **1.5b** (`gafiatulin/vibevoice-1.5b-mlx`): Good quality, much faster (~30 min for 2000 words on M2 Pro)
- For most use cases, 1.5b provides acceptable quality at half the time

### Quantization Settings

- **8-bit** (default): Good balance of quality and speed
- **4-bit**: Fastest, slight quality loss — good for drafts and previews
- Higher quantization = better quality but slower
- Diffusion head is always quantized (no separate flag needed)

### Use CoreML Semantic Encoder

- MLX can leverage CoreML for faster inference
- Ensure CoreML models are available:
  ```bash
  python3 -c "import mlx.core as mx; print(mx.backends.coreml.is_available())"
  ```
- If available, inference may be faster due to dedicated ML hardware

### Free Up RAM

- Close other applications before running
- 16GB+ RAM recommended for 7b model
- 8GB may work with 1.5b model and quantization

### Expected Performance by Chip

| Chip | 7b Model (approx.) | 1.5b Model (approx.) |
|------|---------------------|-----------------------|
| M1 | ~90 min (2000 words) | ~45 min |
| M2 | ~75 min | ~38 min |
| M2 Pro | ~60 min | ~30 min |
| M3 | ~50 min | ~25 min |
| M3 Pro | ~40 min | ~20 min |
| M4 | ~35 min | ~18 min |

These are rough estimates. Actual times vary based on model size, quantization, diffusion settings, and available RAM.

## Comparison with AWS Version

### Local MLX Advantages
- **No cost**: Free to use, no per-run charges
- **Privacy**: Audio never leaves your machine
- **Simplicity**: Single script, no infrastructure setup
- **No AWS account needed**: Works out of the box
- **No cleanup required**: No remote resources to manage

### Local MLX Disadvantages
- **Slower**: Apple Silicon is slower than AWS GPU instances
- **Hardware required**: Must have Apple Silicon Mac
- **RAM constrained**: Limited by your Mac's unified memory
- **Single execution**: Can only generate one podcast at a time
- **First run delay**: ~5GB model download on first run

### AWS Bedrock Advantages
- **Faster**: GPU instances generate audio more quickly
- **Scalable**: Can run multiple generations in parallel
- **No local hardware needed**: Works on any machine with AWS access
- **Consistent performance**: Same speed regardless of local hardware

### AWS Bedrock Disadvantages
- **Costs money**: ~$1.35 per run
- **Setup required**: One-time AWS infrastructure setup
- **Privacy concern**: Audio processed on remote EC2
- **Cleanup responsibility**: Automatic but requires trust in the script
- **AWS account needed**: Requires AWS credentials and permissions

## Notes

- **Model caching**: First run downloads model (~5GB), cached by huggingface-hub for subsequent runs
- **Audio format**: Generated as WAV file only; use `convert-audio:convert-audio` skill for format conversion
- **Loudness normalization**: New reference voices are prepared with `scripts/normalize_voices.py` (−23 LUFS / −1 dBTP); the output is normalized to −16 LUFS / −1 dBTP by default (see [Loudness Normalization](#loudness-normalization)). Both are linear-gain two-pass `loudnorm`, no compression
- **Speech tempo analysis**: MANDATORY post-generation analysis using ffprobe to calculate actual WPM and drift percentage
- **Duration limit**: 60 minutes maximum — validate before generating
- **Voice files**: Bundled demo voices (Alice, Frank, Carter) used by default; custom voices named `{speaker_num}_{name}.wav` in `assets/voices/` directory
- **Output naming**: Always include timestamps to prevent file conflicts
- **No remote cleanup**: Local execution, no resources to clean up
- **ffprobe required**: Must be installed for tempo analysis (`brew install ffmpeg`)
- **CoreML acceleration**: May be available for faster inference on newer Macs
- **Signal handling**: Ctrl+C stops generation; no automatic cleanup needed for local execution

## Self-Improvement: Documenting Execution Lessons

**IMPORTANT:** At the end of your execution, output a "Lessons from This Execution" section that documents what could make this skill better.

**Format:** For each problem encountered, write a concise problem-solution pair:
- **What went wrong or caused confusion** (1 sentence describing the actual issue you hit)
- **How the skill should be updated** (1 sentence describing the specific instruction/clarification to add)
