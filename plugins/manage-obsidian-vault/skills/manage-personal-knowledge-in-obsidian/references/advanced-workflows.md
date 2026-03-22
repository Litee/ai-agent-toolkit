# Advanced Obsidian Workflows

Load this file when the user needs template-based note creation, bulk property updates, vault health analysis, property management, or task management.

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
