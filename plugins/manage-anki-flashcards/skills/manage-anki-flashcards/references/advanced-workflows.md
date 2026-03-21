# Advanced Anki Workflows

Reference for less-common operations. Load this file when the user needs tag management, review session control, AnkiWeb sync, advanced Python operations, or library usage beyond the CLI.

## Workflow 5: Managing Tags

**Add tags to existing notes:**

```bash
# Find notes to tag
${SKILL_DIR}/scripts/anki_connect.py find-notes --query "deck:Programming -tag:reviewed"
# Example output: [1234567890, 9876543210, ...]

# Add tags
${SKILL_DIR}/scripts/anki_connect.py invoke \
    --action "addTags" \
    --params '{"notes": [1234567890, 9876543210], "tags": "reviewed"}'

# Remove tags
${SKILL_DIR}/scripts/anki_connect.py invoke \
    --action "removeTags" \
    --params '{"notes": [1234567890], "tags": "reviewed"}'

# List all tags in the collection
${SKILL_DIR}/scripts/anki_connect.py invoke \
    --action "getTags" \
    --params '{}'
```

## Workflow 6: Review Session Control

Control Anki's review interface programmatically (Python library only — no CLI equivalent):

```python
from scripts.anki_connect import AnkiConnectClient  # run from skill directory

client = AnkiConnectClient()

# Open deck for review
client.invoke("guiDeckReview", {"name": "Default"})

# Get current card
current = client.invoke("guiCurrentCard")
if current:
    print(f"Question: {current['question']}")
    client.invoke("guiShowAnswer")
    # ease: 1=Again, 2=Hard, 3=Good, 4=Easy
    client.invoke("guiAnswerCard", {"ease": 3})
```

## Workflow 7: Syncing with AnkiWeb

```bash
${SKILL_DIR}/scripts/anki_connect.py sync
```

## Python Library Usage

**Use sparingly.** Prefer CLI for bulk operations — it is less error-prone.

The `AnkiConnectClient` class is appropriate for:
- Quick one-off queries (checking connection, getting deck names, single note lookups)
- GUI/review session control (no CLI equivalent)
- Cases where `invoke` with raw JSON is genuinely awkward

```python
from scripts.anki_connect import AnkiConnectClient  # run from skill directory

client = AnkiConnectClient()

# Check connection
if not client.check_connection():
    print("Cannot connect to AnkiConnect")
    exit(1)

# Basic operations
decks = client.deck_names()
models = client.model_names()
note_id = client.add_note(
    deck_name="Default",
    model_name="Basic",
    fields={"Front": "Question", "Back": "Answer"},
    tags=["python"]
)
notes = client.notes_info([note_id])
notes_filtered = client.notes_info([note_id], fields=["Front", "Back"])
result = client.invoke("getDeckStats", {"decks": ["Default"]})
```

### Creating Custom Note Types

```python
from scripts.anki_connect import AnkiConnectClient  # run from skill directory

client = AnkiConnectClient()
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
from scripts.anki_connect import AnkiConnectClient  # run from skill directory

client = AnkiConnectClient()
client.invoke("storeMediaFile", {
    "filename": "diagram.png",
    "url": "https://example.com/diagram.png"
})
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

```python
from scripts.anki_connect import AnkiConnectClient  # run from skill directory

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

### Check Field Names for a Model

```python
from scripts.anki_connect import AnkiConnectClient  # run from skill directory
client = AnkiConnectClient()
fields = client.model_field_names("Basic")
print(fields)  # ['Front', 'Back']
```
