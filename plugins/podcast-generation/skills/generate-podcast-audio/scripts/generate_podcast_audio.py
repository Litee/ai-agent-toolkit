#!/usr/bin/env python3
"""
Podcast audio generation script.

Generates a podcast audio file from a formatted script using the persistent
AWS infrastructure created by setup_infrastructure.py.

Prerequisites:
  Run setup_infrastructure.py once before using this script:
    python3 setup_infrastructure.py --profile YOUR_PROFILE --region REGION

Usage:
  python3 generate_podcast_audio.py \\
    --script-path path/to/script_20251025143000.md \\
    --speaker-names Alice Frank \\
    --profile YOUR_PROFILE \\
    --region us-west-2
"""

import argparse
import sys
import json
import time
import subprocess
import re
import os
from pathlib import Path
from datetime import datetime, timedelta

from _podcast_shared import (
    BUILTIN_VOICES,
    get_default_voices_dir,
    is_s3_uri,
    list_s3_wav_files,
    copy_s3_to_s3,
    log_progress,
    get_aws_account_id,
    get_aws_region,
    upload_to_s3,
    download_from_s3,
    get_bucket_name,
    get_ec2_instance_profile_name,
    get_state_machine_arn,
    get_ec2_role_name,
    get_state_machine_name,
)


# ---------------------------------------------------------------------------
# Infra verification
# ---------------------------------------------------------------------------

def verify_infrastructure(*, profile: str, region: str, account_id: str) -> None:
    """
    Verify that persistent infrastructure exists before attempting generation.
    Fails fast with a clear message if setup_infrastructure.py has not been run.
    """
    log_progress("Verifying infrastructure...")

    bucket_name = get_bucket_name(account_id, region)
    ec2_role_name = get_ec2_role_name(account_id, region)
    state_machine_name = get_state_machine_name(region)

    errors = []

    # Check S3 bucket
    result = subprocess.run([
        "aws", "s3api", "head-bucket",
        "--profile", profile,
        "--bucket", bucket_name
    ], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        errors.append(f"S3 bucket not found: {bucket_name}")

    # Check EC2 role (proxy for all IAM roles)
    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", ec2_role_name
    ], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        errors.append(f"EC2 IAM role not found: {ec2_role_name}")

    # Check Step Functions state machine
    result = subprocess.run([
        "aws", "stepfunctions", "describe-state-machine",
        "--profile", profile,
        "--region", region,
        "--state-machine-arn", get_state_machine_arn(account_id, region)
    ], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        errors.append(f"Step Functions state machine not found: {state_machine_name}")

    if errors:
        log_progress("Infrastructure verification failed:", "ERROR")
        for err in errors:
            log_progress(f"  - {err}", "ERROR")
        log_progress(
            f"\nRun setup first: python3 setup_infrastructure.py "
            f"--profile {profile} --region {region}",
            "ERROR"
        )
        raise Exception("Infrastructure not set up. Run setup_infrastructure.py first.")

    log_progress("Infrastructure verified")


# ---------------------------------------------------------------------------
# Script validation and metrics
# ---------------------------------------------------------------------------

def validate_script_format(script_path: str) -> None:
    """Validate script file format before launching Step Functions execution."""
    log_progress("Validating script format...")

    if not os.path.exists(script_path):
        raise ValueError(f"Script file not found: {script_path}")

    with open(script_path, 'r') as f:
        lines = f.readlines()

    if not lines:
        raise ValueError("Script file is empty")

    errors = []
    speaker_pattern = re.compile(r'^Speaker \d+:')

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue

        if line.startswith('#'):
            errors.append(f"Line {line_num}: Contains markdown header: {line[:50]}")

        if line.startswith('//') or line.startswith('/*'):
            errors.append(f"Line {line_num}: Contains comment: {line[:50]}")

        if not speaker_pattern.match(line):
            errors.append(f"Line {line_num}: Missing 'Speaker N:' format: {line[:50]}")

    if errors:
        error_msg = "Script format validation failed:\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_msg += f"\n... and {len(errors) - 10} more errors"
        raise ValueError(error_msg)

    log_progress("Script format validation passed")


def count_script_words(script_path: str) -> int:
    """Count words in the script, excluding 'Speaker N:' prefixes."""
    with open(script_path, 'r') as f:
        lines = f.readlines()

    speaker_pattern = re.compile(r'^Speaker \d+:\s*')
    total_words = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        content = speaker_pattern.sub('', line)
        total_words += len(content.split())

    return total_words


def calculate_expected_completion(word_count: int) -> tuple[int, str]:
    """Calculate expected completion time based on word count."""
    estimate_minutes = int(20 + (word_count / 100)) + 1
    completion_time = datetime.now() + timedelta(minutes=estimate_minutes)
    return estimate_minutes, completion_time.strftime("%H:%M")


# ---------------------------------------------------------------------------
# AMI lookup
# ---------------------------------------------------------------------------

def find_ami(*, profile: str, region: str) -> str:
    """Find the latest Ubuntu Deep Learning AMI."""
    log_progress("Finding Ubuntu Deep Learning AMI...")
    result = subprocess.run([
        "aws", "ec2", "describe-images",
        "--profile", profile,
        "--region", region,
        "--owners", "amazon",
        "--filters",
        "Name=name,Values=Deep Learning OSS Nvidia Driver AMI GPU PyTorch * (Ubuntu 22.04) *",
        "Name=state,Values=available",
        "--query", "Images | sort_by(@, &CreationDate) | [-1].ImageId",
        "--output", "text"
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to find AMI: {result.stderr}")

    ami_id = result.stdout.strip()
    log_progress(f"Using AMI: {ami_id}")
    return ami_id


# ---------------------------------------------------------------------------
# Voice handling
# ---------------------------------------------------------------------------

def verify_voices_directory(voices_dir: str | None = None, *, profile: str | None = None) -> list[str]:
    """Verify voice files exist and return list of WAV filenames.

    Accepts either a local directory path or an S3 URI (s3://bucket/prefix/).
    When voices_dir is an S3 URI, profile must be provided.
    """
    resolved_dir: str = voices_dir if voices_dir is not None else get_default_voices_dir()

    if is_s3_uri(resolved_dir):
        if profile is None:
            raise ValueError("profile is required when voices_dir is an S3 URI")
        wav_filenames = list_s3_wav_files(profile=profile, s3_uri=resolved_dir)
        if not wav_filenames:
            raise ValueError(f"No voice files (.wav) found in: {resolved_dir}")
        log_progress(f"Found {len(wav_filenames)} voice files in {resolved_dir}")
        for name in sorted(wav_filenames):
            log_progress(f"  - {name}")
        return wav_filenames

    voices_path = Path(resolved_dir)
    if not voices_path.exists():
        raise FileNotFoundError(f"Voices directory not found: {voices_path.absolute()}")

    wav_files = list(voices_path.glob("*.wav"))
    if not wav_files:
        raise ValueError(f"No voice files (.wav) found in: {voices_path.absolute()}")

    log_progress(f"Found {len(wav_files)} voice files in {resolved_dir}/")
    for wav_file in sorted(wav_files):
        log_progress(f"  - {wav_file.name}")

    return [f.name for f in wav_files]


def upload_voices(*, profile: str, bucket: str, timestamp: str, speaker_names: list[str],
                  voices_dir: str | None = None) -> None:
    """Upload custom voice samples to S3 for specified speakers.

    voices_dir may be a local directory path or an S3 URI (s3://bucket/prefix/).
    For S3 URIs, matched voice files are copied S3-to-S3 into the temp bucket.
    """
    resolved_dir: str = voices_dir if voices_dir is not None else get_default_voices_dir()

    builtin_requested = []
    custom_requested = []
    for speaker_name in speaker_names:
        if speaker_name.lower() in BUILTIN_VOICES:
            builtin_requested.append(speaker_name)
        else:
            custom_requested.append(speaker_name)

    if builtin_requested:
        log_progress(f"Built-in voices (available after VibeVoice clone): {', '.join(builtin_requested)}")

    if not custom_requested:
        log_progress("No custom voices to upload (using built-in voices only)")
        return

    if is_s3_uri(resolved_dir):
        # --- S3 source: list, match, then S3-to-S3 copy ---
        src_prefix = resolved_dir if resolved_dir.endswith("/") else resolved_dir + "/"
        all_wav_filenames = list_s3_wav_files(profile=profile, s3_uri=src_prefix)

        matched_filenames = [
            fname for fname in all_wav_filenames
            if any(name.lower() in Path(fname).stem.lower() for name in custom_requested)
        ]

        missing_custom_voices = [
            name for name in custom_requested
            if not any(name.lower() in Path(fname).stem.lower() for fname in matched_filenames)
        ]
        if missing_custom_voices:
            available_stems = [Path(f).stem for f in all_wav_filenames]
            raise ValueError(
                f"Custom voice files not found: {missing_custom_voices}. "
                f"Available custom voices: {', '.join(available_stems)}. "
                f"Available built-in voices: {', '.join(sorted(BUILTIN_VOICES))}"
            )

        log_progress(f"Copying {len(matched_filenames)} custom voice files from S3 to temp bucket...")
        for fname in matched_filenames:
            src_uri = src_prefix + fname
            dst_uri = f"s3://{bucket}/{timestamp}/voices/{fname}"
            copy_s3_to_s3(profile=profile, src_uri=src_uri, dst_uri=dst_uri)
            log_progress(f"  {fname}")
    else:
        # --- Local source: glob, match, then upload ---
        voices_path = Path(resolved_dir)
        all_wav_files = list(voices_path.glob("*.wav"))

        custom_wav_files = [
            wav_file for wav_file in all_wav_files
            if any(name.lower() in wav_file.stem.lower() for name in custom_requested)
        ]

        missing_custom_voices = [
            name for name in custom_requested
            if not any(name.lower() in wav_file.stem.lower() for wav_file in custom_wav_files)
        ]
        if missing_custom_voices:
            available_custom_voices = [f.stem for f in all_wav_files]
            raise ValueError(
                f"Custom voice files not found: {missing_custom_voices}. "
                f"Available custom voices: {', '.join(available_custom_voices)}. "
                f"Available built-in voices: {', '.join(sorted(BUILTIN_VOICES))}"
            )

        log_progress(f"Uploading {len(custom_wav_files)} custom voice files to S3...")
        for wav_file in custom_wav_files:
            s3_key = f"{timestamp}/voices/{wav_file.name}"
            upload_to_s3(profile=profile, bucket=bucket, local_path=str(wav_file), s3_key=s3_key)
            log_progress(f"  {wav_file.name}")


# ---------------------------------------------------------------------------
# Step Functions execution
# ---------------------------------------------------------------------------

def start_execution(*, profile: str, region: str, state_machine_arn: str,
                    execution_input: dict) -> str:
    """Start Step Functions execution. Returns execution ARN."""
    execution_name = f"podcast-{execution_input['timestamp']}"
    log_progress(f"Starting execution: {execution_name}")

    result = subprocess.run([
        "aws", "stepfunctions", "start-execution",
        "--profile", profile,
        "--region", region,
        "--state-machine-arn", state_machine_arn,
        "--name", execution_name,
        "--input", json.dumps(execution_input)
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to start execution: {result.stderr}")

    execution_arn = json.loads(result.stdout)['executionArn']
    log_progress(f"Execution started: {execution_arn}")
    return execution_arn


def monitor_execution(*, profile: str, region: str, execution_arn: str) -> dict:
    """Monitor Step Functions execution until completion."""
    log_progress("Monitoring execution...")
    log_progress(
        f"View in console: https://{region}.console.aws.amazon.com/states/home"
        f"?region={region}#/executions/details/{execution_arn}"
    )

    while True:
        result = subprocess.run([
            "aws", "stepfunctions", "describe-execution",
            "--profile", profile,
            "--region", region,
            "--execution-arn", execution_arn,
            "--output", "json"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to describe execution: {result.stderr}")

        data = json.loads(result.stdout)
        status = data['status']

        if status == 'SUCCEEDED':
            log_progress("Execution completed successfully!")
            return data

        if status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
            log_progress(f"Execution {status.lower()}", "ERROR")
            if 'error' in data:
                log_progress(f"Error: {data.get('error')}", "ERROR")
            if 'cause' in data:
                log_progress(f"Cause: {data.get('cause')}", "ERROR")
            raise Exception(f"Execution {status.lower()}")

        log_progress(f"Status: {status} - Waiting...")
        time.sleep(30)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Generate podcast audio using AWS Step Functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisite: run setup_infrastructure.py once per account/region first.

Examples:
  # Built-in voices only
  %(prog)s --script-path script_20251025.md --speaker-names Alice Frank \\
           --profile my-profile --region us-west-2

  # With custom voices
  %(prog)s --script-path script_20251025.md --speaker-names MyVoice Alice \\
           --voices-dir ~/my-voices --profile my-profile --region us-west-2
        """
    )
    parser.add_argument('--script-path', required=True,
                        help='Path to podcast script file')
    parser.add_argument('--profile', required=True,
                        help='AWS CLI profile')
    parser.add_argument('--region', default=None,
                        help='AWS region (default: profile\'s configured region)')
    parser.add_argument('--instance-type', default='g6.4xlarge',
                        help='EC2 instance type (default: g6.4xlarge)')
    parser.add_argument('--speaker-names', nargs='+', required=True,
                        help='Speaker voice names in order (e.g., Alice Frank Carter)')
    parser.add_argument('--output-dir', default='.',
                        help='Output directory for audio files (default: same directory as script)')
    parser.add_argument('--voices-dir', default=None,
                        help='Directory containing custom voice WAV files, '
                             'or an S3 URI (s3://bucket/prefix/) for voices already on S3 '
                             '(default: assets/voices/ relative to this script)')

    args = parser.parse_args()
    if args.region is None:
        args.region = get_aws_region(profile=args.profile)
        log_progress(f"No --region specified, using profile default: {args.region}")

    separator = "=" * 80
    log_progress(separator)
    log_progress("PODCAST AUDIO GENERATION")
    log_progress(separator)

    try:
        # Phase 1: Local validation
        log_progress("")
        log_progress("=== Phase 1: Validation ===")
        validate_script_format(args.script_path)

        word_count = count_script_words(args.script_path)
        log_progress(f"Script word count: {word_count} words")

        account_id = get_aws_account_id(profile=args.profile)
        log_progress(f"Account ID: {account_id}")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_progress(f"Timestamp: {timestamp}")

        # Phase 2: Verify infrastructure
        log_progress("")
        log_progress("=== Phase 2: Infrastructure Verification ===")
        verify_infrastructure(profile=args.profile, region=args.region, account_id=account_id)

        # Phase 3: Verify voice files (skip when only built-in voices and no explicit voices_dir)
        all_builtin = all(name.lower() in BUILTIN_VOICES for name in args.speaker_names)
        if args.voices_dir is not None or not all_builtin:
            log_progress("")
            log_progress("=== Phase 3: Verifying Voice Files ===")
            verify_voices_directory(args.voices_dir, profile=args.profile)

        log_progress("")
        log_progress("=== Finding AMI ===")
        ami_id = find_ami(profile=args.profile, region=args.region)

        # Phase 4: Upload to S3
        bucket_name = get_bucket_name(account_id, args.region)
        log_progress("")
        log_progress("=== Phase 4: Uploading Files to S3 ===")

        script_s3_key = f"{timestamp}/script.md"
        upload_to_s3(profile=args.profile, bucket=bucket_name,
                     local_path=args.script_path, s3_key=script_s3_key)

        upload_voices(profile=args.profile, bucket=bucket_name,
                      timestamp=timestamp, speaker_names=args.speaker_names,
                      voices_dir=args.voices_dir)

        # Phase 5: Execute
        ec2_instance_profile = get_ec2_instance_profile_name(account_id, args.region)
        sm_arn = get_state_machine_arn(account_id, args.region)
        speakers = " ".join(args.speaker_names)
        remote_script_path = "/tmp/script.md"

        download_commands = [
            f"mkdir -p ~/VibeVoice/demo/voices",
            f"aws s3 cp s3://{bucket_name}/{script_s3_key} {remote_script_path}",
            f"aws s3 sync s3://{bucket_name}/{timestamp}/voices/ ~/VibeVoice/demo/voices/"
        ]

        generation_command = (
            f"cd VibeVoice && nohup python3 demo/inference_from_file.py "
            f"--model_path vibevoice/VibeVoice-7B "
            f"--txt_path {remote_script_path} "
            f"--speaker_names {speakers} "
            f"> /tmp/podcast-{timestamp}.log 2>&1 &"
        )

        upload_command = [
            f"ls VibeVoice/outputs/*.wav | head -1 | "
            f"xargs -I {{}} aws s3 cp {{}} s3://{bucket_name}/{timestamp}/output.wav"
        ]

        execution_input = {
            "timestamp": timestamp,
            "bucketName": bucket_name,
            "region": args.region,
            "instanceType": args.instance_type,
            "speakerNames": args.speaker_names,
            "scriptPath": remote_script_path,
            "outputDir": args.output_dir,
            "iamInstanceProfile": ec2_instance_profile,
            "amiId": ami_id,
            "generationCommand": generation_command,
            "downloadCommands": download_commands,
            "uploadCommand": upload_command
        }

        log_progress("")
        log_progress("=== Phase 5: Starting Execution ===")
        execution_arn = start_execution(
            profile=args.profile,
            region=args.region,
            state_machine_arn=sm_arn,
            execution_input=execution_input
        )

        estimate_minutes, completion_time = calculate_expected_completion(word_count)
        log_progress(f"Expected completion: ~{estimate_minutes} minutes (around {completion_time})")
        log_progress(f"Tip: Ask for status after {completion_time}")

        log_progress("")
        log_progress("=== Monitoring Execution ===")
        monitor_execution(
            profile=args.profile,
            region=args.region,
            execution_arn=execution_arn
        )

        # Phase 6: Download result
        log_progress("")
        log_progress("=== Phase 6: Downloading Generated Audio ===")
        if args.output_dir == '.':
            output_dir = Path(args.script_path).resolve().parent
        else:
            output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        script_basename = Path(args.script_path).stem
        local_wav = output_dir / f"{script_basename}.wav"

        audio_s3_key = f"{timestamp}/output.wav"
        download_from_s3(
            profile=args.profile,
            bucket=bucket_name,
            s3_key=audio_s3_key,
            local_path=str(local_wav)
        )

        log_progress("")
        log_progress(separator)
        log_progress("EXECUTION COMPLETED SUCCESSFULLY")
        log_progress(separator)
        log_progress(f"Execution ARN:   {execution_arn}")
        log_progress(f"State Machine:   {sm_arn}")
        log_progress(f"Output WAV:      {local_wav}")
        log_progress(f"S3 Backup:       s3://{bucket_name}/{audio_s3_key}")
        log_progress(separator)

    except Exception as e:
        log_progress(f"ERROR: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
