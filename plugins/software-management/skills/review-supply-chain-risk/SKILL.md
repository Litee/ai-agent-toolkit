---
name: review-supply-chain-risk
description: Use when reviewing a code change set — a git diff, a commit range, a pull request, or an extracted package/release tarball — for malware, supply-chain tampering, and critical/high vulnerabilities. Triggers on "review this diff/PR for malware", "check this commit range for supply-chain risk", "is this tarball safe", "audit these changes for tampering". Reviews only — does not fetch, install, build, or modify anything.
---

# Review Supply-Chain Risk

This skill reviews a change set — a git diff, a commit range, a pull request, or an extracted package/release tarball — for malware and supply-chain tampering, and for critical/high security vulnerabilities. It emits prioritized risk signals and a SAFE/REVIEW/BLOCK score. This skill reviews only — it does not fetch, clone, install, or modify anything.

## Inputs

The change set to review: diff text, a `<base>..<head>` range in a local clone, a PR, or an extracted tarball directory.

Apply this to every commit / file in the change set under review. Goal: detect **malware / supply-chain tampering** and **critical/high security vulnerabilities** introduced by the change set.

Review by priority. The highest-risk changes are in build, release, and dependency machinery — not application logic.

## Priority 1 — Build, release & install machinery

These run with elevated trust on a developer or CI machine. Scrutinise every change.

- **Install hooks**: `preinstall`, `postinstall`, `install`, `prepare`, `prepublish` scripts (npm); `build.rs` (Rust); `setup.py`/`pyproject` build hooks (Python); Makefile install targets.
- **CI / release workflows**: `.github/workflows/*`, especially anything that publishes artifacts, pushes tags, or touches secrets (`secrets.*`, signing keys, `NPM_TOKEN`, `GH_TOKEN`).
- **Packaging config**: changes to `files`/`bin`/`main`/`exports` (package.json), entry points, or what gets bundled into the released artifact.
- **New committed binaries/blobs**: any binary, `.node`, `.so`, `.dylib`, `.wasm`, minified-only file, or large base64/hex blob added to the tree.

Red flags: a release workflow newly downloads-and-executes a remote script; a postinstall hook added where none existed; signing/checksum steps removed or weakened.

## Priority 2 — Code-level vulnerabilities & malware patterns

Grep the diff and read the surrounding context.

- **Dynamic code execution**: `eval`, `Function(...)`, `exec`, `child_process`, `os.system`, `subprocess` with shell=True, `vm.runInContext`.
- **Obfuscation**: base64/hex/char-code-assembled strings, unusually dense one-liners, string concatenation building URLs or commands.
- **Network egress**: new outbound HTTP(S), DNS, or socket calls — especially to hardcoded IPs/domains, URL shorteners, or paste sites. Telemetry added silently.
- **Secret / credential access**: reads of `~/.ssh`, `~/.aws`, `.env`, keychain, browser profiles, `process.env` exfiltration.
- **Filesystem reach**: writes outside the app's own dirs, modifications to shell profiles (`.bashrc`, `.zshrc`, `.profile`), cron, launchd/systemd units.
- **Injection vulns**: command injection (unsanitised input into shell), path traversal, SQL/template injection, unsafe deserialization (`pickle`, `yaml.load`, `Marshal`).
- **Crypto / transport downgrades**: disabled TLS verification (`rejectUnauthorized: false`, `verify=False`), weakened auth, permission checks removed.

Useful sweep over the diff — replace `<diff-source>` with e.g. `git diff <base>..<head>`, `git show <sha>`, or `cat patch.diff`:

```bash
# <diff-source> is e.g.: git diff <base>..<head>  |  git show <sha>  |  cat patch.diff
<diff-source> | grep -nE \
  "eval\(|Function\(|exec\(|child_process|os\.system|subprocess|vm\.runInContext|base64|atob\(|fromCharCode|pickle|yaml\.load|Marshal|rejectUnauthorized|verify *= *False|http://|https://|\.ssh|\.aws|process\.env"
```

(Manually confirm every hit in context — these patterns have legitimate uses.) An empty result is **not** automatically clean: confirm the `<diff-source>` command actually produced a diff — a bad ref or empty range yields zero hits too.

## Priority 3 — Provenance & maintainership

*(Applies only when you have the repository / git history. For raw diff text, a bare PR patch, or an extracted tarball with no history, Priority 3 is N/A — rely on Priority 1–2.)*

- Commit authors: are sensitive paths (build/release/deps) touched by unfamiliar or first-time contributors?
- Tag integrity: was the reviewed ref/tag (if any) force-pushed or re-pointed? (`git log` of the tag ref).
- Release notes vs. actual diff: do the published notes match what changed? Undocumented changes to sensitive files are a flag.

## Scoring

- **BLOCK** — any credible malware/tampering indicator, an introduced critical/high vulnerability, or a compromised/weakened release pipeline.
- **REVIEW** — plausible-but-unconfirmed concerns: new telemetry, new dependency from an unknown author, medium-severity issue, undocumented behaviour change.
- **SAFE** — only routine changes; nothing in Priority 1–3 raised a concern.

When uncertain, escalate (SAFE → REVIEW → BLOCK), never the reverse.

## Related Skills

- **`audit-dependency-advisories`** — this skill does **not** do dependency advisory/CVE/freshness lookups. When the change set bumps dependencies, run `audit-dependency-advisories` on the changed `name@version`s to cover advisories and <72h freshness.
- **`audit-software-upgrade`** — the full single-app upgrade audit; it invokes this skill over the upgrade's commit range as its commit-review step.
