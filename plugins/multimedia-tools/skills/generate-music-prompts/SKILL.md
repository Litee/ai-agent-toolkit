---
name: generate-music-prompts
description: Use when writing or improving a music-generation prompt, style caption, musical brief, or song lyrics for an AI music tool (local MiniMax-Music3 / YuE2, or Suno-style platforms). Triggers on "write a music prompt", "music brief", "style caption for a song", "song lyrics / structure a song / section tags", "iterate or improve a music prompt", "variations of a prompt", "improve a generated song", "AI music direction". Produces a compact structured prompt and optionally a lyric skeleton, tuned for directed iteration (brief, batch, change one variable per round) rather than one-shot generation.
---

# Generate Music Prompts

Write prompts as a **brief**: a small set of compatible constraints, not a dense paragraph. Treat AI music as **directed iteration** — brief, batch, keep the winner, change one variable per round — not one-shot prompting.

Prompts feed the local backends through the `generate-music-local` skill (`--backend yue2` default, or `minimax-mlx`). Finish tracks with `convert-audio` when available.

## Workflow

1. **Write the one-sentence brief.** Fix: the **function** (background bed / standalone song / trailer cue / club track / game loop / demo); **genre + subgenre** ("late-90s atmospheric breakbeat", not "breakbeat"); the **emotional arc** ("restrained nocturnal verse that blooms into a euphoric chorus", not "sad"); **tempo in BPM** when it matters; the **2–4 palette elements** that make the track recognizable; the **vocal decision** (instrumental / gender / timbre / delivery / language / intimacy / backing amount); and the **structure** (intro → verse → pre-chorus → chorus, or build → drop → breakdown → final drop). *Done when the brief fits one sentence and names ≤4 identity-making elements.*
2. **Expand into a structured prompt** with the template below. The opening line fixes the broad musical distribution; tempo + rhythm remove movement ambiguity; a short instrument list builds identity without conflicts; arrangement language says *when* intensity changes; mix terms steer texture, while musical direction stays in the instrument and arrangement clauses. *Done when every clause maps to exactly one brief constraint and no two clauses fight.*
3. **Batch, then change one variable per round.** Generate 4–8 candidates from one prompt. Pick a **winner by component** — the vocal of take 2, the drums of take 5, the arrangement of take 7 — never demand one take win every category. Diagnose exactly one failure ("chorus arrives too early", "vocals too theatrical", "drums too busy", "harmonic movement too generic") and revise only the instruction that addresses it. *Done when exactly one variable changed.* Diagnosis→fix wording, worked examples, and the iteration log format live in `references/templates.md`.
4. **Write lyrics for singability, not the page** (vocal tracks only): short lines with a clear stress pattern; concrete imagery over emotion-word strings; the chorus simpler and more repetitive than the verses; rhymes that stay natural; one job per section (verse details, pre-chorus builds tension, chorus states the thesis); include the section tags the tool recognizes (`[Intro]`, `[Verse]`, `[Pre-Chorus]`, `[Chorus]`, `[Bridge]`, `[Instrumental]`, `[Outro]`). Keep the *musical treatment* in the style prompt and the lyric box lyrical; exclusions stay sparse and phrased positively ("instrumental only", "no rap phrasing" → "sung delivery throughout"). *Done when each section has a single job and the chorus is the simplest section.*
5. **Finish with editorial judgment.** Treat the raw output as a source session: keep the hook / vocal tone / chord colour / groove; export stems where available; replace weak kick, sub, percussion, transitions, and lead motifs; rebuild the arrangement with genre-appropriate phrasing (dance formats favor 16/32-bar sections and DJ-friendly intros/outros); A/B against two target tracks at matched loudness; check in mono, quietly, on headphones, and on a phone; re-listen after a night's sleep before releasing. *Done when you can name the one element the raw output contributed and the one you replaced.*
6. **Log the round.** One line per round: prompt version, seed/clip, what worked, what failed, the single next change. A prompt log converts generator quirks into repeatable wording. *Done when the round's single change is recorded together with the prompt text used.*

## The template

```text
[Genre + era/subgenre], [tempo or energy], [mood],
[key instruments and rhythm],
[vocal character or instrumental],
[arrangement / dynamics],
[production / mix character].
```

```text
128 BPM melodic techno, nocturnal and tense but euphoric at the peak.
Pulsing analog bass, tight four-on-the-floor kick, metallic percussion,
wide shimmering pads and a simple minor-key arpeggio. Instrumental.
Minimal 16-bar intro, gradual build, spacious breakdown, emotionally large
second drop. Clean, modern, club-ready mix; controlled sub-bass.
```

## Guardrails

- Consult the tool's exact current **commercial-use, ownership, distribution, and attribution** terms before releasing anything; they vary by plan, territory, and feature. Locally, the YuE2 backend weights are **CC BY-NC 4.0** (non-commercial); the code is Apache-2.0/MIT, but the weights bind.
- Never target a living artist's name, recognizable voice, or a specific copyrighted recording. Describe attributes instead: "airy female dream-pop vocal, chorus-drenched guitars, 90 BPM, intimate bedroom production".
- Keep sources, stems, project files, prompt history, and human edits — they document creative contribution and make revision feasible.
- Treat "royalty-free" labels cautiously: they do not settle training-data, vocal-likeness, Content ID, or downstream platform questions.

## Reference

- `references/templates.md` — prompt variants, diagnosis→fix table, lyric skeleton, worked examples, iteration-log format.