"""YuE2-3B on native MLX, from the audio.cpp GGUF weight set.

Weights are the audio.cpp Q8_0 repack (main model) plus its F16 Oobleck VAE,
run by a vendored, torch-free MLX runtime that ships inside this skill. The
runtime is a pre-patched vendor, so setup needs no clone, no fetch of the
upstream repo, and no patch step on the user's machine -- see
``_yue2mlx/VENDORED.md`` for the pinned upstream revisions and every local change.

Output: 48 kHz stereo (WAV or FLAC). Weights are CC BY-NC 4.0: non-commercial.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from ._common import ensure_memory, resolve_hf

NAME = "yue2-mlx"
DESCRIPTION = ("YuE2-3B (audio.cpp GGUF Q8_0 + F16 VAE) on Apple Silicon via native MLX "
               "-- torch-free, 48 kHz stereo")
# Measured peak *physical footprint* of the whole process: 11.05 GiB for a 7-minute
# song, 10.66 GiB of it MLX. 16 GiB leaves headroom without demanding 48 GB. Note
# that running with less free RAM still completes -- it is just markedly slower
# (measured ~6x: 13.8 vs 81.9 tokens/s), which is why the pre-flight exists.
REQUIRED_RAM_GB = 16.0

GGUF_REPO = "audio-cpp/Yue2-3B-GGUF"
GGUF_MAIN = "yue2-3b-q8_0.gguf"       # 4,264,186,432 bytes
GGUF_VAE = "yue2-vae-f16.gguf"        # 265,218,656 bytes
# Provenance files (config, tokenizer, licences) must come from the pinned HF
# source, because the runtime's converter hashes them against those revisions.
MODEL_REPO = "m-a-p/YuE2-3B"
MODEL_REVISION = "1a96eca688d6ae5d7f0feb88573fec89920fcd19"
VAE_REPO = "m-a-p/YuE2-Vae"
VAE_REVISION = "95535e72a97bc0f09b8ada125d26b4009428c0e8"
PROVENANCE_FILES = ("config.json", "qwen.tiktoken", "LICENSE", "THIRD_PARTY_NOTICES.md",
                    "licenses/SnakeBeta-NVIDIA-MIT.txt", "licenses/stable-audio-tools-MIT.txt")

FRAMES_PER_SECOND = 25          # 48000 Hz / 1920 samples per latent frame
# This model has no duration conditioning: it ends when it decides to, by emitting
# its end token. Treating --seconds as a hard cap therefore CUTS songs mid-phrase
# (measured: renders that hit the cap ended at 58-138% of the song's own RMS, i.e.
# at full energy, and stopped at exactly the requested second). So --seconds is a
# *target* and the cap gets headroom, letting the model reach a real ending.
SECONDS_HEADROOM = 1.5
# `len(prefix) + max_tokens <= CONTEXT` is enforced by the runtime, so the cap has
# to leave room for the lyrics + generated score. Measured prefixes: 49 (cot=off),
# 896 (60 s cot=full), 2380 (175 s), ~4200 (416 s) -- 8192 is comfortably above all.
CONTEXT_TOKENS = 24576
PREFIX_RESERVE_TOKENS = 8192
VENDOR_DIR = Path(__file__).resolve().parent / "_yue2mlx"
DEFAULT_WORK_DIR = Path.home() / "Models" / "Yue2-MLX-GGUF"


def _work_dir(args) -> Path:
    return Path(args.work_dir).expanduser() if getattr(args, "work_dir", None) else DEFAULT_WORK_DIR


def _hf_cache_snapshot(slug: str) -> Path | None:
    snapshots = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{slug}" / "snapshots"
    if not snapshots.is_dir():
        return None
    # Prefer the snapshot that actually carries the files we need.
    subs = [p for p in snapshots.iterdir() if p.is_dir()]
    for sub in sorted(subs, key=lambda p: p.stat().st_mtime, reverse=True):
        if any((sub / name).exists() for name in PROVENANCE_FILES):
            return sub
    return subs[0] if subs else None


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--seconds", type=float, default=None,
                   help="target song length in seconds (default 180). This model has no "
                        "native duration flag: it ends when it decides to, driven by the "
                        "lyrics. --seconds is a target, not a guarantee, and the token cap "
                        "gets 1.5x headroom so the model can reach a real ending.")
    p.add_argument("--max-seconds", type=float, default=None,
                   help="explicit hard cap in seconds, replacing the 1.5x headroom. A render "
                        "that reaches this cap is cut off mid-phrase; use only when you "
                        "need to bound cost.")
    p.add_argument("--min-seconds", type=float, default=None,
                   help="guaranteed minimum length in seconds (sets the token floor that "
                        "suppresses the end token). Omit to let the model end naturally.")
    p.add_argument("--cot", choices=("full", "melody", "off"), default="full",
                   help="chain-of-thought mode: full (generate a score, default), "
                        "melody, or off (direct generation, no score)")
    p.add_argument("--precision", choices=("8bit", "bf16"), default="8bit",
                   help="AR precision: 8bit consumes the GGUF's native Q8_0 weights "
                        "directly (default); bf16 dequantises them")
    p.add_argument("--memory-budget", type=float, default=16.0,
                   help="GiB budget for the runtime's true-memory guard; it aborts if the "
                        "process's physical footprint exceeds this (default 16)")
    p.add_argument("--vae-core-frames", type=int, default=256,
                   help="VAE decode tile size in latent frames (default 256)")
    p.add_argument("--query-chunk-size", type=int, default=256,
                   help="NAR attention query tile (default 256)")
    p.add_argument("--work-dir", type=Path, default=None,
                   help=f"where artifacts and the venv live (default {DEFAULT_WORK_DIR})")
    p.add_argument("--resource-log", type=Path, default=None,
                   help="write the guard's memory samples here as .jsonl")
    p.add_argument("--reconvert", action="store_true",
                   help="rebuild the artifacts even if a valid conversion exists")


def _runs_as_312(exe: str) -> bool:
    """PATH presence is not proof: mise/asdf/pyenv shims resolve but can fail."""
    try:
        out = subprocess.run([exe, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0 and out.stdout.strip() == "3.12"


def _venv_ready(python: Path) -> bool:
    if not python.exists():
        return False
    probe = subprocess.run(
        [str(python), "-c", "import sys, mlx.core, mlx_lm, soundfile, tiktoken; "
                           "assert sys.version_info[:2] == (3, 12), sys.version"],
        capture_output=True, text=True)
    return probe.returncode == 0


def create_venv(venv: Path) -> tuple[Path, list[str]]:
    """Create a Python 3.12 venv. Returns (python, pip-install command prefix).

    Prefers ``uv``: it fetches a 3.12 interpreter itself and is unaffected by
    tool-manager shims. Falls back to a PATH interpreter only after proving it
    actually runs as 3.12 -- ``shutil.which("python3.12")`` happily returns a mise
    shim that exits 1 with "No version is set for shim".
    """
    if shutil.which("uv"):
        print("[setup] creating Python 3.12 venv with uv", flush=True)
        subprocess.run(["uv", "venv", "--python", "3.12", str(venv)], check=True)
        python = venv / "bin" / "python"
        return python, ["uv", "pip", "install", "--python", str(python)]
    for candidate in ("python3.12", "python3"):
        exe = shutil.which(candidate)
        if exe and _runs_as_312(exe):
            print(f"[setup] creating Python 3.12 venv with {exe}", flush=True)
            subprocess.run([exe, "-m", "venv", str(venv)], check=True)
            return venv / "bin" / "python", [str(venv / "bin" / "pip"), "install"]
    raise SystemExit(
        "A working Python 3.12 interpreter was not found.\n"
        "The MLX runtime is validated on 3.12 only. Install one:\n"
        "  brew install uv          # recommended: uv fetches 3.12 itself\n"
        "  brew install python@3.12\n"
        "Note: tool-manager shims (mise/asdf/pyenv) can be on PATH yet fail with\n"
        "'No version is set for shim' -- verify with `python3.12 -V` directly."
    )


def ensure_venv(do_setup: bool, work: Path) -> Path:
    venv = work / ".venv"
    python = venv / "bin" / "python"
    if _venv_ready(python):
        return venv
    if not do_setup:
        raise SystemExit(
            f"yue2-mlx venv not set up at {venv}. Re-run with --setup to create it and "
            f"install the torch-free requirements ({VENDOR_DIR / 'requirements.txt'})."
        )
    work.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(venv, ignore_errors=True)   # clear any partial venv from a failed run
    python, pip = create_venv(venv)
    if not _runs_as_312_simple(python):
        raise SystemExit(f"Created venv is not Python 3.12: {python}")
    print("[setup] installing torch-free requirements", flush=True)
    subprocess.run([*pip, "-r", str(VENDOR_DIR / "requirements.txt")], check=True)
    return venv


def _runs_as_312_simple(python: Path) -> bool:
    try:
        out = subprocess.run([str(python), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                             capture_output=True, text=True)
    except OSError:
        return False
    return out.returncode == 0 and out.stdout.strip() == "3.12"


def _ensure_hf_file(repo: str, filename: str, revision: str, target_dir: Path) -> None:
    target = target_dir / filename
    if target.exists() and target.stat().st_size > 0:
        return
    hf = resolve_hf()
    revision_flag = ["--revision", revision] if revision else []
    print(f"[setup] downloading {repo}/{filename}", flush=True)
    subprocess.run([hf, "download", repo, filename, *revision_flag,
                    "--local-dir", str(target_dir)], check=True)


def ensure_weights(do_setup: bool, work: Path) -> None:
    """Fetch the two GGUFs plus the pinned provenance files into the HF cache."""
    gguf_dir = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{GGUF_REPO.replace('/', '--')}"
    have_gguf = all(
        any(p.stat().st_size > 0 for p in gguf_dir.glob(f"snapshots/*/{name}"))
        for name in (GGUF_MAIN, GGUF_VAE)
    ) if gguf_dir.is_dir() else False
    have_prov = _hf_cache_snapshot(MODEL_REPO.replace("/", "--")) is not None \
        and _hf_cache_snapshot(VAE_REPO.replace("/", "--")) is not None
    if have_gguf and have_prov:
        return
    if not do_setup:
        missing = "GGUF weights" if not have_gguf else "provenance files"
        raise SystemExit(
            f"{missing} not found in the Hugging Face cache. Re-run with --setup to download:\n"
            f"  {GGUF_REPO} ({GGUF_MAIN} 4.3 GB + {GGUF_VAE} 0.3 GB)\n"
            f"  {MODEL_REPO}@{MODEL_REVISION[:12]} (config, tokenizer, licences)\n"
            f"  {VAE_REPO}@{VAE_REVISION[:12]} (config)"
        )
    hf = resolve_hf()
    print(f"[setup] downloading {GGUF_REPO} GGUF weights (~4.5 GB)", flush=True)
    subprocess.run([hf, "download", GGUF_REPO, GGUF_MAIN, GGUF_VAE], check=True)
    print(f"[setup] downloading {MODEL_REPO} provenance files", flush=True)
    subprocess.run([hf, "download", MODEL_REPO, "--revision", MODEL_REVISION,
                    *PROVENANCE_FILES], check=True)
    print(f"[setup] downloading {VAE_REPO} config", flush=True)
    subprocess.run([hf, "download", VAE_REPO, "--revision", VAE_REVISION, "config.json"], check=True)


def ensure_converted(do_setup: bool, work: Path, venv: Path, *, reconvert: bool = False) -> tuple[Path, Path]:
    generator, vae = work / "generator", work / "vae"
    if not reconvert and (generator / "conversion.json").is_file() and (vae / "model.safetensors").is_file():
        return generator, vae
    if not do_setup:
        raise SystemExit(
            f"Converted artifacts not found under {work}. Re-run with --setup to build them "
            f"(about 10 GB and a few minutes)."
        )
    main_gguf = next((Path.home() / ".cache" / "huggingface" / "hub"
                      / f"models--{GGUF_REPO.replace('/', '--')}").glob(f"snapshots/*/{GGUF_MAIN}"), None)
    vae_gguf = next((Path.home() / ".cache" / "huggingface" / "hub"
                     / f"models--{GGUF_REPO.replace('/', '--')}").glob(f"snapshots/*/{GGUF_VAE}"), None)
    model_dir = _hf_cache_snapshot(MODEL_REPO.replace("/", "--"))
    vae_dir = _hf_cache_snapshot(VAE_REPO.replace("/", "--"))
    if not all((main_gguf, vae_gguf, model_dir, vae_dir)):
        raise SystemExit("Downloaded weights are incomplete; re-run with --setup.")
    print(f"[setup] converting {main_gguf.name} -> {generator} (~10 GB, a few minutes)", flush=True)
    subprocess.run([str(venv / "bin" / "python"), "-m", "backends._yue2mlx.gguf",
                    "--main-gguf", str(main_gguf), "--vae-gguf", str(vae_gguf),
                    "--out", str(generator), "--vae-out", str(vae),
                    "--source-dir", str(model_dir), "--vae-source-dir", str(vae_dir)],
                   check=True, cwd=str(VENDOR_DIR.parent.parent))
    return generator, vae


_DRIVER = r"""
import json, sys
cfg = json.loads(sys.argv[1])
import numpy as np
import mlx.core as mx
from backends._yue2mlx.core.protocol import GenerationConfig
from backends._yue2mlx.runtime.pipeline import YuE2Pipeline

pipe = YuE2Pipeline(
    cfg["generator"], cfg["vae"], precision=cfg["precision"],
    generation_config=GenerationConfig.from_dict(cfg["generation"]),
    memory_budget_gib=cfg["memory_budget"], vae_core_frames=cfg["vae_core_frames"],
    query_chunk_size=cfg["query_chunk_size"], progress=True,
    resource_path=cfg["resource_log"],
)
try:
    result = pipe(style=cfg["style"], lyrics=cfg["lyrics"], cot=cfg["cot"],
                  seed=cfg["seed"], id=cfg["id"])
    result.save(cfg["output"])
finally:
    pipe.close()

# Report measured signal health: clipped samples are a defect, not a preference.
audio = result.audio
peak = float(np.abs(audio).max())
rms = float(np.sqrt((audio ** 2).mean()))
clipped = int((np.abs(audio) >= 0.999).sum())
seconds = audio.shape[0] / result.sample_rate
print(f"[audio] {seconds:.1f}s  {result.sample_rate} Hz  {audio.shape[1]} ch", flush=True)
print(f"[audio] peak {peak:.4f} ({20*np.log10(max(peak,1e-9)):.2f} dBFS)  "
      f"RMS {rms:.4f} ({20*np.log10(max(rms,1e-9)):.2f} dB)", flush=True)
print(f"[audio] clipped samples: {clipped}", flush=True)
if clipped:
    print(f"[audio] WARNING: {clipped} sample(s) at or above full scale -- the render "
          f"clipped and was hard-limited by the decoder.", flush=True)
print(f"[timing] {json.dumps(result.timing)}", flush=True)

# Independent tail check: a natural ending decays toward silence, a cap-truncated
# one stops at full energy. This catches abrupt endings whatever their cause.
tail = audio[-max(1, int(result.sample_rate * 0.5)):]
tail_rms = float(np.sqrt((tail ** 2).mean()))
ratio = tail_rms / max(rms, 1e-9)
print(f"[audio] tail RMS {tail_rms:.4f} vs overall {rms:.4f} (ratio {ratio:.2f})", flush=True)
trunc = result.truncated or {}
if trunc.get("semantic") or trunc.get("abc"):
    print("[audio] WARNING: generation hit its token cap -- the ending is abrupt, not "
          "musical. Raise --seconds, or shorten the lyrics.", flush=True)
elif ratio > 0.5:
    print(f"[audio] WARNING: the render ends at {ratio:.0%} of its average energy, which "
          "usually means it was cut off rather than resolved.", flush=True)

# The floor is the mirror problem: min_tokens suppresses the end token, so a song
# that wanted to finish earlier is held open and then ends at the first opportunity.
n_sem = len(result.semantic.tokens)
floor = cfg.get("generation", {}).get("semantic", {}).get("min_tokens", 0)
if floor and n_sem <= floor + 40:
    print(f"[audio] WARNING: the song ran only {n_sem - floor} tokens past the "
          f"--min-seconds floor ({floor} tokens), so the model was held open and then "
          f"ended at the first opportunity -- a forced ending. Lower --min-seconds, or "
          f"lengthen the lyrics.", flush=True)
print(f"[tokens] semantic {n_sem} (floor {floor or 0})", flush=True)
"""


def run(args: argparse.Namespace) -> Path:
    ensure_memory(REQUIRED_RAM_GB, args.wait_for_memory)
    work = _work_dir(args)
    venv = ensure_venv(args.setup, work)
    ensure_weights(args.setup, work)
    generator, vae = ensure_converted(args.setup, work, venv, reconvert=args.reconvert)

    lyrics = args.lyrics
    if args.lyrics_file:
        lyrics = Path(args.lyrics_file).read_text(encoding="utf-8")

    seconds = 180.0 if args.seconds is None else float(args.seconds)
    if args.max_seconds is not None:
        cap_seconds = float(args.max_seconds)
    else:
        cap_seconds = seconds * SECONDS_HEADROOM
    abc_budget = max(4096, int(round(seconds * 9)))
    # Clamp so that prefix + budget still fits the 24576 context.
    ceiling = CONTEXT_TOKENS - PREFIX_RESERVE_TOKENS
    max_tokens = int(round(cap_seconds * FRAMES_PER_SECOND))
    if max_tokens > ceiling:
        print(f"[run] note: cap clamped from {max_tokens} to {ceiling} tokens "
              f"({ceiling / FRAMES_PER_SECOND:.0f}s) to fit the context window", flush=True)
        max_tokens = ceiling
    generation = {"semantic": {"max_tokens": max_tokens}}
    if args.min_seconds is not None:
        generation["semantic"]["min_tokens"] = int(round(float(args.min_seconds) * FRAMES_PER_SECOND))
    # A long song needs a long score; the runtime's default abc cap (4096) is what
    # a ~8 token/second score needs, so only lift it for very long requests.
    generation["abc"] = {"max_tokens": abc_budget}

    output = Path(args.output).resolve()
    resource_log = args.resource_log
    if resource_log is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        resource_log = work / "resources" / f"{output.stem}-{stamp}.jsonl"
    resource_log = Path(resource_log)
    resource_log.parent.mkdir(parents=True, exist_ok=True)

    cfg = {
        "generator": str(generator), "vae": str(vae),
        "precision": args.precision, "cot": args.cot, "seed": args.seed,
        "style": args.prompt, "lyrics": lyrics, "id": output.stem[:170] or "song",
        "memory_budget": args.memory_budget, "vae_core_frames": args.vae_core_frames,
        "query_chunk_size": args.query_chunk_size, "generation": generation,
        "output": str(output), "resource_log": str(resource_log),
    }
    cmd = [str(venv / "bin" / "python"), "-c", _DRIVER, json.dumps(cfg)]
    print(f"[run] yue2-mlx: precision={args.precision} cot={args.cot} seed={args.seed} "
          f"seconds={seconds:g}"
          + (f" min_seconds={args.min_seconds:g}" if args.min_seconds is not None else "")
          + f"\n[run] semantic tokens {generation['semantic'].get('min_tokens', 0)}"
            f"-{generation['semantic']['max_tokens']}  abc<= {generation['abc']['max_tokens']}"
          + f"\n[run] output={output}", flush=True)
    subprocess.run(cmd, check=True, cwd=str(VENDOR_DIR.parent.parent))
    return output
