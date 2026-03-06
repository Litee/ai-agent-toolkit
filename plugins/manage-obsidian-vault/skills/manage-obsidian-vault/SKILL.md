---
name: manage-obsidian-vault
description: Manage Obsidian vault notes via the Obsidian CLI. Use for creating notes, linking, tagging, searching, organizing, backlink analysis, properties/metadata, daily notes, templates, task management, and vault health analysis. Triggers on any request involving Obsidian, knowledge management, PKM, or vault operations.
---

# Manage Obsidian Vault

## Overview

This skill enables programmatic management of Obsidian vault notes using the Obsidian CLI. Notes are treated as atomic knowledge cards — discrete units of knowledge that link together to form a personal knowledge graph.

The Obsidian CLI (`obsidian`) connects to a running Obsidian instance over a local socket. It exposes every Obsidian capability — file operations, search, tagging, properties, backlinks, daily notes, templates, and more — as terminal commands suitable for scripting and automation.

For the complete command reference with all parameters and flags, read `references/cli-reference.md`.

## Prerequisites

Requires Obsidian desktop app 1.12+ (installer 1.12.4+) with CLI enabled in Obsidian Settings → General.

### Check CLI Installation

Before any vault operation, verify the CLI is available:

```bash
which obsidian
```

If not found, check Obsidian is installed and the CLI has been registered:
1. Open Obsidian → Settings → General
2. Enable **Command line interface**
3. Follow the prompt to register the CLI (adds to PATH)
4. **Restart the terminal** after registration

macOS PATH (added to `~/.zprofile`):
```bash
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
```

For other shells (bash, fish), add the path manually to `~/.bash_profile` or run `fish_add_path /Applications/Obsidian.app/Contents/MacOS`.

### Verify Connection

The Obsidian app must be running. Verify connectivity:

```bash
obsidian vault
```

If Obsidian is not running, launching the CLI will start it. Wait a few seconds, then retry.

### Requirements

- Obsidian desktop app version **1.12+** (requires installer 1.12.4+)
- CLI enabled in Obsidian Settings → General
- For multi-vault setups: identify the target vault name with `obsidian vaults`

---

## Quick Start

```bash
# Check vault info and connectivity
obsidian vault

# Create a new note
obsidian create name="My First Note" content="# My First Note\n\nHello world"

# Read a note
obsidian read file="My First Note"

# Search the vault
obsidian search query="machine learning"

# List all tags with counts
obsidian tags counts sort=count
```

---

## Best Practices for Knowledge Management

### Atomic Notes

Each note should capture **one concept or idea**. Atomic notes are:
- **Self-contained**: readable without requiring context from other notes
- **Titled descriptively**: the note name should be a complete thought (not "Meeting 2024-03-01" but "Q1 Planning decisions and rationale")
- **Concise**: if a note grows beyond 500 words, consider splitting into multiple linked notes

**Anti-patterns to avoid:**
- "Dump notes" that accumulate everything about a broad topic
- Date-based naming without content description (use daily notes for that)
- Notes that are just lists with no synthesis

### Linking Strategy

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

Run vault health checks periodically (see Workflow 7) to keep the knowledge graph connected.

### Tagging Conventions

Use **hierarchical tags** for classification: `#topic/subtopic` (e.g., `#programming/python`, `#status/draft`, `#type/concept`).

**Principles:**
- Tags classify what a note *is*; links express how notes *relate*
- Keep tag vocabulary controlled — audit with `obsidian tags counts sort=count`
- Common tag namespaces: `#type/` (concept, reference, project, person), `#status/` (draft, review, permanent), `#topic/` (subject area)
- Avoid excessive tags — 3-5 per note is usually sufficient

### Folder Organization

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

### Properties and Frontmatter

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

For content with wikilinks (`[[...]]`), use single quotes around the content argument to prevent shell interpretation:

```bash
obsidian create name="My Note" content='# Title\n\nSee [[Related Note]] for context.'
```

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

### Workflow 5: Creating Notes from Templates

To create consistently structured notes:

```bash
# List available templates
obsidian templates

# Preview a template with variable resolution
obsidian template:read name="Knowledge Card" resolve

# Create a note from a template
obsidian create name="New Concept" template="Knowledge Card"
obsidian create path="Projects/NewProject/Overview.md" template="Project Overview"
```

### Workflow 6: Bulk Property Updates

To update metadata across multiple notes:

```bash
# Promote all draft notes in a folder to review status
# (list files, then update each one)
obsidian files folder="Inbox" | while read -r filepath; do
  notename=$(basename "$filepath" .md)
  obsidian property:set name="status" value="review" type="text" file="$notename"
done

# Add a property to all notes tagged with a specific tag (use format=json for reliable parsing)
obsidian tag name="status/draft" format=json | jq -r '.[].path' | while read -r filepath; do
  notename=$(basename "$filepath" .md)
  obsidian property:set name="reviewed" value="false" type="checkbox" file="$notename"
done
```

Note: output format of `files` and `tag` commands affects parsing. Use `format=json` for more reliable programmatic processing:

```bash
obsidian files folder="Inbox" format=json
```

### Workflow 7: Vault Health Analysis

To audit the knowledge graph and find structural issues:

```bash
# Find orphaned notes (no incoming links — isolated knowledge)
obsidian orphans
obsidian orphans total

# Find dead-end notes (no outgoing links — stubs or incomplete)
obsidian deadends
obsidian deadends total

# Find broken links (references to non-existent notes)
obsidian unresolved
obsidian unresolved verbose

# Review tag distribution to spot unused or overly broad tags
obsidian tags counts sort=count

# Count files and folders
obsidian vault info=files
obsidian vault info=folders
```

Health check routine — run all at once:
```bash
echo "=== Orphans ===" && obsidian orphans total
echo "=== Dead Ends ===" && obsidian deadends total
echo "=== Unresolved Links ===" && obsidian unresolved total
echo "=== Top Tags ===" && obsidian tags counts sort=count | head -20
```

### Workflow 8: Working with Properties and Metadata

To manage frontmatter across notes:

```bash
# Read all properties on a note
obsidian properties file="My Note"

# Read a specific property value
obsidian property:read name="status" file="My Note"

# Set a property (creates or updates)
obsidian property:set name="status" value="permanent" type="text" file="My Note"
obsidian property:set name="priority" value="3" type="number" file="My Note"
obsidian property:set name="reviewed" value="true" type="checkbox" file="My Note"
obsidian property:set name="due" value="2024-03-15" type="date" file="My Note"

# Remove a property
obsidian property:remove name="obsolete-field" file="My Note"

# List all property names used across the vault (with counts)
obsidian properties counts sort=count
```

### Workflow 9: Task Management within Notes

To manage tasks embedded in notes:

```bash
# List all incomplete tasks in the vault
obsidian tasks todo

# List all completed tasks
obsidian tasks done

# List tasks in a specific file
obsidian tasks todo file="Project Plan"

# List tasks from today's daily note
obsidian tasks daily

# List tasks with file and line number
obsidian tasks verbose

# Toggle a specific task (by file + line number)
obsidian task file="Project Plan" line=8 toggle

# Mark a task done
obsidian task file="Project Plan" line=8 done

# Mark a task as todo
obsidian task file="Project Plan" line=8 todo

# Use task reference syntax
obsidian task ref="Projects/Plan.md:8" toggle
```

---

## Multi-Vault Operations

To target a specific vault without switching to it, prefix any command with `vault=<name>`:

```bash
# List all known vaults
obsidian vaults

# Target a specific vault by name
obsidian vault=Work search query="quarterly review"
obsidian vault="Personal Notes" daily:append content="- [ ] New task"
obsidian vault=Archive files total
```

The `vault=<name>` prefix must appear **before** the command and any other parameters.

---

## Shell Escaping Notes

**Content with wikilinks**: Use single quotes to prevent shell interpretation of `[[` and `]]`:
```bash
obsidian create name="Note" content='See [[Related Note]] for details.'
```

**Content with double quotes**: Escape inner quotes or use single quotes:
```bash
obsidian append file="Note" content='He said "hello world" to the terminal.'
```

**Multiline content**: Use `\n` for newlines, `\t` for tabs:
```bash
obsidian create name="Note" content="# Title\n\nFirst paragraph.\n\nSecond paragraph."
```

**Special shell characters** (`$`, `!`, backticks) in content: Use single quotes:
```bash
obsidian create name="Note" content='Cost: $100. Running `echo hello`.'
```

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|---------|
| `obsidian: command not found` | CLI not on PATH | Check `~/.zprofile`, restart terminal, or re-register CLI in Obsidian settings |
| `Failed to connect` | Obsidian not running | Launch Obsidian app, wait a few seconds, retry |
| `File not found` | Wrong file name or path | Use `obsidian files` to list files; try `path=` instead of `file=` for exact paths |
| `Vault not found` | Wrong vault name | Use `obsidian vaults` to list vault names |
| `Template not found` | Wrong template name | Use `obsidian templates` to list available templates |
| `File already exists` | Attempting to create existing file | Add `overwrite` flag or choose a different name |

---

## When to Use This Skill

**Use when:**
- Creating, reading, updating, or deleting notes in Obsidian
- Searching for information across the vault
- Organizing notes (moving, renaming, tagging)
- Analyzing vault structure (backlinks, orphans, dead-ends, unresolved links)
- Managing note properties and frontmatter
- Working with daily notes for capture and review
- Creating notes from templates
- Managing tasks within notes
- Running vault health audits
- Bulk operations on multiple notes

**Do NOT use when:**
- Obsidian app is not running and cannot be started (use standard file system tools on `.md` files as a fallback — but internal links won't update)
- User wants to interact with the Obsidian GUI directly — use `obsidian open file=<name>` to hand off to the app
- Community plugin functionality not exposed via CLI is needed — use `obsidian command id=<plugin-command>` to invoke plugin commands, or instruct the user to interact with the GUI

---

## CLI Reference

For the complete command reference with all commands, parameters, flags, and examples, read `references/cli-reference.md`.

Available command categories:
- **Files and Folders**: `create`, `read`, `append`, `prepend`, `move`, `rename`, `delete`, `open`, `file`, `files`, `folders`
- **Search**: `search`, `search:context`, `search:open`
- **Tags**: `tags`, `tag`
- **Properties**: `properties`, `property:set`, `property:remove`, `property:read`, `aliases`
- **Links/Graph**: `backlinks`, `links`, `unresolved`, `orphans`, `deadends`
- **Tasks**: `tasks`, `task`
- **Daily Notes**: `daily`, `daily:path`, `daily:read`, `daily:append`, `daily:prepend`
- **Templates**: `templates`, `template:read`, `template:insert`
- **Bookmarks**: `bookmarks`, `bookmark`
- **Outline**: `outline`
- **Vault**: `vault`, `vaults`, `vault:open`
- **File History**: `diff`, `history`, `history:list`, `history:read`, `history:restore`
- **Sync**: `sync`, `sync:status`, `sync:history`, `sync:read`, `sync:restore`, `sync:deleted`
- **Publish**: `publish:site`, `publish:list`, `publish:status`, `publish:add`, `publish:remove`
- **Plugins**: `plugins`, `plugin`, `plugin:enable`, `plugin:disable`, `plugin:install`, `plugin:reload`
- **Themes**: `themes`, `theme`, `theme:set`, `theme:install`, `snippets`
- **Workspace**: `workspace`, `workspaces`, `tabs`, `recents`
- **Developer**: `devtools`, `eval`, `dev:debug`, `dev:screenshot`, `dev:console`, `dev:errors`
- **Other**: `random`, `unique`, `web`, `wordcount`, `bases`, `commands`, `command`
