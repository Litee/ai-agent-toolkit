# Templates & Reference — Generate Music Prompts

Consulted on demand by SKILL.md ("Generate Music Prompts"). The main file holds the workflow and the one universal template; this file holds the branches and the material only some runs need.

## Prompt variants

### Vocal song (pop / rock / ballad)

```text
[Genre + era], [BPM], [mood arc],
[lead instrument(s) + rhythm identity],
[vocal character — gender, timbre, delivery, intimacy, backing amount],
[arrangement — verse/pre-chorus/chorus layering],
[production/mix].
```

Example:
```text
90s alt-rock power ballad, 76 BPM, intimate verse that swells into a
stadium-wide chorus. Fingerpicked acoustic + delayed electric arpeggio,
live drums building from brushes to full kit.
Intimate low-register male vocal, soft doubles in chorus only, sung
delivery throughout, restrained vibrato.
Two subdued verses, tense pre-chorus, huge four-part-harmony chorus,
guitar-solo bridge, final chorus up a key.
Broad, roomy mix with natural compression; no modern brickwall loudness.
```

### Restyle / cover version of an existing kept song

Keep the lyrics byte-identical; change only the style prompt (one variable per round):

```text
[Same lyrics as <song tag>, unchanged]
[New genre/era], [new BPM], [new mood],
[new instrument identity],
[same vocal character or decisively different one — pick one],
[same arrangement density or new one — pick one],
[new production/mix].
```

### Game loop / background bed

```text
[Genre], [BPM], [mood],
[minimal loopable palette — 2–3 elements],
[instrumental],
[loopable structure — any 8–16 bars can loop without a hard restart],
[mix shelved for dialogue/foley headroom].
```

### One-variable variation recipe (A/B control)

Fix every clause except one, and say which is the variable in the log:

```text
[identical prompt to version N] — except: <the single changed clause>
```

## Diagnosis → fix

| Diagnosis | Fix instruction (drop into the prompt) |
|---|---|
| Arrangement too busy | "sparse arrangement, fewer percussion layers, ample negative space" |
| Vocals too theatrical / belted | "close-mic, conversational, breathy restrained vocal" |
| Drop / chorus lands weak | "stronger contrast: strip drums before the drop, then full kick and sub return" |
| Melody drifts, hook not retained | shorten lyric lines and repeat a concise hook verbatim in each chorus |
| Chorus arrives too early | "two verses and a pre-chorus before the first chorus; chorus at the 3rd minute" |
| Harmonic movement too generic | give the pre-chorus a secondary dominant or ii–V–I; extend chords on the chorus |
| Drums too busy | "eight-bar drum pattern, half-time fills only at section ends, sidechained to the kick" |
| Too bright / harsh on repeat listens | "dark, rolled-off top end; round, pillowy highs" (then verify in mono and on a phone) |

Each fix edits **one** clause. If two problems persist, run a separate round per problem.

## Lyric skeleton

```text
[Verse]
Streetlights break across the rain
I trace your name on window panes

[Pre-Chorus]
Hold your breath, the room goes still
One more second, one more thrill

[Chorus]
We were sparks in the afterglow
Nowhere left that we have to go
```

Checklist: short lines with a clear stress pattern; concrete imagery; chorus simpler and more repetitive than verses; natural rhymes only (a forced rhyme is worse than no rhyme); one job per section; tags per section when the tool recognizes them. Keep the musical treatment in the style prompt, not the lyric box.

## Worked example — iterating a kept song

Starting point: user likes `eurobeat_03_tokyo-ignition` (kept; lyrics + seed known).

- **Round 1 (identity):** "Eurobeat, 154 BPM, neon highway at 2am, layered synth leads, heavy four-on-the-floor, anthemic male vocal, tight arrangement, bright club mix." — 4 seeds. Winner by component: vocal of seed 2, leads of seed 3.
- **Round 2 (one variable: vocal):** same prompt except "restrained close-mic male vocal, no belting, roomy chorus reverb". Diagnosis: leads still generic → next round changes only the lead clause.
- **Round 3 (one variable: leads):** same prompt except "double-time plucky lead with a syncopated counter-melody". Log each round with the prompt text used.

## Iteration log

One line per round (append to `prompt_log.md` next to the outputs):

```text
round | prompt_version | seeds/clips | kept component | failure | next change
r1    | v1             | 4 seeds     | vocal (t2), leads (t3) | leads generic | v2: lead clause only
r2    | v2             | 2 seeds     | vocal (t1)            | chorus late    | v3: chorus timing
```

## What not to do — the fragmentation failure

```text
Make an amazing emotional electronic song that is catchy, cinematic, lo-fi,
hard-hitting, relaxed, dark, happy, with lots of instruments.
```
The clauses fight (relaxed vs hard-hitting, dark vs happy, catchy vs lo-fi) and every musical decision is left unspecified — the model has to guess the distribution, the movement, the identity, and the arrangement in one shot. Same failure mode, milder, is a prompt that lists eight genres "inspired by" without choosing. Prefer the one-sentence brief + template: chose what defines identity, left everything else to the generator.