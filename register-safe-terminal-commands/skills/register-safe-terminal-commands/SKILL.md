---
name: register-safe-terminal-commands
description: This skill should be used when registering or syncing safe terminal commands to Claude Code settings. Use when the user wants to configure which bash commands Claude Code can execute without requiring approval, or when they need to register/update their safe commands list from the reference file.
dependencies:
  - python3
---

# Register Safe Terminal Commands Skill

## Purpose

This skill manages safe terminal commands for Claude Code—bash commands that can be executed automatically without requiring user approval for each execution. Safe commands are typically read-only, non-destructive operations like viewing files, checking status, or querying services.

## When to Use This Skill

Use this skill when:
- Adding or updating safe terminal commands in Claude Code settings
- Syncing safe commands from the reference file to `~/.claude/settings.json`
- Managing the list of pre-approved bash commands
- User asks to "add safe commands" or "sync safe commands to Claude Code"

## How It Works

### Safe Commands Reference File

The `references/safe_terminal_commands.txt` file contains **289 pre-configured safe commands** across these categories:

- **AWS CLI**: Read-only operations for 30+ AWS services (S3, EC2, Lambda, Athena, CloudWatch, etc.)
- **Git**: Status, log, diff, branch, show, blame operations
- **Docker**: Inspect, ps, images, logs, info commands
- **File System**: ls, cat, find, tree, du, df, stat
- **Text Processing**: grep, rg, awk, sed, jq, yq
- **Package Managers**: npm list, pip list, cargo check
- **Build/Test Tools**: npm run test, pytest, cargo test, swift test
- **Network/System**: curl, ping, hostname, whoami, uname, ps

The file supports Python-style comments for documentation:
```txt
# This is a full-line comment
git status
ls  # This is an end-of-line comment
```

### Sync Script

The `scripts/sync_safe_commands.py` script syncs commands from the reference file to Claude Code settings:

#### Basic Usage

```bash
python scripts/sync_safe_commands.py
```

This will:
1. Read commands from `references/safe_terminal_commands.txt`
2. Update `~/.claude/settings.json` with commands in `permissions.allow` array
3. Format each command as `Bash(command:*)`
4. Sort permissions alphabetically
5. Create a backup of settings before writing
6. Report added/unchanged commands

#### Advanced Options

```bash
# Preview changes without modifying settings (dry-run mode)
python scripts/sync_safe_commands.py --dry-run
python scripts/sync_safe_commands.py -n

# Show all commands including unchanged ones (verbose mode)
python scripts/sync_safe_commands.py --verbose
python scripts/sync_safe_commands.py -v

# Combine options
python scripts/sync_safe_commands.py -n -v
```

#### Command-line Options

- `--dry-run` / `-n`: Preview changes without modifying the settings file
- `--verbose` / `-v`: Show all commands including unchanged ones in the report

### Claude Code Settings Format

When synced, commands are stored in `~/.claude/settings.json` as:

```json
{
  "permissions": {
    "allow": [
      "Bash(git status:*)",
      "Bash(ls:*)",
      "Bash(aws s3 ls:*)"
    ]
  }
}
```

The `Bash(command:*)` format tells Claude Code to automatically approve any bash command matching that pattern.

## Workflow

When a user requests to sync safe commands:

1. **Locate the sync script**: Navigate to this skill's `scripts/` directory
2. **Run the sync script**: Execute `python scripts/sync_safe_commands.py`
3. **Use options as needed**: Add `--dry-run` to preview or `--verbose` for detailed output
4. **Verify the output**: Review the sync report showing added/unchanged commands
5. **Confirm completion**: The script will report total changes made and create a backup

## Adding New Safe Commands

To add new safe commands to the list:

1. **Edit the reference file**: Open `references/safe_terminal_commands.txt`
2. **Add commands**: One command per line, can include comments
3. **Run the sync script**: Execute the sync script to update Claude Code settings
4. **Verify**: Use `--verbose` to confirm the new commands were added

## Safety Notes

- The sync script **creates a backup** (`.json.bak`) before modifying settings
- Commands are **additive only** - the script never removes existing permissions
- All commands should be **read-only or non-destructive** operations
- The reference file includes only **safe, commonly-used commands** across development tools
