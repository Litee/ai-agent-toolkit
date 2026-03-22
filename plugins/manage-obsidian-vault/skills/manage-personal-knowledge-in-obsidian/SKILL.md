---
name: manage-personal-knowledge-in-obsidian
description: Manage personal knowledge in Obsidian using atomic notes, linking strategies, tagging conventions, and structured workflows. Use for knowledge management, note organization, vault health analysis, and building a personal knowledge graph. Triggers on requests involving PKM, Zettelkasten, knowledge management, note-taking methodology, or managing an Obsidian vault as a knowledge base.
---

# Personal Knowledge Management in Obsidian

This skill provides opinionated guidance for building and maintaining a personal knowledge base in Obsidian. It assumes the `use-obsidian-cli` skill for CLI operations and `use-obsidian-markdown` for note content syntax.

For advanced workflows (templates, bulk property updates, vault health analysis, task management), read `references/advanced-workflows.md`.

---

## Core Philosophy: Atomic Notes

Each note should capture **one concept or idea**. Atomic notes are:
- **Self-contained**: readable without requiring context from other notes
- **Titled descriptively**: the note name should be a complete thought (not "Meeting 2024-03-01" but "Q1 Planning decisions and rationale")
- **Concise**: if a note grows beyond 500 words, consider splitting into multiple linked notes

**Anti-patterns to avoid:**
- "Dump notes" that accumulate everything about a broad topic
- Date-based naming without content description (use daily notes for that)
- Notes that are just lists with no synthesis

---

## Linking Strategy

Links between notes are the core value of Obsidian. Use `[[wikilinks]]` liberally in note content.

**When to link:**
- Reference any concept that has its own note
- Link supporting evidence to claim notes
- Link examples to principle notes

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

Run vault health checks periodically (see Workflow 7 in `references/advanced-workflows.md`) to keep the knowledge graph connected.

---

## Tagging Conventions

Use **hierarchical tags** for classification: `#topic/subtopic` (e.g., `#programming/python`, `#status/draft`, `#type/concept`).

**Principles:**
- Tags classify what a note *is*; links express how notes *relate*
- Keep tag vocabulary controlled — audit with `obsidian tags counts sort=count`
- Common tag namespaces: `#type/` (concept, reference, project, person), `#status/` (draft, review, permanent), `#topic/` (subject area)
- Avoid excessive tags — 3-5 per note is usually sufficient

---

## Folder Organization

Use folders for **broad categories**, not fine-grained topics. Topics are expressed through tags and links.

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
```

For shell escaping rules when content contains wikilinks or special characters, see the `use-obsidian-cli` skill.

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

### Workflows 5–9: Templates, Bulk Updates, Health Analysis, Properties, Tasks

For these advanced workflows, load `references/advanced-workflows.md`. Quick reference:

```bash
obsidian templates                              # list templates
obsidian tasks todo                             # list incomplete tasks
obsidian orphans total                          # count isolated notes
obsidian unresolved total                       # count broken links
obsidian properties counts sort=count          # all property names with counts
```
