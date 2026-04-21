# CLI Best Practices Reference

Comprehensive, language-agnostic rules drawn from ~58 sources including clig.dev, POSIX/GNU standards, ThoughtWorks, Atlassian, seirdy.one, and the CLI Spec (clispec.dev).

---

## 1. Command Naming and Structure

- Use clear, lowercase, human-readable names; avoid cryptic abbreviations ("Clever names age badly. Clear names scale.")
- Pick ONE consistent structure — `tool <noun> <verb>` or `tool <verb> <noun>` — and never mix
- Use kebab-case for multi-word commands and flags
- Group related functionality under subcommands of one tool rather than many separate executables
- Use consistent verb pairs: `add/remove`, `start/stop`, `enable/disable`, `create/delete`, `list/describe`
- Subcommand names: short, imperative verbs
- Check for binary name conflicts before publishing
- Command names should be easy to type — ergonomics matter for commands run hundreds of times daily (Docker Compose was renamed `fig` from `plum` because `plum` was physically awkward)

## 2. Flags and Arguments

- Prefer named flags over positional arguments — flags are self-documenting and order-independent
- One positional argument is fine; two are questionable; three or more is a design error
- Use long-form (`--verbose`) as primary; add short aliases (`-v`) for frequent flags
- Support `--` to separate options from arguments (POSIX standard)
- Support `-` as a filename to mean stdin/stdout
- Standard short aliases: `-h` (help), `-v` (verbose), `-q` (quiet), `-n` (dry-run), `-f` (force/file), `-o` (output), `-a` (all), `-d` (debug)
- Provide sensible defaults so most flags are optional
- Never accept secrets via flags (visible in `ps` and shell history)

## 3. Help Text

- Support `-h` and `--help` on every command and subcommand
- When required arguments are missing, show concise help — not a full manual
- Lead with examples — they are "by far the most read and revisited" section
- Show common flags/commands first; put rare options later
- Show defaults inline: `--timeout=30s`
- Structure: description → usage pattern → examples → flags → link to docs
- Link to web docs from `--help` for deeper reference
- Provide man pages (standardized, screen-reader-friendly, work offline)
- Provide shell completions for bash/zsh/fish/PowerShell with descriptions
- Progressive disclosure: `--help` for common options, man page or `--help-all` for everything

## 4. Output and Display

- Human-first by default when stdout is a TTY: aligned tables, brief messages, subtle colors, spinners
- Machine-readable on request: `--json` for structured output, `--plain` for grep-able tabular output
- TTY detection: auto-disable colors, spinners, progress bars when output is piped or redirected
- Send primary output to stdout; send diagnostics/progress/errors to stderr
- Acknowledge state changes: when something changes, tell the user what happened
- Keep success messages brief — too little feels broken, too much drowns the signal
- Support `--quiet` to suppress all non-essential output
- For JSON: stable field names, ISO 8601 timestamps, consistent casing; NDJSON for streaming
- Use a pager for large output when stdout is a TTY
- stdout is fully buffered when piped — flush explicitly for real-time pipeline output

## 5. Colors, Formatting, and Accessibility

- Never rely solely on color to convey meaning — always add a text label (`ERROR:`, `WARNING:`)
- Check `NO_COLOR` env var, `TERM=dumb`, and `isatty()` before emitting ANSI codes
- Support `--no-color` and `--color=always|never|auto`
- Avoid decorative ASCII art borders (break on resize, confuse screen readers, corrupt piped data)
- Avoid animated spinners in non-TTY contexts; use simple percentage or step counters
- Ensure output remains grep-able — don't use emojis to replace searchable words
- Test output through a screen reader (e.g., `espeak-ng`) to verify it makes sense
- Use emojis and colors sparingly — "if everything is a highlight, nothing is a highlight"

## 6. Error Messages

- State WHAT failed (include the offending value), WHY it failed, and HOW to fix it
- Use plain language — not internal jargon, exception names, or raw stack traces
- Provide doc links or bug-report paths for complex or unexpected failures
- Return a structured error object to stderr in `--json` mode:
  ```json
  {"error": {"code": "AUTH_EXPIRED", "message": "Token expired", "suggestion": "Run: tool auth login", "docs": "https://..."}}
  ```
- Suggest corrections for typos (edit distance / Damerau-Levenshtein)
- Distinguish tool errors from third-party service errors
- Put the most important information last (closest to the user's cursor)
- Validate input early — fail before starting any mutations

## 7. Exit Codes

- 0 = success; non-zero = failure — universal contract for scripts and CI
- Conventional codes: 0=success, 1=general error, 2=usage/argument error
- BSD sysexits.h range (64–78): EX_USAGE=64, EX_DATAERR=65, EX_NOINPUT=66, EX_UNAVAILABLE=69, EX_SOFTWARE=70, EX_TEMPFAIL=75, EX_CONFIG=78
- Reserved: 126=command not executable, 127=command not found
- Signal codes: 128+N (130=SIGINT, 137=SIGKILL, 143=SIGTERM)
- Exit codes are a single unsigned byte (0–255); use 0–127 for application codes
- Document exit codes; test every code path; treat them as API

## 8. Interactivity and Safety

- Only prompt when stdin is a TTY; when piped, either apply defaults or fail with guidance
- Provide `--yes`/`--force`/`--no-input` flags to bypass all prompts for automation
- Scale confirmation to severity: mild (optional), moderate (`--force` required), severe (type the resource name)
- Offer `--dry-run` for every command that mutates state
- Provide clear exit pathways; remind users about Ctrl+C for interactive modes
- "Double Ctrl+C": first SIGINT → graceful shutdown; second SIGINT → immediate exit (code 130)
- Never let prompts block CI/CD — if stdin is not a TTY, show which flag to pass instead

## 9. Progress and Responsiveness

- Print something within 100ms if work may take time — silence feels broken
- Spinners for indeterminate waits; progress bars for determinate ones
- Show granular progress: current step, total steps (`[3/7] Uploading artifacts...`)
- Send progress indicators to stderr so they don't pollute stdout data
- Provide `--no-progress` flag to disable indicators for scripts

## 10. Discoverability and Conversational Design

- Suggest next commands after successful operations ("Next: run `tool deploy`")
- Suggest corrections when the user makes a typo ("Did you mean `create`?")
- Make current state easy to inspect — `git status` is the gold standard
- Design for trial-and-error learning: errors should teach, not just fail
- Provide context-aware behavior: pick up project config files, adapt to the working directory

## 11. Configuration Precedence

- Strict order (highest to lowest): CLI flags > env vars > project config > user config > system config > built-in defaults
- Follow XDG Base Directory spec on Linux/macOS: `$XDG_CONFIG_HOME` (~/.config), `$XDG_DATA_HOME` (~/.local/share), `$XDG_CACHE_HOME` (~/.cache)
- On macOS, use `~/.config/tool/` — NOT `~/Library/Application Support/` (that is for `.app` GUI bundles)
- On Windows: `%APPDATA%` for config, `%LOCALAPPDATA%` for data/cache
- Consistent env var prefix (`TOOL_*`); map `TOOL_MAX_RETRIES` → `maxRetries`
- Support `--config <path>` to explicitly override config file location
- Walk up directory tree for project-level config (cosmiconfig pattern — like ESLint, Prettier)
- Provide `tool config show` to display resolved configuration with source annotations

## 12. Authentication and Credential Storage

- System keychains are primary recommended storage: macOS Keychain, Windows Credential Manager, libsecret on Linux
- For interactive auth, prefer OAuth Device Code Flow (RFC 8628) — decouples browser from CLI, works in SSH/Docker/headless environments, supports SSO/MFA
- For local machines, browser-based OAuth (Authorization Code Flow) works; bind only to 127.0.0.1, use CSRF state parameter
- API keys for machine-to-machine only (CI/CD service accounts); they lack identity and SSO support
- Exchange long-lived credentials for short-lived tokens at runtime (STS pattern)
- Token files must use restrictive permissions (chmod 600)
- Support multiple auth profiles (dev, staging, prod, CI)
- Provide `tool auth status` to inspect current authentication state

## 13. Composability and Unix Citizenship

- stdout for data; stderr for diagnostics — always, without exception
- End output with a trailing newline
- Support `-` as a filename to read from / write to stdin/stdout
- Handle SIGPIPE/EPIPE gracefully — when downstream reader closes, exit cleanly (code 0 or 141)
- Respect standard env vars: `NO_COLOR`, `EDITOR`, `VISUAL`, `PAGER`, `HTTP_PROXY`, `TERM`
- Make operations idempotent where possible
- Avoid implicit side effects — if a command does something beyond its stated purpose, make it explicit

## 14. Signal Handling and Graceful Shutdown

- Handle SIGTERM and SIGINT at minimum
- Signal handlers must be async-signal-safe — set only atomic flags; no malloc, locks, or I/O in the handler itself
- Five-step shutdown sequence: (1) stop accepting work, (2) set force-exit timeout, (3) wait for in-flight ops, (4) close external resources, (5) final cleanup
- Use atomic file writes: write to temp file in same directory, then rename (POSIX rename is atomic on same filesystem)
- Clean up temp files on SIGTERM/SIGINT; leave them on SIGQUIT (post-mortem convention)
- Use RAII / try-finally / defer for cleanup — ensure it runs on all exit paths
- Kubernetes grace period: default 30s — reserve ~20% safety margin for cleanup

## 15. Idempotency and Crash Recovery

- Design operations to be idempotent: running once or N times produces the same result
- Use idempotency keys for state-altering operations (caller-generated unique ID per intended action)
- Checkpoint progress for long-running operations — support `--resume` to restart from last successful point
- Retry with exponential backoff and jitter to avoid thundering herd
- Distinguish retryable errors (network timeout, 429, 503) from non-retryable (401, 404, 400)
- Use MERGE/upsert instead of INSERT to make write operations safe to retry

## 16. Testing

- Test the binary as a black box: spawn the actual compiled executable, assert on stdout, stderr, and exit code
- Layer tests: unit (parsing/validation logic) → integration (full command execution) → E2E (multi-step workflows)
- Snapshot test stdout/stderr output for format stability — catches unintentional breaking changes to scripts
- Test both TTY and non-TTY modes (`--json`, `--quiet`, suppressed prompts)
- Test edge cases: no arguments, `--help`, invalid flags, `-` for stdin, `--dry-run`
- Mock filesystem and network at the integration boundary (temp directories, fixture files)
- Run matrix builds in CI: Linux, macOS, Windows
- JSON output schema is API — run contract tests to detect field changes

## 17. Versioning and Breaking Changes

- Use SemVer: MAJOR = breaking, MINOR = new features, PATCH = bug fixes
- Breaking changes: removing/renaming flags or subcommands, changing default behavior, changing JSON schema, changing exit codes
- Not breaking: adding flags/subcommands, adding JSON fields, improving human-readable messages
- Deprecate before removing: print warning to stderr (not stdout), keep working for at least one minor version, include migration guidance
- Version JSON output schemas explicitly (`{"version": 2, "data": {...}}`)
- Maintain CHANGELOG.md with Added/Changed/Deprecated/Removed/Fixed/Security sections
- Keep "golden" tests that exercise documented previous-version behavior

## 18. Performance

- Target sub-100ms startup; sub-50ms feels instant
- Defer heavy imports to command handlers — not module top-level (highest-impact single optimization)
- Avoid all network calls on startup (update checks, telemetry, config fetches)
- Lazy-load plugins; never initialize all plugins for every invocation
- Treat startup performance regressions as build failures — measure in CI with a time budget
- Print something within 100ms for long-running operations; print progress within 500ms

## 19. Distribution and Packaging

- Ship prebuilt single-file binaries for all targets (linux-x64, linux-arm64, darwin-x64, darwin-arm64, win-x64)
- Publish SHA-256 checksums for every artifact; sign with GPG/PGP or Sigstore/Cosign
- For npm: use wrapper + optional platform packages pattern; avoid postinstall download scripts
- GitHub Releases as universal baseline; automate publishing via CI on tag push
- Publish to channels where users already are; diminishing returns after ~3 channels
- Implement `tool update` with checksum verification and rollback (keep previous binary as backup)
- Respect package manager installs — `tool update` should warn if installed via Homebrew/apt

## 20. Plugin and Extension Systems

- Five core responsibilities: discovery → loading → registration → lifecycle → isolation
- Discovery: naming-convention packages (`tool-plugin-*`), explicit config entries
- Clear contract: plugin exports `{name, version, commands?, hooks?, config?}`
- Hook-based lifecycle: `init`, `beforeCommand`, `afterCommand`, `error`, `shutdown`
- Validate plugin exports against contract at load time; reject invalid; warn on unknown hooks
- Isolation levels (increasing safety): in-process → module isolation → process isolation → WASM sandbox
- Lazy-load plugins: discover at startup, initialize only when the relevant command runs

## 21. AI-Agent-Friendly Design

- JSON output with stable, versioned schemas — non-negotiable for agent consumption
- Consistent envelope: `{"status":"ok","data":{...}}` or `{"error":{"code":"...","message":"...","suggestion":"..."}}`
- Schema introspection: `tool --schema` returns JSON schema of inputs/outputs for agent discovery
- Deterministic, non-interactive by default — never hang waiting for stdin when piped
- Terse, action-oriented output — agents pay per token; verbose decorative output wastes context window
- Structured errors with the exact fix command in the `suggestion` field
- `--dry-run` for pre-validation before committing to execution
- Idempotent operations — running a command twice is safe
- Batch operations to reduce round-trips
- Dual-interface pattern: CLI for deterministic automation/CI; MCP for conversational agent integration

## 22. Telemetry

- No data collection without explicit user consent
- Opt-in preferred; if opt-out, make disabling trivial (`tool telemetry disable`)
- Disclose what is collected and where it is sent
- Non-blocking: telemetry must never delay startup or command execution
- Auto-disable in CI/non-interactive environments
