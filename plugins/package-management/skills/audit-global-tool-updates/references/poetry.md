# Poetry

**Config:**
- **Project config (pyproject.toml):** `[tool.poetry.solver] min-release-age = 10080`
- **Global config via CLI:** `poetry config solver.min-release-age 10080`
- **Global config file (~/.config/pypoetry/config):** `[solver] min-release-age = 10080`
- **Setting:** `solver.min-release-age` (minutes) + `solver.min-release-age-exclude` (names) + `solver.min-release-age-exclude-source`
- **Note:** Value in **minutes** (10080 = 7 days).

**Global tool detection:**

```bash
# List globally installed Poetry-managed tools
poetry self show --json

# Check latest version of a specific package
poetry show <package> --latest

# Get package info for version comparison
pip index versions <package>
```

**Update a global tool:**

```bash
poetry self add <package>@latest
```
