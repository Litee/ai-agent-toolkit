---
name: manage-personal-knowledge-in-obsidian
description: Use when building, maintaining, or analyzing a personal-knowledge-management vault in Obsidian. Triggers on requests involving PKM, Zettelkasten, knowledge management, atomic notes, note organization, vault health analysis, or building a personal knowledge graph.
---

# Personal Knowledge Management in Obsidian

This skill provides opinionated guidance for building and maintaining a personal knowledge base in Obsidian. It assumes the `obsidian:use-obsidian-cli` skill for CLI operations and `obsidian:use-obsidian-markdown` for note content syntax.

Obsidian stores everything as plain Markdown files — notes outlive any app. Favor simplicity and portability over plugin-dependent workflows.

For advanced workflows (templates, bulk property updates, vault health analysis, task management, vault gardening), read `${SKILL_DIR}/references/advanced-workflows.md`.

---

## Core Philosophy: Atomic Notes

Each note should capture **one concept or idea**. Atomic notes are:
- **Self-contained**: readable without requiring context from other notes
- **Titled descriptively**: the note name should be a complete thought (not "Meeting 2024-03-01" but "Q1 Planning decisions and rationale")
- **Concise**: length follows from atomicity, not a word count target — a simple concept may be 2 sentences; a nuanced argument may be 5 paragraphs

**Anti-patterns to avoid:**
- "Dump notes" that accumulate everything about a broad topic
- Date-based naming without content description (use daily notes for that)
- Notes that are just lists with no synthesis
- Notes that copy-paste source text without your own synthesis (quotes belong in reference/literature notes, not permanent knowledge cards)

---

## Card Structure

A well-formed knowledge card follows this anatomy:

1. **Opening definition** (1-2 sentences of prose before any `##` header): state the concept directly in your own words. This should be self-contained — readable without clicking any links.

2. **Body**: use `##` for major sections. Use **bold text** for lightweight sub-groupings within a section; reserve `###` for sub-sections substantial enough to warrant their own anchor.

3. **Related Topics** (at the end): each entry is a wikilink followed by ` - ` and a one-sentence explanation of the relationship.

**Example card:**

```markdown
Consistent hashing distributes keys across a virtual ring of nodes, minimizing key reassignment when the cluster size changes.

## How It Works
- Each node occupies one or more positions on a hash ring
- A key hashes to a position and is assigned to the next clockwise node
- **Virtual nodes:** each physical node maps to multiple ring positions for more even load distribution

## Trade-offs
- Outperforms modular hashing for dynamic clusters (fewer keys migrate on node changes)
- Without virtual nodes, load distribution can still be uneven

## Related Topics
- [[Hash Functions]] - Consistent hashing depends on uniform hash distribution across the ring
- [[Distributed Caching]] - Primary use case; consistent hashing enables cache cluster scaling without full resharding
- [[CAP Theorem]] - Informs the availability vs consistency choices in ring-based designs
```

**Formatting rules:**
- Distill insights into your own voice — no standalone source attributions ("Author X says..." or "According to Book Y...")
- No empty lines between bullet points to limit vertical size
- Default to minimalistic cards; expand only when the idea genuinely requires it
- Use Title Case for note names in wikilinks: `[[Binary-to-Text Encoding]]`
- Use pipe syntax when display text differs from the canonical name: `[[Consistent Hashing|consistent hashing]]`

> **Comparison notes follow different rules.** See [## Comparison Notes](#comparison-notes) below — they prohibit opening definitions and Related Topics sections.

---

## Comparison Notes

Comparison notes have their own conventions. Apply these **instead of** the standard card rules where they conflict.

### Naming conventions

- `X vs Y` — use when the pairing is idiomatic or widely recognised (e.g. *Correlation vs Causation*, *Compute Bound vs Memory Bound*)
- `Comparison of X and Y` / `Comparison of X, Y, and Z` — use for multi-subject comparisons or when the subjects don't form a well-known paired concept

Add an `aliases` frontmatter entry for the alternative form when it is commonly used (e.g. a `Comparison of X and Y` note may alias `X vs Y`).

### Structure options (all valid — choose by complexity)

1. **Bullet list with bold subject labels** — flat list of dimension bullets, each prefixed `**Subject:**`. Best for compact comparisons with few dimensions.

2. **`###` dimension sections, each containing bold-labeled subject bullets** — repeated `**Subject:**` entries under each `###` heading. Best for 5–10 dimension comparisons.

3. **Markdown table** — one row per subject, one column per dimension. Best when there are many subjects or when the comparison is at-a-glance. Richer notes may combine a summary table with prose `###` sections.

### Required opening line

Unlike standard knowledge cards, comparison notes must **not** open with a definition of either concept. Instead, write a single framing sentence that names the subjects and states the key tension or purpose:

> *"A side-by-side comparison of Apache Arrow and Apache Parquet — two columnar formats designed for different purposes."*

This orients the reader without defining either concept.

### Prohibited elements

- **No opening definition** (the 1–2 sentence prose opener before a `##` header that standard cards require). Comparison notes use a framing sentence instead — see above.
- **No Related Topics section** — no exceptions. Comparison notes are primarily designed to be embedded into parent notes as collapsed callouts (default pattern):
  ```markdown
  > [!info]- Comparison
  > ![[Comparison of X and Y]]
  ```
  A Related Topics section creates visual noise inside the callout. Use inline wikilinks within comparison bullets instead.

### Optional elements

- **`### When to Choose`** (or similar) at the end of richer comparisons (3+ subjects) — practical guidance on which subject is appropriate in which scenario.
- **`### External Resources`** — include when genuinely useful; omit otherwise. Standard card rules apply here.

---

## Linking Strategy

Links between notes are the core value of Obsidian. Two complementary types:

**Contextual links** (inline in prose): the strongest form — surrounding text explains *why* the connection exists:
> "This builds on [[First Principles Thinking]] by applying decomposition at the system boundary."

**Related Topics** (at card bottom): for conceptually adjacent notes that don't fit naturally in prose. Always annotate each link — a bare link list offers no more value than a search result.

**Virtual links**: link freely to notes that don't exist yet. Unresolved links appear in Obsidian's graph view and signal future cards to create. It is normal to have some unresolved links. Guidance for choosing virtual links:
- **Wikipedia test**: anything that could plausibly be its own Wikipedia article is a good virtual-link candidate. Concrete concepts, named techniques, technologies, people, and places qualify; generic adjectives and one-off phrases do not.
- **Link first mention only**: link the first occurrence of a notion within each top-level (`##`) section. Second and later mentions in the same section stay unlinked to avoid visual noise.
- **Related Topics complement, not replace**: a Related Topics entry never substitutes for an inline link. If a notion is meaningfully discussed in the main content, link it there too — Related Topics is for adjacent notes that didn't earn an inline mention.
- **Avoid acronyms as link names**: don't make the canonical link an acronym unless it is universally well known (e.g. `USA`, `HTTP`). Prefer the spelled-out name: `[[Cache Invalidation]]`, not `[[CI]]`.
- **Abbreviations are fine once expanded**: it is acceptable to use an abbreviation in a link if the full name is rendered at least once in the document, e.g. introduce `[[Test-Driven Development]] (TDD)` once, then `[[Test-Driven Development|TDD]]` afterwards.

**Quality over quantity**: before creating a link, ask "would this note be useful in the target's backlink panel?" If a term appears in hundreds of notes, linking it everywhere adds noise, not signal. Don't link generic terms that lack their own meaningful note.

**Linking in both directions:** when you add a new card to the vault, the outgoing links you write in it are only half the job. Existing neighboring notes do not automatically gain a link to the new card. After creating or substantially modifying a card, identify 2-5 existing notes that are conceptually close and update each to include a link back to the new card (inline or in Related Topics). This bidirectional linking is what weaves a new card into the existing graph rather than leaving it as an isolated leaf.

**Wikilink naming conventions:**
- Use Title Case canonical names: `[[Binary-to-Text Encoding]]`
- Use pipe syntax for display text: `[[Consistent Hashing|consistent hashing]]` — especially mid-sentence where Title Case is jarring; at sentence start or for proper nouns, the bare wikilink is fine
- Cap Related Topics links at ~5-7 entries; if more are needed, the cluster may warrant a dedicated index note

**Maintaining graph health:**
```bash
# Find isolated notes — nothing links to them
obsidian orphans

# Find notes that reference nothing — potential stubs
obsidian deadends

# Find broken links — references to notes that don't exist yet
obsidian unresolved

# Explore what links to a given note
obsidian backlinks file="Core Concept" counts
```

Run vault health checks periodically (see Workflow 7 and 10 in `${SKILL_DIR}/references/advanced-workflows.md`) to keep the knowledge graph connected.

---

## Tagging Conventions

Use **hierarchical tags** for classification: `#topic/subtopic` (e.g., `#programming/python`, `#status/draft`, `#type/concept`).

**Principles:**
- Tags classify what a note *is*; links express how notes *relate*
- Keep tag vocabulary controlled — audit with `obsidian tags counts sort=count`
- Only add tags you will actually filter or query on — avoid completionist tagging
- Avoid excessive tags — 3-5 per note is usually sufficient

**Recommended tag namespaces:**
- `#type/` — concept, reference, project, person, decision, question
- `#status/` — draft, review, permanent
- `#topic/` — subject area (max 2 levels: `#topic/programming/python`)
- `#source/` — book, article, video, podcast, conversation

---

## Folder Organization

Use folders for **broad categories**, not fine-grained topics. Topics are expressed through tags and links. Keep folder hierarchies **shallow** — max 2 levels deep. Beyond that, use tags.

Common vault structures:
- **PARA**: Projects/, Areas/, Resources/, Archive/
- **Simple**: Inbox/, Notes/, Archive/
- **Mixed**: Inbox/ (unsorted), Projects/ (active work), Permanent/ (settled knowledge)

When moving notes, always use `obsidian move` — it automatically updates all internal wikilinks:
```bash
obsidian move file="Old Note" to="Archive/"
```

Never rename vault files outside of Obsidian — wikilinks won't update.

---

## Properties and Frontmatter

Use YAML frontmatter properties for structured metadata. Consistent schemas enable vault-wide queries.

**Recommended properties for knowledge cards:**

| Property | Type | Values | Purpose |
|----------|------|---------|---------|
| `type` | text | concept, reference, project, person | Note classification |
| `status` | text | draft, review, permanent | Maturity level |
| `source` | text | URL or "Book Title by Author" | Provenance |
| `created` | date | YYYY-MM-DD | Creation date |
| `tags` | list | tag names (without #) | Searchable tags |

Set properties:
```bash
obsidian property:set name="status" value="draft" type="text" file="My Note"
obsidian property:set name="type" value="concept" type="text" file="My Note"
```

---

## Common Workflows

### Workflow 1: Creating a Knowledge Card

To capture a new concept as a permanent note:

```bash
# 1. Create the note with content
obsidian create name="Redis Cache Invalidation Strategies" content="# Redis Cache Invalidation Strategies\n\nKey approaches for managing stale data in Redis...\n\n## Strategies\n\n- TTL-based expiration\n- Event-driven invalidation\n- Cache-aside pattern\n\nSee also: [[Cache Patterns]] [[Redis Configuration]]"

# 2. Set metadata properties
obsidian property:set name="type" value="concept" type="text" file="Redis Cache Invalidation Strategies"
obsidian property:set name="status" value="draft" type="text" file="Redis Cache Invalidation Strategies"
obsidian property:set name="source" value="https://redis.io/docs/manual/eviction" type="text" file="Redis Cache Invalidation Strategies"

# 3. Verify the note was created correctly
obsidian read file="Redis Cache Invalidation Strategies"

# 4. Check what already links to related concepts
obsidian backlinks file="Cache Patterns"

# 5. Update backward links — find existing notes that should link back to this new card
obsidian search query="Redis cache invalidation"
obsidian search query="cache eviction"
# For each related note found, open it and add a contextual wikilink or Related Topics entry
# pointing to "Redis Cache Invalidation Strategies" where the connection is meaningful
obsidian read file="Cache Patterns"
# Then update Cache Patterns to add: [[Redis Cache Invalidation Strategies]] - specific strategies for Redis
```

> **Backward-linking is not optional.** A new note that nothing links to is invisible in the graph. After creating a card, always search for 2-5 existing notes that cover related concepts and add a contextual wikilink or Related Topics entry in each of those notes pointing back to the new card. Only add links where the connection is genuinely useful to a reader of the *existing* note — do not mass-link.

For shell escaping rules when content contains wikilinks or special characters, see the `obsidian:use-obsidian-cli` skill.

### Workflow 2: Capturing Quick Ideas via Daily Notes

To capture thoughts throughout the day without breaking flow:

```bash
# Append a task
obsidian daily:append content="- [ ] Follow up on Redis caching approach"

# Append a quick idea
obsidian daily:append content="\n## Idea\n\nExplore connection between cache invalidation and event sourcing"

# Prepend an urgent item
obsidian daily:prepend content="## URGENT\n\nReview production incident report\n\n"

# Read the daily note to review
obsidian daily:read
```

At end of day, promote valuable ideas to permanent notes using Workflow 1.

### Workflow 3: Searching and Discovering Notes

To find information across the vault:

```bash
# Full-text search returning file paths
obsidian search query="cache invalidation"
obsidian search query="cache invalidation" path="Notes" limit=10

# Search with surrounding context (grep-style output)
obsidian search:context query="TTL expiration"

# Discover notes by tag
obsidian tag name="programming/databases" verbose

# Find all notes that link to a concept
obsidian backlinks file="Redis Cache Invalidation Strategies" counts

# Find all notes a given note links to
obsidian links file="Redis Cache Invalidation Strategies"

# Copy search results to clipboard
obsidian search query="TODO" --copy
```

### Workflow 4: Organizing and Refactoring the Vault

To move notes and clean up structure:

```bash
# Move a note to a different folder (updates all links automatically)
obsidian move file="Misplaced Note" to="Notes/Technology/"

# Rename a note (preserves extension, updates links)
obsidian rename file="Old Name" name="Better Descriptive Name"

# Move multiple notes to archive using shell loop
for note in "Old Note 1" "Old Note 2" "Old Note 3"; do
  obsidian move file="$note" to="Archive/"
done
```

### Workflows 5–10: Templates, Bulk Updates, Health Analysis, Properties, Tasks, Gardening

For these advanced workflows, load `${SKILL_DIR}/references/advanced-workflows.md`. Quick reference:

```bash
obsidian templates                              # list templates
obsidian tasks todo                             # list incomplete tasks
obsidian orphans total                          # count isolated notes
obsidian unresolved total                       # count broken links
obsidian properties counts sort=count          # all property names with counts
```

---

## AI-Assisted PKM Workflows

When managing the vault as an AI agent, use these patterns:

**Link suggestion (bidirectional)**: after creating a note, search for related notes and:
1. Add outgoing links from the new note to those related notes (inline or Related Topics).
2. Update existing related notes to add a link *back* to the new note where the connection adds value to a reader of that note.

Both directions matter — a note no existing note links to is invisible in graph view and backlink panels.
```bash
# Search for notes related to a new concept
obsidian search query="cache invalidation"
obsidian search query="distributed systems"
```

**Summary extraction**: distill daily note content into standalone knowledge cards. Read the daily note, identify distinct concepts, create a card per concept using Workflow 1.

**Vault analysis**: periodically surface problems for the user to address:
```bash
obsidian orphans total        # isolated notes needing links
obsidian deadends total       # stub notes needing outgoing links
obsidian unresolved total     # broken links needing resolution
obsidian tags counts sort=count  # tag sprawl / inconsistencies
```

**Gap analysis**: after creating a note, check which linked notes don't exist yet and flag them as candidates for future cards:
```bash
obsidian unresolved verbose   # shows which notes have broken outgoing links
```

For a complete periodic gardening workflow, see Workflow 10 in `${SKILL_DIR}/references/advanced-workflows.md`.

---

## When the CLI Fails

> **The `obsidian` CLI acts on the app's active vault, not your shell's working directory.** A git worktree or checkout of a vault is *not* automatically targeted — edits land in the active vault and worktree files stay invisible to the CLI. Open the intended vault as the active vault first.

See `${SKILL_DIR}/references/troubleshooting.md` for the fallback and escalation rules specific to PKM workflows (when to fall back to `rg`/`find`, when writes are forbidden, how to resume mid-workflow). The lower-level CLI error matrix lives in `obsidian:use-obsidian-cli` → `references/troubleshooting.md`.
