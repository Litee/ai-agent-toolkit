# Bun

**Available since:** v1.3 (October 2025)

**Config file:** `bunfig.toml` (project or global `~/.config/bun/bunfig.toml`)

**Setting:** `minimumReleaseAge` (in seconds)

**Global config (~/.config/bun/bunfig.toml):**

```toml
# ~/.config/bun/bunfig.toml — global Bun config
[install]
minimumReleaseAge = 259200  # 3 days in seconds
```

**Project config (bunfig.toml):**

```toml
[install]
minimumReleaseAge = 259200  # 3 days in seconds
```

**CLI override:**

```bash
bun install --minimum-release-age=259200
```

**Notes:**
- Value is in **seconds** (259200 = 3 days = 72 hours).
