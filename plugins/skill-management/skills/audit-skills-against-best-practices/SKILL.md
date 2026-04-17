---
name: audit-skills-against-best-practices
description: "Use when asked to 'audit all skills', 'check skills for best practices', 'review skills for quality', 'find issues across all skills', 'sweep skills for compliance', or any bulk quality sweep of a plugin workspace. Dispatches parallel sub-agents to evaluate every skill in a plugin against a canonical 10-criterion checklist, then aggregates findings by severity and auto-files actionable items. Do NOT use when the goal is to review a single skill in isolation (just read that skill's SKILL.md and apply the checklist manually), or when the user wants to fix a specific known issue (use use-local-skills-issue-tracker directly)."
---

> Found major gaps or factual errors in this skill? Report it via the `use-local-skills-issue-tracker` skill, if the skill exists.

# audit-skills-against-best-practices

## Overview

This skill guides a systematic, parallel quality audit of all skills in a plugin workspace. It dispatches sub-agents in batches to evaluate each skill against a canonical checklist, aggregates findings by severity, and auto-files actionable items via `use-local-skills-issue-tracker`.

---

## Checklist

**Before auditing, invoke `skill-creator` and `skill-creator-extra-tips`** to load the full best practices. Use their criteria as the authoritative checklist for each sub-agent — do not summarise or paraphrase them.

In addition, each skill must be checked for these criteria not covered by those skills:

| # | Criterion | What to Check |
|---|---|---|
| 1 | **No internal leaks** | No company-internal tool names, auth commands, or internal URLs in public/shared plugins |
| 2 | **Related skills cross-referenced** | If commonly used alongside another skill, a `## Related Skills` or `## See Also` section exists |
| 3 | **Knowledge skills: no stale claims** | Knowledge skills note that facts need verification against source; no unconditional present-tense assertions about dynamic systems |
| 4 | **Action skills: error handling documented** | What to do when the tool/API fails is documented (retry, fallback, escalation path) |

Always include the full criteria (from `skill-creator` + `skill-creator-extra-tips` + the table above) verbatim in every sub-agent prompt — agents without the full list will invent their own criteria.

---

## Severity Classification

| Severity | Examples | Action |
|---|---|---|
| `CRITICAL` | Internal leaks, transient data in SKILL.md body, missing trigger conditions | Must fix before merging; block the PR |
| `SHOULD_FIX` | Missing gotchas, missing error handling, missing cross-references, large tables inline | Fix in the same PR/worktree |
| `NICE_TO_HAVE` | Minor phrasing improvements, optional cross-references, subjective readability | File as a skill issue; do not block |

---

## Skill Type Classification

Apply type-specific emphasis when evaluating each criterion:

- **Action skills** (`query-*`, `use-*`, `manage-*`, `watch-*`, `operate-*`): Focus on error handling (criterion 4), auth gotchas, API limits, and negative trigger examples (misfire prevention)
- **Knowledge skills** (`*-knowledge`): Focus on no stale claims (criterion 3), no transient data, and moving large tables to `references/`
- **Workflow skills** (brainstorm, debugging, systematic-*, etc.): Focus on checklist completeness, step ordering, negative examples, and cross-references to complementary skills (criterion 2)

---

## Audit Procedure

### Step 1 — Discover skills

List all skill directories in the target plugin:

```bash
ls <plugin-root>/skills/
```

Do not rely on README.md — audit the filesystem directly. README may be out of sync.

### Step 2 — Group into batches

Partition skills into batches of 3–5 per sub-agent. Prioritise grouping skills from the same skill type together (all knowledge skills in one batch, all action skills in another) — agents calibrate their emphasis better when batch composition is homogeneous.

### Step 3 — Dispatch sub-agents in parallel

For each batch, dispatch a sub-agent with:

1. The full criteria from `skill-creator`, `skill-creator-extra-tips`, plus the 4 additional criteria above (copy verbatim — do not summarise)
2. The skill type classification rules above
3. The list of SKILL.md paths to evaluate
4. This output format requirement:

```
skill-name | criterion-number | severity | evidence
```

Example output line:
```
query-foo-api | 4 | SHOULD_FIX | description field has no negative trigger examples
query-foo-api | 10 | CRITICAL | no error handling documented; API is rate-limited and known to 429
```

### Step 4 — Aggregate findings

After all sub-agents return, deduplicate: the same (skill-name, criterion-number) finding reported by multiple agents counts as one finding. Keep the highest severity and the most specific evidence string.

### Step 5 — Auto-file actionable items

For each CRITICAL and SHOULD_FIX finding, call `use-local-skills-issue-tracker` to file a skill issue. Use the evidence string as the issue description. Do not file NICE_TO_HAVE items — they are noted in the summary but not filed.

### Step 6 — Report

Produce a structured summary:

```
## Audit Results — <plugin-name>

### CRITICAL (<count>)
- <skill-name>: <criterion> — <evidence>

### SHOULD_FIX (<count>)
- <skill-name>: <criterion> — <evidence>

### NICE_TO_HAVE (<count>)
- <skill-name>: <criterion> — <evidence>

### Clean skills (<count>)
- <skill-name>, <skill-name>, ...

Issues filed: <count> (CRITICAL + SHOULD_FIX)
```

---

## Gotchas

- **Always include the full checklist in sub-agent prompts.** Agents without the checklist in front of them will invent their own criteria, producing inconsistent findings across batches.
- **"No transient data" is the most commonly missed criterion.** Explicitly prompt sub-agents to scan for years, specific version numbers, measured latency/throughput values, and "as of [date]" phrases.
- **Some plugins are intentionally scoped to a specific organization or platform.** Check the plugin description first — internal-use plugins may intentionally reference internal tool names or auth flows and should not be flagged for internal leak violations.
- **Audit the filesystem, not just README.md.** README may list skills that have been deleted or omit skills that have been added.
- **Internal leak scope depends on plugin audience.** Internal plugins (private, org-only) have no internal-leak obligation. Public/shared plugins must not leak internal tool names or auth flows.
- **One finding per (skill, criterion) pair.** Do not file duplicate issues if two agents both flag the same criterion for the same skill.

## Related Skills

- `use-local-skills-issue-tracker` — file and track the issues discovered during the audit
- `skill-creator` — consult when unsure whether a specific pattern violates best practices
- `skill-creator-extra-tips` — additional best-practice tips complementing skill-creator
