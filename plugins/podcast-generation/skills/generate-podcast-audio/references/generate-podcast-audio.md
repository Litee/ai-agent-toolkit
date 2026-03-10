# Generate Podcast Audio from Script

Convert formatted podcast scripts into high-quality audio using VibeVoice on AWS EC2 GPU instances. The automation script handles all operations end-to-end.

## 🤖 CRITICAL DIRECTIVE: Automatic Cleanup - Never Ask User

**⚠️ MANDATORY BEHAVIOR FOR CLAUDE:**
- The automation script handles ALL resource cleanup automatically via signal handlers and atexit hooks
- **NEVER ask the user to manually clean up AWS resources** unless the script itself is blocked or has failed
- **NEVER instruct the user to run manual AWS CLI commands** for cleanup unless automatic cleanup has failed
- Trust the script's automatic cleanup - it handles Ctrl+C gracefully and cleans up on exit

**PERMANENT Infrastructure** (created by `setup_infrastructure.py`, NEVER deleted by `generate_podcast_audio.py`):
- S3 bucket: `podcast-temp-{account-id}-{region}` - DO NOT delete it or ask user to delete it (automatically configured with 24-hour lifecycle policy)
- IAM role: `podcast-ec2-role-{account-id}-{region}` - DO NOT delete it or ask user to delete it (created by setup_infrastructure.py)
- IAM instance profile: Same as IAM role - DO NOT delete it or ask user to delete it (created by setup_infrastructure.py)
- Step Functions state machine: `podcast-generation-{region}` - DO NOT delete it (created by setup_infrastructure.py)

**Per-Run Resources** (automatically cleaned up each run):
- EC2 instances: Terminated automatically
- Security groups: Deleted automatically
- S3 files: Only timestamp-specific files (under `{timestamp}/`) are cleaned up per run

**Benefits**: Zero risk of parallel execution conflicts, faster execution (~15 sec saved), more reliable

**🔑 Key Features**:
- **No SSH keys required** - SSM provides secure command execution without SSH
- **No open ports** - More secure than traditional SSH (port 22 not needed)
- **S3 for file transfers** - Script, voice samples, and generated audio use S3 as intermediary
- **24-hour S3 retention** - Audio files remain in S3 as backup for 24 hours with automatic cleanup
- **Permanent infrastructure** - S3 bucket and IAM role are NEVER deleted (safe for parallel executions)
- **Better reliability** - SSM more reliable for long-running operations than SSH
- **Automatic cleanup** - All temporary resources deleted automatically (EC2, security groups)
- **Faster execution** - Permanent IAM role saves ~15 seconds per run (no creation/deletion needed)
- **Predictable timing** - Total execution time ≈ 12 + (Word_Count / 63) minutes (~44 min for 2,000-word script)

## Parameters

### setup_infrastructure.py

- **--profile** (required): AWS CLI profile name
- **--region** (optional): AWS region where infrastructure will be created (default: profile's configured region)

### generate_podcast_audio.py

- **--script-path** (required): Path to existing script file
- **--speaker-names** (required): Space-separated list of speaker voice names in order (first voice = Speaker 1, second = Speaker 2, etc.). Example: Alice Frank
- **--profile** (required): AWS CLI profile name
- **--region** (optional): AWS region for EC2 instance launch (default: profile's configured region)
- **--instance-type** (optional): EC2 instance type (defaults to g6.4xlarge)
- **--output-dir** (optional): Local directory for audio files (defaults to current directory)
- **--voices-dir** (optional): Path to directory containing custom voice WAV files (defaults to `assets/voices/` next to the script). Only needed when using voices beyond the VibeVoice built-ins.
- **--verbose** (optional): Enable detailed SSH debugging output (defaults to false)

### 🚨 CRITICAL: Preventing File Name Conflicts

**Output files are named based on the script filename**, which means generating multiple podcasts will overwrite files if they have the same script name.

**MANDATORY: Always include timestamps in your workflow using ONE of these approaches:**

1. **Timestamp in script filename** (Recommended):
   ```bash
   --script-path ~/podcasts/tech-episode_20251025143000.md
   ```
   This generates: `tech-episode_20251025143000.wav`

2. **Timestamp in output directory**:
   ```bash
   --output-dir ~/podcasts/output_20251025143000/
   ```
   All outputs for this generation go into a unique timestamped directory

3. **Both** (Maximum safety):
   ```bash
   --script-path ~/podcasts/episode_20251025143000.md \
   --output-dir ~/podcasts/output_20251025143000/
   ```

**Why this matters:** Without timestamps, downloading a new podcast to the same directory will silently overwrite the previous audio files. Timestamps ensure each generation is preserved with unique filenames.

**Available Voice Names:**

Voices come from two sources:

**1. VibeVoice built-in voices (always available):**
- Alice (woman), Carter (man), Frank (man), Mary (woman)

These are included automatically after VibeVoice is cloned on EC2. No setup required.

**2. Custom voices (user-provided):**
- Any WAV voice sample you provide. The voice name must appear somewhere in the filename (e.g., `en-Helen_woman.wav` can be referenced as `Helen`).
- Custom voices are uploaded from your voices directory (`--voices-dir`) to S3 and copied to EC2 before generation.

**Custom Voice Setup:**

To use custom voices:
1. Record or obtain WAV voice samples for your desired voices (short 5-30 second clips of the voice speaking work best)
2. Name each file so the voice name appears in the filename, e.g., `my-voice.wav` or `en-John_man.wav`
3. Place all voice WAV files in a directory on your local machine
4. Pass the directory path via `--voices-dir /path/to/your/voices`
5. Reference voices by the name portion of their filename (e.g., `my-voice` or `John`)

**Tip:** For multi-speaker podcasts, using a mix of different male and female voices helps create distinct, engaging speaker identities.

**Constraints:**
- Script file MUST use "Speaker N:" format for each line (where N is 1, 2, 3, etc.)
- **Maximum audio duration**: 60 minutes (1 hour) - enforced by the ML model
- AWS CLI must be configured with appropriate credentials
- Python 3.10+ required for automation script

## Steps

### 1. Verify Dependencies and Environment

**Prerequisites for Automation Script:**
- Python 3.10 or higher
- AWS CLI configured with valid credentials
- Podcast script file in correct format

**Note:** SSH/SCP clients are NOT required - this script uses AWS SSM for command execution and S3 for file transfers.

**Verification Commands:**
```bash
# Verify Python version
python3 --version

# Verify AWS CLI and test credentials
aws configure list
aws sts get-caller-identity --profile YOUR_PROFILE

# Verify script file exists
ls -lh path/to/your-script.md
```

### 2. Set Up AWS Infrastructure (One-Time)

**⚠️ REQUIRED BEFORE FIRST USE:** Run `setup_infrastructure.py` once per AWS account/region before generating any podcasts. This creates the permanent infrastructure that `generate_podcast_audio.py` relies on.

```bash
python3 scripts/setup_infrastructure.py \
  --profile YOUR_PROFILE \
  --region us-west-2
```

**What it creates:**
- S3 bucket: `podcast-temp-{account-id}-{region}` (with 24-hour lifecycle policy)
- IAM role for Lambda: `podcast-lambda-role-{account-id}-{region}`
- IAM role for Step Functions: `podcast-stepfunctions-role-{account-id}-{region}`
- IAM role + instance profile for EC2: `podcast-ec2-role-{account-id}-{region}`
- Step Functions state machine: `podcast-generation-{region}`

**Safe to re-run** — all operations are idempotent. Re-running on an existing setup just verifies resources exist.

If infrastructure is missing when you run `generate_podcast_audio.py`, the script will fail immediately with a clear message telling you to run `setup_infrastructure.py` first.

### 3. Validate Script Duration (MANDATORY)

**⚠️ CRITICAL: Before proceeding with audio generation, you MUST validate the script duration.**

The VibeVoice ML model has a hard limit of **60 minutes (1 hour)** for audio generation. Scripts that exceed this duration will fail during processing, wasting time and AWS resources.

**Validation Steps:**

1. **Estimate script duration** using word count:
   ```bash
   # Count words in script (exclude "Speaker N:" prefixes)
   grep "^Speaker [0-9]" script.md | sed 's/^Speaker [0-9]*: //' | wc -w
   ```

2. **Calculate estimated duration**:
   - Typical speech rate: ~175-195 words per minute
   - Formula: `total_words / 175` (use 175 as standard rate)
   - Example: 10,000 words ÷ 175 = ~57.1 minutes

3. **If duration > 60 minutes, ask for user confirmation:**
   - Display estimated duration to user
   - Show the following warning:
     ```
     ⚠️ WARNING: Script Duration Exceeds Model Limit

     Estimated duration: XX minutes (based on YY words)
     Model limit: 60 minutes (1 hour)

     The VibeVoice ML model has a hard limit of 60 minutes for audio generation.
     Scripts exceeding this limit will fail during processing, wasting time and AWS resources (~$1.35/hour).

     Options:
     1. Split the script into multiple parts (recommended)
     2. Reduce script length to stay under 60 minutes
     3. Proceed anyway (will likely fail during generation)

     Do you want to proceed with audio generation?
     ```
   - Do NOT proceed unless user explicitly confirms

**Why this matters:**
- Prevents wasted AWS costs (~$1.35/hour for g6.4xlarge)
- Avoids long-running operations that will ultimately fail
- Saves time by catching issues before EC2 launch

### 4. Select Compute Resources

**Default Instance Type:** g6.4xlarge (can be changed with `--instance-type` parameter)

**Note:** If an instance type is unavailable due to capacity constraints, try a different region or wait and try again later.

### 5. Generate Audio Using Automation Script

The automation script handles all EC2 operations automatically, providing a simple, reliable workflow with robust error handling and automatic cleanup. **Infrastructure must be set up first** (Step 2).

#### What the Script Does

The [`generate_podcast_audio.py`](generate_podcast_audio.py) automation script provides end-to-end podcast generation:

**Automated Operations:**
1. ✅ Validates script format before launching EC2 (catches errors early)
   - **Note**: Duration validation (60-minute limit check) must be done manually before running the script (see Step 3)
2. ✅ Verifies infrastructure exists (fails fast with clear message if `setup_infrastructure.py` hasn't been run)
3. ✅ Launches EC2 instance with 12-hour auto-termination safeguard
4. ✅ Waits for SSM agent availability with retry logic
5. ✅ Installs all dependencies via SSM (clones VibeVoice from GitHub, installs from source)
6. ✅ Transfers script file to instance via S3
7. ✅ Executes audio generation with progress monitoring via SSM
8. ✅ Downloads generated audio file via S3 (WAV format)
9. ✅ Cleans up temporary AWS resources (instance, security groups, S3 files; permanent infra retained)
10. ✅ Detects ALL orphaned resources from any run (helps identify stuck instances from previous runs)

**Key Features:**
- **Fail-fast validation** - Checks script format before spending money on EC2
- **Automatic cleanup** - Resources deleted even if script crashes (signal handlers + atexit)
- **Orphaned resource detection** - Scans for stuck instances from other runs (within 12-hour window)
- **12-hour auto-termination** - Instance shuts down automatically after 12 hours
- **Progress monitoring** - Timestamped status updates throughout execution
- **SSM retry logic** - Handles connection issues with exponential backoff
- **S3 backup** - Audio files retained in S3 for 24 hours as backup
- **No SSH required** - Uses AWS Systems Manager for secure command execution
- **Error handling** - Clear error messages with automatic resource cleanup

#### Basic Usage

```bash
python3 generate_podcast_audio.py \
  --script-path path/to/your-script_20251025143000.md \
  --speaker-names Alice Frank \
  --profile YOUR_PROFILE \
  --region us-west-2
```

With custom voices:
```bash
python3 generate_podcast_audio.py \
  --script-path path/to/your-script_20251025143000.md \
  --speaker-names MyVoice Alice \
  --voices-dir ~/my-voices \
  --profile YOUR_PROFILE \
  --region us-west-2
```

#### All Parameters

```bash
python3 generate_podcast_audio.py \
  --script-path <path>           # (Required) Path to podcast script file
  --speaker-names <names...>     # (Required) Space-separated voice names
  --region <region>              # (Required) AWS region for EC2 instance
  --profile <profile>            # (Required) AWS CLI profile
  --instance-type <type>         # (Optional) EC2 type (default: g6.4xlarge)
  --output-dir <directory>       # (Optional) Local output directory (default: .)
  --voices-dir <directory>       # (Optional) Directory with custom voice WAV files
  --verbose                      # (Optional) Enable detailed SSH debugging output
```

#### Parameter Details

**--script-path** (required)
- Path to your podcast script file
- File must use "Speaker N:" format for each line
- Script validated before EC2 launch to catch format errors early

**--speaker-names** (required)
- Space-separated list of voice names matching script speakers (see "Available Voice Names" section above for full list)
- **IMPORTANT: Voices are applied in the specified order** - first voice = Speaker 1, second voice = Speaker 2, third voice = Speaker 3, etc.
- Example: `--speaker-names Alice Frank` assigns Alice to Speaker 1, Frank to Speaker 2

**--profile** (required)
- AWS CLI profile name (must be explicitly provided)
- Must have EC2 permissions

**--region** (optional, default: profile's configured region)
- AWS region for EC2 instance launch
- Common options: us-west-2, us-east-1
- Consider capacity availability for GPU instances

**--instance-type** (optional, default: g6.4xlarge)
- Specific instance type to launch
- If unavailable, script will fail with capacity error

**--output-dir** (optional, default: current directory)
- Local directory for downloaded audio files
- Will be created if doesn't exist
- Audio files named based on script filename: `<script-name>.wav`

**--voices-dir** (optional, default: `assets/voices/` next to the script)
- Directory containing your custom voice WAV files
- Only needed if using voices beyond the VibeVoice built-ins (Alice, Carter, Frank, Mary)
- Voice name matching: the voice name you pass in `--speaker-names` must appear somewhere in the WAV filename
- Example: `--voices-dir ~/my-custom-voices`

**--verbose** (optional, default: false)
- Enables detailed SSM command debugging output
- Shows all SSM commands, STDOUT, STDERR, and execution status
- Useful for troubleshooting connection or installation issues
- Example: `--verbose`

#### Usage Examples

**Example 1: Basic usage with built-in voices (timestamp in filename)**
```bash
python3 generate_podcast_audio.py \
  --script-path ~/podcasts/tech-podcast_20251025143000.md \
  --speaker-names Alice Frank \
  --region us-west-2
```

**Example 2: Timestamp in output directory with custom voices**
```bash
python3 generate_podcast_audio.py \
  --script-path ~/podcasts/podcast-interview.md \
  --speaker-names MyHost MyGuest \
  --voices-dir ~/my-voices \
  --profile my-aws-profile \
  --region us-west-2 \
  --output-dir ~/podcast-outputs/run_20251025143000
```

**Example 3: Both timestamp approaches for maximum safety**
```bash
python3 generate_podcast_audio.py \
  --script-path ~/podcasts/episode_20251025143000.md \
  --speaker-names Alice Carter \
  --region us-west-2 \
  --output-dir ~/podcasts/output_20251025143000 \
  --verbose
```

### 6. Shutdown and Resource Cleanup

**⚠️ CRITICAL: Graceful Shutdown Requirement**

The automation script manages temporary AWS resources that incur costs. Always shut down the script properly to ensure automatic cleanup.

#### Graceful Shutdown (Recommended)

**Use Ctrl+C (SIGINT) or Ctrl+\\ (SIGTERM) to stop the script:**
- The script has registered signal handlers that catch these signals
- Automatic cleanup is triggered immediately
- All AWS resources are deleted: EC2 instance, SSH key pair, security group
- Local temporary files are left in /tmp for debugging (SSH key files)

**What gets cleaned up automatically:**
1. EC2 instance is terminated
2. IAM role and instance profile are deleted
3. Security group is deleted from AWS
4. S3 files for this run are deleted (bucket retained for reuse)
5. Script exits cleanly

#### Forceful Kill (NOT Recommended)

**If you use `kill -9` (SIGKILL) on the script process:**
- Signal handlers CANNOT be executed
- NO automatic cleanup occurs
- YOU are responsible for manually cleaning up all resources
- Costs will continue to accrue until resources are removed (up to 12 hours for instance auto-termination)

**Manual cleanup after forceful kill:**

If the script was forcefully killed (kill -9) or cleanup failed, use the cleanup script to find and terminate orphaned resources.

#### Using the Cleanup Script

A Python cleanup script is provided to safely discover and optionally terminate orphaned EC2 instances. The script will **ONLY terminate EC2 instances** when using `--delete`. All other resources are listed for informational purposes but never deleted.

**Quick Usage:**

```bash
# Step 1: Discover orphaned resources (read-only, safe)
python3 cleanup_orphaned_resources.py \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --max-age-hours 12

# Step 2: Review the report, then terminate EC2 instances if needed
python3 cleanup_orphaned_resources.py \
  --profile YOUR_PROFILE \
  --region YOUR_REGION \
  --max-age-hours 12 \
  --delete
```

**For detailed instructions, usage examples, and troubleshooting, see:**
[Cleanup Orphaned Resources Documentation](cleanup-orphaned-resources.md)

#### Failsafe: 12-Hour Auto-Termination

Even if cleanup fails, all EC2 instances have a built-in 12-hour auto-termination safeguard:
- User-data script schedules `shutdown` command 12 hours after launch
- Prevents runaway costs from forgotten instances
- Maximum cost exposure: 12 hours × instance hourly rate

**However:** You should NEVER rely on this failsafe. Always clean up resources immediately.

### 7. Monitor Progress

When using the automation script, progress monitoring is automatic:

- **Script format validation** - Occurs before EC2 launch (duration validation must be done manually in Step 2)
- **Infrastructure setup** - SSH keys, security groups created
- **Instance launch** - Includes instance type fallback attempts
- **Dependency installation** - Step-by-step progress for each component
- **Audio generation** - Regular status updates every 30 seconds
- **Completion detection** - Checks for output file existence
- **Download progress** - File size and transfer status
- **Orphaned resource detection** - Scans for resources from other runs (within 12-hour window)

**Monitoring Tips:**
- Watch for "Phase N" headers to track workflow progress
- Timestamp shows elapsed time for each operation
- If script appears stalled, check the last logged operation
- Ctrl+C safely triggers cleanup (script catches signals)
- Orphaned resource detection helps identify stuck instances from failed previous runs

#### Token-Efficient Status Checking for LLM Agents

**MANDATORY for LLM agents:** After starting generation:

1. **Calculate estimate:** `20 + (Word_Count / 100)` minutes
2. **Communicate to user:** Show expected completion time (duration + clock time)
3. **Inform user:** They can ask for status after the expected completion time
4. **DO NOT continuously poll** - generation runs independently on AWS

**Rationale:** Generation takes 45-120+ minutes. Continuous polling wastes tokens without providing value.

### 8. Retrieve Generated Audio

**Automatic Download with Script:**
The automation script downloads files automatically to your specified output directory via S3. Audio files are:
1. Generated on EC2 instance
2. Uploaded to S3 by EC2 instance
3. Downloaded from S3 to your local machine
4. Retained in S3 for 24 hours as backup

**Output Files:**
- **WAV file** - High-quality audio: `<script-name>.wav`

**Note:** To convert WAV to other formats (MP3, AAC, etc.), use a separate audio format conversion skill.

**S3 Backup Location:**
After completion, the script displays the S3 URI where your audio is stored:
```
S3 Backup Location (available for 24 hours):
  Bucket: podcast-temp-{account-id}-{region}
  Path:   {timestamp}/output.wav
  URI:    s3://podcast-temp-{account-id}-{region}/{timestamp}/output.wav
```

You can retrieve the file from S3 at any time within 24 hours (files are automatically deleted after 24 hours via S3 bucket lifecycle policy):
```bash
aws s3 cp s3://podcast-temp-{account-id}-{region}/{timestamp}/output.wav ./backup.wav
```

**File Locations:**
```bash
# Default output location (current directory)
./<script-name>.wav

# Custom output location
<output-dir>/<script-name>.wav
```

**File Format:**
- **WAV**: Uncompressed, highest quality, large file size (~150MB for 15 minutes)

### 9. Speech Tempo Analysis (MANDATORY)

**⚠️ CRITICAL**: This step is MANDATORY and must be performed after WAV file download. You MUST analyze speech tempo to determine if speed adjustment is needed.

After the WAV file is generated and downloaded, you MUST analyze the speech tempo to determine if speed adjustment is needed.

#### Target Speech Tempo

**Use the speech_tempo value from script generation:**
- The target tempo comes from the script generation phase (parameter: `speech_tempo`)
- Default: 175 words per minute (WPM) if not specified during script generation
- Typical speech rates: 165-185 WPM (brisk to fast conversational), 185-205 WPM (very fast/energetic)
- This value should match the script's intended tempo

#### Prerequisites

**⚠️ MANDATORY: Check for ffprobe availability at the START of tempo analysis:**
```bash
which ffprobe
```

**If ffprobe IS available (REQUIRED method):**
- Proceed with tempo analysis steps below using ffprobe
- ffprobe is the PRIMARY and REQUIRED method for accurate duration measurement

**If ffprobe is NOT available (EMERGENCY FALLBACK ONLY):**
- Use fallback file-size calculation method (see below)
- **⚠️ WARNING**: File-size calculation can be inaccurate (up to 10% error observed in real-world usage)
- Inform user that tempo analysis is using file-size-based duration estimation and may be less accurate

#### Fallback Method (When ffprobe is NOT available)

VibeVoice consistently generates WAV files with these specifications:
- **Format**: PCM 16-bit (signed, little-endian)
- **Sample rate**: 22,050 Hz (22.05 kHz)
- **Channels**: 1 (mono)

**Calculate duration from file size:**
```bash
# Using the bundled Python script:
duration_seconds=$(python scripts/calculate_podcast_metrics.py actual-duration --wav-file output.wav)
```

**Example:**
- File size: 1,000,000 bytes
- Duration: 1,000,000 / 44,100 = 22.68 seconds

**Note:** This simplified formula ignores the WAV header (44 bytes) which is negligible for typical podcast lengths. While theoretically accurate to within 0.01 seconds for VibeVoice-generated WAV files, **⚠️ real-world accuracy can vary up to 10%** depending on actual audio format and encoding parameters. Always prefer ffprobe when available.

#### Tempo Analysis Steps

**1. Count words in the original script:**
```bash
# Using the bundled Python script (excludes "Speaker N:" prefixes):
word_count=$(python scripts/calculate_podcast_metrics.py count-words --file script.md)
```

**2. Get audio duration:**

**REQUIRED Method - Using ffprobe:**
```bash
duration_seconds=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.wav)
```
This returns the duration in seconds (e.g., `902.5` for 15 minutes 2.5 seconds).

**EMERGENCY FALLBACK ONLY - File size calculation (when ffprobe is unavailable):**
```bash
duration_seconds=$(python scripts/calculate_podcast_metrics.py actual-duration --wav-file output.wav)
```
**⚠️ WARNING**: This method can be inaccurate (up to 10% error). Only use when ffprobe is not available.

**3. Calculate actual WPM:**
```
actual_wpm = (word_count / duration_seconds) * 60
```

**Example:**
- Word count: 2625 words
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

**⚠️ IMPORTANT: Skip Speed Adjustment if Already Close to Target**
If the actual WPM is already within 5% of the target WPM, **DO NOT apply speed adjustment**. Audio quality is better without unnecessary processing.

**5% Threshold Calculation:**
```
drift_percentage = abs(actual_wpm - target_wpm) / target_wpm * 100
if drift_percentage <= 5.0:
    # Skip speed adjustment - already close enough
```

#### Display Results to User

Always show the analysis results:

```
📊 Speech Tempo Analysis:
   Audio duration: {duration_seconds}s ({formatted_time})
   Word count: {word_count} words
   Actual speech rate: {actual_wpm:.1f} WPM
   Target speech rate: {target_wpm} WPM
   Required speed adjustment: {speed_factor:.2f}x
```

#### Calculate Drift Percentage

After calculating the speed adjustment factor, calculate the drift percentage:

```
drift_percentage = abs(actual_wpm - target_wpm) / target_wpm * 100
```

**Example:**
- Actual WPM: 160 WPM
- Target WPM: 175 WPM
- Drift: |160 - 175| / 175 * 100 = 8.6%

#### Pre-Conversion Sanity Check

**⚠️ CRITICAL**: Before applying any speed adjustment, calculate and verify the expected outcome to catch calculation errors before they result in wrong audio output.

**Calculate Expected Outcome:**
1. **Expected new duration:**
   ```
   expected_duration = original_duration / speed_factor
   ```

2. **Expected new WPM:**
   ```
   expected_wpm = actual_wpm × speed_factor
   ```

**Verification Steps:**
1. Display the expected outcome to the user:
   ```
   🔍 Pre-Conversion Verification:
      Original duration: {original_duration}s
      Speed factor: {speed_factor:.2f}x
      Expected new duration: {expected_duration:.1f}s
      Expected new WPM: {expected_wpm:.1f} WPM
      Target WPM: {target_wpm} WPM
   ```

2. **Sanity Check - STOP if something is wrong:**
   - If expected new WPM differs from target by more than 5%, **STOP** and re-verify duration using ffprobe
   - This indicates a calculation error or inaccurate duration measurement
   - Re-run tempo analysis using ffprobe (not file-size calculation) before proceeding

**Example:**
- Original duration: 900 seconds
- Speed factor: 1.167x (to speed up from 150 WPM to 175 WPM)
- Expected duration: 900 / 1.167 = 771 seconds
- Expected WPM: 150 × 1.167 = 175.0 WPM ✅ **Matches target!**

### 10. Metadata Extraction (MANDATORY)

**⚠️ CRITICAL**: After successful audio generation and tempo analysis, you MUST extract and display metadata for use with the convert-audio skill.

**Purpose**: The metadata (title, artist, description) will be embedded into the final audio file (MP3) when using the convert-audio skill. This step ensures proper podcast metadata for media players and podcast platforms.

#### Extraction Process

**Use a Task sub-agent to extract metadata from the script file:**

1. **Title Extraction:**
   - Extract the title from the script file
   - Ensure the title is consistent with the script filename
   - Examples:
     - `future-of-ai-in-healthcare_20251107.md` → "The Future of AI in Healthcare"
     - `episode-5-quantum-computing_20251107.md` → "Episode 5: Quantum Computing"
     - `interview-sarah-chen-on-mlops_20251107.md` → "Interview: Sarah Chen on MLOps"

2. **Artist Collection:**
   - Extract persona names from the script (the character names that listeners hear, NOT the voice names)
   - Combine persona names with voice names used during audio generation
   - Format as: "Persona (Voice name)", comma-separated
   - Example: If script has "Dr. Sarah Chen", "Alex Martinez", "Prof. Duncan Wade" and voices are Helen, Ryan, Duncan:
     - Result: `Dr. Sarah Chen (Helen voice), Alex Martinez (Ryan voice), Prof. Duncan Wade (Duncan voice)`

3. **Description Extraction:**
   - Extract description from script content or topic
   - Should provide context about the podcast episode
   - Example: "A technical discussion about AI development practices"

#### Display Metadata

After extraction, display the metadata in this format:

```
=== Podcast Metadata ===
Title: [Extracted title]
Artist: [Persona1 (Voice1 voice), Persona2 (Voice2 voice), Persona3 (Voice3 voice)]
Description: [Extracted description]
========================

These metadata fields can be embedded into the final audio file using the convert-audio skill.
```

**Important Notes:**
- This step only displays the metadata; it does not modify any files
- The metadata is provided so the LLM can pass it to the convert-audio skill
- Metadata extraction uses a sub-agent for efficient processing
- This step only runs after successful audio generation (don't waste resources if generation fails)

### 11. Tempo Adjustment Recommendation

**⚠️ CRITICAL**: Based on the drift percentage, you MUST provide recommendations for tempo adjustment using the convert-audio skill:

#### Case 1: Drift ≤ 5% (Acceptable Range)

**Action: No adjustment needed**

Display message:
```
✅ Speech tempo within acceptable range:
   Actual: {actual_wpm:.1f} WPM
   Target: {target_wpm} WPM
   Drift: {drift_percentage:.1f}% (≤5% threshold)

   No speed adjustment required. Audio quality is optimal.
```

**Do NOT recommend any speed adjustment.** The WAV file is ready for use.

#### Case 2: Drift 5-30% (Moderate Adjustment - RECOMMEND CONVERSION)

**Action: Recommend using convert-audio skill**

Display message:
```
⚙️ Tempo adjustment recommended:
   Actual: {actual_wpm:.1f} WPM
   Target: {target_wpm} WPM
   Drift: {drift_percentage:.1f}% (5-30% range)
   Speed factor: {speed_factor:.2f}x

   To adjust the audio tempo, use the convert-audio skill with these parameters:
   - Input file: {wav_file_path}
   - Output format: MP3
   - Speed factor: {speed_factor:.2f}
   - Bitrate: 64 kbps (recommended for podcasts)

   Example command:
   Use convert-audio skill to convert {wav_file_path} to MP3 with speed adjustment of {speed_factor:.2f}x
```

**You MUST:**
1. Inform the user that tempo adjustment is recommended
2. Provide the exact speed factor calculated from the analysis
3. Recommend using the convert-audio skill
4. Include the specific parameters needed

#### Case 3: Drift > 30% (Extreme Adjustment - WARN USER)

**Action: Warn user and ask if they want to proceed with conversion**

Display warning message:
```
⚠️ WARNING: Large Speed Adjustment Required

Current speed: {actual_wpm:.1f} WPM
Target speed: {target_wpm} WPM
Drift: {drift_percentage:.1f}% (>30% threshold)
Required speed factor: {speed_factor:.2f}x

This requires significant speed adjustment (>30% drift).
Large speed adjustments may noticeably affect audio quality and naturalness:
- Pitch shifting may sound artificial
- Speech rhythm may become unnatural
- Audio artifacts may be introduced

Recommendations:
1. Accept the current speech rate (no adjustment needed)
2. Regenerate the podcast with adjusted script or TTS settings
3. Proceed with conversion anyway (audio quality may be affected)

If you want to proceed with tempo adjustment, use the convert-audio skill:
- Input file: {wav_file_path}
- Output format: MP3
- Speed factor: {speed_factor:.2f}
- Bitrate: 64 kbps
```

**Wait for user decision:**
- User can use convert-audio skill if they choose to proceed
- User can accept the WAV file as-is if they decline adjustment
- User can regenerate the podcast with different settings

#### Important Notes

- **WAV preservation**: The original WAV file is always provided
- **Conversion delegation**: All format conversion and speed adjustment is handled by the convert-audio skill
- **This skill only generates WAV**: Audio generation ends after downloading the WAV file and performing tempo analysis
- **Quality**: Moderate adjustments (5-30%) via convert-audio skill typically have minimal perceptible quality impact

## Example

### Example Input

```
Generate podcast from ~/tech-podcast_20251025143000.md with three hosts using built-in voices: Alice, Carter, and Frank.

Script: ~/tech-podcast_20251025143000.md
Speakers: Alice Carter Frank
Region: us-west-2
Budget: Standard performance
```

### Example Commands

```bash
# Step 1 (one-time): Set up infrastructure
python3 scripts/setup_infrastructure.py \
  --profile YOUR_PROFILE \
  --region us-west-2
```

```bash
# Step 2: Generate audio (note: timestamp in filename prevents file conflicts)
python3 generate_podcast_audio.py \
  --script-path ~/tech-podcast_20251025143000.md \
  --speaker-names Alice Carter Frank \
  --profile YOUR_PROFILE \
  --region us-west-2 \
  --output-dir ~/podcast-outputs
```

### Example Command (with custom voices)

```bash
python3 generate_podcast_audio.py \
  --script-path ~/tech-podcast_20251025143000.md \
  --speaker-names Jordan Sam Alex \
  --voices-dir ~/my-voices \
  --profile YOUR_PROFILE \
  --region us-west-2 \
  --output-dir ~/podcast-outputs
```

### Expected Output

```
✅ Script format validated successfully
✅ Infrastructure verified (S3 bucket, IAM roles, state machine present)
✅ EC2 instance launched: i-0abc123def456 (g6.4xlarge)
✅ Dependencies installed
✅ Audio generation completed
✅ Files downloaded:
   - ~/podcast-outputs/tech-podcast_20251025143000.wav
✅ AWS resources cleaned up automatically

=== Phase 7: Orphaned Resource Detection ===
Scanning for orphaned resources from other runs (max age: 12 hours)...

Orphaned Resource Detection Report:
  EC2 Instances: 0 found
  Security Groups: 0 found
  IAM Roles: 0 found

✅ No orphaned resources detected

📊 Speech Tempo Analysis:
   Audio duration: 900s (15m 0s)
   Word count: 2625 words
   Actual speech rate: 175.0 WPM
   Target speech rate: 175 WPM
   Required speed adjustment: 1.00x

=== Podcast Metadata ===
Title: The Future of AI in Healthcare
Artist: Dr. Sarah Chen (Alice voice), Alex Martinez (Carter voice), Prof. Duncan Wade (Frank voice)
Description: A technical discussion exploring how artificial intelligence is transforming modern healthcare delivery and patient outcomes
========================

These metadata fields can be embedded into the final audio file using the convert-audio skill.

Total execution time: ~40 minutes (for 2,000-word script)
  Formula: Execution_Time ≈ 20 + (Word_Count / 100) minutes
  Example: 20 + (2000 / 100) = 20 + 20 = 40 minutes
```

**Note:** If orphaned resources are detected, they will be listed with their IDs, names, ages, and instance types. You can then use the cleanup script to investigate or terminate them if needed.

## Troubleshooting

### Script Validation Errors

**Issue:** Script format validation fails before EC2 launch

**Common Causes:**
- Lines missing "Speaker N:" prefix
- Markdown headers or comments in script
- Empty lines or whitespace-only lines

**Solution:**
```bash
# Check script format manually
grep -v "^Speaker [0-9]" your-script.md

# Each non-empty line should start with "Speaker N:"
# Fix any lines that don't match this pattern
```

### Instance Capacity Issues

**Issue:** "InsufficientInstanceCapacity" error

**Solution:**
If the requested instance type is unavailable:
- Try a different instance type: `--instance-type g6e.2xlarge`
- Try a different region: `--region us-east-1`
- Try during off-peak hours
- Check AWS console for capacity status

**Note:** The script does not automatically fall back to alternative instance types. You must manually specify a different type if the default is unavailable.

### SSM Connection Problems

**Issue:** SSM connection fails or times out

**Solution:**
The script includes built-in SSM retry logic with exponential backoff:
- Retries failed commands up to 5 times
- Increases delay between attempts (10s, 20s, 40s, 80s, 160s)
- Waits up to 3.5 minutes for SSM agent to come online

**Enable verbose output for debugging:**
```bash
python3 generate_podcast_audio.py \
  --script-path script.md \
  --speaker-names Alice Frank \
  --region us-west-2 \
  --verbose
```

With `--verbose`, you'll see:
- Full SSM command IDs
- Complete STDOUT output from remote commands
- Complete STDERR output (errors/warnings)
- Command execution status
- Helps identify exactly where failures occur

If problems persist:
- Verify IAM instance profile has SSM permissions (AmazonSSMManagedInstanceCore)
- Check that instance has internet access (for SSM agent communication)
- Ensure AWS CLI profile has correct permissions
- Verify VPC endpoints for SSM if using private subnets

### Audio Generation Failures

**Issue:** Generation process fails or produces no output

**Solution:**
Check the script logs for specific error messages. Common issues:

1. **OOM (Out of Memory):**
   - Script too long for selected instance type
   - Try an instance type with more memory

2. **Model download failures:**
   - Network connectivity issues
   - Script will retry automatically
   - Check instance has internet access

3. **Script format issues:**
   - Despite validation, complex formatting may cause issues
   - Simplify script (remove special characters)
   - Ensure consistent "Speaker N:" format

### Cleanup Issues

**Issue:** Resources not cleaned up after script exits

**Cause:** Script was forcefully killed (kill -9) or cleanup handlers failed

**Solution:**
The script registers cleanup handlers for graceful shutdown (Ctrl+C). If you forcefully killed the script or cleanup failed, refer to the detailed **manual cleanup commands in Section 5: Shutdown and Resource Cleanup** above.

**Prevention:**
- Always use Ctrl+C (SIGINT) to stop the script - this triggers automatic cleanup
- Never use `kill -9` unless absolutely necessary
- The script catches SIGINT, SIGTERM, and uses atexit handlers for reliability

## Notes

- **Instance auto-termination:** All instances automatically shut down after 12 hours
- **Orphaned resource detection:** Script automatically scans for stuck instances from other runs (within 12-hour window) at the end of each workflow
- **Model caching:** First run downloads models (~5GB), subsequent runs reuse cached models
- **Audio format:** Generated as WAV file only; use separate skill for format conversion
- **Speech tempo analysis:** MANDATORY post-generation analysis using ffprobe to calculate actual WPM and drift percentage; for 5-30% drift, recommend convert-audio skill for speed adjustment; for >30% drift, warn user and let them decide
- **Metadata extraction:** MANDATORY post-generation extraction of title, artist, and description using sub-agent; metadata displayed for use with convert-audio skill to embed into final MP3 files
- **Signal handling:** Ctrl+C triggers graceful cleanup (SIGINT/SIGTERM handlers)
- **Timeout protection:** 4-hour maximum generation time before timeout
- **S3 storage:** Audio files transferred via S3 with 24-hour retention as backup
- **S3 bucket:** Auto-created as `podcast-temp-{account-id}-{region}` with automatic 24-hour lifecycle policy for file deletion
- **No SSH required:** Uses AWS Systems Manager (SSM) for secure command execution
- **Debugging support:** Use `--verbose` flag to see all SSM commands, output, and execution status

## Self-Improvement: Documenting Execution Lessons

**IMPORTANT:** At the end of your execution, output a "Lessons from This Execution" section that documents what could make this skill better.

**Format:** For each problem encountered, write a concise problem-solution pair:
- **What went wrong or caused confusion** (1 sentence describing the actual issue you hit)
- **How the skill should be updated** (1 sentence describing the specific instruction/clarification to add)