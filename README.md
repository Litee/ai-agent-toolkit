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
/plugin install aws-documentation@litee-claude-code-plugins
/plugin install cmux@litee-claude-code-plugins
/plugin install communicate-well@litee-claude-code-plugins
/plugin install convert-audio@litee-claude-code-plugins
/plugin install cron-restoration-guard@litee-claude-code-plugins
/plugin install file-system-tools@litee-claude-code-plugins
/plugin install generate-image@litee-claude-code-plugins
/plugin install manage-anki-flashcards@litee-claude-code-plugins
/plugin install manage-obsidian-vault@litee-claude-code-plugins
/plugin install ml-system-design-interviewer@litee-claude-code-plugins
/plugin install podcast-generation@litee-claude-code-plugins
/plugin install protect-file-system-access@litee-claude-code-plugins
/plugin install aws-query-tools@litee-claude-code-plugins
/plugin install register-safe-terminal-commands@litee-claude-code-plugins
/plugin install status-line@litee-claude-code-plugins
```

### Available Plugins

Each plugin installs a skill that extends Claude's capabilities:

| Plugin (Skill) | Category | Description |
|--------|----------|-------------|
| `aws-documentation` | developer-tools | AWS CDK expert guidance and official AWS documentation search via MCP servers |
| `aws-query-tools` | developer-tools | AWS Athena SQL queries and CloudWatch Log Insights with query optimization, CTE patterns, and real-time progress tracking |
| `cmux` (`use-cmux`) | developer-tools | Terminal multiplexer integration: orchestrate sessions, browser automation, progress reporting; SessionStart hook prints cmux context and LLM behavioural instructions when running inside cmux |
| `communicate-well` | productivity | AI agent async communication guidelines: value test, message style, frequency, anti-patterns, and channel-type rules for chat, tickets, and code reviews |
| `convert-audio` | user | Audio format conversion using ffmpeg (MP3, WAV, AAC, FLAC, Opus, OGG), bitrate/speed adjustment, and metadata tagging (ID3 tags) |
| `cron-restoration-guard` | developer-tools | SessionStart hook (resume only) that instructs the agent to verify and re-register any cron jobs from the previous session that are no longer active |
| `file-system-tools` | developer-tools | Free disk space by cleaning development caches, IDE artefacts, and Docker resources. Scan for bloat directories (node_modules, virtual environments, build caches) |
| `generate-image` | user | Image generation using Amazon Nova Canvas on AWS Bedrock |
| `manage-anki-flashcards` | productivity | Anki flashcard management through AnkiConnect API |
| `manage-obsidian-vault` (`use-obsidian-cli`, `use-obsidian-markdown`, `manage-personal-knowledge-in-obsidian`) | productivity | Three skills: Obsidian CLI operations (CRUD, search, tags, properties, daily notes, templates, tasks); Obsidian Flavored Markdown syntax (wikilinks, embeds, callouts, properties, math, Mermaid); personal knowledge management methodology (atomic notes, PKM workflows, vault health) |
| `ml-system-design-interviewer` | productivity | ML System Design interview framework for Principal/Staff-level candidates |
| `podcast-generation` | user | AI-powered podcast script generation and audio synthesis using AWS TTS |
| `protect-file-system-access` | developer-tools | PreToolUse hook blocking direct edits to AWS credentials, SSH keys, shell profiles, and lockfiles |
| `register-safe-terminal-commands` | developer-tools | SessionStart hook that auto-syncs safe terminal commands to Claude Code settings; skill available for manual dry-run/verbose sync |
| `status-line` | developer-tools | SessionStart hook that configures Claude Code statusline to display context usage, token counts, cost, model ID, git branch, and working directory |

**Note:** Each plugin may have additional dependencies. Check the individual [skill documentation](skills/) for prerequisites and detailed usage instructions.
