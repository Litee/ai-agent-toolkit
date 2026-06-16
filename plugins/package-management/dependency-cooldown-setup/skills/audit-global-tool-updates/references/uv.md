# uv

**Config:**
- **Global config (~/.config/uv/uv.toml):** `resolve.exclude-newer = "7 days"`
- **CLI override:** `uv sync --exclude-newer 7days`
- **Setting:** `exclude-newer` (relative duration like `"7 days"`, `"30 days"`, or absolute date)
- **Note:** Accepts relative durations and absolute dates. ISO 8601 (`P7D`) supported.

**Global tool detection:**

```bash
# List all installed packages with versions
uv tool list --format json

# Check latest version of a specific package
uv pip index versions <package>

# Get package info for version comparison
pip index versions <package>
```

**Update a global tool:**

```bash
uv tool install <package>@latest --force
```
