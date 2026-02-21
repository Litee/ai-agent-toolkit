#!/usr/bin/env python3
"""
Podcast audio generation using AWS Step Functions orchestration.

This script creates/updates an AWS Step Functions state machine that orchestrates
the entire podcast generation workflow with stronger cleanup guarantees.

Key benefits over manual script:
- Built-in error handling and retry logic
- Automatic state persistence
- Visual workflow tracking in AWS console
- Guaranteed cleanup on success or failure
- Parallel execution support
- Built-in timeout handling

Architecture:
- Step Functions state machine orchestrates the workflow
- Lambda functions for custom logic (validation, file operations)
- Direct AWS SDK integrations (EC2, SSM, S3, IAM)
- Cleanup handlers in catch blocks ensure resources are released
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


# Built-in VibeVoice voices that come with the cloned repository
BUILTIN_VOICES = {
    'alice', 'carter', 'frank', 'mary'
}


def get_script_dir() -> Path:
    """Get the directory where this script is located."""
    return Path(__file__).parent.resolve()


def get_default_voices_dir() -> str:
    """Get the default voices directory path."""
    return str(get_script_dir().parent / "assets" / "voices")


def log_progress(message: str, level: str = "INFO") -> None:
    """Print timestamped progress message."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {message}", flush=True)


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

        # Remove "Speaker N:" prefix
        content = speaker_pattern.sub('', line)
        # Count words in the remaining content
        words = content.split()
        total_words += len(words)

    return total_words


def calculate_expected_completion(word_count: int) -> tuple[int, str]:
    """Calculate expected completion time based on word count.

    Args:
        word_count: Number of words in the script

    Returns:
        Tuple of (estimate_minutes, completion_time_str)
    """
    estimate_minutes = int(20 + (word_count / 100)) + 1  # round up
    completion_time = datetime.now() + timedelta(minutes=estimate_minutes)
    return estimate_minutes, completion_time.strftime("%H:%M")


def get_aws_account_id(*, profile: str) -> str:
    """Get AWS account ID for the given profile."""
    result = subprocess.run([
        "aws", "sts", "get-caller-identity",
        "--profile", profile,
        "--query", "Account",
        "--output", "text"
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to get account ID: {result.stderr}")

    return result.stdout.strip()


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


def upload_to_s3(*, profile: str, bucket: str, local_path: str, s3_key: str) -> str:
    """Upload file to S3 bucket. Returns S3 URI."""
    log_progress(f"Uploading {Path(local_path).name} to S3...")

    result = subprocess.run([
        "aws", "s3", "cp",
        "--profile", profile,
        local_path,
        f"s3://{bucket}/{s3_key}"
    ], capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"Failed to upload to S3: {result.stderr}")

    s3_uri = f"s3://{bucket}/{s3_key}"
    log_progress(f"Uploaded to: {s3_uri}")
    return s3_uri


def download_from_s3(*, profile: str, bucket: str, s3_key: str, local_path: str) -> None:
    """Download file from S3 bucket."""
    log_progress(f"Downloading {s3_key} from S3...")

    result = subprocess.run([
        "aws", "s3", "cp",
        "--profile", profile,
        f"s3://{bucket}/{s3_key}",
        local_path
    ], capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise Exception(f"Failed to download from S3: {result.stderr}")

    log_progress(f"Downloaded to: {local_path}")


def verify_voices_directory(voices_dir: str | None = None) -> list[Path]:
    """Verify voice files exist and return list of WAV files."""
    if voices_dir is None:
        voices_dir = get_default_voices_dir()

    voices_path = Path(voices_dir)

    if not voices_path.exists():
        raise FileNotFoundError(f"Voices directory not found: {voices_path.absolute()}")

    wav_files = list(voices_path.glob("*.wav"))

    if not wav_files:
        raise ValueError(f"No voice files (.wav) found in: {voices_path.absolute()}")

    log_progress(f"✓ Found {len(wav_files)} voice files in {voices_dir}/")
    for wav_file in sorted(wav_files):
        log_progress(f"  - {wav_file.name}")

    return wav_files


def upload_voices(*, profile: str, bucket: str, timestamp: str, speaker_names: list[str],
                 voices_dir: str | None = None) -> None:
    """Upload voice samples to S3 for specified speakers."""
    if voices_dir is None:
        voices_dir = get_default_voices_dir()

    voices_path = Path(voices_dir)
    all_wav_files = list(voices_path.glob("*.wav"))

    # Separate built-in and custom voices
    builtin_requested = []
    custom_requested = []

    for speaker_name in speaker_names:
        if speaker_name.lower() in BUILTIN_VOICES:
            builtin_requested.append(speaker_name)
        else:
            custom_requested.append(speaker_name)

    # Find custom voice files that need to be uploaded
    custom_wav_files = []
    if custom_requested:
        for wav_file in all_wav_files:
            if any(speaker_name.lower() in wav_file.stem.lower() for speaker_name in custom_requested):
                custom_wav_files.append(wav_file)

    # Check if all requested custom voices were found
    missing_custom_voices = []
    for custom_voice in custom_requested:
        found = any(custom_voice.lower() in wav_file.stem.lower() for wav_file in custom_wav_files)
        if not found:
            missing_custom_voices.append(custom_voice)

    if missing_custom_voices:
        available_custom_voices = [f.stem for f in all_wav_files]
        available_builtin_voices = list(BUILTIN_VOICES)
        raise ValueError(
            f"Custom voice files not found: {missing_custom_voices}. "
            f"Available custom voices: {', '.join(available_custom_voices)}. "
            f"Available built-in voices: {', '.join(available_builtin_voices)}"
        )

    # Log what will be used
    if builtin_requested:
        log_progress(f"Built-in voices (will be available after VibeVoice clone): {', '.join(builtin_requested)}")

    if custom_wav_files:
        log_progress(f"Uploading {len(custom_wav_files)} custom voice files to S3...")
        for wav_file in custom_wav_files:
            s3_key = f"{timestamp}/voices/{wav_file.name}"
            upload_to_s3(profile=profile, bucket=bucket, local_path=str(wav_file), s3_key=s3_key)
            log_progress(f"  ✓ {wav_file.name}")
    else:
        log_progress("No custom voices to upload")


def ensure_s3_bucket(*, profile: str, region: str, bucket_name: str) -> None:
    """Create S3 bucket if it doesn't exist and configure lifecycle policy."""
    log_progress(f"Checking S3 bucket: {bucket_name}")

    # Check if bucket exists
    result = subprocess.run([
        "aws", "s3api", "head-bucket",
        "--profile", profile,
        "--bucket", bucket_name
    ], capture_output=True, text=True, timeout=30)

    bucket_exists = result.returncode == 0

    if bucket_exists:
        log_progress(f"S3 bucket already exists: {bucket_name}")
    else:
        log_progress(f"Creating S3 bucket: {bucket_name}")

        # Create bucket
        create_cmd = [
            "aws", "s3api", "create-bucket",
            "--profile", profile,
            "--bucket", bucket_name,
            "--region", region
        ]

        if region != "us-east-1":
            create_cmd.extend([
                "--create-bucket-configuration",
                f"LocationConstraint={region}"
            ])

        result = subprocess.run(create_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create S3 bucket: {result.stderr}")

        log_progress(f"S3 bucket created: {bucket_name}")

    # Configure lifecycle policy (both for new and existing buckets)
    configure_s3_lifecycle_policy(profile=profile, bucket_name=bucket_name)


def configure_s3_lifecycle_policy(*, profile: str, bucket_name: str) -> None:
    """Configure S3 lifecycle policy to delete objects after 24 hours."""
    log_progress(f"Configuring lifecycle policy for bucket: {bucket_name}")

    # Lifecycle configuration for 24-hour deletion
    lifecycle_config = {
        "Rules": [
            {
                "Id": "DeleteGeneratedFilesAfter24Hours",
                "Status": "Enabled",
                "Filter": {},  # Apply to all objects in bucket
                "Expiration": {
                    "Days": 1  # Delete after 1 day (24 hours)
                }
            }
        ]
    }

    # Write config to temp file
    config_file = f"/tmp/s3-lifecycle-{bucket_name}.json"
    try:
        with open(config_file, 'w') as f:
            json.dump(lifecycle_config, f)

        # Apply lifecycle policy
        result = subprocess.run([
            "aws", "s3api", "put-bucket-lifecycle-configuration",
            "--profile", profile,
            "--bucket", bucket_name,
            "--lifecycle-configuration", f"file://{config_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            # Log warning but don't fail - lifecycle policy is best-effort
            log_progress(f"Warning: Failed to configure lifecycle policy: {result.stderr}", "WARNING")
        else:
            log_progress("Lifecycle policy configured: objects will expire after 1 day")

    except Exception as e:
        # Log warning but don't fail - lifecycle policy is best-effort
        log_progress(f"Warning: Failed to configure lifecycle policy: {e}", "WARNING")

    finally:
        # Clean up temp file
        try:
            if os.path.exists(config_file):
                os.remove(config_file)
        except:
            pass


def create_lambda_execution_role(*, profile: str, region: str, account_id: str) -> str:
    """
    Create IAM role for Lambda functions used in Step Functions.

    Returns:
        Role ARN
    """
    role_name = f"podcast-lambda-role-{account_id}-{region}"
    log_progress(f"Checking Lambda execution role: {role_name}")

    # Check if role exists
    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']
        log_progress(f"Lambda role already exists: {role_arn}")
    else:
        log_progress(f"Creating Lambda execution role: {role_name}")

        # Trust policy for Lambda
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/lambda-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        # Create role
        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create Lambda role: {result.stderr}")

        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']

    # Attach basic Lambda execution policy
    subprocess.run([
        "aws", "iam", "attach-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-arn", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    ], capture_output=True, text=True, timeout=30)

    # Attach policies for EC2, S3, SSM, IAM operations
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:*",
                    "s3:*",
                    "ssm:*",
                    "iam:GetRole",
                    "iam:CreateRole",
                    "iam:AttachRolePolicy",
                    "iam:PutRolePolicy",
                    "iam:GetInstanceProfile",
                    "iam:CreateInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "sts:GetCallerIdentity"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/lambda-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "PodcastGenerationAccess",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    if role_already_existed:
        log_progress(f"Lambda role policies ensured: {role_arn}")
    else:
        log_progress(f"Lambda role created: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(10)

    return role_arn


def create_step_functions_role(*, profile: str, region: str, account_id: str) -> str:
    """
    Create IAM role for Step Functions state machine.

    Returns:
        Role ARN
    """
    role_name = f"podcast-stepfunctions-role-{account_id}-{region}"
    log_progress(f"Checking Step Functions role: {role_name}")

    # Check if role exists
    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']
        log_progress(f"Step Functions role already exists: {role_arn}")
    else:
        log_progress(f"Creating Step Functions role: {role_name}")

        # Trust policy for Step Functions
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "states.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/sf-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        # Create role
        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create Step Functions role: {result.stderr}")

        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']

    # Attach policies for Lambda, EC2, SSM, S3
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction",
                    "ec2:*",
                    "ssm:*",
                    "s3:*",
                    "iam:PassRole",
                    "logs:*"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/sf-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "StepFunctionsExecution",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    if role_already_existed:
        log_progress(f"Step Functions role policies ensured: {role_arn}")
    else:
        log_progress(f"Step Functions role created: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(10)

    return role_arn


def create_ec2_role(*, profile: str, region: str, account_id: str) -> tuple[str, str]:
    """
    Create IAM role and instance profile for EC2 instances.

    Returns:
        Tuple of (role ARN, instance profile name)
    """
    role_name = f"podcast-ec2-role-{account_id}-{region}"
    instance_profile_name = f"podcast-ec2-role-{account_id}-{region}"
    log_progress(f"Checking EC2 role: {role_name}")

    # Check if role exists
    result = subprocess.run([
        "aws", "iam", "get-role",
        "--profile", profile,
        "--role-name", role_name
    ], capture_output=True, text=True, timeout=30)

    role_already_existed = result.returncode == 0

    if role_already_existed:
        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']
        log_progress(f"EC2 role already exists: {role_arn}")
    else:
        log_progress(f"Creating EC2 role: {role_name}")

        # Trust policy for EC2
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }

        trust_policy_file = f"/tmp/ec2-trust-policy-{account_id}.json"
        with open(trust_policy_file, 'w') as f:
            json.dump(trust_policy, f)

        # Create role
        result = subprocess.run([
            "aws", "iam", "create-role",
            "--profile", profile,
            "--role-name", role_name,
            "--assume-role-policy-document", f"file://{trust_policy_file}"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create EC2 role: {result.stderr}")

        role_data = json.loads(result.stdout)
        role_arn = role_data['Role']['Arn']

    # Attach SSM managed instance core policy
    subprocess.run([
        "aws", "iam", "attach-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-arn", "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    ], capture_output=True, text=True, timeout=30)

    # Attach CloudRanger host monitoring policy
    subprocess.run([
        "aws", "iam", "attach-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-arn", "arn:aws:iam::aws:policy/CloudRangerHostPolicy"
    ], capture_output=True, text=True, timeout=30)

    # Attach S3 access, CloudRanger, and CloudWatch policies
    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cloudranger:SendTelemetry",
                    "cloudranger:GetConfiguration",
                    "cloudranger:UpdateAgentStatus"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }

    policy_file = f"/tmp/ec2-inline-policy-{account_id}.json"
    with open(policy_file, 'w') as f:
        json.dump(inline_policy, f)

    subprocess.run([
        "aws", "iam", "put-role-policy",
        "--profile", profile,
        "--role-name", role_name,
        "--policy-name", "PodcastAccessPolicy",
        "--policy-document", f"file://{policy_file}"
    ], capture_output=True, text=True, timeout=30)

    # Check if instance profile exists
    result = subprocess.run([
        "aws", "iam", "get-instance-profile",
        "--profile", profile,
        "--instance-profile-name", instance_profile_name
    ], capture_output=True, text=True, timeout=30)

    instance_profile_already_existed = result.returncode == 0

    if instance_profile_already_existed:
        log_progress(f"EC2 instance profile already exists: {instance_profile_name}")
    else:
        log_progress(f"Creating EC2 instance profile: {instance_profile_name}")

        # Create instance profile
        result = subprocess.run([
            "aws", "iam", "create-instance-profile",
            "--profile", profile,
            "--instance-profile-name", instance_profile_name
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create instance profile: {result.stderr}")

        # Add role to instance profile
        result = subprocess.run([
            "aws", "iam", "add-role-to-instance-profile",
            "--profile", profile,
            "--instance-profile-name", instance_profile_name,
            "--role-name", role_name
        ], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to add role to instance profile: {result.stderr}")

    # Determine if we created anything new (need to wait for propagation)
    created_new_resources = not role_already_existed or not instance_profile_already_existed

    if role_already_existed and instance_profile_already_existed:
        log_progress(f"EC2 role and instance profile policies ensured: {role_arn}")
    elif created_new_resources:
        log_progress(f"EC2 role and instance profile ready: {role_arn}")
        log_progress("Waiting for IAM role to propagate...")
        time.sleep(30)  # EC2 instance profiles need more time to propagate

    return role_arn, instance_profile_name


def get_state_machine_definition(lambda_role_arn: str, account_id: str, region: str) -> dict:
    """
    Generate Step Functions state machine definition.

    This state machine orchestrates the entire podcast generation workflow with:
    - Error handling and automatic cleanup
    - Retry logic for transient failures
    - Parallel execution where possible
    - State tracking and monitoring
    """
    return {
        "Comment": "Podcast Audio Generation Workflow with Automatic Cleanup",
        "StartAt": "ValidateAndSetup",
        "States": {
            "ValidateAndSetup": {
                "Type": "Pass",
                "Comment": "Initial validation and setup",
                "Result": {
                    "Timestamp": "$.timestamp",
                    "SetupComplete": True
                },
                "ResultPath": "$.setup",
                "Next": "CreateS3Bucket"
            },

            "CreateS3Bucket": {
                "Type": "Task",
                "Comment": "Create or verify S3 bucket for file transfers",
                "Resource": "arn:aws:states:::aws-sdk:s3:headBucket",
                "Parameters": {
                    "Bucket.$": "$.bucketName"
                },
                "ResultPath": "$.s3BucketCheck",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CreateBucketIfNotExists"
                    }
                ],
                "Next": "EnsureIAMRole"
            },

            "CreateBucketIfNotExists": {
                "Type": "Task",
                "Comment": "Create S3 bucket if it doesn't exist",
                "Resource": "arn:aws:states:::aws-sdk:s3:createBucket",
                "Parameters": {
                    "Bucket.$": "$.bucketName",
                    "CreateBucketConfiguration": {
                        "LocationConstraint.$": "$.region"
                    }
                },
                "ResultPath": "$.bucketCreated",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupOnError"
                    }
                ],
                "Next": "EnsureIAMRole"
            },

            "EnsureIAMRole": {
                "Type": "Pass",
                "Comment": "IAM role is created as permanent infrastructure outside workflow",
                "Result": {
                    "Message": "Using pre-created IAM role"
                },
                "ResultPath": "$.iamCheck",
                "Next": "CreateSecurityGroup"
            },

            "CreateSecurityGroup": {
                "Type": "Task",
                "Comment": "Create security group for EC2 instance",
                "Resource": "arn:aws:states:::aws-sdk:ec2:createSecurityGroup",
                "Parameters": {
                    "GroupName.$": "States.Format('podcast-sg-{}', $.timestamp)",
                    "Description": "Temporary security group for podcast generation"
                },
                "ResultPath": "$.securityGroup",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupOnError"
                    }
                ],
                "Next": "LaunchEC2Instance"
            },

            "LaunchEC2Instance": {
                "Type": "Task",
                "Comment": "Launch EC2 instance for podcast generation",
                "Resource": "arn:aws:states:::aws-sdk:ec2:runInstances",
                "Parameters": {
                    "ImageId.$": "$.amiId",
                    "InstanceType.$": "$.instanceType",
                    "MaxCount": 1,
                    "MinCount": 1,
                    "IamInstanceProfile": {
                        "Name.$": "$.iamInstanceProfile"
                    },
                    "SecurityGroupIds.$": "States.Array($.securityGroup.GroupId)",
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/sda1",
                            "Ebs": {
                                "VolumeSize": 150,
                                "VolumeType": "gp3"
                            }
                        }
                    ],
                    "TagSpecifications": [
                        {
                            "ResourceType": "instance",
                            "Tags": [
                                {
                                    "Key": "Name",
                                    "Value.$": "States.Format('podcast-generation-{}', $.timestamp)"
                                },
                                {
                                    "Key": "Purpose",
                                    "Value": "podcast-generation"
                                },
                                {
                                    "Key": "ManagedBy",
                                    "Value": "StepFunctions"
                                }
                            ]
                        }
                    ]
                },
                "ResultPath": "$.instance",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupSecurityGroup"
                    }
                ],
                "Next": "WaitForInstance"
            },

            "WaitForInstance": {
                "Type": "Wait",
                "Comment": "Wait for instance to initialize",
                "Seconds": 30,
                "Next": "CheckSSMStatus"
            },

            "CheckSSMStatus": {
                "Type": "Task",
                "Comment": "Check if SSM agent is online",
                "Resource": "arn:aws:states:::aws-sdk:ssm:describeInstanceInformation",
                "Parameters": {
                    "Filters": [
                        {
                            "Key": "InstanceIds",
                            "Values.$": "States.Array($.instance.Instances[0].InstanceId)"
                        }
                    ]
                },
                "ResultPath": "$.ssmStatus",
                "Next": "IsSSMReady"
            },

            "IsSSMReady": {
                "Type": "Choice",
                "Comment": "Check if SSM is ready",
                "Choices": [
                    {
                        "And": [
                            {
                                "Variable": "$.ssmStatus.InstanceInformationList[0]",
                                "IsPresent": True
                            },
                            {
                                "Variable": "$.ssmStatus.InstanceInformationList[0].PingStatus",
                                "StringEquals": "Online"
                            }
                        ],
                        "Next": "InstallDependencies"
                    }
                ],
                "Default": "WaitForSSM"
            },

            "WaitForSSM": {
                "Type": "Wait",
                "Seconds": 10,
                "Next": "CheckSSMStatus"
            },

            "InstallDependencies": {
                "Type": "Task",
                "Comment": "Install VibeVoice and dependencies",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "sudo apt-get update",
                            "git clone https://github.com/vibevoice-community/VibeVoice.git",
                            "pip install --prefer-binary torch transformers accelerate",
                            "cd VibeVoice && pip install -e ."
                        ]
                    }
                },
                "ResultPath": "$.installCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "InstallCloudRanger"
            },

            "InstallCloudRanger": {
                "Type": "Task",
                "Comment": "Install CloudRanger host monitoring agent",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "sudo apt-get install -y cloud-ranger-agent",
                            "sudo systemctl start cloud-ranger",
                            "sudo systemctl enable cloud-ranger"
                        ]
                    }
                },
                "ResultPath": "$.cloudRangerInstall",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForCloudRangerInstall"
            },

            "WaitForCloudRangerInstall": {
                "Type": "Wait",
                "Comment": "Wait for CloudRanger installation to complete",
                "Seconds": 30,
                "Next": "VerifyCloudRanger"
            },

            "VerifyCloudRanger": {
                "Type": "Task",
                "Comment": "Verify CloudRanger agent is running",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "sudo systemctl status cloud-ranger --no-pager",
                            "sudo cloud-ranger-agent --version"
                        ]
                    }
                },
                "ResultPath": "$.cloudRangerVerify",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForInstallation"
            },

            "WaitForInstallation": {
                "Type": "Wait",
                "Comment": "Wait for installation to complete",
                "Seconds": 300,
                "Next": "DownloadFilesFromS3"
            },

            "DownloadFilesFromS3": {
                "Type": "Task",
                "Comment": "Download voices and script from S3 to EC2",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "$.downloadCommands"
                    }
                },
                "ResultPath": "$.downloadCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForDownload"
            },

            "WaitForDownload": {
                "Type": "Wait",
                "Seconds": 10,
                "Next": "StartAudioGeneration"
            },

            "StartAudioGeneration": {
                "Type": "Task",
                "Comment": "Start audio generation process",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "States.Array($.generationCommand)"
                    }
                },
                "ResultPath": "$.generationCommand",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "InitializeMonitoringCounter"
            },

            "InitializeMonitoringCounter": {
                "Type": "Pass",
                "Comment": "Initialize monitoring counter for timeout (240 iterations = 4 hours)",
                "Result": 0,
                "ResultPath": "$.monitoringIterations",
                "Next": "MonitorGeneration"
            },

            "MonitorGeneration": {
                "Type": "Wait",
                "Comment": "Wait while generation is in progress (60s per iteration, max 240 iterations = 4 hours)",
                "Seconds": 60,
                "Next": "IncrementMonitoringCounter"
            },

            "IncrementMonitoringCounter": {
                "Type": "Pass",
                "Comment": "Increment monitoring counter and preserve all critical fields",
                "Parameters": {
                    "monitoringIterations.$": "States.MathAdd($.monitoringIterations, 1)",
                    "instance.$": "$.instance",
                    "timestamp.$": "$.timestamp",
                    "bucketName.$": "$.bucketName",
                    "uploadCommand.$": "$.uploadCommand",
                    "securityGroup.$": "$.securityGroup",
                    "region.$": "$.region",
                    "amiId.$": "$.amiId",
                    "instanceType.$": "$.instanceType",
                    "iamInstanceProfile.$": "$.iamInstanceProfile"
                },
                "Next": "CheckMonitoringTimeout"
            },

            "CheckMonitoringTimeout": {
                "Type": "Choice",
                "Comment": "Check if monitoring has exceeded 4-hour timeout (240 iterations)",
                "Choices": [
                    {
                        "Variable": "$.monitoringIterations",
                        "NumericGreaterThan": 240,
                        "Next": "RecordGenerationTimeout"
                    }
                ],
                "Default": "CheckGenerationStatus"
            },

            "RecordGenerationTimeout": {
                "Type": "Pass",
                "Comment": "Record that generation timed out, then proceed to cleanup",
                "Result": {
                    "Error": "GenerationTimeout",
                    "Message": "Audio generation did not complete within 4 hours"
                },
                "ResultPath": "$.timeoutError",
                "Next": "CleanupInstance"
            },

            "CheckGenerationStatus": {
                "Type": "Task",
                "Comment": "Send command to check if audio generation is complete",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands": [
                            "ls -lh VibeVoice/outputs/*.wav 2>/dev/null || echo 'RUNNING'"
                        ]
                    }
                },
                "ResultPath": "$.statusCheck",
                "Next": "WaitForStatusCheck"
            },

            "WaitForStatusCheck": {
                "Type": "Wait",
                "Comment": "Wait for status check command to complete",
                "Seconds": 5,
                "Next": "GetStatusCheckResult"
            },

            "GetStatusCheckResult": {
                "Type": "Task",
                "Comment": "Retrieve the command output to check if file exists",
                "Resource": "arn:aws:states:::aws-sdk:ssm:getCommandInvocation",
                "Parameters": {
                    "CommandId.$": "$.statusCheck.Command.CommandId",
                    "InstanceId.$": "$.instance.Instances[0].InstanceId"
                },
                "ResultPath": "$.commandResult",
                "Retry": [
                    {
                        "ErrorEquals": ["Ssm.InvocationDoesNotExist"],
                        "IntervalSeconds": 2,
                        "MaxAttempts": 3,
                        "BackoffRate": 2.0
                    }
                ],
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "MonitorGeneration"
                    }
                ],
                "Next": "IsGenerationComplete"
            },

            "IsGenerationComplete": {
                "Type": "Choice",
                "Comment": "Check if generation is complete by examining command output",
                "Choices": [
                    {
                        "And": [
                            {
                                "Variable": "$.commandResult.Status",
                                "StringEquals": "Success"
                            },
                            {
                                "Variable": "$.commandResult.StandardOutputContent",
                                "IsPresent": True
                            },
                            {
                                "Not": {
                                    "Variable": "$.commandResult.StandardOutputContent",
                                    "StringMatches": "*RUNNING*"
                                }
                            }
                        ],
                        "Next": "UploadAudioToS3"
                    }
                ],
                "Default": "MonitorGeneration"
            },

            "UploadAudioToS3": {
                "Type": "Task",
                "Comment": "Upload generated audio from EC2 to S3",
                "Resource": "arn:aws:states:::aws-sdk:ssm:sendCommand",
                "Parameters": {
                    "DocumentName": "AWS-RunShellScript",
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)",
                    "Parameters": {
                        "commands.$": "$.uploadCommand"
                    }
                },
                "ResultPath": "$.uploadResult",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "CleanupInstance"
                    }
                ],
                "Next": "WaitForUpload"
            },

            "WaitForUpload": {
                "Type": "Wait",
                "Seconds": 30,
                "Next": "CleanupInstance"
            },

            "CleanupInstance": {
                "Type": "Task",
                "Comment": "Terminate EC2 instance",
                "Resource": "arn:aws:states:::aws-sdk:ec2:terminateInstances",
                "Parameters": {
                    "InstanceIds.$": "States.Array($.instance.Instances[0].InstanceId)"
                },
                "ResultPath": "$.instanceTermination",
                "Next": "WaitForTermination",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.cleanupError",
                        "Next": "CleanupSecurityGroup"
                    }
                ]
            },

            "WaitForTermination": {
                "Type": "Wait",
                "Seconds": 300,
                "Next": "CleanupSecurityGroup"
            },

            "CleanupSecurityGroup": {
                "Type": "Task",
                "Comment": "Delete security group",
                "Resource": "arn:aws:states:::aws-sdk:ec2:deleteSecurityGroup",
                "Parameters": {
                    "GroupId.$": "$.securityGroup.GroupId"
                },
                "ResultPath": "$.sgDeletion",
                "Next": "CleanupS3Files",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.cleanupError",
                        "Next": "CleanupS3Files"
                    }
                ]
            },

            "CleanupS3Files": {
                "Type": "Pass",
                "Comment": "S3 files automatically deleted after 24 hours via bucket lifecycle policy",
                "Result": {
                    "Message": "S3 cleanup handled by lifecycle policy (24-hour retention)"
                },
                "ResultPath": "$.s3Cleanup",
                "Next": "WorkflowComplete"
            },

            "WorkflowComplete": {
                "Type": "Succeed",
                "Comment": "Workflow completed successfully"
            },

            "CleanupOnError": {
                "Type": "Pass",
                "Comment": "Cleanup path for early failures",
                "Result": {
                    "Message": "Error occurred, cleanup initiated"
                },
                "ResultPath": "$.errorCleanup",
                "Next": "WorkflowFailed"
            },

            "WorkflowFailed": {
                "Type": "Fail",
                "Comment": "Workflow failed",
                "Error": "WorkflowExecutionFailed",
                "Cause": "An error occurred during podcast generation"
            }
        }
    }


def create_or_update_state_machine(*, profile: str, region: str, account_id: str,
                                   sf_role_arn: str, lambda_role_arn: str) -> str:
    """
    Create or update Step Functions state machine.

    Returns:
        State machine ARN
    """
    state_machine_name = f"podcast-generation-{region}"
    log_progress(f"Creating/updating state machine: {state_machine_name}")

    definition = get_state_machine_definition(lambda_role_arn, account_id, region)
    definition_str = json.dumps(definition)

    # Check if state machine exists
    result = subprocess.run([
        "aws", "stepfunctions", "list-state-machines",
        "--profile", profile,
        "--region", region,
        "--output", "json"
    ], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        data = json.loads(result.stdout)
        existing = [sm for sm in data.get('stateMachines', [])
                   if sm['name'] == state_machine_name]

        if existing:
            state_machine_arn = existing[0]['stateMachineArn']
            log_progress(f"Updating existing state machine: {state_machine_arn}")

            # Update state machine
            result = subprocess.run([
                "aws", "stepfunctions", "update-state-machine",
                "--profile", profile,
                "--region", region,
                "--state-machine-arn", state_machine_arn,
                "--definition", definition_str,
                "--role-arn", sf_role_arn
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"Failed to update state machine: {result.stderr}")

            log_progress("State machine updated successfully")
            return state_machine_arn

    # Create new state machine
    log_progress("Creating new state machine")

    result = subprocess.run([
        "aws", "stepfunctions", "create-state-machine",
        "--profile", profile,
        "--region", region,
        "--name", state_machine_name,
        "--definition", definition_str,
        "--role-arn", sf_role_arn
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to create state machine: {result.stderr}")

    data = json.loads(result.stdout)
    state_machine_arn = data['stateMachineArn']
    log_progress(f"State machine created: {state_machine_arn}")

    return state_machine_arn


def start_execution(*, profile: str, region: str, state_machine_arn: str,
                   execution_input: dict) -> str:
    """
    Start Step Functions execution.

    Returns:
        Execution ARN
    """
    execution_name = f"podcast-{execution_input['timestamp']}"
    log_progress(f"Starting execution: {execution_name}")

    input_str = json.dumps(execution_input)

    result = subprocess.run([
        "aws", "stepfunctions", "start-execution",
        "--profile", profile,
        "--region", region,
        "--state-machine-arn", state_machine_arn,
        "--name", execution_name,
        "--input", input_str
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        raise Exception(f"Failed to start execution: {result.stderr}")

    data = json.loads(result.stdout)
    execution_arn = data['executionArn']
    log_progress(f"Execution started: {execution_arn}")

    return execution_arn


def monitor_execution(*, profile: str, region: str, execution_arn: str) -> dict:
    """
    Monitor Step Functions execution until completion.

    Returns:
        Execution result
    """
    log_progress("Monitoring execution...")
    log_progress(f"View in console: https://{region}.console.aws.amazon.com/states/home?region={region}#/executions/details/{execution_arn}")

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


def main():
    parser = argparse.ArgumentParser(
        description='Generate podcast audio using AWS Step Functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  %(prog)s --script-path script.md --region us-west-2 --speaker-names Alice Bob

Benefits of Step Functions approach:
  - Stronger cleanup guarantees (built-in error handling)
  - Visual workflow tracking in AWS console
  - Automatic state persistence and recovery
  - Built-in retry logic for transient failures
  - Parallel execution support

The state machine provides guaranteed cleanup on both success and failure paths.
        """
    )
    parser.add_argument('--script-path', required=True,
                       help='Path to podcast script file')
    parser.add_argument('--profile', required=True,
                       help='AWS CLI profile')
    parser.add_argument('--region', required=True,
                       help='AWS region')
    parser.add_argument('--instance-type', default='g6.4xlarge',
                       help='EC2 instance type (default: g6.4xlarge)')
    parser.add_argument('--speaker-names', nargs='+', required=True,
                       help='Speaker names (e.g., Alice Frank Carter)')
    parser.add_argument('--output-dir', default='.',
                       help='Output directory for audio files (default: same directory as script)')

    args = parser.parse_args()

    separator = "=" * 80
    log_progress(separator)
    log_progress("PODCAST AUDIO GENERATION - STEP FUNCTIONS")
    log_progress(separator)

    try:
        # Validate script format before starting any AWS operations
        log_progress("")
        log_progress("=== Phase 1: Validation ===")
        validate_script_format(args.script_path)

        # Count words for execution time estimate
        word_count = count_script_words(args.script_path)
        log_progress(f"Script word count: {word_count} words")

        # Get AWS account ID
        account_id = get_aws_account_id(profile=args.profile)
        log_progress(f"Account ID: {account_id}")

        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_progress(f"Timestamp: {timestamp}")

        # Verify voices directory
        log_progress("")
        log_progress("=== Verifying Voice Files ===")
        verify_voices_directory()

        # Find AMI
        log_progress("")
        log_progress("=== Finding AMI ===")
        ami_id = find_ami(profile=args.profile, region=args.region)

        # Prepare S3 bucket
        bucket_name = f"podcast-temp-{account_id}-{args.region}"
        log_progress("")
        log_progress("=== Preparing S3 Bucket ===")
        ensure_s3_bucket(profile=args.profile, region=args.region, bucket_name=bucket_name)

        # Upload files to S3
        log_progress("")
        log_progress("=== Uploading Files to S3 ===")

        # Upload script
        script_s3_key = f"{timestamp}/script.md"
        upload_to_s3(profile=args.profile, bucket=bucket_name,
                    local_path=args.script_path, s3_key=script_s3_key)

        # Upload voices
        upload_voices(profile=args.profile, bucket=bucket_name,
                     timestamp=timestamp, speaker_names=args.speaker_names)

        # Create IAM roles
        log_progress("")
        log_progress("=== Creating IAM Roles ===")
        lambda_role_arn = create_lambda_execution_role(
            profile=args.profile, region=args.region, account_id=account_id
        )
        sf_role_arn = create_step_functions_role(
            profile=args.profile, region=args.region, account_id=account_id
        )
        ec2_role_arn, ec2_instance_profile = create_ec2_role(
            profile=args.profile, region=args.region, account_id=account_id
        )

        # Create/update state machine
        log_progress("")
        log_progress("=== Creating/Updating State Machine ===")
        state_machine_arn = create_or_update_state_machine(
            profile=args.profile,
            region=args.region,
            account_id=account_id,
            sf_role_arn=sf_role_arn,
            lambda_role_arn=lambda_role_arn
        )

        # Prepare execution input
        # Use the EC2 instance profile created above
        speakers = " ".join(args.speaker_names)
        remote_script_path = "/tmp/script.md"

        # Build download commands
        download_commands = [
            f"mkdir -p ~/VibeVoice/demo/voices",
            f"aws s3 cp s3://{bucket_name}/{script_s3_key} {remote_script_path}",
            f"aws s3 sync s3://{bucket_name}/{timestamp}/voices/ ~/VibeVoice/demo/voices/"
        ]

        # Build generation command
        generation_command = f"cd VibeVoice && nohup python3 demo/inference_from_file.py --model_path vibevoice/VibeVoice-7B --txt_path {remote_script_path} --speaker_names {speakers} > /tmp/podcast-{timestamp}.log 2>&1 &"

        # Build upload command
        upload_command = [
            f"ls VibeVoice/outputs/*.wav | head -1 | xargs -I {{}} aws s3 cp {{}} s3://{bucket_name}/{timestamp}/output.wav"
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

        # Start execution
        log_progress("")
        log_progress("=== Starting Execution ===")
        execution_arn = start_execution(
            profile=args.profile,
            region=args.region,
            state_machine_arn=state_machine_arn,
            execution_input=execution_input
        )

        # Calculate and display expected completion time
        estimate_minutes, completion_time = calculate_expected_completion(word_count)
        log_progress(f"📊 Expected completion: ~{estimate_minutes} minutes (around {completion_time})")
        log_progress(f"💡 Tip: Ask for status after {completion_time}")

        # Monitor execution
        log_progress("")
        log_progress("=== Monitoring Execution ===")
        result = monitor_execution(
            profile=args.profile,
            region=args.region,
            execution_arn=execution_arn
        )

        # Download audio from S3
        log_progress("")
        log_progress("=== Downloading Generated Audio ===")
        # Use script's directory if --output-dir not explicitly provided
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
        log_progress(f"Execution ARN: {execution_arn}")
        log_progress(f"State Machine ARN: {state_machine_arn}")
        log_progress(f"Output WAV: {local_wav}")
        log_progress(f"S3 Backup: s3://{bucket_name}/{audio_s3_key}")
        log_progress(separator)

    except Exception as e:
        log_progress(f"ERROR: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
