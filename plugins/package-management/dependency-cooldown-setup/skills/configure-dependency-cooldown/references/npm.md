# npm

**Available since:** v11.10.0 (February 2026)

**Config file:** `.npmrc` (project or global)

**Setting:** `minimum-release-age` (in days) + `minimum-release-age-exclude` (list of package names or minimatch globs)

**Global config (~/.npmrc):**

```ini
# ~/.npmrc — applies to all npm projects
minimum-release-age=3
minimum-release-age-exclude[]=webpack
minimum-release-age-exclude[]=react
minimum-release-age-exclude[]=typescript
```

**CLI override:**

```bash
npm install --minimum-release-age=3
```

**Notes:**
- Value is in **days** (3 = 3 days = 72 hours). Internally converts to `--before` using `86400000 * age` milliseconds.
- `minimum-release-age-exclude` supports exact package names and minimatch globs (e.g. `@myorg/*`).
- If both `before` and `min-release-age` are set in the same source, `before` wins (absolute date overrides relative window).
