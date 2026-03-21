---
name: manage-anki-flashcards
description: Manage Anki flashcards through the AnkiConnect API. Use for creating flashcards, managing decks, searching notes/cards, syncing collections, controlling review sessions, or any Anki automation tasks.
---

# Manage Anki

## Overview

This skill provides comprehensive integration with Anki flashcard software through the AnkiConnect plugin API. Use this skill to programmatically create flashcards, manage decks and tags, search cards, control review sessions, and automate Anki workflows.

## Prerequisites

Before using this skill, ensure:

1. **Anki is running** on the local machine
2. **AnkiConnect plugin is installed**
   - Install from Anki: Tools → Add-ons → Get Add-ons
   - Add-on code: **2055492159**
   - Verify installation by visiting `http://localhost:8765` in a browser
3. **Python 3** is available (for using the helper script)

## Quick Start

### Check Connection

First, verify AnkiConnect is accessible:

```bash
${SKILL_DIR}/scripts/anki_connect.py deck-names
```

This should list all your Anki decks. If it fails, ensure Anki is running and AnkiConnect is installed.

### Create a Simple Flashcard

```bash
${SKILL_DIR}/scripts/anki_connect.py add-note \
    --deck "Default" \
    --model "Basic" \
    --fields '{"Front":"What is Python?","Back":"A programming language"}' \
    --tags "python,programming"
```

### Search for Notes

```bash
${SKILL_DIR}/scripts/anki_connect.py find-notes --query "deck:Default tag:python"
```

### List All Decks and Note Types

```bash
${SKILL_DIR}/scripts/anki_connect.py deck-names
${SKILL_DIR}/scripts/anki_connect.py model-names
```

## Best Practices

**IMPORTANT: Avoid Python Scripts for Bulk Operations**

When performing bulk operations (adding many cards, updating tags, moving cards between decks), **do NOT write custom Python scripts** that import the `AnkiConnectClient` library. This approach has been found to be error-prone in practice.

**Instead, use these recommended approaches:**

1. **CLI with JSON files** (Preferred for bulk operations)
   - Create a temporary JSON file with your data
   - Use the CLI command to process the file: `${SKILL_DIR}/scripts/anki_connect.py add-notes --json-file data.json`
   - This is safer, easier to debug, and less error-prone

2. **CLI invoke command** (For operations without dedicated commands)
   - Use `${SKILL_DIR}/scripts/anki_connect.py invoke --action <action> --params <params>`
   - Keeps logic simple and leverages the tested CLI tool

3. **Python library** (Use sparingly and with caution)
   - Only for quick one-off queries or when CLI is genuinely insufficient
   - Examples: checking connection, querying deck names, getting single note info
   - NOT recommended for bulk operations

## Common Workflows

### Workflow 1: Creating Flashcards from Content

When you have content to convert into flashcards:

1. **Identify the deck and note type**
   ```bash
   ${SKILL_DIR}/scripts/anki_connect.py deck-names
   ${SKILL_DIR}/scripts/anki_connect.py model-names
   ```

2. **Check fields for the note type**
   - Use the AnkiConnect API reference to understand field requirements
   - Common note types:
     - **Basic**: Front, Back
     - **Basic (and reversed card)**: Front, Back
     - **Cloze**: Text (with {{c1::cloze deletions}})

3. **Create notes**
   - Single note:
     ```bash
     ${SKILL_DIR}/scripts/anki_connect.py add-note \
         --deck "My Deck" \
         --model "Basic" \
         --fields '{"Front":"Question","Back":"Answer"}' \
         --tags "topic,subtopic"
     ```
   - Multiple notes (from JSON file):
     ```json
     [
       {
         "deckName": "My Deck",
         "modelName": "Basic",
         "fields": {"Front": "Q1", "Back": "A1"},
         "tags": ["tag1"]
       },
       {
         "deckName": "My Deck",
         "modelName": "Basic",
         "fields": {"Front": "Q2", "Back": "A2"},
         "tags": ["tag2"]
       }
     ]
     ```
     ```bash
     ${SKILL_DIR}/scripts/anki_connect.py add-notes --json-file notes.json
     ```

### Workflow 2: Bulk Importing Flashcards

For bulk operations, create a temporary JSON file in `/tmp` and use the CLI:

**Step 1: Create a JSON file** (e.g., `/tmp/bulk_notes.json`) with your notes:

```json
[
  {
    "deckName": "My Deck",
    "modelName": "Basic",
    "fields": {
      "Front": "Question 1",
      "Back": "Answer 1"
    },
    "tags": ["topic1", "subtopic1"]
  },
  {
    "deckName": "My Deck",
    "modelName": "Basic",
    "fields": {
      "Front": "Question 2",
      "Back": "Answer 2"
    },
    "tags": ["topic1", "subtopic2"]
  }
]
```

**Step 2: Import using the CLI:**

```bash
${SKILL_DIR}/scripts/anki_connect.py add-notes --json-file /tmp/bulk_notes.json
```

This approach is safer and less error-prone than writing custom Python scripts.

### Workflow 3: Searching and Querying Cards

Search using Anki's query syntax:

**Common search patterns:**
- `deck:DeckName` - Cards in specific deck
- `tag:tagname` - Cards with specific tag
- `is:due` - Due cards
- `is:new` - New cards
- `is:suspended` - Suspended cards
- `deck:DeckName tag:python` - Combine conditions

**Example: Find all due Python cards**
```bash
${SKILL_DIR}/scripts/anki_connect.py find-cards --query "deck:Programming tag:python is:due"
```

**Example: Get information about specific notes**
```bash
# First find notes
${SKILL_DIR}/scripts/anki_connect.py find-notes --query "deck:Default"

# Then get detailed info (all fields)
${SKILL_DIR}/scripts/anki_connect.py notes-info --note-ids 1234567890 9876543210

# Get only specific fields
${SKILL_DIR}/scripts/anki_connect.py notes-info --note-ids 1234567890 --fields "Front,Back"
```

### Workflow 4: Managing Decks and Organization

**Create a new deck:**
```bash
${SKILL_DIR}/scripts/anki_connect.py create-deck --deck "Python::Advanced Concepts"
```

**Get deck statistics:**
```bash
${SKILL_DIR}/scripts/anki_connect.py invoke \
    --action "getDeckStats" \
    --params '{"decks": ["Default", "Programming"]}'
```

**Move cards to different deck:**

First, find the cards you want to move:
```bash
${SKILL_DIR}/scripts/anki_connect.py find-cards --query "deck:OldDeck tag:python"
# Example output: [1234567890, 9876543210, ...]
```

Then move them using the `changeDeck` action:
```bash
${SKILL_DIR}/scripts/anki_connect.py invoke \
    --action "changeDeck" \
    --params '{"cards": [1234567890, 9876543210], "deck": "NewDeck"}'
```

### Workflow 5–7: Tags, Review Sessions, and Syncing

For tag management, programmatic review session control, and AnkiWeb syncing, see `references/advanced-workflows.md`.

Quick reference:
```bash
# Sync with AnkiWeb
${SKILL_DIR}/scripts/anki_connect.py sync

# List all tags
${SKILL_DIR}/scripts/anki_connect.py invoke --action "getTags" --params '{}'
```

## CLI Reference

Available commands for `${SKILL_DIR}/scripts/anki_connect.py`:
- `add-note` - Create a single flashcard
- `add-notes` - Bulk create from JSON file
- `find-notes` - Search for notes
- `notes-info` - Get note details (supports `--fields` to filter specific fields)
- `find-cards` - Search for cards
- `deck-names` - List all decks
- `create-deck` - Create a new deck
- `model-names` - List note types
- `sync` - Sync with AnkiWeb
- `invoke` - Raw API call for any action

Run `${SKILL_DIR}/scripts/anki_connect.py --help` or `${SKILL_DIR}/scripts/anki_connect.py <command> --help` for details.

## Python Library

**Use sparingly.** The CLI with JSON files is safer for bulk operations. Load `references/advanced-workflows.md` for library usage examples (custom note types, media, batch operations, review session control).

## API Reference

For complete API documentation, including all available actions, parameters, and examples, read [references/api-reference.md](references/api-reference.md).

The API reference covers:
- **Deck Actions**: Create, delete, configure decks
- **Note Actions**: Add, update, search, delete notes
- **Card Actions**: Find, suspend, answer cards
- **Model Actions**: Create and manage note types
- **Media Actions**: Store and retrieve media files
- **Graphical Actions**: Control Anki UI
- **Statistical Actions**: Get review statistics
- **Miscellaneous**: Sync, export, import

## Error Handling

### Common Issues

**1. Connection Failed**
```
ERROR: Cannot connect to AnkiConnect at http://localhost:8765
```
- **Solution**: Ensure Anki is running and AnkiConnect plugin is installed

**2. Invalid Deck Name**
```
AnkiConnect error: Deck 'NonExistent' not found
```
- **Solution**: Create the deck first or check deck name spelling

**3. Invalid Model/Note Type**
```
AnkiConnect error: Model 'NonExistent' not found
```
- **Solution**: Check available models with `model-names` command

**4. Missing Fields**
```
AnkiConnect error: Missing field 'Front'
```
- **Solution**: Ensure all required fields for the note type are provided

**5. Duplicate Note**
```
AnkiConnect error: Cannot create note because it is a duplicate
```
- **Solution**: This is expected behavior to prevent duplicates. Check existing notes or use `updateNoteFields` to modify existing note

### Debugging Tips

1. **Test connection first**:
   ```bash
   curl http://localhost:8765
   ```
   Should return: `"AnkiConnect"`

2. **Verify deck and model names**:
   ```bash
   ${SKILL_DIR}/scripts/anki_connect.py deck-names
   ${SKILL_DIR}/scripts/anki_connect.py model-names
   ```

3. **Check field names for a model** (see `references/advanced-workflows.md` for library usage):
   ```bash
   ${SKILL_DIR}/scripts/anki_connect.py invoke \
       --action "modelFieldNames" \
       --params '{"modelName": "Basic"}'
   ```

4. **Use raw invoke for debugging**:
   ```bash
   ${SKILL_DIR}/scripts/anki_connect.py invoke \
       --action "version" \
       --params '{}'
   ```

## When to Use This Skill

Use this skill when:
- Creating flashcards from learning materials, notes, or documentation
- Creating well-formulated flashcards following best practices
- Converting documentation or learning materials into effective cards
- Bulk importing cards from data sources (CSVs, APIs, databases)
- Automating flashcard generation from code comments or documentation
- Searching and analyzing your card collection
- Managing deck organization and tags
- Automating review workflows
- Syncing operations with AnkiWeb
- Integrating Anki with other tools and workflows
- Programmatically controlling review sessions
- Exporting or importing deck packages

Do NOT use this skill for:
- General Anki usage questions (use Anki documentation)
- Mobile device operations (AnkiConnect is desktop only)
- Operations when Anki is not running
- Direct database manipulation (always use AnkiConnect API)

## Resources

### scripts/anki_connect.py

Portable Python client for AnkiConnect with:
- CLI interface for common operations
- Python library with `AnkiConnectClient` class
- Methods for note, card, deck, and model operations
- Error handling and connection validation

### references/api-reference.md

Complete AnkiConnect API documentation with:
- All available actions organized by category
- Parameter descriptions for each action
- Request/response examples
- Error handling guidance
- Search query syntax reference

### references/card-creation-guide.md

Comprehensive guide on creating effective Anki cards with:
- Cognitive science principles for memory retention
- Card formulation techniques and examples
- Common mistakes and how to avoid them
- Note type selection guidance
- Tagging strategy

### references/advanced-workflows.md

Advanced operations: tag management (Workflow 5), review session control (Workflow 6), AnkiWeb sync (Workflow 7), Python library usage, creating custom note types, adding media, batch operations.
