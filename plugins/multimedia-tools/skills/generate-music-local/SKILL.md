---
name: generate-music-local
description: Use when generating full songs or instrumental tracks locally on Apple Silicon from a text prompt and lyrics (text-to-music). Triggers on "generate music", "create a song", "make a track", "AI music generation", "compose music", "music from lyrics", "text-to-music", "instrumental music", "local music model", "MiniMax music", "YuE2", "yue2-mlx", or "GGUF music". Multi-backend — YuE2-3B via native MLX from GGUF weights (torch-free), YuE2-3B via PyTorch MPS, and MiniMax-Music3 MLX.
---

# Generate Music (multi-backend, Apple Silicon)

Generate complete songs and instrumentals **locally on Apple Silicon** from a text
prompt and lyrics. Three engines are available through one entry point:

| `--backend` | Engine | Runtime | Output |
|---|---|---|---|
| `yue2-mlx` | YuE2-3B (audio.cpp **GGUF** Q8_0 + F16 VAE) | **native MLX**, torch-free (vendored) | 48 kHz stereo |
| `yue2` *(default)* | YuE2-3B (m-a-p) + YuE2-Vae | PyTorch **MPS** (`yue2_infer` wheel) | 48 kHz stereo |
| `minimax-mlx` | [MiniMax-Music3 MLX](https://huggingface.co/PocketAiHub/MiniMax-Music3-MLX) port | MLX | 44.1 kHz 16-bit stereo |

All three run on-device — no CUDA, no cloud API. Each is an independent
community port with its own licences; weights are the binding constraint, not
the code (see each backend and **Licences** below).

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
- **Memory: 32 GB works only for short clips; 48 GB is the practical minimum for full 2–4 min songs, and 64 GB is recommended.** Measured during eval: a 180 s @ 30 steps clip peaked at **~56 GB system memory used** (8 GB free on a 64 GB Mac) with no OOM. Generation is memory-heavy, batch size 1. Backend memory guards: `minimax-mlx` refuses to load below **48 GB** free, `yue2` below **8 GB**, `yue2-mlx` below **16 GB** (see Backends); all can wait via `--wait-for-memory`.
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
# YuE2 backend (default): style prompt + lyrics -> 48 kHz song
python3.11 ${SKILL_DIR}/scripts/generate_music.py --setup \
  --prompt "Pop rock, driving guitars, 126 BPM, male lead" \
  --lyrics-file song.lyrics.txt --cot full --seed 20260815 \
  --output ./song.wav

# MiniMax-Music3 backend: pass --backend minimax-mlx explicitly
python3.11 ${SKILL_DIR}/scripts/generate_music.py --setup --backend minimax-mlx \
  --prompt "Lo-fi hip hop, mellow piano, soft vinyl crackle, 84 BPM" \
  --lyrics "[Instrumental]" \
  --seconds 30 --steps 30 --seed 20260815 \
  --output ./song.wav

# Later runs (weights + venv already present) omit --setup.
python3.11 ${SKILL_DIR}/scripts/generate_music.py --backend minimax-mlx \
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

## Backends

`--backend` selects the model engine. **Default: `yue2`.** Common flags (`--prompt`, `--lyrics`/`--lyrics-file`, `--seed`, `--output`, `--setup`, `--wait-for-memory`) apply to all backends; each backend registers its own extra flags.

### `yue2` (default)

- **YuE2-3B** (m-a-p) + YuE2-Vae, run via the official `yue2_infer-0.1.5` wheel on PyTorch **MPS** (experimental — officially CUDA-only; works on Apple Silicon, ~30–35 min per ~3-min song on M-class).
- Example: `python3.11 generate_music.py --prompt "Pop rock, driving guitars, 126 BPM, male lead" --lyrics-file song.lyrics.txt --cot full --output song.wav` (omitting --backend uses yue2).
- Extra flags: `--yue2-model`, `--vae`, `--cot` (`full`|`melody`|`off`, default `full`), `--memory-budget` (default 12).
- Memory guard: refuses to load below **8 GB** free RAM.
- Output: 48 kHz stereo WAV. Weights: **CC BY-NC 4.0** (non-commercial). Venv at `~/Models/YuE2/.venv` (`--setup` installs pinned torch 2.10.0 / transformers 4.57.6 / the reviewed wheel).

### `minimax-mlx`

- **MiniMax-Music3 MLX** (PocketAiHub) — weights auto-detected from the HF hub cache; `python3.11 generate_music.py --backend minimax-mlx --prompt "…" --lyrics "…" --seconds 180 --steps 30 --output song.wav`.
- Extra flags: `--model-dir`, `--seconds` (10–300), `--steps` (1–30).
- Memory guard: refuses to load below **48 GB** free RAM (measured ~56 GB peak for a 180 s clip on a 64 GB Mac).
- Output: 44.1 kHz / 16-bit stereo WAV.

### `yue2-mlx`

- **YuE2-3B** from the [audio.cpp GGUF repack](https://huggingface.co/audio-cpp/Yue2-3B-GGUF) (`yue2-3b-q8_0.gguf` + `yue2-vae-f16.gguf`), run on **native MLX** by a **vendored, torch-free** runtime that ships inside this skill. No PyTorch, no MPS fallback, and no clone or patch step at setup.
- Example: `python3.11 generate_music.py --backend yue2-mlx --prompt "Melodic alt-rock, warm baritone, driving guitars, 92 BPM" --lyrics-file song.lyrics.txt --seconds 180 --min-seconds 170 --output song.wav`
- Extra flags: `--seconds`, `--min-seconds`, `--max-seconds`, `--cot` (`full`|`melody`|`off`, default `full`), `--precision` (`8bit`|`bf16`, default `8bit`), `--memory-budget` (GiB, default 16), `--vae-core-frames`, `--query-chunk-size`, `--work-dir`, `--resource-log`, `--reconvert`.
- **Duration**: this model has no native duration flag. Length comes from the lyrics and a token budget at **25 frames/s**. `--seconds` is a **target**, not a cap: the token ceiling gets **1.5× headroom** so the model can reach a real ending (a hard cap was measured to cut 31% of a batch mid-phrase). `--min-seconds` sets a floor that suppresses the end token; `--max-seconds` replaces the headroom with an explicit hard cap when you need to bound cost. Lyrics are the real length driver — a short lyric will not fill a long `--seconds`. Every run reports whether it hit the cap or the floor, plus a tail-energy check that distinguishes a decayed ending from a cut.
- Memory guard: refuses to load below **16 GB** free RAM (measured peak *physical footprint* **11.05 GiB** for a 7-minute song). Running with less free RAM still completes but is markedly slower — measured **~6x** (13.8 vs 81.9 tokens/s) with zero swapping.
- Setup: `--setup` builds a **torch-free Python 3.12** venv (via `uv`), fetches the GGUFs (~4.5 GB) plus pinned provenance files, and converts them into runtime artifacts (~10 GB, a few minutes) under `~/Models/Yue2-MLX-GGUF`. Setup is idempotent.
- Output: 48 kHz stereo, WAV (float32) or FLAC — prefer `.flac` for long songs. Weights: **CC BY-NC 4.0** (non-commercial).
- Reported at the end of each run: duration, sample rate, channels, peak, RMS and **clipped-sample count** (a clipped render is a defect).
- **Upstream provenance:** the MLX runtime is a pinned, pre-patched vendor. `scripts/backends/_yue2mlx/VENDORED.md` records the upstream revisions, every local change (99 lines), the licence inventory and the re-vendor procedure; licence texts ship in `scripts/backends/_yue2mlx/licenses/`. Use it to pull upstream improvements or to fork.

Adding a backend = drop a module into `scripts/backends/` exposing `NAME`, `DESCRIPTION`, `REQUIRED_RAM_GB`, `add_arguments()`, `run()` (plus an optional `ensure_venv()`), then register it in `BACKENDS`.

## Core Parameters

| Parameter | Required | Default | Range / Notes |
|-----------|----------|---------|---------------|
| `--prompt` | ✅ | — | Musical direction / caption. Use a **Structured Caption** (Global Metadata / Vocal Details / Arrangement) for precise control — see `references/parameters.md` |
| `--lyrics` | ✅* | — | Lyrics text. Use `[Instrumental]` for no vocals. Mutually exclusive with `--lyrics-file` |
| `--lyrics-file` | ✅* | — | UTF-8 file with lyrics (supports `[Verse]`/`[Chorus]` section tags). Mutually exclusive with `--lyrics` |
| `--seconds` | — | `60` | **10–300** (float). Duration of the generated clip (MiniMax backend only) |
| `--steps` | — | `30` | **1–30** (int). Flow-DiT sampling steps. 30 = best quality; 10–15 is fine for drafts (MiniMax backend only) |
| `--seed` | — | `7` | `0 … 2**31-1`. Deterministic for the pinned runtime + MLX versions |
| `--model-dir` | — | auto (HF cache snapshot) | Path to the downloaded repo. **Auto-detected** from the Hugging Face hub cache, so usually omitted; pass it to override (e.g. a `--local-dir` checkout). A normal `--local-dir` checkout or an HF-cache snapshot both work; the helper sets `PYTHONPATH` automatically. Native `generate.py` defaults to its own folder |
| `--output` | — | `song.wav` | Output WAV path (44.1 kHz / 16-bit / stereo) |
| `--wait-for-memory` | — | `0` | If free RAM is below the backend's threshold (48 GB `minimax-mlx` / 8 GB `yue2` / 16 GB `yue2-mlx`), wait up to this many seconds (re-checking every 10 s) before loading the model. `0` = abort immediately with guidance. |
| `--setup` | — | off | Download weights + create venv + install requirements if missing (idempotent) |
| `--backend` | — | `yue2` | Model engine: `yue2` (default), `yue2-mlx`, or `minimax-mlx`. Each backend adds its own flags — see **Backends** below |

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

The helper emits **WAV only**. To deliver MP3s, prefer the sibling **`convert-audio`**
skill if present (same `multimedia-tools` plugin) — it covers format, bitrate and
ID3 options (`-b:a 320k` = max-quality MP3). Fallback one-liner:

```bash
ffmpeg -n -i song.wav -b:a 320k song.mp3 && rm song.wav   # yue2: 48 kHz, minimax-mlx: 44.1 kHz
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
- **Per-backend differences:**
  - `minimax-mlx` uses the pinned Comfy-Org **INT8** weight set, not upstream full-precision Diffusers.
  - `yue2-mlx` has no duration flag: length is driven by lyric length plus the token budget (25 frames/s). A short lyric will not fill a long `--seconds`.
  - `yue2-mlx` writes 48 kHz stereo **float32 WAV** (or FLAC). Prefer `.flac` for songs over ~2 minutes; convert with the `convert-audio` skill (320 kbps one-liner below).
  - `yue2-mlx` renders can run hot at long durations: a 7-minute render measured **70 samples at 0 dBFS** (hard-limited by the decoder, RMS −14.2 dB) while 60-second renders came back clean. Every run reports its clipped-sample count — treat non-zero as a defect and re-seed.
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

- Local, on-device music generation for Apple Silicon only. Three backends behind one CLI: `yue2-mlx` (native MLX, torch-free, GGUF weights), `yue2` (PyTorch MPS, default), `minimax-mlx` (MiniMax-Music3 MLX).
- Required: `--prompt` and exactly one of `--lyrics` / `--lyrics-file`.
- Output: 48 kHz stereo for both YuE2 backends, 44.1 kHz/16-bit for `minimax-mlx`.
- `--seconds` 10–300 for `minimax-mlx`; for `yue2-mlx`, `--seconds`/`--min-seconds` set the token budget (length is really lyric-driven); `yue2` takes no duration flag.
- One-time `--setup` per backend: `yue2-mlx` builds a torch-free Python 3.12 venv and converts the GGUFs (~10 GB); `yue2` installs the reviewed wheel; `minimax-mlx` downloads ~12 GB.
- Save the prompt and lyrics next to the output so each song is reproducible, and report the output path.
- **Review the licences before use.** YuE2 weights (both `yue2` and `yue2-mlx`) are **CC BY-NC 4.0 — non-commercial**; MiniMax-Music3 is under its Community License. Licence texts ship with each backend, and `yue2-mlx`'s upstream provenance is recorded in `scripts/backends/_yue2mlx/VENDORED.md`.
