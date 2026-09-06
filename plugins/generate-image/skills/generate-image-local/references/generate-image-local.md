# generate-image-local — Reference

Deep-dive for the Krea 2 Turbo local generation skill (8-bit MLX/mflux engine). Read this before modifying the skill.

## Model

- **Model**: `MLXBits/krea-2-mlx-q8` — an **8-bit MLX** conversion of `krea/Krea-2-Turbo` (12.9B single-stream MMDiT, distilled/TDM checkpoint: 8 steps, guidance off). Made with/resolved by **mflux** (Apple-Silicon MLX toolchain).
- **Engine**: `mflux.models.krea2.Krea2` (mflux **0.19.1**, mlx **0.32.2**). Loads the pre-quantized checkpoints as-is from a local dir — no re-quantization, no network.
- **Cache location**: `~/.cache/huggingface/hub/models--MLXBits--krea-2-mlx-q8/snapshots/<revision>/`
  - mflux-format snapshot: top-level `model.safetensors.index.json` + transformer shards `0.safetensors … 6.safetensors` (13.6 GB), `text_encoder/` (Qwen3-VL-4B, 4 shards, ~8 GB), `vae/` (Qwen-Image, ~0.5 GB), `tokenizer/`.
  - The repo is **not** gated — `hf download MLXBits/krea-2-mlx-q8` works without accepting a license.
- The previous engine (diffusers `Krea2Pipeline` + bf16 `unsloth/Krea-2-Turbo` on MPS, float16) was replaced on 2026-09-06 — see the benchmark below for why.

## Benchmark (vs. the old bf16/fp16 diffusers path)

Same prompt, seed 42, 8 steps, cold start (model load included), measured on this Mac:

| Size | bf16/fp16 diffusers | 8-bit MLX (mflux) | Speedup |
|---|---|---|---|
| 512 × 512 | 58.4 s | 19.1 s | 3.06× |
| 1024 × 1024 | 98.9 s | 65.1 s | 1.52× |
| 1280 × 1280 | 161.4 s | 114.3 s | 1.41× |

Peak memory: bf16/fp16 process RSS 40–53 GiB; MLX process RSS ~21 GiB (Metal heap peak: 22.3 GB @512, 29.7 GB @1024, 30.4 GB @1280). The MLX build's printed "Peak MLX memory" is the honest number — its process RSS stays flat because most memory lives in the Metal heap.

## Inference call

```python
from mflux.models.krea2 import Krea2

model = Krea2(model_path=model_dir)   # loads the 8-bit checkpoints as-is; offline
result = model.generate_image(
    seed=seed,                 # int, required
    prompt=prompt,             # compiled Krea 2 prose from the JSON prompt object
    num_inference_steps=8,     # distilled: keep low
    height=height,             # pixels; mflux pads to latent multiples
    width=width,               # pixels; mflux pads to latent multiples
    guidance=1.0,              # distilled: CFG effectively off
)
result.save(out_path)          # GeneratedImage.save(path) — plain PNG
```

### Device notes

- **MLX / Metal** — Apple Silicon only; no torch/CUDA involved.
- `Krea2(model_path=...)` loads the already-quantized weights; do not pass `quantize=` (that would re-quantize/re-download).
- Model load is ~10–20 s; generation is ~7 s/step at 1024² (peak MLX memory 29.7 GB).

## Script architecture

`scripts/generate_image_local.py`:

1. `parse_args` — `--prompt-json` (required; the **only** prompt interface), `--output-dir` (required), `--filename`, `--steps`, `--width`, `--height`, `--seed`, `--num-images`, `--sidecar`, `--model-path`, `--wait-for-memory`.
2. **venv bootstrap** (`ensure_venv`): if `/tmp/krea-image-venv` doesn't exist, `uv venv` + `uv pip install --python <venv> <pinned DEPS>`. All deps are **pinned** — `mflux==0.19.1`, `mlx==0.32.2`, `pillow==12.3.0`, `psutil==7.2.2` (see `DEPS` in the script; the versions the skill was verified against). The `.deps-installed` marker stores a fingerprint of the pinned spec, so the venv **re-syncs automatically when the pins change** — no manual marker surgery.
3. **re-exec** into the venv python (`os.execv` with `KREA_IN_VENV=1`) so `mflux`/`mlx` are importable.
4. `generate` — resolve the compiled prompt (`load_prompt` → `compile_json_prompt`), resolve model dir (explicit `--model-path`, else newest snapshot under the cache; fail clearly if absent/pruned), load `Krea2(model_path=...)`, generate `--num-images` images (seed `+i` when `--seed` given, else a fresh random seed per image — always printed), save `{filename}{_i}.png` into `--output-dir`, and (with `--sidecar`) `write_sidecar` the input JSON to `{filename}{_i}.txt`.

### Sidecar files (--sidecar)

`--sidecar` writes `<image>.txt` next to each saved image containing the **input JSON
prompt object** (pretty-printed via `write_sidecar`). What this preserves and what it
deliberately does not:

- **Preserved:** the JSON fully reconstructs the compiled prose — `compile_json_prompt`
  is a deterministic, pure function of the object (and deps are pinned), so the sidecar
  is a complete record of what prompted this image.
- **Not captured:** the other CLI parameters (seed, steps, width/height, model path).
  Those are the caller's record (stdout prints each saved path; the seed is always
  printed). If full-config reproduction is ever wanted, extend the sidecar with a small
  params header — the script stays JSON-only by design.
- **Not the AGENTS.md convention:** the user's earlier `POSITIVE PROMPT:` /
  `NEGATIVE PROMPT:` sidecars belong to the hosted/cloud workflow (and negatives are
  meaningless on Turbo anyway); this skill's sidecar is the raw JSON input instead.

## Memory gate (resolution-scaled)

- The gate scales with the requested resolution instead of a flat floor: `required =
  max(16, 22 + 9.5 * megapixels)` GiB (`BASE_WEIGHTS_GB` + `ACTIVATION_GB_PER_MP` in the
  script). Examples: 512² ≈ 18, 1024² ≈ 32, 1280² ≈ 37, 2048² ≈ 62 GiB. This tracks the
  measured peaks (29.7 GB @1024², 30.4 @1280², 60.6 @2048²) with some headroom.
- Measured via `psutil.virtual_memory().available` on the host (macOS counts cached
  pages as available, so this is a loose heuristic).
- **`--wait-for-memory <seconds>`**: if below the resolution-scaled threshold, poll
  every 10 s (up to the timeout) until enough memory is available, then load; on
  timeout, abort before loading.
- Without `--wait-for-memory` (or a value ≤ 0), insufficient memory fails immediately
  with a clear message naming the required amount.

## Structured JSON prompts (--prompt-json)

`--prompt-json FILE` (or `-` for stdin) takes a JSON object and compiles it into Krea 2
prose with a fixed field order: `scene, subject, characters, environment, composition,
lighting, style, mood, details`. **This is the only prompt interface** — there is no
positional prompt argument. Rationale:

- The official krea-2 `docs/prompting.md` explicitly recommends **natural-language** prompts; the model was trained on flowing, comma-separated scene descriptions.
- ComfyUI's Krea 2 support and community "structured prompt" tooling (e.g. `AI-KSK/krea2-prompt-suite`'s `krea2_prompt_compiler.py`, structured-prompt builder nodes) assemble prose the same way: structured fields → dense description.
- Verbatim Ideogram-4-style JSON captions (`high_level_description` / `style_description` / `compositional_deconstruction`) are deliberately **not** used: that is Ideogram 4's caption schema, and Krea 2 conditions on plain text.

`compile_json_prompt()` is deterministic and independent of pipeline internals; the
compiled prose is what gets passed to `model.generate_image(prompt=...)`. Errors:
non-JSON input or an empty object fail with a clear message.

### No negative conditioning

Krea 2 Turbo is a distilled (TDM) checkpoint: the script hardcodes `guidance=1.0` (CFG
effectively off), so negative conditioning is meaningless. The JSON schema therefore has
no negative field, and the CLI has no `--negative-prompt`. Unwanted elements are best
handled by describing what you *want* positively; "without X" phrasing is only weakly
honored by prose.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `MLXBits/krea-2-mlx-q8 not found in the HF cache` | Cache dir absent | `hf download MLXBits/krea-2-mlx-q8` |
| `Model snapshot incomplete (missing model.safetensors.index.json or vae/)` | Snapshot pruned (blobs may remain) | Re-fetch the model; snapshot must be restored |
| `'uv' not found` | uv missing | `https://docs.astral.sh/uv/` |
| mlx/mflux import errors | Venv drifted from pins | Delete `.deps-installed` in `/tmp/krea-image-venv`, rerun |
| `< N GB available for this resolution>` | Not enough free memory for the requested size | Close apps, or `--wait-for-memory <seconds>` |
| Out of memory / swap | 2K resolution too heavy | Lower `--width`/`--height`, lower `--num-images` |

## Why offline-only?

The user explicitly chose "assume present, fail clearly": the skill never downloads the
model, never falls back to a cloud endpoint, and never talks to the Unsloth Studio
server. `Krea2(model_path=...)` reads the local mflux snapshot only. That keeps behavior
deterministic and local.

## Related

- Cloud variant: `plugins/generate-image/skills/generate-image/SKILL.md` (Bedrock Nova Canvas).
- The `uv` + stable `/tmp` venv pattern mirrors `plugins/podcast-generation/skills/generate-podcast-audio-local/` (VibeVoice MLX) and the generate-music-local skill.