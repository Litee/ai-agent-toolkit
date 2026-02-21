---
name: generate-podcast-audio
description: Convert podcast scripts into high-quality audio using text-to-speech synthesis on AWS. Use when generating podcast audio, voice content, or converting scripts to speech.
---

# Podcast Audio Generator

Convert formatted podcast scripts into high-quality audio using VibeVoice text-to-speech synthesis on AWS EC2 GPU instances.

## 🚀 Implementation

This skill uses a Step Functions-based orchestration script for robust podcast generation:

**Script**: `scripts/generate_podcast_audio.py`
- ✅ **Guaranteed cleanup** even if script crashes or client disconnects
- ✅ Visual workflow tracking in AWS console
- ✅ Built-in retry logic and error handling
- ✅ Can disconnect and check status later
- ✅ Execution audit trails
- ✅ Idempotent IAM role creation (policies always ensured on every run)

**Why Step Functions?**
Step Functions provides stronger guarantees for cleanup and error handling compared to direct execution, making it production-ready for all workloads.

## 🤖 CRITICAL DIRECTIVE: Automatic Cleanup

**⚠️ MANDATORY:** The script handles resource cleanup automatically:
- **Step Functions**: Cleanup guaranteed via Catch blocks, runs even if client disconnects
- **Automatic cleanup** of temporary resources (EC2 instances, security groups deleted immediately; S3 files retained for 24-hour backup then auto-deleted via bucket lifecycle policy)

**NEVER ask the user to manually clean up resources** unless the script is blocked/failed.

## 💰 AWS Resources & Costs

**Per Run:** Creates temporary EC2 instance (~$1.35/hr for g6.4xlarge) that auto-terminates after completion.

**Step Functions Overhead:** ~$0.025 per 1,000 state transitions (<$0.05 per podcast, <5% of total cost)

**One-Time Setup:** Creates permanent S3 bucket and IAM roles (reused across runs, minimal/no cost). Safe for concurrent executions.

## ⚠️ MANDATORY: Read Detailed Instructions First

**🚨 CRITICAL: Before using this skill, you MUST read [`references/generate-podcast-audio.md`](references/generate-podcast-audio.md) in full.**

The reference contains essential information about:
- Complete parameter details, voice ordering, and usage examples
- AWS resource management and cleanup procedures
- Troubleshooting guide for common issues
- Cost estimates and instance type options

**Do NOT proceed without reading the reference.** The information below is only a quick overview.

## Required Inputs

- **Script file**: Must follow the "Speaker N:" format for each line
  - **Duration Limit**: The ML model has a maximum limit of 60 minutes (1 hour) for audio generation
  - **Validation Required**: Before generating audio, you MUST validate the script duration and ask for user confirmation if it may exceed 60 minutes
- **Voice selection**: Choose from available voice profiles for each speaker
- **AWS region**: Specify the AWS region for EC2 instance deployment
- **Speech tempo**: Track the speech_tempo value from script generation (default: 175 WPM)
  - Used for mandatory tempo analysis after audio generation
  - Needed to calculate drift and determine if speed adjustment is required

### 🚨 CRITICAL: Output File Naming

**ALWAYS include timestamps in output filenames to prevent file conflicts:**
- Use script names with timestamps in `YYYYMMDDHHmmss` format: `--script-path podcast_20251025143000.md`
- OR use timestamped output directories: `--output-dir ~/podcasts/output_20251025143000/`
- Without timestamps, different podcast generations will overwrite each other when downloaded to the same directory

## Execution Time Estimates

**BEFORE running the Python script**, calculate execution time estimate:

```bash
# Count words in script
word_count=$(python scripts/calculate_podcast_metrics.py count-words --file script.txt)

# Calculate estimate: 20 + (word_count / 100) minutes
# Example: 8,000 words ≈ 100 minutes (20 + 8000/100)
```

**Note**: First-run with cold cache may add 5-10 minutes

### 🕐 CRITICAL: Communicate Expected Completion Time

**MANDATORY BEHAVIOR:** After starting audio generation, you MUST:
1. Calculate estimated completion time: `20 + (word_count / 100)` minutes
2. Tell the user the expected completion time and clock time
3. Inform user they can ask for status after that time
4. **DO NOT continuously poll** - this wastes tokens

**Why:** Audio generation takes 45-120+ minutes. Continuous polling wastes tokens and provides no value.

**Example message to user:**
```
✅ Audio generation started successfully!

📊 Execution Details:
   Word count: 8,000 words
   Estimated duration: ~100 minutes
   Expected completion: ~3:45 PM

🔗 Monitor in AWS Console: [Step Functions URL]

⏰ You can ask me for status after 3:45 PM and I'll check the results.
```

## Workflow Overview

1. **Calculate and communicate execution time** - Estimate duration, inform user of expected completion time
2. **Validation & Setup** - Validate script format and AWS credentials
3. **Infrastructure Creation** - Create S3 bucket, IAM roles, security groups
4. **EC2 Launch** - Launch GPU instance and install dependencies
5. **Audio Generation** - Generate audio using VibeVoice TTS
6. **Download** - Download WAV file from S3
7. **Tempo Analysis (MANDATORY)** - Analyze speech rate and calculate drift percentage
8. **Metadata Extraction (MANDATORY)** - After successful generation:
   - **Use a Task sub-agent** to extract title and description from the script file
   - Title should be consistent with the script filename
   - Collect artist information from the speaker names used in generation
   - Display metadata in clear format for use with convert-audio skill
9. **Tempo Adjustment Decision** - Based on drift:
   - **0-5% drift**: No adjustment needed (optimal quality)
   - **5-30% drift**: Recommend using convert-audio skill with speed adjustment
   - **>30% drift**: Warn user, ask if they want to use convert-audio skill
10. **Cleanup** - Terminate EC2, delete security groups, retain S3 backup for 24 hours

### Output

- **WAV file**: High-quality uncompressed audio (always preserved)
- **Tempo analysis report**: Actual vs. target WPM, drift percentage, speed factor
- **Metadata display**: Title, artist, and description extracted from script for audio conversion
- **Recommendation**: If drift > 5%, recommend using convert-audio skill
- **Cleaned resources**: Temporary AWS resources automatically removed
- **Orphaned resource report**: Detection of stuck instances from other runs

## Bundled Resources

- **scripts/generate_podcast_audio.py** - Step Functions orchestration script
- **scripts/calculate_podcast_metrics.py** - Python script for word counting and duration calculations
- **references/generate-podcast-audio.md** - Complete usage guide (MANDATORY)
- **assets/voices/** - Custom voice samples

## Related Skills

- **generate-podcast-script** - Generate AI-powered podcast scripts
