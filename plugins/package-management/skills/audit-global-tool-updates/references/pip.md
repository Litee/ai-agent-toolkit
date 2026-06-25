# pip

**Config:**
- **Global config (~/.config/pip/pip.conf):** `[install] uploaded-prior-to = P7D`
- **CLI override:** `pip install --uploaded-prior-to=P7D .`
- **Setting:** `uploaded-prior-to` (ISO 8601 datetime or `PnD` duration format)
- **Note:** pip 26.1 added `PnD` format. pip 26.0 only supported absolute dates. Exclusive upper bound.

**Global tool detection:**

```bash
# List all installed packages with versions
pip list --format=json

# Check latest version of a specific package
pip index versions <package>

# Get package info for version comparison
pip show <package>
```

**Update a global tool:**

```bash
pip install --upgrade <package>
```
