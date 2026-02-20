#!/usr/bin/env python3
"""
Podcast Metrics Calculator

Calculate word counts, expected duration, and actual WAV file duration
for podcast scripts and audio files.
"""

import argparse
import os
import re
import sys
from pathlib import Path


# Constants
DEFAULT_TEMPO_WPM = 175  # Default speech tempo in words per minute
WAV_DIVISOR = 44100      # Sample rate (22050 Hz) × bytes per sample (2) × channels (1)
SPEAKER_PATTERN = re.compile(r'^Speaker \d+:\s*')


def count_words_in_script(script_file: str) -> int:
    """
    Count spoken words in a podcast script file.
    Excludes "Speaker N:" prefixes from the count.

    Args:
        script_file: Path to the script file

    Returns:
        Total number of spoken words

    Raises:
        FileNotFoundError: If script file doesn't exist
        IOError: If file cannot be read
    """
    if not os.path.exists(script_file):
        raise FileNotFoundError(f"Script file not found: {script_file}")

    total_words = 0

    try:
        with open(script_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Only process lines that start with "Speaker N:"
                if SPEAKER_PATTERN.match(line):
                    # Remove the speaker prefix
                    dialogue = SPEAKER_PATTERN.sub('', line)
                    # Count words in the dialogue
                    words = dialogue.split()
                    total_words += len(words)
    except IOError as e:
        raise IOError(f"Error reading script file: {e}")

    return total_words


def calculate_expected_duration(word_count: int, tempo_wpm: int = DEFAULT_TEMPO_WPM) -> float:
    """
    Calculate expected podcast duration from word count and speaking tempo.

    Args:
        word_count: Total number of words in the script
        tempo_wpm: Speaking tempo in words per minute (default: 175)

    Returns:
        Expected duration in seconds
    """
    if word_count <= 0:
        return 0.0
    if tempo_wpm <= 0:
        raise ValueError("Tempo must be greater than 0")

    # Duration in seconds = (words / words_per_minute) * 60
    duration_seconds = (word_count / tempo_wpm) * 60
    return round(duration_seconds, 2)


def calculate_actual_duration(wav_file: str) -> float:
    """
    Calculate actual duration of a WAV file from its size.

    This assumes the WAV file has the following specifications:
    - Format: PCM 16-bit (signed, little-endian)
    - Sample rate: 22,050 Hz (22.05 kHz)
    - Channels: 1 (mono)
    - Bytes per sample: 2

    Formula: duration_seconds = file_size / (sample_rate × bytes_per_sample × channels)
              = file_size / 44,100

    Args:
        wav_file: Path to the WAV audio file

    Returns:
        Duration in seconds

    Raises:
        FileNotFoundError: If WAV file doesn't exist
    """
    if not os.path.exists(wav_file):
        raise FileNotFoundError(f"WAV file not found: {wav_file}")

    file_size = os.path.getsize(wav_file)
    duration_seconds = file_size / WAV_DIVISOR
    return round(duration_seconds, 2)


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to MM:SS format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string in MM:SS format
    """
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}:{remaining_seconds:02d}"


def main():
    parser = argparse.ArgumentParser(
        description='Calculate podcast metrics: word count, duration, and tempo analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Count words in a script
  %(prog)s count-words --file script.txt

  # Calculate expected duration (5 minute podcast at 175 WPM)
  %(prog)s expected-duration --minutes 5
  %(prog)s expected-duration --words 875 --tempo 175

  # Calculate actual WAV file duration
  %(prog)s actual-duration --wav-file output.wav

  # Verbose output with labels
  %(prog)s count-words --file script.txt --verbose
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # count-words subcommand
    parser_count = subparsers.add_parser(
        'count-words',
        help='Count spoken words in a script file (excludes "Speaker N:" prefixes)'
    )
    parser_count.add_argument(
        '--file',
        required=True,
        help='Path to the podcast script file'
    )
    parser_count.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Output with labels'
    )

    # expected-duration subcommand
    parser_expected = subparsers.add_parser(
        'expected-duration',
        help='Calculate expected duration from word count and tempo'
    )
    group = parser_expected.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--words',
        type=int,
        help='Total word count'
    )
    group.add_argument(
        '--minutes',
        type=float,
        help='Target duration in minutes (calculates word count using tempo)'
    )
    parser_expected.add_argument(
        '--tempo',
        type=int,
        default=DEFAULT_TEMPO_WPM,
        help=f'Speaking tempo in words per minute (default: {DEFAULT_TEMPO_WPM})'
    )
    parser_expected.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Output with labels'
    )

    # actual-duration subcommand
    parser_actual = subparsers.add_parser(
        'actual-duration',
        help='Calculate actual duration from WAV file size'
    )
    parser_actual.add_argument(
        '--wav-file',
        required=True,
        help='Path to the WAV audio file'
    )
    parser_actual.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Output with labels'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == 'count-words':
            word_count = count_words_in_script(args.file)
            if args.verbose:
                print(f"Word count: {word_count}")
            else:
                print(word_count)

        elif args.command == 'expected-duration':
            if args.minutes:
                # Calculate word count from target minutes
                word_count = int(args.minutes * args.tempo)
                duration_seconds = args.minutes * 60
            else:
                # Calculate duration from word count
                word_count = args.words
                duration_seconds = calculate_expected_duration(word_count, args.tempo)

            if args.verbose:
                duration_str = format_duration(duration_seconds)
                print(f"Word count: {word_count}")
                print(f"Tempo: {args.tempo} WPM")
                print(f"Expected duration: {duration_seconds} seconds ({duration_str})")
            else:
                print(duration_seconds)

        elif args.command == 'actual-duration':
            duration_seconds = calculate_actual_duration(args.wav_file)
            if args.verbose:
                duration_str = format_duration(duration_seconds)
                file_size = os.path.getsize(args.wav_file)
                print(f"File: {args.wav_file}")
                print(f"File size: {file_size:,} bytes")
                print(f"Duration: {duration_seconds} seconds ({duration_str})")
            else:
                print(duration_seconds)

    except (FileNotFoundError, IOError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
