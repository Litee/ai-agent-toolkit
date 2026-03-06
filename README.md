# ai-agent-toolkit

A repository with prompts, skills, and configuration tools for AI agents.

## Installing as Claude Code Plugins

These skills can be installed as plugins in Claude Code.

### Step 1: Register the Marketplace

```bash
/plugin marketplace add Litee/ai-agent-toolkit
```

### Step 2: Install Plugins

**Interactive installation:**
1. Run `/plugin` and select `Browse and install plugins`
2. Select `litee-claude-code-plugins`
3. Choose the plugin you want to install
4. Select `Install now`

**Direct installation:**
```bash
/plugin install analyze-mcp@litee-claude-code-plugins
/plugin install aws-documentation@litee-claude-code-plugins
/plugin install convert-audio@litee-claude-code-plugins
/plugin install generate-image@litee-claude-code-plugins
/plugin install manage-anki-flashcards@litee-claude-code-plugins
/plugin install manage-obsidian-vault@litee-claude-code-plugins
/plugin install ml-system-design-interviewer@litee-claude-code-plugins
/plugin install podcast-generation@litee-claude-code-plugins
/plugin install protect-file-system-access@litee-claude-code-plugins
/plugin install aws-query-tools@litee-claude-code-plugins
/plugin install register-safe-terminal-commands@litee-claude-code-plugins
```

### Available Plugins

Each plugin installs a skill that extends Claude's capabilities:

| Plugin (Skill) | Category | Description |
|--------|----------|-------------|
| `analyze-mcp` | developer-tools | MCP server introspection and tool testing via CLI |
| `aws-documentation` | developer-tools | AWS CDK expert guidance and official AWS documentation search via MCP servers |
| `aws-query-tools` | developer-tools | AWS Athena SQL queries and CloudWatch Log Insights with query optimization, CTE patterns, and real-time progress tracking |
| `convert-audio` | user | Audio format conversion using ffmpeg (MP3, WAV, AAC, FLAC, Opus, OGG) |
| `generate-image` | user | Image generation using Amazon Nova Canvas on AWS Bedrock |
| `manage-anki-flashcards` | productivity | Anki flashcard management through AnkiConnect API |
| `manage-obsidian-vault` | productivity | Obsidian vault note management via CLI for knowledge management workflows |
| `ml-system-design-interviewer` | productivity | ML System Design interview framework for Principal-level candidates |
| `podcast-generation` | user | AI-powered podcast script generation and audio synthesis using AWS TTS |
| `protect-file-system-access` | developer-tools | PreToolUse hook blocking direct edits to AWS credentials, SSH keys, shell profiles, and lockfiles |
| `register-safe-terminal-commands` | developer-tools | Safe terminal command configuration for Claude Code |

**Note:** Each plugin may have additional dependencies. Check the individual [skill documentation](skills/) for prerequisites and detailed usage instructions.
