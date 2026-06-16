# pnpm

**Available since:** v10.16 (September 2025)

**Config file:** `pnpm-workspace.yaml` (root) or `.npmrc`

**Setting:** `minimumReleaseAge` (in minutes) + `minimumReleaseAgeExclude` (list of package names to skip)

**Global config (~/.npmrc):**

```ini
# ~/.npmrc — applies to all pnpm projects
minimumReleaseAge=10080
minimumReleaseAgeExclude=webpack,react,typescript
```

**Workspace config (pnpm-workspace.yaml):**

```yaml
# pnpm-workspace.yaml (project root)
settings:
  minimumReleaseAge: 10080
  minimumReleaseAgeExclude:
    - webpack
    - react
    - typescript
```

**CLI override:**

```bash
pnpm install --minimum-release-age=10080
```

**Notes:**
- Applies to both direct and transitive dependencies.
- `minimumReleaseAgeExclude` lists package names that bypass the cooldown.
- Value is in **minutes** (10080 = 7 days).
