# pip

**Available since:** v26.0 (January 2026) — absolute timestamps only. v26.1 (April 2026) — relative duration support.

**Config file:** `pip.conf` (Linux/macOS: `~/.config/pip/pip.conf` or `~/.pip/pip.conf`; Windows: `%APPDATA%\pip\pip.ini`)

**Setting:** `uploaded-prior-to` (ISO 8601 datetime or `PnD` duration format)

**Global config (~/.config/pip/pip.conf):**

```ini
# ~/.config/pip/pip.conf — global pip config (pip >= 26.1)
[install]
uploaded-prior-to = P7D
```

**Absolute timestamp (pip 26.0 only):**

```ini
# ~/.config/pip/pip.conf — absolute date cutoff
[install]
uploaded-prior-to = 2026-06-07T00:00:00+00:00
```

**CLI override:**

```bash
pip install --uploaded-prior-to=P7D .
pip install --uploaded-prior-to=2026-06-07 .
```

**Notes:**
- pip 26.1 added `PnD` format (e.g., `P7D` = 7 days) for relative cooldowns.
- pip 26.0 only supported absolute dates.
- This is an **exclusive upper bound**: `P7D` excludes packages uploaded within the last 7 days.
- Pair with a vulnerability scanner like `pip-audit` or Dependabot for independent security notifications.
