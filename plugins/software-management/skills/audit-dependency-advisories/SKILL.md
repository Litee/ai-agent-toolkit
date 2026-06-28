---
name: audit-dependency-advisories
description: Use when checking whether third-party dependencies are safe — cross-checking a specific name@version (or a set of dependency changes, or a lockfile) against security advisory databases (GitHub Advisory Database, OSV) and flagging versions published less than 72 hours ago (a supply-chain attack window). Covers npm, PyPI, crates.io, Go, Swift/SPM, RubyGems, and more. Triggers on "does <pkg>@<ver> have a CVE/advisory", "is this dependency version too new", "audit these dependency changes", "check this lockfile for vulnerable packages". Read-only lookups; does not install or modify dependencies.
---

# Audit Dependency Advisories

This skill checks whether dependencies are safe. Given a single `name@version`, a set of dependency changes, or a lockfile, it cross-checks advisory databases (GitHub Advisory Database, OSV.dev, and ecosystem auditors) and flags any version published less than 72 hours ago — a common supply-chain attack window. Read-only; never installs or modifies anything.

## 1. Find the dependency changes

> If you were handed a single `name@version`, skip to §2 — the steps in §1 are for discovering changes across a diff or lockfile.

First, **identify which ecosystem(s) the project actually uses** — do not assume npm. Check what manifest/lockfiles exist (via `ls`, or `git show <ref>:<path>`), then examine the dependency changes under review (or a lockfile, or a single package). The list below is not exhaustive; match it to the project:

```bash
git diff <base>..<head> -- \
  package.json package-lock.json pnpm-lock.yaml yarn.lock \
  Cargo.toml Cargo.lock \
  go.mod go.sum \
  requirements.txt pyproject.toml poetry.lock uv.lock \
  Gemfile.lock composer.lock \
  Package.swift Package.resolved \
  build.gradle build.gradle.kts pom.xml \
  *.csproj packages.lock.json pubspec.yaml pubspec.lock
```

| Ecosystem | Manifests / lockfiles |
|-----------|-----------------------|
| Node/npm | `package.json`, `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock` |
| Rust | `Cargo.toml`, `Cargo.lock` |
| Go | `go.mod`, `go.sum` |
| Python | `requirements.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock` |
| Ruby | `Gemfile`, `Gemfile.lock` |
| PHP | `composer.json`, `composer.lock` |
| **Swift / SPM** | **`Package.swift`, `Package.resolved`** (native macOS/iOS apps live here, *not* in `package.json`) |
| Java/Kotlin | `build.gradle(.kts)`, `pom.xml` |
| .NET | `*.csproj`, `packages.lock.json` |
| Dart/Flutter | `pubspec.yaml`, `pubspec.lock` |

> A native app (Swift, Kotlin, Go, Rust) will have **no** `package.json`. If the manifest diff comes back empty, confirm you targeted the right ecosystem before concluding "no dependency changes" — an empty diff against the wrong manifest is a false negative, not a clean bill of health.

Produce a list of **added**, **removed**, and **version-bumped** dependencies: `name: old → new`.

Pay special attention to:
- A dependency moved from `devDependencies` to `dependencies` (now ships to users).
- A new transitive dependency pulled in by a lockfile change.
- A version bump that crosses a major boundary or jumps many minor versions.

## 2. Cross-check against advisory databases

### GitHub Advisory Database (covers npm/PyPI/RubyGems/Maven/NuGet/Go/Rust/Composer/Swift/etc.)

With `gh` (authenticated):

```bash
gh api -X GET /advisories \
  -f ecosystem=<npm|pip|rust|go|...> \
  -f affects='<pkg>@<version>' \
  --jq '.[] | {ghsa: .ghsa_id, severity, summary, vulnerable: [.vulnerabilities[].vulnerable_version_range]}'
```

If `gh` is unavailable or unauthenticated, hit the same public endpoint with `curl` (no auth required for reads):

```bash
curl -s "https://api.github.com/advisories?ecosystem=<npm|pip|rust|go|...>&affects=<pkg>@<version>" \
  | jq '.[] | {ghsa: .ghsa_id, severity, summary, vulnerable: [.vulnerabilities[].vulnerable_version_range]}'
```

> **Do not trust an empty `affects=<pkg>@<version>` result as "clean."** The `affects=` filter only returns advisories whose vulnerable range *includes that exact version* — so a package with a real advisory at older versions (and your version already patched) returns `[]`, masking the advisory's existence. Always **also** query by package name alone and read the ranges yourself, so you can see *what was vulnerable, when it was fixed, and whether your version is genuinely past the fix* (a fixed-but-recent advisory is useful provenance context, not noise):
>
> ```bash
> # name-only scan (no @version): returns EVERY advisory affecting the package,
> # across all versions — then read the ranges and decide where your version sits.
> # gh --paginate follows the Link header so a high-advisory package isn't truncated:
> gh api --paginate "/advisories?ecosystem=<eco>&affects=<pkg>&per_page=100" \
>   --jq '.[] | {ghsa: .ghsa_id, severity, summary, ranges: [.vulnerabilities[] | select(.package.name=="<pkg>") | .vulnerable_version_range]}'
> # curl fallback (no auto-paginate — if a full 100 rows return, fetch &page=2…):
> curl -s "https://api.github.com/advisories?ecosystem=<eco>&affects=<pkg>&per_page=100" \
>   | jq '.[] | {ghsa: .ghsa_id, severity, summary, ranges: [.vulnerabilities[] | select(.package.name=="<pkg>") | .vulnerable_version_range]}'
> ```
>
> Then decide whether `<version>` falls inside any returned range. This mirrors the §1 false-negative guard: an empty filtered result is not the same as no advisory. (Do **not** substitute a bare `?ecosystem=<eco>&per_page=100` listing without `affects=` — that returns only the first page of the entire ecosystem's advisories, not your package's, and will spuriously come back empty.) And when a full page (100) of advisories comes back from the `affects=` scan, **page through the rest** (`gh api --paginate`, or `&page=N` with curl) — a truncated first page is not "clean."
>
> **API limits & failures:** unauthenticated `api.github.com` is rate-limited (~60 req/hr); `gh` (authenticated) is far higher. On a `403`/`429`/rate-limit/network error, treat the result as **unknown and escalate to REVIEW** — never report "clean" from a failed lookup.

### OSV.dev (any ecosystem, no auth)

```bash
curl -s "https://api.osv.dev/v1/query" -d '{
  "package": {"name": "<pkg>", "ecosystem": "<npm|PyPI|crates.io|Go|...>"},
  "version": "<version>"
}' | jq '.vulns[]? | {id, summary, severity}'
```

> **Ecosystem identifiers matter** — OSV is case- and spelling-sensitive: `npm`, `PyPI`, `crates.io`, `Go`, `RubyGems`, `Packagist`, `Maven`, `NuGet`, `Pub`, `SwiftURL`. For **Swift / SPM** use ecosystem `SwiftURL` and the package `name` as the **full repo URL without scheme**, e.g. `github.com/apple/swift-asn1`:
>
> ```bash
> curl -s "https://api.osv.dev/v1/query" -d '{
>   "package": {"name": "github.com/apple/swift-asn1", "ecosystem": "SwiftURL"},
>   "version": "1.7.1"
> }' | jq '.vulns[]? | {id, summary, severity}'
> ```
>
> OSV's Swift (`SwiftURL`) index is **sparse** — an empty result is weak evidence. For Swift/SPM, treat the GitHub Advisory Database (above, with the package-name-wide scan) as the primary source and OSV as a secondary cross-check.

### Ecosystem-native auditors (run against a checkout, read-only)

```bash
npm audit --omit=dev --json          # npm/Node
osv-scanner --lockfile=<lockfile>    # universal, reads many lockfiles
pip-audit -r requirements.txt        # Python
cargo audit                          # Rust (needs Cargo.lock)
bundle audit                         # Ruby
```

These only **read** the lockfile — they do not install or upgrade anything.

## 3. Flag freshly-published versions (< 72 hours old)

A dependency version published **less than 72 hours ago** is a supply-chain red flag: compromised or typosquatted releases are usually caught and yanked within a day or two, so a brand-new version deserves extra scrutiny *even if no advisory exists yet* (advisories lag the attack).

For each **added or version-bumped** dependency, look up the publish timestamp of the introduced version and compute its age:

```bash
NOW=$(date -u +%s)

# npm — registry returns per-version publish times under .time
curl -s "https://registry.npmjs.org/<pkg>" \
  | jq -r --arg v "<version>" '.time[$v]'
# → ISO timestamp, e.g. 2026-06-22T14:03:11.000Z

# PyPI — .releases[<version>][].upload_time_iso_8601
curl -s "https://pypi.org/pypi/<pkg>/json" \
  | jq -r --arg v "<version>" '.releases[$v][0].upload_time_iso_8601'

# crates.io (Rust) — .version.created_at  (crates.io REQUIRES a User-Agent header)
curl -s -H "User-Agent: audit-dependency-advisories (security review)" \
  "https://crates.io/api/v1/crates/<pkg>/<version>" \
  | jq -r '.version.created_at'

# RubyGems — match .number, read .created_at
curl -s "https://rubygems.org/api/v1/versions/<pkg>.json" \
  | jq -r --arg v "<version>" '.[] | select(.number==$v) | .created_at'

# Go modules — proxy returns .Time for the version
curl -s "https://proxy.golang.org/<module>/@v/<version>.info" \
  | jq -r '.Time'

# Swift / SPM — deps are GitHub repos pinned by tag in Package.resolved.
# Use the version tag's commit/publish date from the dependency's repo:
curl -s "https://api.github.com/repos/<owner>/<dep-repo>/git/refs/tags/<version-tag>" \
  | jq -r '.object.url' | xargs curl -s \
  | jq -r '.tagger.date // .committer.date // .author.date'
# (or, simpler, the release publish date:)
curl -s "https://api.github.com/repos/<owner>/<dep-repo>/releases/tags/<version-tag>" \
  | jq -r '.published_at'
```

Convert the timestamp to epoch seconds and compare:

```bash
# macOS date; on Linux use: date -u -d "<iso>" +%s
PUB=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "$(echo <iso> | cut -d. -f1 | tr -d Z)" +%s)
AGE_HOURS=$(( (NOW - PUB) / 3600 ))
# AGE_HOURS < 72  → flag as FRESH
```

> The Go proxy `.Time` has no fractional seconds and ends in `Z` (e.g. `2026-06-22T00:00:00Z`). On macOS, strip the trailing `Z` first (`| cut -d. -f1 | tr -d Z`) to avoid a harmless "extraneous characters" warning; the epoch is correct either way. Also, **uppercase letters in a Go module path must be `!`-escaped** (e.g. `github.com/Sirupsen/logrus` → `github.com/!sirupsen/logrus`), or the proxy `.info` request 404s and freshness silently reads empty.

Mark any dependency whose introduced version is **< 72 hours old** as `FRESH`. Tune the window (widen it, or set it to 0) if a project intentionally tracks bleeding-edge releases.

## 4. Classify findings

For each dependency with an advisory or freshness flag:

| Field | Capture |
|-------|---------|
| Dependency | `name old → new` |
| Advisory | GHSA / CVE / OSV id (or none) |
| Severity | critical / high / medium / low |
| Affected | does the introduced version fall in the vulnerable range? |
| Reachable | is the vulnerable code path plausibly used by this project? |
| Age | publish age of the introduced version; `FRESH` if < 72h |

## 5. Verdict

Emit a `SAFE` / `REVIEW` / `BLOCK` verdict for the dependencies reviewed. When this skill is composed into a larger audit (e.g. `audit-software-upgrade`), this becomes the dependency dimension of that audit's verdict.

- **Critical or high** advisory affecting a reviewed dependency, with the version in range → **BLOCK**.
- **`FRESH`** (version < 72h old) → at least a **REVIEW**: too new to have accumulated scrutiny. Escalate to **BLOCK** if combined with any other signal — an advisory here, or (when composed with `review-supply-chain-risk`) a new author on the bump, install hooks, or obfuscation.
- **Medium/low**, or a high that a version change actually *fixes* (old version vulnerable, new version patched) → note it; typically **REVIEW** or **SAFE**.
- No advisories, nothing fresh → **SAFE**.

Always note when a version change *remediates* a vulnerability — that is a point in favour of the change.

## Related Skills

- **`review-supply-chain-risk`** — reviews a diff / PR / commit-range / tarball for malware and tampering (install hooks, obfuscation, exfiltration). Pair with it when you have the actual *code* change, not just dependency names/versions.
- **`audit-software-upgrade`** — the full single-app upgrade audit; invokes this skill for its dependency dimension.
- **`configure-dependency-cooldown`** (in the `package-management` plugin) — the *preventative* complement: configures package managers to delay installing newly published versions, so FRESH versions never get installed in the first place.
