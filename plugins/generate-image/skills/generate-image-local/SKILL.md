---
name: generate-image-local
description: Use when generating images locally on Apple Silicon using the Krea 2 Turbo text-to-image diffusion model loaded directly from the Hugging Face cache (offline, no cloud). Triggers on "generate image locally", "Krea 2", "Krea 2 Turbo", "local text-to-image", "generate a picture on my Mac", or any request to create images with local ML inference instead of AWS Bedrock. Do NOT use for editing existing images.
---

# Generate Image (Local — Krea 2 Turbo)

Generate text-to-image using **Krea 2 Turbo** via the diffusers `Krea2Pipeline`, loaded **directly from the local Hugging Face cache** — fully offline, no cloud, no Unsloth/Studio dependency. Runs on **Apple Silicon (MPS)** only.

This is the **local** counterpart to the `generate-image` skill (which uses AWS Bedrock Nova Canvas).

## Prerequisites

1. **Apple Silicon Mac** (M1/M2/M3/M4) — the pipeline runs on the `mps` device.
2. **`uv`** installed (`https://docs.astral.sh/uv/`).
3. **The model present in the HF cache**, at:
   `~/.cache/huggingface/hub/models--unsloth--Krea-2-Turbo/snapshots/<revision>/`
   - The script never downloads anything. Populate the cache first via the Unsloth Images tab, or `hf download unsloth/Krea-2-Turbo`.
   - If the cache is missing or pruned (e.g. empty snapshot / no `model_index.json`), the script fails with a clear message — it does **not** download.
4. **≥ 35 GB of available memory.** Loading Krea-2-Turbo is refused below that threshold (see `--wait-for-memory` to wait instead of failing).

## Quick Start

```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py "a serene alpine hot spring at dusk, romantic light" \
  --output-dir ./my_images
```

First run bootstraps a stable uv venv at `/tmp/krea-image-venv` (installs torch + dev diffusers + transformers) and then runs generation. Subsequent runs reuse the venv.

## Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `prompt` | Text description of the image (positional, required) | — |
| `--output-dir` | Directory to save images (required) | — |
| `--filename` | Base filename for saved images | `krea` |
| `--steps` | Denoising steps (Krea 2 Turbo is distilled) | `8` |
| `--width` | Image width in pixels (multiple of 16) | `1024` |
| `--height` | Image height in pixels (multiple of 16) | `1024` |
| `--negative-prompt` | What to exclude from the image | None |
| `--seed` | Base random seed; image *i* uses `seed + i` | Random |
| `--num-images` | Number of images to generate | `1` |
| `--model-path` | Override the cached model directory | Auto (newest snapshot) |
| `--wait-for-memory` | If < 35 GB available, poll every 10 s until enough memory, up to this many seconds, then fail | None (fail immediately) |

> **Resolution follows the model.** `Krea2Pipeline` accepts `--width`/`--height` in pixels (not aspect-ratio presets). Width/height must be multiples of 16. `guidance_scale` is fixed at `0.0` because Krea 2 Turbo is a distilled (TDM) checkpoint.

## Examples

Basic:
```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py "a fox in the snow" --output-dir ./out
```

Negative prompt + resolution + seed:
```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py \
  "a portrait of a woman in warm light" \
  --output-dir ./portraits \
  --width 1024 --height 1024 \
  --negative-prompt "deformed hands, extra fingers, low quality, watermark, text" \
  --seed 42
```

Multiple images:
```bash
python3 ${SKILL_DIR}/scripts/generate_image_local.py "abstract flowing shapes" \
  --output-dir ./abstract --num-images 4 --filename study
```
Produces `study.png`, `study_1.png`, `study_2.png`, `study_3.png`.

## Prompt Guidance

- Krea 2 responds well to a clear **subject + environment + (optional) pose/lighting/style** structure.
- Put things you *don't* want in `--negative-prompt` (e.g. `deformed hands, extra limbs, bad anatomy, watermark, text`), not as negations in the prompt.

## Troubleshooting

- **`Krea-2-Turbo not found in the HF cache` / `snapshot incomplete`** — the model isn't in the cache or was pruned. Populate it (Unsloth Images tab or `hf download unsloth/Krea-2-Turbo`) and rerun. The script intentionally does not auto-download.
- **`'uv' not found`** — install `uv` and rerun.
- **`at least 35 GB of memory must be available`** — the model is refused below 35 GB free memory. Close other apps and retry, or pass `--wait-for-memory 120` to poll every 10 s until memory frees up (fails after the timeout).
- **bfloat16 error on MPS** — the script already forces `float16`; if a custom run hits it, that's why.
- **Out of memory** — lower `--width`/`--height`, keep `--num-images` low, and close other GPU apps.

## Related Skills

- **`generate-image:generate-image`** — cloud version (AWS Bedrock Nova Canvas).
- **`generate-music:generate-music`**, **`podcast-generation:generate-podcast-audio-local`** — other local-generation skills using the same venv+CLI pattern.
