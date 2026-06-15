# Fetching Captions and Transcripts

## Canonical invocation

```bash
YT=/tmp/yt-tools-venv/bin/yt-dlp

# Download auto-generated English captions as VTT
$YT --skip-download --write-auto-subs --sub-langs "en" --sub-format vtt \
    --no-warnings --quiet \
    -o "/tmp/caps/%(id)s" \
    "https://www.youtube.com/watch?v=xxxxxxxxxxx"
# Produces /tmp/caps/<id>.en.vtt
```

For plaintext conversion (dedup overlapping cues, optional timestamps), use the `convert-vtt-to-text` skill. This skill downloads raw VTT only; it does not convert captions to plaintext.

## Multiple languages in one run

```bash
# English + Spanish auto-generated
$YT --skip-download --write-auto-subs --sub-langs "en,es" --sub-format vtt \
    -o "/tmp/caps/%(id)s" URL
# Produces <id>.en.vtt and <id>.es.vtt
```

## Manual vs auto-generated

```bash
# Prefer manually-uploaded captions
$YT --skip-download --write-subs --sub-langs "en" --sub-format vtt \
    -o "/tmp/caps/%(id)s" URL

# Try manual first, fall back to auto (two separate calls in a script)
$YT --skip-download --write-subs --sub-langs "en" -o "/tmp/caps/%(id)s" URL \
    || $YT --skip-download --write-auto-subs --sub-langs "en" -o "/tmp/caps/%(id)s" URL
```

## List available caption tracks

```bash
$YT --list-subs URL
```

## Convert existing VTT to other formats

```bash
# Via yt-dlp post-processor
$YT --skip-download --write-auto-subs --sub-langs "en" --convert-subs srt \
    -o "/tmp/caps/%(id)s" URL
```

## Live chat replay

```bash
$YT --skip-download --write-subs --sub-langs "live_chat" \
    -o "/tmp/caps/%(id)s" URL
# Produces <id>.live_chat.json with timestamped messages
```

## Gotchas

- **`--sleep-subtitles` vs `--sleep-interval`:** `--sleep-interval` and `--min/max-sleep-interval` do NOT apply to subtitle downloads — only to video downloads. Use `--sleep-subtitles 5` to add a sleep before each subtitle file fetch. Combine with `--sleep-requests` for the metadata extraction phase. Omitting this is the most common cause of 429s in caption batch jobs.
- **Empty VTT files despite `rc == 0` and captions confirmed in JSON (PO Token enforcement):** YouTube requires a Proof of Origin Token (POT) on subtitle endpoints for the `web` client. Symptom: probe succeeds, subtitle URLs appear in JSON, but downloaded VTT files are empty or 0 bytes. Before treating it as a permanent CDN gap: (1) try `--extractor-args "youtube:player_client=tv,mweb"` — `tv,mweb` provides a fallback chain; the `tv` client does not require a POT; (2) if the failure is sustained across many videos, install the PO Token provider plugin: `pip install bgutil-ytdlp-pot-provider`. Keep yt-dlp up to date — POT handling improves with each release.
- VTT auto-captions have overlapping cue windows and inline tag noise. Convert to plaintext with the `convert-vtt-to-text` skill before passing captions to an LLM or text index.
- Language code variants: try `en` first, then `en-US`, then `en-orig` (auto-translated source).
- `--sub-langs "all,-live_chat"` downloads every language except live chat.
- Timeout per video in subprocess calls: use 120 s minimum for long videos.
- **JS challenge (`n` parameter):** `--skip-download` still resolves video format URLs to locate subtitle tracks, which can trigger the `n` parameter JS challenge under certain rate-limit/session conditions. If you see `n challenge solving failed` errors, add `--remote-components ejs:github`. Try without it first — it only fires under specific conditions and adds overhead.

## Distinguishing absent captions from transient errors

The reliable discriminator is `yt-dlp -J --skip-download <URL>` (exit code + JSON fields):

- `rc != 0` with `ERROR:` on stderr — transient error (429, bot-check). These are retry-worthy; feed them to the adaptive throttle. Note: age-gate and members-only errors also produce `rc != 0` but are not retry-worthy without adding `--cookies-from-browser`; they will land in `failed.txt` for manual triage.
- `rc == 0` with `subtitles == {}` and `automatic_captions == {}` — the video genuinely has no captions. Do not retry.
- `rc == 0` with non-empty subtitle dicts but the requested language absent — language mismatch. Do not retry.
- `rc == 0` (probe succeeded, captions confirmed) but the VTT download produced no files — CDN gap or private endpoint. Not a rate-limit signal. Status is `download_failed`; do not feed the throttle.

**Warning:** do NOT string-match `[info] There are no subtitles for the requested languages` on stderr. The `-J` flag suppresses that message; the JSON fields (`subtitles`, `automatic_captions`) are the durable contract.
