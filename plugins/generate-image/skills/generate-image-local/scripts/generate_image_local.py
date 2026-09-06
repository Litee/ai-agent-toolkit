#!/usr/bin/env python3
"""Generate images locally with Krea 2 Turbo (8-bit MLX, mflux) from the HF cache.

Apple Silicon (MLX/Metal) only. Offline: the model must already be present in the
Hugging Face cache (MLXBits/krea-2-mlx-q8) — the script never downloads anything.
If the cache is missing/pruned it fails with a clear error.

Engine: mflux's Krea2 (8-bit MLX quantized transformer, Qwen3-VL-4B text encoder,
Qwen-Image VAE) — roughly 1.5-3x faster than the old bf16/fp16 diffusers-on-MPS path
and ~half the memory (see references/generate-image-local.md for the benchmark).

Prompts are JSON objects (--prompt-json), compiled into Krea 2 prose — there is no
positional prompt argument. Optional --sidecar writes the input JSON next to each image.

The script bootstraps a stable uv-managed venv at /tmp/krea-image-venv on first use,
then re-execs itself inside that venv to run the actual generation.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time

VENV_DIR = "/tmp/krea-image-venv"
HF_CACHE_ROOT = os.path.expanduser(
    "~/.cache/huggingface/hub/models--MLXBits--krea-2-mlx-q8/snapshots"
)
MODEL_REPO = "MLXBits/krea-2-mlx-q8"

# Pinned known-good dependency set (verified on Apple Silicon on 2026-09-06).
# mflux == the 8-bit MLX Krea 2 engine; mlx pinned to the tested build.
DEPS = [
    "mflux==0.19.1",
    "mlx==0.32.2",
    "pillow==12.3.0",
    "psutil==7.2.2",
]
# Fingerprint of the pinned spec, stored in the venv marker; if DEPS ever change,
# the venv is re-synced automatically on the next run.
DEP_FINGERPRINT = "\n".join(DEPS)

# The 8-bit MLX model needs ~22 GB of unified memory for weights plus activations
# that grow with resolution (measured peaks: ~22.3 GB @512, ~29.7 @1024, ~30.4 @1280,
# ~60.6 @2048). The gate scales with the requested resolution instead of a flat floor.
BASE_WEIGHTS_GB = 22.0          # 8-bit MLX weights + text encoder + VAE
ACTIVATION_GB_PER_MP = 9.5      # rough fit to measured peaks (per megapixel)
MIN_AVAILABLE_GB = 16.0         # absolute floor for tiny resolutions
MEMORY_POLL_SECONDS = 10


def required_memory_gb(width, height):
    """Estimated unified-memory headroom needed for a given resolution, in GiB."""
    megapixels = width * height / 1e6
    return max(MIN_AVAILABLE_GB, BASE_WEIGHTS_GB + ACTIVATION_GB_PER_MP * megapixels)

# Krea 2 Turbo is a distilled (TDM) checkpoint: 8 steps, guidance off.
STEPS_DEFAULT = 8
GUIDANCE = 1.0  # mflux krea2 convention; CFG effectively disabled


def _available_memory_bytes():
    """Available system memory in bytes (psutil, works on macOS)."""
    try:
        import psutil
    except ImportError:
        sys.exit("error: psutil is required but not installed; run a fresh venv bootstrap.")
    return psutil.virtual_memory().available


def _available_gb():
    return _available_memory_bytes() / 1024.0**3


def wait_for_memory(wait_seconds, required_bytes):
    """Gate model loading on ``required_bytes`` of free memory (resolution-scaled).

    Polls every MEMORY_POLL_SECONDS. Without --wait-for-memory (or a value <= 0)
    it fails immediately on insufficient memory.
    """
    if _available_memory_bytes() >= required_bytes:
        return
    required_gb = required_bytes / 1024.0**3
    if wait_seconds is None or wait_seconds <= 0:
        sys.exit(
            f"error: at least {required_gb:.1f} GB of memory must be available for this "
            f"resolution (currently {_available_gb():.1f} GB available). Close other "
            f"applications and retry, or pass --wait-for-memory <seconds>."
        )
    deadline = time.monotonic() + wait_seconds
    print(
        f"waiting for >= {required_gb:.1f} GB free memory "
        f"(currently {_available_gb():.1f} GB); polling every {MEMORY_POLL_SECONDS}s "
        f"up to {wait_seconds}s..."
    )
    while time.monotonic() < deadline:
        time.sleep(MEMORY_POLL_SECONDS)
        gb = _available_gb()
        print(f"  memory: {gb:.1f} GB available (need >= {required_gb:.1f})")
        if _available_memory_bytes() >= required_bytes:
            print("enough memory available; proceeding")
            return
    sys.exit(
        f"error: still below {required_gb:.1f} GB of available memory after "
        f"{wait_seconds}s. Aborting without loading the model."
    )


def ensure_venv():
    """Create/repair the stable /tmp venv; install deps exactly per the pinned DEPS.

    The marker file stores DEP_FINGERPRINT, so a changed pin list re-syncs the venv
    automatically (no stale venv after a dependency bump).
    """
    if not shutil_which("uv"):
        sys.exit("error: 'uv' not found. Install it (https://docs.astral.sh/uv/) and rerun.")
    py = os.path.join(VENV_DIR, "bin", "python")
    marker = os.path.join(VENV_DIR, ".deps-installed")
    needs_install = not os.path.isdir(VENV_DIR) or not os.path.isfile(py)
    if not needs_install and os.path.isfile(marker):
        with open(marker) as f:
            needs_install = f.read() != DEP_FINGERPRINT
    if needs_install and not os.path.isdir(VENV_DIR):
        subprocess.run(["uv", "venv", VENV_DIR], check=True)
    if needs_install:
        print("installing pinned dependencies into", VENV_DIR, "(first run may take a while)")
        subprocess.run(["uv", "pip", "install", "--python", py] + DEPS, check=True)
        with open(marker, "w") as f:
            f.write(DEP_FINGERPRINT)
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
            f"{MODEL_REPO} not found in the HF cache.\n"
            f"Populate it first (`hf download {MODEL_REPO}`), then rerun."
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
    # The MLXBits mflux snapshot has a top-level transformer index plus text_encoder/,
    # vae/ and tokenizer/ subdirs. model.safetensors.index.json is a reliable marker.
    if not os.path.exists(os.path.join(model_dir, "model.safetensors.index.json")) or not os.path.isdir(
        os.path.join(model_dir, "vae")
    ):
        sys.exit(
            f"Model snapshot incomplete (missing model.safetensors.index.json or vae/) "
            f"at {model_dir}. The cache may be pruned; re-fetch the model before rerunning."
        )
    return model_dir


# Structured-JSON -> prose prompt support (--prompt-json). Krea 2 (mflux Krea2, and the
# diffusers pipeline before it) conditions on prose: the official krea-2 docs recommend
# natural language and the model was trained to read flowing, comma-separated scene
# descriptions, not JSON/markup. This compiler mirrors the "structured prompt" nodes
# in the ComfyUI ecosystem / AI-KSK prompt suite: it flattens a JSON object into that
# prose in a fixed field order, so the output is deterministic given the same JSON.
JSON_PROMPT_FIELDS = [
    "scene",        # required-ish anchor: what is happening, where, when
    "subject",      # main subject(s) of the image
    "characters",   # additional characters / figure descriptions
    "environment",  # background / surroundings
    "composition",  # camera angle, framing, crop, perspective
    "lighting",     # light source(s), time of day, quality of light
    "style",        # medium / technique / art-movement vocabulary
    "mood",         # emotional tone
    "details",      # anything else: props, textures, extra elements
]


def compile_json_prompt(data):
    """Compile a structured JSON prompt object into Krea 2 prose (deterministic)."""
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        sys.exit("error: --prompt-json must be a JSON object with string/list values")
    parts = []
    for key in JSON_PROMPT_FIELDS:
        value = data.get(key)
        if isinstance(value, list):
            value = ", ".join(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    if not parts:
        sys.exit(
            'error: --prompt-json needs at least one non-empty field '
            '(e.g. "scene": "a hot spring at dusk")'
        )
    return ", ".join(parts)


def load_prompt(args):
    """Load the JSON prompt object from --prompt-json.

    Returns (compiled_prose, prompt_object). JSON prompting is the only prompt
    interface — there is no positional prompt. The parsed object is also what
    --sidecar writes next to each image.
    """
    if args.prompt_json == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(args.prompt_json) as f:
                raw = f.read()
        except OSError as e:
            sys.exit(f"error: cannot read --prompt-json file: {e}")
    try:
        prompt_obj = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"error: --prompt-json is not valid JSON: {e}")
    return compile_json_prompt(prompt_obj), prompt_obj


def write_sidecar(image_path, prompt_obj):
    """Write '<image>.txt' next to an image containing the input JSON (pretty-printed).

    The compiled prose is a pure, deterministic function of prompt_obj, so the input
    JSON fully reconstructs what was sent to the model.
    """
    sidecar = os.path.splitext(image_path)[0] + ".txt"
    with open(sidecar, "w") as f:
        f.write(json.dumps(prompt_obj, indent=2, ensure_ascii=False) + "\n")
    return sidecar


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="generate_image_local.py",
        description="Local Krea 2 Turbo text-to-image (8-bit MLX via mflux, offline). "
                    "Prompts are JSON objects (--prompt-json).",
    )
    p.add_argument("--prompt-json", metavar="FILE", required=True,
                   help="Path to a structured JSON prompt object, or '-' to read it from "
                        "stdin. Compiled into Krea 2 prose. See SKILL.md for the schema. "
                        "(required; the only prompt interface)")
    p.add_argument("--output-dir", required=True, help="Directory to save images (required).")
    p.add_argument("--filename", default=None, help="Base filename (default: 'krea').")
    p.add_argument("--steps", type=int, default=STEPS_DEFAULT,
                   help=f"Denoising steps (Krea 2 Turbo is distilled; default {STEPS_DEFAULT}).")
    p.add_argument("--width", type=int, default=1024, help="Image width (multiple of 16).")
    p.add_argument("--height", type=int, default=1024, help="Image height (multiple of 16).")
    p.add_argument("--seed", type=int, default=None,
                   help="Base seed; image i uses seed + i. Random when unset (printed).")
    p.add_argument("--num-images", type=int, default=1, help="Number of images to generate.")
    p.add_argument("--sidecar", action="store_true",
                   help="Write '<image>.txt' next to each saved image containing the "
                        "input JSON prompt object (pretty-printed).")
    p.add_argument("--model-path", default=None, help="Override the cached model directory.")
    p.add_argument(
        "--wait-for-memory",
        type=int,
        default=None,
        metavar="SECONDS",
        help="If the resolution-scaled minimum (~22 GB of weights + ~9.5 GB/megapixel "
        "of activations, floored at 16 GB) is not available, poll every 10s until it "
        "is, up to this many seconds, then fail. Default: fail immediately.",
    )
    return p.parse_args(argv)


def generate(args):
    from mflux.models.krea2 import Krea2

    # Validate/compile the prompt first (cheap): a bad prompt should fail instantly
    # instead of after a possibly long --wait-for-memory poll.
    prompt, prompt_obj = load_prompt(args)

    # Resolution-scaled memory gate: bigger canvas, bigger required headroom.
    wait_for_memory(args.wait_for_memory, int(required_memory_gb(args.width, args.height) * 1024**3))

    if args.width % 16 or args.height % 16:
        sys.exit("error: --width and --height must be multiples of 16.")

    model_dir = resolve_model_dir(args.model_path)
    print(f"loading Krea 2 Turbo 8-bit MLX from {model_dir} (this can take a minute)...")
    model = Krea2(model_path=model_dir)  # loads the quantized checkpoints as-is
    print("model ready")

    os.makedirs(args.output_dir, exist_ok=True)
    base = args.filename or "krea"
    for i in range(args.num_images):
        seed = args.seed + i if args.seed is not None else random.randint(0, 2**31 - 1)
        print(f"generating image {i + 1}/{args.num_images} (seed {seed})...")
        result = model.generate_image(
            seed=seed,
            prompt=prompt,
            num_inference_steps=args.steps,
            height=args.height,
            width=args.width,
            guidance=GUIDANCE,  # CFG off for the distilled checkpoint
        )
        suffix = "" if args.num_images == 1 else f"_{i}"
        path = os.path.join(args.output_dir, f"{base}{suffix}.png")
        result.save(path)
        print(f"saved {path}")
        if args.sidecar:
            sidecar = write_sidecar(path, prompt_obj)
            print(f"saved {sidecar}")


def main():
    args = parse_args(sys.argv[1:])
    if not os.environ.get("KREA_IN_VENV"):
        py = ensure_venv()
        env = dict(os.environ, KREA_IN_VENV="1")
        os.execve(py, [py, os.path.abspath(__file__)] + sys.argv[1:], env)
    generate(args)


if __name__ == "__main__":
    main()