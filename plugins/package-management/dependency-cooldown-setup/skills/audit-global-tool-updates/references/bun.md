# Bun

**Config:**
- **Global config (~/.config/bun/bunfig.toml):** `[install] minimumReleaseAge = 259200` (3 days in seconds)
- **CLI override:** `bun install --minimum-release-age=259200`
- **Setting:** `minimumReleaseAge` (seconds)
- **Note:** Value in **seconds** (259200 = 3 days).

**Global tool detection:**

```bash
# List all globally installed packages with versions
bpm list -g --json

# Check latest version of a specific package
bun pm ls --json

# Get package info for version comparison
bun pm info <package> --json
```

**Update a global tool:**

```bash
bun add -g <package>@latest
```
