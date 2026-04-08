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
/plugin install anki@litee-claude-code-plugins
/plugin install aws@litee-claude-code-plugins
/plugin install aws-documentation@litee-claude-code-plugins
/plugin install aws-query-tools@litee-claude-code-plugins
/plugin install cmux@litee-claude-code-plugins
/plugin install communication@litee-claude-code-plugins
/plugin install convert-audio@litee-claude-code-plugins
/plugin install cron-restoration-guard@litee-claude-code-plugins
/plugin install file-system-tools@litee-claude-code-plugins
/plugin install generate-image@litee-claude-code-plugins
/plugin install large-file-handling@litee-claude-code-plugins
/plugin install local-skill-issues-tracker@litee-claude-code-plugins
/plugin install ml-system-design-interviewer@litee-claude-code-plugins
/plugin install obsidian@litee-claude-code-plugins
/plugin install podcast-generation@litee-claude-code-plugins
/plugin install protect-file-system-access@litee-claude-code-plugins
/plugin install pyspark@litee-claude-code-plugins
/plugin install register-safe-terminal-commands@litee-claude-code-plugins
/plugin install status-line@litee-claude-code-plugins
/plugin install update-versioned-permissions@litee-claude-code-plugins
/plugin install writing@litee-claude-code-plugins
```

### Available Plugins

Each plugin installs a skill that extends Claude's capabilities:

| Plugin (Skill) | Category | Description |
|--------|----------|-------------|
| `anki` | productivity | Anki flashcard management through AnkiConnect API |
| `aws` (`use-aws-glue`) | developer-tools | AWS Glue ETL job configuration, update-job gotchas, worker type sizing, CloudWatch and Observability metrics, S3 shuffle, cron-based monitoring, per-worker progress reporting, and API call tracking |
| `aws-documentation` | developer-tools | AWS CDK expert guidance and official AWS documentation search via MCP servers |
| `aws-query-tools` (`query-aws-athena`, `query-aws-cloudwatch-logs-insights`, `monitor-aws-glue-job`) | developer-tools | AWS Athena SQL queries with S3 download and CTE optimization; CloudWatch Log Insights with real-time progress tracking; Glue job monitoring with background state-change notifications via cmux keystroke injection or team agent polling |
| `cmux` (`use-cmux`) | developer-tools | Terminal multiplexer integration: orchestrate sessions, browser automation, progress reporting; SessionStart hook prints cmux context and LLM behavioural instructions when running inside cmux |
| `communication` (`communicate-well`, `write-good-emails`) | productivity | Async communication guidelines for AI agents: value test, message style, frequency, anti-patterns, and channel-type rules; professional email writing: subject lines, tone calibration, difficult scenarios, follow-up strategy, and AI prompting for emails |
| `convert-audio` | user | Audio format conversion using ffmpeg (MP3, WAV, AAC, FLAC, Opus, OGG), bitrate/speed adjustment, and metadata tagging (ID3 tags) |
| `cron-restoration-guard` | developer-tools | SessionStart hook (resume only) that instructs the agent to verify and re-register any cron jobs from the previous session that are no longer active |
| `file-system-tools` | developer-tools | Free disk space by cleaning development caches, IDE artefacts, and Docker resources. Scan for bloat directories (node_modules, virtual environments, build caches) |
| `generate-image` | user | Image generation using Amazon Nova Canvas on AWS Bedrock |
| `large-file-handling` (`handle-large-files`) | developer-tools | Safe large file analysis without exceeding the context window: size-checking strategies, targeted extraction one-liners (Bash/Python/Node.js/PowerShell), structured data probing (JSON, CSV, XML, logs), codebase reconnaissance, and token estimation |
| `local-skill-issues-tracker` (`use-local-skills-issue-tracker`) | developer-tools | Local JSON-based issue tracker for disconnected agents to report skill bugs and feature requests. Includes a filesystem watcher with cmux integration for live notifications on new issues, status changes, and comments |
| `ml-system-design-interviewer` | productivity | ML System Design interview framework for Principal/Staff-level candidates |
| `obsidian` (`use-obsidian-cli`, `use-obsidian-markdown`, `manage-personal-knowledge-in-obsidian`) | productivity | Three skills: Obsidian CLI operations (CRUD, search, tags, properties, daily notes, templates, tasks); Obsidian Flavored Markdown syntax (wikilinks, embeds, callouts, properties, math, Mermaid); personal knowledge management methodology (atomic notes, PKM workflows, vault health) |
| `podcast-generation` | user | AI-powered podcast script generation and audio synthesis using AWS TTS |
| `protect-file-system-access` | developer-tools | PreToolUse hook blocking direct edits to AWS credentials, SSH keys, shell profiles, and lockfiles |
| `pyspark` (`use-pyspark`) | developer-tools | PySpark anti-patterns (JSON inference OOM, data skew, shuffle spill, Python UDFs), coding style guide (import aliases, type hints, method chains, join hygiene, null handling), and Spark tuning (AQE, broadcast joins, shuffle partitions) |
| `register-safe-terminal-commands` | developer-tools | SessionStart hook that auto-syncs safe terminal commands to Claude Code settings; skill available for manual dry-run/verbose sync |
| `status-line` | developer-tools | SessionStart hook that configures Claude Code statusline to display context usage, token counts, cost, model ID, git branch, and working directory |
| `update-versioned-permissions` | developer-tools | SessionStart hook that auto-clones stale versioned plugin path entries in permissions when plugins are upgraded; additive-only, also updates statusLine.command to latest installed version |
| `writing` (`write-technical-design`, `write-well`) | productivity | Two skills: technical design document drafting (HLD/LLD templates, section standards, architecture diagrams, assembly checklists, red-flag detection); universal writing quality (clarity, structure, conciseness, AI writing hygiene, editing checklists, format-aware guidance for design docs, RFCs, emails, postmortems, and status updates) |

**Note:** Each plugin may have additional dependencies. Check the individual [skill documentation](skills/) for prerequisites and detailed usage instructions.
