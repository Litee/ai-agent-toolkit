---
name: configure-dependency-cooldown
description: Use when configuring dependency cooldowns across package managers to delay installation of newly published versions. Triggers on requests to set up cooldowns for npm, pnpm, Yarn, Bun, Deno, uv, pip, Poetry, Bundler, or Cargo.
---

# Dependency Cooldown Configuration

A dependency cooldown delays installation of newly published package versions, giving the community and security vendors time to flag problems before automated tooling pulls them into your project. Most supply chain attacks have a window of opportunity under a week — a 7-day cooldown would have blocked most of them.

## Quick Reference

| Manager | Global Config Path | Project Config File |
|---------|-------------------|---------------------|
| **pnpm** | `~/.npmrc` | `.npmrc` or `pnpm-workspace.yaml` |
| **npm** | `~/.npmrc` | `.npmrc` |
| **Yarn** | `~/.yarnrc.yml` | `.yarnrc.yml` |
| **Bun** | `~/.config/bun/bunfig.toml` | `bunfig.toml` |
| **Deno** | N/A (project-level only) | `deno.json` / `deno.jsonc` |
| **uv** | `~/.config/uv/uv.toml` | `pyproject.toml` or `uv.toml` |
| **pip** | `~/.config/pip/pip.conf` | N/A (CLI only) |
| **Poetry** | `~/.config/pypoetry/config` | `pyproject.toml` |
| **Bundler** | `~/.bundle/config` | `.bundle/config` or Gemfile |

For detailed configuration examples, CLI overrides, and per-manager gotchas, read the reference files:

- **npm**: `${SKILL_DIR}/references/npm.md`
- **pnpm**: `${SKILL_DIR}/references/pnpm.md`
- **Yarn**: `${SKILL_DIR}/references/yarn.md`
- **Bun**: `${SKILL_DIR}/references/bun.md`
- **Deno**: `${SKILL_DIR}/references/deno.md`
- **uv**: `${SKILL_DIR}/references/uv.md`
- **pip**: `${SKILL_DIR}/references/pip.md`
- **Poetry**: `${SKILL_DIR}/references/poetry.md`
- **Bundler**: `${SKILL_DIR}/references/bundler.md`
- **Cargo**: `${SKILL_DIR}/references/cargo.md`

## Decision Framework

1. **Identify the package manager** — language (npm/pnpm/Yarn/Bun/Deno/uv/pip/Poetry/Bundler/Cargo).
2. **Choose global vs. project** — global configs apply to all projects; project configs apply to one.
3. **Pick a cooldown duration** — 7 days is the recommended default (blocks most supply-chain attacks). Shorter (3 days) for fast-moving ecosystems; longer (14 days) for high-security contexts.
4. **Configure the setting** — see the relevant reference file for the exact config key and format.
5. **Handle exemptions** — pin critical packages (react, webpack, framework deps) to the exclude list so your own projects don't stall.

## Key Concepts

### Relative Duration vs. Absolute Timestamp

- **Relative** (7 days, P7D, 10080 min, 259200 sec) — sliding window that always excludes recent publishes. Best for security cooldowns.
- **Absolute** (2026-06-07) — pins resolution to a moment in time. Best for reproducible builds.

### Unit Differences

- **Minutes**: pnpm, Yarn, Poetry, Deno (plain integer)
- **Days**: npm, Bundler
- **Seconds**: Bun (259200 = 3 days)
- **Duration strings**: uv ("7 days"), pip ("P7D")

### What to Watch

- Most registries have a single upload timestamp — cooldowns are a pure client-side filter.
- npm's `time` field only appears in the full packument (not the abbreviated response), so enabling cooldowns means pulling multi-megabyte JSON files for popular packages.
- RubyGems' compact index doesn't carry timestamps — Bundler reads `created_at` from the dependency API endpoint.

### System vs. Language Package Managers

- **Language managers** (npm, pip, gems, crates.io): Cooldowns retrofit a review window onto ecosystems that never had one.
- **System managers** (apt, brew, Fedora): Already have human review + CI pipelines. Cooldowns are unnecessary.

## Still Waiting (No Native Support)

Go, Composer (PHP), Dart, Conda, Maven/Gradle (Java), Swift Package Manager — no cooldown discussion or implementation found. NuGet has open issues but Dependabot already supports cooldowns for it.
