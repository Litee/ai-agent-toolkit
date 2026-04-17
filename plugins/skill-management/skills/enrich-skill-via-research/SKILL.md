---
name: enrich-skill-via-research
description: "Use when asked to 'improve a skill', 'enrich a skill with best practices', 'add anti-patterns to a skill', 'research and update a skill', or 'find what's missing in a skill'. Distinct from skill-creator (creates skills from scratch) and audit-skills-against-best-practices (checks compliance against existing standards). This skill specifically adds NEW knowledge sourced from external references — internet, documentation, code examples, post-mortems — into an existing SKILL.md."
---

# enrich-skill-via-research

> Found major gaps or factual errors in this skill? Report it via the `use-local-skills-issue-tracker` skill (if available).

## Overview

This skill guides the process of improving an existing skill by researching external sources and merging the findings into the skill's SKILL.md. The output is a richer skill with better coverage of failure modes, anti-patterns, and operational wisdom — without bloating it with noise or duplicating what is already there.

**Distinct from:**
- `skill-creator` — creates a skill from scratch
- `audit-skills-against-best-practices` — checks an existing skill against structural/quality standards

---

## Phase 1: Gap Analysis (Before Researching)

Run this before touching any external source. Research without a defined target produces noise.

1. Read the target skill's SKILL.md in full.
2. Read all files in its `references/` directory (if present).
3. Identify which of the following are thin or entirely absent:
   - Common failure modes and their root causes
   - Anti-patterns (what people do wrong, and why it's wrong)
   - Operational gotchas that are non-obvious from the API/tool surface alone
   - Performance and cost considerations that affect usage decisions
   - Security considerations
   - Troubleshooting steps for real-world failure scenarios
4. Write a research brief: *"I need to find: [specific gaps listed precisely]"*. Be narrow — over-researching produces content that fails the filter in Phase 3.

---

## Phase 2: Research

Dispatch parallel sub-agents, each scoped to one source type. Each agent must return raw findings with source citations; do not filter inside the research agent.

**Source types:**

| Source | Examples | Priority |
|---|---|---|
| Official documentation | AWS docs, tool reference docs, language specs | Highest |
| Team wikis and runbooks | Internal team wikis, oncall guides, post-mortems | High |
| Authoritative engineering blogs | AWS blog, Netflix tech blog, engineering post-mortems | Medium |
| Code search | Patterns in existing repos, usage examples, test cases | Medium |
| Community Q&A | Stack Overflow, GitHub issues | Low |

**Source priority rule:** Official docs > team wikis/runbooks > authoritative engineering blogs > Stack Overflow. When sources conflict, prefer the higher-priority source and note the conflict.

---

## Phase 3: Filter and Merge

Apply these rules to every candidate finding before writing anything.

### Add

- Gotchas that are **non-obvious** from the API surface and not already in the skill (even phrased differently)
- Anti-patterns with: (a) a clear explanation of *why* they're bad, and (b) what to do instead
- Troubleshooting steps for failure modes that actually occur in production
- Performance or cost considerations that would change a usage decision

### Skip

- Content already present in the skill (even if phrased differently — duplication adds maintenance burden)
- Version-specific tutorials ("in v2.3, you need to…") — these rot
- Pricing information — transient, will be stale within weeks
- Content that duplicates official documentation verbatim — link instead
- Benchmark numbers without operational context — they change and mislead
- Best practices from an adjacent but different context (e.g., AWS Lambda best practices are not AWS Glue best practices — verify transferability before including)

---

## Phase 4: Write

**Structure rules:**
- Add new content to **existing sections** — do not create new top-level sections unless there is genuinely no existing home for the content
- Preserve the existing voice, terminology, and heading structure
- After adding content, re-read the full skill: does it still flow? Is it still skimmable?

**Source attribution:**
- For non-obvious technical claims from external sources, add a brief inline note: `*(source: [description])*`
- Detailed source metadata (URL, capture date, context) belongs in a `references/` file, not the SKILL.md body
- Do not let `references/` content leak into the main skill body

---

## Gotchas

- Research agents without filtering rules will dump raw internet content into skills — always provide the filter (Phase 3) in the agent prompt, not as a post-processing step
- "Best practices" from one context do not automatically transfer: AWS Lambda ≠ Glue ≠ ECS — verify the context matches before including
- If a gap exists because the topic is genuinely ambiguous or unsettled in the field, document the ambiguity explicitly rather than picking an arbitrary answer
- Don't add content that belongs in `references/` to the main SKILL.md body — time-sensitive or sourcing metadata belongs in references
- Resist the temptation to add content that is "nice to have" — every addition increases the cognitive load of the skill and the maintenance surface

## Related Skills

- `skill-creator` — creates a skill from scratch; this skill enriches existing ones
- `skill-creator-extra-tips` — structural and quality tips for writing skills
- `audit-skills-against-best-practices` — checks an existing skill against standards (does not add new content)
