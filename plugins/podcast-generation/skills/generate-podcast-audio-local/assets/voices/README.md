# Bundled Demo Voices

These WAV files are the default reference voices used by the
`generate-podcast-audio-local` skill when no `--voices-dir` is provided.

## Source

The voices were downloaded from the **demo voices directory** of the
VibeVoice community fork:

- Repo: <https://github.com/vibevoice-community/VibeVoice>
- Path: `demo/voices/`
- Original files: `en-Alice_woman.wav`, `en-Frank_man.wav`, `en-Carter_man.wav`

They are the same demo voices that ship with the original
[Microsoft VibeVoice](https://github.com/microsoft/VibeVoice) repository.

## Files

| Bundled file | Original demo clip | Voice |
|---|---|---|
| `Alice.wav` | `en-Alice_woman.wav` | Woman |
| `Frank.wav` | `en-Frank_man.wav` | Man |
| `Carter.wav` | `en-Carter_man.wav` | Man |

## Processing

The clips were normalized with the skill's own
`scripts/normalize_voices.py` (a two-pass ffmpeg `loudnorm` with linear
gain — no compression):

- Integrated loudness: **−23 LUFS** (EBU R128 broadcast standard)
- True peak: **−1 dBTP**
- Sample rate: **24 kHz** (VibeVoice MLX model's native rate)

This is why they all sit at equal volume. Original levels varied by
nearly 10 LU — e.g. `en-Alice_woman.wav` measured −15.31 LUFS and
clipped at +0.10 dBTP, while the male clips measured about −24.9 LUFS.

## License

The demo voices are distributed under the **MIT License**
(© 2025 Microsoft), included verbatim in [`LICENSE`](LICENSE) in this
directory.

## Adding New Voices

Place new WAV reference clips in this directory (or a `--voices-dir` of
your choice), then prepare them to the same standard:

```bash
python3 ${SKILL_DIR}/scripts/normalize_voices.py --voices-dir ${SKILL_DIR}/assets/voices/
```

See `references/generate-podcast-audio-local.md` for the full voice
naming and loudness guidance.
