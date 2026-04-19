---
name: free-disk-space
description: This skill should be used when the user needs to free up disk space on a developer machine, clean development caches, or troubleshoot disk full errors. Also use when scanning for bloat directories like node_modules, virtual environments (.venv, venv), or build caches. Triggers on mentions of "free disk space", "disk full", "clean cache", "no space left on device", "find node_modules", "find virtual environments", "scan for bloat", disk cleanup, reclaim space, or storage management on dev desktops or Mac laptops.
---

# Free Disk Space

Guide for reclaiming disk space on developer machines (Mac and Linux). Covers standard package manager caches, IDE build artefacts, and Docker.

**Not covered:** Removing application data, databases, or user files — only regenerable caches and build artefacts.

## Diagnosis

Check overall disk usage before and after cleanup:

```bash
# Show filesystem usage
df -h

# Show top space consumers in current directory
du -sh * | sort -rh | head -20

# Show top space consumers from home directory
du -sh ~/* | sort -rh | head -20
```

## Safety Rules

**Before running any cleanup:**

- Use `scripts/clean_caches.py` as the unified entry point — it covers both CLI-managed caches (npm, pip, yarn, pnpm, go, brew, docker, etc.) and directory caches (Maven, Gradle, JetBrains, etc.)
- Always run the script without `--apply` first to review sizes, then with `--apply` to perform deletion
- NEVER run raw `rm -rf` on cache directories manually; the script handles safety checks
- The manual CLI commands in this file are for reference only — the script invokes them internally

## The Cleanup Script

`scripts/clean_caches.py` is the primary cleanup tool. It covers all cache types — CLI-managed (npm, pip, yarn, pnpm, go, brew, docker, etc.), directory-based (Maven, Gradle, JetBrains, etc.), and scan-based (node_modules under a given root).

```bash
# Step 1: Report all cache sizes without deleting anything
python3 ${SKILL_DIR}/scripts/clean_caches.py

# Step 2: Clean everything
python3 ${SKILL_DIR}/scripts/clean_caches.py --apply

# Step 3: (Special cases) Clean only specific targets
python3 ${SKILL_DIR}/scripts/clean_caches.py --apply --target maven gradle
```

The script reports sizes and then confirms before deleting. The `--target` flag is for special cases where only specific caches need cleaning.

### Scan-based targets (require `--scan-root`)

Scan targets recursively find directories by name under a given root and delete them. They are **opt-in only** — not included in the default run.

| Target | Scans for | Notes |
|--------|-----------|-------|
| `node_modules` | All `node_modules` directories | Does not descend into matched dirs (no double-counting) |

```bash
# Report node_modules under ~/projects (no deletion)
python3 ${SKILL_DIR}/scripts/clean_caches.py --target node_modules --scan-root ~/projects

# Delete all found node_modules directories
python3 ${SKILL_DIR}/scripts/clean_caches.py --apply --target node_modules --scan-root ~/projects
```

## The Bloat Scanner

`scripts/scan_bloat.py` scans a directory tree for known bloat directories (virtual environments, dependency caches, build caches). It reports paths and sizes — it does not delete anything.

```bash
# Scan ~/projects and print a human-readable table
python3 ${SKILL_DIR}/scripts/scan_bloat.py --path ~/projects --human

# Scan and write structured JSON output
python3 ${SKILL_DIR}/scripts/scan_bloat.py --path ~/projects --output /tmp/bloat.json

# Both: JSON to file and table to stdout
python3 ${SKILL_DIR}/scripts/scan_bloat.py --path ~/projects --output /tmp/bloat.json --human

# Filter to directories >= 100MB, sorted by name
python3 ${SKILL_DIR}/scripts/scan_bloat.py --path ~/projects --min-size 100M --sort name --human

# Avoid crossing filesystem boundaries (e.g. NFS mounts)
python3 ${SKILL_DIR}/scripts/scan_bloat.py --path ~/projects --same-filesystem --human
```

### Scanned patterns

| Pattern | Purpose |
|---------|---------|
| `node_modules` | npm/yarn/pnpm dependencies |
| `.venv` | Python virtual environment (PEP convention) |
| `venv` | Python virtual environment (common convention) |
| `.virtualenv` | virtualenv tool default |
| `.next` | Next.js build cache |
| `.nuxt` | Nuxt.js build cache |
| `.tox` | tox testing environments |
| `.turbo` | Turborepo cache |

The scanner does not descend into matched directories (so nested `node_modules` inside `node_modules` are not double-counted).

### Output flags

| Flag | Description |
|------|-------------|
| `--path PATH` | **(Required)** Root directory to scan |
| `--output FILE` | Write JSON results to FILE (default: stdout if no --human) |
| `--human` | Print a formatted table to stdout |
| `--sort size\|name` | Sort by size (default) or alphabetically by path |
| `--min-size SIZE` | Filter out directories below SIZE (e.g. `10M`, `1G`) |
| `--same-filesystem` | Don't cross filesystem boundaries |

### CLI-managed caches (invoked by the script)

| Target | What it runs | Notes |
|--------|-------------|-------|
| `npm` | `npm cache clean --force` | npm cache (`~/.npm`) |
| `pip` | `pip cache purge` | pip cache (`~/.cache/pip` or `~/Library/Caches/pip`) |
| `yarn` | `yarn cache clean` | Yarn cache |
| `pnpm` | `pnpm store prune` | pnpm store |
| `go` | `go clean -cache && go clean -modcache` | Go build and module caches |
| `brew` | `brew cleanup --prune=all` | Homebrew cache (`~/Library/Caches/Homebrew`) |
| `rustup` | manual only | Lists unused toolchains — must remove manually with `rustup toolchain remove <name>` |
| `docker` | `docker system prune --force` | Stopped containers, dangling images, build cache |

### Directory caches (deleted directly by the script)

| Target | Paths | Notes |
|--------|-------|-------|
| `claude-code-debug` | `~/.claude/debug` | Claude Code debug logs |
| `maven` | `~/.m2/repository` | Java dependency cache; rebuilt on next `mvn` build |
| `gradle` | `~/.gradle/caches`, `~/.gradle/wrapper/dists` | Java build cache; rebuilt on next `gradle` build |
| `jetbrains` | `~/Library/Caches/JetBrains` (Mac) | IDE index and plugin caches; rebuilt on IDE restart |
| `xcode` | `~/Library/Developer/Xcode/DerivedData` | Build intermediates; rebuilt on next Xcode build |
| `vscode` | `~/Library/Application Support/Code/Cache`, `CachedData`, `CachedExtensions` | Extension and data caches |

## Quick Reference

The fastest path to a clean machine:

```bash
# 1. Report what can be freed (no changes made)
python3 ${SKILL_DIR}/scripts/clean_caches.py

# 2. Clean everything
python3 ${SKILL_DIR}/scripts/clean_caches.py --apply
```
