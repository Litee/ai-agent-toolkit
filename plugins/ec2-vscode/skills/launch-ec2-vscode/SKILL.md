---
name: launch-ec2-vscode
description: 'Use when spinning up an EC2 instance for remote development with VS Code, launching a cloud workstation, doing remote dev on EC2, starting a cloud dev machine, resuming an EC2 session, stopping an EC2 session, terminating an EC2 session, listing EC2 dev sessions, EC2 VS Code remote, launch EC2 with VS Code, spin up EC2, cloud workstation, remote development EC2, ec2 vscode remote, start remote dev environment. Manages the full lifecycle: create or resume a stopped instance, configure SSH, open VS Code Remote-SSH, watch for VS Code close, then auto-stop the instance. The terminate command destroys instance + key pair + security group + SSH config entry.'
---

# Launch EC2 VS Code — Remote Development Skill

## Purpose

Spin up (or resume) an EC2 instance, open VS Code in Remote-SSH mode, watch for VS Code to close, then automatically stop the instance. A separate `terminate` command destroys everything the skill created.

## Prerequisites

- Python 3.8+ and `boto3` installed (`pip install boto3`)
- VS Code with the **Remote - SSH** extension installed
- AWS credentials configured in `~/.aws/config` or via environment variables; verify with `aws sts get-caller-identity --profile <profile>` before running
- SSH client on `PATH`
- The script: `${SKILL_DIR}/scripts/ec2_vscode.py`

## Quick Reference

```bash
# Launch (or resume) a session
python3 ${SKILL_DIR}/scripts/ec2_vscode.py launch \
  --profile <aws-profile> \
  --region <region> \
  --session-name <name> \
  --instance-type t3.medium \
  --ami <ami-id> \
  [--workspace /home/ec2-user/my-project]

# Stop an instance (without destroying resources)
python3 ${SKILL_DIR}/scripts/ec2_vscode.py stop \
  --profile <aws-profile> \
  --region <region> \
  --session-name <name>

# Terminate everything created by a session
python3 ${SKILL_DIR}/scripts/ec2_vscode.py terminate \
  --profile <aws-profile> \
  --region <region> \
  --session-name <name>

# List all sessions in a region
python3 ${SKILL_DIR}/scripts/ec2_vscode.py list \
  --profile <aws-profile> \
  --region <region>
```

---

## Workflow: Launching a Session

1. **Run `launch`** — the script:
   1. Checks `~/.pi-ec2-sessions/<session-name>.json` for an existing session record
   2. If a stopped instance is found with the `pi-ec2-session` tag matching `<session-name>`, starts it
   3. Otherwise creates fresh resources: key pair → security group → EC2 instance
   4. Waits for the instance to reach `running` state and pass both status checks
   5. Writes `~/.ssh/config` entry `Host pi-ec2-<session-name>` with the instance's public DNS, key, and remote user
   6. **Post-launch setup** (unless `--skip-setup` is passed):
      - Creates a dedicated IAM role `pi-ec2-<session-name>-role` with EC2 trust policy and `AmazonBedrockFullAccess`, plus a matching instance profile. This lets Claude Code authenticate to Bedrock via the instance profile — no AWS credentials on disk.
      - Installs `nvm`, Node.js LTS, and the `@anthropic-ai/claude-code` npm package on the remote instance
      - Adds `anthropic.claude-code` to `remote.SSH.defaultExtensions` in the local VS Code `settings.json` so the extension is auto-installed on every remote SSH host
      - Writes `~/.vscode-server/data/Machine/settings.json` on the remote to configure Claude Code for Bedrock (via `CLAUDE_CODE_USE_BEDROCK=1` and `AWS_REGION`; no `AWS_PROFILE` — the instance profile handles auth)
   7. Runs `code --remote ssh-remote+pi-ec2-<session-name> <workspace-dir>`
   8. **Phase 1 — startup detection:** polls `ps aux | grep '[v]scode-server'` on the instance every 15 s via SSH until a vscode-server process appears (confirms VS Code has connected), timing out after 10 minutes.
   9. **Phase 2 — disconnect detection:** once vscode-server is confirmed running, counts active TCP connections associated with the process (`sudo ss -tnp | grep 'vscode-server' | wc -l`) every 15 s (`sudo` is required — without it, Ubuntu's `ss -p` doesn't show process names). Requires **3 consecutive** zero-connection readings before stopping, to avoid false positives from brief VS Code reconnects.
   10. Transient SSH failures (connection refused, network unreachable) are tolerated up to 3 consecutive times before treating the session as ended.

2. **Close VS Code** — the script detects the disconnection within ~15 s and stops the EC2 instance automatically

### Key Pair, Security Group, and IAM Resources

| Resource | Location |
|---|---|
| Key pair PEM | `~/.ssh/pi-ec2-<session-name>.pem` |
| Security group | Named `pi-ec2-<session-name>-sg` |
| IAM role | `pi-ec2-<session-name>-role` (EC2 trust policy + `AmazonBedrockFullAccess`) |
| IAM instance profile | `pi-ec2-<session-name>-profile` |
| SSH config entry | `~/.ssh/config` block `Host pi-ec2-<session-name>` |
| Session metadata | `~/.pi-ec2-sessions/<session-name>.json` (stores instance ID, key path, sg ID, IAM role/profile names) |

The security group allows **SSH (port 22) from `0.0.0.0/0`** (any IP). This is intentional — restricting to a caller IP is unreliable when running from corporate networks where the AWS API egress IP differs from the TCP connection source IP.

---

## Workflow: Resuming a Session

If a session's instance exists in a **stopped** state, `launch` will start it automatically — no new key pair or security group is created. The existing `~/.ssh/config` entry is updated with the new public DNS assigned after start.

If the instance was **terminated** (e.g. AWS reclaimed a Spot instance), run `terminate` first, then `launch` again with the same session name.

---

## Workflow: Stopping a Session

`stop` shuts down the EC2 instance without deleting any resources — key pair, security group, SSH config, and state file all remain intact. Use this to pause work and resume later without the overhead of recreating resources.

**After running `stop`, immediately refresh the EC2 instance watcher** (if one is active) by calling:
```
ec2_instance_watcher({ action: "list" })
```
If no watch exists for this instance yet, add one with `stopOnStopped: true` so the agent is notified when the instance reaches `stopped` state.

```bash
python3 ${SKILL_DIR}/scripts/ec2_vscode.py stop \
  --profile my-profile \
  --region us-east-1 \
  --session-name dev
```

Resume the stopped instance at any time with `launch` (no `--ami` or `--instance-type` needed):

```bash
python3 ${SKILL_DIR}/scripts/ec2_vscode.py launch \
  --profile my-profile \
  --region us-east-1 \
  --session-name dev
```

> **Note:** `stop` is also what the `launch` watcher does automatically when VS Code is closed. Use `stop` explicitly if you want to shut down the instance without opening VS Code first.

> **Note:** If the instance has already been terminated (e.g. by AWS), `stop` will exit with an error and prompt you to run `terminate` to clean up remaining resources.

---

## Workflow: Terminating a Session

`terminate` removes every resource the skill created:

- Terminates the EC2 instance (waits for `terminated` state)
- Deletes the AWS key pair
- Removes `~/.ssh/pi-ec2-<session-name>.pem`
- Deletes the security group (retries until the ENI is released)
- Removes the IAM role and instance profile created for the session (`pi-ec2-<session-name>-role` / `pi-ec2-<session-name>-profile`) — in correct IAM dependency order
- Removes the `Host pi-ec2-<session-name>` block from `~/.ssh/config`
- Removes `~/.pi-ec2-sessions/<session-name>.json`

```bash
python3 ${SKILL_DIR}/scripts/ec2_vscode.py terminate \
  --profile my-profile \
  --region us-east-1 \
  --session-name dev
```

> **Tip:** If a mid-launch failure leaves partial resources (e.g., key pair created but instance launch failed), running `terminate` with the same session name is safe — it skips resources that no longer exist.

---

## Workflow: Listing Sessions

```bash
python3 ${SKILL_DIR}/scripts/ec2_vscode.py list \
  --profile my-profile \
  --region us-east-1
```

Output format:

```
SESSION          INSTANCE-ID          STATE     TYPE        PUBLIC-DNS
dev              i-0abc123def456      running   t3.medium   ec2-1-2-3-4.compute-1.amazonaws.com
staging          i-0def789abc012      stopped   t3.large    -
```

---

## All Flags

### `launch`

| Flag | Required | Description |
|---|---|---|
| `--profile` | ✅ | AWS profile name (ADA/SSO/static) |
| `--region` | ✅ | AWS region, e.g. `us-east-1` |
| `--session-name` | ✅ | Logical name; used as tag and SSH host suffix |
| `--instance-type` | ✅ (new only) | EC2 instance type, e.g. `t3.medium` |
| `--ami` | ✅ (new only) | AMI ID, e.g. `ami-0abcdef1234567890` |
| `--workspace` | ❌ | Remote directory to open (default: `/home/ec2-user`) |
| `--user` | ❌ | SSH username (default: `ec2-user`) |
| `--poll-interval` | ❌ | Seconds between VS Code server polls (default: `15`) |
| `--startup-grace` | ❌ | Seconds to wait before first connection poll (default: `30`) |
| `--skip-setup` | ❌ | Skip post-launch setup (Claude Code CLI, VS Code extension, Bedrock config) |

### `stop`

| Flag | Required | Description |
|---|---|---|
| `--profile` | ✅ | AWS profile name |
| `--region` | ✅ | AWS region |
| `--session-name` | ✅ | Session to stop |

### `terminate`

| Flag | Required | Description |
|---|---|---|
| `--profile` | ✅ | AWS profile name |
| `--region` | ✅ | AWS region |
| `--session-name` | ✅ | Session to terminate and clean up |

### `list`

| Flag | Required | Description |
|---|---|---|
| `--profile` | ✅ | AWS profile name |
| `--region` | ✅ | AWS region |

---

## Gotchas

1. **AWS credentials must be active before running.** If credentials are expired you'll get `AuthFailure` / `ExpiredToken` from boto3. Verify with `aws sts get-caller-identity --profile <profile>` and refresh using your credential provider (SSO, IAM role, etc.) before running.

2. **VS Code detection has a ~15 s lag.** After closing VS Code, wait up to 15 seconds before the instance stops.

3. **`--ami` and `--instance-type` are only used for new instances.** When resuming a stopped instance they are ignored.

4. **Security group deletion may retry.** AWS holds a security group until the ENI (elastic network interface) is released after termination; the script retries up to 12 times with 10 s backoff.

5. **SSH `StrictHostKeyChecking`** is set to `accept-new` in the generated config block. Old known-hosts entries for the same alias will cause conflicts on resume; the script removes them automatically.

6. **Default user is `ec2-user` (Amazon Linux).** For Ubuntu/Debian AMIs, pass `--user ubuntu`. For other AMIs, check the correct SSH username for your AMI vendor.

---

## Error Handling

| Symptom | Cause | Fix |
|---|---|---|
| `AuthFailure` / `ExpiredToken` | Stale credentials | Verify with `aws sts get-caller-identity --profile <profile>` and refresh using your credential provider |
| `SSH: Connection refused` on first connect | Instance not ready | Wait ~30 s; status checks can pass before `sshd` is up |
| `InvalidGroup.NotFound` during terminate | SG already deleted | Safe to ignore; script continues |
| `DependencyViolation` on SG delete | ENI not yet released | Script retries automatically |
| VS Code never opens | `code` not on `PATH` | Ensure VS Code CLI is installed: **VS Code → Command Palette → "Shell Command: Install 'code' command in PATH"** |
| Mid-launch failure leaves partial resources | Any boto3 exception during create | Run `terminate` to clean up, then `launch` again |
| VS Code server stays running / instance never auto-stops | vscode-server persists after client close (by design) | Run `terminate` or stop manually: `aws ec2 stop-instances --instance-ids <id> --profile <profile> --region <region>` |
| Bedrock access denied on remote | IAM instance profile may not have propagated yet | Wait 15 s and retry; the script already waits 10 s before launch but propagation can take slightly longer |

---

## Related Skills

- Ensure AWS credentials are configured in `~/.aws/config` or via environment variables before running. Use `aws sts get-caller-identity --profile <profile>` to verify they are active.

---

## Example End-to-End

```bash
# 1. Verify credentials are active
aws sts get-caller-identity --profile my-dev-profile

# 2. Launch
python3 ${SKILL_DIR}/scripts/ec2_vscode.py launch \
  --profile my-dev-profile \
  --region us-west-2 \
  --session-name dev \
  --instance-type t3.medium \
  --ami ami-0892d3c7ee96c0bf7 \
  --workspace /home/ec2-user/my-repo

# ... VS Code opens, you work, then close it ...
# Script auto-stops the instance.

# 3. Resume later (no --ami / --instance-type needed)
python3 ${SKILL_DIR}/scripts/ec2_vscode.py launch \
  --profile my-dev-profile \
  --region us-west-2 \
  --session-name dev

# 4. Terminate when done with the project
python3 ${SKILL_DIR}/scripts/ec2_vscode.py terminate \
  --profile my-dev-profile \
  --region us-west-2 \
  --session-name dev
```
