#!/usr/bin/env python3
"""
AnkiConnect API Client

A portable Python client for interacting with Anki through the AnkiConnect plugin.
Supports common operations and provides a CLI interface for direct execution.

Prerequisites:
- Anki must be running
- AnkiConnect plugin must be installed (add-on code: 2055492159)

Usage:
    # Add a single note
    python3 anki_connect.py add-note --deck "Default" --model "Basic" \\
        --fields '{"Front":"What is Python?","Back":"A programming language"}'

    # Add multiple notes from JSON
    python3 anki_connect.py add-notes --json-file notes.json

    # Search for notes
    python3 anki_connect.py find-notes --query "deck:Default"

    # Get note information
    python3 anki_connect.py notes-info --note-ids 1234567890 9876543210

    # Get note information with specific fields only
    python3 anki_connect.py notes-info --note-ids 1234567890 --fields "Front,Back"

    # List all decks
    python3 anki_connect.py deck-names

    # Create a new deck
    python3 anki_connect.py create-deck --deck "My New Deck"

    # List all note types
    python3 anki_connect.py model-names

    # Sync with AnkiWeb
    python3 anki_connect.py sync

    # Raw API call
    python3 anki_connect.py invoke --action "deckNames" --params '{}'
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


def parse_json_argument(value: str, arg_name: str) -> dict:
    """
    Parse and validate a JSON argument, providing helpful error messages.

    Args:
        value: The JSON string to parse
        arg_name: The name of the argument (for error messages)

    Returns:
        The parsed dictionary

    Raises:
        ValueError: If the JSON is malformed or not a dictionary
    """
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON for {arg_name}: {e.msg} at position {e.pos}\n"
            f"Input: {value}\n"
            f"Hint: Ensure property names are double-quoted, e.g., "
            f'{{"Front":"value","Back":"value"}}'
        )

    if not isinstance(parsed, dict):
        raise ValueError(
            f"{arg_name} must be a JSON object (dict), not {type(parsed).__name__}\n"
            f"Expected format: {{\"key\": \"value\"}}"
        )

    return parsed


class AnkiConnectClient:
    """Client for interacting with AnkiConnect API."""

    def __init__(self, url: str = "http://localhost:8765"):
        """
        Initialize AnkiConnect client.

        Args:
            url: AnkiConnect endpoint URL (default: http://localhost:8765)
        """
        self.url = url
        self.version = 6

    def invoke(self, action: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Invoke an AnkiConnect API action.

        Args:
            action: The API action name
            params: Parameters for the action (optional)

        Returns:
            The result from the API call

        Raises:
            Exception: If the API returns an error or connection fails
        """
        request_data = {
            "action": action,
            "version": self.version
        }

        if params is not None:
            request_data["params"] = params

        request_json = json.dumps(request_data).encode('utf-8')

        try:
            req = urllib.request.Request(self.url, request_json, {'Content-Type': 'application/json'})
            response = urllib.request.urlopen(req)
            response_data = json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            raise Exception(f"Failed to connect to AnkiConnect at {self.url}. "
                          f"Make sure Anki is running and AnkiConnect is installed. Error: {e}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")

        if response_data.get('error') is not None:
            raise Exception(f"AnkiConnect error: {response_data['error']}")

        return response_data.get('result')

    def check_connection(self) -> bool:
        """
        Check if AnkiConnect is accessible.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            version = self.invoke("version")
            return version is not None
        except Exception:
            return False

    # Note Operations

    def add_note(self, deck_name: str, model_name: str, fields: Dict[str, str],
                 tags: Optional[List[str]] = None) -> int:
        """
        Add a single note to Anki.

        Args:
            deck_name: Name of the deck
            model_name: Name of the note type/model
            fields: Dictionary of field names to values
            tags: Optional list of tags

        Returns:
            Note ID of the created note

        Example:
            note_id = client.add_note(
                deck_name="Default",
                model_name="Basic",
                fields={"Front": "Question", "Back": "Answer"},
                tags=["python", "programming"]
            )
        """
        note = {
            "deckName": deck_name,
            "modelName": model_name,
            "fields": fields,
            "tags": tags or []
        }

        return self.invoke("addNote", {"note": note})

    def add_notes(self, notes: List[Dict[str, Any]]) -> List[Optional[int]]:
        """
        Add multiple notes to Anki.

        Args:
            notes: List of note dictionaries, each containing:
                - deckName: Name of the deck
                - modelName: Name of the note type
                - fields: Dictionary of field names to values
                - tags: Optional list of tags

        Returns:
            List of note IDs (None for failed notes)

        Example:
            note_ids = client.add_notes([
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Q1", "Back": "A1"},
                    "tags": ["tag1"]
                },
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Q2", "Back": "A2"},
                    "tags": ["tag2"]
                }
            ])
        """
        return self.invoke("addNotes", {"notes": notes})

    def find_notes(self, query: str) -> List[int]:
        """
        Search for notes matching a query.

        Args:
            query: Anki search query (e.g., "deck:Default tag:python")

        Returns:
            List of note IDs matching the query

        Example:
            note_ids = client.find_notes("deck:Default tag:python")
        """
        return self.invoke("findNotes", {"query": query})

    def notes_info(self, note_ids: List[int],
                   fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get detailed information about notes.

        Args:
            note_ids: List of note IDs
            fields: Optional list of field names to include (returns all fields if None)

        Returns:
            List of note information dictionaries

        Example:
            # Get all fields
            notes = client.notes_info([1234567890, 9876543210])

            # Get only specific fields
            notes = client.notes_info([1234567890], fields=["Front", "Back"])
        """
        result = self.invoke("notesInfo", {"notes": note_ids})

        if fields is not None and result:
            for note in result:
                if "fields" in note:
                    note["fields"] = {
                        k: v for k, v in note["fields"].items()
                        if k in fields
                    }

        return result

    def update_note_fields(self, note_id: int, fields: Dict[str, str]) -> None:
        """
        Update fields of an existing note.

        Args:
            note_id: ID of the note to update
            fields: Dictionary of field names to new values

        Example:
            client.update_note_fields(1234567890, {"Front": "Updated question"})
        """
        self.invoke("updateNoteFields", {"note": {"id": note_id, "fields": fields}})

    def delete_notes(self, note_ids: List[int]) -> None:
        """
        Delete notes.

        Args:
            note_ids: List of note IDs to delete

        Example:
            client.delete_notes([1234567890, 9876543210])
        """
        self.invoke("deleteNotes", {"notes": note_ids})

    # Card Operations

    def find_cards(self, query: str) -> List[int]:
        """
        Search for cards matching a query.

        Args:
            query: Anki search query

        Returns:
            List of card IDs matching the query

        Example:
            card_ids = client.find_cards("deck:Default is:due")
        """
        return self.invoke("findCards", {"query": query})

    def cards_info(self, card_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get detailed information about cards.

        Args:
            card_ids: List of card IDs

        Returns:
            List of card information dictionaries

        Example:
            cards = client.cards_info([1234567890])
        """
        return self.invoke("cardsInfo", {"cards": card_ids})

    def suspend_cards(self, card_ids: List[int]) -> bool:
        """
        Suspend cards.

        Args:
            card_ids: List of card IDs to suspend

        Returns:
            True if successful

        Example:
            client.suspend_cards([1234567890, 9876543210])
        """
        return self.invoke("suspend", {"cards": card_ids})

    def unsuspend_cards(self, card_ids: List[int]) -> bool:
        """
        Unsuspend cards.

        Args:
            card_ids: List of card IDs to unsuspend

        Returns:
            True if successful

        Example:
            client.unsuspend_cards([1234567890, 9876543210])
        """
        return self.invoke("unsuspend", {"cards": card_ids})

    # Deck Operations

    def deck_names(self) -> List[str]:
        """
        Get list of all deck names.

        Returns:
            List of deck names

        Example:
            decks = client.deck_names()
        """
        return self.invoke("deckNames")

    def deck_names_and_ids(self) -> Dict[str, int]:
        """
        Get mapping of deck names to IDs.

        Returns:
            Dictionary mapping deck names to deck IDs

        Example:
            decks = client.deck_names_and_ids()
        """
        return self.invoke("deckNamesAndIds")

    def create_deck(self, deck_name: str) -> int:
        """
        Create a new deck.

        Args:
            deck_name: Name of the deck to create (supports hierarchy with ::)

        Returns:
            Deck ID

        Example:
            deck_id = client.create_deck("My Deck::Subdeck")
        """
        return self.invoke("createDeck", {"deck": deck_name})

    def delete_decks(self, deck_names: List[str], cards_too: bool = True) -> None:
        """
        Delete decks.

        Args:
            deck_names: List of deck names to delete
            cards_too: Whether to delete cards in the deck (must be True)

        Example:
            client.delete_decks(["Old Deck"], cards_too=True)
        """
        self.invoke("deleteDecks", {"decks": deck_names, "cardsToo": cards_too})

    def get_deck_stats(self, deck_names: List[str]) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for decks.

        Args:
            deck_names: List of deck names

        Returns:
            Dictionary mapping deck names to statistics

        Example:
            stats = client.get_deck_stats(["Default", "My Deck"])
        """
        return self.invoke("getDeckStats", {"decks": deck_names})

    # Model Operations

    def model_names(self) -> List[str]:
        """
        Get list of all note type names.

        Returns:
            List of model/note type names

        Example:
            models = client.model_names()
        """
        return self.invoke("modelNames")

    def model_names_and_ids(self) -> Dict[str, int]:
        """
        Get mapping of model names to IDs.

        Returns:
            Dictionary mapping model names to model IDs

        Example:
            models = client.model_names_and_ids()
        """
        return self.invoke("modelNamesAndIds")

    def model_field_names(self, model_name: str) -> List[str]:
        """
        Get field names for a model.

        Args:
            model_name: Name of the model/note type

        Returns:
            List of field names

        Example:
            fields = client.model_field_names("Basic")
        """
        return self.invoke("modelFieldNames", {"modelName": model_name})

    # Miscellaneous

    def sync(self) -> None:
        """
        Synchronize collection with AnkiWeb.

        Example:
            client.sync()
        """
        self.invoke("sync")

    def get_tags(self) -> List[str]:
        """
        Get list of all tags.

        Returns:
            List of tags

        Example:
            tags = client.get_tags()
        """
        return self.invoke("getTags")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description='AnkiConnect API Client - Interact with Anki',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--url',
        default='http://localhost:8765',
        help='AnkiConnect endpoint URL (default: http://localhost:8765)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    subparsers.required = True

    # add-note command
    add_note_parser = subparsers.add_parser('add-note', help='Add a single note')
    add_note_parser.add_argument('--deck', required=True, help='Deck name')
    add_note_parser.add_argument('--model', required=True, help='Model/note type name')
    add_note_parser.add_argument('--fields', required=True, help='Fields as JSON (e.g., \'{"Front":"Q","Back":"A"}\')')
    add_note_parser.add_argument('--tags', help='Tags as comma-separated list')

    # add-notes command
    add_notes_parser = subparsers.add_parser('add-notes', help='Add multiple notes')
    add_notes_parser.add_argument('--json-file', required=True, help='JSON file containing notes array')

    # find-notes command
    find_notes_parser = subparsers.add_parser('find-notes', help='Search for notes')
    find_notes_parser.add_argument('--query', required=True, help='Anki search query')

    # notes-info command
    notes_info_parser = subparsers.add_parser('notes-info', help='Get note information')
    notes_info_parser.add_argument('--note-ids', required=True, nargs='+', type=int, help='Note IDs')
    notes_info_parser.add_argument('--fields', help='Field names to include (comma-separated)')

    # find-cards command
    find_cards_parser = subparsers.add_parser('find-cards', help='Search for cards')
    find_cards_parser.add_argument('--query', required=True, help='Anki search query')

    # deck-names command
    subparsers.add_parser('deck-names', help='List all deck names')

    # create-deck command
    create_deck_parser = subparsers.add_parser('create-deck', help='Create a new deck')
    create_deck_parser.add_argument('--deck', required=True, help='Deck name')

    # model-names command
    subparsers.add_parser('model-names', help='List all note type names')

    # sync command
    subparsers.add_parser('sync', help='Sync with AnkiWeb')

    # invoke command (raw API call)
    invoke_parser = subparsers.add_parser('invoke', help='Raw API call')
    invoke_parser.add_argument('--action', required=True, help='API action name')
    invoke_parser.add_argument('--params', default='{}', help='Parameters as JSON')

    args = parser.parse_args()

    # Initialize client
    client = AnkiConnectClient(url=args.url)

    # Check connection
    if not client.check_connection():
        print("ERROR: Cannot connect to AnkiConnect.", file=sys.stderr)
        print("Make sure Anki is running and AnkiConnect plugin is installed.", file=sys.stderr)
        sys.exit(1)

    try:
        # Execute command
        if args.command == 'add-note':
            fields = parse_json_argument(args.fields, '--fields')
            tags = args.tags.split(',') if args.tags else None
            note_id = client.add_note(args.deck, args.model, fields, tags)
            print(f"Note created with ID: {note_id}")

        elif args.command == 'add-notes':
            with open(args.json_file, 'r') as f:
                notes = json.load(f)

            # Validate that notes is a list
            if not isinstance(notes, list):
                raise ValueError(
                    f"JSON file must contain an array of notes, not {type(notes).__name__}\n"
                    f"Expected format: [{...}, {...}]"
                )

            note_ids = client.add_notes(notes)
            print(f"Created {len([n for n in note_ids if n is not None])} notes")
            print(f"Note IDs: {note_ids}")

        elif args.command == 'find-notes':
            note_ids = client.find_notes(args.query)
            print(f"Found {len(note_ids)} notes")
            print(json.dumps(note_ids, indent=2))

        elif args.command == 'notes-info':
            fields_filter = args.fields.split(',') if args.fields else None
            notes = client.notes_info(args.note_ids, fields=fields_filter)
            print(json.dumps(notes, indent=2))

        elif args.command == 'find-cards':
            card_ids = client.find_cards(args.query)
            print(f"Found {len(card_ids)} cards")
            print(json.dumps(card_ids, indent=2))

        elif args.command == 'deck-names':
            decks = client.deck_names()
            print("Available decks:")
            for deck in sorted(decks):
                print(f"  - {deck}")

        elif args.command == 'create-deck':
            deck_id = client.create_deck(args.deck)
            print(f"Deck created with ID: {deck_id}")

        elif args.command == 'model-names':
            models = client.model_names()
            print("Available note types:")
            for model in sorted(models):
                print(f"  - {model}")

        elif args.command == 'sync':
            print("Syncing with AnkiWeb...")
            client.sync()
            print("Sync completed successfully")

        elif args.command == 'invoke':
            params = parse_json_argument(args.params, '--params')
            result = client.invoke(args.action, params)
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
