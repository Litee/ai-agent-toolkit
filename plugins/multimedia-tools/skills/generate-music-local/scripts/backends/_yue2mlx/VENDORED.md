# Vendored upstream record

This file records **exactly which upstream revisions this backend's runtime came
from, what was changed, and how to re-vendor**. It exists so we can later pull
upstream improvements, or fork the runtime into our own repository, without
re-deriving any of this.

Vendored: **2026-09-15**
Verification: `selfcheck_torch_free.py` (run it after any re-vendor).

## Upstream sources

| What | Upstream | Pinned revision | Licence |
|---|---|---|---|
| MLX inference runtime | [vanch007/mlx-Yue](https://github.com/vanch007/mlx-Yue) | `9253ed133343406947bde7b67d43c7a63fb39d99` | Apache-2.0 |
| Planning/protocol layer | `yue2_infer-0.1.5-py3-none-any.whl`, shipped inside [m-a-p/YuE2-3B](https://huggingface.co/m-a-p/YuE2-3B) | snapshot `29b3558dd46954a0cd9021dc76d5c91864a0f1c7` | see `licenses/` |
| YuE2-3B weights | [m-a-p/YuE2-3B](https://huggingface.co/m-a-p/YuE2-3B) | `1a96eca688d6ae5d7f0feb88573fec89920fcd19` | CC BY-NC 4.0 |
| YuE2-Vae weights | [m-a-p/YuE2-Vae](https://huggingface.co/m-a-p/YuE2-Vae) | `95535e72a97bc0f09b8ada125d26b4009428c0e8` | CC BY-NC 4.0 |
| YuE reference implementation | [multimodal-art-projection/YuE](https://github.com/multimodal-art-projection/YuE) | `92a73cc7652fcc1f937855e4b765e0a0edd7ff2e` | Apache-2.0 |
| GGUF weight set consumed at runtime | [audio-cpp/Yue2-3B-GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF) | snapshot `eb116220931de5f373d024d48800338178c7de51` | cc-by-nc-4.0 |

The GGUF repack and mlx-Yue's own converter both target the **same** YuE2-3B
revision (`1a96eca6…`), which is why the provenance files in this skill
hash-match the pinned source.

### Why the repo is fetched as individual files, not a tarball

The `vanch007/mlx-Yue` repository is **~580 MB** because it ships
`docs/audio/fullsong/*.mp3` demo renders. Fetching the archive to get eleven
Python files is wasteful, so re-vendoring pulls just the sources from
`raw.githubusercontent.com` at the pinned SHA (see below). Nothing at install
time fetches the repo at all — the runtime is vendored.

## What was vendored

### `runtime/` — from `src/lyra/` at the pin

| File | Upstream sha256 (16) | Vendored sha256 (16) | Changed lines | Change |
|---|---|---|---|---|
| `__init__.py` | `5a8c62f6eb777605` | `16a9c7ded81721d2` | 4 | lazy imports repointed |
| `pipeline.py` | `1549bc6460b5e795` | `e256cc927d1d5d41` | 21 | imports + provenance hashing made torch-free |
| `ar.py` | `4f2f5ce2ff812fa6` | `5e32e0d745aa05ae` | 9 | group size via constant + imports |
| `nar.py` | `da2e525d0cb65ce8` | `d1d372272f8b38d3` | 2 | import repointed |
| `vae.py` | `c92fdfd145ba23d2` | `c92fdfd145ba23d2` | 0 | **unchanged** |
| `sampling.py` | `5b74067cccad4d51` | `e029f6ae992e8dc9` | 2 | import repointed |
| `measure.py` | `8fd8dc05a349d26c` | `62fb6d4a51ee1026` | 35 | guard rewritten (see below) |
| `runtime.py` | `9b5815038d438720` | `9b5815038d438720` | 0 | **unchanged** |
| `conversion.py` | `70a39502c5625345` | `58341c711465ecf9` | 18 | group size 32 + imports |
| `artifacts.py` | `f3895d9eaf01dece` | `dc9aca13bcfe6ed0` | 6 | imports repointed |
| `checkpoints.py` | `372495fce3489b33` | `db1e1bc650601179` | 2 | import repointed |

**Total: 99 changed lines** against upstream. The other two files (`vae.py`,
`runtime.py`) are byte-identical, so upstream bugfixes to them apply cleanly.

### `core/` — torch-free planning layer

| File | Origin | Change |
|---|---|---|
| `protocol.py` | `yue2/protocol.py` | verbatim (torch-free upstream) |
| `storage.py` | `yue2/storage.py` | verbatim (its `transformers` import is function-local) |
| `progress.py` | `yue2/progress.py` | verbatim |
| `tokenization_yue2.py` | `yue2/tokenization_yue2.py` | verbatim |
| `ar_keys.py` | `yue2/fast.py` lines 33–54 | extracted; only these functions are used |
| `pipeline.py` | `yue2/pipeline.py` | **rewritten torch-free** (below) |

## The four substantive changes

1. **Native Q8_0 group size (32).** `_QUANTIZATION_GROUP_SIZE` 64 → 32 in
   `runtime/conversion.py`, and `runtime/ar.py` now reads that constant instead
   of a hardcoded `64`. mlx-Yue's upstream converter dequantises to bf16 and
   re-quantises at group 64; audio.cpp's Q8_0 blocks are 32-element groups, and
   MLX unpacks them natively into exactly that affine layout with the ggml fp16
   scale preserved bit-for-bit — so group 32 lets us consume the GGUF with no
   dequantisation and no second, lossy re-quantisation.

2. **Memory guard on true usage** (`runtime/measure.py`). Upstream aborts on
   `system_memory_pressure_level != 1` and on `>64 MiB` new swap-out. Both
   describe the whole machine, so unrelated processes killed healthy renders: a
   run holding only a **6.31 GiB footprint with 21 GiB available** was aborted at
   pressure level 2, and 110 MiB of swap appeared from work we had not started.
   The guard now fails closed on the process's own **physical footprint**
   (`task_info` phys_footprint — what `footprint -p` reports) plus a **2 GiB
   genuinely-available** floor. Ambient signals are still sampled into the
   resource trace as evidence, but are never fatal.

3. **Imports repointed** `yue2.*` → `..core.*` (the 53 lines across nine files).

4. **`core/pipeline.py` rewritten torch-free.** mlx-Yue imports
   `SemanticResult`, `SymbolicPlan` and `YuE2Pipeline` from `yue2/pipeline.py`,
   which imports torch — so mlx-Yue's advertised "torch-free runtime" is not true
   upstream, and its declared dependencies omit `yue2` entirely (it is not on
   PyPI). The MLX runtime overrides 15 of that module's 21 methods, and every
   torch use sits in `__init__`/`_load_model`/`_generate`/`synthesize`/`decode` —
   all replaced. Keeping only `SymbolicPlan`, `SemanticResult`, `SongResult`,
   `_request`, `_status`, `plan`, `generate_semantic` and `effective_config`
   removes torch completely. Proven, not assumed: see `selfcheck_torch_free.py`.

5. **Two latent `yue2` dependencies in `runtime/pipeline.py`.** Upstream hashes
   the installed `yue2` package for provenance
   (`Path(__import__("yue2").__file__).parent`), which raises
   `ModuleNotFoundError` in a runtime that does not install it; it now hashes the
   vendored `core/` directory instead. It also probed
   `importlib.metadata.version("mlx-yue")` for its runtime record, which raises
   `PackageNotFoundError` because the runtime is vendored rather than installed;
   it now reports `"mlx-yue": "vendored"`. Both were found by running the
   backend from a clean state — they are invisible in a tree where `yue2` and
   `mlx-yue` happen to be installed.

## Not vendored

`cli.py`, `commands.py`, `bart.py`, `mert.py`, `music_tools/`, `transcription/`,
`oracle/`, `docs/`, `examples/`, `reports/` — CLI/transcription/cover features and
project scaffolding. Only the generation path is vendored.

## Licences

| File in `licenses/` | Covers |
|---|---|
| `mlx-Yue-Apache-2.0.txt` | the vendored MLX runtime |
| `YuE-upstream-Apache-2.0.txt` | the upstream YuE implementation the protocol follows |
| `YuE2-weights-CC-BY-NC-4.0.txt` | YuE2-3B / YuE2-Vae / GGUF weights — **non-commercial** |
| `stable-audio-tools-MIT.txt` | Oobleck VAE (Stability AI) |
| `SnakeBeta-NVIDIA-MIT.txt` | SnakeBeta / BigVGAN (NVIDIA) |
| `THIRD_PARTY_NOTICES.md` | upstream's own third-party summary |

**The binding constraint is CC BY-NC 4.0 on the weights: commercial use of the
model or its outputs is blocked.** The code (Apache-2.0) and the bundled
VAE/SnakeBeta components (MIT) are permissive. Each vendored file keeps its
upstream module docstring; per Apache-2.0 §4(b) this file is the prominent notice
that the files were changed.

## Re-vendoring

```bash
PIN=9253ed133343406947bde7b67d43c7a63fb39d99   # or a newer upstream SHA
cd runtime
for f in __init__ pipeline ar nar vae sampling measure runtime conversion artifacts checkpoints; do
  curl -sfLO "https://raw.githubusercontent.com/vanch007/mlx-Yue/$PIN/src/lyra/$f.py"
done
```

Then re-apply the four changes above and re-run `selfcheck_torch_free.py`. To see
what upstream changed since this vendor, diff the vendored files against a fresh
fetch at a newer SHA; the three byte-identical files (`vae.py`, `runtime.py`, and
`core/*` except `pipeline.py`) will show upstream fixes directly.

## Tested configuration

Verified on: Apple Silicon **M5 Pro**, **64 GB**, **macOS 26.6.2**.
Not verified: other macOS versions, 24/32 GB machines, other Apple Silicon
generations. Treat those as untested rather than supported.
