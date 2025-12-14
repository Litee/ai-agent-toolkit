# ai-agent-toolkit

A repository with prompts, skills, and configuration tools for AI agents.

## Available Skills

### [register-safe-terminal-commands](skills/register-safe-terminal-commands/)

Manages safe terminal commands for Claude Code—bash commands that can be executed automatically without requiring user approval. Includes 289 pre-configured safe commands for AWS CLI, Git, Docker, and common development tools.

**Use this skill to:**
- Register safe terminal commands in Claude Code settings
- Sync commands from the reference file to `~/.claude/settings.json`
- Add new safe commands to the pre-approved list

**Quick start:**
```bash
python skills/register-safe-terminal-commands/scripts/sync_safe_commands.py
```

See the [skill documentation](skills/register-safe-terminal-commands/SKILL.md) for detailed usage instructions.
