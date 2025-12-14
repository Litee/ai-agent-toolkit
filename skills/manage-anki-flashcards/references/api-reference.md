# AnkiConnect API Reference

Complete reference for all AnkiConnect API actions. All requests use JSON format sent to `http://localhost:8765`.

## Request/Response Format

### Request Structure
```json
{
  "action": "actionName",
  "version": 6,
  "params": {...},
  "key": "optional_api_key"
}
```

### Response Structure
```json
{
  "result": <value>,
  "error": null
}
```

If an error occurs, `error` will contain the error message and `result` will be null.

---

## Deck Actions

### deckNames
Get list of all deck names.

**Parameters:** None

**Example:**
```json
{
  "action": "deckNames",
  "version": 6
}
```

**Result:**
```json
["Default", "Japanese::Vocab", "Programming"]
```

---

### deckNamesAndIds
Get mapping of deck names to IDs.

**Parameters:** None

**Example:**
```json
{
  "action": "deckNamesAndIds",
  "version": 6
}
```

**Result:**
```json
{
  "Default": 1,
  "Japanese::Vocab": 1234567890123,
  "Programming": 9876543210987
}
```

---

### createDeck
Create a new deck.

**Parameters:**
- `deck` (string): Deck name (supports hierarchy with `::`)

**Example:**
```json
{
  "action": "createDeck",
  "version": 6,
  "params": {
    "deck": "My New Deck::Subdeck"
  }
}
```

**Result:** Deck ID (integer)

---

### deleteDecks
Delete decks and optionally their cards.

**Parameters:**
- `decks` (array of strings): Deck names to delete
- `cardsToo` (boolean): Must be `true` to delete cards

**Example:**
```json
{
  "action": "deleteDecks",
  "version": 6,
  "params": {
    "decks": ["Old Deck", "Unused Deck"],
    "cardsToo": true
  }
}
```

**Result:** `null` on success

---

### getDeckStats
Get statistics for specified decks.

**Parameters:**
- `decks` (array of strings): Deck names

**Example:**
```json
{
  "action": "getDeckStats",
  "version": 6,
  "params": {
    "decks": ["Default"]
  }
}
```

**Result:**
```json
{
  "Default": {
    "new_count": 20,
    "learn_count": 15,
    "review_count": 10,
    "total_in_deck": 100
  }
}
```

---

### changeDeck
Move cards to a different deck.

**Parameters:**
- `cards` (array of integers): Card IDs to move
- `deck` (string): Target deck name

**Example:**
```json
{
  "action": "changeDeck",
  "version": 6,
  "params": {
    "cards": [1234567890, 9876543210],
    "deck": "Target Deck"
  }
}
```

**Result:** `null` on success

---

### getDeckConfig
Get configuration for a deck.

**Parameters:**
- `deck` (string): Deck name

**Example:**
```json
{
  "action": "getDeckConfig",
  "version": 6,
  "params": {
    "deck": "Default"
  }
}
```

**Result:** Configuration object with scheduling settings

---

## Note Actions

### addNote
Add a single note.

**Parameters:**
- `note` (object):
  - `deckName` (string): Target deck
  - `modelName` (string): Note type/model name
  - `fields` (object): Field name to value mapping
  - `tags` (array of strings, optional): Tags to add
  - `audio` (array, optional): Audio files to include
  - `video` (array, optional): Video files to include
  - `picture` (array, optional): Image files to include

**Example:**
```json
{
  "action": "addNote",
  "version": 6,
  "params": {
    "note": {
      "deckName": "Default",
      "modelName": "Basic",
      "fields": {
        "Front": "What is Python?",
        "Back": "A high-level programming language"
      },
      "tags": ["python", "programming"]
    }
  }
}
```

**Result:** Note ID (integer) or `null` if failed

---

### addNotes
Add multiple notes in one request.

**Parameters:**
- `notes` (array of objects): Array of note objects (same structure as `addNote`)

**Example:**
```json
{
  "action": "addNotes",
  "version": 6,
  "params": {
    "notes": [
      {
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Question 1", "Back": "Answer 1"},
        "tags": ["tag1"]
      },
      {
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Question 2", "Back": "Answer 2"},
        "tags": ["tag2"]
      }
    ]
  }
}
```

**Result:** Array of note IDs (`null` for failed notes)

---

### findNotes
Search for notes matching a query.

**Parameters:**
- `query` (string): Anki search query

**Search Query Syntax:**
- `deck:DeckName` - Notes in specific deck
- `tag:tagname` - Notes with specific tag
- `card:CardType` - Notes with specific card type
- `is:due` - Due cards
- `is:new` - New cards
- `is:suspended` - Suspended cards
- Combine with AND/OR/NOT operators

**Example:**
```json
{
  "action": "findNotes",
  "version": 6,
  "params": {
    "query": "deck:Default tag:python"
  }
}
```

**Result:** Array of note IDs

---

### notesInfo
Get detailed information about notes.

**Parameters:**
- `notes` (array of integers): Note IDs

**Example:**
```json
{
  "action": "notesInfo",
  "version": 6,
  "params": {
    "notes": [1234567890, 9876543210]
  }
}
```

**Result:**
```json
[
  {
    "noteId": 1234567890,
    "modelName": "Basic",
    "tags": ["python", "programming"],
    "fields": {
      "Front": {"value": "What is Python?", "order": 0},
      "Back": {"value": "A programming language", "order": 1}
    },
    "cards": [1111111111]
  }
]
```

---

### updateNoteFields
Update fields of an existing note.

**Parameters:**
- `note` (object):
  - `id` (integer): Note ID
  - `fields` (object): Field name to new value mapping

**Example:**
```json
{
  "action": "updateNoteFields",
  "version": 6,
  "params": {
    "note": {
      "id": 1234567890,
      "fields": {
        "Front": "Updated question",
        "Back": "Updated answer"
      }
    }
  }
}
```

**Result:** `null` on success

---

### updateNote
Update fields and/or tags of a note.

**Parameters:**
- `note` (object):
  - `id` (integer): Note ID
  - `fields` (object, optional): Field updates
  - `tags` (array of strings, optional): New tag list

**Example:**
```json
{
  "action": "updateNote",
  "version": 6,
  "params": {
    "note": {
      "id": 1234567890,
      "fields": {"Front": "New question"},
      "tags": ["updated", "python"]
    }
  }
}
```

**Result:** `null` on success

---

### deleteNotes
Delete notes and their associated cards.

**Parameters:**
- `notes` (array of integers): Note IDs to delete

**Example:**
```json
{
  "action": "deleteNotes",
  "version": 6,
  "params": {
    "notes": [1234567890, 9876543210]
  }
}
```

**Result:** `null` on success

---

### addTags
Add tags to notes.

**Parameters:**
- `notes` (array of integers): Note IDs
- `tags` (string): Space-separated tags to add

**Example:**
```json
{
  "action": "addTags",
  "version": 6,
  "params": {
    "notes": [1234567890],
    "tags": "important reviewed"
  }
}
```

**Result:** `null` on success

---

### removeTags
Remove tags from notes.

**Parameters:**
- `notes` (array of integers): Note IDs
- `tags` (string): Space-separated tags to remove

**Example:**
```json
{
  "action": "removeTags",
  "version": 6,
  "params": {
    "notes": [1234567890],
    "tags": "obsolete"
  }
}
```

**Result:** `null` on success

---

### getTags
Get all tags in the collection.

**Parameters:** None

**Example:**
```json
{
  "action": "getTags",
  "version": 6
}
```

**Result:** Array of tag strings

---

## Card Actions

### findCards
Search for cards matching a query.

**Parameters:**
- `query` (string): Anki search query (same syntax as `findNotes`)

**Example:**
```json
{
  "action": "findCards",
  "version": 6,
  "params": {
    "query": "deck:Default is:due"
  }
}
```

**Result:** Array of card IDs

---

### cardsInfo
Get detailed information about cards.

**Parameters:**
- `cards` (array of integers): Card IDs

**Example:**
```json
{
  "action": "cardsInfo",
  "version": 6,
  "params": {
    "cards": [1111111111]
  }
}
```

**Result:**
```json
[
  {
    "cardId": 1111111111,
    "fields": {"Front": {"value": "Question"}, "Back": {"value": "Answer"}},
    "fieldOrder": 0,
    "question": "<div>Question</div>",
    "answer": "<div>Answer</div>",
    "modelName": "Basic",
    "deckName": "Default",
    "css": "card style CSS",
    "interval": 10,
    "note": 1234567890,
    "type": 2,
    "queue": 2,
    "due": 12345,
    "reps": 5,
    "lapses": 0,
    "left": 0
  }
]
```

---

### suspend
Suspend cards (prevent from appearing in reviews).

**Parameters:**
- `cards` (array of integers): Card IDs to suspend

**Example:**
```json
{
  "action": "suspend",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** `true` if any card state changed

---

### unsuspend
Unsuspend cards (allow them in reviews again).

**Parameters:**
- `cards` (array of integers): Card IDs to unsuspend

**Example:**
```json
{
  "action": "unsuspend",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** `true` if any card state changed

---

### areSuspended
Check if cards are suspended.

**Parameters:**
- `cards` (array of integers): Card IDs to check

**Example:**
```json
{
  "action": "areSuspended",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** Array of booleans

---

### areDue
Check if cards are due for review.

**Parameters:**
- `cards` (array of integers): Card IDs to check

**Example:**
```json
{
  "action": "areDue",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** Array of booleans

---

### getIntervals
Get review intervals for cards.

**Parameters:**
- `cards` (array of integers): Card IDs
- `complete` (boolean, optional): Get full interval history

**Example:**
```json
{
  "action": "getIntervals",
  "version": 6,
  "params": {
    "cards": [1111111111]
  }
}
```

**Result:** Array of arrays with intervals (negative for seconds, positive for days)

---

### answerCards
Submit review answers for cards.

**Parameters:**
- `answers` (array of objects):
  - `cardId` (integer): Card ID
  - `ease` (integer): Answer button (1=Again, 2=Hard, 3=Good, 4=Easy)

**Example:**
```json
{
  "action": "answerCards",
  "version": 6,
  "params": {
    "answers": [
      {"cardId": 1111111111, "ease": 3},
      {"cardId": 2222222222, "ease": 4}
    ]
  }
}
```

**Result:** Array of success booleans

---

### setDueDate
Set due dates for cards.

**Parameters:**
- `cards` (array of integers): Card IDs
- `days` (string): Days from now (e.g., "0", "3", "3-7" for random)

**Example:**
```json
{
  "action": "setDueDate",
  "version": 6,
  "params": {
    "cards": [1111111111],
    "days": "5"
  }
}
```

**Result:** `true` on success

---

### forgetCards
Reset card learning progress.

**Parameters:**
- `cards` (array of integers): Card IDs to reset

**Example:**
```json
{
  "action": "forgetCards",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** `null` on success

---

### relearnCards
Move cards back to learning queue.

**Parameters:**
- `cards` (array of integers): Card IDs

**Example:**
```json
{
  "action": "relearnCards",
  "version": 6,
  "params": {
    "cards": [1111111111]
  }
}
```

**Result:** `null` on success

---

## Model (Note Type) Actions

### modelNames
Get list of all note type names.

**Parameters:** None

**Example:**
```json
{
  "action": "modelNames",
  "version": 6
}
```

**Result:** `["Basic", "Basic (and reversed card)", "Cloze"]`

---

### modelNamesAndIds
Get mapping of model names to IDs.

**Parameters:** None

**Example:**
```json
{
  "action": "modelNamesAndIds",
  "version": 6
}
```

**Result:**
```json
{
  "Basic": 1234567890123,
  "Cloze": 9876543210987
}
```

---

### modelFieldNames
Get field names for a model.

**Parameters:**
- `modelName` (string): Model/note type name

**Example:**
```json
{
  "action": "modelFieldNames",
  "version": 6,
  "params": {
    "modelName": "Basic"
  }
}
```

**Result:** `["Front", "Back"]`

---

### createModel
Create a new note type.

**Parameters:**
- `modelName` (string): Name for the new model
- `inOrderFields` (array of strings): Field names in order
- `cardTemplates` (array of objects): Card template definitions
  - `Front` (string): Front template HTML
  - `Back` (string): Back template HTML
- `css` (string, optional): Styling CSS
- `isCloze` (boolean, optional): Whether this is a cloze model

**Example:**
```json
{
  "action": "createModel",
  "version": 6,
  "params": {
    "modelName": "Custom Model",
    "inOrderFields": ["Question", "Answer", "Extra"],
    "cardTemplates": [
      {
        "Front": "{{Question}}",
        "Back": "{{Answer}}<br>{{Extra}}"
      }
    ],
    "css": ".card { font-family: Arial; }"
  }
}
```

**Result:** Model object

---

### findModelsById
Get model definitions by ID.

**Parameters:**
- `modelIds` (array of integers): Model IDs

**Example:**
```json
{
  "action": "findModelsById",
  "version": 6,
  "params": {
    "modelIds": [1234567890123]
  }
}
```

**Result:** Array of model objects with complete definitions

---

### findModelsByName
Get model definitions by name.

**Parameters:**
- `modelNames` (array of strings): Model names

**Example:**
```json
{
  "action": "findModelsByName",
  "version": 6,
  "params": {
    "modelNames": ["Basic"]
  }
}
```

**Result:** Array of model objects

---

## Media Actions

### storeMediaFile
Add a file to Anki's media folder.

**Parameters:**
- `filename` (string): File name
- One of:
  - `data` (string): Base64 encoded file content
  - `path` (string): Path to local file
  - `url` (string): URL to download from
- `deleteExisting` (boolean, optional): Overwrite if exists (default: true)

**Example:**
```json
{
  "action": "storeMediaFile",
  "version": 6,
  "params": {
    "filename": "image.jpg",
    "url": "https://example.com/image.jpg"
  }
}
```

**Result:** Filename string

---

### retrieveMediaFile
Get a media file as base64.

**Parameters:**
- `filename` (string): Media filename

**Example:**
```json
{
  "action": "retrieveMediaFile",
  "version": 6,
  "params": {
    "filename": "image.jpg"
  }
}
```

**Result:** Base64 encoded content or `false` if not found

---

### getMediaFilesNames
List media files matching a pattern.

**Parameters:**
- `pattern` (string, optional): Wildcard pattern (default: "*")

**Example:**
```json
{
  "action": "getMediaFilesNames",
  "version": 6,
  "params": {
    "pattern": "*.jpg"
  }
}
```

**Result:** Array of matching filenames

---

### deleteMediaFile
Remove a media file.

**Parameters:**
- `filename` (string): Media filename to delete

**Example:**
```json
{
  "action": "deleteMediaFile",
  "version": 6,
  "params": {
    "filename": "old_image.jpg"
  }
}
```

**Result:** `null` on success

---

## Graphical Actions

### guiBrowse
Open card browser with a search query.

**Parameters:**
- `query` (string): Search query

**Example:**
```json
{
  "action": "guiBrowse",
  "version": 6,
  "params": {
    "query": "deck:Default tag:important"
  }
}
```

**Result:** Array of matching card IDs

---

### guiAddCards
Open add cards dialog with pre-filled note.

**Parameters:**
- `note` (object): Note object with deck, model, fields, tags (same as `addNote`)

**Example:**
```json
{
  "action": "guiAddCards",
  "version": 6,
  "params": {
    "note": {
      "deckName": "Default",
      "modelName": "Basic",
      "fields": {"Front": "Prefilled question", "Back": "Prefilled answer"}
    }
  }
}
```

**Result:** Prospective note ID

---

### guiEditNote
Open note editor for a specific note.

**Parameters:**
- `note` (integer): Note ID

**Example:**
```json
{
  "action": "guiEditNote",
  "version": 6,
  "params": {
    "note": 1234567890
  }
}
```

**Result:** `null` on success

---

### guiCurrentCard
Get information about the card currently in reviewer.

**Parameters:** None

**Example:**
```json
{
  "action": "guiCurrentCard",
  "version": 6
}
```

**Result:** Card object with question/answer/buttons or `null` if not reviewing

---

### guiStartCardTimer
Start timer for current card in reviewer.

**Parameters:** None

**Result:** `true` if in review mode

---

### guiShowQuestion
Show question side of current card.

**Parameters:** None

**Result:** `true` if in review mode with question shown

---

### guiShowAnswer
Show answer side of current card.

**Parameters:** None

**Result:** `true` if in review mode with answer shown

---

### guiAnswerCard
Submit answer for current card in reviewer.

**Parameters:**
- `ease` (integer): Answer button (1-4)

**Example:**
```json
{
  "action": "guiAnswerCard",
  "version": 6,
  "params": {
    "ease": 3
  }
}
```

**Result:** `true` if successful

---

### guiDeckOverview
Open deck overview.

**Parameters:**
- `name` (string): Deck name

**Example:**
```json
{
  "action": "guiDeckOverview",
  "version": 6,
  "params": {
    "name": "Default"
  }
}
```

**Result:** `true` on success

---

### guiDeckBrowser
Open deck browser/selector.

**Parameters:** None

**Result:** `true` on success

---

### guiDeckReview
Start reviewing a deck.

**Parameters:**
- `name` (string): Deck name

**Example:**
```json
{
  "action": "guiDeckReview",
  "version": 6,
  "params": {
    "name": "Default"
  }
}
```

**Result:** `true` on success

---

### guiExitAnki
Close Anki gracefully.

**Parameters:** None

**Result:** Async, no return value

---

## Statistical Actions

### getNumCardsReviewedToday
Get number of cards reviewed today.

**Parameters:** None

**Example:**
```json
{
  "action": "getNumCardsReviewedToday",
  "version": 6
}
```

**Result:** Integer count

---

### getNumCardsReviewedByDay
Get review counts by day.

**Parameters:** None

**Example:**
```json
{
  "action": "getNumCardsReviewedByDay",
  "version": 6
}
```

**Result:** Array of `[date_string, count]` pairs

---

### cardReviews
Get review history for a deck.

**Parameters:**
- `deck` (string): Deck name
- `startID` (integer): Unix timestamp (exclusive lower bound)

**Example:**
```json
{
  "action": "cardReviews",
  "version": 6,
  "params": {
    "deck": "Default",
    "startID": 1640000000000
  }
}
```

**Result:** Array of 9-tuples: (time, cardID, usn, buttonPressed, newInterval, previousInterval, factor, duration, type)

---

### getReviewsOfCards
Get review history for specific cards.

**Parameters:**
- `cards` (array of integers): Card IDs

**Example:**
```json
{
  "action": "getReviewsOfCards",
  "version": 6,
  "params": {
    "cards": [1111111111, 2222222222]
  }
}
```

**Result:** Object mapping card IDs to arrays of review records

---

### getCollectionStatsHTML
Get statistics as HTML.

**Parameters:**
- `wholeCollection` (boolean, optional): Stats for entire collection vs current deck

**Example:**
```json
{
  "action": "getCollectionStatsHTML",
  "version": 6,
  "params": {
    "wholeCollection": true
  }
}
```

**Result:** HTML string with statistics

---

## Miscellaneous Actions

### version
Get AnkiConnect API version.

**Parameters:** None

**Example:**
```json
{
  "action": "version",
  "version": 6
}
```

**Result:** Integer version number (currently 6)

---

### sync
Synchronize collection with AnkiWeb.

**Parameters:** None

**Example:**
```json
{
  "action": "sync",
  "version": 6
}
```

**Result:** `null` on success

---

### multi
Execute multiple actions in one request.

**Parameters:**
- `actions` (array of objects): Array of action objects (each with `action` and `params`)

**Example:**
```json
{
  "action": "multi",
  "version": 6,
  "params": {
    "actions": [
      {"action": "deckNames"},
      {"action": "modelNames"}
    ]
  }
}
```

**Result:** Array of results (one per action)

---

### exportPackage
Export deck as .apkg file.

**Parameters:**
- `deck` (string): Deck name
- `path` (string): Output file path
- `includeSched` (boolean, optional): Include scheduling info

**Example:**
```json
{
  "action": "exportPackage",
  "version": 6,
  "params": {
    "deck": "My Deck",
    "path": "/path/to/export.apkg",
    "includeSched": true
  }
}
```

**Result:** `true` on success

---

### importPackage
Import .apkg file.

**Parameters:**
- `path` (string): Path to .apkg file (relative to media folder)

**Example:**
```json
{
  "action": "importPackage",
  "version": 6,
  "params": {
    "path": "../import.apkg"
  }
}
```

**Result:** `true` on success

---

### reloadCollection
Reload collection from disk.

**Parameters:** None

**Example:**
```json
{
  "action": "reloadCollection",
  "version": 6
}
```

**Result:** `null` on success

---

## Error Handling

When an error occurs, the response will have:
```json
{
  "result": null,
  "error": "Error description here"
}
```

Common errors:
- **Connection refused**: Anki is not running or AnkiConnect is not installed
- **Cannot find deck/model**: Specified deck or note type doesn't exist
- **Invalid field names**: Field doesn't exist in the model
- **Duplicate note**: Note with same content already exists (for addNote)
- **Invalid parameters**: Missing required parameters or wrong types
