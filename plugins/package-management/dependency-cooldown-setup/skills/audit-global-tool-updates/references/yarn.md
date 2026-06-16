# Yarn (Berry)

**Config:**
- **Global config (~/.yarnrc.yml):** `npmMinimalAgeGate: 10080`, `npmPreapprovedPackages: [webpack, react]`
- **CLI override:** `yarn install --minimum-age-gate=10080`
- **Setting:** `npmMinimalAgeGate` (minutes) + `npmPreapprovedPackages` (names)
- **Note:** Value in **minutes** (10080 = 7 days).

**Global tool detection:**

```bash
# List all globally installed packages with versions
yarn global list --json

# Check latest version of a specific package
yarn info <package> version --json

# Get package info for version comparison
yarn info <package> versions --json
```

**Update a global tool:**

```bash
yarn global add <package>@latest
```
