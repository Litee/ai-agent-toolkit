#!/usr/bin/env python3
"""Generate music locally with MiniMax-Music3-MLX on Apple Silicon.

Orchestrates one-time setup (download ~12 GB weights, create a Python 3.11 venv,
install MLX requirements) and then invokes the bundled ``generate.py``.

Setup is opt-in behind ``--setup`` so the user is never surprised by a large
download. Plain generation requires the repo + venv to already exist.

Stdlib only — run with the system Python (e.g. ``python3.11``); it shells out to
the venv's Python to run the actual model.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ID = "PocketAiHub/MiniMax-Music3-MLX"
# Fallback for manual `--local-dir` checkouts. Normally the helper auto-detects
# the weights from the Hugging Face hub cache instead (see `_default_model_dir`),
# so no `~/Models` symlink is required.
LEGACY_MODEL_DIR = Path.home() / "Models" / "MiniMax-Music3-MLX"


def _default_model_dir() -> Path:
    """Locate the model weights without requiring a `~/Models` symlink.

    `hf download` (no `--local-dir`) lands the repo in the HF hub cache at
    ``~/.cache/huggingface/hub/models--<repo>/snapshots/<commit>``. We return
    that snapshot directory (most recently modified if several exist),
    falling back to the legacy `~/Models` path for manual checkouts.
    """
    snap = (Path.home() / ".cache" / "huggingface" / "hub"
            / "models--PocketAiHub--MiniMax-Music3-MLX" / "snapshots")
    if snap.is_dir():
        subs = [p for p in snap.iterdir() if p.is_dir()]
        if subs:
            subs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return subs[0]
    return LEGACY_MODEL_DIR


def _resolve(exe: str) -> str | None:
    return shutil.which(exe)


def _resolve_hf() -> str:
    for candidate in ("hf", "huggingface-cli"):
        if _resolve(candidate):
            return candidate
    raise SystemExit(
        "Hugging Face CLI not found. Install it (`pip install -U 'huggingface_hub[cli]'` "
        "or `brew install huggingface-cli`) and re-run with --setup."
    )


def _resolve_python311() -> str:
    for candidate in ("python3.11", "python3.12", "python3.13", "python3"):
        exe = _resolve(candidate)
        if exe:
            return exe
    raise SystemExit("Python 3.11+ not found on PATH.")


def ensure_model(model_dir: Path, do_setup: bool) -> None:
    if (model_dir / "generate.py").exists():
        return
    if not do_setup:
        raise SystemExit(
            f"Model not found at {model_dir}. Re-run with --setup to download it "
            f"(~12 GB) from Hugging Face ({REPO_ID})."
        )
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    hf = _resolve_hf()
    print(f"[setup] downloading {REPO_ID} -> {model_dir}", flush=True)
    subprocess.run([hf, "download", REPO_ID, "--local-dir", str(model_dir)], check=True)


def ensure_venv(model_dir: Path, do_setup: bool) -> Path:
    venv = model_dir / ".venv"
    py = venv / "bin" / "python"
    if py.exists() and (venv / "bin" / "pip").exists():
        return venv
    if not do_setup:
        raise SystemExit(
            f"Venv not set up at {venv}. Re-run with --setup to create it and "
            f"install requirements (mlx==0.30.6, numpy, tokenizers)."
        )
    print(f"[setup] creating venv with {_resolve_python311()} ...", flush=True)
    subprocess.run([_resolve_python311(), "-m", "venv", str(venv)], check=True)
    pip = venv / "bin" / "pip"
    subprocess.run([str(pip), "install", "-U", "pip"], check=True)
    req = model_dir / "requirements.txt"
    if not req.exists():
        raise SystemExit(f"requirements.txt missing in {model_dir}; download may be incomplete.")
    subprocess.run([str(pip), "install", "-r", str(req)], check=True)
    return venv


def run_generate(model_dir: Path, venv: Path, args: argparse.Namespace) -> Path:
    python = venv / "bin" / "python"
    # Resolve symlinks so the repo's own modules (minimax_mlx_model) stay importable
    # even when --model-dir points into an HF hub-cache snapshot (generate.py there
    # is a symlink to a content-hashed blob, which would otherwise break imports).
    real_model = model_dir.resolve()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(real_model) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        str(python),
        str(real_model / "generate.py"),
        "--prompt", args.prompt,
        "--seconds", str(args.seconds),
        "--steps", str(args.steps),
        "--seed", str(args.seed),
        "--model-dir", str(real_model),
        "--output", str(args.output),
    ]
    if args.lyrics_file:
        cmd += ["--lyrics-file", str(args.lyrics_file)]
    else:
        cmd += ["--lyrics", args.lyrics]
    print(f"[run] {shlex.join(cmd)}", flush=True)
    # NOTE: do NOT set cwd to the model dir. The helper is normally launched from the
    # user's working directory, and relative --lyrics-file / --output paths must resolve
    # there (not inside the model repo). PYTHONPATH already makes minimax_mlx_model
    # importable, so cwd is left as the caller's cwd.
    subprocess.run(cmd, check=True, env=env)
    return args.output


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate music locally with MiniMax-Music3 MLX (Apple Silicon).",
    )
    p.add_argument("--model-dir", type=Path, default=None,
                   help="Downloaded repo path. Defaults to the Hugging Face hub "
                        "cache snapshot for this model (auto-detected); a "
                        "`--local-dir` checkout also works.")
    p.add_argument("--prompt", required=True, help="Musical direction / caption")
    lyrics = p.add_mutually_exclusive_group(required=True)
    lyrics.add_argument("--lyrics", help="Lyrics text; use [Instrumental] for no vocals")
    lyrics.add_argument("--lyrics-file", type=Path, help="UTF-8 lyrics file")
    p.add_argument("--seconds", type=float, default=60.0, help="Duration 10-300 (default 60)")
    p.add_argument("--steps", type=int, default=30, help="Flow steps 1-30 (default 30)")
    p.add_argument("--seed", type=int, default=7, help="Seed 0..2^31-1 (default 7)")
    p.add_argument("--output", type=Path, default=Path("song.wav"), help="Output WAV path")
    p.add_argument("--setup", action="store_true",
                   help="Download weights + create venv + install requirements if missing")
    return p


def main() -> None:
    args = build_parser().parse_args()
    model_dir = args.model_dir or _default_model_dir()
    ensure_model(model_dir, args.setup)
    venv = ensure_venv(model_dir, args.setup)
    out = run_generate(model_dir, venv, args)
    print(f"[done] {out.resolve()}")


if __name__ == "__main__":
    main()
