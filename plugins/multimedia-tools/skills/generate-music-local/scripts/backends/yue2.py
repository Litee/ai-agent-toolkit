"""YuE2-3B backend for the generate-music-local skill.

Runs the official ``yue2-infer`` wheel (reviewed) on Apple Silicon via PyTorch
MPS: m-a-p/YuE2-3B (weights auto-resolved from the HF cache) + m-a-p/YuE2-Vae.
Output is 48 kHz stereo WAV. Officially CUDA-only; MPS is experimental but the
wheel ships MPS branches (eager/SDPA fallback) and works on Apple Silicon.

Weights are CC BY-NC 4.0 (non-commercial).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from ._common import ensure_memory, ensure_venv_check, resolve_hf

NAME = "yue2"
DESCRIPTION = "YuE2-3B (m-a-p) — frontier open song generation (48 kHz stereo) on Apple Silicon via MPS"
REQUIRED_RAM_GB = 8.0  # YuE2 footprint (~3.6B bf16 + VAE); ran successfully down to ~6 GB free

MODEL = "m-a-p/YuE2-3B"
VAE = "m-a-p/YuE2-Vae"
WHEEL = "yue2_infer-0.1.5-py3-none-any.whl"
VENV = Path.home() / "Models" / "YuE2" / ".venv"
REPO_CACHE = Path.home() / ".cache" / "huggingface" / "hub" / "models--m-a-p--YuE2-3B"

_DRIVER = r"""
import json, sys
cfg = json.loads(sys.argv[1])
from yue2 import YuE2Pipeline
pipe = YuE2Pipeline.from_pretrained(
    cfg["model"], vae=cfg["vae"], device="mps",
    memory_budget_gib=cfg["memory_budget"], progress=True)
try:
    song = pipe(style=cfg["style"], lyrics=cfg["lyrics"], cot=cfg["cot"], seed=cfg["seed"])
    song.save(cfg["output"])
    print(f"done {len(song.audio) / song.sample_rate:.1f}s @ {song.sample_rate}Hz", flush=True)
finally:
    pipe.close()
"""


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--yue2-model", default=MODEL, help=f"YuE2 model repo or dir (default {MODEL})")
    p.add_argument("--vae", default=VAE, help=f"YuE2 VAE repo or dir (default {VAE})")
    p.add_argument("--cot", choices=("full", "melody", "off"), default="full",
                   help="chain-of-thought mode: full (melody+chord plan, default), melody, or off")
    p.add_argument("--memory-budget", type=float, default=12.0,
                   help="GiB budget; drives VAE chunking and peak RAM (default 12)")


def _locate_wheel() -> Path | None:
    snap = REPO_CACHE / "snapshots"
    if not snap.is_dir():
        return None
    for sub in snap.iterdir():
        if sub.is_dir():
            cand = sub / WHEEL
            if cand.is_file():
                return cand
    return None


def ensure_venv(do_setup: bool) -> Path:
    venv = ensure_venv_check(VENV, do_setup, "YuE2",
                             "Install: torch==2.10.0, transformers==4.57.6, huggingface-hub==0.36.2, "
                             "safetensors, tiktoken, numpy, soundfile, accelerate + the reviewed "
                             "yue2_infer-0.1.5 wheel.")
    pip = venv / "bin" / "pip"
    # Check whether the package is already installed (idempotent).
    probe = subprocess.run([str(venv / "bin" / "python"), "-c", "import yue2, torch"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        return venv
    # Prefer the wheel already present in the HF cache snapshot (no re-download),
    # otherwise fetch the tiny (66 KB) wheel from the model repo.
    wheel = _locate_wheel()
    if wheel is None:
        hf = resolve_hf()
        wheel_dir = VENV.parent
        print(f"[setup] downloading {WHEEL} from {MODEL} ...", flush=True)
        subprocess.run([hf, "download", MODEL, WHEEL, "--local-dir", str(wheel_dir)], check=True)
        wheel = wheel_dir / WHEEL
    print(f"[setup] installing {wheel.name} (pins torch 2.10 / transformers 4.57.6 etc.) ...", flush=True)
    subprocess.run([str(pip), "install", str(wheel)], check=True)
    return venv


def run(args: argparse.Namespace) -> Path:
    ensure_memory(REQUIRED_RAM_GB, args.wait_for_memory)
    venv = ensure_venv(args.setup)
    lyrics = args.lyrics
    if args.lyrics_file:
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")
    cfg = {
        "model": args.yue2_model,
        "vae": args.vae,
        "memory_budget": args.memory_budget,
        "style": args.prompt,
        "lyrics": lyrics,
        "cot": args.cot,
        "seed": args.seed,
        "output": str(Path(args.output).resolve()),
    }
    cmd = [str(venv / "bin" / "python"), "-c", _DRIVER, json.dumps(cfg)]
    print(f"[run] yue2 pipeline: model={cfg['model']} vae={cfg['vae']} "
          f"cot={cfg['cot']} seed={cfg['seed']} output={cfg['output']}", flush=True)
    subprocess.run(cmd, check=True)
    return Path(cfg["output"])