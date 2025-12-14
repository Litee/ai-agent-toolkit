# ai-agent-toolkit

A repository with prompts, skills, and configuration tools for AI agents.

## Available Skills

### [manage-anki-flashcards](skills/manage-anki-flashcards/)

Comprehensive integration with Anki flashcard software through the AnkiConnect API. Create flashcards, manage decks, search notes/cards, sync collections, control review sessions, and automate Anki workflows.

**Use this skill to:**
- Create flashcards from learning materials and documentation
- Bulk import cards from data sources (CSVs, APIs, databases)
- Search and analyze your card collection
- Manage deck organization and tags
- Automate review workflows and syncing operations

**Quick start:**
```bash
# Check connection to AnkiConnect
python3 skills/manage-anki-flashcards/scripts/anki_connect.py deck-names

# Create a simple flashcard
python3 skills/manage-anki-flashcards/scripts/anki_connect.py add-note \
    --deck "Default" \
    --model "Basic" \
    --fields '{"Front":"What is Python?","Back":"A programming language"}' \
    --tags "python,programming"
```

**Prerequisites:** Anki must be running with AnkiConnect plugin installed (add-on code: 2055492159)

See the [skill documentation](skills/manage-anki-flashcards/SKILL.md) for detailed usage instructions, best practices for creating effective flashcards, and complete API reference.

---

### [register-safe-terminal-commands](skills/register-safe-terminal-commands/)

Manages safe terminal commands for Claude Code—bash commands that can be executed automatically without requiring user approval. Includes 289 pre-configured safe commands for AWS CLI, Git, Docker, and common development tools.

**Use this skill to:**
- Register safe terminal commands in Claude Code settings
- Sync commands from the reference file to `~/.claude/settings.json`
- Add new safe commands to the pre-approved list

**Quick start:**
```bash
python skills/register-safe-terminal-commands/scripts/sync_safe_commands.py
```

See the [skill documentation](skills/register-safe-terminal-commands/SKILL.md) for detailed usage instructions.
