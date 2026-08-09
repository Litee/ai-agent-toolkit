#!/usr/bin/env python3
"""
Normalize voice reference clips for the podcast-generation skill.

Prepares new reference voices to the standard the skill expects: EBU R128
loudness (integrated -23 LUFS, true peak -1 dBTP) at 24 kHz, using a
two-pass ffmpeg loudnorm with linear gain (no compression, speech dynamics
untouched).

The bundled demo voices (Alice, Frank, Carter) are already normalized.
Run this only when adding new voice files — e.g. freshly downloaded or
recorded clips that vary in level (the demo Alice clip, for instance, is
~10 LU hotter than the male voices and clips at +0.1 dBTP).

Usage:
  python3 normalize_voices.py --voices-dir /path/to/voices
  python3 normalize_voices.py --voices-dir /path/to/voices --output-dir /path/to/normalized
  python3 normalize_voices.py   # normalize the skill's bundled assets/voices/ in place
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from _mlx_shared import (
    log_progress,
    check_ffmpeg,
    get_default_voices_dir,
    measure_loudness,
    normalize_audio_loudness,
)

# EBU R128 broadcast standard, matched to the bundled demo voices.
TARGET_LUFS = -23.0
TARGET_TP = -1.0
TARGET_LRA = 7.0
TARGET_SR = 24000  # VibeVoice MLX model's native sample rate


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize voice reference WAV files to EBU R128 loudness "
            "(-23 LUFS / -1 dBTP) at 24 kHz."
        ),
        epilog=(
            "Examples:\n"
            "  %(prog)s --voices-dir /path/to/voices\n"
            "  %(prog)s --voices-dir /path/to/voices --output-dir out/\n"
            "  %(prog)s   # normalize the bundled assets/voices/ in place"
        ),
    )
    parser.add_argument(
        "--voices-dir", default=None,
        help="Directory with voice WAV files (default: the skill's bundled "
             "assets/voices/)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Write normalized copies here instead of overwriting the "
             "originals in place",
    )
    args = parser.parse_args()

    if not check_ffmpeg():
        log_progress(
            "ffmpeg is required but not found on PATH. Install with: "
            "brew install ffmpeg",
            "ERROR",
        )
        sys.exit(1)

    voices_dir = (
        Path(args.voices_dir).resolve()
        if args.voices_dir
        else get_default_voices_dir()
    )
    if not voices_dir.is_dir():
        log_progress(f"Voices directory not found: {voices_dir}", "ERROR")
        sys.exit(1)

    wav_files = sorted(voices_dir.glob("*.wav"))
    if not wav_files:
        log_progress(f"No .wav files found in {voices_dir}", "ERROR")
        sys.exit(1)

    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    log_progress(
        f"Normalizing {len(wav_files)} voice file(s) to EBU R128 "
        f"(I={TARGET_LUFS:g} LUFS, TP={TARGET_TP:g} dBTP, {TARGET_SR} Hz)"
    )
    for wf in wav_files:
        before = measure_loudness(wf, TARGET_LUFS, TARGET_TP, TARGET_LRA)
        if output_dir:
            dst = output_dir / wf.name
        else:
            dst = wf.with_name(f"{wf.stem}.normalized.wav")
        after_i, after_tp = normalize_audio_loudness(
            wf,
            dst,
            target_i=TARGET_LUFS,
            target_tp=TARGET_TP,
            target_lra=TARGET_LRA,
            target_sr=TARGET_SR,
        )
        if output_dir:
            log_progress(
                f"  {wf.name}: {before['input_i']} LUFS / {before['input_tp']} "
                f"dBTP -> {after_i:.2f} LUFS / {after_tp:.2f} dBTP -> {dst}"
            )
        else:
            os.replace(dst, wf)
            log_progress(
                f"  {wf.name}: {before['input_i']} LUFS / {before['input_tp']} "
                f"dBTP -> {after_i:.2f} LUFS / {after_tp:.2f} dBTP (in place)"
            )

    log_progress(
        f"Done — {len(wav_files)} voice(s) normalized to "
        f"{TARGET_LUFS:g} LUFS / {TARGET_TP:g} dBTP at {TARGET_SR} Hz"
    )


if __name__ == "__main__":
    main()
