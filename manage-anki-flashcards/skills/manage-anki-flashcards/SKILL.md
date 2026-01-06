---
name: manage-anki-flashcards
description: This skill should be used when working with Anki flashcard software through the AnkiConnect API. Use for creating flashcards, managing decks, searching notes/cards, syncing collections, controlling review sessions, or any Anki automation tasks.
dependencies:
  - python3
  - Anki
  - AnkiConnect plugin (add-on code: 2055492159)
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
python3 scripts/anki_connect.py deck-names
```

This should list all your Anki decks. If it fails, ensure Anki is running and AnkiConnect is installed.

### Create a Simple Flashcard

```bash
python3 scripts/anki_connect.py add-note \
    --deck "Default" \
    --model "Basic" \
    --fields '{"Front":"What is Python?","Back":"A programming language"}' \
    --tags "python,programming"
```

### Search for Notes

```bash
python3 scripts/anki_connect.py find-notes --query "deck:Default tag:python"
```

### List All Decks and Note Types

```bash
python3 scripts/anki_connect.py deck-names
python3 scripts/anki_connect.py model-names
```

## Best Practices

**IMPORTANT: Avoid Python Scripts for Bulk Operations**

When performing bulk operations (adding many cards, updating tags, moving cards between decks), **do NOT write custom Python scripts** that import the `AnkiConnectClient` library. This approach has been found to be error-prone in practice.

**Instead, use these recommended approaches:**

1. **CLI with JSON files** (Preferred for bulk operations)
   - Create a temporary JSON file with your data
   - Use the CLI command to process the file: `python3 scripts/anki_connect.py add-notes --json-file data.json`
   - This is safer, easier to debug, and less error-prone

2. **CLI invoke command** (For operations without dedicated commands)
   - Use `python3 scripts/anki_connect.py invoke --action <action> --params <params>`
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
   python3 scripts/anki_connect.py deck-names
   python3 scripts/anki_connect.py model-names
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
     python3 scripts/anki_connect.py add-note \
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
     python3 scripts/anki_connect.py add-notes --json-file notes.json
     ```

### Workflow 2: Bulk Importing Flashcards

For bulk operations, create a temporary JSON file with your data and use the CLI:

**Step 1: Create a JSON file** (e.g., `bulk_notes.json`) with your notes:

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
python3 scripts/anki_connect.py add-notes --json-file bulk_notes.json
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
python3 scripts/anki_connect.py find-cards --query "deck:Programming tag:python is:due"
```

**Example: Get information about specific notes**
```bash
# First find notes
python3 scripts/anki_connect.py find-notes --query "deck:Default"

# Then get detailed info (all fields)
python3 scripts/anki_connect.py notes-info --note-ids 1234567890 9876543210

# Get only specific fields
python3 scripts/anki_connect.py notes-info --note-ids 1234567890 --fields "Front,Back"
```

### Workflow 4: Managing Decks and Organization

**Create a new deck:**
```bash
python3 scripts/anki_connect.py create-deck --deck "Python::Advanced Concepts"
```

**Get deck statistics:**
```bash
python3 scripts/anki_connect.py invoke \
    --action "getDeckStats" \
    --params '{"decks": ["Default", "Programming"]}'
```

**Move cards to different deck:**

First, find the cards you want to move:
```bash
python3 scripts/anki_connect.py find-cards --query "deck:OldDeck tag:python"
# Example output: [1234567890, 9876543210, ...]
```

Then move them using the `changeDeck` action:
```bash
python3 scripts/anki_connect.py invoke \
    --action "changeDeck" \
    --params '{"cards": [1234567890, 9876543210], "deck": "NewDeck"}'
```

### Workflow 5: Managing Tags

**Add tags to existing notes:**

First, find the notes you want to tag:
```bash
python3 scripts/anki_connect.py find-notes --query "deck:Programming -tag:reviewed"
# Example output: [1234567890, 9876543210, ...]
```

Then add the tags:
```bash
python3 scripts/anki_connect.py invoke \
    --action "addTags" \
    --params '{"notes": [1234567890, 9876543210], "tags": "reviewed"}'
```

**List all tags:**
```bash
python3 scripts/anki_connect.py invoke \
    --action "getTags" \
    --params '{}'
```

### Workflow 6: Review Session Control

Control Anki's review interface programmatically:

```python
from scripts.anki_connect import AnkiConnectClient

client = AnkiConnectClient()

# Open deck for review
client.invoke("guiDeckReview", {"name": "Default"})

# Get current card
current = client.invoke("guiCurrentCard")
if current:
    print(f"Question: {current['question']}")

    # Show answer
    client.invoke("guiShowAnswer")

    # Answer with "Good" (ease=3)
    client.invoke("guiAnswerCard", {"ease": 3})
```

### Workflow 7: Syncing with AnkiWeb

```bash
python3 scripts/anki_connect.py sync
```

Or programmatically:
```python
from scripts.anki_connect import AnkiConnectClient

client = AnkiConnectClient()
client.sync()
print("Synced with AnkiWeb")
```

## Using the Python Script

The `anki_connect.py` script provides both a CLI interface and a Python library.

### CLI Usage

Available commands:
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

**CLI Examples:**
```bash
# Get help
python3 scripts/anki_connect.py --help
python3 scripts/anki_connect.py add-note --help

# Raw API call
python3 scripts/anki_connect.py invoke \
    --action "deckNames" \
    --params '{}'

# Search with complex query
python3 scripts/anki_connect.py find-notes \
    --query "deck:Default (tag:python OR tag:javascript) -is:suspended"
```

### Library Usage

**WARNING: Use the Python library sparingly and with caution.**

The `AnkiConnectClient` Python library should only be used for:
- Quick one-off queries (checking connection, getting deck names, single note lookups)
- Cases where the CLI is genuinely insufficient

**Do NOT use the Python library for bulk operations** - instead, use the CLI with JSON files as shown in the workflows above. Writing custom Python scripts for bulk operations is error-prone.

If you must use the library, here's how to import and use the `AnkiConnectClient` class:

---

## Creating Effective Anki Cards

This section captures established best practices for creating effective flashcards based on cognitive science research, particularly the "20 Rules of Formulating Knowledge" and spaced repetition literature.

### Core Principles

#### 1. Understand Before You Memorize
- **DO**: Build comprehension before creating cards. Read full chapters/docs first.
- **DON'T**: Create cards for material you don't understand - this yields negligible value.
- **Why**: Individual facts without context are like "scattered words" - disconnected and fragile.

#### 2. Minimum Information Principle
- **DO**: Keep each card focused on ONE atomic piece of information
- **DO**: Make answers brief and specific
- **DON'T**: Create multi-part questions or lengthy answers
- **Why**: Simple items are neurologically easier to process consistently and schedule efficiently

**Bad Example:**
```
Q: What are the characteristics of the Dead Sea?
A: Salt lake, borders Israel/Jordan, 420m below sea level, 67km long, 18km wide, 377m deep, 33.7% salinity
```

**Good Example (split into separate cards):**
```
Q: What type of body of water is the Dead Sea?
A: Salt lake

Q: What countries border the Dead Sea?
A: Israel and Jordan

Q: What is the Dead Sea's elevation?
A: 420m below sea level
```

#### 3. Use Cloze Deletions Effectively
- **DO**: Convert complex sentences into cloze format: `{{c1::answer}}`
- **DO**: Create multiple cloze cards from one sentence for different facts
- **Example**: "Bill {{c1::Clinton}} was the {{c2::second}} US president to go through impeachment"

#### 4. Avoid Sets and Unordered Lists
- **DON'T**: Ask "What are the EU countries?" or "List the AWS compute services"
- **DO**: Convert sets into ordered sequences, relationships, or contextual items
- **Why**: Unordered sets overload memory because each recall uses different mental sequencing

#### 5. Combat Interference
- **DO**: Add distinguishing context for similar items
- **DO**: Use examples, emotional content, or personal references
- **DON'T**: Create cards that look nearly identical
- **Why**: Interference is "probably the single greatest cause of forgetting"

### Card Formulation Techniques

#### Use Imagery
- Visual memory is stronger than verbal memory
- Include diagrams, charts, maps for spatial/relational concepts
- "One picture is worth a thousand words"

#### Personalize and Add Examples
- Connect items to personal experiences
- Use specific, concrete examples rather than abstract definitions
- Personal references create distinctive neural pathways

#### Provide Context Cues
- Use category labels, prefixes, or tags (e.g., `bioch: GRE`, `aws: ec2`)
- Context reduces necessary wording and prevents interference

#### Strategic Redundancy
- Create complementary cards from different angles (e.g., term→definition AND definition→term)
- Different viewpoints strengthen recall probability

### Common Mistakes to Avoid

| Mistake | Problem | Solution |
|---------|---------|----------|
| Cards too complex | Multiple neural pathways cause interference | Split into atomic cards |
| Learning without understanding | Creates "useless material" | Read/understand first |
| Memorizing unordered lists | Each recall uses different sequencing | Convert to ordered sequences or relationships |
| Identical-looking cards | Causes chronic interference | Add distinguishing context |
| Skipping basics | Forgetting basics creates cascading problems | Start with fundamentals |
| Verbose answers | Hard to recall consistently | Keep answers brief (ideally 1-5 words) |

### Effective Note Types

| Note Type | Best For | Field Structure |
|-----------|----------|-----------------|
| Basic | Simple Q&A facts | Front, Back |
| Basic (reversed) | Bidirectional learning (vocabulary) | Front, Back |
| Cloze | Sentences with fill-in-blank | Text with {{c1::deletions}} |
| Image Occlusion | Diagrams, anatomy, maps | Image with masked regions |

### Tags Strategy
- Use hierarchical tags: `programming::python::syntax`
- Tag by topic, source, and difficulty
- Tag volatile information with dates: `2024-data`
- Use tags to filter review sessions

### When to Use Different Card Types

**Use Basic cards for:**
- Definitions and terminology
- Simple factual associations
- Command syntax and shortcuts

**Use Cloze cards for:**
- Converting textbook sentences
- Learning sequences/processes
- Fill-in-the-blank from documentation

**Use Image Occlusion for:**
- Architecture diagrams
- Flowcharts and processes
- Geographic/spatial information

---

```python
from scripts.anki_connect import AnkiConnectClient

# Initialize client
client = AnkiConnectClient()

# Check connection
if not client.check_connection():
    print("Cannot connect to AnkiConnect")
    exit(1)

# Use any method
decks = client.deck_names()
models = client.model_names()
note_id = client.add_note(
    deck_name="Default",
    model_name="Basic",
    fields={"Front": "Question", "Back": "Answer"},
    tags=["python"]
)

# Get note information (all fields)
notes = client.notes_info([note_id])

# Get note information (specific fields only)
notes = client.notes_info([note_id], fields=["Front", "Back"])

# Use invoke() for any API action
result = client.invoke("getDeckStats", {"decks": ["Default"]})
```

## Advanced Operations

**NOTE:** The examples in this section use the Python library for demonstration purposes. These are advanced, one-off operations where the Python approach may be acceptable. However, for any bulk operations, you should still prefer the CLI with JSON files approach as described in the Best Practices section.

### Creating Custom Note Types

```python
from scripts.anki_connect import AnkiConnectClient

client = AnkiConnectClient()

# Create a new note type with three fields
client.invoke("createModel", {
    "modelName": "Programming Card",
    "inOrderFields": ["Concept", "Code", "Explanation"],
    "cardTemplates": [
        {
            "Front": "<h2>{{Concept}}</h2><pre>{{Code}}</pre>",
            "Back": "{{FrontSide}}<hr><div>{{Explanation}}</div>"
        }
    ],
    "css": ".card { font-family: monospace; font-size: 16px; }"
})
```

### Adding Media to Cards

```python
from scripts.anki_connect import AnkiConnectClient

client = AnkiConnectClient()

# Store image from URL
client.invoke("storeMediaFile", {
    "filename": "diagram.png",
    "url": "https://example.com/diagram.png"
})

# Add note with image
client.add_note(
    deck_name="Default",
    model_name="Basic",
    fields={
        "Front": "What does this diagram show?<br><img src='diagram.png'>",
        "Back": "System architecture overview"
    }
)
```

### Batch Operations with Multi

Execute multiple operations in one request:

```python
from scripts.anki_connect import AnkiConnectClient

client = AnkiConnectClient()

result = client.invoke("multi", {
    "actions": [
        {"action": "deckNames"},
        {"action": "modelNames"},
        {"action": "getTags"}
    ]
})

decks, models, tags = result
```

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
   python3 scripts/anki_connect.py deck-names
   python3 scripts/anki_connect.py model-names
   ```

3. **Check field names for a model**:
   ```python
   from scripts.anki_connect import AnkiConnectClient
   client = AnkiConnectClient()
   fields = client.model_field_names("Basic")
   print(fields)  # ['Front', 'Back']
   ```

4. **Use raw invoke for debugging**:
   ```bash
   python3 scripts/anki_connect.py invoke \
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
