# Obsidian CLI Reference

Complete command reference for the Obsidian CLI (`obsidian`). Requires Obsidian 1.12+ with CLI enabled in Settings → General.

## General Syntax

```
obsidian [vault=<name>] <command> [parameters] [flags]
```

- **Parameters** take a value: `parameter=value` or `parameter="value with spaces"`
- **Flags** are boolean switches: include to enable (e.g., `open`, `overwrite`)
- **Vault targeting**: prefix any command with `vault=<name>` to target a specific vault
- **Multiline content**: use `\n` for newline, `\t` for tab
- **Copy output**: add `--copy` to any command to copy output to clipboard

---

## General Commands

### `help`
Show list of all available commands.

```bash
obsidian help
obsidian help create      # help for a specific command
```

### `version`
Show Obsidian version.

```bash
obsidian version
```

### `reload`
Reload the app window.

```bash
obsidian reload
```

### `restart`
Restart the app.

```bash
obsidian restart
```

---

## Files and Folders

### `create`
Create or overwrite a file.

```
name=<name>        # file name (without extension)
path=<path>        # exact path from vault root (e.g. folder/note.md)
content=<text>     # initial content
template=<name>    # template to use

overwrite          # overwrite if file exists
open               # open file after creating
newtab             # open in new tab
```

Examples:
```bash
obsidian create name="My Note"
obsidian create name="Recipe" content="# Recipe\n\nIngredients..."
obsidian create path="Projects/ProjectX/Overview.md" content="# Overview"
obsidian create name="Trip to Paris" template=Travel open
obsidian create name="Note" content="Hello world" overwrite
```

### `read`
Read file contents (default: active file).

```
file=<name>        # file name (wikilink-style resolution)
path=<path>        # exact path from vault root
```

Examples:
```bash
obsidian read
obsidian read file=Recipe
obsidian read path="Templates/Recipe.md"
obsidian read file=Recipe --copy
```

### `append`
Append content to a file (default: active file).

```
file=<name>        # file name
path=<path>        # file path
content=<text>     # (required) content to append

inline             # append without leading newline
```

Examples:
```bash
obsidian append file="My Note" content="New paragraph"
obsidian append content="- New bullet point" inline
```

### `prepend`
Prepend content after frontmatter (default: active file).

```
file=<name>        # file name
path=<path>        # file path
content=<text>     # (required) content to prepend

inline             # prepend without trailing newline
```

### `move`
Move or rename a file (default: active file). Automatically updates internal links if enabled in vault settings.

```
file=<name>        # file name
path=<path>        # file path
to=<path>          # (required) destination folder or full path
```

Examples:
```bash
obsidian move file="Old Note" to="Archive/"
obsidian move file="Draft" to="Projects/NewName.md"
```

### `rename`
Rename a file (default: active file). Preserves extension automatically. Automatically updates internal links.

```
file=<name>        # file name
path=<path>        # file path
name=<name>        # (required) new file name
```

Examples:
```bash
obsidian rename file="Draft" name="Final Version"
```

### `delete`
Delete a file (default: active file, moves to trash by default).

```
file=<name>        # file name
path=<path>        # file path

permanent          # skip trash, delete permanently
```

Examples:
```bash
obsidian delete file="Old Note"
obsidian delete file="Temp" permanent
```

### `open`
Open a file in Obsidian.

```
file=<name>        # file name
path=<path>        # file path

newtab             # open in new tab
```

### `file`
Show file info (default: active file). Returns path, name, extension, size, created, modified timestamps.

```
file=<name>        # file name
path=<path>        # file path
```

### `files`
List files in the vault.

```
folder=<path>      # filter by folder
ext=<extension>    # filter by extension (e.g. ext=md)

total              # return file count only
```

Examples:
```bash
obsidian files
obsidian files folder="Projects"
obsidian files ext=md total
```

### `folder`
Show folder info.

```
path=<path>              # (required) folder path
info=files|folders|size  # return specific info only
```

### `folders`
List folders in the vault.

```
folder=<path>      # filter by parent folder

total              # return folder count only
```

---

## Search

### `search`
Search vault for text. Returns matching file paths.

```
query=<text>       # (required) search query
path=<folder>      # limit search to folder
limit=<n>          # max files to return
format=text|json   # output format (default: text)

total              # return match count only
case               # case sensitive
```

Examples:
```bash
obsidian search query="machine learning"
obsidian search query="cache" path="Projects" limit=10
obsidian search query="TODO" --copy
obsidian search query="redis" format=json
```

### `search:context`
Search with matching line context. Returns grep-style `path:line: text` output.

```
query=<text>       # (required) search query
path=<folder>      # limit to folder
limit=<n>          # max files
format=text|json   # output format (default: text)

case               # case sensitive
```

Examples:
```bash
obsidian search:context query="important concept"
```

### `search:open`
Open search view in Obsidian.

```
query=<text>       # initial search query
```

---

## Tags

### `tags`
List tags in the vault. Use `active` or `file`/`path` to show tags for a specific file.

```
file=<name>        # show tags for file
path=<path>        # show tags for path
sort=count         # sort by count (default: sort by name)
format=json|tsv|csv  # output format (default: tsv)

total              # return tag count only
counts             # include tag counts
active             # show tags for active file
```

Examples:
```bash
obsidian tags
obsidian tags counts sort=count
obsidian tags file="My Note"
obsidian tags format=json
```

### `tag`
Get info about a specific tag.

```
name=<tag>         # (required) tag name (without #)

total              # return occurrence count only
verbose            # include file list and count per file
```

Examples:
```bash
obsidian tag name="programming/python"
obsidian tag name="project" verbose
obsidian tag name="status/draft" total
```

---

## Properties

### `properties`
List properties in the vault. Use `active` or `file`/`path` to show properties for a specific file.

```
file=<name>        # show properties for file
path=<path>        # show properties for path
name=<name>        # get specific property count
sort=count         # sort by count (default: name)
format=yaml|json|tsv  # output format (default: yaml)

total              # return property count only
counts             # include occurrence counts
active             # show properties for active file
```

Examples:
```bash
obsidian properties file="My Note"
obsidian properties counts sort=count
obsidian properties name=status
```

### `property:set`
Set a property on a file (default: active file).

```
name=<name>                                    # (required) property name
value=<value>                                  # (required) property value
type=text|list|number|checkbox|date|datetime   # property type
file=<name>                                    # file name
path=<path>                                    # file path
```

Examples:
```bash
obsidian property:set name="status" value="draft" type="text" file="My Note"
obsidian property:set name="tags" value="programming, python" type="list" file="My Note"
obsidian property:set name="priority" value="3" type="number" file="My Note"
obsidian property:set name="reviewed" value="true" type="checkbox" file="My Note"
obsidian property:set name="created" value="2024-03-01" type="date" file="My Note"
```

### `property:remove`
Remove a property from a file (default: active file).

```
name=<name>        # (required) property name
file=<name>        # file name
path=<path>        # file path
```

Examples:
```bash
obsidian property:remove name="obsolete" file="My Note"
```

### `property:read`
Read a property value from a file (default: active file).

```
name=<name>        # (required) property name
file=<name>        # file name
path=<path>        # file path
```

Examples:
```bash
obsidian property:read name="status" file="My Note"
```

### `aliases`
List aliases in the vault. Use `active` or `file`/`path` to show aliases for a specific file.

```
file=<name>        # file name
path=<path>        # file path

total              # return alias count only
verbose            # include file paths
active             # show aliases for active file
```

---

## Links and Graph

### `backlinks`
List backlinks to a file (default: active file).

```
file=<name>        # target file name
path=<path>        # target file path
format=json|tsv|csv  # output format (default: tsv)

counts             # include link counts
total              # return backlink count only
```

Examples:
```bash
obsidian backlinks file="Core Concept"
obsidian backlinks file="Core Concept" counts
obsidian backlinks file="Core Concept" total
```

### `links`
List outgoing links from a file (default: active file).

```
file=<name>        # file name
path=<path>        # file path

total              # return link count only
```

### `unresolved`
List unresolved (broken) links in vault.

```
total              # return unresolved link count only
counts             # include link counts per file
verbose            # include source files
format=json|tsv|csv  # output format (default: tsv)
```

Examples:
```bash
obsidian unresolved
obsidian unresolved verbose
```

### `orphans`
List files with no incoming links (nothing links to them).

```
total              # return orphan count only
```

Examples:
```bash
obsidian orphans
obsidian orphans total
```

### `deadends`
List files with no outgoing links (they link to nothing).

```
total              # return dead-end count only
```

Examples:
```bash
obsidian deadends
obsidian deadends total
```

---

## Tasks

### `tasks`
List tasks in the vault. Use `active` or `file`/`path` to show tasks for a specific file.

```
file=<name>        # filter by file name
path=<path>        # filter by file path
status="<char>"    # filter by status character

total              # return task count only
done               # show completed tasks only
todo               # show incomplete tasks only
verbose            # group by file with line numbers
format=json|tsv|csv  # output format (default: text)
active             # show tasks for active file
daily              # show tasks from daily note
```

Examples:
```bash
obsidian tasks
obsidian tasks todo
obsidian tasks done
obsidian tasks file=Recipe done
obsidian tasks daily
obsidian tasks daily total
obsidian tasks verbose
obsidian tasks 'status=?'
```

### `task`
Show or update a task.

```
ref=<path:line>    # task reference (path:line, e.g. "Recipe.md:8")
file=<name>        # file name
path=<path>        # file path
line=<n>           # line number
status="<char>"    # set status character

toggle             # toggle task status
daily              # target daily note
done               # mark as done [x]
todo               # mark as todo [ ]
```

Examples:
```bash
obsidian task file=Recipe line=8
obsidian task ref="Recipe.md:8"
obsidian task ref="Recipe.md:8" toggle
obsidian task daily line=3 toggle
obsidian task file=Recipe line=8 done
obsidian task file=Recipe line=8 todo
obsidian task file=Recipe line=8 status=-
```

---

## Daily Notes

### `daily`
Open daily note.

```
paneType=tab|split|window    # pane type to open in
```

### `daily:path`
Get daily note path. Returns expected path even if file hasn't been created yet.

### `daily:read`
Read daily note contents.

### `daily:append`
Append content to daily note.

```
content=<text>     # (required) content to append
paneType=tab|split|window    # pane type to open in

inline             # append without leading newline
open               # open file after adding
```

Examples:
```bash
obsidian daily:append content="- [ ] Review PR"
obsidian daily:append content="## Idea\n\nExplore connection between X and Y"
```

### `daily:prepend`
Prepend content to daily note.

```
content=<text>     # (required) content to prepend
paneType=tab|split|window    # pane type to open in

inline             # prepend without trailing newline
open               # open file after adding
```

---

## Templates

### `templates`
List templates.

```
total              # return template count only
```

### `template:read`
Read template content.

```
name=<template>    # (required) template name
title=<title>      # title for variable resolution

resolve            # resolve template variables ({{date}}, {{time}}, {{title}})
```

Examples:
```bash
obsidian templates
obsidian template:read name="Knowledge Card"
obsidian template:read name="Meeting Notes" resolve
```

### `template:insert`
Insert template into active file.

```
name=<template>    # (required) template name
```

Notes:
- `resolve` option processes `{{date}}`, `{{time}}`, `{{title}}` variables
- To create a file from a template, use `create path=<path> template=<name>`

---

## Bookmarks

### `bookmarks`
List bookmarks.

```
total              # return bookmark count only
verbose            # include bookmark types
format=json|tsv|csv  # output format (default: tsv)
```

### `bookmark`
Add a bookmark.

```
file=<path>        # file to bookmark
subpath=<subpath>  # subpath (heading or block) within file
folder=<path>      # folder to bookmark
search=<query>     # search query to bookmark
url=<url>          # URL to bookmark
title=<title>      # bookmark title
```

---

## Outline

### `outline`
Show headings for a file (default: active file).

```
file=<name>        # file name
path=<path>        # file path
format=tree|md|json  # output format (default: tree)

total              # return heading count only
```

Examples:
```bash
obsidian outline file="Long Document"
obsidian outline file="Long Document" format=json
```

---

## Vault

### `vault`
Show vault info.

```
info=name|path|files|folders|size  # return specific info only
```

Examples:
```bash
obsidian vault
obsidian vault info=path
```

### `vaults`
List known vaults.

```
total              # return vault count only
verbose            # include vault paths
```

### `vault:open`
Switch to a different vault (TUI only).

```
name=<name>        # (required) vault name
```

**Multi-vault targeting**: Prefix any command with `vault=<name>` to target a specific vault without switching:
```bash
obsidian vault=Notes daily
obsidian vault="My Vault" search query="test"
```

---

## File History

### `diff`
List or compare versions from local File recovery and Sync. Versions numbered newest to oldest.

```
file=<name>          # file name
path=<path>          # file path
from=<n>             # version number to diff from
to=<n>               # version number to diff to
filter=local|sync    # filter by version source
```

Examples:
```bash
obsidian diff
obsidian diff file=Recipe
obsidian diff file=Recipe from=1
obsidian diff file=Recipe from=2 to=1
obsidian diff filter=sync
```

### `history`
List versions from local File recovery only.

```
file=<name>        # file name
path=<path>        # file path
```

### `history:list`
List all files with local history.

### `history:read`
Read a local history version.

```
file=<name>        # file name
path=<path>        # file path
version=<n>        # version number (default: 1)
```

### `history:restore`
Restore a local history version.

```
file=<name>        # file name
path=<path>        # file path
version=<n>        # (required) version number
```

### `history:open`
Open file recovery panel.

```
file=<name>        # file name
path=<path>        # file path
```

---

## Sync

### `sync`
Pause or resume Obsidian Sync.

```
on                 # resume sync
off                # pause sync
```

### `sync:status`
Show sync status and usage.

### `sync:history`
List sync version history for a file (default: active file).

```
file=<name>        # file name
path=<path>        # file path

total              # return version count only
```

### `sync:read`
Read a sync version (default: active file).

```
file=<name>        # file name
path=<path>        # file path
version=<n>        # (required) version number
```

### `sync:restore`
Restore a sync version (default: active file).

```
file=<name>        # file name
path=<path>        # file path
version=<n>        # (required) version number
```

### `sync:open`
Open sync history panel (default: active file).

```
file=<name>        # file name
path=<path>        # file path
```

### `sync:deleted`
List deleted files in sync.

```
total              # return deleted file count only
```

---

## Publish

### `publish:site`
Show publish site info (slug, URL).

### `publish:list`
List published files.

```
total              # return published file count only
```

### `publish:status`
List publish changes.

```
total              # return change count only
new                # show new files only
changed            # show changed files only
deleted            # show deleted files only
```

### `publish:add`
Publish a file or all changed files (default: active file).

```
file=<name>        # file name
path=<path>        # file path

changed            # publish all changed files
```

### `publish:remove`
Unpublish a file (default: active file).

```
file=<name>        # file name
path=<path>        # file path
```

### `publish:open`
Open file on published site (default: active file).

```
file=<name>        # file name
path=<path>        # file path
```

---

## Plugins

### `plugins`
List installed plugins.

```
filter=core|community  # filter by plugin type

versions               # include version numbers
format=json|tsv|csv    # output format (default: tsv)
```

### `plugins:enabled`
List enabled plugins.

```
filter=core|community  # filter by plugin type

versions               # include version numbers
format=json|tsv|csv    # output format (default: tsv)
```

### `plugins:restrict`
Toggle or check restricted mode.

```
on                 # enable restricted mode
off                # disable restricted mode
```

### `plugin`
Get plugin info.

```
id=<plugin-id>     # (required) plugin ID
```

### `plugin:enable`
Enable a plugin.

```
id=<id>                # (required) plugin ID
filter=core|community  # plugin type
```

### `plugin:disable`
Disable a plugin.

```
id=<id>                # (required) plugin ID
filter=core|community  # plugin type
```

### `plugin:install`
Install a community plugin.

```
id=<id>            # (required) plugin ID

enable             # enable after install
```

### `plugin:uninstall`
Uninstall a community plugin.

```
id=<id>            # (required) plugin ID
```

### `plugin:reload`
Reload a plugin (for developers).

```
id=<id>            # (required) plugin ID
```

---

## Themes and Snippets

### `themes`
List installed themes.

```
versions           # include version numbers
```

### `theme`
Show active theme or get info.

```
name=<name>        # theme name for details
```

### `theme:set`
Set active theme.

```
name=<name>        # (required) theme name (empty string for default)
```

### `theme:install`
Install a community theme.

```
name=<name>        # (required) theme name

enable             # activate after install
```

### `theme:uninstall`
Uninstall a theme.

```
name=<name>        # (required) theme name
```

### `snippets`
List installed CSS snippets.

### `snippets:enabled`
List enabled CSS snippets.

### `snippet:enable`
Enable a CSS snippet.

```
name=<name>        # (required) snippet name
```

### `snippet:disable`
Disable a CSS snippet.

```
name=<name>        # (required) snippet name
```

---

## Workspace

### `workspace`
Show workspace tree.

```
ids                # include workspace item IDs
```

### `workspaces`
List saved workspaces.

```
total              # return workspace count only
```

### `workspace:save`
Save current layout as workspace.

```
name=<name>        # workspace name
```

### `workspace:load`
Load a saved workspace.

```
name=<name>        # (required) workspace name
```

### `workspace:delete`
Delete a saved workspace.

```
name=<name>        # (required) workspace name
```

### `tabs`
List open tabs.

```
ids                # include tab IDs
```

### `tab:open`
Open a new tab.

```
group=<id>         # tab group ID
file=<path>        # file to open
view=<type>        # view type to open
```

### `recents`
List recently opened files.

```
total              # return recent file count only
```

---

## Random Notes

### `random`
Open a random note.

```
folder=<path>      # limit to folder

newtab             # open in new tab
```

### `random:read`
Read a random note (includes path in output).

```
folder=<path>      # limit to folder
```

---

## Bases

Commands for Obsidian Bases.

### `bases`
List all `.base` files in the vault.

### `base:views`
List views in the current base file.

### `base:create`
Create a new item in a base. Defaults to active base view if no file specified.

```
file=<name>        # base file name
path=<path>        # base file path
view=<name>        # view name
name=<name>        # new file name
content=<text>     # initial content

open               # open file after creating
newtab             # open in new tab
```

### `base:query`
Query a base and return results.

```
file=<name>                    # base file name
path=<path>                    # base file path
view=<name>                    # view name to query
format=json|csv|tsv|md|paths   # output format (default: json)
```

---

## Command Palette

### `commands`
List available command IDs.

```
filter=<prefix>    # filter by ID prefix
```

### `command`
Execute an Obsidian command by ID.

```
id=<command-id>    # (required) command ID to execute
```

Examples:
```bash
obsidian commands
obsidian commands filter=templater
obsidian command id="templater-obsidian:insert-templater-file-template"
```

### `hotkeys`
List hotkeys for all commands.

```
total              # return hotkey count only
verbose            # show if hotkey is custom
format=json|tsv|csv  # output format (default: tsv)
```

### `hotkey`
Get hotkey for a command.

```
id=<command-id>    # (required) command ID

verbose            # show if custom or default
```

---

## Unique Notes

### `unique`
Create unique note (uses Unique note creator plugin).

```
name=<text>        # note name
content=<text>     # initial content
paneType=tab|split|window    # pane type to open in

open               # open file after creating
```

---

## Web Viewer

### `web`
Open URL in web viewer.

```
url=<url>          # (required) URL to open

newtab             # open in new tab
```

---

## Word Count

### `wordcount`
Count words and characters (default: active file).

```
file=<name>        # file name
path=<path>        # file path

words              # return word count only
characters         # return character count only
```

---

## Developer Commands

These commands assist with plugin and theme development. Also enable agentic coding tools to test and debug Obsidian.

### `devtools`
Toggle Electron developer tools.

### `eval`
Execute JavaScript and return result.

```
code=<javascript>  # (required) JavaScript code to execute
```

Examples:
```bash
obsidian eval code="app.vault.getFiles().length"
obsidian eval code="app.workspace.getActiveFile()?.path"
```

### `dev:debug`
Attach/detach Chrome DevTools Protocol debugger.

```
on                 # attach debugger
off                # detach debugger
```

### `dev:cdp`
Run a Chrome DevTools Protocol command.

```
method=<CDP.method>  # (required) CDP method to call
params=<json>        # method parameters as JSON
```

### `dev:errors`
Show captured JavaScript errors.

```
clear              # clear the error buffer
```

### `dev:screenshot`
Take a screenshot (returns base64 PNG).

```
path=<filename>    # output file path
```

### `dev:console`
Show captured console messages.

```
limit=<n>                        # max messages (default: 50)
level=log|warn|error|info|debug  # filter by log level

clear                            # clear the console buffer
```

### `dev:css`
Inspect CSS with source locations.

```
selector=<css>     # (required) CSS selector
prop=<name>        # filter by property name
```

### `dev:dom`
Query DOM elements.

```
selector=<css>     # (required) CSS selector
attr=<name>        # get attribute value
css=<prop>         # get CSS property value

total              # return element count only
text               # return text content
inner              # return innerHTML instead of outerHTML
all                # return all matches instead of first
```

### `dev:mobile`
Toggle mobile emulation.

```
on                 # enable mobile emulation
off                # disable mobile emulation
```

---

## TUI Keyboard Shortcuts

Available in interactive TUI mode (`obsidian` with no arguments):

| Action | Shortcut |
|--------|----------|
| Move cursor left | `←` / `Ctrl+B` |
| Move cursor right / accept suggestion | `→` / `Ctrl+F` |
| Jump to start of line | `Ctrl+A` |
| Jump to end of line | `Ctrl+E` |
| Move back one word | `Alt+B` |
| Move forward one word | `Alt+F` |
| Delete to start of line | `Ctrl+U` |
| Delete to end of line | `Ctrl+K` |
| Delete previous word | `Ctrl+W` / `Alt+Backspace` |
| Enter/accept suggestion | `Tab` |
| Exit suggestion mode | `Shift+Tab` |
| Previous history / navigate up | `↑` / `Ctrl+P` |
| Next history / navigate down | `↓` / `Ctrl+N` |
| Reverse history search | `Ctrl+R` |
| Execute command | `Enter` |
| Undo / clear input | `Escape` |
| Clear screen | `Ctrl+L` |
| Exit | `Ctrl+C` / `Ctrl+D` |
