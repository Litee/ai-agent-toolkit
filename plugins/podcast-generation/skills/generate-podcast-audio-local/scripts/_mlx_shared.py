#!/usr/bin/env python3
"""
Shared utilities for MLX-based podcast generation scripts.

This module provides common helpers (logging, voice directory defaults,
slugification, ffprobe checks) used by scripts in this skill.
"""


class VoiceEncodingError(FileNotFoundError):
    """Custom exception for voice file encoding errors with detailed instructions."""
    pass

import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Pattern that matches a speaker header line, e.g. "Speaker 1:" or "Speaker 12:"
SPEAKER_HEADER_RE = re.compile(r"^Speaker\s+(\d+):\s*")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_progress(message: str, level: str = "INFO") -> None:
    """Print timestamped progress message to stderr."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {message}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Slugification
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Convert text to a lowercase slug suitable for filenames.

    Replaces spaces and special characters with hyphens, collapses multiple
    hyphens, and strips leading/trailing hyphens.

    Examples:
        "My Podcast Episode" -> "my-podcast-episode"
        "Hello, World!"      -> "hello-world"
        "---test---"         -> "test"
    """
    import re
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s_-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


# ---------------------------------------------------------------------------
# FFprobe detection
# ---------------------------------------------------------------------------

def check_ffprobe() -> bool:
    """Return True if ffprobe is available on PATH."""
    return shutil.which("ffprobe") is not None


def prompt_install_ffprobe() -> bool:
    """Ask the user whether to install ffmpeg via brew.

    Returns True if ffprobe is now available, False otherwise.
    """
    print("", file=sys.stderr)
    log_progress("ffprobe is required for tempo analysis. Install it with:")
    print("  brew install ffmpeg", file=sys.stderr)
    print("", file=sys.stderr)
    answer = input("Would you like to install it now? (y/n): ").strip().lower()
    if answer not in ("y", "yes"):
        log_progress("Skipping ffprobe installation. Tempo analysis will use file-size fallback.", "WARN")
        return False

    log_progress("Installing ffmpeg via brew…")
    result = subprocess.run(["brew", "install", "ffmpeg"], capture_output=True, text=True)
    if result.returncode != 0:
        log_progress(f"brew install failed: {result.stderr.strip()}", "ERROR")
        log_progress("Continuing without ffprobe. Tempo analysis will use file-size fallback.", "WARN")
        return False

    if check_ffprobe():
        log_progress("ffprobe installed successfully.")
        return True
    else:
        log_progress("ffprobe still not found after installation.", "WARN")
        return False


# ---------------------------------------------------------------------------
# Voice directory defaults
# ---------------------------------------------------------------------------

LOCAL_TTS_VOICES_DIR_ENV = "LOCAL_TTS_VOICES_DIR"


def get_default_voices_dir(skill_dir: Path | None = None) -> Path:
    """Return the default voices directory path.

    Defaults to ``<skill_dir>/assets/voices/`` where *skill_dir* is the
    root of the MLX skill (``generate-podcast-audio-local``).
    """
    if skill_dir is None:
        skill_dir = Path(__file__).resolve().parent.parent.parent
    return skill_dir / "assets" / "voices"


def resolve_voices_dir(custom_dir: Path | None, skill_dir: Path | None = None) -> Path:
    """Resolve the voices directory with a clear priority order.

    Priority:
      1. ``custom_dir`` if explicitly provided via ``--voices-dir``
      2. ``LOCAL_TTS_VOICES_DIR`` environment variable
      3. ``<skill_dir>/assets/voices/`` (fallback)

    Raises ``FileNotFoundError`` if none of the locations contain .wav files.
    """
    # 1. Explicit custom directory
    if custom_dir and custom_dir.is_dir():
        wav_files = list(custom_dir.glob("*.wav"))
        if wav_files:
            log_progress(f"Using custom voices directory: {custom_dir}")
            return custom_dir
        # If custom directory is explicitly provided but has no .wav files,
        # raise an error with helpful voice encoding instructions
        raise VoiceEncodingError(
            f"No .wav files found in voices directory: {custom_dir}\n\n"
            "Voice File Naming Convention:\n"
            "  - Recommended format: <speaker_num>_<name>.wav (e.g., '1_Alice.wav', '2_Frank.wav')\n"
            "  - Speaker number should match the 'Speaker N:' in your script\n"
            "  - Matching is case-insensitive and uses substring matching\n\n"
            "To create custom voices:\n"
            "  1. Record short (5-30 second) WAV samples of each speaker\n"
            "  2. Name them using the pattern above (e.g., '1_Alice.wav', '2_Frank.wav')\n"
            "  3. Place them in the voices directory passed to --voices-dir"
        )

    # 2. LOCAL_TTS_VOICES_DIR environment variable
    env_dir = os.environ.get(LOCAL_TTS_VOICES_DIR_ENV)
    if env_dir:
        env_path = Path(env_dir)
        if env_path.is_dir():
            wav_files = list(env_path.glob("*.wav"))
            if wav_files:
                log_progress(f"Using voices directory from {LOCAL_TTS_VOICES_DIR_ENV}: {env_path}")
                return env_path
            log_progress(f"{LOCAL_TTS_VOICES_DIR_ENV} directory has no .wav files: {env_path}", "WARN")
        else:
            log_progress(f"{LOCAL_TTS_VOICES_DIR_ENV} is not a directory: {env_path}", "WARN")



    # 3. Skill's assets/voices/
    fallback = get_default_voices_dir(skill_dir)
    if fallback.is_dir():
        wav_files = list(fallback.glob("*.wav"))
        if wav_files:
            log_progress(f"Using fallback voices directory: {fallback}")
            return fallback

    # Nothing found — fail with a helpful message
    raise FileNotFoundError(
        f"No voice files found in any location:\n"
        f"  1. Custom directory: {custom_dir}\n"
        f"  2. {LOCAL_TTS_VOICES_DIR_ENV}: {env_dir}\n"
        f"  3. Skill assets: {fallback}\n\n"
        f"Please provide voices via --voices-dir, set {LOCAL_TTS_VOICES_DIR_ENV}, or place .wav files in one of the above locations."
    )


# ---------------------------------------------------------------------------
# Voice matching helpers
# ---------------------------------------------------------------------------

def find_voice_by_name(name: str, voices_dir: Path) -> Path:
    """Find a WAV voice file by matching *name* as a case-insensitive
    substring against the filename stem.

    Voice file naming convention:
      - Use pattern: {speaker_num}_{name}.wav (e.g., "1_Alice.wav", "2_Frank.wav")
      - The speaker number should match the "Speaker N:" in the script
      - Matching is case-insensitive and uses substring matching

    Raises ``FileNotFoundError`` if no match is found.
    """
    name_lower = name.lower()
    wav_files = sorted(voices_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(
            f"No .wav files found in voices directory: {voices_dir}"
        )

    # Try exact stem match first (best precision)
    for wf in wav_files:
        if wf.stem.lower() == name_lower:
            return wf

    # Try substring match
    matches = [wf for wf in wav_files if name_lower in wf.stem.lower()]
    if matches:
        return matches[0]

    # Last resort: match against the speaker name as a simpler substring
    for wf in wav_files:
        if name_lower in wf.stem.lower():
            return wf

    available = ", ".join(sorted(f.name for f in wav_files))
    raise FileNotFoundError(
        f"Voice file not found for speaker '{name}'.\n\n"
        "Voice File Naming Convention:\n"
        "  - Recommended format: <speaker_num>_<name>.wav (e.g., '1_Alice.wav', '2_Frank.wav')\n"
        "  - Speaker number should match the 'Speaker N:' in the script\n"
        "  - Matching is case-insensitive and uses substring matching\n\n"
        "  Available files in directory:\n"
        f"    {available}\n\n"
        "To create custom voices:\n"
        "  1. Record short (5-30 second) WAV samples of each speaker\n"
        "  2. Name them using the pattern above (e.g., '1_Alice.wav', '2_Frank.wav')\n"
        "  3. Place them in the voices directory passed to --voices-dir"
    )


def verify_voices(
    speaker_names: list[str],
    voices_dir: Path,
) -> list[Path]:
    """Verify that a voice file exists for each speaker.

    Returns a list of resolved voice paths in the order given by
    *speaker_names*.
    """
    wav_files = list(voices_dir.glob("*.wav"))
    if not wav_files:
        raise VoiceEncodingError(
            f"No .wav files found in voices directory: {voices_dir}\n\n"
            "Voice File Naming Convention:\n"
            "  - Recommended format: <speaker_num>_<name>.wav (e.g., '1_Alice.wav', '2_Frank.wav')\n"
            "  - Speaker number should match the 'Speaker N:' in your script\n"
            "  - Matching is case-insensitive and uses substring matching\n\n"
            "To create custom voices:\n"
            "  1. Record short (5-30 second) WAV samples of each speaker\n"
            "  2. Name them using the pattern above (e.g., '1_Alice.wav', '2_Frank.wav')\n"
            "  3. Place them in the voices directory passed to --voices-dir"
        )

    log_progress(f"Found {len(wav_files)} voice file(s) in {voices_dir}/")
    for wf in sorted(wav_files):
        log_progress(f"  - {wf.name}")

    ref_audios: list[Path] = []
    for name in speaker_names:
        voice_path = find_voice_by_name(name, voices_dir)
        ref_audios.append(voice_path)
        log_progress(f"  {name} -> {voice_path.name}")

    return ref_audios



