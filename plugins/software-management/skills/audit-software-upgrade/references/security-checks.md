# Commit Security Review Checklist

Apply this to every commit in the `current-tag..target-tag` range. Goal: detect **malware / supply-chain tampering** and **critical/high security vulnerabilities** introduced by the upgrade.

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

Useful sweeps over the diff:

```bash
git diff <current-tag>..<target-tag> | grep -nE \
  "eval\(|exec\(|child_process|os\.system|subprocess|base64|atob\(|fromCharCode|rejectUnauthorized|verify *= *False|http://|https://|\.ssh|\.aws|process\.env"
```

(Manually confirm every hit in context — these patterns have legitimate uses.)

## Priority 3 — Provenance & maintainership

- Commit authors: are sensitive paths (build/release/deps) touched by unfamiliar or first-time contributors?
- Tag integrity: was the target tag force-pushed or re-pointed? (`git log` of the tag ref).
- Release notes vs. actual diff: do the published notes match what changed? Undocumented changes to sensitive files are a flag.

## Scoring

- **BLOCK** — any credible malware/tampering indicator, an introduced critical/high vulnerability, or a compromised/weakened release pipeline.
- **REVIEW** — plausible-but-unconfirmed concerns: new telemetry, new dependency from an unknown author, medium-severity issue, undocumented behaviour change.
- **SAFE** — only routine changes; nothing in Priority 1–3 raised a concern.

When uncertain, escalate (SAFE → REVIEW → BLOCK), never the reverse.
