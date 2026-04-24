---
name: write-technical-design
description: "Use when drafting or structuring technical design documents — HLD, LLD, architecture proposals, or technical specs. Triggers on 'write a design doc', 'draft a technical design', 'HLD', 'LLD', 'architecture document', 'technical proposal', 'system design document', 'design specification', 'technical spec', 'design review prep', or any request to create or structure a technical design. For general writing quality use writing:write-well alongside this skill."
---

# write-technical-design

Guides drafting of technical design documents section-by-section with engineering standards built in.

> For general writing quality — clarity, conciseness, active voice, cutting filler — apply the `writing:write-well` skill alongside this one.

---

## The Iron Law

```
PROBLEM FIRST. ONE RECOMMENDED SOLUTION. DIAGRAMS NOT WALLS OF TEXT.
```

Every design document exists to answer: "How should we build this, and why?" If a reader finishes your doc unsure of what you are proposing or why you chose it, the document has failed.

---

## Process

### Step 1: Determine Document Type

| Type | When to Use | Typical Scope |
|------|-------------|---------------|
| **HLD (High-Level Design)** | New system, major feature, cross-team initiative | Multiple components, architectural decisions |
| **LLD (Low-Level Design)** | Single component, API contract, data model change | Implementation details, schemas, exact interfaces |
| **Combined** | Smaller projects where splitting adds no value | Under ~2 months of work, single team |

**Auto-detect hints:**
- Multiple teams involved → HLD first
- Detailed API or schema specs needed → LLD
- Architecture decisions and tradeoffs → HLD
- Scope unclear → ask before writing

### Step 2: Gather Context

Before drafting any section, answer these five questions. Ask the user if the answers are not in the input.

1. **What problem are we solving?** (One sentence from the user/business perspective, not engineering)
2. **Who is the audience?** (Engineering team, cross-functional stakeholders, leadership?)
3. **What constraints exist?** (Timeline, existing systems, budget, compliance requirements)
4. **What has already been tried or ruled out?** (Prior art, previous approaches, known dead ends)
5. **What does success look like?** (Measurable outcomes that confirm the design works)

### Step 3: Draft Section by Section

For each section:
1. Ask the user for raw notes or bullets
2. Convert to structured narrative immediately
3. Flag any violations (vague requirements, missing diagrams, absent alternatives) before moving on
4. Confirm the section with the user before proceeding to the next

---

## HLD Sections

### 1. Problem Statement

**Format:** 1–3 paragraphs, written from the user or business perspective.

| Reject | Accept |
|--------|--------|
| "The current architecture doesn't scale" | "At peak load, the checkout service returns errors for 8% of requests, causing an estimated $50K/day in lost conversions" |
| "We need to redesign the data layer" | "Support agents spend 45 minutes per escalation reconstructing event history because logs are scattered across 6 separate systems" |

**Rules:**
- Lead with impact: who is affected, how, and at what scale
- Include quantified pain where possible (latency numbers, error rates, cost, time lost)
- No solution details here — only the problem

### 2. Requirements

**Format:** Functional + Non-Functional, each with explicit priorities.

```
## Functional Requirements
- [P0] Users can complete checkout in under 3 seconds for 99% of requests
- [P1] System supports order cancellation up to 30 minutes after placement
- [Stretch] Support split payments across two payment methods

## Non-Functional Requirements
| Requirement    | Target  | Current |
|----------------|---------|---------|
| Availability   | 99.95%  | 99.2%   |
| P99 latency    | <500ms  | 3.2s    |
| Throughput     | 10K TPS | 2K TPS  |
```

**Rules:**
- Every requirement must be testable
- Priorities (P0/P1/Stretch) prevent scope creep during review
- Non-functional targets must be specific numbers, not adjectives

### 3. In-Scope and Out-of-Scope

**Format:** Two explicit bulleted lists. Out-of-scope items include a reason.

| In-Scope | Out-of-Scope |
|----------|--------------|
| Read path latency optimization | Write path changes (separate initiative) |
| Primary region | Secondary regions (Phase 2) |
| Authenticated user flows | Guest checkout (deferred, low traffic) |

**Why this matters:** Without explicit boundaries, every reviewer will assume different scope. This section is the single source of truth for "are we doing X?"

### 4. High-Level Architecture

**Format:** Diagram first, then component descriptions.

**Must include:**
- Architecture diagram with all major components labeled
- Arrows showing data flow direction
- External dependencies and integrations visible
- Security trust boundaries marked

**Component descriptions:** 2–3 sentences each — what the component does, why it exists, what it communicates with.

**Diagram tools:** Prefer text-based formats that live in version control (Mermaid, PlantUML, draw.io XML). Avoid screenshots of whiteboard photos.

**Diagram checklist:**
- [ ] Every box is labeled
- [ ] Every arrow has a direction and a label
- [ ] External systems are visually distinct from internal ones
- [ ] No orphaned components (every box connects to at least one other)

### 5. Alternatives Considered

**Format:** One subsection per alternative, with a final decision rationale.

```
### Option A: [Name] — Recommended
**Description:** [1–2 sentences]
**Pros:** ...
**Cons:** ...

### Option B: [Name]
**Description:** [1–2 sentences]
**Pros:** ...
**Cons:** ...

### Option C: Do Nothing
**Why rejected:** [Why the status quo is unacceptable]

### Decision Rationale
[Specific reasons Option A was chosen over the alternatives]
```

**Rules:**
- Minimum 2 alternatives (plus "do nothing" when relevant)
- Cons must be specific — "not extensible" is not a con; "adding a new event type requires changes to 6 files" is
- The decision rationale is the most important part of this section

### 6. Risks and Mitigations

**Format:** Risk matrix.

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dependent service API changes during rollout | Medium | High | Pin to versioned API, add integration tests |
| Traffic spike exceeds provisioned capacity | Low | High | Load test to 2× expected peak before launch |
| Schema migration takes longer than maintenance window | Medium | Medium | Dual-write migration pattern, no hard cutover |

### 7. Security Considerations

**Must address:**
- Data classification: what data does this system handle, how sensitive is it?
- Authentication and authorization model
- Encryption at rest and in transit
- Audit logging requirements
- Key security boundaries and trust assumptions

If a full threat model is warranted, reference it rather than inlining it.

### 8. Milestones and Timeline

**Format:** Phased delivery table.

| Phase | Deliverable | Definition of Done | Target Date | Dependencies |
|-------|-------------|-------------------|-------------|--------------|
| 1 | API contract finalized | Reviewed and signed off by consumers | Week 2 | Requirements approval |
| 2 | Core implementation | All P0 tests passing, deployed to staging | Week 6 | Phase 1 |
| 3 | Production rollout | Canary at 5% for 48 hours with no regressions | Week 8 | Phase 2 |

**Rules:**
- Each milestone has a concrete deliverable, not a vague description
- "Definition of Done" removes ambiguity about when the phase is complete
- Callout dependencies between milestones explicitly

---

## LLD Additional Sections

When writing an LLD (standalone or combined), include all HLD sections plus:

### 9. API Specifications

**Format:** Full request/response schemas for every endpoint.

```
### POST /v1/orders

**Request:**
| Field      | Type          | Required | Description              |
|------------|---------------|----------|--------------------------|
| customerId | String (UUID) | Yes      | Authenticated customer   |
| items      | Array<Item>   | Yes      | Line items with quantity |

**Response:**
| Field   | Type          | Description                    |
|---------|---------------|--------------------------------|
| orderId | String (UUID) | Created order identifier       |
| status  | Enum          | CREATED, PENDING, or CONFIRMED |

**Errors:**
| Code | Condition             |
|------|-----------------------|
| 400  | Missing required field |
| 404  | Customer not found    |
| 409  | Duplicate order       |
```

**Rules:**
- Version the API from day one
- Include example request/response payloads for each endpoint
- Document every error code the caller might receive

### 10. Data Model

**Format:** Schema definition with access patterns.

```
### Table: orders

**Keys:**
- Partition key: customer_id (String)
- Sort key: order_id (String)

**Attributes:**
| Name         | Type    | Required | Description           |
|--------------|---------|----------|-----------------------|
| status       | String  | Yes      | Order status enum     |
| total_cents  | Integer | Yes      | Total amount in cents |
| created_at   | String  | Yes      | ISO 8601 timestamp    |

**Access Patterns:**
1. Get all orders for a customer → Query on partition key
2. Get orders by status → GSI on status attribute

**Migration Strategy:** [How existing data transitions to this schema]
```

### 11. Sequence Diagrams

Show at least:
- The happy path (successful end-to-end flow)
- A representative error path
- Any async or background processing flow

Label every arrow with the operation name and key payload fields.

### 12. Operational Considerations

| Aspect | Details |
|--------|---------|
| **Deployment** | Strategy (blue-green, canary, rolling), rollback procedure |
| **Metrics** | Key metrics to emit (latency, error rate, throughput) |
| **Alerts** | Conditions that page on-call (thresholds, duration) |
| **Dashboards** | Link to monitoring dashboard (or note it needs to be created) |
| **Runbook** | Link to on-call runbook |
| **Load testing** | Target load numbers and acceptance criteria |

---

## Red Flags

These thoughts mean STOP — address the underlying issue before continuing:

| Thought | What it actually means |
|---------|----------------------|
| "I'll figure out the details during implementation" | The design is incomplete. Work out the details now. |
| "This is too complex to diagram" | The architecture is too complex. Simplify before documenting. |
| "Everyone knows how this works" | Nobody will remember in 6 months. Write it down. |
| "We can handle that edge case later" | The edge case will become a production incident. Address it now or explicitly add it to Out-of-Scope with a tracking item. |
| "The requirements are obvious" | They are not. Different readers assume different requirements. Write them down. |
| "One option is clearly best — no need for alternatives" | Show your reasoning. Alternatives prove you explored the space and make your recommendation defensible. |
| "We don't need a rollback plan" | You will need a rollback plan. |

---

## Rationalization Table

| Excuse | Reality | Action |
|--------|---------|--------|
| "It's a small change" | Small changes to critical paths cause large outages | Write a lightweight LLD (2–3 pages) |
| "We're in a hurry" | Skipping design costs more time during implementation and debugging | Time-box the design to 2 hours |
| "The design is in my head" | Your head is not version-controlled, searchable, or reviewable | Write it down |
| "We discussed it in a meeting" | Meeting memory degrades within days. No artifact = no decision record | Capture the decision in a doc |
| "It's just a prototype" | Prototypes become production systems. Always. | Design for what it will become |

---

## Assembly Checklists

### HLD Checklist

- [ ] Problem statement is written from the user/business perspective with quantified impact
- [ ] Requirements have priorities (P0/P1/Stretch) and are testable
- [ ] In-scope and out-of-scope boundaries are explicit, with reasons for out-of-scope items
- [ ] Architecture section leads with a diagram; every component is described in text
- [ ] At least 2 alternatives considered, with a clear decision rationale
- [ ] Risks have likelihood, impact, and mitigations — not just a list of fears
- [ ] Security section addresses auth, encryption, and data classification
- [ ] Milestones have concrete deliverables, definitions of done, and dates
- [ ] Document passes the `writing:write-well` editing checklist (structure, clarity, conciseness)

### LLD Checklist (add to HLD checklist)

- [ ] API specs include request/response schemas, all error codes, and example payloads
- [ ] Data model shows schema and access patterns
- [ ] Sequence diagrams cover happy path and at least one error path
- [ ] Operational section covers deployment strategy, metrics, alerts, and rollback
- [ ] Migration strategy documented for any data model changes

---

## Weasel Words

The `writing:write-well` skill covers weasel word detection comprehensively — refer to its **Be Concrete and Specific** section. In design documents, the most damaging weasel words hide uncommitted requirements:

- "should" / "might" — is this required or optional?
- "fast" / "scalable" / "reliable" — what are the actual numbers?
- "significant" / "most" / "some" — what is the count or percentage?
- "as needed" / "appropriate" — decided by whom, when, using what criteria?

Replace every instance before sending for review.

---

## After Drafting

Once the draft is complete, run the `writing:write-well` editing checklist (three passes: structure, clarity, conciseness) before sending for review.

---

## Related Skills

- **`writing:write-well`** — Apply alongside this skill for sentence-level clarity, conciseness, active voice, and the full editing checklist. Every design doc should pass the `writing:write-well` three-pass review before sharing.
- **`communication:communicate-well`** — Use when distributing the finished doc: choosing the right channel, crafting the announcement message, and managing async review threads in Slack or tickets.
