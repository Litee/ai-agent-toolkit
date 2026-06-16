# uv

**Available since:** v0.9.17 (December 2025) — relative duration support

**Config file:** `pyproject.toml`, `uv.toml`, or environment variable

**Setting:** `exclude-newer` (relative duration like `1 week`, `30 days`, or absolute date)

**Global config (~/.config/uv/uv.toml):**

```toml
# ~/.config/uv/uv.toml — global uv config
resolve.exclude-newer = "2026-06-07"
```

**Relative duration (recommended for cooldown):**

```toml
# ~/.config/uv/uv.toml
resolve.exclude-newer = "7 days"
```

**Project config (pyproject.toml):**

```toml
[tool.uv]
exclude-newer = "7 days"
```

**Per-package overrides:**

```toml
# ~/.config/uv/uv.toml
resolve.exclude-newer-package = [
    { package = "requests", exclude-newer = "2026-06-01" },
    { package = "flask", exclude-newer = "2026-06-01" },
]
```

**CLI override:**

```bash
uv pip install --exclude-newer 7days .
uv sync --exclude-newer 7days
```

**Notes:**
- Accepts both relative durations (`1 week`, `30 days`) and absolute dates (`2026-06-07`).
- ISO 8601 durations (`P7D`) also supported, but months and years are excluded.
- `exclude-newer-package` allows per-package exceptions.
