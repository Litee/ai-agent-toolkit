# npm

**Config:**
- **Global config (~/.npmrc):** `minimum-release-age=3`, `minimum-release-age-exclude[]=webpack`
- **CLI override:** `npm install --minimum-release-age=3`
- **Setting:** `minimum-release-age` (days) + `minimum-release-age-exclude` (names or minimatch globs)
- **Note:** Value in **days**. If both `before` and `min-release-age` are set, `before` wins.

**Global tool detection:**

```bash
# List all globally installed packages with versions
npm ls -g --depth=0 --json

# List outdated global packages
npm outdated -g --json

# Check latest version of a specific package
npm view <package>@latest version

# Get package info for version comparison
npm view <package> versions --json
```

**Update a global tool:**

```bash
npm update -g <package>
# or
npm install -g <package>@latest
```
