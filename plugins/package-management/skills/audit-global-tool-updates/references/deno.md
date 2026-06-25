# Deno

**Config:**
- **Project config (deno.json):** `"minimumDependencyAge": "10080"`
- **CLI override:** `deno install --minimum-dependency-age=10080`
- **Setting:** `minimumDependencyAge` (minutes, ISO-8601 duration, or RFC3339 timestamp)
- **Note:** Applies to `deno update` and `deno outdated`. Works with JSR and npm packages.

**Duration formats:** plain integer (minutes), ISO-8601 (`"P7D"`), RFC3339 (`"2025-09-16"`).

**Global tool detection:**

```bash
# List all globally installed (imported) packages
deno info --json

# Check latest version of a specific package
deno info <package-url> --json

# Get version info from registry
curl -s https://registry.npmjs.org/<package>/latest | jq '.version'
```

**Update a global tool:**

```bash
deno install --allow-read --allow-write -g <package>@latest
```
