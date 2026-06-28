# GitHub: target version & commit-range fetch

Commands to resolve the target version and fetch the commit range between two versions of a GitHub-hosted app. Prefer `gh`; fall back to `git`.

## Resolve the target version

```bash
# Latest release tag
gh release view --repo <owner>/<repo> --json tagName,name,publishedAt

# All recent releases
gh release list --repo <owner>/<repo> --limit 20
```

Map a human version (`0.64.16`) to its git tag (`v0.64.16` or `0.64.16`) — they often differ. Verify both the current and target tags exist:

```bash
gh api repos/<owner>/<repo>/git/refs/tags --jq '.[].ref' | grep -i <version>
# or with git:
git ls-remote --tags <repo-url> | grep -i <version>
```

## Fetch the commit range

### With gh (preferred)

```bash
# Release notes for both ends
gh release view <current-tag> --repo <owner>/<repo>
gh release view <target-tag>  --repo <owner>/<repo>

# Full comparison: commits, authors, and files changed between the two tags
gh api repos/<owner>/<repo>/compare/<current-tag>...<target-tag> \
  --jq '{total_commits, commits: [.commits[] | {sha: .sha[0:9], author: .commit.author.name, message: .commit.message}], files: [.files[] | {filename, status, additions, deletions}]}'

# Full unified diff for a focused path or the whole range
gh api repos/<owner>/<repo>/compare/<current-tag>...<target-tag> -H "Accept: application/vnd.github.diff"
```

### With git (fallback, no gh)

```bash
git clone --filter=blob:none <repo-url> /tmp/<app>-audit
cd /tmp/<app>-audit
git fetch --tags

git log --oneline --no-merges <current-tag>..<target-tag>
git log --stat <current-tag>..<target-tag>          # files touched per commit
git diff <current-tag>..<target-tag>                 # full diff
git diff <current-tag>..<target-tag> -- <path>       # focused diff (e.g. build/, package.json)
git show <sha>                                        # inspect a single suspicious commit
```

### With plain curl (no gh, no clone)

```bash
curl -s "https://api.github.com/repos/<owner>/<repo>/compare/<current-tag>...<target-tag>"
```

## Notes

- Use `--filter=blob:none` (partial clone) to avoid downloading full history blobs you don't need.
- **Commit-list truncation:** the `gh api .../compare/A...B` endpoint returns at most **250 commits** and truncates very large diffs. If `total_commits` exceeds 250 (or the diff is truncated), fall back to a `git clone` + `git log`/`git diff` so you review the *entire* range — do not report "Commits reviewed: N" from a truncated comparison.
- For very large diffs, review by path priority: build/CI/release config and dependency manifests first, then native code, then everything else.
- Always clean up `/tmp/<app>-audit` after the audit.
