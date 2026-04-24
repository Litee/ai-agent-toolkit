---
name: write-well
description: "Use when composing or editing any written document — design docs, RFCs, emails, proposals, reports, README files, postmortems, status updates, or meeting notes. Triggers on 'write a document', 'draft', 'compose', 'edit this text', 'improve my writing', 'make this clearer', 'review my draft', 'rewrite', 'proofread', 'too wordy', 'tighten this up', or any request involving creating or improving written text. Does NOT cover channel etiquette — use communication:communicate-well for that."
---

# write-well

Universal principles for clear, effective professional writing. Apply when composing or editing any document.

---

## The Quality Test

Before finalizing any document, every section must pass:

1. **Does it say one thing clearly?** If you cannot state the section's point in one sentence, rewrite it.
2. **Does the reader need this?** Cut anything that serves the writer's ego but not the reader's understanding.
3. **Is every word earning its place?** Read each sentence and ask what would be lost if you deleted it. If the answer is "nothing" -- delete it.
4. **Would you read this?** If you would skim past it, your reader will too.

---

## Core Principles

### 1. Clarity Above All

Clear writing reflects clear thinking. If the reader is confused, the writer has failed -- not the reader.

- One idea per sentence. One topic per paragraph.
- Subject and verb close together. Do not insert long parenthetical phrases between them.
- If a sentence needs re-reading, it needs rewriting.

### 2. Cut Ruthlessly

"Omit needless words." -- Strunk & White. "If it is possible to cut a word out, always cut it out." -- Orwell.

- First drafts can typically lose 30-50% of their words without losing meaning.
- Delete throat-clearing ("It is important to note that...", "As we all know...", "In order to...").
- Replace nominalizations with verbs: "made a decision" becomes "decided." "Conducted an investigation" becomes "investigated."
- Kill filler qualifiers: "very," "really," "quite," "rather," "basically," "actually," "essentially," "simply," "just," "easy," "obviously."
- Never use "simply," "just," "easy," or "obviously" to describe a process -- what is obvious to you may not be to the reader, and these words make readers feel inadequate when they struggle.
- Cut redundant pairs: "full and complete," "each and every," "first and foremost," "true and accurate." When two words mean the same thing, pick one.
- Don't announce what you're about to say -- just say it. "I want to point out that there are two risks" becomes "There are two risks."

### 3. Use Active Voice

Name the actor. Push forward.

- "The team shipped the fix" not "The fix was shipped by the team."
- Passive voice is acceptable when the actor is unknown, irrelevant, or deliberately de-emphasized. Otherwise, use active.
- Watch for hidden passives: "mistakes were made," "it was decided," "the ball was dropped."

### 4. Be Concrete and Specific

Specific beats general. Data beats assertion.

- "Cut processing time from 3 hours to 20 minutes" not "significantly improved performance."
- "14,200 users received errors over 47 minutes" not "some users were affected."
- Concrete words ("dog," "server," "crashed") activate richer mental representations than abstract ones ("entity," "resource," "degraded") and are easier to remember.
- Replace weasel words with data or a statement of intent. Weasel words -- should, might, could, often, generally, usually, probably, significant, soon, some, most -- weaken claims. "A significant proportion may be affected" becomes "This affects 23% of sellers." "We should see improvement soon" becomes "We will reduce latency by 40ms in Q2."
- **Organize evidence before you write.** For each argument, ask: What data, examples, or expert findings support it? If you cannot name at least one concrete piece of evidence, the argument is an assertion -- cut it or find the evidence first. Anecdotal examples are acceptable only when they illustrate a broader pattern, not as the sole support.
- **Know your reasoning direction.** Deductive: start from a general principle and show this case fits it. Inductive: show a pattern across specific cases and draw the generalization. Either works; mixing them mid-argument confuses the reader.

### 5. Use Simple Words

Prefer the common word. Anglo-Saxon over Latin.

| Instead of | Write |
|-----------|-------|
| utilize | use |
| leverage | use |
| facilitate | help |
| commence | start |
| terminate | end, stop |
| approximately | about |
| in order to | to |
| due to the fact that | because |
| at this point in time | now |
| a large number of | many |
| in the event that | if |
| prior to | before |
| it is necessary that | must |
| cannot be avoided | must |
| for the purpose of [-ing] | to [infinitive] |
| under circumstances in which | if |

### 6. Revise

First drafts are never good enough. Rewriting IS writing.

- Write fast, edit slow. Separate composition from revision.
- Read aloud. If it sounds awkward spoken, it reads awkwardly too.
- Delete the first paragraph. The real content usually starts at paragraph two.

### 7. Write for the Reader

Every sentence must serve the reader, not the writer.

- Know your audience before you start: Who reads this? What do they know? What do they need to do with it?
- Executives want decisions and impact. Engineers want methodology and detail. Calibrate.
- Front-load the most important information. Respect the reader's time.

---

## Structure & Organization

### Lead with the Answer

Always. Whether it is a one-line email or a 20-page design doc, the first sentence should carry the main point.

- **Pyramid Principle (Minto):** Start with the answer/recommendation, then group 2-5 supporting arguments beneath it, each backed by evidence.
- **Inverted Pyramid (journalism):** Present information in descending order of importance. The document can be truncated from the bottom at any point and still function.
- **BLUF (Bottom Line Up Front):** State your conclusion, recommendation, or request in the first sentence.

### Use the SCQA Framework for Introductions

When a document needs context before the answer:

1. **Situation:** What the reader already knows (the status quo)
2. **Complication:** What changed or went wrong (creates tension)
3. **Question:** The question the reader naturally asks
4. **Answer:** Your thesis or recommendation

### Progressive Disclosure

Layer depth for mixed audiences:

- Executive summary (for scanners) -> Section summaries -> Detailed content -> Appendices/raw data
- TL;DR -> Full analysis -> Supporting evidence
- **Back pocket data:** Keep supporting data one level below your appendices -- available for reference but not in the document. If the format supports references or links, point to this evidence rather than burying it. When presenting, have it ready for questions.

### Structural Rules

- **Acronyms:** Spell out on first use, then abbreviate. "Customer Service Associate (CSA)" -- then "CSA" after. Limit total acronyms per document; too many force the reader to keep a mental glossary.
- **Headings:** Use hierarchical headings. Never skip levels. Test: read only the headings -- do they tell the story?
- **Paragraphs:** 3-5 sentences each. One idea per paragraph. Front-load the key point in the first sentence.
- **Lists:** Use numbered lists for sequences, bullets for non-ordered items. Keep parallel grammatical structure.
- **Cognitive load limit:** No more than 5-7 items at any level of hierarchy. If a section has 10 subsections, regroup.
- **Scanability:** Bold key terms. Use whitespace as chunk delimiters. Readers scan in an F-pattern -- front-load the left margin.

---

## Style & Voice

### Sentence Construction

- **Vary sentence length.** Mix short sentences with longer ones. This creates rhythm. Uniform length -- the hallmark of weak writing -- flatlines the reader's attention.
- **Start with the subject.** Subject-verb-object is the default parsing path. Deviations cost cognitive effort.
- **Use transitions sparingly.** "Also" and "But" beat "Furthermore" and "Nevertheless." Often no transition is needed at all -- just start the next sentence.

### Word Choice

- Use contractions in informal contexts ("don't" not "do not").
- Write with nouns and verbs, not adjectives and adverbs. If you keep an adjective or adverb, back it with data: "Sales grew quickly" becomes "Sales grew 450bps from $XX to $YY in Q4."
- Avoid cliches. If you have seen the phrase a hundred times, your reader has seen it a thousand.
- Prefer one-syllable and two-syllable words when they carry the same meaning as longer alternatives.

### Tone

- Have a consistent voice. Authoritative, conversational, technical -- pick one and commit.
- State opinions when you have them. Hedging everything weakens the entire document.
- Be direct. "This approach is wrong because X" is clearer than "One might argue that this approach has certain limitations."

### Converting Outlines to Prose

Bullet points are scaffolding, not the document. When an outline needs to become narrative:

- Give each paragraph a topic sentence that states its one idea.
- Absorb bullet content into sentences with transitions ("This reduces costs because...", "As a result...", "The second factor is...").
- Vary sentence length around the information density -- dense evidence deserves longer sentences; transitions can be short.

**Before (bullet points):**
> The benefits of the new system include:
> - 65% reduction in processing costs
> - 75% decrease in time spent on expense reporting
> - Elimination of manual data entry errors
> - Increased employee satisfaction

**After (narrative prose):**
> The new system reduces processing costs by 65% and cuts the time employees spend on expense reporting by 75%. It eliminates manual data entry errors, which currently affect 15% of reports. Faster reimbursements and a simpler process raise employee satisfaction.

---

## AI Writing Hygiene

When AI generates or assists with text, actively eliminate these patterns:

### Structural Tells

- **Uniform sentence length.** Vary deliberately: mix 5-word fragments with 25-word compound sentences.
- **Predictable paragraph template.** Break the topic-support-conclusion formula. Vary paragraph lengths.
- **Over-structuring.** Not every section needs a subheading. Let prose flow when appropriate.
- **Symmetrical lists.** Vary list item lengths. Real lists are messy.

### Vocabulary Ban List

Search and replace these AI-default words:

| AI Default | Human Alternative |
|-----------|-------------------|
| delve / dive into | look into, explore, examine |
| moreover / furthermore | also, plus, and |
| crucial / vital / essential | important, key, matters |
| robust | strong, solid, reliable |
| seamless | smooth, easy |
| leverage | use, take advantage of |
| comprehensive | thorough, complete, full |
| navigate | deal with, handle, figure out |
| landscape / realm / tapestry | field, area, world |
| foster / cultivate | encourage, build, support |
| streamline | simplify, speed up |
| multifaceted | complex, varied |
| embark | start, begin |
| In today's [X] world | [delete entirely] |
| It's worth noting that | [just state the thing] |
| It's important to note | [just state the thing] |
| In conclusion | [just conclude] |
| Let's dive in / explore | [just start] |

### Tone Tells

- **Kill relentless positivity.** Not everything is "exciting" or "powerful."
- **Drop excessive hedging.** Replace "it could potentially be argued that" with a direct statement.
- **Have opinions.** AI that presents "both sides" of everything reads as evasive, not balanced.
- **Allow imperfection.** Sentence fragments, starting with "But," one-word paragraphs -- these read as human.
- **Cut the first paragraph.** AI throat-clearing is worst at the opening. The substance usually starts at paragraph two.

---

## Editing Checklist

Apply in three passes:

### Pass 1: Structure (zoom out)

- [ ] Does the document lead with its main point?
- [ ] Can a reader get the gist from headings alone?
- [ ] Is every section in the right order?
- [ ] Are there sections that can be cut entirely?
- [ ] Does each paragraph have one clear idea?

### Pass 2: Clarity (sentence level)

- [ ] Is every sentence in active voice (where appropriate)?
- [ ] Are subject and verb close together?
- [ ] Are there sentences that need re-reading? Rewrite them.
- [ ] Are nominalizations converted to verbs?
- [ ] Are concrete specifics used instead of vague abstractions?

### Pass 3: Conciseness (word level)

- [ ] Can any sentence be deleted without losing meaning?
- [ ] Are filler words and phrases removed?
- [ ] Are there any AI vocabulary words that need replacing?
- [ ] Is the document 30% shorter than the first draft?
- [ ] Read aloud: does it sound natural?
- [ ] When rewriting someone else's text: does the output preserve their original formatting (bullets stay bullets, prose stays prose) unless restructuring was explicitly requested?

---

## Format-Aware Guidance

When writing specific document types, apply the core principles above plus these format-specific guidelines:

### Design Documents

- Write BEFORE coding. The document forces you to think through edge cases.
- Lead with the "why" -- problem statement and business motivation first.
- The "Alternatives Considered" section is often the most valuable part -- it records why you chose path A over B.
- Include diagrams. Architecture diagrams communicate structure faster than prose.
- Aim for 5-10 pages. Longer means the scope is too broad -- split it.
- Key sections: Overview, Goals/Non-Goals, Background, Detailed Design, Alternatives Considered, Security, Testing & Rollout, Open Questions.

### RFCs

- Keep it to one page. Long RFCs do not get read.
- Name 2-4 explicit reviewers with a deadline. "The team" means nobody.
- Silence equals consent after the deadline.
- Separate the problem from the solution -- spend equal space on each.
- Record the final decision with date and rationale after review.
- Key sections: Context, Proposal, Alternatives, Key Decisions, Risks, Open Questions, Decision Record.

### Emails and Messages

- Subject line = the action you need. "Decision needed: API versioning approach by Friday" not "Quick question."
- First sentence = the ask or conclusion. Do not build up to it.
- If longer than 5 sentences, use bullet points.
- One email = one topic. Multiple topics get split into multiple emails.
- End with a clear call to action and deadline.

### Postmortems

- Blameless. Focus on systemic factors, not individuals.
- Hold within 24-48 hours while memory is fresh.
- Use Five Whys to get past the proximate cause to the root cause.
- Quantify impact precisely with numbers, not "some users were affected."
- Every action item needs an owner, deliverable, and due date.
- Track action item completion -- the most common failure is thorough postmortems with actions that never get done.

### Status Updates

- Lead with the headline: on track, at risk, or blocked.
- Use RAG (Red/Amber/Green) status indicators consistently.
- Be honest about risks early. Always-green until launch week destroys trust.
- Separate accomplishments from next steps from blockers.
- Include explicit asks if you need decisions or unblocks.

### Meeting Notes

- Capture decisions and actions, not dialogue.
- Bold action items with owner and due date.
- Record context behind decisions ("chose Kafka over SQS because..."), not just conclusions.
- Distribute within 24 hours.

---

## Anti-Patterns

| Anti-Pattern | Description | Fix |
|---|---|---|
| **The Wall of Text** | No headings, no breaks, no visual hierarchy | Add structure: headings, lists, whitespace |
| **Throat-Clearing** | Two paragraphs of context before the point | Delete everything before the main point, add context after |
| **The Hedge Maze** | Every statement qualified into meaninglessness | State the thing directly. Add caveats only where genuinely needed |
| **Jargon Soup** | Dense with undefined acronyms and technical terms | Define on first use or use plain alternatives |
| **The Kitchen Sink** | Covers every angle instead of having a focused argument | Cut to the 3-5 most important points |
| **Passive Evasion** | "Mistakes were made" / "It was decided" | Name the actor. Use active voice |
| **The Zombie Nominalization** | "Implementation of" / "Utilization of" / "Facilitation of" | Use the verb: implement, use, help |
| **Copy-Paste AI** | Uniform sentence length, banned vocabulary, relentless positivity | Apply the AI Writing Hygiene section |
| **The Circular Conclusion** | Conclusion restates the introduction verbatim | End with the implication, next step, or open question |

---

## Related Skills

- **`writing:write-technical-design`** — Applies the principles here to technical design documents (HLD/LLD). Use alongside this skill when drafting architecture proposals, API specs, or system design docs.
- **`communication:communicate-well`** — Covers async channel etiquette: when to post, where to post, how to structure messages in Slack, tickets, and code reviews. Complements this skill for any written communication that goes through an async channel.
- **`communication:write-good-emails`** — Dedicated guidance for professional email: subject lines, tone calibration, follow-up strategy, and prompting AI for email drafts.
