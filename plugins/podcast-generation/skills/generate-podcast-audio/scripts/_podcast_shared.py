#!/usr/bin/env python3
"""
Shared utilities and naming conventions for podcast generation scripts.

This module is used by both setup_infrastructure.py and generate_podcast_audio.py.
All AWS resource names are derived deterministically from (account_id, region)
so no config file handoff is required between the two scripts.
"""

import subprocess
from datetime import datetime
from pathlib import Path


# Built-in VibeVoice voices that come with the cloned repository
BUILTIN_VOICES = {
    'alice', 'carter', 'frank', 'mary'
}


# ---------------------------------------------------------------------------
# Naming conventions
# All resource names are deterministic from (account_id, region).
# ---------------------------------------------------------------------------

def get_bucket_name(account_id: str, region: str) -> str:
    return f"podcast-temp-{account_id}-{region}"


def get_lambda_role_name(account_id: str, region: str) -> str:
    return f"podcast-lambda-role-{account_id}-{region}"


def get_sf_role_name(account_id: str, region: str) -> str:
    return f"podcast-stepfunctions-role-{account_id}-{region}"


def get_ec2_role_name(account_id: str, region: str) -> str:
    return f"podcast-ec2-role-{account_id}-{region}"


def get_ec2_instance_profile_name(account_id: str, region: str) -> str:
    # Instance profile has same name as the EC2 role
    return get_ec2_role_name(account_id, region)


def get_state_machine_name(region: str) -> str:
    return f"podcast-generation-{region}"


def get_state_machine_arn(account_id: str, region: str) -> str:
    name = get_state_machine_name(region)
    return f"arn:aws:states:{region}:{account_id}:stateMachine:{name}"


def get_lambda_role_arn(account_id: str, region: str) -> str:
    name = get_lambda_role_name(account_id, region)
    return f"arn:aws:iam::{account_id}:role/{name}"


def get_sf_role_arn(account_id: str, region: str) -> str:
    name = get_sf_role_name(account_id, region)
    return f"arn:aws:iam::{account_id}:role/{name}"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

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
