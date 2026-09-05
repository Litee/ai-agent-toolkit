---
name: generate-music-local
description: Use when generating full songs or instrumental tracks locally on Apple Silicon from a text prompt and lyrics (text-to-music). Triggers on "generate music", "create a song", "make a track", "AI music generation", "compose music", "music from lyrics", "text-to-music", "instrumental music", "local music model", or "MiniMax music". Uses the MiniMax-Music3 MLX port (PocketAiHub/MiniMax-Music3-MLX).
---

# Generate Music (MiniMax-Music3 MLX)

Generate complete songs and instrumentals **locally on Apple Silicon** using the
[MiniMax-Music3 MLX port](https://huggingface.co/PocketAiHub/MiniMax-Music3-MLX)
(PocketAiHub). The port runs the full autoregressive → flow-DiT → DAV synthesis
path with MLX — no CUDA, no ComfyUI, no cloud API. Output is a 44.1 kHz, 16-bit
stereo WAV.

This is an **independent community port**, not an official MiniMax release. The
bundled weights are unchanged copies of the pinned Comfy-Org INT8 repack.

## ⚠️ License — read before generating

Generated audio, the model weights, and this package are governed by the
**MiniMax-Music3 Community License** (bundled as `LICENSE` in the repo). It
includes an acceptable-use policy and commercial-use terms. **Review it before
downloading, redistributing, or deploying.** You are responsible for the rights
to your prompts, lyrics, and any generated content. If the user's intended use
looks commercial or out of scope, point them at the license file first.

## Prerequisites (hardware / OS)

This port targets **Apple Silicon macOS only**:

- Apple Silicon Mac (M1/M2/M3/M4/M5)
- macOS 14 (Sonoma) or newer
- Python 3.11–3.13 (3.11 recommended)
- **Memory: 32 GB works only for short clips; 48 GB is the practical minimum for full 2–4 min songs, and 64 GB is recommended.** Measured during eval: a 180 s @ 30 steps clip peaked at **~56 GB system memory used** (8 GB free on a 64 GB Mac) with no OOM. Generation is memory-heavy, batch size 1.
- ~12 GB free disk for the repo + weights

Intel Macs, Linux, Windows, and CPU-only execution are **not** supported.

## Setup (one time)

The skill ships a helper (`scripts/generate_music.py`) that performs setup and
generation in one command. Setup downloads the ~12 GB weights **into the Hugging
Face cache** (via the `hf` CLI) and creates a Python 3.11 venv, so it is **opt-in**
behind `--setup` (never surprises the user with a 12 GB download). `--setup` is
**idempotent**: re-running it skips the download when `generate.py` is already present
**No `~/Models` symlink is required** — the helper auto-detects the downloaded
weights in your Hugging Face hub cache (`~/.cache/huggingface/hub/.../snapshots/<commit>`),
so you can omit `--model-dir` entirely. A `--local-dir` checkout also works if you
prefer an explicit path.

### Option A — helper (recommended)

```bash
# One-time setup: download weights into the HF cache + create venv + install MLX deps
python3.11 ${SKILL_DIR}/scripts/generate_music.py --setup \
  --prompt "Lo-fi hip hop, mellow piano, soft vinyl crackle, 84 BPM" \
  --lyrics "[Instrumental]" \
  --seconds 30 --steps 30 --seed 20260815 \
  --output ./song.wav

# Later runs (weights + venv already present) omit --setup.
# --model-dir is auto-detected from the HF cache; pass it only to override.
python3.11 ${SKILL_DIR}/scripts/generate_music.py \
  --prompt "..." --lyrics-file lyrics.txt --seconds 60 --output ./song.wav
```

### Option B — manual (HF CLI → HF cache)

```bash
# Downloads into the HF cache by default (no --local-dir):
hf download PocketAiHub/MiniMax-Music3-MLX
# Locate the snapshot it landed in:
ls ~/.cache/huggingface/hub/models--PocketAiHub--MiniMax-Music3-MLX/snapshots/
cd ~/.cache/huggingface/hub/models--PocketAiHub--MiniMax-Music3-MLX/snapshots/<commit>
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt      # mlx==0.30.6, numpy>=2.0,<3, tokenizers>=0.22,<0.23
```
# (The helper auto-detects that snapshot, so you can omit --model-dir entirely.)

The helper runs `generate.py` with `PYTHONPATH` set to the resolved model dir, so it
works whether `--model-dir` is an HF-cache snapshot (auto-detected by default — no
symlink needed) or a normal `--local-dir` checkout.

## Core Parameters

| Parameter | Required | Default | Range / Notes |
|-----------|----------|---------|---------------|
| `--prompt` | ✅ | — | Musical direction / caption. Use a **Structured Caption** (Global Metadata / Vocal Details / Arrangement) for precise control — see `references/parameters.md` |
| `--lyrics` | ✅* | — | Lyrics text. Use `[Instrumental]` for no vocals. Mutually exclusive with `--lyrics-file` |
| `--lyrics-file` | ✅* | — | UTF-8 file with lyrics (supports `[Verse]`/`[Chorus]` section tags). Mutually exclusive with `--lyrics` |
| `--seconds` | — | `60` | **10–300** (float). Duration of the generated clip |
| `--steps` | — | `30` | **1–30** (int). Flow-DiT sampling steps. 30 = best quality; 10–15 is fine for drafts |
| `--seed` | — | `7` | `0 … 2**31-1`. Deterministic for the pinned runtime + MLX versions |
| `--model-dir` | — | auto (HF cache snapshot) | Path to the downloaded repo. **Auto-detected** from the Hugging Face hub cache, so usually omitted; pass it to override (e.g. a `--local-dir` checkout). A normal `--local-dir` checkout or an HF-cache snapshot both work; the helper sets `PYTHONPATH` automatically. Native `generate.py` defaults to its own folder |
| `--output` | — | `song.wav` | Output WAV path (44.1 kHz / 16-bit / stereo) |
| `--wait-for-memory` | — | `0` | If free RAM < 48 GB, wait up to this many seconds (re-checking every 10 s) for enough memory before loading the model. `0` = abort immediately with guidance. |
| `--setup` | — | off | Download weights + create venv + install requirements if missing (idempotent) |

\* Exactly one of `--lyrics` / `--lyrics-file` is required.

See `references/parameters.md` for prompt/lyrics guidance and `references/troubleshooting.md`
for failures (install, OOM, stereo collapse, signal checks).

## Lyrics format

Use section tags and line breaks. The model treats tags as soft structure hints —
output may vary:

```
[Verse]
Neon on the dashboard, midnight in the street
Engine keeps on rumbling to a backbeat

[Chorus]
Turn it up, let the good times roll
Fire in the speakers, thunder in your soul
```

For instrumentals, pass `--lyrics "[Instrumental]"` (or a one-line lyrics file
containing `[Instrumental]`).

## Command construction (native CLI)

> These examples invoke the NATIVE `generate.py` directly — you must be in the
> activated venv and inside the repo (or set `PYTHONPATH` to it). The helper
> `scripts/generate_music.py` wraps the same arguments and handles the venv +
> `PYTHONPATH` for you; prefer it.

```bash
python generate.py \
  --prompt "High-energy rock and roll, gritty male vocal, crunchy guitars, boogie piano, live drums, punchy bass, 148 BPM" \
  --lyrics-file lyrics.txt \
  --seconds 180 \
  --steps 30 \
  --seed 20260815 \
  --output song.wav
```

Standard songs run **120–240 s (2–4 min)**; 300 s is the maximum.

Progress prints two phases of stages (model loading 1–3, then generation 1–5):

```
[1/5] Loading MiniMax-Music3 autoregressive model into MLX…
[2/5] Loading MiniMax-Music3 flow transformer into MLX…
[3/5] Loading MiniMax-Music3 DAV decoder into MLX…
[1/5] Generating MiniMax-Music3 acoustic tokens with MLX…
[2/5] Sampling MiniMax-Music3 flow transformer (30 steps)…
[4/5] Decoding MiniMax-Music3 stereo audio with DAV…
[5/5] Writing song.wav…
```

A full song (≈2–4 min / 120–240 s) at 30 steps takes **~30 min** on an M5 Pro / 64 GB
(measured) — the DAV decode of the long waveform dominates. Speed and memory scale with
duration. Measured peak: a 180 s clip used ~56 GB system memory on a 64 GB Mac — ensure
the machine has ≥48 GB free capability for full-length songs. (In the generation phase the
pipeline prints only stages 1, 2, 4, and 5 — stage 3 is not emitted.)

## Examples

### Example 1 — Full vocal song (≈3 min)
```bash
python generate.py --prompt "Dreamy synth-pop, breathy female vocal, warm pads, 100 BPM" \
  --lyrics-file lyrics.txt --seconds 180 --steps 30 --seed 20260815 --output dreamy.wav
```

### Example 2 — Instrumental (≈2.5 min)
```bash
python generate.py --prompt "Cinematic ambient, swelling strings, deep sub bass, 70 BPM" \
  --lyrics "[Instrumental]" --seconds 150 --steps 30 --seed 1 --output ambient.wav
```

### Example 3 — Quick draft (short + few steps)
Use a short duration and fewer steps for a fast sanity check (e.g. 10 s @ 10 steps):
```bash
python generate.py --prompt "Acoustic folk, gentle guitar, 90 BPM" \
  --lyrics "[Instrumental]" --seconds 10 --steps 10 --seed 7 --output draft.wav
```

## Verify the output

The DAV decoder rejects obviously broken output (non-finite, silent, implausible
peak, or ≥75% stereo collapse). After generation, sanity-check the WAV:

```bash
ffmpeg -i song.wav 2>&1 | grep -E "Duration|Hz"      # expect ~44.1 kHz, stereo
python -m unittest tests/test_minimax_mlx_model.py   # repo's lightweight self-tests
```

For a real signal check (channel RMS, peak, stereo correlation, clipped samples),
load the WAV with `wave`/`numpy` or run the repo's `examples/rock-and-roll-60s.json`
reference. A healthy render has: channel peaks < 1.0, non-trivial stereo correlation,
and **0** clipped samples / collapsed blocks. Duration is **approximate** — healthy
renders are commonly shorter than requested (a 180 s request has produced 141–197 s
across seeds) — so judge health on the signal checks, not on hitting the exact
requested duration.

## Limitations

- Apple Silicon macOS only (no Intel/Linux/Windows/CUDA/CPU).
- Memory-intensive, batch size 1.
- Uses the pinned Comfy-Org **INT8** weight set, not upstream full-precision Diffusers.
- Prompts and section tags are generative guidance, not guarantees — lyrics, tempo,
  instrumentation, and structure may vary.
- Seeded output is deterministic **for the pinned runtime + MLX versions** but will
  not match PyTorch/ComfyUI sample-for-sample (different RNG backends).

## Workflow

1. **License check** — confirm the user has reviewed `LICENSE` (MiniMax-Music3 Community License).
2. **Hardware check** — Apple Silicon, macOS 14+, ≥32 GB RAM, ~12 GB disk.
3. **Setup** — if `--model-dir` lacks `generate.py`, download via `hf` and create the venv (helper `--setup`).
4. **Prepare lyrics** — write `<slug>.lyrics.txt` with section tags, or use `--lyrics "[Instrumental]"`. Also save the exact `--prompt` to `<slug>.prompt.txt` (keep both next to the output `.wav`) so the result is reproducible.
5. **Generate** — run `generate.py` (or the helper) with prompt + duration (standard **120–240 s / 2–4 min**) + steps + seed.
6. **Verify** — check duration/format and signal health; report the output path.

## Error handling

- **`command not found: hf`** — install the Hugging Face CLI (`pip install -U huggingface_hub` or `brew install huggingface-cli`); the new binary is `hf`.
- **`python3.11: command not found`** — install Python 3.11 (e.g. `brew install python@3.11`); the pinned `mlx==0.30.6` needs 3.11–3.13.
- **`ModuleNotFoundError: mlx`** — the venv wasn't used; activate `.venv` (or rely on the helper, which calls the venv python directly).
- **OOM / "Application terminated" / swap thrash** — lower `--seconds` (try 10–20, or 120 for a 2–4 min clip), lower `--steps` (10), and close other memory-heavy apps; 48 GB+ is recommended for 60 s @ 30 steps, and a 2–4 min clip is the most memory-hungry case. **Watch memory live during a run:** `vm_stat` (or Activity Monitor → Memory Pressure) is the authoritative signal. `ps -o rss= -p "$(pgrep -f 'snapshots/.*generate.py' | head -1)"` under-reports usage because MLX allocates through the Metal unified-memory allocator, which doesn't show in process RSS — so trust system-wide free/Pressure over the process RSS. If Memory Pressure turns red, stop the run and reduce `--seconds`.
- **`RuntimeError: ... collapsed stereo channel`** — the DAV decode hit the diagnosed stereo-collapse signature; retry with a different `--seed` (the runtime rejects these automatically, so a new run usually succeeds).
- **`RuntimeError: produced silent audio` / `non-finite audio`** — bad seed or prompt; retry with a different seed.
- **Download interrupted** — re-run the same `hf download ... --local-dir <dir>`; it resumes.

## Reference docs

- **`references/parameters.md`** — prompt writing, lyrics/section tags, duration/step trade-offs, seed behavior, output format details, and fine-grained Structured-Caption control.
- **`references/troubleshooting.md`** — install/setup failures, memory tuning, stereo-collapse, signal-check procedure, license/commercial-use notes.

## Summary

- Local, on-device music generation for Apple Silicon only.
- One-time: `hf download` (~12 GB) + Python 3.11 venv + `pip install -r requirements.txt`.
- Required: `--prompt` and exactly one of `--lyrics` / `--lyrics-file`.
- `--seconds` 10–300 (standard songs 120–240 / 2–4 min), `--steps` 1–30 (30 = best), `--seed` for reproducibility.
- Output: 44.1 kHz / 16-bit / stereo WAV.
- Save the prompt (`<slug>.prompt.txt`) and lyrics (`<slug>.lyrics.txt`) next to the output `.wav` so each song is reproducible.
- Review the MiniMax-Music3 Community License before use.
