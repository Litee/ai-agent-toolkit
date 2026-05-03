---
name: use-obsidian-cli
description: Use when creating, reading, updating, or searching notes in an Obsidian vault via the CLI; managing tags, properties, links, tasks, daily notes, templates, bookmarks, or plugins. Triggers on any request to perform operations on an Obsidian vault via the command line.
---

# Obsidian CLI

The `obsidian` CLI connects to a running Obsidian instance over a local socket. It exposes every Obsidian capability as terminal commands suitable for scripting and automation.

For the complete command reference with all parameters and flags, read `${SKILL_DIR}/references/cli-reference.md`.

## Prerequisites

Requires Obsidian desktop app 1.12+ (installer 1.12.4+) with CLI enabled in Obsidian Settings → General.

### Check CLI Installation

Before any vault operation, verify the CLI is available:

```bash
which obsidian
```

If not found:
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

## Multi-Vault Operations

To target a specific vault without switching to it, prefix any command with `vault=<name>`:

```bash
# List all known vaults
obsidian vaults

# Target a specific vault by name
obsidian vault=Work search query="quarterly review"
obsidian vault="Personal Notes" daily:append content="- [ ] New task"
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

For the complete command reference with all commands, parameters, flags, and examples, read `${SKILL_DIR}/references/cli-reference.md`.

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
