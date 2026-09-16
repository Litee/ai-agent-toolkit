"""MiniMax-Music3 MLX backend (default) for the generate-music-local skill.

Weights auto-detected from the Hugging Face hub cache (no ~/Models symlink).
Runs the repo's bundled ``generate.py`` in the snapshot's venv.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path

from ._common import ensure_memory, ensure_venv_check, resolve_hf

NAME = "minimax-mlx"
DESCRIPTION = "MiniMax-Music3 MLX port (PocketAiHub) — text-to-music on Apple Silicon via MLX"
REQUIRED_RAM_GB = 48.0  # measured ~56 GB peak for a 180 s clip on a 64 GB Mac

REPO_ID = "PocketAiHub/MiniMax-Music3-MLX"
LEGACY_MODEL_DIR = Path.home() / "Models" / "MiniMax-Music3-MLX"


def default_model_dir() -> Path:
    snap = (Path.home() / ".cache" / "huggingface" / "hub"
            / "models--PocketAiHub--MiniMax-Music3-MLX" / "snapshots")
    if snap.is_dir():
        subs = [p for p in snap.iterdir() if p.is_dir()]
        if subs:
            subs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return subs[0]
    return LEGACY_MODEL_DIR


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--model-dir", type=Path, default=None,
                   help="Downloaded repo path. Defaults to the Hugging Face hub "
                        "cache snapshot for this model (auto-detected); a "
                        "`--local-dir` checkout also works.")
    p.add_argument("--seconds", type=float, default=60.0, help="Duration 10-300 (default 60)")
    p.add_argument("--steps", type=int, default=30, help="Flow steps 1-30 (default 30)")


def ensure_model(model_dir: Path, do_setup: bool) -> None:
    if (model_dir / "generate.py").exists():
        return
    if not do_setup:
        raise SystemExit(
            f"Model not found at {model_dir}. Re-run with --setup to download it "
            f"(~12 GB) from Hugging Face ({REPO_ID})."
        )
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    hf = resolve_hf()
    print(f"[setup] downloading {REPO_ID} -> {model_dir}", flush=True)
    subprocess.run([hf, "download", REPO_ID, "--local-dir", str(model_dir)], check=True)


def ensure_venv(model_dir: Path, do_setup: bool) -> Path:
    venv = ensure_venv_check(model_dir / ".venv", do_setup, "MiniMax-Music3",
                             "Install: mlx==0.30.6, numpy, tokenizers from the repo's requirements.txt.")
    pip = venv / "bin" / "pip"
    req = model_dir / "requirements.txt"
    if not req.exists():
        raise SystemExit(f"requirements.txt missing in {model_dir}; download may be incomplete.")
    subprocess.run([str(pip), "install", "-r", str(req)], check=True)
    return venv


def run(args: argparse.Namespace) -> Path:
    model_dir = args.model_dir or default_model_dir()
    ensure_model(model_dir, args.setup)
    venv = ensure_venv(model_dir, args.setup)
    ensure_memory(REQUIRED_RAM_GB, args.wait_for_memory)
    python = venv / "bin" / "python"
    # Resolve symlinks so the repo's own modules (minimax_mlx_model) stay importable
    # even when --model-dir points into an HF hub-cache snapshot (generate.py there
    # is a symlink to a content-hashed blob).
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
    # NOTE: do NOT set cwd to the model dir. Relative --lyrics-file / --output must
    # resolve in the caller's cwd. PYTHONPATH already makes minimax_mlx_model importable.
    subprocess.run(cmd, check=True, env=env)
    return args.output