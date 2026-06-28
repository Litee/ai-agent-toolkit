---
name: audit-global-tool-updates
description: Use when scanning the globally installed CLI tools on a machine (across npm, pnpm, Yarn, Bun, Deno, uv, pip, Poetry, Cargo) for available updates and reviewing each upgrade before applying it. This is the fleet-wide counterpart to a single-app audit — it enumerates what is installed globally, finds which tools are outdated, and produces a per-tool SAFE/REVIEW/BLOCK verdict. Triggers on "what global CLI tools can I update", "audit my globally installed tools", "are my global tools safe to upgrade". Read-only; never updates anything without confirmation.
---

# Global Tool Update Auditor

Scans the globally installed CLI tools across package managers, detects which have updates available, and produces a security-reviewed verdict per tool before any upgrade. This is the **fleet-scan** entry point: it answers *"across everything I have installed globally, what's updatable and is each update safe?"* — as opposed to auditing one named application.

> **Rule:** Never auto-update. Always produce a report with a verdict (SAFE / REVIEW / BLOCK) per tool and ask for human confirmation before proceeding.

## 1. Scan — enumerate globally installed tools

Query each package manager present on the machine for its globally installed packages and versions. See the per-manager reference files for the exact enumerate / check-latest / update commands:

- **npm**: `${SKILL_DIR}/references/npm.md`
- **pnpm**: `${SKILL_DIR}/references/pnpm.md`
- **Yarn**: `${SKILL_DIR}/references/yarn.md`
- **Bun**: `${SKILL_DIR}/references/bun.md`
- **Deno**: `${SKILL_DIR}/references/deno.md`
- **uv**: `${SKILL_DIR}/references/uv.md`
- **pip**: `${SKILL_DIR}/references/pip.md`
- **Poetry**: `${SKILL_DIR}/references/poetry.md`
- **Cargo**: `${SKILL_DIR}/references/cargo.md`
- **Bundler/RubyGems**: `${SKILL_DIR}/references/bundler.md`

Only probe managers that are actually installed — a missing manager is not a finding.

## 2. Check for updates

For each installed tool, query the registry for the latest version (commands in the reference files) and compare installed vs. latest. Keep only the tools with a newer version available; those are the upgrade candidates.

## 3. Review each candidate upgrade

For each tool with an update available, you have two version points (installed → latest). Review the change between them by **delegating to the dedicated audit skills** rather than re-deriving the checks here:

- **Run the `review-supply-chain-risk` skill** (in the `software-management` plugin) over the diff between the installed and latest versions — it flags install hooks, obfuscation, exfiltration, new binaries, weakened release pipelines, and dangerous code patterns, and returns a SAFE/REVIEW/BLOCK score. If you cannot obtain a source diff for a registry-only package, review the published tarball contents (extract both versions and diff) and feed that to the same skill.
- **Run the `audit-dependency-advisories` skill** (in the `software-management` plugin) on the tool itself and on any dependency it pulls in — it cross-checks GitHub Advisory Database / OSV and flags any version published less than 72 hours ago (`FRESH`).

Do not reconstruct those checklists from memory — invoke the skills so the analysis stays complete and current.

## 4. Report — produce a per-tool verdict

For each updatable tool, produce a concise report combining the two skills' signals:

```
📦 <package-name> (<manager>): <current> → <latest>
  Changes:  <summary of key changes>
  Advisory: <GHSA/CVE/OSV id or none>  |  Freshness: <age or FRESH>
  Verdict:  SAFE | REVIEW | BLOCK
  Reason:   <brief explanation>
```

Verdict meanings:
- **SAFE** — no suspicious changes, no advisory, not fresh. Safe to approve.
- **REVIEW** — minor changes flagged for human attention (new deps, changed scripts, a `FRESH` version, a medium-severity issue). Approve with caution.
- **BLOCK** — high-risk changes (new executables, obfuscated code, permission changes, a critical/high advisory in range). Do not approve.

## 5. Confirm — ask for human approval

Present the report. Ask for confirmation per tool. Block `BLOCK` verdicts automatically. For `REVIEW`, let the human drill into specifics before approving. Apply approved updates only after explicit confirmation, using the update commands in the reference files.

## Related Skills

- **`review-supply-chain-risk`** (`software-management`) — does the per-upgrade malware/tampering/vulnerability review this skill delegates to.
- **`audit-dependency-advisories`** (`software-management`) — does the advisory + <72h freshness check this skill delegates to.
- **`audit-software-upgrade`** (`software-management`) — the single-application counterpart: deep audit of one named app's upgrade. Use it when the user names a specific tool; use *this* skill to sweep the whole installed fleet.
- **`configure-dependency-cooldown`** (`package-management`) — the preventative complement: delays installing newly published versions so `FRESH` releases are never picked up in the first place.
