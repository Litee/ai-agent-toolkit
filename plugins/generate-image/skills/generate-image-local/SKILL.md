---
name: generate-image-local
description: Use when generating images locally on Apple Silicon using the Krea 2 Turbo text-to-image diffusion model (8-bit MLX via mflux) loaded directly from the Hugging Face cache (offline, no cloud). Triggers on "generate image locally", "Krea 2", "Krea 2 Turbo", "local text-to-image", "generate a picture on my Mac", or any request to create images with local ML inference instead of AWS Bedrock. Do NOT use for editing existing images.
---

# Generate Image (Local — Krea 2 Turbo, 8-bit MLX)

Generate text-to-image using **Krea 2 Turbo** via mflux's **8-bit MLX** model (`MLXBits/krea-2-mlx-q8`), loaded **directly from the local Hugging Face cache** — fully offline, no cloud, no Unsloth/Studio dependency. Runs on **Apple Silicon (MLX/Metal)** only. Roughly **1.5–3× faster** than the previous bf16/fp16 diffusers path at half the memory (benchmark in `references/generate-image-local.md`).

This is the **local** counterpart to the `generate-image` skill (which uses AWS Bedrock Nova Canvas).

## Prerequisites

1. **Apple Silicon Mac** (M1/M2/M3/M4) — the pipeline runs on the MLX/Metal device.
2. **`uv`** installed (`https://docs.astral.sh/uv/`).
3. **The model present in the HF cache**, at:
   `~/.cache/huggingface/hub/models--MLXBits--krea-2-mlx-q8/snapshots/<revision>/`
   - The script never downloads anything. Populate the cache first: `hf download MLXBits/krea-2-mlx-q8`.
   - If the cache is missing or pruned (e.g. empty snapshot / no `model.safetensors.index.json`), the script fails with a clear message — it does **not** download.
4. **Resolution-scaled memory.** The model needs ~22 GB of unified memory for weights plus ~9.5 GB per megapixel of activations (measured peaks: ~30 GB @1024², ~61 GB @2048²); loading is refused below that (floored at 16 GB) unless `--wait-for-memory` is used.

## Quick Start

Prompting is **JSON-only**: write a prompt object to a file, then pass `--prompt-json`:

```json
{ "scene": "a serene alpine hot spring at dusk, romantic light" }
```

```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py \
  --prompt-json ./prompt.json --output-dir ./my_images
```

First run bootstraps a stable uv venv at `/tmp/krea-image-venv` (installs the **pinned** dependency set — mflux 0.19.1, mlx 0.32.2, pillow, psutil) and then runs generation. Subsequent runs reuse the venv; bumping the pins in the script re-syncs it automatically.

## CLI Reference

Every argument of `scripts/generate_image_local.py` (run `--help` for the same list):

| Argument | Required | Description | Default |
|----------|----------|-------------|---------|
| `--prompt-json FILE` | ✅ | Path to the JSON prompt object, or `-` to read it from stdin. **The only prompt interface.** Compiled into Krea 2 prose (see Prompting below) | — |
| `--output-dir DIR` | ✅ | Directory to save images (created if missing) | — |
| `--filename NAME` | | Base filename; image *i* is saved as `NAME.png` (single) or `NAME_i.png` (multiple) | `krea` |
| `--steps N` | | Denoising steps (Krea 2 Turbo is distilled) | `8` |
| `--width W` | | Image width in pixels (multiple of 16) | `1024` |
| `--height H` | | Image height in pixels (multiple of 16) | `1024` |
| `--seed N` | | Base seed; image *i* uses `seed + i`. Random per image when unset (the chosen seed is printed) | Random |
| `--num-images N` | | Number of images to generate from the compiled prompt | `1` |
| `--sidecar` | | Write `<image>.txt` next to each saved image, containing the input JSON prompt object (pretty-printed) | Off |
| `--model-path DIR` | | Override the cached model directory (must be an mflux-format snapshot with `model.safetensors.index.json` + `text_encoder/`, `vae/`, `tokenizer/`) | Auto: newest snapshot in the HF cache |
| `--wait-for-memory SECONDS` | | If the resolution-scaled minimum (~22 GB weights + ~9.5 GB/megapixel, floor 16 GB) isn't available, poll every 10 s until enough, up to `SECONDS`, then fail | None — fail immediately |

There is **no positional prompt and no `--negative-prompt`**: prompts are JSON objects
only, and Krea 2 **Turbo** runs with guidance effectively disabled (`guidance=1.0`,
distilled TDM checkpoint), so negative conditioning is a no-op and is intentionally not
exposed.

> **Resolution follows the model.** mflux's Krea2 accepts `--width`/`--height` in pixels; Krea 2 Turbo is trained for 1k–2k resolution. Width/height must be multiples of 16 (mflux pads as needed). `guidance` is fixed at `1.0` (CFG off) because Krea 2 Turbo is a distilled (TDM) checkpoint.

## Examples

Basic (inline JSON via stdin):
```bash
echo '{"scene":"a fox in the snow"}' | \
  python3 ${SKILL_DIR}/scripts/generate_image_local.py --prompt-json - --output-dir ./out
```

Structured prompt + resolution + seed:
```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py \
  --prompt-json ./portrait.json \
  --output-dir ./portraits \
  --width 1024 --height 1024 \
  --seed 42
```
with `portrait.json`:
```json
{
  "scene": "a portrait of a woman in warm light",
  "composition": "close-up, shallow depth of field",
  "lighting": "soft directional studio lighting",
  "style": "editorial photography, film grain"
}
```

Multiple images:
```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py \
  --prompt-json ./abstract.json --output-dir ./abstract \
  --num-images 4 --filename study --sidecar
```
Produces `study.png`, `study_1.png`, `study_2.png`, `study_3.png` — and with `--sidecar` a
matching `study.txt`, `study_1.txt`, … containing the input JSON next to each image.

## Prompting (JSON only)

Krea 2 conditions on **prose**, not JSON (the official krea-2 docs recommend natural language). `--prompt-json` takes a structured object and deterministically compiles it into a dense scene description with a fixed field order — the same idea as the structured-prompt nodes in the ComfyUI ecosystem. This is the **only** prompt interface; there is no positional prompt.

```json
{
  "scene": "young women bathing in a hot spring at dusk, steam rising off the water",
  "subject": "two women, soft smiles, relaxed poses",
  "composition": "wide shot, camera at water level, silhouettes against the orange sky",
  "lighting": "warm golden-hour glow reflected on wet skin",
  "style": "watercolor, loose paper texture, visible brushstrokes",
  "mood": "serene, intimate, romantic",
  "details": "pine trees on the far bank, floating lanterns"
}
```

```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py \
  --prompt-json ./hot-spring.json --output-dir ./out
```

Field order: `scene, subject, characters, environment, composition, lighting, style, mood, details` — any field may also be a list. Add `--sidecar` to write the same JSON object to `<image>.txt` next to each output, so every image keeps its prompt alongside it. (Verbatim Ideogram-4-style JSON captions are *not* used — that schema belongs to Ideogram 4's caption format, and Krea 2 conditions on plain text.)

- Krea 2 responds well to a clear **subject + environment + (optional) pose/lighting/style** structure — put each part in its JSON field.
- There is **no negative conditioning on Turbo**: guidance is disabled (distilled checkpoint), so `--negative-prompt` is not exposed. Describe what you *want* positively; phrases like "without X" are only weakly honored by prose.

## Troubleshooting

- **`MLXBits/krea-2-mlx-q8 not found in the HF cache` / `snapshot incomplete`** — the model isn't in the cache or was pruned. Populate it with `hf download MLXBits/krea-2-mlx-q8` and rerun. The script intentionally does not auto-download.
- **`'uv' not found`** — install `uv` and rerun.
- **`at least N GB of memory must be available for this resolution`** — the gate scales with resolution (`~22 GB` weights + `~9.5 GB/megapixel`, floored at 16 GB): 512² ≈ 18, 1024² ≈ 32, 1280² ≈ 37, 2048² ≈ 62. Close other apps and retry, or pass `--wait-for-memory 120` to poll until memory frees up (fails after the timeout).
- **mlx/mflux import errors** — the venv deps are pinned; if you bumped them or the re-sync failed, delete the `.deps-installed` marker in `/tmp/krea-image-venv` and rerun.
- **Out of memory** — lower `--width`/`--height` (2048² peaks at ~60+ GB), keep `--num-images` low, and close other GPU apps.

## Related Skills

- **`generate-image:generate-image`** — cloud version (AWS Bedrock Nova Canvas).
- **`generate-music:generate-music`**, **`podcast-generation:generate-podcast-audio-local`** — other local-generation skills using the same venv+CLI pattern.