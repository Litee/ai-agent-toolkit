# pnpm

**Config:**
- **Global config (~/.npmrc):** `minimumReleaseAge=10080`, `minimumReleaseAgeExclude=webpack,react,typescript`
- **CLI override:** `pnpm install --minimum-release-age=10080`
- **Setting:** `minimumReleaseAge` (minutes) + `minimumReleaseAgeExclude` (names)
- **Note:** Applies to direct and transitive dependencies. Value in **minutes** (10080 = 7 days).

**Global tool detection:**

```bash
# List all globally installed packages with versions
pnpm list -g --depth=0 --json

# Check latest version of a specific package
pnpm view <package>@latest version

# Get package info for version comparison
pnpm view <package> versions --json
```

**Update a global tool:**

```bash
pnpm add -g <package>@latest
```
