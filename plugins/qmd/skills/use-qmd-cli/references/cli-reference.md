# QMD CLI Reference

Complete command and flag reference for `qmd`. Requires Node.js >= 22 or Bun >= 1.0.0.

## General Syntax

```
qmd [--index <name>] <command> [options]
```

## Global Options

| Flag | Description |
|------|-------------|
| `--index <name>` | Use a named index (default: `index`). Database stored at `~/.cache/qmd/<name>.sqlite` |
| `--version` / `-v` | Print version |
| `--help` / `-h` | Print help |
| `--skill` | Alias for `qmd skill show` |

---

## Search Commands

All three search commands share these output and filtering options.

### Common Search Options

| Flag | Default | Description |
|------|---------|-------------|
| `-n <num>` | 5 (CLI), 20 (--files/--json) | Maximum number of results |
| `--all` | off | Return all matches (limit 100000); pair with `--min-score` |
| `--min-score <float>` | 0 (search/query), 0.3 (vsearch) | Minimum similarity score threshold |
| `--full` | off | Show full document content instead of snippet |
| `-c, --collection <name>` | all | Filter by collection name; repeatable for multiple |
| `--line-numbers` | off | Include line numbers in output |
| `--explain` | off | Include retrieval score traces (RRF + rerank blend details) |
| `--chunk-strategy <auto\|regex>` | regex | Chunking mode: `auto` uses AST for code files; `regex` uses text-based splitting |
| `--files` | | Output format: `docid,score,filepath,context` per line |
| `--json` | | Output format: JSON with snippets |
| `--csv` | | Output format: CSV with headers `docid,score,file,title,context,line,snippet` |
| `--md` | | Output format: Markdown |
| `--xml` | | Output format: XML |

Output format flags are mutually exclusive. If none specified, colorized TTY output (respects `NO_COLOR` env var).

---

### `qmd query <query>`

Hybrid search: BM25 + vector retrieval + LLM query expansion + cross-encoder re-ranking. Recommended for best quality.

Additional options beyond common search options:

| Flag | Default | Description |
|------|---------|-------------|
| `--intent <text>` | | Domain intent for query expansion disambiguation |
| `-C, --candidate-limit <n>` | 40 | Max candidates passed to re-ranker (lower = faster) |
| `--no-rerank` | off | Skip LLM re-ranking, use RRF scores only (much faster on CPU) |

**Query syntax** — two forms:

1. **Simple text** (auto-expanded): `qmd query "how does auth work"`
2. **Structured query document** (typed lines, use `$'...'` in bash for `\n`):

```
intent: <domain hint>
lex: <BM25 keyword query>
vec: <vector semantic query>
hyde: <hypothetical document text for embedding>
```

Constraints:
- Simple text and typed lines cannot be mixed
- `intent:` is a top-level prefix, not a typed line
- Each typed line must be single-line text with balanced quotes
- `lex:` supports phrase matching (`"exact phrase"`) and negation (`-term`)

---

### `qmd search <query>`

BM25 full-text keyword search via SQLite FTS5. No LLM, no embeddings. Supports all common search options.

---

### `qmd vsearch <query>`

Vector semantic search only. Supports all common search options minus `--no-rerank` (not applicable).

Alias: `qmd vector-search`

---

## Document Retrieval

### `qmd get <file>[:line]`

Retrieve a single document. `<file>` can be a path, a path with line offset (`file.md:50`), or a docid (`#abc123`).

| Flag | Description |
|------|-------------|
| `--from <num>` | Start output from this line number |
| `-l <num>` | Maximum number of lines to return |
| `--line-numbers` | Include line numbers in output |
| `--json/--csv/--md/--xml/--files` | Output format |

---

### `qmd multi-get <pattern>`

Batch fetch via glob pattern or comma-separated list of paths/docids.

| Flag | Default | Description |
|------|---------|-------------|
| `-l <num>` | unlimited | Maximum lines per file |
| `--max-bytes <num>` | 10240 (10KB) | Skip files larger than N bytes |
| `--json/--csv/--md/--xml/--files` | | Output format |

---

## Collection Management

### `qmd collection add <path> [options]`

| Flag | Description |
|------|-------------|
| `--name <name>` | Collection name (defaults to directory basename) |
| `--mask <pattern>` | Glob pattern for files to include (default: `**/*.md`) |

### `qmd collection list`

List all collections with their paths, file counts, and include-by-default status.

### `qmd collection remove <name>`

Remove a collection. Aliases: `qmd collection rm`.

### `qmd collection rename <old> <new>`

Rename a collection. Aliases: `qmd collection mv`.

### `qmd collection show <name>`

Show detailed collection info. Aliases: `qmd collection info`.

### `qmd collection update-cmd <name> [cmd]`

Set or clear the pre-update bash command for a collection (run during `qmd update --pull`).

### `qmd collection include <name>` / `qmd collection exclude <name>`

Toggle whether a collection is included in queries that don't specify `-c`.

---

## File Listing

### `qmd ls [collection[/path]]`

List indexed files like `ls -l`. Optionally scoped to a collection or path prefix.

---

## Context Management

### `qmd context add [path] "<text>"`

Attach a human-written description to a path prefix. Steers retrieval.

- `qmd context add / "text"` — global context for all collections
- `qmd context add ~/notes/journal "text"` — scoped to a path
- `qmd context add qmd://name/ "text"` — by virtual collection path

### `qmd context list`

List all context entries.

### `qmd context rm <path>`

Remove a context entry. Aliases: `qmd context remove`.

---

## Index Maintenance

### `qmd update [--pull]`

Re-index all collections. With `--pull`, runs each collection's configured update command (e.g., `git pull`) before re-indexing.

### `qmd embed [options]`

Generate or refresh vector embeddings.

| Flag | Description |
|------|-------------|
| `-f, --force` | Force full re-embedding (clears all vectors first) |
| `--max-docs-per-batch <n>` | Cap docs loaded into memory per embedding batch |
| `--max-batch-mb <n>` | Cap UTF-8 MB loaded into memory per embedding batch |
| `--chunk-strategy <auto\|regex>` | Chunking mode for embedding |

### `qmd status`

Show index health, collection stats, model info, GPU detection, and AST status.

### `qmd cleanup`

Clear caches, remove orphaned data, and vacuum the SQLite database.

### `qmd pull [--refresh]`

Download and verify GGUF models. `--refresh` forces re-download even if present.

---

## MCP Server

### `qmd mcp`

Start the MCP server using stdio transport (default for Claude Code / AI agent integration).

### `qmd mcp --http [--port N] [--daemon]`

| Flag | Default | Description |
|------|---------|-------------|
| `--http` | off | Use HTTP transport instead of stdio |
| `--port <num>` | 8181 | HTTP port |
| `--daemon` | off | Run as background daemon (requires `--http`) |

HTTP endpoints:
- `POST /mcp` — MCP Streamable HTTP (JSON responses, stateless)
- `GET /health` — Liveness check

### `qmd mcp stop`

Stop the background HTTP daemon.

---

## Skill Management

### `qmd skill show`

Print the bundled QMD skill content to stdout.

### `qmd skill install [options]`

Install the bundled QMD skill.

| Flag | Description |
|------|-------------|
| `--global` | Install to `~/.agents/skills/qmd` (default: `./.agents/skills/qmd`) |
| `--yes` | Auto-create the `.claude/skills/qmd` symlink without prompting |
| `-f, --force` | Replace existing install or symlink |

---

## Benchmarking

### `qmd bench <fixture.json>`

Run search quality benchmarks against a fixture file.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QMD_EDITOR_URI` | `vscode://file/{path}:{line}:{col}` | Editor link template for clickable TTY output. Placeholders: `{path}`, `{line}`, `{col}`/`{column}` |
| `QMD_EMBED_MODEL` | `embeddinggemma-300M-Q8_0` | Override embedding model (useful for multilingual notes) |
| `QMD_CONFIG_DIR` | | Override config directory entirely |
| `XDG_CACHE_HOME` | `~/.cache` | Cache directory (database and models) |
| `XDG_CONFIG_HOME` | `~/.config` | Config directory (YAML files) |
| `NO_COLOR` | | Disable ANSI color output when set |
| `INDEX_PATH` | | Override database path (for testing) |

Editor URI templates for common editors:

| Editor | Template |
|--------|----------|
| VS Code (default) | `vscode://file/{path}:{line}:{col}` |
| Cursor | `cursor://file/{path}:{line}:{col}` |
| Zed | `zed://file/{path}:{line}:{col}` |
| Sublime Text | `subl://open?url=file://{path}&line={line}` |

---

## Configuration File

YAML config at `~/.config/qmd/index.yml` (or `~/.config/qmd/<name>.yml` for named indexes):

```yaml
global_context: "Optional global description applied to all collections."

# Override GGUF models (use HuggingFace GGUF URLs)
models:
  embed: "hf:org/repo/model-Q8_0.gguf"
  rerank: "hf:org/repo/reranker.gguf"
  generate: "hf:org/repo/generator.gguf"

# Editor link template
editor_uri: "cursor://file/{path}:{line}:{col}"

collections:
  notes:
    path: ~/Documents/Notes
    pattern: "**/*.md"
    ignore: ["Archive/**", "*.draft.md"]
    update: "git stash && git pull --rebase --ff-only && git stash pop"
    includeByDefault: true
    context:
      "/": "Personal notes and project documentation"
      "/journal/2025": "Daily notes from 2025"
```

### Collection config fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `path` | string | required | Absolute path to the directory |
| `pattern` | string | `**/*.md` | Glob pattern for files to include |
| `ignore` | string[] | `[]` | Glob patterns to exclude |
| `context` | map | `{}` | Path-prefix → description for retrieval steering |
| `update` | string | null | Bash command run during `qmd update --pull` |
| `includeByDefault` | boolean | true | Include in queries that don't specify `-c` |

---

## Data Paths

| Purpose | Default Path |
|---------|-------------|
| SQLite database | `~/.cache/qmd/index.sqlite` |
| Named index database | `~/.cache/qmd/<name>.sqlite` |
| Config file | `~/.config/qmd/index.yml` |
| Named config | `~/.config/qmd/<name>.yml` |
| GGUF models | `~/.cache/qmd/models/` |

---

## Bundled GGUF Models

Auto-downloaded on first use via `qmd pull`:

| Model | Purpose | Size |
|-------|---------|------|
| `embeddinggemma-300M-Q8_0` | Vector embeddings | ~300MB |
| `qwen3-reranker-0.6b-q8_0` | Cross-encoder re-ranking | ~640MB |
| `qmd-query-expansion-1.7B-q4_k_m` | Query expansion (fine-tuned) | ~1.1GB |

Total: ~2GB on first install. GPU acceleration via Metal (macOS) or CUDA (Linux/Windows) if available.

---

## Command Aliases

| Canonical | Aliases |
|-----------|---------|
| `qmd vsearch` | `qmd vector-search` |
| `qmd query` | `qmd deep-search` |
| `qmd collection remove` | `qmd collection rm` |
| `qmd collection rename` | `qmd collection mv` |
| `qmd collection show` | `qmd collection info` |
| `qmd collection update-cmd` | `qmd collection set-update` |
| `qmd context rm` | `qmd context remove` |
