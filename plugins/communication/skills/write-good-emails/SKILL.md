---
name: write-good-emails
description: "Use when composing, editing, or prompting AI to draft any email — professional, cold outreach, follow-up, difficult conversations, bad news, escalation, or announcements. Triggers on 'write an email', 'draft an email', 'email template', 'follow-up email', 'cold email', 'email subject line', 'difficult email', 'rewrite this email', or any request to compose or improve an email. For general writing clarity use writing:write-well; for chat/tickets/code reviews use communication:communicate-well."
---

# write-good-emails

<!-- NOTE: This skill is intentionally a single file with no references — all content is needed on every invocation. -->

Guidelines for writing effective professional emails. For general writing clarity, see **writing:write-well**. For async channel etiquette (Slack, tickets, code reviews), see **communication:communicate-well**.

---

## The Email Test

Before sending any email, every item must pass:

1. **Can the subject line stand alone?** If the recipient reads only the subject, do they know what to do or why this matters?
2. **Is this one topic?** If you need "and" to describe the email's purpose, split it into two emails.
3. **Is the ask in the first two sentences?** If the reader must scroll to find what you need, rewrite from the top.
4. **Is there a deadline?** "When you get a chance" means never. Every ask needs a when.
5. **Would this survive a phone screen?** Long paragraphs, wide tables, and buried links break on mobile. Reformat before sending.

---

## Anatomy of an Effective Email

### Subject Line

The most important line. If it fails, nothing else matters.

| Pattern | Example | When |
|---------|---------|------|
| Action + Topic + Deadline | "Approve needed: Q3 budget by Thursday" | You need something done |
| Status + Topic | "Resolved: Checkout latency spike" | Status updates |
| FYI + Topic | "FYI: Expense policy change effective May 1" | Informational, no action |
| Question + Topic | "Quick question: API versioning approach" | Seeking input, low urgency |

**Rules:**
- 6-10 words. Longer subjects get truncated on mobile and get fewer opens.
- Front-load the action verb. "Decision needed" beats "I wanted to get your thoughts on."
- Never: "Following up," "Quick question," "Hey," "Important," "Checking in." These are invisible.
- Studies suggest personalized subjects boost open rates and reply rates — reference something specific to the recipient.

### Opening Line

State the ask or conclusion in the first sentence. One sentence of context maximum before the point.

Never: "I hope this email finds you well." "Per my last email." "As discussed." "Just circling back."

### Body

- BLUF first: conclusion or request before reasoning. (See **writing:write-well** for the full pyramid principle.)
- Under 200 words. Research indicates longer emails receive fewer replies.
- If longer than 5 sentences, switch to bullet points.
- One screen on mobile = the entire email.
- One idea per paragraph. Two or three sentences max.

### Call to Action

Every email ends with one explicit ask and a deadline.

**Good:** "Please approve the proposal in Confluence by EOD Thursday."  
**Bad:** "Let me know your thoughts." "Happy to discuss." "Looking forward to hearing from you."

If you need multiple actions: number them, assign owners, include deadlines for each.

### Signature

Keep it under 4 lines. Name, title, one contact method. No inspirational quotes. No legal disclaimers in casual internal email.

---

## Tone Calibration by Audience

| Recipient | Tone | Do | Don't |
|-----------|------|----|-------|
| Executive / skip-level | Concise, data-driven | Lead with business impact and decision needed | Explain implementation details or justify your process |
| Direct manager | Direct, transparent | Flag risks early; include your recommendation | Hide problems or hedge excessively |
| Peer / teammate | Collaborative, casual-professional | Use contractions; be direct about asks | Over-formalize or pad with pleasantries |
| Client / external | Professional-approachable | Mirror their formality; proofread twice | Use internal jargon, acronyms, or Jira ticket numbers |
| Cold outreach | Respectful, value-first | Lead with what is in it for them; 3-4 sentences max | Open with your credentials or company history |
| Vendor / support | Factual, specific | Include account IDs, error codes, screenshots | Write a narrative; get to the point immediately |

**Rules:**
- Mirror the recipient's formality level. If they write formally, write formally.
- When unsure, default one notch more formal than you think is needed.
- Adjust as the relationship develops — match the register of their last email to you.

---

## Prompting AI for Email Drafts

### Minimum Viable Prompt

Every AI email prompt needs four elements:

1. **Role:** "You are a [title] at [company type]"
2. **Context:** Who you are writing to, your relationship, any relevant prior interactions
3. **Task:** What kind of email, what outcome you need
4. **Constraints:** Desired tone, length limit, what to include or exclude

**Weak:** "Write a follow-up email to a client."  
**Strong:** "You are a software account executive. Write a follow-up email to a VP of Engineering at a mid-size SaaS company. We met at a conference two weeks ago and they expressed interest in our monitoring product but haven't responded to my first email. Tone: professional but direct. Under 100 words. One specific CTA: 15-minute call this week."

### Advanced Techniques

- **Feed examples of your own writing** (2-3 past emails) so AI can calibrate your voice.
- **Break complex emails into steps:** "First list the key points I need to make. Then arrange them in order of importance. Then draft the email." This reduces AI hallucination on multi-faceted situations.
- **Tell AI to ask for missing context:** Add "Ask me for any information you need before drafting" to prevent the AI from inventing details.
- **For sensitive situations:** Tell the AI your emotional state and what you *want* to say, then ask it to translate into professional language.

### After AI Generates

Treat AI like a capable intern — review everything before sending:

- Read aloud. If it sounds robotic, it is.
- Add one personal or specific detail the AI could not have known.
- Verify every fact, name, date, and number.
- Remove: "I hope this email finds you well," "Furthermore," "Please do not hesitate to," "It is worth noting that."
- Apply the AI Writing Hygiene checklist from **writing:write-well** (vocabulary ban list, structural tells).

---

## Difficult Email Scenarios

### Delivering Bad News

1. Lead with the decision, not the reasoning. Recipients need the conclusion first.
2. State the impact in one sentence.
3. Offer the next step or alternative immediately.
4. Apologize once, briefly, if warranted. Do not repeat it.
5. Do not hedge the decision. "We've decided" not "we're considering" or "it seems like we may need to."

### Pushing Back or Saying No

1. Acknowledge the request in one sentence.
2. State your position and one reason. One reason is more persuasive than three.
3. Propose a concrete alternative or partial yes if possible.
4. Keep the entire email to 4 sentences. Lengthy justifications invite debate.
5. Do not apologize for having a position.

### Escalation

1. First sentence: the issue and its business impact.
2. Second sentence: what you have already tried and when.
3. Third: the specific decision or action you need, from whom.
4. CC the minimum necessary people. Every extra CC reduces the chance the right person acts.
5. Do not escalate before attempting direct resolution. Document that you did.

### Cold Outreach

1. 3-4 sentences maximum. No exceptions.
2. Open with something specific and relevant to them (their company, recent news, shared connection).
3. One sentence on the value — what is in it for them, not what your product does.
4. One low-commitment CTA: 15-minute call, a yes/no question, a link to one resource.
5. No attachments on first contact.

### Following Up on Silence

1. Reply to the original thread. Never start a new email chain.
2. Add one new piece of information or reframe the ask. Never just "bumping this."
3. Make the CTA easier: shorter time commitment, simpler answer format.
4. Shorten the email with each attempt. If the first was 150 words, the follow-up should be 75.

---

## Follow-Up Strategy

| Attempt | Timing | What to do |
|---------|--------|------------|
| Follow-up 1 | 2-3 business days | Reply to thread, add new info, same CTA |
| Follow-up 2 | 5-7 days after first | Shorten, simplify CTA, reframe if needed |
| Follow-up 3 | 5-7 days after second | Change angle or channel (try Slack, phone) |
| Stop | After 3 attempts | Take the hint; move to a different path |

**The first follow-up is the highest-leverage email you can send.** Most people do not follow up at all — research consistently shows that a single follow-up can significantly boost reply rates.

**Rules:**
- Always reply to the original thread. Do not start fresh.
- Each follow-up must add something new: new information, new framing, new deadline, or a different question.
- Never send "Just wanted to follow up." That is not a message, it is noise.
- If you need a response urgently: say so, say why, and say what happens if you do not hear back.

---

## Mobile and Formatting

Over 60% of emails are read on mobile. Format for the smallest screen first.

- **Preview text matters:** The first 40-90 characters after the subject appear in most email clients. Do not waste them on "Hi [Name]," or "I am writing to."
- **Paragraph length:** 2-3 sentences maximum. Walls of text on mobile mean no one reads past line two.
- **Links:** Put them on their own line with descriptive anchor text. Not "click here." Not raw URLs.
- **No tables in email body:** Tables break on mobile. Replace with bullet lists.
- **Bold sparingly:** Bold the action item or key date. If everything is bold, nothing is.
- **Scrolling test:** If your email requires more than two scrolls on a phone screen, it is too long.

---

## Anti-Patterns

| Anti-Pattern | Description | Fix |
|---|---|---|
| **The Buried Ask** | The request appears in paragraph 3 after two paragraphs of context | First sentence = the ask. Context follows |
| **Kitchen Sink Email** | Three unrelated topics in one email | One email = one topic. Split into separate threads |
| **Vague Subject Line** | "Quick question," "Following up," "Hey," "Important" | Action + Topic + Deadline formula |
| **Reply-All Bomb** | Reply All to a 50-person thread with "Thanks!" or a personal response | Reply to sender only unless the full list genuinely needs it |
| **Premature Escalation** | CC'ing a manager before talking to the person directly | Attempt direct resolution first. Escalate only after documented attempts fail |
| **The Novel** | 500-word email that could have been 100 words | Under 200 words. If it needs more, write a document and send a summary email with a link |
| **Passive-Aggressive CC** | Adding people to CC to apply social pressure, not for information | CC only people who need the information to act or decide |
| **Graveyard Subject** | Reusing an old subject thread for a new, unrelated topic | New topic = new email with a new subject line |
| **Disappearing CTA** | No clear ask, no deadline, ends with "Let me know your thoughts" | Explicit action + explicit deadline in the final sentence |
| **The Auto-Apologist** | "Sorry to bother you," "Sorry for the long email," "Sorry for the late reply" — as a reflex | Remove the apology. Respect the reader's time by being concise, not by pre-apologizing for the email's existence |
| **The AI Paste Job** | Sending AI-generated email without editing — wrong tone, hallucinated facts, robotic phrasing | Read every word aloud. Add one personal detail. Verify every fact. Remove AI vocabulary tells |
