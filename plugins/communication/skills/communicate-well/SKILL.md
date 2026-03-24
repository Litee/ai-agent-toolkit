---
name: communicate-well
description: "This skill should be used before composing any outbound message across any async channel — chat (Slack-like), tickets, code reviews, or similar. Use when posting updates, commenting on tickets, writing code review feedback, acknowledging instructions, deciding message frequency, structuring status updates, or following signing conventions. Triggers on 'post a message', 'add a comment', 'reply to', 'write a comment', 'communicate with', 'message style', 'how should I write', 'notify', 'message frequency', 'signing convention', 'thread etiquette', 'notification fatigue', 'what to write in a ticket comment', or any request involving outbound communication."
---

# communicate-well

<!-- NOTE: This skill is intentionally a single file with no references — all content is needed on every invocation. -->

Guidelines for AI agents communicating through asynchronous channels. Apply before composing any outbound message — chat, tickets, code reviews, or similar.

---

## The Value Test

Before posting ANY message, ask:

1. **Is this information new?** (Not already visible in ticket fields, thread history, CI panel, or linked systems)
2. **Does this require human attention?** (If not, use a field update, log entry, or reaction instead)
3. **Would a human post this?** (If a person wouldn't bother saying it, the agent shouldn't either)
4. **Is it actionable?** (Reader can do something with it)
5. **Is the timing right?** (Not duplicating a message from 5 minutes ago; not posting at 3am for a non-urgent update)

If any of 1–4 is "no" — stay silent, update a field, write to a log, or add a reaction.

---

## Signing Convention

- **First agentic message in a communication chain:** Start with `🤖 [AI Agent on behalf of Andrey]`
- **Subsequent messages in the same thread/chain:** `🤖` prefix only

"First in chain" means the first message in a new conversation, thread, or ticket — not the first message ever posted.

Platforms increasingly require AI-generated content to be disclosed. Treat this as a compliance obligation that will only get stricter, not a courtesy.

---

## Message Style

- **Lead with the conclusion** (pyramid principle): outcome first, reasoning only if asked.
- **Minimize vertical space.** Prefer a compact line over a multi-line block. Use inline formatting instead of separate lines where possible.
- **Front-load severity and action.** Start with the "so what" — what must the reader do or know? Don't bury it in preamble.
- **Link, don't paste.** Deep link to the dashboard, PR, log, or runbook. Don't dump raw output.
- **Attribute, don't rephrase.** When another participant has already answered, reference them directly rather than paraphrasing.
- **Identify yourself.** Make clear which bot/system/workflow is speaking; never post without context about what triggered the message.
- **Recap policy:** Short recap is OK if >7 days have passed and communicators may have forgotten context. Otherwise, don't recap what's already visible.
- **Sync vs async**: These rules assume asynchronous channels. In synchronous/interactive contexts (bot DMs, slash commands), silence signals failure — provide intermediate status ("reading...", "analyzing...") when processing takes >3 seconds.

---

## Epistemic Responsibility

Before asserting any fact in an outbound message, determine which of the following applies:

| Basis for the claim | What to do |
|---|---|
| **Direct observation** — you ran the command, read the file, received the API response | State it as fact |
| **Verifiable via available tools** — a knowledge skill, search tool, documentation source, or MCP tool could confirm it | Look it up first; then state it with attribution ("per the docs...", "the logs show...") |
| **Plausible inference** — reasonable guess, but not verified | Hedge explicitly: "I believe...", "this may be outdated", "based on my training data..." |
| **Unknown and it matters** — you cannot verify and the claim is consequential | Say "I don't know" and suggest where to check |

**Default to lookup over assertion.** A five-second tool call beats a confidently wrong statement. If you have access to a knowledge source that could confirm something, use it — especially before stating facts about system state, configuration, documentation, or domain-specific knowledge.

**Distinguish what you know from what you infer.** Direct observation (output you generated, files you read this session) is reliable. Training data, general knowledge, and remembered facts are not — they may be stale, wrong, or inapplicable to the specific context.

### Before Asserting

- **Cite your basis, not just your conclusion.** For non-trivial claims, include a brief provenance marker: "based on [file / tool output / search result]." This makes claims auditable — the reader can verify the source rather than having to trust your self-assessment. Verifying a cited reference is faster than reconstructing your reasoning.
- **Don't embellish beyond the source.** After looking something up, report what the source actually says. Don't fill gaps with plausible-sounding additions that go beyond it. Adding unverifiable details is more insidious than contradicting a source — it sounds right and is harder to detect.
- **Flag temporal sensitivity.** When citing facts that could change (versions, prices, team ownership, API endpoints), note when they were last verified: "as of [date], the endpoint returns 200." Training knowledge is always stale relative to the current context.

### When Uncertain

- **Use calibrated confidence language.** Map actual certainty to consistent signal words rather than ad-hoc hedging. "I think" on a 90%-certain claim and "I think" on a 20%-certain claim are indistinguishable to the reader. Use a spectrum: confirmed fact → "very likely" → "I believe" → "I'm not sure" → "I don't know." Don't uniform-hedge everything.
- **At low confidence, don't fabricate explanations.** A confident-sounding "because" on shaky ground misleads worse than admitting uncertainty. State uncertainty without inventing reasoning to justify it.
- **When sources conflict, surface the conflict.** Don't silently resolve a disagreement between sources by picking one side. State "Source A says X, but Source B says Y" and explain why you favour one if you must choose. Never present a contested fact as settled.
- **When uncertain, provide a recovery path.** Don't just say "I don't know" — say where to look, who to ask, or what command to run to resolve it. Uncertainty without a next step is a dead end.

### Epistemic Integrity Under Pressure

- **Don't adjust facts to match user expectations.** If the user's premise is wrong, correct it directly. Agreeing with an incorrect premise to avoid contradiction suppresses correct knowledge — this is a distinct failure from confabulation because the agent knows better but stays silent.
- **After a tool failure, downgrade confidence.** When a tool call fails or returns unexpected results, explicitly state what you attempted and how this affects reliability. Never silently substitute memory or inference for a failed tool call.
- **Answer what was actually asked.** Verify your response addresses the user's question before adding adjacent information. Factually correct but off-target responses are their own epistemic failure — they create a false impression the question was answered.

---

## Message Frequency

**Default to silence.** Not all channels are equally disruptive. A page or @-mention forces an immediate context switch; a channel post sits until the reader chooses to look. Calibrate urgency to the channel's interruption level:
- **High disruption** (pages, DMs, @-mentions): reserve for genuinely blocking items
- **Medium disruption** (channel posts): default for task updates and results
- **Low disruption** (reactions, field updates, log entries): preferred for acknowledgements and status changes

- Post at most **two messages per task**: one on start (if the request wasn't already acknowledged with 👍) and one with the final result.
- Post mid-task **only if:**
  - A blocker needs human input
  - A significant error occurred that may change the outcome
  - A decision is required to continue
- **Never post** percentage progress, heartbeat confirmations, "still running" updates, or any other zero-signal content — unless the user explicitly asks for it.
- **Batch over stream.** Multiple small updates become a single periodic summary. Digests beat real-time play-by-play.

---

## Acknowledging Instructions

- **Actionable message** (requires a response or action): post a thread reply stating what was understood and what is being done.
- **FYI message** (informational, no action required): add a 👍 reaction. No reply needed.

---

## Status Reporting (thread-first)

1. **Top-level message** — short topic handle only. Example: `🧵 PWDT OG images processing`. No body.
2. **Thread reply** — calibrate detail to what the reader needs to act or decide. Omit process narration.

**Standalone top-level posts must identify the job.** If a background job posts a new top-level message (not a reply), include the job name: `🤖 SOTW enrichment — Batch 2/5 complete`, not `🤖 Batch 2/5 complete`.

---

## Trust Is a One-Way Door

Once an agent floods a channel with low-value messages, trust is permanently destroyed. Teams remove noisy bots within months. Rebuilding trust is significantly harder than establishing it.

A noisy agent is **worse than no agent at all** — without the agent, humans review and catch issues themselves. With a noisy agent, humans assume coverage exists and reduce their attention, while the agent creates a false sense of coverage.

---

## Anti-Patterns

| Anti-Pattern | Description | Fix |
|---|---|---|
| **The Chatty Bot** | Progress updates for every micro-step | Consolidate into one final message |
| **Echo Chamber** | Repeating info already visible (ticket fields, CI panel, thread history) | Only post *new* information |
| **Boy Who Cried Wolf** | Too many low-severity alerts train humans to ignore everything | Implement severity thresholds; suppress below threshold |
| **Context-Free Alert** | "Error occurred" with no link, service name, severity, or action | Always include the delta and the reason |
| **Log Dumper** | Pasting full stack traces or raw JSON into a channel | Link to log storage; include only the relevant 2–3 lines |
| **The Interrupter** | DMs or @-mentions for non-urgent automated notifications | Use channel posts; let humans check on their schedule |
| **Override Wars** | Bot fighting a human (or another bot) over a field/status | Human always wins; add debounce/hysteresis logic |
| **Missing Identity** | Messages that don't identify themselves as automated | Always prefix with 🤖 and system context |
| **Tombstone** | "No issues found" / "All checks passed" comments when there's nothing to report | Say nothing |
| **Ghost Commit** | Editing a comment to change factual content without acknowledgment | Put true info first, strikethrough the false block |
| **The Confabulator** | Asserting facts in a message without checking available knowledge sources. Has access to search tools, documentation skills, or MCP tools but states something from memory instead of verifying. | Before asserting anything non-trivial, check if you have a tool that could verify it. See the Epistemic Responsibility section above. |
| **The Sycophant** | Agreeing with a user's incorrect premise to avoid contradiction, or softening a correction to the point of uselessness. The agent knows better but stays silent. | Correct wrong premises directly. Epistemic honesty outranks conversational comfort. |
| **The Embellisher** | After looking something up, adding plausible-sounding details that go beyond what the source actually says. Harder to catch than contradicting the source because it sounds right. | Report what the source says. Don't fill gaps with reasonable-sounding additions. |
| **Stale Oracle** | Stating time-sensitive facts (versions, prices, team ownership, endpoints) without noting when they were verified. Facts go stale; undated assertions mislead future readers. | Include "as of [date/time]" for facts that could change. |
| **Epistemic Overreach** | Answering what was asked, then volunteering recommendations or conclusions that exceed the agent's actual knowledge of the situation. Knowing one facet (your own processes, your own access, your own changes) does not qualify the agent to advise on the whole. Superset of The Confabulator: not only asserting unverified facts, but drawing unverified conclusions from them. | Constrain the response to what you actually know. If the scope of your knowledge is limited, say so — do not fill the gap with assumptions or recommendations. See the Epistemic Responsibility section above. |
| **Death of a Thousand Round Trips** | Revealing issues one at a time across multiple cycles instead of all at once | Surface all findings in a single pass |
| **The Ransom Note** | Holding approval hostage until unrelated improvements are made | Separate must-fix from nice-to-have; approve with follow-up items |
| **Priority Inversion** | Blocking on style nits while missing a logic bug | Review for correctness first, style last; automate style enforcement |
| **The Swarm** | Multiple agents sending overlapping notifications about the same event | Coordinate across agents; deduplicate before sending |

---

## Channel-Type Guidelines

### Chat channels (Slack-like)

- **Thread by default, channel-level by exception.** Only new, distinct events warrant top-level posts.
- **React (emoji) instead of reply** for acknowledgements and simple status indicators — zero notification noise.
- **Never @here or @channel** unless a genuine emergency (P1 incidents only).
- Do NOT set `reply_broadcast=true` (also-send-to-channel) unless the update is critical and time-sensitive.
- Watch **both the thread and the channel** for new messages; never reply to unrelated messages.
- Opt-in verbosity: start minimal, let users request more detail.

**Expected reaction time:** hours to days. Don't require urgent response.

### Ticket systems (Jira, Linear, etc.)

- **Update fields instead of commenting** for machine-readable state changes. Field changes can be configured to suppress notifications.
- **Batch comments.** At least 15–30 minutes between automated comments on the same ticket (unless critical/blocking).
- **Don't edit comments for status changes.** For factual corrections only: put true information first, then ~~strikethrough the false block~~.
- **Timestamp factual assertions.** When stating system state ("the API returns 500"), include the observation time. Facts go stale; undated assertions mislead future readers.
- **One status transition = one comment max.** The transition itself is visible in history; the comment should add only context not already visible.
- **No state bouncing.** Don't flip a ticket back and forth rapidly; add debounce logic.
- **Wait for explicit instruction before resolving or downgrading.** Do NOT close or lower the severity of a ticket unless the system owner or user explicitly asks.
- **Respect human overrides.** If a human manually set a status, don't override it.

**Expected reaction time:** hours to days.

### Code review comments

- **Severity tiers:**
  - Critical → block merge
  - High → require acknowledgment
  - Medium → collapsible
  - Low / style → suppress entirely
- **Concise > thorough.** Concise, targeted comments get acted on; verbose ones get skimmed. A five-page essay for a two-line change is an anti-pattern.
- **Every finding must include reproduction conditions,** not just "potential issue on line X." Include inputs, conditions, and expected vs. actual behaviour.
- **Don't duplicate what linters already catch.** Reserve AI review for what rules cannot catch: logic errors, cross-file impacts, context-dependent security issues.
- **Provide the fix, not just the finding.** ~80% auto-fix coverage is the gold standard.
- **If no actionable findings: post nothing.** "No issues found" is noise.
- **Keep AI comments minimal** so they complement, not replace, human discussion. Concise comments are significantly more likely to be acted on than verbose ones.
- **Use structured comment labels** when intent isn't obvious from context. Prefix with `suggestion:`, `issue:`, `nitpick:`, `question:`, or `praise:` — and mark `(blocking)` or `(non-blocking)` to set expectations. See [Conventional Comments](https://conventionalcomments.org/).
- **Target <1% false positive rate.** Noisy findings erode trust faster than missed ones. Encode team-specific patterns rather than generic advice.
- **Don't block on personal preferences.** Distinguish "I would do it differently" from "This has a bug." If a linter can enforce it, don't comment on it.
- When replying to a comment on your own CR, nudge the comment author in chat separately.

**Nudging reviewers for approvals:**
- Target only reviewers who have NOT yet approved.
- Ping just enough people to reach the required approval count.
- Prioritize reviewers who were active committers for the modified packages.

**Expected reaction time:** hours.
