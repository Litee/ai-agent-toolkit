---
name: build-cli
description: This skill should be used when the user asks to "design a CLI", "build a command-line tool", "review my CLI design", "add a subcommand", "improve CLI ergonomics", "make my CLI scriptable", "add --json output", "fix CLI error messages", or asks about CLI best practices, CLI conventions, POSIX flags, shell completion, exit codes, or CLI anti-patterns. Also triggers when reviewing or critiquing an existing CLI's interface, output, or configuration design.
version: 0.1.0
---

# CLI Design Skill

Guide for designing and reviewing command-line interfaces (CLIs). Covers language-agnostic best practices, POSIX/GNU conventions, anti-patterns, and modern patterns for both human and AI-agent consumers.

Reference `references/best-practices.md` for detailed rules organized by topic. Reference `references/anti-patterns.md` for a checklist of common mistakes with real-world examples.

---

## Core Mental Model

A CLI is simultaneously a **user interface** (humans type commands) and an **API contract** (scripts, CI/CD pipelines, and AI agents parse output and check exit codes). Design decisions must serve both audiences. The key mechanism: detect TTY at runtime and adapt — colors/spinners/prompts for humans, clean structured output for pipes/scripts.

---

## Command Naming and Structure

Pick **one** consistent structure (noun-verb or verb-noun) and never mix:
- `tool <noun> <verb>` — e.g., `tool user create`, `tool job list`
- `tool <verb> <noun>` — e.g., `tool create user`, `tool list jobs`

Use kebab-case for multi-word commands and flags. Use consistent verb pairs everywhere: `add/remove`, `start/stop`, `enable/disable`, `create/delete`. Never use different verbs for the same concept across subcommands.

**Rule of thumb for positional arguments:** one is fine, two are questionable, three or more is a design error — use named flags instead.

---

## Essential Flags

Every CLI must support:

| Flag | Short | Purpose |
|------|-------|---------|
| `--help` | `-h` | Help on every command and subcommand |
| `--version` | | Version + build commit/date |
| `--json` | | Machine-readable output |
| `--quiet` | `-q` | Suppress non-essential output |
| `--verbose` | `-v` | Extra diagnostic output |
| `--no-color` | | Disable ANSI codes |
| `--dry-run` | `-n` | Preview without executing (all mutations) |
| `--force` / `--yes` | | Skip confirmation prompts for automation |

Never accept secrets via command-line flags — they appear in `ps` output and shell history. Use files, environment variables, or credential stores instead.

---

## Streams and Output

```
stdout  →  data (machine-readable results, piped to next command)
stderr  →  diagnostics (errors, warnings, progress, spinners)
```

Never mix them. Progress bars or status messages on stdout corrupt piped data.

| Mode | Behavior |
|------|----------|
| TTY (interactive) | Human-friendly tables, colors, spinners, progress bars |
| Pipe / redirect | Plain text or JSON — no ANSI codes, no spinners, no prompts |
| `--json` | Stable JSON envelope: `{"status":"ok","data":{...}}` or `{"error":{"code":"...","message":"..."}}` |
| `--quiet` | Suppress everything except primary output |
| `--plain` | Grep-friendly tabular output (one record per line) |

For JSON output, treat field names, nesting, and types as a versioned API contract. Additive changes (new fields) are safe; removals and renames are breaking changes requiring a major version bump.

---

## Error Messages

Every error must answer three questions:

1. **What** failed (include the offending value)
2. **Why** it failed
3. **How** to fix it (concrete next step or doc link)

Structured error format for `--json` mode:
```json
{"error": {"code": "AUTH_EXPIRED", "message": "Token expired at 2025-01-15T10:00:00Z", "suggestion": "Run: tool auth login"}}
```

Never dump raw stack traces by default. Suggest corrections for typos. Link to documentation for complex failures. Put the most important information last (closest to the cursor).

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General / runtime error |
| 2 | Usage / argument error |
| 64–78 | BSD sysexits.h range (EX_USAGE=64, EX_NOINPUT=66, EX_UNAVAILABLE=69, EX_TEMPFAIL=75) |
| 126 | Command not executable |
| 127 | Command not found |
| 128+N | Killed by signal N (130=SIGINT, 137=SIGKILL, 143=SIGTERM) |

Exit codes are part of the API contract — document them and test every code path. Never exit with 0 on failure.

---

## Interactivity and Safety

- Only prompt when stdin is a TTY; never hang waiting for input when piped
- Always provide `--yes`/`--force`/`--no-input` to bypass prompts for automation and CI
- Confirm destructive actions; scale severity:
  - Mild → optional confirmation
  - Moderate → require `--force`
  - Severe → require typing the resource name
- Offer `--dry-run` for every command that mutates state
- "Double Ctrl+C" pattern: first SIGINT → graceful shutdown, second → force exit (code 130)

---

## Configuration Precedence

Apply in strict order, highest to lowest priority:

```
CLI flags > env vars > project config (.toolrc) > user config (~/.config/tool/) > system config (/etc/tool/) > built-in defaults
```

- Follow XDG Base Directory spec on Linux/macOS (`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME`)
- On macOS, CLI tools use `~/.config/` — **not** `~/Library/Application Support/` (that is for `.app` GUI bundles)
- Use a consistent env var prefix (`TOOL_*`) and document all supported env vars
- Provide `tool config show` to display resolved configuration for debugging

---

## Help Text

Structure every `--help` output as:
1. One-line description
2. Usage pattern with `[flags]` notation
3. **Examples first** — the most-read section by far
4. Common flags (with defaults shown inline)
5. Link to web documentation

Support `-h` and `--help` on every subcommand. When run with no required arguments provided, show concise help — not a full manual. Use progressive disclosure: `--help` for common options, man page or `--help-all` for everything.

---

## Accessibility

- Never rely solely on color to convey meaning — always pair with a text label (`ERROR:`, `WARNING:`)
- Respect `NO_COLOR` environment variable and `TERM=dumb`
- Avoid decorative ASCII art borders (break on resize, unreadable to screen readers, corrupt when piped)
- Avoid animated spinners in non-TTY contexts — use a simple percentage counter or step number as fallback
- Ensure output remains grep-able — don't use emojis to replace searchable words

---

## Performance

| Threshold | User perception |
|-----------|----------------|
| < 50ms | Instant |
| < 100ms | Fast |
| 200–500ms | Sluggish |
| > 500ms | Resentment |
| > 1s | Seeking alternatives |

Key practices:
- Defer heavy imports to command handlers (not module top-level) — single highest-impact optimization
- Avoid any network calls on startup (update checks, telemetry pings, config fetches)
- Lazy-load plugins; never initialize all plugins on every invocation
- Treat startup regressions as build failures — measure in CI

---

## Testing

- Test the **binary as a black box** — spawn the actual executable and assert on stdout, stderr, and exit code
- Layer tests: unit (parsing / validation logic) → integration (full command execution) → E2E (multi-step workflows)
- Snapshot test stdout/stderr for output format stability — catches unintentional breaking changes
- Test both TTY and non-TTY modes (`--json`, `--quiet`, no interactive prompts)
- Test boundary cases: no arguments, `--help`, invalid flags, `-` for stdin, `--dry-run`
- Run on all target platforms in CI matrix (Linux, macOS, Windows)

---

## Versioning

Use SemVer. **Breaking changes** in a CLI include: removing/renaming flags or subcommands, changing default behavior, changing JSON output schema (field removal, type changes, nesting), changing exit codes.

**Not breaking:** adding new flags/subcommands, adding fields to JSON output, improving human-readable error messages.

Deprecate before removing: print a warning to **stderr** (not stdout), keep old behavior working for at least one minor version, include migration guidance in the warning.

---

## AI-Agent-Friendly Design

AI agents are first-class consumers of CLIs. Key requirements:

- JSON output with stable, versioned schemas (`--json` flag or auto-detect when not TTY)
- Schema introspection: `tool --schema` returns JSON schema of inputs/outputs
- Deterministic, non-interactive by default — never hang waiting for stdin
- Terse, action-oriented output (agents pay per token; verbose decorative output wastes context window)
- Structured errors with exact fix commands in the `suggestion` field
- `--dry-run` for pre-validation before execution
- Idempotent operations — running a command twice produces the same result

---

## Distribution

- Ship prebuilt single-file binaries for all targets: linux-x64, linux-arm64, darwin-x64, darwin-arm64, win-x64
- Publish SHA-256 checksums for every artifact; sign with GPG/PGP or Sigstore/Cosign
- For npm: use "wrapper + optional platform packages" pattern (not postinstall download scripts — they break behind proxies and in offline CI)
- Publish to channels where users already are: GitHub Releases as baseline, then Homebrew, apt/yum, pip, crates.io, etc.
- Automate publishing via CI on tag push
- Implement `tool update` with checksum verification and previous-version rollback support

---

## Additional Resources

- **`references/best-practices.md`** — Full rules organized by topic (naming, flags, help, output, colors, errors, exit codes, interactivity, progress, discoverability, config, auth, signals, idempotency, testing, versioning, performance, distribution, plugins, telemetry)
- **`references/anti-patterns.md`** — Checklist of common mistakes organized by category, drawn from real-world CLI design failures (git, npm, AWS CLI, Docker, and others)
