# generate-image-local — Reference

Deep-dive for the Krea 2 Turbo local generation skill. Read this before modifying the skill.

## Model

- **Model**: `unsloth/Krea-2-Turbo` (12B diffusion transformer, distilled/TDM checkpoint, 8 steps, guidance off).
- **Pipeline**: `diffusers.Krea2Pipeline` (dev diffusers `0.39.0.dev0` — **must be installed from git**; the class is not in a stable release yet).
- **Cache location**: `~/.cache/huggingface/hub/models--unsloth--Krea-2-Turbo/snapshots/<revision>/`
  - The snapshot is a diffusers-format directory: `model_index.json`, `transformer/`, `vae/`, `text_encoder/` (Qwen3VL), `tokenizer/`, `scheduler/`.
  - The repository is license-gated on HF; the user must have accepted the license and logged in (`hf auth whoami` shows the user) before a cache exists.

## Inference call

```python
import torch
from diffusers import Krea2Pipeline

pipe = Krea2Pipeline.from_pretrained(model_dir, torch_dtype=torch.float16, local_files_only=True)
pipe = pipe.to("mps")
image = pipe(
    prompt=prompt,
    negative_prompt=negative_prompt,   # optional
    height=height,                     # multiple of 16
    width=width,                       # multiple of 16
    num_inference_steps=8,             # distilled: keep low
    guidance_scale=0.0,                # distilled: guidance disabled
    generator=torch.Generator("mps").manual_seed(seed),  # optional
).images[0]
image.save(out_path)
```

### Device / dtype notes

- **Device is `mps`** — Apple Silicon only. CUDA is out of scope for this skill.
- **`torch.float16`**, not bf16: `bfloat16` is unreliable on MPS.
- The first generation on a fresh load can be slow (model load + compile); later generations are fast.

## Script architecture

`scripts/generate_image_local.py`:

1. `parse_args` — prompt (required), `--output-dir` (required), `--filename`, `--steps`, `--width`, `--height`, `--negative-prompt`, `--seed`, `--num-images`, `--model-path`.
2. **venv bootstrap** (`ensure_venv`): if `/tmp/krea-image-venv` doesn't exist, `uv venv` + `uv pip install --python <venv> torch transformers accelerate safetensors pillow git+https://github.com/huggingface/diffusers.git`. Idempotent via a `.deps-installed` marker — delete the marker to force a reinstall.
3. **re-exec** into the venv python (`os.execv` with `KREA_IN_VENV=1`) so `torch`/`diffusers` are importable.
4. `generate` — resolve model dir (explicit `--model-path`, else newest snapshot under the cache; fail clearly if absent/pruned), load pipeline with `local_files_only=True`, generate `--num-images` images using `seed + i` per image, save `{filename}{_i}.png` into `--output-dir`.

### No sidecar prompt files

The user's earlier "sidecar `.txt` with POSITIVE/NEGATIVE prompts" behavior belongs to the *agent* using this skill, not the skill itself. If that's requested for a batch, write the `.txt` sidecars as part of the agent's workflow — do not change the script to emit them.

## Memory gate

- The script refuses to load the model when fewer than **35 GB** of memory are available (headroom for the 12B transformer + Qwen3VL encoder on unified memory).
- Measured via `psutil.virtual_memory().available` on the host.
- **`--wait-for-memory <seconds>`**: if below the threshold, poll every 10 s (up to the timeout) until enough memory is available, then load; on timeout, abort before loading.
- Without `--wait-for-memory` (or a value ≤ 0), insufficient memory fails immediately with a clear message.

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `Krea-2-Turbo not found in the HF cache` | Cache dir absent | `hf download unsloth/Krea-2-Turbo` or Unsloth Images tab |
| `Model snapshot incomplete (missing model_index.json)` | Snapshot pruned (blobs may remain) | Re-fetch the model; snapshot must be restored |
| `'uv' not found` | uv missing | `https://docs.astral.sh/uv/` |
| bf16/`mps` dtype errors | User changed dtype | Keep `torch.float16` |
| `< 35 GB available` | Not enough free memory | Close apps, or `--wait-for-memory <seconds>` |
| OOM | Resolution too high / too many images | Lower `--width`/`--height`, lower `--num-images` |

## Why offline-only?

The user explicitly chose "assume present, fail clearly": the skill never downloads the model, never falls back to a cloud endpoint, and never talks to the Unsloth Studio server. That keeps behavior deterministic and local.

## Related

- Cloud variant: `plugins/generate-image/skills/generate-image/SKILL.md` (Bedrock Nova Canvas).
- The `uv` + stable `/tmp` venv pattern mirrors `plugins/podcast-generation/skills/generate-podcast-audio-local/` (VibeVoice MLX) and the generate-music-local skill.