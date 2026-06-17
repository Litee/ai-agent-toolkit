# Upstream

This plugin is a local port of an upstream Claude Code plugin. Use the
information below to diff against upstream and pick up future changes.

## Source

- **Repository:** [`JayKim88/claude-ai-engineering`](https://github.com/JayKim88/claude-ai-engineering)
- **Upstream path:** `plugins/ai-news-digest/`
  (`skills/ai-news-digest/SKILL.md`, `config/fetch_news.py`,
  `config/trend_analyzer.py`, `config/cache_manager.py`, `config/feeds.yaml`,
  `config/user_preferences.yaml`, `README.md`)
- **License:** MIT, © Jay Kim

## Copied versions

- **Initially ported:** `f624ea7ba8c045eb6c42afdd83a485bef8a2575e`
  (`fix(plugins): enforce \`date\` command for accurate timestamps in 6 plugins`,
  2026-02-23) — last commit that touched `plugins/ai-news-digest/`.
- **Repo HEAD at port time:** `cb722e388c71ff9ce94d05e0d94847ba8966cf31`
  (2026-05-29).

For intentional local divergences see **Differences from upstream** below.

## Differences from upstream

- **AWS profile vs. API keys:** No change required. The upstream plugin uses
  **no LLM API keys at all** — `fetch_news.py` only fetches RSS feeds over
  `urllib`/`feedparser`, scores and deduplicates them locally, and the host
  agent writes the summaries and "Why It Matters" analysis. There is nothing to
  swap for an AWS profile. Should LLM enrichment ever be added, it should call
  AWS Bedrock via an AWS profile (boto3) rather than an external API key.
- **Portable script paths (`SKILL.md`):** Upstream located `fetch_news.py` via
  hardcoded `~/.claude/skills/...` paths (Claude Code's symlink layout). Ported
  version uses the harness-resolved `${SKILL_DIR}/../../config/fetch_news.py`
  so it runs under any harness/marketplace layout. The optional trend-analysis
  step likewise runs from `${SKILL_DIR}/../../config` instead of importing
  `config.trend_analyzer` from a fixed CWD.
- **Removed dead cross-references:** Upstream referenced sibling skills
  `ai-digest` and `learning-summary` (present only in the upstream monorepo).
  These do not exist in this marketplace, so the `## Related Skills` section was
  softened and the `~/.claude/skills/learning-summary/config.yaml` →
  `learning_repo` save-location lookup was dropped; the digest now saves to the
  current working directory (or a user-specified directory).
- **Removed transient/measured data from `SKILL.md`:** Version-specific speedup
  percentages (63%, ~95%), absolute timings, and hardcoded feed/article counts
  were replaced with qualitative descriptions to avoid stale claims as
  `feeds.yaml` evolves.
- **Frontmatter:** Dropped the non-standard `version:` field from the SKILL
  frontmatter (the version lives in `marketplace.json`); rewrote `description`
  to be triggers-only per skill-authoring guidance.
- Python scripts and YAML config copied verbatim. No code divergences yet.

## How to check for upstream changes

```bash
UP=$(mktemp -d)/jaykim88-claude-ai-engineering
git clone --quiet https://github.com/JayKim88/claude-ai-engineering.git "$UP"
git -C "$UP" log f624ea7..origin/HEAD -- plugins/ai-news-digest
```
