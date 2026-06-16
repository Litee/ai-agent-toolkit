# Poetry

**Available since:** v2.4.0

**Config file:** `pyproject.toml` or `poetry config` CLI

**Setting:** `solver.min-release-age` (in minutes) + `solver.min-release-age-exclude` + `solver.min-release-age-exclude-source`

**Project config (pyproject.toml):**

```toml
[tool.poetry.solver]
min-release-age = 10080
min-release-age-exclude = ["requests", "flask"]
```

**Global config via CLI:**

```bash
poetry config solver.min-release-age 10080
poetry config solver.min-release-age-exclude "requests flask"
```

**Config file (global ~/.config/pypoetry/config):**

```ini
[solver]
min-release-age = 10080
min-release-age-exclude = ["requests", "flask"]
```

**Notes:**
- Value is in **minutes** (10080 = 7 days).
- `min-release-age-exclude` lists package names to bypass cooldown.
- `min-release-age-exclude-source` allows excluding by package source.
