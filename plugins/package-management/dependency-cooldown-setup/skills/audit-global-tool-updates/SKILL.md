---
name: audit-global-tool-updates
description: Use when scanning globally installed CLI tools across package managers for available updates, analyzing version diffs, and reviewing security implications before upgrading. Triggers on requests to audit, review, or safely update globally installed CLI tools.
---

# Global Tool Update Auditor

Scans globally installed CLI tools across package managers, detects available updates, diffs changes, and provides security-reviewed verdicts before any upgrade.

> **Rule:** Never auto-update. Always produce a report with a verdict (SAFE / REVIEW / BLOCK) and ask for human confirmation before proceeding.

## Workflow

### 1. Scan — Detect Globally Installed Tools

Query the registry for each package manager to find globally installed packages and their versions. See reference files for the exact commands:

- **npm**: `${SKILL_DIR}/references/npm.md`
- **pnpm**: `${SKILL_DIR}/references/pnpm.md`
- **Yarn**: `${SKILL_DIR}/references/yarn.md`
- **Bun**: `${SKILL_DIR}/references/bun.md`
- **Deno**: `${SKILL_DIR}/references/deno.md`
- **uv**: `${SKILL_DIR}/references/uv.md`
- **pip**: `${SKILL_DIR}/references/pip.md`
- **Poetry**: `${SKILL_DIR}/references/poetry.md`
- **Cargo**: `${SKILL_DIR}/references/cargo.md`

### 2. Check for Updates

For each installed tool, query the registry for the latest version. Compare installed version vs. latest.

### 3. Diff — Analyze Changes

For tools with new versions, fetch and diff the changes:
- Extract the registry tarball for both versions
- Compare `package.json`, `bin/`, `scripts/`, and all source files
- Use `${SKILL_DIR}/references/security-checks.md` for the security review checklist

### 4. Report — Produce Verdict

For each updatable tool, produce a concise report:

```
📦 <package-name>: <current> → <latest>
  Changes: <summary of key changes>
  Verdict: SAFE | REVIEW | BLOCK
  Reason: <brief explanation>
```

Verdict meanings:
- **SAFE** — No suspicious changes. Safe to approve.
- **REVIEW** — Minor changes flagged for human attention (new deps, changed scripts). Approve with caution.
- **BLOCK** — High-risk changes (new executables, obfuscated code, permission changes). Do not approve.

### 5. Confirm — Ask for Human Approval

Present the report. Ask for confirmation per tool. Block BLOCK verdicts automatically. For REVIEW, let the human drill into specifics before approving.

## Security Review Checklist

Use `${SKILL_DIR}/references/security-checks.md` to examine diffs for:

- New/changed `bin` scripts or entry points
- New dependencies (especially devDependencies → dependencies)
- Changes to `package.json` fields (`files`, `main`, `exports`, `scripts`)
- New files (especially build scripts, pre/post-install hooks)
- Obfuscated code, eval/exec calls, network requests
- Permission or environment changes

## Reference Files

For detection commands and update-check queries per package manager:

- **npm**: `${SKILL_DIR}/references/npm.md`
- **pnpm**: `${SKILL_DIR}/references/pnpm.md`
- **Yarn**: `${SKILL_DIR}/references/yarn.md`
- **Bun**: `${SKILL_DIR}/references/bun.md`
- **Deno**: `${SKILL_DIR}/references/deno.md`
- **uv**: `${SKILL_DIR}/references/uv.md`
- **pip**: `${SKILL_DIR}/references/pip.md`
- **Poetry**: `${SKILL_DIR}/references/poetry.md`
- **Cargo**: `${SKILL_DIR}/references/cargo.md`
- **Security checks**: `${SKILL_DIR}/references/security-checks.md` (NEW)
