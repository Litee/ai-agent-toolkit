# Troubleshooting: Advanced Failure Modes

Load this reference when `SKILL.md` Common Errors doesn't cover the symptom — specifically for silent corruption, DRM-protected input, or missing codec builds.

## Silent Failures (exit 0 but output is bad)

ffmpeg occasionally exits with status 0 yet produces a corrupt, truncated, or zero-duration file (wrong codec mapping, truncated input, incompatible encoder/container pairing). Always verify the output before trusting the exit code.

- **Post-convert sanity check** — run `ffprobe -v error -show_entries format=duration,bit_rate -of default=nw=1 "$OUTPUT"`. A zero/missing duration, a duration much shorter than the source, or a bit_rate far below the one you requested is a red flag.
- **Duration diff** — compare source and destination:
  ```bash
  src_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN")
  dst_dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
  ```
  Alert if `abs(src_dur - dst_dur) > 1s` (allow a small tolerance for trim-silence / codec padding).
- **Force-decode playback test** — `ffplay -autoexit "$OUT"`, or headless: `ffmpeg -i "$OUT" -t 5 -f null -` to force the decoder to actually read the frames.
- **Canary container** — if output is consistently bad, re-run the conversion into a neutral container such as `.wav` to isolate whether the bug is in the encoder or the container muxer.
- **Remediation** — upgrade ffmpeg (`brew upgrade ffmpeg` on macOS), retry with `-c:a copy` to rule out transcoding, and file an upstream ffmpeg bug if the `.wav` canary is also corrupt.

## DRM-Protected Input

- **Symptom** — ffmpeg reports `Invalid data found when processing input`, `Operation not permitted`, or `moov atom not found` on files sourced from Apple Music, Audible, Spotify downloads, etc.
- **Diagnosis** — `ffprobe -v trace "$IN" 2>&1 | grep -iE "encrypt|drm|atom"` usually surfaces an `encrypted` stream atom. Apple FairPlay content uses `.m4p` (vs. plain `.m4a`); Audible uses `.aax` with activation-bytes.
- **Policy — this skill does NOT document DRM bypass.** If a file is DRM-protected, the supported path is to re-export or re-record it from the authorized application (e.g. macOS Music app → File → Convert) or to obtain a DRM-free equivalent. Do not attempt to circumvent DRM — it is a copyright-law and ToS concern that is outside this skill's scope.
- **Escalation** — if you are certain the file is NOT DRM-protected but ffmpeg still refuses (e.g. proprietary container metadata), try `ffmpeg -err_detect ignore_err -i "$IN" ...` as a last-resort diagnostic. Output may still be unusable; treat the result as best-effort only.

## Unsupported Codec (decoder or encoder missing)

- **Symptom** — `Unknown encoder 'libopus'` or `Decoder (codec libaom-av1) not found for input stream #0:0`. The local ffmpeg build was compiled without that codec.
- **Diagnosis** — inspect the codec table:
  ```bash
  ffmpeg -codecs 2>/dev/null | grep -iE "^\s*D|^\s*.E" | grep -i <codec>
  ```
  The `D.....` column marks decoders and `..E...` marks encoders. `ffmpeg -encoders` and `ffmpeg -decoders` also list everything available in the current build.
- **Remediation** — on macOS with Homebrew, `brew install ffmpeg` covers most common codecs. For libfdk_aac (non-free) use `brew install ffmpeg --with-fdk-aac` or install via MacPorts. On Linux, use a distro package that ships the needed codec, or a static build from https://johnvansickle.com/ffmpeg/ which bundles virtually everything.
- **Fallback substitution** — if the target codec is unavailable, swap to a widely-supported equivalent:
  - AAC via built-in `-c:a aac` (always present) instead of `libfdk_aac`
  - Vorbis (`-c:a libvorbis`) instead of Opus when libopus is missing
  - `flac` or `wav` as a lossless fallback (always present)
- **Escalation** — before silently swapping, tell the user: "this ffmpeg build lacks `<codec>`; would you like me to proceed with `<fallback_codec>` at approximately the same quality?" and wait for confirmation.

Always run the ffprobe duration-diff check after any conversion — it catches roughly half of the silent-failure modes with one command.
