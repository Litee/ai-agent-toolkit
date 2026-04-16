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
/plugin install aws-athena@litee-claude-code-plugins
/plugin install aws-cloudwatch@litee-claude-code-plugins
/plugin install aws-documentation@litee-claude-code-plugins
/plugin install aws-glue@litee-claude-code-plugins
/plugin install aws-quota-service@litee-claude-code-plugins
/plugin install aws-support@litee-claude-code-plugins
/plugin install claude-code-status-line@litee-claude-code-plugins
/plugin install cmux-terminal@litee-claude-code-plugins
/plugin install communication@litee-claude-code-plugins
/plugin install convert-audio@litee-claude-code-plugins
/plugin install cron-restoration-guard@litee-claude-code-plugins
/plugin install file-system-tools@litee-claude-code-plugins
/plugin install generate-image@litee-claude-code-plugins
/plugin install local-skill-issues-tracker@litee-claude-code-plugins
/plugin install ml-system-design-interviewer@litee-claude-code-plugins
/plugin install obsidian@litee-claude-code-plugins
/plugin install podcast-generation@litee-claude-code-plugins
/plugin install protect-file-system-access@litee-claude-code-plugins
/plugin install pyspark@litee-claude-code-plugins
/plugin install register-safe-terminal-commands@litee-claude-code-plugins
/plugin install skill-creator-extra-tips@litee-claude-code-plugins
/plugin install update-versioned-permissions@litee-claude-code-plugins
/plugin install writing@litee-claude-code-plugins
```

### Available Plugins

Each plugin installs a skill that extends Claude's capabilities:

| Plugin (Skill) | Category | Description |
|--------|----------|-------------|
| `anki` | productivity | Anki flashcard management through AnkiConnect API |
| `aws-athena` (`query-aws-athena`) | developer-tools | AWS Athena SQL queries with S3 result download, parallel execution, and CTE optimization |
| `aws-cloudwatch` (`query-aws-cloudwatch-logs-insights`, `use-aws-cloudwatch-metrics`) | developer-tools | CloudWatch Log Insights queries with real-time progress tracking, flexible time ranges, multiple output formats (JSON, CSV, table), and multi-log-group support; CloudWatch custom metrics best practices: PutMetricData batching, EMF, GetMetricData, alarms with M-of-N evaluation and missing-data treatment, composite alarms, metric math, dimension cardinality design, high-resolution metrics, metric streams, Contributor Insights, cost optimization |
| `aws-documentation` | developer-tools | AWS CDK expert guidance and official AWS documentation search via MCP servers |
| `aws-glue` (`use-aws-glue`, `watch-aws-glue-job`) | developer-tools | AWS Glue ETL job writing, configuration, debugging, monitoring with CloudWatch and Observability metrics, S3 shuffle, worker sizing, per-worker progress reporting, API call tracking, live job monitoring (long-poll, cmux, and tmux modes), VPC endpoint validation, Flex job cost savings, Spark UI setup, small files handling (groupFiles/coalesce), timeout/MaxConcurrentRuns anti-patterns, and troubleshooting quick-reference |
| `aws-quota-service` (`watch-aws-quota-requests`) | developer-tools | AWS Service Quotas increase request monitoring with approval/denial notifications (long-poll, cmux, and tmux modes) |
| `aws-support` (`watch-aws-support-cases`) | developer-tools | AWS Support case monitoring with status/severity/communication change detection (long-poll, cmux, and tmux modes). Requires Business or Enterprise AWS support plan |
| `claude-code-status-line` | developer-tools | SessionStart hook that configures Claude Code statusline to display context usage, token counts, cost, model ID, git branch, and working directory |
| `cmux-terminal` (`use-cmux-terminal`) | developer-tools | Terminal multiplexer integration: orchestrate sessions, browser automation, progress reporting; SessionStart hook prints cmux context and LLM behavioural instructions when running inside cmux |
| `communication` (`communicate-well`, `write-good-emails`) | productivity | Async communication guidelines for AI agents: value test, message style, frequency, anti-patterns, and channel-type rules; professional email writing: subject lines, tone calibration, difficult scenarios, follow-up strategy, and AI prompting for emails |
| `convert-audio` | user | Audio format conversion using ffmpeg (MP3, WAV, AAC, FLAC, Opus, OGG), bitrate/speed adjustment, and metadata tagging (ID3 tags) |
| `cron-restoration-guard` | developer-tools | SessionStart hook (resume only) that instructs the agent to verify and re-register any cron jobs from the previous session that are no longer active |
| `file-system-tools` (`free-disk-space`, `handle-large-files`) | developer-tools | Free disk space by cleaning development caches, IDE artefacts, and Docker resources. Scan for bloat directories (node_modules, virtual environments, build caches). Safely analyze large files without exceeding the context window: size-checking strategies, targeted extraction one-liners (Bash/Python/Node.js), structured data probing (JSON, CSV, XML, logs), and token estimation |
| `generate-image` | user | Image generation using Amazon Nova Canvas on AWS Bedrock |
| `local-skill-issues-tracker` (`use-local-skills-issue-tracker`) | developer-tools | Local JSON-based issue tracker for disconnected agents to report skill bugs and feature requests. Includes a filesystem watcher with cmux and tmux integration for live notifications on new issues, status changes, and comments |
| `ml-system-design-interviewer` | productivity | ML System Design interview framework for Principal/Staff-level candidates |
| `obsidian` (`use-obsidian-cli`, `use-obsidian-markdown`, `manage-personal-knowledge-in-obsidian`) | productivity | Three skills: Obsidian CLI operations (CRUD, search, tags, properties, daily notes, templates, tasks); Obsidian Flavored Markdown syntax (wikilinks, embeds, callouts, properties, math, Mermaid); personal knowledge management methodology (atomic notes, PKM workflows, vault health) |
| `podcast-generation` | user | AI-powered podcast script generation and audio synthesis using AWS TTS |
| `protect-file-system-access` | developer-tools | PreToolUse hook blocking direct edits to AWS credentials, SSH keys, shell profiles, and lockfiles |
| `pyspark` (`use-pyspark`) | developer-tools | PySpark anti-patterns (JSON inference OOM, data skew, shuffle spill, Python UDFs), coding style guide (import aliases, type hints, method chains, join hygiene, null handling), and Spark tuning (AQE, broadcast joins, shuffle partitions) |
| `register-safe-terminal-commands` | developer-tools | SessionStart hook that auto-syncs safe terminal commands to Claude Code settings; skill available for manual dry-run/verbose sync |
| `skill-creator-extra-tips` | developer-tools | Supplementary skill-authoring guidance: portability best practices, file naming conventions, `${SKILL_DIR}` placeholder, three-level context management, self-containment rules, and automated tooling references |
| `update-versioned-permissions` | developer-tools | SessionStart hook that auto-clones stale versioned plugin path entries in permissions when plugins are upgraded; additive-only, also updates statusLine.command to latest installed version |
| `writing` (`write-technical-design`, `write-well`) | productivity | Two skills: technical design document drafting (HLD/LLD templates, section standards, architecture diagrams, assembly checklists, red-flag detection); universal writing quality (clarity, structure, conciseness, AI writing hygiene, editing checklists, format-aware guidance for design docs, RFCs, emails, postmortems, and status updates) |

**Note:** Each plugin may have additional dependencies. Check the individual [skill documentation](skills/) for prerequisites and detailed usage instructions.
