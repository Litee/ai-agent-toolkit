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
/plugin install manage-anki-flashcards@litee-claude-code-plugins
/plugin install query-aws-athena@litee-claude-code-plugins
/plugin install query-cloudwatch-logs@litee-claude-code-plugins
/plugin install register-safe-terminal-commands@litee-claude-code-plugins
/plugin install convert-audio@litee-claude-code-plugins
```

### Available Plugins

Each plugin installs a skill that extends Claude's capabilities:

| Plugin (Skill) | Category | Description |
|--------|----------|-------------|
| `convert-audio` | user | Audio format conversion using ffmpeg (MP3, WAV, AAC, FLAC, Opus, OGG) |
| `manage-anki-flashcards` | productivity | Anki flashcard management through AnkiConnect API |
| `query-aws-athena` | developer-tools | AWS Athena queries and CloudWatch Log Insights with query optimization and real-time progress tracking |
| `query-cloudwatch-logs` | developer-tools | CloudWatch Log Insights queries with real-time progress tracking |
| `register-safe-terminal-commands` | developer-tools | Safe terminal command configuration for Claude Code |

**Note:** Each plugin may have additional dependencies. Check the individual [skill documentation](skills/) for prerequisites and detailed usage instructions.
