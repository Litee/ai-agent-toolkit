---
name: audit-software-upgrade
description: Use when verifying whether a newer version of a GitHub-hosted installed application is safe to upgrade to, before any install happens. Triggers on "is it safe to update <app>", "review the new version of <app>", "audit the upgrade for <app>", "should I upgrade <app>", or "check <app> before updating". GitHub-hosted apps only; audit-and-report only, never installs.
---

# Audit Software Upgrade

Audit a candidate software upgrade and produce a **verdict** before any installation happens. This skill **never installs anything** — it gathers evidence, reviews the change set for malware and high/critical vulnerabilities, audits third-party dependency changes, evaluates the trust model for the distributed artifact, and reports a `SAFE` / `REVIEW` / `BLOCK` verdict for a human to act on.

> **Rule:** Audit and report only. Do not run installers, package upgrades, `brew upgrade`, `make install`, or any build step. End every run by saving the report to a timestamped file under `/tmp/`, presenting the verdict, and stopping for human confirmation.

## When to use

The user wants to know whether upgrading a specific installed app (e.g. cmux) to a newer version is safe. The app is hosted on **GitHub**. First-version scope is GitHub only.

## Inputs you need

1. **App name** — what is being upgraded.
2. **Current version** — see [Determine versions](#1-determine-current-and-target-versions).
3. **Target version** — the version the user wants to move to (a release tag, or "latest").
4. **App spec** (optional but preferred) — a per-app file under `${SKILL_DIR}/references/apps/` describing the repo, version-detection hints, trust policy, and custom checks. See [App specifications](#app-specifications).

## Workflow

### 1. Determine current and target versions

Resolve the **current** version using this precedence:

1. **Homebrew** — if the app is managed by Homebrew, get everything from brew first. See `${SKILL_DIR}/references/homebrew.md` for detection commands and the cask-vs-formula trust signal.
2. **The app itself** — if not on brew, ask the app for its version:
   ```bash
   <app> --version    # or -v, version, --help
   ```
3. **Ask the user** — if neither works, ask the user to provide both the current and target versions explicitly.

Resolve the **target** version from the user's request, or query GitHub for the latest release (see below). Always confirm the resolved `current → target` pair with the user before doing heavy analysis.

### 2. Identify the GitHub repository

- Prefer the repo declared in the app spec (`${SKILL_DIR}/references/apps/<app>.md`).
- Otherwise derive it from `brew info` source URL, the app's homepage, or ask the user.
- Confirm the repo before fetching.

### 3. Fetch the commit range

Map the current/target **versions** to their **git tags** (versions and tags differ — e.g. `<x.y.z>` vs `v<x.y.z>`), confirm both tags exist, then fetch the commit range and file changes between them — prefer the GitHub CLI (`gh`), fall back to `git`.

See `${SKILL_DIR}/references/github-fetch.md` for the exact `gh` / `git` / `curl` commands. Note: the `gh ... compare` API caps at 250 commits and truncates very large diffs — for a big version jump, fall back to a `git clone` and review by path priority.

### 4. Review every commit for malware and vulnerabilities

**REQUIRED — run the `review-supply-chain-risk` skill** over the commit range. It applies the full malware / supply-chain / vulnerability checklist (install hooks, obfuscation, exfiltration, new binaries, weakened release pipelines, injection/deserialization, provenance red flags) and returns prioritized risk signals plus a per-change SAFE/REVIEW/BLOCK score. Do not reconstruct that checklist from memory here — invoke the skill so the analysis stays complete and current.

Prioritise commits that touch: build/release/CI config, dependency manifests, install hooks, native code, anything dealing with credentials, network, or the filesystem.

### 5. Audit third-party dependency changes

Diff the dependency manifests/lockfiles between versions. Then, **REQUIRED — run the `audit-dependency-advisories` skill** on the **added, removed, or version-bumped** dependencies: it cross-checks advisory databases (GitHub Advisory Database, OSV, native auditors) and flags any version **published less than 72 hours ago** (`FRESH`). Don't reproduce its lookups from memory — invoke it.

Record every dependency in the per-dependency table (see step 8) with its old→new version and per-dependency verdict, so the result can be reused by a future multi-app sweep.

### 6. Check source-vs-artifact divergence

When the upgrade will install a **prebuilt artifact** (release binary, tarball, DMG, brew cask) rather than building from the reviewed source, compare the artifact against the reviewed source tree and flag anything present in the artifact but absent from / inconsistent with the git source — extra files, unexpected binaries, post-build code injection. This is a classic supply-chain hiding spot: the published artifact contains code not in the repo. If the artifact cannot be directly compared to source (e.g. a compiled binary), say so explicitly and treat unverifiable divergence as at least a `REVIEW`.

### 7. Decide trust: prebuilt binary vs build from source

Each app spec declares a **trust policy**. Honour it; the human may override.

- **`TRUST_RELEASE_BINARY`** — the provider's signed release artifact is trusted. Verify provenance before recommending: checksum match against the published checksum, signature/notarization, and that the artifact came from the same release tag you audited. See `${SKILL_DIR}/references/trust-and-build.md`.
- **`BUILD_FROM_SOURCE`** — do not trust prebuilt binaries; the human should build and install from the reviewed source. Surface the documented build steps from the spec so the human can run them after approval (this skill does not run them).

If no spec exists, present the evidence (is it signed? reproducible? same provenance as the audited tag?) and recommend a policy, but let the human choose.

### 8. Produce the verdict

Assemble the report in this format:

```
🔎 <app>: <current> → <target>   (repo: <owner>/<repo>)
  Commits reviewed: <N>   Range: <current-tag>..<target-tag>
  Malware / tampering: <none | findings>
  Critical/high vulns: <none | findings>
  3P dependency changes: <summary; advisories found; any FRESH (<72h) versions>
  Dependencies reviewed:
    | dependency | ecosystem | old → new | advisory | freshness | verdict |
    |------------|-----------|-----------|----------|-----------|---------|
    | <name>     | <eco>     | <a → b>   | <none|GHSA-…> | <age; FRESH?> | SAFE|REVIEW|BLOCK |
  (Per-dependency verdicts above are reusable by a future multi-app sweep.)
  Source-vs-artifact: <none | divergence found>
  Trust policy: TRUST_RELEASE_BINARY | BUILD_FROM_SOURCE
  Artifact provenance: <checksum/signature status, or build steps>
  ─────────────────────────────────────────────
  Verdict: SAFE | REVIEW | BLOCK
  Reason: <brief explanation>
  Next step (human action, not run by this skill): <upgrade command or build steps>
```

**Save the report to a timestamped file before presenting it.** A full audit is expensive to produce and easy to lose to a truncated response or a crash — persist it so it survives. Write the complete report (the block above plus the supporting detail you gathered — per-commit notes, dependency findings, provenance evidence) to:

```bash
REPORT="/tmp/audit-software-upgrade-<app>-$(date -u +%Y%m%dT%H%M%SZ).md"
# write the full report to "$REPORT"
```

Use a UTC timestamp (`%Y%m%dT%H%M%SZ`) to avoid clashes across runs. Sanitise `<app>` to a filesystem-safe slug (lowercase, non-alphanumerics → `-`). Then present the report inline **and** tell the human the saved path, e.g. `Full report saved to /tmp/audit-software-upgrade-cmux-20260623T141502Z.md`.

> Tip: for a long audit, write a partial report to this file incrementally as you complete each step (versions resolved → commits reviewed → deps audited → trust evaluated), so a mid-analysis interruption still leaves the work-so-far on disk. Overwrite the same timestamped path each time.

Verdict meanings:

- **SAFE** — No malware, no critical/high vulns, dependency changes clean (no advisories, nothing published < 72h ago), artifact provenance verified per policy. Safe for the human to upgrade.
- **REVIEW** — Minor concerns a human should weigh (new low/medium-risk deps, a freshly-published <72h dependency version, new authors, unverified-but-plausible provenance). Drill into specifics before approving.
- **BLOCK** — Malware indicators, critical/high vulnerability, compromised release pipeline, or unverifiable provenance. Do **not** upgrade.

### 9. Stop for human confirmation

Always end here. Do not perform the upgrade. Auto-block `BLOCK` verdicts. For `REVIEW`, let the human inspect the flagged items before deciding. Make sure the saved report path from step 8 is surfaced so the human can revisit the full analysis later.

## App specifications

Per-app config lives in `${SKILL_DIR}/references/apps/`, one markdown file per app (e.g. `cmux.md`). A spec declares the repo, how to detect the installed version, the trust policy, build steps (for `BUILD_FROM_SOURCE`), and any **custom checks** specific to that app. The agent reads and reasons over the spec.

- Template: `${SKILL_DIR}/references/apps/_template.md`
- Worked example: `${SKILL_DIR}/references/apps/cmux.md`

To support a new app, copy the template and fill it in. If no spec exists for the requested app, run the generic workflow and ask the user for the missing details (repo, trust preference, special checks).

## Related Skills

This skill composes two sibling skills in the same plugin — invoke them by name at the steps above:

- **`review-supply-chain-risk`** — applies the malware / supply-chain red-flag checklist to the commit range (step 4). Also usable standalone to review any diff, PR, or tarball.
- **`audit-dependency-advisories`** — advisory (GHSA/OSV) + <72h freshness checks for changed dependencies (step 5). Also usable standalone to vet a single package or a lockfile.

Related, in the `package-management` plugin:
- **`configure-dependency-cooldown`** — proactively delays installing newly published dependency versions (the preventative complement to this skill's freshness check).

## Reference files

- Homebrew version detection & trust signal: `${SKILL_DIR}/references/homebrew.md`
- GitHub target-version & commit-range fetch: `${SKILL_DIR}/references/github-fetch.md`
- Trust model & build-from-source verification: `${SKILL_DIR}/references/trust-and-build.md`
- Per-app specs (template + examples): `${SKILL_DIR}/references/apps/`

Delegated analysis lives in sibling skills (see Related skills): `review-supply-chain-risk` and `audit-dependency-advisories`.
