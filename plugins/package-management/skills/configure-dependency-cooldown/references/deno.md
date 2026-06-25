# Deno

**Available since:** v2.6 (December 2025)

**Config file:** `deno.json` or `deno.jsonc` (project root)

**Setting:** `minimumDependencyAge` (minutes, ISO-8601 duration, or RFC3339 timestamp)

**Project config (deno.json):**

```json
{
  "minimumDependencyAge": "10080"
}
```

**CLI override:**

```bash
deno install --minimum-dependency-age=10080
deno update --minimum-dependency-age=7d
```

**Duration formats accepted:**
- Plain integer: `"10080"` = 10080 minutes
- ISO-8601 duration: `"P7D"` = 7 days, `"P2D"` = 2 days
- RFC3339 absolute: `"2025-09-16"` (cutoff date) or `"2025-09-16T12:00:00+00:00"` (cutoff time)

**Notes:**
- Applies to `deno update` and `deno outdated` commands.
- Works with both JSR and npm packages.
