#!/usr/bin/env python3
"""Generate music locally with any registered backend on Apple Silicon.

Backends: ``yue2-mlx`` (YuE2-3B GGUF on native MLX, torch-free), ``yue2``
(YuE2-3B on MPS) and ``minimax-mlx`` (MiniMax-Music3 MLX). ``--backend``
selects the engine; each backend adds its own flags and one-time setup happens
behind ``--setup``.

Stdlib only — run with the system Python (e.g. ``python3.11``); backends shell
out to their own venv Python to run the actual model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from backends import BACKENDS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate music locally (multi-backend, Apple Silicon).",
    )
    p.add_argument("--backend", choices=sorted(BACKENDS), default="yue2",
                   help="Model engine (default: yue2). See `--help` after "
                        "selection, or SKILL.md 'Backends' for per-backend flags.")
    p.add_argument("--prompt", required=True,
                   help="Musical direction / Structured Caption (MiniMax) or style "
                        "description (YuE2)")
    lyrics = p.add_mutually_exclusive_group(required=True)
    lyrics.add_argument("--lyrics", help="Lyrics text; use [Instrumental] for no vocals")
    lyrics.add_argument("--lyrics-file", type=Path, help="UTF-8 lyrics file")
    p.add_argument("--seed", type=int, default=7, help="Seed 0..2^31-1 (default 7)")
    p.add_argument("--output", type=Path, default=Path("song.wav"),
                   help="Output WAV path (44.1 kHz MiniMax / 48 kHz YuE2)")
    p.add_argument("--setup", action="store_true",
                   help="One-time setup for the selected backend if missing "
                        "(download weights + create venv + install deps)")
    p.add_argument("--wait-for-memory", type=int, default=0, metavar="SECONDS",
                   help="If free RAM is below the backend's safe threshold "
                        "(48 GB minimax-mlx / 8 GB yue2 / 16 GB yue2-mlx), wait up to "
                        "SECONDS (re-checking every 10s) before loading the model. "
                        "0 = abort immediately (default).")
    return p


def main() -> None:
    p = build_parser()
    # Two-pass parsing: pick the backend first, then let it register its own
    # flags before the final parse.
    known, _ = p.parse_known_args()
    backend = BACKENDS[known.backend]
    backend.add_arguments(p)
    args = p.parse_args()
    out = backend.run(args)
    print(f"[done] {out.resolve()}")


if __name__ == "__main__":
    main()