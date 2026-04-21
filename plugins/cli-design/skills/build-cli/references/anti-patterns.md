# CLI Anti-Patterns Reference

Common mistakes organized by category. Each entry includes the problem, why it matters, and the fix.

---

## Output Anti-Patterns

**Mixing stdout and stderr**
Sending progress messages, warnings, or diagnostics to stdout instead of stderr. This breaks piping — any downstream tool parsing stdout gets garbage mixed into the data stream.
Fix: stdout = data only; stderr = everything else.

**No machine-readable output mode**
Only supporting human-readable tables or prose with no `--json` or `--output <format>` option. Forces consumers to parse fragile text.
Fix: Add `--json` that emits a stable, versioned envelope.

**Walls of debug noise by default**
Dumping stack traces, verbose logs, or debug info without the user requesting it. Conversely, zero output for long operations is equally bad — silence feels broken.
Fix: Human-readable summary by default; `--verbose`/`--debug` for detail; acknowledge long operations within 100ms.

**Relying solely on color to convey meaning**
Using red text as the only indicator of failure with no `ERROR:` label. Breaks in CI logs, when piped, for colorblind users, and for screen readers.
Fix: Always pair color with a text label.

**Ignoring `NO_COLOR`**
Hardcoding ANSI color codes without checking `NO_COLOR`, `TERM=dumb`, or whether stdout is a TTY.
Fix: Check all three before emitting ANSI codes; support `--no-color`.

**Decorative ASCII art and borders**
Box-drawing characters and elaborate art break on terminal resize, are unreadable to screen readers, and corrupt piped data.
Fix: No decorative borders in command output.

**Animated spinners without fallback**
Spinners are problematic for screen readers and break in non-TTY contexts.
Fix: Disable spinners when not on a TTY; use a simple percentage or step counter instead.

**Binary output to stdout without explicit request**
Surprising users by dumping binary data when they expected text.
Fix: Only emit binary when explicitly requested (`--output-format=binary` or piping from a dedicated subcommand).

**No output for long-running operations**
Hanging silently for 15+ seconds with no indication that work is happening. Users assume the tool is frozen.
Fix: Print a status line within 100ms; show progress within 500ms.

---

## Error Handling Anti-Patterns

**Cryptic / opaque error messages**
Messages like `InvalidArgs`, `NotFound`, `General failure`, or `Execution failed` with no context.
Fix: State what failed, why, and how to fix it. Include the offending value.

**No remediation guidance**
Stating what went wrong without suggesting how to fix it.
Fix: Every error should end with a concrete next step or doc link.

**Internal jargon in user-facing errors**
Exposing raw backend exception names, internal error codes, or stack traces.
Fix: Catch expected errors and rewrite them in plain language; hide internal details behind `--verbose`.

**Silent failures**
Doing the wrong thing without any indication — skipping files, ignoring invalid flags, or partially completing without reporting.
Fix: Fail loudly and early; validate inputs before starting mutations.

**Failing late after partial work**
Validating input lazily so the tool does half the work, then fails, leaving state corrupted.
Fix: Validate all inputs before executing any side effects.

**Exit 0 on failure**
Exiting with 0 when the command did not succeed. Scripts and CI pipelines depend on non-zero exit codes to detect failure.
Fix: Always exit non-zero on failure; never use 0 for error cases.

**Unstructured machine-readable errors**
Emitting prose-only error messages with no machine-readable error code. Consumers cannot programmatically distinguish auth failures from not-found from timeouts.
Fix: In `--json` mode, return `{"error": {"code": "CATEGORY_ERROR", "message": "..."}}` to stderr.

---

## Flag and Argument Anti-Patterns

**Positional arguments over flags**
Requiring users to memorize argument order.
Fix: Use named flags; reserve positional args for the single most obvious primary target.

**Non-standard flag names**
Inventing `--ver`, `--verb`, `--sil` when well-known conventions exist (`--version`, `--verbose`, `--quiet`).
Fix: Use established flag names; check against the tool's ecosystem conventions.

**Required option ordering**
Failing when options are provided in a different order than expected.
Fix: Options must be order-independent.

**No short aliases for common flags**
Forcing `--verbose` every time instead of also accepting `-v`.
Fix: Provide short forms for flags used frequently (help, verbose, quiet, output, force).

**Requiring JSON or complex data on the command line**
Expecting users to type escaped JSON strings as arguments. AWS CLI is a canonical bad example.
Fix: Accept complex input from files, stdin, or config; not raw command-line strings.

**No `--` separator support**
Not implementing the standard `--` to separate options from arguments, causing problems when arguments look like flags.
Fix: Implement `--`; anything after it is treated as a literal argument.

**Accepting secrets via flags**
Passwords and API tokens passed as `--password=secret` are visible in `ps` output, shell history, and process monitoring.
Fix: Accept secrets via files (`--password-file`), environment variables, stdin prompt, or credential stores.

---

## Interactivity Anti-Patterns

**Mandatory interactive prompts**
Blocking on user input without flag-based alternatives. This kills CI/CD pipelines and automation.
Fix: Every prompt must have a `--flag` equivalent; check isatty() before prompting.

**No `--yes` / `--force` for scripting**
Failing to provide a non-interactive bypass for confirmation prompts.
Fix: Add `--yes` or `--force` to suppress all confirmations.

**No confirmation for destructive actions**
Running `tool delete prod-db` and immediately deleting production data with no confirmation.
Fix: Require explicit confirmation scaled to severity; provide `--dry-run`.

**No `--dry-run` for mutations**
Any command that changes state should have a preview mode that shows what would happen without doing it.
Fix: Add `--dry-run` to every subcommand that creates, modifies, or deletes.

**Surprise prompts in non-interactive tools**
A tool that normally runs non-interactively suddenly asking for input under certain conditions, breaking scripts.
Fix: Check isatty() before ever prompting; use `--no-input` to enforce non-interactive mode.

---

## Consistency Anti-Patterns

**Inconsistent verbs across subcommands**
Using `add/delete` for one resource but `create/remove` for another. "Better to be weird and consistent than perfectly logical but a guessing game."
Fix: Define a verb vocabulary and apply it uniformly.

**Inconsistent flag behavior across subcommands**
A flag meaning one thing under one subcommand and something different under another.
Fix: Flags with the same name must have the same behavior everywhere.

**Mixed naming conventions**
Mixing camelCase, snake_case, and kebab-case in commands and flags.
Fix: Pick kebab-case for multi-word commands/flags and apply universally.

**No standard command structure**
Mixing `tool verb-noun`, `tool noun verb`, and `tool noun-verb` randomly.
Fix: Pick one pattern and document it; enforce it in code review.

---

## Help and Discoverability Anti-Patterns

**No `--help` on subcommands**
Only supporting `--help` at the top level.
Fix: Register `-h`/`--help` on every command and subcommand.

**Help with no examples**
Help output lists flags and types but includes zero usage examples.
Fix: Examples section is mandatory; it is the most-read part of help text.

**No "Did you mean?" suggestions**
Responding to typos with just "invalid subcommand" instead of suggesting the closest match.
Fix: Implement edit-distance suggestion for typos in command and flag names.

**No suggestion of next steps**
After a successful command, not hinting at what the user likely wants to do next.
Fix: Print a one-line "Next:" suggestion after success, especially for onboarding commands.

**Overwhelming help text**
Dumping every possible option at once.
Fix: Show common commands first; use progressive disclosure for advanced options.

---

## Architecture Anti-Patterns

**Mirroring API structure instead of user tasks**
Building a CLI as a 1:1 wrapper around REST endpoints rather than designing around user workflows.
Fix: Design around the tasks users want to accomplish, not the HTTP endpoints that exist.

**Rolling your own argument parser**
Implementing custom command-line parsing from scratch instead of using established libraries.
Fix: Use a battle-tested CLI framework appropriate to your language; they handle edge cases and generate help automatically.

**Implicit side effects**
An `init` command that overwrites existing config without warning; a `log` command that makes network calls; opt-out telemetry.
Fix: Commands should do exactly what their name says; unexpected side effects must be opt-in and documented.

**No configuration hierarchy**
Hardcoding behavior with no way to configure via env vars, config file, or flags.
Fix: Implement the standard precedence: flags > env vars > project config > user config > system config > defaults.

**Binary name conflicts**
Publishing a tool named `run`, `get`, or `build` without checking for conflicts in major package repositories.
Fix: Check `which <name>`, search npm/pip/Homebrew/apt before committing to a name.

---

## Security Anti-Patterns

**Secrets via command-line arguments**
Visible in `ps` output, shell history, and process monitoring.
Fix: Accept secrets via files (`--token-file`), env vars, stdin prompt, or system keychain.

**No credential management**
For SaaS CLIs, not supporting multiple authentication profiles.
Fix: Support named profiles; provide `tool auth status` and `tool auth login --profile <name>`.

**Opt-out telemetry without disclosure**
Collecting usage data without informing users or providing easy opt-out.
Fix: Opt-in preferred; if opt-out, provide `tool telemetry disable` and disclose what is collected.

---

## Compatibility and Distribution Anti-Patterns

**Not being a good Unix citizen**
Not ending output with a trailing newline, not supporting `-` for stdin, not respecting `$NO_COLOR`, `$EDITOR`, `$PAGER`.
Fix: Follow POSIX conventions; test with `set -e` scripts.

**Slow startup time**
`--help` taking 2+ seconds. Java-style cold starts. Users invoke help frequently; it must be instant.
Fix: Lazy-load imports; no network on startup; budget startup time in CI; target < 100ms.

**No shell completions**
Not providing tab-completion scripts for bash, zsh, fish, PowerShell.
Fix: Generate completions from your CLI schema; ship them with the install.

**Breaking changes without deprecation warnings**
Removing flags or changing behavior without a deprecation period.
Fix: Deprecate first (warn to stderr, keep working); remove only after a major version bump.

**Ambiguous abbreviations that block future growth**
`tool i` meaning `install` today prevents adding `init` tomorrow without a breaking change.
Fix: Do not allow arbitrary prefix abbreviations of subcommands; require exact names.

**Postinstall download scripts for npm packages**
Fragile: breaks behind proxies, in offline CI, with restrictive permissions.
Fix: Use the optional-dependencies pattern (wrapper package + platform-specific optional packages).

---

## Real-World CLI Design Failures (Lessons Learned)

**Git's overloaded `checkout`**
`git checkout` historically meant three unrelated things: switch branch, restore files, create branch. Required splitting into `git switch` and `git restore` decades later after massive user confusion.
Lesson: Don't overload a single command to do multiple unrelated things.

**Docker CLI flat namespace**
Original flat `docker run/stop/rm` namespace became unwieldy as Docker grew, requiring the noun-grouped `docker container run` reorganization.
Lesson: Plan for growth; group commands under nouns from the start.

**AWS CLI requiring inline JSON**
`aws ec2 run-instances --block-device-mappings '[{"DeviceName":"/dev/xvda",...}]'` requires shell-escaped JSON on the command line.
Lesson: Accept complex structured input from files or stdin, not raw command-line strings.

**npm's mixed output streams**
npm historically mixed human-readable and machine-readable output in unpredictable ways, making scripting fragile.
Lesson: Strict stdout/stderr separation is non-negotiable.
