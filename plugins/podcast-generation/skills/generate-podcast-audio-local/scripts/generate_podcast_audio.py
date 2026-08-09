#!/usr/bin/env python3
"""
Podcast audio generation script using VibeVoice MLX (local GPU).

Generates a multi-speaker podcast audio file from a formatted script
using the local MLX-powered VibeVoice model — no cloud infrastructure required.

Usage:
  python3 generate_podcast_audio.py \\
    --script-path path/to/podcast_script.txt \\
    --speaker-names Samuel Bowen

  # With custom voices from a directory (voice names derived from WAV filenames)
  python3 generate_podcast_audio.py \\
    --script-path script.txt \\
    --speaker-names Helen John \\
    --voices-dir ~/my-voices \\
    --quantize 4
"""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from _mlx_shared import (
    log_progress,
    check_ffprobe,
    check_ffmpeg,
    measure_loudness,
    normalize_audio_loudness,
    prompt_install_ffprobe,
    resolve_voices_dir,
    verify_voices,
    slugify,
    VoiceEncodingError,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# VibeVoice MLX repository
VIBEVOICE_GIT_URL = "https://github.com/Litee/vibevoice-mlx.git"

# Default parameters
DEFAULT_MODEL = "gafiatulin/vibevoice-7b-mlx"
DEFAULT_QUANTIZE = "8"
DEFAULT_SEED = "42"
DEFAULT_MAX_SPEECH_TOKENS = "1000000"

# Minimum Python version
PYTHON_MIN_VERSION = (3, 10)

# Formatting
SEPARATOR_WIDTH = 80

# Pattern that matches a speaker header line, e.g. "Speaker 1:" or "Speaker 12:"
SPEAKER_HEADER_RE = re.compile(r"^Speaker\s+(\d+):\s*")


# ---------------------------------------------------------------------------
# Environment checks
# ---------------------------------------------------------------------------

def check_tool(name: str) -> bool:
    """Return True if *name* is available on PATH."""
    return shutil.which(name) is not None


def verify_python() -> None:
    """Ensure we are running Python 3.10+."""
    if sys.version_info < (3, 10):
        log_progress(f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}", "ERROR")
        sys.exit(1)
    log_progress(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} OK")


def verify_uv() -> None:
    """Ensure uv is available."""
    if not check_tool("uv"):
        log_progress(
            "uv is required but not found on PATH. "
            "Install it: https://docs.astral.sh/uv/getting-started/installation/",
            "ERROR",
        )
        sys.exit(1)
    log_progress("uv OK")


def verify_git() -> None:
    """Ensure git is available."""
    if not check_tool("git"):
        log_progress(
            "git is required but not found on PATH. "
            "Please install git and retry.",
            "ERROR",
        )
        sys.exit(1)
    log_progress("git OK")


# ---------------------------------------------------------------------------
# VibeVoice MLX clone / temp directory
# ---------------------------------------------------------------------------

# Fixed path for the VibeVoice MLX repository cache
VIBEVOICE_CACHE_DIR = Path(tempfile.gettempdir()) / "vibevoice-mlx"


def ensure_vibevoice_mlx() -> Path:
    """Ensure the VibeVoice MLX repo is cloned and dependencies installed.

    On first run: full clone + uv sync.
    On subsequent runs: git pull --rebase + uv sync (fast on cached deps).

    Returns the path to the cloned repo.  Raises on failure.
    """
    log_progress("Ensuring VibeVoice MLX repository…")
    needs_clone = not VIBEVOICE_CACHE_DIR.exists()

    if needs_clone:
        log_progress("First run — cloning repository…")
        result = subprocess.run(
            ["git", "clone", VIBEVOICE_GIT_URL, str(VIBEVOICE_CACHE_DIR)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            shutil.rmtree(VIBEVOICE_CACHE_DIR, ignore_errors=True)
            raise RuntimeError(
                f"git clone failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )
        log_progress("Repository cloned successfully")
    else:
        log_progress("Repository cached — updating…")
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=str(VIBEVOICE_CACHE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log_progress(f"Pull failed (may be up-to-date): {result.stderr.strip()[:200]}", "WARN")
        log_progress("Repository updated")

    # Always sync dependencies (fast on cached deps, avoids staleness)
    log_progress("Syncing dependencies with uv…")
    result = subprocess.run(
        ["uv", "sync"],
        cwd=str(VIBEVOICE_CACHE_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"uv sync failed (exit {result.returncode}):\n{result.stderr.strip()}"
        )
    log_progress("Dependencies synced")
    log_progress(f"VibeVoice MLX directory: {VIBEVOICE_CACHE_DIR}")
    return VIBEVOICE_CACHE_DIR


# ---------------------------------------------------------------------------
# Script validation
# ---------------------------------------------------------------------------

def validate_script(script_path: Path) -> None:
    """Validate that the script file exists and uses proper 'Speaker N:' format."""
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    lines = script_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Script file is empty")

    found_headers = set()
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        m = SPEAKER_HEADER_RE.match(stripped)
        if m:
            found_headers.add(int(m.group(1)))
        else:
            raise ValueError(
                f"Line {line_num}: Expected 'Speaker N:' format, got: {stripped[:60]}"
            )

    if not found_headers:
        raise ValueError("Script contains no 'Speaker N:' header lines")

    log_progress(f"Script format validated — {len(found_headers)} speaker(s) found")


def count_script_words(script_path: Path) -> int:
    """Count words in the script, excluding 'Speaker N:' prefixes."""
    text = script_path.read_text(encoding="utf-8")
    total = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        content = SPEAKER_HEADER_RE.sub("", stripped)
        total += len(content.split())
    return total


def count_script_speakers(script_path: Path) -> int:
    """Return the number of distinct speaker numbers in the script."""
    headers = set()
    for line in script_path.read_text(encoding="utf-8").splitlines():
        m = SPEAKER_HEADER_RE.match(line.strip())
        if m:
            headers.add(int(m.group(1)))
    return len(headers)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(script_path: Path) -> str:
    """Read the script and return text with 'Speaker N:' prefixes preserved.

    The MLX model uses these prefixes to assign each segment to the correct
    voice. Do NOT strip them.
    """
    text = script_path.read_text(encoding="utf-8")
    # Normalize line endings: ensure each speaker line is on its own line
    # Replace any Windows-style line endings and normalize spacing
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


# ---------------------------------------------------------------------------
# MLX command building
# ---------------------------------------------------------------------------

def build_mlx_command(
    ref_audios: list[Path],
    text: str,
    output_path: Path,
    model: str,
    quantize: str,
    seed: int,
) -> list[str]:
    """Build the ``uv run vibevoice-mlx`` command as a list of arguments.

    Note: --ref-audio uses nargs="+" in the CLI, so ALL voice files must be
    passed as arguments to a SINGLE --ref-audio flag.
    """
    cmd = [
        "uv", "run", "vibevoice-mlx",
        "--model", model,
        "--ref-audio",
    ]
    for audio in ref_audios:
        cmd.append(str(audio))

    cmd.extend([
        "--text", text,
        "--output", str(output_path),
        "--quantize", quantize,
        "--quantize-diffusion",
        "--seed", str(seed),
        "--max-speech-tokens", DEFAULT_MAX_SPEECH_TOKENS,
    ])
    return cmd


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate podcast audio using VibeVoice MLX (local GPU).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage (uses default model Litee/vibevoice-1.5b-mlx, demo voices)
  %(prog)s --script-path podcast.txt --speaker-names Samuel Bowen

  # Custom voices from a directory (voice names derived from WAV filenames)
  %(prog)s --script-path podcast.txt --speaker-names Helen John \\
           --voices-dir ~/my-voices --quantize 4
        """,
    )
    parser.add_argument(
        "--script-path", required=True,
        help="Path to the podcast script file",
    )
    parser.add_argument(
        "--speaker-names", nargs="+", required=True,
        help="Voice names in order (e.g., Samuel Bowen)",
    )
    parser.add_argument(
        "--voices-dir", default=None,
        help="Directory with custom voice WAV files "
             "(default: bundled demo voices, then assets/voices/)",
    )
    parser.add_argument(
        "--target-lufs", type=float, default=-16.0,
        help="Target integrated loudness for the output audio in LUFS "
             "(default: -16, Apple Podcasts recommendation)",
    )
    parser.add_argument(
        "--target-tp", type=float, default=-1.0,
        help="Target true peak for the output audio in dBTP (default: -1)",
    )
    parser.add_argument(
        "--normalize-output", dest="normalize_output",
        action="store_true", default=True,
        help="Normalize the generated audio to --target-lufs/--target-tp "
             "(default: enabled; disable with --no-normalize-output)",
    )
    parser.add_argument(
        "--no-normalize-output", dest="normalize_output", action="store_false",
        help="Skip output loudness normalization",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"MLX model ID or path (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--quantize", default=DEFAULT_QUANTIZE,
        help=f"Quantization level: 4 or 8 (default: {DEFAULT_QUANTIZE})",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Directory for output WAV file (default: current working directory)",
    )

    args = parser.parse_args()

    log_progress("=" * SEPARATOR_WIDTH)
    log_progress("PODCAST AUDIO GENERATION (MLX)")
    log_progress("=" * SEPARATOR_WIDTH)

    temp_dir: Path | None = None
    try:
        # ------------------------------------------------------------------
        # Phase 0: Environment checks
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 0: Environment Checks ===")
        verify_python()
        verify_uv()
        verify_git()
        # ------------------------------------------------------------------
        # Phase 1: FFprobe check
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 1: FFprobe Check ===")
        if check_ffprobe():
            log_progress("ffprobe is available.")
        else:
            log_progress("ffprobe is NOT available.", "WARN")
            prompt_install_ffprobe()

        # Loudness normalization of the output needs the full ffmpeg binary,
        # not just ffprobe.
        ffmpeg_available = check_ffmpeg()
        if ffmpeg_available:
            log_progress("ffmpeg is available (output loudness normalization OK).")
        else:
            log_progress(
                "ffmpeg is NOT available — output loudness normalization will "
                "be SKIPPED. Install with: brew install ffmpeg",
                "WARN",
            )

        # ------------------------------------------------------------------
        # Phase 2: Clone vibevoice-mlx
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 2: Clone vibevoice-mlx ===")
        temp_dir = ensure_vibevoice_mlx()

        # ------------------------------------------------------------------
        # Phase 3: Script validation
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 3: Script Validation ===")
        script_path = Path(args.script_path).resolve()
        validate_script(script_path)

        word_count = count_script_words(script_path)
        log_progress(f"Word count: {word_count}")

        speaker_count = count_script_speakers(script_path)
        name_count = len(args.speaker_names)
        if speaker_count != name_count:
            raise ValueError(
                f"Speaker count mismatch: script has {speaker_count} distinct "
                f"speaker(s) but {name_count} name(s) provided via "
                f"--speaker-names ({', '.join(args.speaker_names)}). "
                f"Provide exactly one name per speaker in the script."
            )
        log_progress(f"Speaker count validated: {speaker_count} speaker(s)")

        # ------------------------------------------------------------------
        # Phase 4: Voice verification
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 4: Voice Verification ===")
        skill_dir = Path(__file__).resolve().parent.parent
        voices_dir = resolve_voices_dir(
            custom_dir=Path(args.voices_dir) if args.voices_dir else None,
            skill_dir=skill_dir,
        )
        ref_audios = verify_voices(args.speaker_names, voices_dir)

        # ------------------------------------------------------------------
        # Phase 5: Text extraction
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 5: Text Extraction ===")
        full_text = extract_text(script_path)
        log_progress(f"Extracted {len(full_text)} characters (with speaker prefixes for MLX)")

        # ------------------------------------------------------------------
        # Phase 6: Audio Generation
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=== Phase 6: Audio Generation ===")

        # Output naming: slugified script name + timestamp
        # Use custom output directory if specified, otherwise current working directory
        output_dir = Path(args.output_dir) if args.output_dir else Path.cwd()
        if not output_dir.is_dir():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        slug = slugify(script_path.stem)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        output_path = output_dir / f"{slug}_{timestamp}.wav"

        cmd = build_mlx_command(
            ref_audios=ref_audios,
            text=full_text,
            output_path=output_path,
            model=args.model,
            quantize=args.quantize,
            seed=args.seed,
        )

        log_progress(f"Output: {output_path.name}")
        log_progress(f"Command: {' '.join(shlex.quote(a) for a in cmd)}")
        log_progress(f"VibeVoice dir: {temp_dir}")
        log_progress(f"Model: {args.model}")
        log_progress(f"Quantize: {args.quantize}")
        log_progress(f"Seed: {args.seed}")
        log_progress("Running VibeVoice MLX…")
        log_progress("-" * 60)

        env = {**dict(os.environ), "PYTHONUNBUFFERED": "1"}
        result = subprocess.run(
            cmd,
            cwd=str(temp_dir),
            env=env,
        )

        if result.returncode != 0:
            log_progress(
                f"\nError: vibevoice-mlx exited with code {result.returncode}",
                "ERROR",
            )
            sys.exit(1)

        if not output_path.exists():
            log_progress(f"\nError: Output file was not created: {output_path}", "ERROR")
            sys.exit(1)

        file_size = output_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        log_progress(f"Generation complete: {file_size_mb:.1f} MB")

        # ------------------------------------------------------------------
        # Phase 7: Output loudness normalization
        # ------------------------------------------------------------------
        if args.normalize_output and ffmpeg_available:
            log_progress("")
            log_progress("=== Phase 7: Output Loudness Normalization ===")
            before = measure_loudness(
                output_path, args.target_lufs, args.target_tp
            )
            log_progress(
                f"Before: {before['input_i']} LUFS / {before['input_tp']} dBTP "
                f"(target {args.target_lufs:g} LUFS / {args.target_tp:g} dBTP)"
            )
            tmp_out = output_path.parent / f"{output_path.stem}.loudnorm.tmp"
            try:
                after_i, after_tp = normalize_audio_loudness(
                    output_path,
                    tmp_out,
                    target_i=args.target_lufs,
                    target_tp=args.target_tp,
                )
            except Exception as e:
                log_progress(
                    f"Output normalization failed ({e}) — keeping the original "
                    f"un-normalized file.",
                    "WARN",
                )
            else:
                os.replace(tmp_out, output_path)
                log_progress(
                    f"After:  {after_i:.2f} LUFS / {after_tp:.2f} dBTP "
                    f"(deviation {after_i - args.target_lufs:+.2f} LU)"
                )
                if abs(after_i - args.target_lufs) > 1.0:
                    log_progress(
                        "Note: loudnorm applies only linear gain, so it will not "
                        "boost past the true-peak ceiling; a result slightly under "
                        "target is expected and within the usual +/-1 LU QC "
                        "tolerance for delivery.",
                        "WARN",
                    )
        elif not args.normalize_output:
            log_progress("Output loudness normalization skipped (--no-normalize-output)")
        elif not ffmpeg_available:
            log_progress("Output loudness normalization skipped (ffmpeg not available)")

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        log_progress("")
        log_progress("=" * SEPARATOR_WIDTH)
        log_progress("EXECUTION COMPLETED SUCCESSFULLY")
        log_progress("=" * SEPARATOR_WIDTH)
        if output_path.exists():
            final_size = output_path.stat().st_size
            final_size_mb = final_size / (1024 * 1024)
            log_progress(f"Output directory: {output_dir}")
            log_progress(f"Output WAV:      {output_path.name}")
            log_progress(f"File size:       {final_size_mb:.1f} MB")
        else:
            log_progress("Output file not found!", "ERROR")
        log_progress(f"Word count:  {word_count}")
        log_progress(f"Speakers:    {', '.join(args.speaker_names)}")
        log_progress(f"Model:       {args.model}")
        log_progress("=" * SEPARATOR_WIDTH)

    except VoiceEncodingError as e:
        # Voice encoding error — display with full instructions
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        log_progress("\n" + "=" * 80, "ERROR")
        log_progress("VOICE ENCODING ERROR", "ERROR")
        log_progress("=" * 80, "ERROR")
        log_progress(f"\n{str(e)}", "ERROR")
        log_progress("\n" + "=" * 80, "ERROR")
        sys.exit(1)
    except Exception as e:
        # Ensure cleanup even on unexpected errors
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        log_progress(f"\nERROR: {str(e)}", "ERROR")
        sys.exit(1)





if __name__ == "__main__":
    main()
