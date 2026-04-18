---
name: evaluate-skills-with-synthetic-tasks
description: "Use when asked to 'test skills', 'evaluate skill quality', 'customer-perspective test', 'end-to-end test skills', 'run synthetic scenarios against skills', or 'find bugs in skills by using them'. Distinct from `review-skill` (checks compliance without executing) — this skill EXECUTES the skill and observes what happens."
---

# evaluate-skills-with-synthetic-tasks — Customer-Perspective Skill Evaluation

## Core Principle: Test as a Customer, Not as an Author

Evaluation agents MUST NOT read the SKILL.md source before testing. They invoke the skill via the `Skill` tool exactly as a real user would. This is the only way to discover:

- Skills that load correctly but give wrong instructions
- Missing context the author assumed was obvious
- Steps that sound clear in the SKILL.md but are ambiguous in practice

## Scenario Templates by Skill Type

### Query/action skills (`query-*`, `use-*`, `manage-*`)

- "Execute a basic query and verify the output format"
- "Try with invalid parameters and observe error handling"
- "Try with missing auth and observe the guidance provided"
- "Chain with another skill it claims to work with"

### Knowledge skills (`*-knowledge`)

- "Ask a specific factual question the skill claims to answer"
- "Ask about an edge case not explicitly documented"
- "Ask a question that is adjacent to the skill's domain — does it correctly defer?"

### Watcher skills (`watch-*`)

- "Start the watcher and verify it starts correctly"
- "Simulate an auth failure and verify recovery guidance"
- "Verify restart instructions are complete and correct"

### Workflow skills (brainstorm, debugging, etc.)

- "Walk through the workflow with a concrete example"
- "Skip a step and observe whether the skill catches it"

## Scoring Rubric

Apply this rubric to each scenario:

| Score | Meaning |
|---|---|
| `PASS` | Skill guided to correct outcome without needing correction |
| `PARTIAL` | Skill guided in right direction but required additional context not in the skill |
| `FAIL` | Skill gave wrong guidance or missed a critical step |
| `BLOCKED` | Could not even start — missing prerequisites, broken references, auth failure not handled |

## Sub-Agent Dispatch Pattern

1. Dispatch one evaluation agent per skill (or per skill category for small skills).
2. Each agent receives:
   - Skill name
   - 3–5 synthetic scenarios from the appropriate template set above
   - The scoring rubric
   - Explicit instruction to NOT read the SKILL.md source before testing
3. Each agent reports: scenario → score → evidence (what happened, what was missing or wrong).
4. The primary agent aggregates results and files issues for FAIL/BLOCKED results via `use-local-skills-issue-tracker`.

## Issue Filing

For each FAIL or BLOCKED result, file a skill issue with:

- **Reproduction**: exact synthetic task that triggered the failure
- **Expected**: what the skill should have guided
- **Actual**: what it actually did
- **Severity**: FAIL = should-fix, BLOCKED = critical

## Gotchas

- Evaluation agents reading the SKILL.md before testing will rationalise failures as "correct" — explicitly forbid this in the agent prompt.
- PARTIAL scores are often more valuable than FAILs because they reveal implicit knowledge the author did not document.
- Some skills require real credentials or access — if the evaluator is blocked by auth, that is BLOCKED not FAIL.
- Do not evaluate knowledge skills by checking if facts are accurate (that is `audit-knowledge-skill-against-source`) — evaluate whether the skill is usable.
- A skill that says "use sub-agents to do X" should be tested by actually dispatching those sub-agents, not just reading the instruction.

## Related Skills

- `review-skill` — checks compliance without executing; use for structural/format audits
- `skill-creator` — canonical guidance for writing new skills
- `use-local-skills-issue-tracker` — file issues for FAIL/BLOCKED results found during evaluation
