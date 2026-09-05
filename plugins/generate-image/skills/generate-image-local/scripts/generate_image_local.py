#!/usr/bin/env python3
"""Generate images locally with Krea 2 Turbo (diffusers Krea2Pipeline) from the HF cache.

Apple Silicon (MPS) only. Offline: the model must already be present in the Hugging Face
cache — the script never downloads anything. If the cache is missing/pruned it fails with
a clear error.

The script bootstraps a stable uv-managed venv at /tmp/krea-image-venv on first use,
then re-execs itself inside that venv to run the actual generation.
"""
import argparse
import os
import subprocess
import sys
import time

VENV_DIR = "/tmp/krea-image-venv"
HF_CACHE_ROOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--unsloth--Krea-2-Turbo/snapshots"
)

# Krea2Pipeline only ships in dev diffusers (0.39); must install from git.
DEPS = [
    "torch",
    "transformers",
    "accelerate",
    "safetensors",
    "pillow",
    "psutil",
    "git+https://github.com/huggingface/diffusers.git",
]

# Loading Krea-2-Turbo (12B transformer + Qwen3VL encoder) needs a lot of headroom.
# Refuse to load unless at least this much memory is available.
MIN_AVAILABLE_MEMORY_BYTES = 35 * 1024**3  # 35 GiB
MEMORY_POLL_SECONDS = 10


def _available_memory_bytes():
    """Available system memory in bytes (psutil, works on macOS)."""
    try:
        import psutil
    except ImportError:
        sys.exit("error: psutil is required but not installed; run a fresh venv bootstrap.")
    return psutil.virtual_memory().available


def _available_gb():
    return _available_memory_bytes() / 1024.0**3


def wait_for_memory(wait_seconds):
    """Gate model loading on >= 35 GB free memory.

    Polls every MEMORY_POLL_SECONDS. Without --wait-for-memory (or a value <= 0)
    it fails immediately on insufficient memory.
    """
    if _available_memory_bytes() >= MIN_AVAILABLE_MEMORY_BYTES:
        return
    if wait_seconds is None or wait_seconds <= 0:
        sys.exit(
            f"error: at least 35 GB of memory must be available to load Krea-2-Turbo "
            f"(currently {_available_gb():.1f} GB available). Close other applications and "
            f"retry, or pass --wait-for-memory <seconds>."
        )
    deadline = time.monotonic() + wait_seconds
    print(
        f"waiting for >= 35 GB free memory "
        f"(currently {_available_gb():.1f} GB); polling every {MEMORY_POLL_SECONDS}s "
        f"up to {wait_seconds}s..."
    )
    while time.monotonic() < deadline:
        time.sleep(MEMORY_POLL_SECONDS)
        gb = _available_gb()
        print(f"  memory: {gb:.1f} GB available (need >= 35)")
        if _available_memory_bytes() >= MIN_AVAILABLE_MEMORY_BYTES:
            print("enough memory available; proceeding")
            return
    sys.exit(
        f"error: still below 35 GB of available memory after {wait_seconds}s. "
        "Aborting without loading the model."
    )


def ensure_venv():
    """Create/repair the stable /tmp venv and install deps once (idempotent)."""
    if not shutil_which("uv"):
        sys.exit("error: 'uv' not found. Install it (https://docs.astral.sh/uv/) and rerun.")
    marker = os.path.join(VENV_DIR, ".deps-installed")
    if not os.path.isdir(VENV_DIR):
        subprocess.run(["uv", "venv", VENV_DIR], check=True)
    py = os.path.join(VENV_DIR, "bin", "python")
    if not os.path.exists(marker):
        print("installing dependencies into", VENV_DIR, "(first run may take a while)")
        subprocess.run(["uv", "pip", "install", "--python", py] + DEPS, check=True)
        open(marker, "w").close()
    return py


def shutil_which(name):
    from shutil import which
    return which(name)


def resolve_model_dir(explicit):
    if explicit:
        if not os.path.isdir(explicit):
            sys.exit(f"error: --model-path not found: {explicit}")
        return explicit
    if not os.path.isdir(HF_CACHE_ROOT):
        sys.exit(
            "Krea-2-Turbo not found in the HF cache.\n"
            "Populate it first (Unsloth Images tab, or `hf download unsloth/Krea-2-Turbo`), "
            "then rerun."
        )
    revs = sorted(
        d for d in os.listdir(HF_CACHE_ROOT)
        if os.path.isdir(os.path.join(HF_CACHE_ROOT, d)) and not d.startswith(".")
    )
    if not revs:
        sys.exit(
            f"No model snapshot under {HF_CACHE_ROOT}. The cache looks pruned; "
            "re-fetch the model before rerunning."
        )
    model_dir = os.path.join(HF_CACHE_ROOT, revs[-1])  # newest revision
    if not os.path.exists(os.path.join(model_dir, "model_index.json")):
        sys.exit(
            f"Model snapshot incomplete (missing model_index.json) at {model_dir}. "
            "The cache may be pruned; re-fetch the model before rerunning."
        )
    return model_dir


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="generate_image_local.py",
        description="Local Krea 2 Turbo text-to-image (diffusers, Apple Silicon/MPS, offline).",
    )
    p.add_argument("prompt", help="Text prompt describing the image (required).")
    p.add_argument("--output-dir", required=True, help="Directory to save images (required).")
    p.add_argument("--filename", default=None, help="Base filename (default: 'krea').")
    p.add_argument("--steps", type=int, default=8,
                   help="Denoising steps (Krea 2 Turbo is distilled; default 8).")
    p.add_argument("--width", type=int, default=1024, help="Image width (multiple of 16).")
    p.add_argument("--height", type=int, default=1024, help="Image height (multiple of 16).")
    p.add_argument("--negative-prompt", default=None, help="What to exclude from the image.")
    p.add_argument("--seed", type=int, default=None, help="Base seed; image i uses seed + i.")
    p.add_argument("--num-images", type=int, default=1, help="Number of images to generate.")
    p.add_argument("--model-path", default=None, help="Override the cached model directory.")
    p.add_argument(
        "--wait-for-memory",
        type=int,
        default=None,
        metavar="SECONDS",
        help="If >= 35 GB of memory is not available, poll every 10s until it is, "
        "up to this many seconds, then fail. Default: fail immediately.",
    )
    return p.parse_args(argv)


def generate(args):
    import torch
    from diffusers import Krea2Pipeline

    wait_for_memory(args.wait_for_memory)

    if args.width % 16 or args.height % 16:
        sys.exit("error: --width and --height must be multiples of 16.")

    model_dir = resolve_model_dir(args.model_path)
    device = "mps"
    # bfloat16 is unreliable on Apple Silicon MPS; float16 is the safe choice.
    dtype = torch.float16

    print(f"loading Krea 2 Turbo from {model_dir} (this can take a minute)...")
    pipe = Krea2Pipeline.from_pretrained(model_dir, dtype=dtype, local_files_only=True)
    pipe = pipe.to(device)
    print("model ready")

    os.makedirs(args.output_dir, exist_ok=True)
    for i in range(args.num_images):
        gen = (
            torch.Generator(device=device).manual_seed(args.seed + i)
            if args.seed is not None
            else None
        )
        image = pipe(
            prompt=args.prompt,
            negative_prompt=args.negative_prompt,
            height=args.height,
            width=args.width,
            num_inference_steps=args.steps,
            guidance_scale=0.0,  # Krea 2 Turbo is distilled: guidance disabled
            generator=gen,
        ).images[0]
        base = args.filename or "krea"
        suffix = "" if args.num_images == 1 else f"_{i}"
        path = os.path.join(args.output_dir, f"{base}{suffix}.png")
        image.save(path)
        print(f"saved {path}")


def main():
    args = parse_args(sys.argv[1:])
    if not os.environ.get("KREA_IN_VENV"):
        py = ensure_venv()
        env = dict(os.environ, KREA_IN_VENV="1")
        os.execve(py, [py, os.path.abspath(__file__)] + sys.argv[1:], env)
    generate(args)


if __name__ == "__main__":
    main()
