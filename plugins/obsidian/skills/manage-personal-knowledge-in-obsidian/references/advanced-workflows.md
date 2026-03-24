# Advanced Obsidian Workflows

Load this file when the user needs template-based note creation, bulk property updates, vault health analysis, property management, task management, or vault gardening.

## Workflow 5: Creating Notes from Templates

```bash
# List available templates
obsidian templates

# Preview a template with variable resolution
obsidian template:read name="Knowledge Card" resolve

# Create a note from a template
obsidian create name="New Concept" template="Knowledge Card"
obsidian create path="Projects/NewProject/Overview.md" template="Project Overview"
```

## Workflow 6: Bulk Property Updates

```bash
# Promote all draft notes in a folder to review status
# Use format=json for reliable programmatic parsing
obsidian files folder="Inbox" format=json | jq -r '.[].path' | while read -r filepath; do
  notename=$(basename "$filepath" .md)
  obsidian property:set name="status" value="review" type="text" file="$notename"
done

# Add a property to all notes with a specific tag
obsidian tag name="status/draft" format=json | jq -r '.[].path' | while read -r filepath; do
  notename=$(basename "$filepath" .md)
  obsidian property:set name="reviewed" value="false" type="checkbox" file="$notename"
done
```

Note: Use `format=json` for reliable programmatic processing. The default text output format may change across CLI versions.

## Workflow 7: Vault Health Analysis

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

## Workflow 8: Working with Properties and Metadata

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

## Workflow 9: Task Management within Notes

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

# Use task reference syntax
obsidian task ref="Projects/Plan.md:8" toggle
```

## Workflow 10: Vault Gardening Session

Run periodically (weekly recommended) to maintain vault health and keep knowledge connected. Think of it as pruning a garden: remove dead growth, connect isolated nodes, and promote mature ideas.

### Step 1: Health Snapshot

```bash
echo "=== Orphans ===" && obsidian orphans total
echo "=== Dead Ends ===" && obsidian deadends total
echo "=== Unresolved Links ===" && obsidian unresolved total
echo "=== Top Tags ===" && obsidian tags counts sort=count | head -20
echo "=== Total Notes ===" && obsidian vault info=files
```

### Step 2: Process Inbox

Review notes in the Inbox/ folder (or however unsorted captures are stored). For each note, decide:
- **Promote**: move to the permanent notes folder, add proper links and properties
- **Archive**: move to Archive/ if no longer relevant
- **Delete**: discard if it was a fleeting thought that no longer applies

```bash
# List all notes in Inbox
obsidian files folder="Inbox"

# Promote a note
obsidian move file="Capture from Monday" to="Notes/"
obsidian property:set name="status" value="permanent" type="text" file="Capture from Monday"

# Archive a note
obsidian move file="Old Idea" to="Archive/"
```

### Step 3: Connect Orphaned Notes

Find notes nothing links to and integrate them into the knowledge graph:

```bash
obsidian orphans
```

For each orphan:
- Add contextual wikilinks in existing related notes that should reference it
- Add a Related Topics section to the orphan itself
- If the orphan genuinely stands alone (e.g., a reference), leave it intentionally

### Step 4: Review Draft Notes

Find notes that have been sitting in draft status and decide their fate:

```bash
# Find all notes tagged with draft status
obsidian tag name="status/draft" verbose
```

For each: promote to `permanent`, continue refining, or archive if stale.

### Step 5: Tag Audit

Spot tag sprawl and inconsistencies:

```bash
obsidian tags counts sort=count
```

- Tags used **fewer than 2 times**: candidates for removal or merge into an existing tag
- Tags used **more than 50 times**: candidates for splitting into sub-tags (e.g., `#topic/programming` → `#topic/programming/python`)
- **Synonym pairs**: look for tags like `#coding` and `#programming` that mean the same thing
- **Orphan tags**: tags that appear in the tag list but were removed from notes

Bulk-update a tag across the vault via property set on all matching notes:
```bash
# Find notes with an old tag and update them
obsidian tag name="coding" format=json | jq -r '.[].path' | while read -r filepath; do
  notename=$(basename "$filepath" .md)
  obsidian property:set name="tags" value="programming" type="list" file="$notename"
done
```

### Step 6: Random Note Review (Optional)

Read a random note to resurface forgotten knowledge and check if it needs updating:

```bash
obsidian random:read
```

If the note is outdated, refine it. If it connects to something you're currently working on, add links.
