# Bundler (Ruby)

**Available since:** v4.0.13 (June 2026)

**Config file:** `~/.bundle/config` (global), `.bundle/config` (project), or environment variable

**Setting:** `cooldown` (in days)

**Global config via CLI:**

```bash
bundle config set cooldown 7
```

**Project config (.bundle/config):**

```yaml
---
BUNDLE_COOLDOWN: "7"
```

**Gemfile per-source cooldown:**

```ruby
source "https://rubygems.org", cooldown: 7 do
  gem "rails"
end
```

**CLI override:**

```bash
bundle install --cooldown 7
```

**Escape hatch:**

```bash
bundle install --cooldown 0  # disable cooldown for immediate install
```

**Environment variable:**

```bash
export BUNDLE_COOLDOWN=7
```

**Notes:**
- Value is in **days** (7 = 7 days).
- Cooldown is attached to the **source**, not individual gems — private registries don't get a cooldown by default.
- Applies to transitive dependencies too.
- Lockfile-pinned versions bypass the cooldown (existing locks don't break).
- `--cooldown 0` is the escape hatch for immediate CVE fixes.
- gem.coop (community gem server) supports cooldowns at the index level: append `/cooldown` to the source URL for automatic 48-hour hold.
