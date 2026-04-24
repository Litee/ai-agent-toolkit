---
name: use-qmd-cli
description: Use when searching a local markdown knowledge base, retrieving notes by path or docid, managing indexed collections, or running structured queries with hybrid BM25 + vector + LLM re-ranking search. Triggers on requests to search, query, or retrieve indexed markdown notes on-device with the QMD CLI.
---

# QMD CLI

QMD (`qmd`) is an on-device search engine for markdown notes combining BM25 full-text search, vector semantic search, and LLM re-ranking — all running locally.

For the complete flag reference, read `${SKILL_DIR}/references/cli-reference.md`.

## Prerequisites

Verify qmd is installed:

```bash
which qmd
qmd --version
```

If not found, install it:

```bash
npm install -g @tobilu/qmd   # requires Node.js >= 22
# or: bun install -g @tobilu/qmd  (requires Bun >= 1.0.0)
```

On first use, download the GGUF models (~2GB total):

```bash
qmd pull
```

Verify the index is healthy:

```bash
qmd status
```

---

## Quick Start

```bash
# 1. Add a folder of markdown files as a collection
qmd collection add ~/notes --name notes

# 2. Index the collection (full-text)
qmd update

# 3. Generate vector embeddings
qmd embed

# 4. Hybrid search (recommended)
qmd query "how does authentication work"

# 5. Retrieve a specific document
qmd get "path/to/file.md"
```

---

## Core Search Commands

### `qmd query` — Recommended

Hybrid search: BM25 + vector retrieval + LLM query expansion + cross-encoder re-ranking. Best quality, slowest. Default for most tasks.

```bash
# Simple text query (auto-expanded)
qmd query "database connection pooling"

# Limit results
qmd query "deployment strategies" -n 10

# Show full document content instead of snippet
qmd query "auth middleware" --full

# Filter to one collection
qmd query "error handling" -c backend-notes

# Machine-readable JSON for programmatic use
qmd query "API rate limiting" --json

# Skip LLM re-ranking (much faster on CPU, lower quality)
qmd query "quick lookup" --no-rerank

# Provide domain intent to steer query expansion
qmd query "connection pooling" --intent "Rust backend"

# Show retrieval score traces
qmd query "caching strategies" --explain
```

### `qmd search` — Fast BM25 Keyword Search

Full-text keyword search via SQLite FTS5. No LLM, no embeddings. Best for exact term lookups.

```bash
qmd search "ConnectionPool"
qmd search "TODO FIXME" -n 20
qmd search '"exact phrase"'          # phrase match
qmd search 'auth -oauth'             # negation
```

### `qmd vsearch` — Vector Semantic Search

Semantic similarity search using embeddings only. No LLM re-ranking. Good for conceptual/paraphrase matching when keywords differ from document language.

```bash
qmd vsearch "how to handle failures gracefully"
qmd vsearch "user authentication" --min-score 0.5
```

### Decision Guide

| Situation | Command |
|-----------|---------|
| Best results, have time | `qmd query` |
| Exact keyword, fast lookup | `qmd search` |
| Conceptual/paraphrase match | `qmd vsearch` |
| Fast + decent quality (no GPU) | `qmd query --no-rerank` |
| Scripting / pipeline | any + `--json` or `--files` |

---

## Retrieving Documents

### `qmd get` — Single Document

```bash
# Full document
qmd get "notes/project.md"

# From line 50 onward
qmd get "notes/project.md:50"

# Limit to 30 lines
qmd get "notes/project.md" -l 30

# With line numbers
qmd get "notes/project.md" --line-numbers

# By docid (6-char hash shown in search results)
qmd get "#abc123"
```

### `qmd multi-get` — Batch Fetch

```bash
# Glob pattern
qmd multi-get "notes/**/*.md"

# Comma-separated paths
qmd multi-get "notes/a.md,notes/b.md"

# JSON output, max 50 lines per file, skip large files
qmd multi-get "notes/*.md" --json -l 50 --max-bytes 20480
```

---

## Query Syntax

`qmd query` accepts two forms:

**Simple text** — auto-expanded via LLM into multiple query variants:

```bash
qmd query "database indexing strategies"
```

**Structured query document** — explicit typed lines give fine-grained control:

```bash
# lex: = BM25 keyword search
# vec: = vector semantic search
# hyde: = hypothetical document embeddings (provide an answer-like text)
# intent: = domain hint for query expansion disambiguation
qmd query $'intent: Rust backend\nlex: connection pool\nvec: managing concurrent database connections'
qmd query $'lex: "retry logic" -synchronous\nvec: resilience fault tolerance'
qmd query $'hyde: The retry mechanism uses exponential backoff with jitter'
```

Rules:
- A simple text query cannot mix with typed lines
- Typed lines use only `lex:`, `vec:`, or `hyde:` prefixes
- `intent:` is a standalone prefix for the whole query

---

## Output Formats for Agents

All search commands support structured output formats suitable for scripting and AI agent pipelines:

| Flag | Format | Use case |
|------|--------|---------|
| `--json` | JSON with snippets | Structured parsing, default count 20 |
| `--files` | `docid,score,filepath,context` | File-path-only pipelines |
| `--csv` | CSV with headers | Spreadsheet/tabular processing |
| `--md` | Markdown | Embedding in documents |
| `--xml` | XML | XML-based pipelines |
| *(none)* | Colorized TTY | Human reading |

Additional flags for controlling output volume:

```bash
-n <num>          # max results (default 5 for CLI, 20 for --files/--json)
--all             # return all matches (use with --min-score to avoid noise)
--min-score <f>   # minimum similarity score threshold
--full            # include full document content, not just snippet
--line-numbers    # include line numbers in output
```

---

## Collection Management

### Add and List

```bash
# Add a directory as a collection
qmd collection add ~/notes --name notes

# Add with a custom file glob (default: **/*.md)
qmd collection add ~/code --name code --mask "**/*.md,**/*.txt"

# List all collections
qmd collection list

# Inspect a collection's details
qmd collection show notes
```

### Remove and Rename

```bash
qmd collection remove old-notes
qmd collection rename my-notes personal-notes
```

### Inspect Indexed Files

```bash
# List all indexed files
qmd ls

# List files in a specific collection
qmd ls notes

# List files under a path prefix
qmd ls notes/journal
```

### Context — Attach Descriptions

Human-written summaries attached to path prefixes that steer retrieval:

```bash
qmd context add / "Personal notes and meeting transcripts"
qmd context add ~/notes/journal "Daily journal entries from 2024-2025"
qmd context add qmd://backend-notes/ "Go service implementation notes"
qmd context list
qmd context rm ~/notes/journal
```

---

## Maintenance

```bash
# Re-index all collections after file changes
qmd update

# Re-index and run git pull (or custom update command) before indexing
qmd update --pull

# Generate/refresh vector embeddings
qmd embed

# Force full re-embedding (clears all vectors first)
qmd embed -f

# Check index and collection health
qmd status

# Clear caches, vacuum SQLite
qmd cleanup

# Download/verify GGUF models
qmd pull

# Force re-download of models
qmd pull --refresh
```

---

## Multiple Indexes

Use `--index <name>` to maintain separate databases (e.g., work vs. personal):

```bash
qmd --index work collection add ~/work-notes --name work-notes
qmd --index work update
qmd --index work query "Q3 planning"
```

Default index is stored at `~/.cache/qmd/index.sqlite`.

---

## Agent Integration

QMD exposes an MCP server for direct integration with Claude Code and other AI tools:

```bash
# stdio transport (default for Claude Code)
qmd mcp

# HTTP transport (foreground)
qmd mcp --http --port 8181

# HTTP daemon (background)
qmd mcp --http --daemon

# Stop HTTP daemon
qmd mcp stop
```

Install the bundled QMD skill into `.agents/skills/qmd`:

```bash
qmd skill install           # project-local
qmd skill install --global  # ~/.agents/skills/qmd
```

---

## When to Use This Skill

**Use when:**
- Searching across a local markdown knowledge base
- Finding semantically related documents where keywords differ
- Retrieving a specific note or section by file path or docid
- Building structured queries with `lex:`/`vec:`/`hyde:` for precision
- Piping search results to other tools via `--json` or `--files`
- Maintaining collections (add, re-index, embed)

**Do NOT use when:**
- Files are not yet indexed — run `qmd update` and `qmd embed` first
- The user wants to create or edit notes (use file system tools or Obsidian CLI)
- Real-time web search is needed — qmd only indexes local files
- Files are not in markdown (qmd supports `**/*.md` by default; use `--mask` to include other types)

---

## CLI Reference

For the complete flag reference with all options, defaults, and environment variables, read `${SKILL_DIR}/references/cli-reference.md`.
