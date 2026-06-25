# Yarn (Berry)

**Available since:** v4.10.0 (September 2025)

**Config file:** `.yarnrc.yml` (project or global `~/.yarnrc.yml`)

**Setting:** `npmMinimalAgeGate` (in minutes) + `npmPreapprovedPackages` (list)

**Global config (~/.yarnrc.yml):**

```yaml
# ~/.yarnrc.yml — global Yarn config
npmMinimalAgeGate: 10080
npmPreapprovedPackages:
  - webpack
  - react
  - typescript
```

**Project config (.yarnrc.yml):**

```yaml
npmMinimalAgeGate: 10080
npmPreapprovedPackages:
  - webpack
```

**CLI override:**

```bash
yarn install --minimum-age-gate=10080
```

**Notes:**
- Value is in **minutes** (10080 = 7 days).
- `npmPreapprovedPackages` exempts specific packages from the cooldown.
