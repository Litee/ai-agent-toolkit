# Third-Party Dependency Advisory Audit

Identify dependency changes introduced by the upgrade and cross-check them against known security advisories. Flag any **critical or high** advisory affecting an added or upgraded dependency.

## 1. Find the dependency changes

First, **identify which ecosystem(s) the app actually uses** — do not assume npm. Check what manifest/lockfiles exist in the repo (`ls`, or `git show <target-tag>:<path>`), then diff those between the two versions. The list below is not exhaustive; match it to the project:

```bash
git diff <current-tag>..<target-tag> -- \
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
  --jq '.[] | {ghsa: .ghsa_id, severity, summary, vulnerable: .vulnerabilities[].vulnerable_version_range}'
```

If `gh` is unavailable or unauthenticated, hit the same public endpoint with `curl` (no auth required for reads):

```bash
curl -s "https://api.github.com/advisories?ecosystem=<npm|pip|rust|go|...>&affects=<pkg>@<version>" \
  | jq '.[] | {ghsa: .ghsa_id, severity, summary, vulnerable: [.vulnerabilities[].vulnerable_version_range]}'
```

> **Do not trust an empty `affects=<pkg>@<version>` result as "clean."** The `affects=` filter only returns advisories whose vulnerable range *includes that exact version* — so a package with a real advisory at older versions (and your version already patched) returns `[]`, masking the advisory's existence. Always **also** query by package name alone and read the ranges yourself, so you can see *what was vulnerable, when it was fixed, and whether your version is genuinely past the fix* (a fixed-but-recent advisory is useful provenance context, not noise):
>
> ```bash
> # package-name-wide scan; filter client-side and read every vulnerable range
> curl -s "https://api.github.com/advisories?ecosystem=<eco>&per_page=100" \
>   | jq --arg pkg "<pkg>" '.[] | select(any(.vulnerabilities[]; .package.name==$pkg))
>            | {ghsa: .ghsa_id, severity, ranges: [.vulnerabilities[] | select(.package.name==$pkg) | .vulnerable_version_range]}'
> ```
>
> Then decide whether `<version>` falls inside any returned range. This mirrors the §1 false-negative guard: an empty filtered result is not the same as no advisory.

### OSV.dev (any ecosystem, no auth)

```bash
curl -s "https://api.osv.dev/v1/query" -d '{
  "package": {"name": "<pkg>", "ecosystem": "<npm|PyPI|crates.io|Go|...>"},
  "version": "<new-version>"
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

### Ecosystem-native auditors (run against a checkout of the target version, read-only)

```bash
npm audit --omit=dev --json          # npm/Node
osv-scanner --lockfile=<lockfile>    # universal, reads many lockfiles
pip-audit -r requirements.txt        # Python
cargo audit                          # Rust (needs Cargo.lock)
bundle audit                         # Ruby
```

These only **read** the lockfile — they do not install or upgrade anything. Run them on the cloned target-version tree.

## 3. Flag freshly-published versions (< 72 hours old)

A dependency version published **less than 72 hours ago** is a supply-chain red flag: compromised or typosquatted releases are usually caught and yanked within a day or two, so a brand-new version that an upgrade pulls in deserves extra scrutiny *even if no advisory exists yet* (advisories lag the attack).

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

# crates.io (Rust) — .version.created_at
curl -s "https://crates.io/api/v1/crates/<pkg>/<version>" \
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
PUB=$(date -u -j -f "%Y-%m-%dT%H:%M:%S" "$(echo <iso> | cut -d. -f1)" +%s)
AGE_HOURS=$(( (NOW - PUB) / 3600 ))
# AGE_HOURS < 72  → flag as FRESH
```

> The Go proxy `.Time` has no fractional seconds and ends in `Z` (e.g. `2026-06-22T00:00:00Z`). On macOS, strip the trailing `Z` first (`| cut -d. -f1 | tr -d Z`) to avoid a harmless "extraneous characters" warning; the epoch is correct either way.

Mark any dependency whose introduced version is **< 72 hours old** as `FRESH`. Tune the window via the app spec if a project intentionally tracks bleeding-edge releases.

## 4. Classify findings

For each introduced/upgraded dependency with an advisory or freshness flag:

| Field | Capture |
|-------|---------|
| Dependency | `name old → new` |
| Advisory | GHSA / CVE / OSV id (or none) |
| Severity | critical / high / medium / low |
| Affected | does the introduced version fall in the vulnerable range? |
| Reachable | is the vulnerable code path plausibly used by this app? |
| Age | publish age of the introduced version; `FRESH` if < 72h |

## 5. Feed into the verdict

- **Critical or high** advisory affecting a newly introduced or upgraded dependency, with the vulnerable version in range → contributes a **BLOCK**.
- **`FRESH`** (introduced version < 72h old) → contributes at least a **REVIEW**: the version is too new to have accumulated scrutiny. Escalate to **BLOCK** if combined with any other signal (new author on the bump, install hooks, obfuscation, an advisory).
- **Medium/low**, or a high that the upgrade actually *fixes* (old version vulnerable, new version patched) → note it; typically **REVIEW** or **SAFE**.
- No advisories, nothing fresh on changed deps → dependency dimension is **SAFE**.

Always note when an upgrade *remediates* a vulnerability — that is a point in favour of upgrading.
