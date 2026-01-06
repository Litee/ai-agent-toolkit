#!/usr/bin/env python3
"""
Script to sync safe terminal commands from safe_terminal_commands.txt to Claude Code settings.
Reads commands from TXT file and updates ~/.claude/settings.json permissions.allow array.
"""

import sys
import json
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SyncReport:
    """Report of synchronization changes made to settings."""
    added: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        """Total number of changes (added)."""
        return len(self.added)

    def print_summary(self, verbose: bool = False) -> None:
        """Print a detailed summary of changes."""
        print(f"\n📊 Sync Report:")
        print(f"  ✅ Added: {len(self.added)} commands")
        print(f"  ⚪ Unchanged: {len(self.unchanged)} commands")

        if self.added:
            print(f"\n  📁 Added commands:")
            for command in sorted(self.added):
                print(f"    + {command}")

        if verbose and self.unchanged:
            print(f"\n  ⚪ Unchanged commands:")
            for command in sorted(self.unchanged):
                print(f"    = {command}")


def read_safe_commands_txt(txt_file: Path) -> set[str]:
    """Read safe commands from TXT file and return as a set.

    Supports Python-style comments:
    - Full-line comments: lines starting with #
    - Line-end comments: text after # on the same line as a command
    """
    commands = set()
    if not txt_file.exists():
        return commands

    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Strip whitespace first
                line = line.strip()

                # Skip empty lines and full-line comments
                if not line or line.startswith('#'):
                    continue

                # Handle line-end comments by taking only the part before '#'
                if '#' in line:
                    line = line.split('#', 1)[0].strip()

                # Add non-empty command to set
                if line:
                    commands.add(line)
    except OSError as e:
        print(f"❌ Error reading safe commands TXT file: {e}")
        sys.exit(1)

    return commands


def extract_bash_commands_from_settings(settings_data: dict) -> set[str]:
    """Extract bash commands from Claude settings JSON permissions.allow array."""
    bash_commands = set()

    permissions = settings_data.get('permissions', {})
    allow_list = permissions.get('allow', [])

    for permission in allow_list:
        if isinstance(permission, str) and permission.startswith('Bash(') and permission.endswith(':*)'):
            # Extract command from "Bash(command:*)" format
            command = permission[5:-3]  # Remove "Bash(" prefix and ":*)" suffix
            bash_commands.add(command)

    return bash_commands


def add_bash_command_to_settings(settings_data: dict, command: str) -> None:
    """Add a bash command to Claude settings JSON permissions.allow array."""
    if 'permissions' not in settings_data:
        settings_data['permissions'] = {}

    if 'allow' not in settings_data['permissions']:
        settings_data['permissions']['allow'] = []

    bash_permission = f"Bash({command}:*)"
    if bash_permission not in settings_data['permissions']['allow']:
        settings_data['permissions']['allow'].append(bash_permission)


def sort_permissions_allow(settings_data: dict) -> None:
    """Sort the permissions.allow array alphabetically."""
    if 'permissions' in settings_data and 'allow' in settings_data['permissions']:
        settings_data['permissions']['allow'].sort()


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sync safe terminal commands to Claude Code settings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Sync commands to settings
  %(prog)s --dry-run          # Preview changes without writing
  %(prog)s --verbose          # Show all commands including unchanged
  %(prog)s -n -v              # Dry-run with verbose output
        """
    )
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        help='Preview changes without modifying settings file'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show all commands including unchanged ones'
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_arguments()

    mode = "DRY RUN - " if args.dry_run else ""
    print(f"🚀 {mode}Syncing safe terminal commands to Claude Code settings...")

    # Get paths - script is in scripts/, txt file is in ../references/
    script_dir = Path(__file__).parent.absolute()
    skill_root = script_dir.parent
    txt_file = skill_root / 'references' / 'safe_terminal_commands.txt'
    settings_file = Path.home() / '.claude' / 'settings.json'

    print(f"\n📁 Configuration:")
    print(f"  Source: {txt_file}")
    print(f"  Target: {settings_file}")
    if args.dry_run:
        print(f"  Mode: DRY RUN (no changes will be made)")

    # Check if source file exists
    if not txt_file.exists():
        print(f"❌ ERROR: Safe commands file does not exist: {txt_file}")
        sys.exit(1)

    # Read commands from TXT file
    print(f"\n🔄 Reading commands from {txt_file.name}...")
    txt_commands = read_safe_commands_txt(txt_file)
    print(f"📊 Loaded {len(txt_commands)} commands from TXT file")

    # Load or create settings file
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            print(f"📊 Loaded existing settings from {settings_file}")
        except (OSError, json.JSONDecodeError) as e:
            print(f"❌ Error reading settings file: {e}")
            sys.exit(1)
    else:
        print(f"📝 Creating new settings file at {settings_file}")
        settings_data = {}
        settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Extract existing bash commands from settings
    json_commands = extract_bash_commands_from_settings(settings_data)
    print(f"📊 Found {len(json_commands)} bash commands in settings file")

    # Determine what needs to be synced
    commands_to_add = txt_commands - json_commands
    unchanged_commands = txt_commands & json_commands

    # Create sync report
    report = SyncReport(
        added=list(commands_to_add),
        unchanged=list(unchanged_commands)
    )

    # Add new commands to settings
    if commands_to_add:
        print(f"\n📝 Adding {len(commands_to_add)} new commands to settings...")
        for command in sorted(commands_to_add):
            add_bash_command_to_settings(settings_data, command)
            print(f"  ✅ Added: {command}")

    # Check if permissions array needs sorting even if no new commands were added
    current_allow = settings_data.get('permissions', {}).get('allow', [])
    sorted_allow = sorted(current_allow)
    needs_sorting = current_allow != sorted_allow

    if commands_to_add or needs_sorting:
        # Sort permissions.allow array alphabetically before saving
        sort_permissions_allow(settings_data)

        if args.dry_run:
            print(f"\n🔍 DRY RUN: Would update settings file (sorted alphabetically): {settings_file}")
            print(f"   No changes were actually made.")
        else:
            # Create backup before writing
            if settings_file.exists():
                backup_file = settings_file.with_suffix('.json.bak')
                try:
                    shutil.copy2(settings_file, backup_file)
                    print(f"\n💾 Created backup: {backup_file}")
                except OSError as e:
                    print(f"⚠️  Warning: Could not create backup: {e}")

            # Write updated settings file
            try:
                with open(settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings_data, f, indent=4, ensure_ascii=False)
                print(f"💾 Updated settings file (sorted alphabetically): {settings_file}")
            except OSError as e:
                print(f"❌ Error writing settings file: {e}")
                sys.exit(1)
    else:
        print(f"\n⚪ No changes needed - files are already in sync")

    # Print summary
    report.print_summary(verbose=args.verbose)

    if args.dry_run:
        print(f"\n✅ Dry run completed: {report.total_changes} changes would be made")
    else:
        print(f"\n✅ Safe commands sync completed: {report.total_changes} changes made")


if __name__ == "__main__":
    main()
