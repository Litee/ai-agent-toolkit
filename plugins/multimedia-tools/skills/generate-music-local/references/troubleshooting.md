# MiniMax-Music3 MLX — Troubleshooting

Failure modes and fixes for the `generate-music-local` skill. The native CLI is
`generate.py` (run inside the downloaded repo's Python 3.11 venv). The helper
`scripts/generate_music.py` wraps setup + invocation.

## Setup / install failures

### `command not found: hf`
The Hugging Face CLI is missing. Install it:
```bash
pip install -U "huggingface_hub[cli]"     # provides the `hf` binary
# or
brew install huggingface-cli
```
Then verify with `hf --help`.

### `python3.11: command not found`
The pinned `mlx==0.30.6` needs Python 3.11–3.13. Install 3.11:
```bash
brew install python@3.11
```
Confirm with `python3.11 --version`.

### `pip install -r requirements.txt` fails / resolver errors
Requirements are pinned: `mlx==0.30.6`, `mlx-metal==0.30.6`, `numpy>=2.0,<3`,
`tokenizers>=0.22,<0.23`. Use a **fresh** venv on Python 3.11–3.13:
```bash
python3.11 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
```
On Apple Silicon, `mlx`/`mlx-metal` install prebuilt wheels; a source build here
usually means the wrong Python arch — confirm `uname -m` is `arm64` and the venv
python is a framework build.

### `ModuleNotFoundError: mlx` at runtime
You ran `generate.py` with the system Python instead of the venv. Activate first:
```bash
source .venv/bin/activate
python generate.py …
```
(The helper calls the venv python directly, so it avoids this.)

### `ModuleNotFoundError: No module named 'minimax_mlx_model'`
`generate.py` does `from minimax_mlx_model import …`, which needs the repo directory on
`sys.path`. This fails when `generate.py` is launched so its own folder isn't importable —
most commonly when you run raw `generate.py` in a checkout where it is a symlink to a
content-hashed blob (a bare Hugging Face **hub-cache checkout**, i.e. `hf download`
*without* `--local-dir`), because Python then resolves `sys.path[0]` to the `blobs/` dir,
where files are named by hash rather than module name. Pointing `--model-dir` at an
HF-cache **snapshot** (a directory of real files, optionally reached through a symlink)
is fine — the skill helper sets `PYTHONPATH` and runs cleanly. Fixes, in order of
preference:

1. **Download with `--local-dir`** so the repo is a normal directory (no symlinks):
   ```bash
   hf download PocketAiHub/MiniMax-Music3-MLX --local-dir MiniMax-Music3-MLX
   ```
2. **Keep the hub-cache checkout** and run with `PYTHONPATH` set to the snapshot dir:
   ```bash
   SNAP=~/.cache/huggingface/hub/models--PocketAiHub--MiniMax-Music3-MLX/snapshots/<commit>
   PYTHONPATH="$SNAP" .venv/bin/python "$SNAP/generate.py" --prompt "…" --lyrics "[Instrumental]" --seconds 30
   ```
3. **Use the skill helper** — `scripts/generate_music.py` sets `PYTHONPATH`/cwd to the real
   model directory automatically, so just point `--model-dir` at the snapshot (or a symlink
   to it) and it works without manual `PYTHONPATH`.

### Download interrupted / partial
Re-run the exact command; `hf download --local-dir <dir>` resumes:
```bash
hf download PocketAiHub/MiniMax-Music3-MLX --local-dir MiniMax-Music3-MLX
```
Repo + weights are ~12 GB. Verify `generate.py` and the `text_encoders/`,
`diffusion_models/`, `vae/` folders exist before generating.

## Runtime failures

### Out of memory / "Application terminated" / heavy swap thrashing
This port is memory-intensive and runs batch size 1. With ≤32 GB you may OOM on
long/high-step clips. Mitigations, in order:
1. Lower duration: `--seconds 10` (or 20).
2. Lower steps: `--steps 10`.
3. Close memory-heavy apps (browsers, containers, Xcode).
4. Ensure ≥48 GB unified memory for 60 s @ 30 steps.

Watch Activity Monitor → Memory Pressure; if it goes red, reduce `--seconds`.

### `RuntimeError: MiniMax-Music3 produced silent audio`
The pipeline produced near-zero RMS. Usually a bad seed/prompt combo. Retry with a
different `--seed`.

### `RuntimeError: MiniMax-Music3 produced non-finite audio`
NaN/Inf in the waveform. Retry with a different `--seed`; if it persists across
seeds, the model dir or weights may be corrupted — re-download.

### `RuntimeError: ... produced an implausible peak (X.XXX)`
Peak > 8.0 — degenerate output. Retry with a different `--seed`.

### `RuntimeError: MiniMax-Music3 DAV decoder produced a collapsed stereo channel in NN% of the audio`
This is the **diagnosed stereo-collapse signature**: one channel collapses to the
other. The runtime rejects it automatically (threshold ≥75%). Fix: change
`--seed` and re-run; a different seed almost always clears it. If it recurs on many
seeds, your MLX version may differ from the pinned one — pin `mlx==0.30.6`.

## Verifying output health (signal check)

A healthy render passes these checks. Quick format/duration check:
```bash
ffmpeg -i song.wav 2>&1 | grep -E "Duration|Hz"
# expect: Duration ~ requested, 44100 Hz, stereo
```
Deeper signal check in Python:
```python
import wave, numpy as np
with wave.open("song.wav", "rb") as w:
    n, sr, ch = w.getnframes(), w.getframerate(), w.getnchannels()
    data = np.frombuffer(w.readframes(n), dtype="<i2").reshape(-1, ch).astype(np.float32) / 32768.0
dur = n / sr
l, r = data[:,0], data[:,1]
peak = float(np.max(np.abs(data)))
rms = float(np.sqrt(np.mean(data**2)))
corr = float(np.corrcoef(l, r)[0,1])
clipped = int(np.sum(np.abs(data) >= 0.999))
print(f"duration={dur:.2f}s sr={sr} ch={ch} peak={peak:.3f} rms={rms:.4f} stereo_corr={corr:.3f} clipped={clipped}")
```
Reference healthy values (from the repo's 60 s example): duration ≈ 59.99 s,
channel peaks ≈ 0.97–0.99, stereo correlation ≈ 0.71, **0** clipped samples, **0%**
collapsed one-second blocks. For your own clips, expect: peak < 1.0, non-trivial
stereo correlation (well above 0), and zero clipped samples.

Repo self-tests (lightweight, no generation):
```bash
python -m unittest tests/test_minimax_mlx_model.py
```

## Platform / capability checks

- **Not Apple Silicon / not macOS 14+**: this port will not run. There is no
  fallback; use a different machine or the upstream ComfyUI/PyTorch path.
- **Intel Mac / Linux / Windows**: unsupported by design.
- Confirm arch: `uname -m` → `arm64`.

## License & commercial use

- Weights, this package, and generated outputs are under the **MiniMax-Music3
  Community License** (repo `LICENSE`). It has an acceptable-use policy and
  commercial-use terms.
- Review it **before** downloading or deploying. Commercial use may require
  separate terms from MiniMax.
- You are responsible for rights to prompts, lyrics, and generated content.
