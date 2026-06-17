#!/usr/bin/env python3
"""
ec2_vscode.py — Spin up (or resume) an EC2 instance and open VS Code Remote-SSH.

Subcommands:
  launch    Create or resume an EC2 instance, open VS Code, watch, then stop.
  stop      Stop the session's EC2 instance (without deleting resources).
  terminate Destroy all resources created by a session.
  list      List EC2 instances tagged as pi-ec2 sessions.

Usage:
  python ec2_vscode.py launch    --profile PROFILE --region REGION \
                                  --session-name NAME --instance-type TYPE \
                                  --ami AMI-ID [--workspace DIR] [--user USER] \
                                  [--poll-interval SECONDS]
  python ec2_vscode.py stop      --profile PROFILE --region REGION \
                                  --session-name NAME
  python ec2_vscode.py terminate --profile PROFILE --region REGION \
                                  --session-name NAME
  python ec2_vscode.py list      --profile PROFILE --region REGION
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.exceptions import ClientError, WaiterError
except ImportError:
    sys.exit("boto3 is required: pip install boto3")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSION_DIR = Path.home() / ".pi-ec2-sessions"
SSH_CONFIG = Path.home() / ".ssh" / "config"
SSH_KEY_DIR = Path.home() / ".ssh"
TAG_KEY = "pi-ec2-session"
SESSION_START_TIMEOUT = 120  # seconds to wait for instance to reach running
STATUS_CHECK_TIMEOUT = 300   # seconds to wait for 2/2 status checks
SG_DELETE_RETRIES = 12
SG_DELETE_WAIT = 10          # seconds between SG delete retries
VSCODE_STARTUP_TIMEOUT = 600  # seconds to wait for vscode-server to appear
MAX_SSH_TRANSIENT_FAILURES = 3  # consecutive SSH failures before treating as gone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def die(msg: str) -> None:
    print(f"[ec2-vscode] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"[ec2-vscode] {msg}")


def ec2_client(profile: str, region: str):
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("ec2")


def load_session_meta(session_name: str) -> Optional[dict]:
    path = SESSION_DIR / f"{session_name}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_session_meta(session_name: str, meta: dict) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSION_DIR / f"{session_name}.json"
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)
    info(f"Session metadata saved to {path}")


def delete_session_meta(session_name: str) -> None:
    path = SESSION_DIR / f"{session_name}.json"
    if path.exists():
        path.unlink()
        info(f"Removed session metadata: {path}")


def key_path(session_name: str) -> Path:
    return SSH_KEY_DIR / f"pi-ec2-{session_name}.pem"


def ssh_host_alias(session_name: str) -> str:
    return f"pi-ec2-{session_name}"


# ---------------------------------------------------------------------------
# SSH config management
# ---------------------------------------------------------------------------


def _block_pattern(session_name: str) -> re.Pattern:
    name = re.escape(session_name)
    return re.compile(
        rf"# BEGIN pi-ec2-{name}\n.*?# END pi-ec2-{name}(?:\n|$)",
        re.DOTALL,
    )


def write_ssh_config_entry(session_name: str, hostname: str, user: str, pem: Path) -> None:
    """Insert or replace an SSH config block for this session."""
    block = (
        f"\n# BEGIN pi-ec2-{session_name}\n"
        f"Host {ssh_host_alias(session_name)}\n"
        f"  HostName {hostname}\n"
        f"  User {user}\n"
        f"  IdentityFile {pem}\n"
        f"  StrictHostKeyChecking accept-new\n"
        f"  ServerAliveInterval 30\n"
        f"# END pi-ec2-{session_name}\n"
    )
    SSH_CONFIG.touch(mode=0o600, exist_ok=True)
    existing = SSH_CONFIG.read_text()
    pattern = _block_pattern(session_name)
    if pattern.search(existing):
        new_content = pattern.sub(block, existing)
    else:
        new_content = existing.rstrip("\n") + block
    SSH_CONFIG.write_text(new_content)
    info(f"SSH config updated: Host {ssh_host_alias(session_name)} → {hostname}")


def remove_ssh_config_entry(session_name: str) -> None:
    if not SSH_CONFIG.exists():
        return
    existing = SSH_CONFIG.read_text()
    pattern = _block_pattern(session_name)
    new_content = pattern.sub("", existing)
    if new_content != existing:
        SSH_CONFIG.write_text(new_content)
        info(f"Removed SSH config entry for {ssh_host_alias(session_name)}")


def remove_known_hosts_entry(session_name: str) -> None:
    """Remove stale known-hosts entry so re-connects don't fail."""
    alias = ssh_host_alias(session_name)
    subprocess.run(
        ["ssh-keygen", "-R", alias],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# EC2 helpers
# ---------------------------------------------------------------------------

def find_existing_instance(ec2, session_name: str) -> Optional[dict]:
    """Return the first non-terminated instance tagged with this session name."""
    resp = ec2.describe_instances(
        Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [session_name]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )
    for reservation in resp["Reservations"]:
        for inst in reservation["Instances"]:
            return inst
    return None


def wait_for_running(ec2, instance_id: str) -> None:
    info(f"Waiting for {instance_id} to reach 'running' state …")
    waiter = ec2.get_waiter("instance_running")
    try:
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 10, "MaxAttempts": SESSION_START_TIMEOUT // 10},
        )
    except WaiterError as exc:
        die(f"Instance did not reach running state: {exc}")
    info(f"{instance_id} is running.")


def wait_for_status_checks(ec2, instance_id: str) -> None:
    info(f"Waiting for status checks on {instance_id} …")
    waiter = ec2.get_waiter("instance_status_ok")
    try:
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": STATUS_CHECK_TIMEOUT // 15},
        )
    except WaiterError as exc:
        die(f"Status checks did not pass: {exc}")
    info("Status checks passed.")


def get_instance_public_dns(ec2, instance_id: str) -> str:
    resp = ec2.describe_instances(InstanceIds=[instance_id])
    inst = resp["Reservations"][0]["Instances"][0]
    dns = inst.get("PublicDnsName") or inst.get("PublicIpAddress") or ""
    if not dns:
        die(f"Instance {instance_id} has no public DNS or IP — ensure it's in a public subnet")
    return dns


def create_key_pair(ec2, session_name: str) -> Path:
    pem = key_path(session_name)
    if pem.exists():
        info(f"Using existing key pair file: {pem}")
        return pem
    kp_name = f"pi-ec2-{session_name}"
    info(f"Creating key pair '{kp_name}' …")
    try:
        resp = ec2.create_key_pair(KeyName=kp_name, KeyType="rsa", KeyFormat="pem")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "InvalidKeyPair.Duplicate":
            info(f"Key pair '{kp_name}' already exists in AWS; local .pem missing — re-create")
            ec2.delete_key_pair(KeyName=kp_name)
            resp = ec2.create_key_pair(KeyName=kp_name, KeyType="rsa", KeyFormat="pem")
        else:
            die(f"Failed to create key pair: {exc}")
    pem.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(pem), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(resp["KeyMaterial"])
    info(f"Key pair saved to {pem}")
    return pem


def create_security_group(ec2, session_name: str, vpc_id: Optional[str] = None) -> str:
    sg_name = f"pi-ec2-{session_name}-sg"
    # Check for existing SG with this name
    filters = [{"Name": "group-name", "Values": [sg_name]}]
    if vpc_id:
        filters.append({"Name": "vpc-id", "Values": [vpc_id]})
    resp = ec2.describe_security_groups(Filters=filters)
    if resp["SecurityGroups"]:
        sg_id = resp["SecurityGroups"][0]["GroupId"]
        info(f"Reusing existing security group {sg_id} ({sg_name})")
        return sg_id

    info(f"Creating security group '{sg_name}' (SSH open to 0.0.0.0/0) …")
    kwargs: dict = {
        "GroupName": sg_name,
        "Description": f"SSH-only access for pi-ec2 session {session_name}",
        "TagSpecifications": [
            {
                "ResourceType": "security-group",
                "Tags": [
                    {"Key": TAG_KEY, "Value": session_name},
                    {"Key": "Name", "Value": sg_name},
                ],
            }
        ],
    }
    if vpc_id:
        kwargs["VpcId"] = vpc_id
    resp = ec2.create_security_group(**kwargs)
    sg_id = resp["GroupId"]
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0", "Description": "pi-ec2 SSH access"}],
            }
        ],
    )
    info(f"Security group created: {sg_id}")
    return sg_id


def launch_instance(
    ec2,
    session_name: str,
    instance_type: str,
    ami_id: str,
    sg_id: str,
    key_name: str,
    iam_instance_profile: Optional[str] = None,
) -> str:
    info(f"Launching EC2 instance (type={instance_type}, ami={ami_id}) …")
    run_kwargs: dict = dict(
        ImageId=ami_id,
        InstanceType=instance_type,
        KeyName=key_name,
        NetworkInterfaces=[
            {
                "DeviceIndex": 0,
                "AssociatePublicIpAddress": True,
                "Groups": [sg_id],
            }
        ],
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": TAG_KEY, "Value": session_name},
                    {"Key": "Name", "Value": f"pi-ec2-{session_name}"},
                ],
            }
        ],
    )
    if iam_instance_profile:
        run_kwargs["IamInstanceProfile"] = {"Name": iam_instance_profile}
    resp = ec2.run_instances(**run_kwargs)
    instance_id = resp["Instances"][0]["InstanceId"]
    info(f"Instance launched: {instance_id}")
    return instance_id


# ---------------------------------------------------------------------------
# IAM helpers
# ---------------------------------------------------------------------------


def create_iam_resources(iam, session_name: str) -> tuple:
    """
    Create IAM role + instance profile for the session.
    Returns (role_name, profile_name).
    EntityAlreadyExists errors are treated as already-created (idempotent).
    """
    role_name = f"pi-ec2-{session_name}-role"
    profile_name = f"pi-ec2-{session_name}-profile"

    trust_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    })

    # 1. Create role
    try:
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=trust_policy,
            Description=f"IAM role for pi-ec2 session {session_name}",
        )
        info(f"IAM role created: {role_name}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "EntityAlreadyExists":
            info(f"IAM role {role_name} already exists — reusing.")
        else:
            info(f"Warning: could not create IAM role (non-fatal): {exc}")
            return role_name, profile_name

    # 2. Attach Bedrock managed policy
    try:
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
        )
        info(f"Attached AmazonBedrockFullAccess to {role_name}")
    except ClientError as exc:
        info(f"Warning: could not attach Bedrock policy (non-fatal): {exc}")

    # 3. Create instance profile
    try:
        iam.create_instance_profile(InstanceProfileName=profile_name)
        info(f"IAM instance profile created: {profile_name}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "EntityAlreadyExists":
            info(f"IAM instance profile {profile_name} already exists — reusing.")
        else:
            info(f"Warning: could not create instance profile (non-fatal): {exc}")
            return role_name, profile_name

    # 4. Add role to instance profile
    try:
        iam.add_role_to_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name,
        )
        info(f"Added role {role_name} to instance profile {profile_name}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "LimitExceeded":
            info(f"Instance profile {profile_name} already has a role — skipping.")
        elif code == "EntityAlreadyExists":
            info(f"Role already in instance profile — skipping.")
        else:
            info(f"Warning: could not add role to instance profile (non-fatal): {exc}")

    # 5. Wait for IAM propagation
    info("Waiting 10s for IAM propagation before launching instance…")
    time.sleep(10)

    return role_name, profile_name


def cleanup_iam_resources(iam, role_name: str, profile_name: str) -> None:
    """
    Clean up IAM role + instance profile created by a session.
    Cleanup order matters: remove role from profile → delete profile →
    detach policies → delete role.
    NoSuchEntity errors are silently ignored.
    """
    # 1. Remove role from instance profile
    try:
        iam.remove_role_from_instance_profile(
            InstanceProfileName=profile_name,
            RoleName=role_name,
        )
        info(f"Removed role {role_name} from instance profile {profile_name}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchEntity", "NoSuchEntityException"):
            info(f"Role/profile not found during cleanup — skipping remove step.")
        else:
            info(f"Warning: could not remove role from instance profile: {exc}")

    # 2. Delete instance profile
    try:
        iam.delete_instance_profile(InstanceProfileName=profile_name)
        info(f"Deleted instance profile {profile_name}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchEntity", "NoSuchEntityException"):
            info(f"Instance profile {profile_name} not found (already deleted).")
        else:
            info(f"Warning: could not delete instance profile: {exc}")

    # 3. Detach all managed policies from role
    try:
        paginator = iam.get_paginator("list_attached_role_policies")
        for page in paginator.paginate(RoleName=role_name):
            for policy in page["AttachedPolicies"]:
                iam.detach_role_policy(RoleName=role_name, PolicyArn=policy["PolicyArn"])
                info(f"Detached policy {policy['PolicyArn']} from {role_name}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchEntity", "NoSuchEntityException"):
            info(f"Role {role_name} not found during policy detach — skipping.")
        else:
            info(f"Warning: could not detach policies from role: {exc}")

    # 4. Delete the role
    try:
        iam.delete_role(RoleName=role_name)
        info(f"Deleted IAM role {role_name}")
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("NoSuchEntity", "NoSuchEntityException"):
            info(f"IAM role {role_name} not found (already deleted).")
        else:
            info(f"Warning: could not delete IAM role: {exc}")


# ---------------------------------------------------------------------------
# Post-launch setup
# ---------------------------------------------------------------------------


def post_launch_setup(hostname: str, user: str, pem: Path, region: str = "") -> None:
    """
    Run post-launch configuration on the remote instance:
    a) Install Claude Code CLI via nvm + node
    b) Add anthropic.claude-code to local VS Code remote.SSH.defaultExtensions
    c) Write remote VS Code Machine settings.json for Bedrock
    """
    # ------------------------------------------------------------------
    # a) Install Claude Code CLI on remote
    # ------------------------------------------------------------------
    info("Installing Claude Code CLI on remote instance…")
    install_claude_cmd = (
        "curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && "
        'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
        "nvm install --lts && "
        "npm install -g @anthropic-ai/claude-code"
    )
    result = _ssh_exec(hostname, user, pem, install_claude_cmd, connect_timeout=30)
    if result.returncode != 0:
        info(f"Warning: Claude Code CLI install failed (non-fatal): {result.stderr.strip()}")
    else:
        info("Claude Code CLI installed.")

    # ------------------------------------------------------------------
    # b) Add anthropic.claude-code to local VS Code remote.SSH.defaultExtensions
    # ------------------------------------------------------------------
    info("Updating local VS Code remote.SSH.defaultExtensions…")
    vscode_settings_path = (
        Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    )
    try:
        ext_id = "anthropic.claude-code"
        settings: dict = {}
        if vscode_settings_path.exists():
            content = vscode_settings_path.read_text().strip()
            if content:
                settings = json.loads(content)
        current_exts: list = settings.get("remote.SSH.defaultExtensions", [])
        if ext_id not in current_exts:
            current_exts.append(ext_id)
            settings["remote.SSH.defaultExtensions"] = current_exts
            vscode_settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(vscode_settings_path, "w") as f:
                json.dump(settings, f, indent=2)
            info(f"Added {ext_id} to remote.SSH.defaultExtensions.")
        else:
            info(f"{ext_id} already in remote.SSH.defaultExtensions.")
    except Exception as exc:
        info(f"Warning: could not update local VS Code settings (non-fatal): {exc}")

    # ------------------------------------------------------------------
    # c) Write remote VS Code Machine settings for Bedrock
    # ------------------------------------------------------------------
    info("Writing remote VS Code Machine settings (Bedrock config)…")
    env_vars = [
        {"name": "CLAUDE_CODE_USE_BEDROCK", "value": "1"},
    ]
    if region:
        env_vars.append({"name": "AWS_REGION", "value": region})
    env_vars += [
        {"name": "CLAUDE_CODE_ENABLE_TELEMETRY", "value": "0"},
        {"name": "DISABLE_ERROR_REPORTING", "value": "1"},
        {"name": "DISABLE_TELEMETRY", "value": "1"},
        {"name": "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "value": "1"},
    ]
    machine_settings = {
        "claudeCode.environmentVariables": env_vars,
        "claudeCode.initialPermissionMode": "plan",
        "claudeCode.preferredLocation": "panel",
        "claudeCode.selectedModel": "opusplan",
        "claudeCode.allowDangerouslySkipPermissions": True,
        "claudeCode.disableLoginPrompt": True,
    }
    machine_settings_b64 = base64.b64encode(
        json.dumps(machine_settings, indent=2).encode()
    ).decode()
    remote_cmd = (
        "mkdir -p ~/.vscode-server/data/Machine && "
        f"echo '{machine_settings_b64}' | base64 -d > ~/.vscode-server/data/Machine/settings.json"
    )
    result = _ssh_exec(hostname, user, pem, remote_cmd, connect_timeout=10)
    if result.returncode != 0:
        info(
            f"Warning: could not write remote VS Code Machine settings (non-fatal): "
            f"{result.stderr.strip()}"
        )
    else:
        info("Remote VS Code Machine settings written.")


# ---------------------------------------------------------------------------
# VS Code lifecycle watch
# ---------------------------------------------------------------------------

def open_vscode(session_name: str, workspace: str) -> None:
    alias = ssh_host_alias(session_name)
    cmd = ["code", "--remote", f"ssh-remote+{alias}", workspace]
    info(f"Opening VS Code: {' '.join(cmd)}")
    try:
        subprocess.Popen(cmd)
    except FileNotFoundError:
        die(
            "VS Code 'code' command not found on PATH. "
            "Install it via VS Code \u2192 Command Palette \u2192 "
            "\"Shell Command: Install 'code' command in PATH\""
        )


def _ssh_exec(
    hostname: str,
    user: str,
    pem: Path,
    cmd: str,
    connect_timeout: int = 10,
) -> subprocess.CompletedProcess:
    """Run a command on the remote host via SSH. Returns CompletedProcess."""
    return subprocess.run(
        [
            "ssh", "-q",
            "-i", str(pem),
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"ConnectTimeout={connect_timeout}",
            "-o", "BatchMode=yes",
            f"{user}@{hostname}",
            cmd,
        ],
        capture_output=True,
        text=True,
    )


def _is_transient_ssh_failure(result: subprocess.CompletedProcess) -> bool:
    """Return True when SSH failed due to a transient connectivity issue."""
    if result.returncode == 0:
        return False
    err = result.stderr.lower()
    return any(
        m in err
        for m in (
            "connection refused",
            "network unreachable",
            "no route to host",
            "ssh: connect to host",
        )
    )


def watch_vscode_and_stop(
    hostname: str,
    user: str,
    pem: Path,
    poll_interval: int,
    startup_grace: int,
    ec2,
    instance_id: str,
) -> None:
    """
    Two-phase VS Code lifecycle watch, then stop the instance.

    Phase 1 — startup detection:
        Poll every poll_interval seconds until a 'vscode-server' process appears
        on the remote host (confirms VS Code successfully connected).
        Waits up to VSCODE_STARTUP_TIMEOUT seconds (10 min).
        An optional startup_grace delay is applied first so VS Code has time
        to begin the initial SSH handshake before the first poll.

    Phase 2 — disconnect detection:
        Once vscode-server is confirmed running, switch to counting active
        TCP connections associated with the process:
            ss -tnp | grep 'vscode-server' | wc -l
        When the count drops to 0, the client has disconnected.

    SSH transient failures (connection refused, network unreachable, etc.) are
    tolerated up to MAX_SSH_TRANSIENT_FAILURES consecutive times before treating
    the session as ended.
    """
    # Optional startup grace period so VS Code has time to begin connecting
    if startup_grace > 0:
        info(f"Waiting {startup_grace}s startup grace before polling …")
        time.sleep(startup_grace)

    # ------------------------------------------------------------------
    # Phase 1: wait for vscode-server process to appear
    # ------------------------------------------------------------------
    info(
        f"Phase 1: waiting for vscode-server to start on {hostname} "
        f"(timeout {VSCODE_STARTUP_TIMEOUT}s, poll every {poll_interval}s) …"
    )
    deadline = time.monotonic() + VSCODE_STARTUP_TIMEOUT
    server_seen = False
    while time.monotonic() < deadline:
        result = _ssh_exec(hostname, user, pem, "ps aux | grep '[v]scode-server'")
        if result.returncode == 0 and result.stdout.strip():
            info("vscode-server detected — VS Code is connected.")
            server_seen = True
            break
        if _is_transient_ssh_failure(result):
            info("Transient SSH failure during startup phase, retrying …")
        else:
            info("vscode-server not yet visible, waiting …")
        time.sleep(poll_interval)

    if server_seen:
        connect_grace = 60
        info(f"Waiting {connect_grace}s for VS Code client to fully establish connection …")
        time.sleep(connect_grace)

    if not server_seen:
        info(
            f"Warning: vscode-server was not detected within {VSCODE_STARTUP_TIMEOUT}s. "
            "Proceeding to disconnect monitoring anyway."
        )

    # ------------------------------------------------------------------
    # Phase 2: count active VS Code client connections
    # ------------------------------------------------------------------
    info(
        "Phase 2: monitoring active VS Code client connections. "
        "Close VS Code to auto-stop the instance."
    )
    consecutive_transient = 0
    consecutive_zero = 0
    ZERO_THRESHOLD = 3  # ~45s with 15s poll interval
    while True:
        # wc -l always succeeds (returns 0 even with empty input), so a
        # non-zero returncode here reliably means the SSH connection itself
        # failed rather than "no connections found".
        # Use sudo so ss can show process names (-p flag) on Ubuntu.
        result = _ssh_exec(
            hostname, user, pem,
            "sudo ss -tnp 2>/dev/null | grep 'vscode-server' | wc -l",
        )
        if result.returncode != 0 or _is_transient_ssh_failure(result):
            consecutive_transient += 1
            info(
                f"Transient SSH failure "
                f"({consecutive_transient}/{MAX_SSH_TRANSIENT_FAILURES}) — retrying …"
            )
            if consecutive_transient >= MAX_SSH_TRANSIENT_FAILURES:
                info(
                    "Too many consecutive SSH failures; "
                    "treating VS Code session as ended."
                )
                break
        else:
            consecutive_transient = 0
            try:
                conn_count = int(result.stdout.strip())
            except ValueError:
                conn_count = 0
            if conn_count == 0:
                consecutive_zero += 1
                if consecutive_zero >= ZERO_THRESHOLD:
                    info("VS Code connection closed — stopping instance.")
                    break
                else:
                    info(
                        f"Zero connections ({consecutive_zero}/{ZERO_THRESHOLD}), "
                        "waiting to confirm…"
                    )
            else:
                consecutive_zero = 0
                info(f"Active VS Code connections: {conn_count} — still running.")
        time.sleep(poll_interval)

    # Auto-stop
    stop_instance(ec2, instance_id)
    info("Session complete.")


def stop_instance(ec2, instance_id: str) -> None:
    info(f"Stopping instance {instance_id} …")
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
        waiter = ec2.get_waiter("instance_stopped")
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 10, "MaxAttempts": 30},
        )
        info(f"Instance {instance_id} stopped.")
    except (ClientError, WaiterError) as exc:
        info(f"Warning: could not confirm instance stopped: {exc}")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_launch(args: argparse.Namespace) -> None:
    session_name: str = args.session_name
    profile: str = args.profile
    region: str = args.region
    workspace: str = args.workspace
    user: str = args.user
    poll_interval: int = args.poll_interval

    ec2 = ec2_client(profile, region)
    meta = load_session_meta(session_name)
    instance_id: Optional[str] = None
    pem: Optional[Path] = None
    sg_id: Optional[str] = None
    iam_role_name: Optional[str] = None
    iam_profile_name: Optional[str] = None

    existing = find_existing_instance(ec2, session_name)

    if existing:
        instance_id = existing["InstanceId"]
        state = existing["State"]["Name"]
        info(f"Found existing instance {instance_id} in state '{state}'")

        if meta:
            pem = Path(meta["key_path"])
            sg_id = meta.get("sg_id")
        else:
            # Reconstruct key path from convention
            pem = key_path(session_name)
            if not pem.exists():
                die(
                    f"Existing instance found but no local key file at {pem}. "
                    "Run terminate and relaunch to recreate resources."
                )

        if state == "stopped":
            info(f"Starting stopped instance {instance_id} …")
            ec2.start_instances(InstanceIds=[instance_id])
            wait_for_running(ec2, instance_id)
            wait_for_status_checks(ec2, instance_id)
        elif state in ("pending", "running"):
            info(f"Instance is already {state}.")
            if state == "pending":
                wait_for_running(ec2, instance_id)
                wait_for_status_checks(ec2, instance_id)
        else:
            die(f"Instance is in state '{state}' — cannot resume. Run terminate first.")
    else:
        # New session
        if not args.instance_type or not args.ami:
            die("--instance-type and --ami are required when creating a new instance")

        try:
            pem = create_key_pair(ec2, session_name)
            sg_id = create_security_group(ec2, session_name)
            # Create IAM role + instance profile so Claude Code can use Bedrock
            iam = boto3.Session(profile_name=profile).client("iam")
            iam_role_name, iam_profile_name = create_iam_resources(iam, session_name)
            kp_name = f"pi-ec2-{session_name}"
            instance_id = launch_instance(
                ec2, session_name, args.instance_type, args.ami, sg_id, kp_name,
                iam_instance_profile=iam_profile_name,
            )
            wait_for_running(ec2, instance_id)
            wait_for_status_checks(ec2, instance_id)
        except Exception as exc:
            print(
                f"[ec2-vscode] Launch failed: {exc}\n"
                "[ec2-vscode] Cleaning up partial resources — run:\n"
                f"  python3 ${{SKILL_DIR}}/scripts/ec2_vscode.py terminate "
                f"--session-name {session_name} --profile {profile} --region {region}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Retrieve public DNS
    hostname = get_instance_public_dns(ec2, instance_id)
    info(f"Instance public DNS: {hostname}")

    # Persist metadata
    meta_to_save: dict = {
        "instance_id": instance_id,
        "key_path": str(pem),
        "sg_id": sg_id,
        "profile": profile,
        "region": region,
        "user": user,
    }
    if iam_role_name:
        meta_to_save["iam_role_name"] = iam_role_name
    if iam_profile_name:
        meta_to_save["iam_profile_name"] = iam_profile_name
    save_session_meta(session_name, meta_to_save)

    # Remove stale known-hosts entry (different host key after stop/start)
    remove_known_hosts_entry(session_name)

    # Update SSH config
    write_ssh_config_entry(session_name, hostname, user, pem)

    # Post-launch setup: install Claude Code CLI, configure Bedrock, etc.
    if not args.skip_setup:
        post_launch_setup(hostname, user, pem, region=region)

    # Open VS Code
    open_vscode(session_name, workspace)

    # Watch for VS Code client disconnect (two-phase), then auto-stop
    watch_vscode_and_stop(
        hostname, user, pem, poll_interval, args.startup_grace, ec2, instance_id
    )


def cmd_terminate(args: argparse.Namespace) -> None:
    session_name: str = args.session_name
    profile: str = args.profile
    region: str = args.region

    ec2 = ec2_client(profile, region)
    meta = load_session_meta(session_name)

    # Gather IDs from metadata and/or AWS tags
    instance_id: Optional[str] = meta.get("instance_id") if meta else None
    sg_id: Optional[str] = meta.get("sg_id") if meta else None
    pem: Path = Path(meta["key_path"]) if meta and "key_path" in meta else key_path(session_name)
    kp_name = f"pi-ec2-{session_name}"

    # If no metadata, try to find resources by tag
    if not instance_id:
        existing = find_existing_instance(ec2, session_name)
        if existing:
            instance_id = existing["InstanceId"]
            info(f"Found instance by tag: {instance_id}")

    # Terminate instance
    if instance_id:
        state = _get_instance_state(ec2, instance_id)
        if state and state != "terminated":
            info(f"Terminating instance {instance_id} …")
            try:
                ec2.terminate_instances(InstanceIds=[instance_id])
                waiter = ec2.get_waiter("instance_terminated")
                waiter.wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={"Delay": 10, "MaxAttempts": 30},
                )
                info(f"Instance {instance_id} terminated.")
            except (ClientError, WaiterError) as exc:
                info(f"Warning: termination issue: {exc}")
        else:
            info(f"Instance {instance_id} is already terminated or not found.")
    else:
        info("No instance found to terminate.")

    # Delete AWS key pair
    info(f"Deleting key pair '{kp_name}' …")
    try:
        ec2.delete_key_pair(KeyName=kp_name)
        info(f"Key pair '{kp_name}' deleted.")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "InvalidKeyPair.NotFound":
            info(f"Key pair '{kp_name}' not found (already deleted).")
        else:
            info(f"Warning: could not delete key pair: {exc}")

    # Remove local .pem
    if pem.exists():
        pem.unlink()
        info(f"Removed local key file: {pem}")

    # Delete security group (with retry)
    if not sg_id:
        sg_name = f"pi-ec2-{session_name}-sg"
        resp = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [sg_name]}])
        if resp["SecurityGroups"]:
            sg_id = resp["SecurityGroups"][0]["GroupId"]
    if sg_id:
        _delete_security_group(ec2, sg_id)
    else:
        info("No security group found to delete.")

    # Clean up IAM role + instance profile (if created by this session)
    iam_role_name: Optional[str] = meta.get("iam_role_name") if meta else None
    iam_profile_name: Optional[str] = meta.get("iam_profile_name") if meta else None
    if iam_role_name and iam_profile_name:
        info(f"Cleaning up IAM resources: role={iam_role_name}, profile={iam_profile_name}")
        iam = boto3.Session(profile_name=profile).client("iam")
        cleanup_iam_resources(iam, iam_role_name, iam_profile_name)
    else:
        info("No IAM resources in session metadata — skipping IAM cleanup.")

    # Remove SSH config entry
    remove_ssh_config_entry(session_name)
    remove_known_hosts_entry(session_name)

    # Remove metadata file
    delete_session_meta(session_name)

    info(f"Session '{session_name}' terminated and all resources removed.")


def _get_instance_state(ec2, instance_id: str) -> Optional[str]:
    try:
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        instances = [
            i for r in resp["Reservations"] for i in r["Instances"]
        ]
        if instances:
            return instances[0]["State"]["Name"]
    except ClientError:
        pass
    return None


def _delete_security_group(ec2, sg_id: str) -> None:
    info(f"Deleting security group {sg_id} …")
    for attempt in range(1, SG_DELETE_RETRIES + 1):
        try:
            ec2.delete_security_group(GroupId=sg_id)
            info(f"Security group {sg_id} deleted.")
            return
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "InvalidGroup.NotFound":
                info(f"Security group {sg_id} not found (already deleted).")
                return
            elif code == "DependencyViolation":
                info(
                    f"SG still has dependencies (attempt {attempt}/{SG_DELETE_RETRIES}). "
                    f"Retrying in {SG_DELETE_WAIT}s …"
                )
                time.sleep(SG_DELETE_WAIT)
            else:
                info(f"Warning: could not delete security group: {exc}")
                return
    info(f"Warning: could not delete security group {sg_id} after {SG_DELETE_RETRIES} attempts.")


def cmd_stop(args: argparse.Namespace) -> None:
    session_name: str = args.session_name
    profile: str = args.profile
    region: str = args.region

    meta = load_session_meta(session_name)
    if not meta:
        die(
            f"No session state file found for '{session_name}'. "
            "Is the session name correct?"
        )

    instance_id: str = meta["instance_id"]
    ec2 = ec2_client(profile, region)

    state = _get_instance_state(ec2, instance_id)
    if state == "stopped":
        info(f"Instance {instance_id} is already stopped.")
        sys.exit(0)
    if state == "terminated":
        die(
            f"Instance {instance_id} is already terminated. "
            "Run 'terminate' to clean up remaining resources "
            "(key pair, security group, SSH config)."
        )

    info(f"Stopping instance {instance_id} …")
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
    except ClientError as exc:
        die(f"Failed to stop instance: {exc}")

    # Poll every 5 s, timeout 5 min
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        state = _get_instance_state(ec2, instance_id)
        if state == "stopped":
            info(
                f"Instance {instance_id} stopped. "
                f"Resume with: launch --session-name {session_name} ..."
            )
            sys.exit(0)
        info(f"Instance state: {state} — waiting …")
        time.sleep(5)

    die(f"Instance {instance_id} did not reach 'stopped' state within 5 minutes.")


def cmd_list(args: argparse.Namespace) -> None:
    ec2 = ec2_client(args.profile, args.region)
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "tag-key", "Values": [TAG_KEY]},
            {
                "Name": "instance-state-name",
                "Values": ["pending", "running", "stopping", "stopped", "terminated"],
            },
        ]
    )

    rows = []
    for reservation in resp["Reservations"]:
        for inst in reservation["Instances"]:
            tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
            session = tags.get(TAG_KEY, "-")
            state = inst["State"]["Name"]
            itype = inst.get("InstanceType", "-")
            dns = inst.get("PublicDnsName") or inst.get("PublicIpAddress") or "-"
            iid = inst["InstanceId"]
            rows.append((session, iid, state, itype, dns))

    if not rows:
        info(f"No pi-ec2 sessions found in {args.region}.")
        return

    rows.sort(key=lambda r: r[0])
    header = f"{'SESSION':<20} {'INSTANCE-ID':<22} {'STATE':<12} {'TYPE':<14} PUBLIC-DNS"
    print(header)
    print("-" * len(header))
    for session, iid, state, itype, dns in rows:
        print(f"{session:<20} {iid:<22} {state:<12} {itype:<14} {dns}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage EC2 instances for VS Code Remote-SSH sessions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- launch ---
    p_launch = sub.add_parser("launch", help="Launch or resume a session")
    p_launch.add_argument("--profile", required=True, help="AWS profile name")
    p_launch.add_argument("--region", required=True, help="AWS region")
    p_launch.add_argument("--session-name", required=True, help="Logical session name")
    p_launch.add_argument("--instance-type", default=None,
                          help="EC2 instance type (required for new instances)")
    p_launch.add_argument("--ami", default=None,
                          help="AMI ID (required for new instances)")
    p_launch.add_argument("--workspace", default="/home/ec2-user",
                          help="Remote workspace directory (default: /home/ec2-user)")
    p_launch.add_argument("--user", default="ec2-user",
                          help="SSH username (default: ec2-user)")
    p_launch.add_argument("--poll-interval", type=int, default=15,
                          help="Seconds between VS Code server polls (default: 15)")
    p_launch.add_argument("--startup-grace", type=int, default=30,
                          help="Seconds to wait before first poll (default: 30)")
    p_launch.add_argument("--skip-setup", action="store_true", default=False,
                          help="Skip post-launch setup (Claude Code CLI, VS Code extension, Bedrock config)")

    # --- stop ---
    p_stop = sub.add_parser("stop", help="Stop a session's EC2 instance without deleting resources")
    p_stop.add_argument("--profile", required=True, help="AWS profile name")
    p_stop.add_argument("--region", required=True, help="AWS region")
    p_stop.add_argument("--session-name", required=True, help="Session name to stop")

    # --- terminate ---
    p_terminate = sub.add_parser("terminate", help="Destroy all resources for a session")
    p_terminate.add_argument("--profile", required=True, help="AWS profile name")
    p_terminate.add_argument("--region", required=True, help="AWS region")
    p_terminate.add_argument("--session-name", required=True, help="Session name to terminate and clean up")

    # --- list ---
    p_list = sub.add_parser("list", help="List all pi-ec2 sessions in a region")
    p_list.add_argument("--profile", required=True, help="AWS profile name")
    p_list.add_argument("--region", required=True, help="AWS region")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "launch":
        cmd_launch(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "terminate":
        cmd_terminate(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
