# MiniMax-Music3 MLX — Parameter Reference

Detailed guidance for the `generate.py` arguments used by the `generate-music-local`
skill. The native CLI is:

```bash
python generate.py --prompt "…" (--lyrics "…" | --lyrics-file lyrics.txt)
  [--seconds N] [--steps N] [--seed N] [--model-dir DIR] [--output FILE.wav]
```

## `--prompt` (required)

A musical direction / caption. This is the strongest steer on style. Include as
many of these as useful:

- **Genre / style**: `lo-fi hip hop`, `synth-pop`, `cinematic ambient`, `rock and roll`, `jazz trio`, `EDM`, `classical string quartet`
- **Mood / energy**: `mellow`, `high-energy`, `dreamy`, `aggressive`, `uplifting`
- **Tempo**: explicit BPM, e.g. `84 BPM`, `148 BPM`
- **Instrumentation**: `warm pads`, `crunchy guitars`, `boogie piano`, `live drums`, `deep sub bass`, `swelling strings`
- **Vocal style** (if lyricized): `breathy female vocal`, `gritty male vocal`, `soft harmonies`

Examples:

```
Lo-fi hip hop, mellow piano, soft vinyl crackle, 84 BPM
High-energy rock and roll, gritty male vocal, crunchy guitars, boogie piano, live drums, punchy bass, 148 BPM
Dreamy synth-pop, breathy female vocal, warm pads, 100 BPM
Cinematic ambient, swelling strings, deep sub bass, 70 BPM
```

For precise, section-aware control, write the prompt as a **Structured Caption**
(Global Metadata / Vocal Details / Arrangement) — see *Fine-Grained Music Control*
below.

> Prompts and section tags are **generative guidance, not guarantees**. Lyrics,
> tempo, instrumentation, and song structure may vary from the caption.

## `--lyrics` vs `--lyrics-file` (exactly one required)

Mutually exclusive. Use one or the other.

### `--lyrics` (inline string)

Good for short input. For instrumentals, pass the literal token:

```bash
--lyrics "[Instrumental]"
```

### `--lyrics-file` (UTF-8 path)

Recommended for multi-section songs. Supports bracketed section tags that act as
soft structure hints:

```
[Verse]
Neon on the dashboard, midnight in the street
Engine keeps on rumbling to a backbeat

[Chorus]
Turn it up, let the good times roll
Fire in the speakers, thunder in your soul

[Bridge]
City lights are bleeding into blue
```

- Tags are recognized case-insensitively: `[Intro]`, `[Verse]`, `[Pre-Chorus]`,
  `[Chorus]`, `[Post-Chorus]`, `[Bridge]`, `[Instrumental]`, `[Solo]`, `[Outro]`.
- Blank lines separate lines; the model reads line breaks as phrasing.
- For a fully instrumental track, the file may contain just `[Instrumental]`.

## Fine-Grained Music Control

The model takes **two complementary inputs**, and using both well is what separates a
generic clip from a song that follows your intent (adapted from the upstream
MiniMax-Music3 model card):

- **Lyrics** — the words to be sung; may include explicit section tags (below) that
  hint at song structure.
- **Music description** — the musical style, emotional progression, vocal
  performance, instrumentation, arrangement, and production profile.

For the most precise control, write the music description as a **Structured Caption**
with three labelled sections.

### Section tags (lyrics)

Recognized case-insensitively; the model treats them as soft structure hints:
`[Intro]`, `[Verse]`, `[Pre-Chorus]`, `[Chorus]`, `[Post-Chorus]`, `[Bridge]`,
`[Instrumental]`, `[Solo]`, `[Outro]`. For a fully instrumental track, the lyrics file
may contain just `[Instrumental]`.

### Structured Caption (music description)

Three sections, each with its own fields:

- **Global Metadata**: genre, subgenre, BPM, key, scale, emotional progression,
  listening scenario, production profile.
- **Vocal Details**: vocal gender, timbre, performance style, harmony, backing
  vocals, vocal effects.
- **Arrangement**: primary and secondary instruments, section-level instrument
  evolution, groove, bass, percussion, textures, spatial effects.

This lets the model follow not just a global style but the musical development of the
song over time (e.g. a sparse verse that builds into a full chorus).

### Example — concise music description

```
Genre: acoustic pop. BPM: 96. Key: C major. Warm and intimate, building gently into
the chorus. Vocals: soft female lead, close and breathy, light stacked harmonies in
the chorus. Arrangement: fingerpicked guitar and soft piano; brushed drums and
upright bass enter in the chorus.
```

### Example — Structured Caption

```
Global Metadata: dream-pop, 112 BPM, F# minor, natural minor; emotional progression
wistful verse -> euphoric chorus; listening scenario late-night drive; production
profile polished, wide stereo, analog warmth.
Vocal Details: female, breathy timbre, intimate performance, soft harmonies, no
backing vocals, subtle reverb.
Arrangement: primary pulsing synth bass + bright piano; secondary airy pads; section
evolution verse sparse -> chorus full with strummed guitar; groove four-on-the-floor;
bass sub-heavy; percussion crisp claps; textures shimmering arpeggios; spatial
ping-pong delay on the chorus hook.
```

### Tips

- A plain one-line description also works (the port accepts it), but a Structured
  Caption gives noticeably tighter control over vocals and arrangement.
- To expand a short idea into a Structured Caption, the upstream project ships a
  `music-caption-rewriter` skill: `npx skills add MiniMax-AI/MiniMax-Music3
  --skill music-caption-rewriter` (needs network; optional).
- The model natively supports songs up to ~5 minutes, so 2–4 min targets are safe.
- Section tags and descriptions are **generative guidance, not guarantees** — tempo,
  key, instrumentation, and structure may still vary.

## `--seconds` (default 60, range 10–300)

Target clip duration in **seconds** (float accepted, e.g. `45.5`).

- **Minimum 10**, **maximum 300**.
- Longer durations need more memory and time. 60 s @ 30 steps takes several minutes
  on Apple Silicon; 10–20 s is enough for a quick draft.
- Generation runs autoregressively, so very long clips are the most memory- and
  time-intensive.
- **Actual duration is approximate, often shorter than requested.** The AR stage may
  stop before the requested frame count (especially with short lyrics or a short
  request), so a `--seconds 15` prompt can yield ~11 s of audio. The pipeline truncates
  the decoded waveform to `context_frames / 25 * 44100` samples. To hit a target length,
  request a little more (e.g. ask for 20 s to land near 15 s). Long requests (e.g. 60 s)
  track the request closely (the reference example: 59.99 s for 60 s). Long clips
  (120–240 s) usually land close to the request too — but the shortfall is
  seed/prompt-dependent: the same 180 s request has produced 179.99 s and 176.88 s in
  this port. Treat duration as approximate, not an exact target.
- **`[Instrumental]` (minimal lyric) shortfall is severe and seed-dependent.** With the
two-token `[Instrumental]` lyric input, the AR stage can stop very early: measured for a
180 s request — 33.8 s (seed 20260303) and 69.7 s (seed 555777). To land an instrumental
in the 2–4 min window, request `--seconds 300` (the max) with a fresh seed (measured
→ 197.2 s), then check the actual duration and re-roll the seed if it's still short.
Duration swings heavily with seed even for lyricized tracks, so always verify the real
duration with ffprobe before calling a track done.

## `--steps` (default 30, range 1–30)

Flow-DiT (flow-matching) sampling steps.

- **1–30**. Higher = better fidelity and coherence; lower = faster but rougher.
- **30** is the quality default used for the reference example.
- **10–15** is a reasonable draft setting for quick iteration.
- There is no benefit (and wasted time) above 30.

Trade-off quick reference:

| Goal | seconds | steps |
|------|---------|-------|
| Fast sanity check | 10 | 10 |
| Draft to judge style | 20–30 | 15 |
| Publish-quality clip | 60 | 30 |
| Long track | up to 300 | 30 |

## `--seed` (default 7, range 0 – 2³¹−1)

Integer seed for reproducibility.

- Deterministic **for the pinned runtime + MLX versions** in this repo.
- **Does not** match PyTorch/ComfyUI sample-for-sample (different RNG backends).
- If a run produces silent / non-finite / stereo-collapsed audio, change the seed
  and retry — the DAV decoder auto-rejects collapsed output, so a new seed usually
  succeeds.

## `--model-dir` (default: auto-detected HF cache snapshot)

Path to the downloaded repo (must contain `generate.py`, `minimax_mlx_model.py`,
and the `text_encoders/`, `diffusion_models/`, `vae/` weight subfolders).

- The helper `scripts/generate_music.py` **auto-detects** the weights from your
  Hugging Face hub cache (`~/.cache/huggingface/hub/models--PocketAiHub--MiniMax-Music3-MLX/snapshots/<commit>`),
  so you can usually **omit `--model-dir` entirely** — no `~/Models` symlink needed.
- Pass `--model-dir` to override (e.g. a `--local-dir` checkout). The helper
  resolves symlinks and sets `PYTHONPATH` so the repo's own modules stay importable.
- The native `generate.py` CLI defaults to its own folder, so you can `cd` into
  the repo and omit it.

## `--output` (default `song.wav`)

Output file path. Written as **44.1 kHz, 16-bit, stereo PCM WAV** (`wave` module,
2 channels, sampwidth 2, `SAMPLE_RATE = 44100`). The path's parent directory is
created automatically if missing. Sample values are clipped to `[-1, 1]` and
scaled down if peak exceeds `0.99`.

## Output format notes

- Container: WAV (`RIFF`).
- Sample rate: 44,100 Hz (CD quality).
- Bit depth: 16-bit signed integer (`<i2`).
- Channels: 2 (stereo).
- If the peak exceeds `0.99`, the whole waveform is normalized to `0.99` to avoid
  clipping.
- Non-finite or silent output raises before writing; ≥75% stereo-collapsed output
  raises and is rejected.

## Determinism & variation

- Same `--prompt` + `--lyrics` + `--seconds` + `--steps` + `--seed` on the same
  machine/runtime reproduces the same audio.
- Changing any of those changes the result.
- The INT8 (tensorwise + ConvRot) weights are fixed copies of the Comfy-Org repack;
  quality is bounded by that quantization.
