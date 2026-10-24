# Song pipeline: styles, song maps, a songwriter and stronger engine settings

24 October 2026. Built in a cloud session from the pushed checkout (`c6a4d4a`), on branch
`claude/intelligent-knuth-6jv48e`. **Nothing was rendered and nobody listened.** The cloud machine has no Apple GPU,
no model weights and no access to your Mac; every claim below is about code, prompts and tests, not about how the
music sounds. The render ledger is unchanged (19 takes).

## Why the outputs fell short

The accepted songs were hand-written producer prompts. Thodi's request names the genre, the singer, the
instruments, the emotion, the order of sections and the production, and its lyrics have Intro, Verse, Pre-Chorus, a
chorus that returns word for word, a Bridge and an Outro. The app replaced that with a sentence template built for
slow Indian instrumentals: 15 instruments, three arc shapes, no genre, BPM and key spent inside the 512-character
caption (ACE-Step's own guide says to pass them as parameters), lyrics drafted without section tags and labelled
Verse/Chorus afterwards, and no singer gender given to the lyric writer (Hindi verbs agree with the speaker). The
sample batch also used `shift` 1.0 where ACE-Step recommends 3.0 for the turbo model, and the optional 5Hz LM
(their "thinking" quality mode) is not installed.

## What changed

New songs now go through a **song pipeline**. Classic plans and the four accepted recipes compile exactly as
before (byte-identical captions, unchanged plan fingerprints), and a setting turns the new pipeline off.

| Piece | File | What it does |
| --- | --- | --- |
| Style presets | `app/genres/presets.json`, `backend/genres.py` | 38 styles: Hindi acoustic ballad (Thodi), Bollywood romantic, dance, retro filmi, Sufi rock, qawwali, ghazal, bhajan, Punjabi bhangra, Hindi indie, rock, R&B, lo-fi, desi hip-hop, Rajasthani folk, semi-classical; raag bansuri (Yamuna), raag sitar, Indian fusion, Indian epic, meditation, warm cinematic ensemble (Daylight); English pop ballad, acoustic, dance pop, indie folk, country pop, rock anthem, alt rock, R&B, hip-hop, EDM, synthwave, lo-fi beat, jazz; cinematic orchestral, ambient, solo piano. Genre words were checked against ACE-Step's own 178,000-entry genre vocabulary; no preset names an artist or film. |
| Instruments | `backend/instruments.py` | 56 instruments (the classic 15 plus sarangi, shehnai, sarod, veena, dholak, dhol, mridangam, tumbi, manjira, ektara, handclaps, electric/nylon guitar, drum kit, brushes, cajon, harp, flute, clarinet, sax, trumpet, brass, organ, Rhodes, ukulele, mandolin, accordion, harmonica, bells, synth pad/lead/bass, 808, drum machine, arpeggiator, oud, duduk, kalimba, marimba, taiko). |
| Song map (blueprint) | `backend/song_blueprint.py` | Song forms: verse/pre-chorus/chorus, mukhda/antara, ghazal couplets, qawwali, rap, dance, EDM build/drop, folk, jazz; and for instrumentals raag (alaap, jor, gat, taans, jhala, cadence), cinematic, ambient, loop. Fitted to tempo and length (optional sections dropped in a fixed order, intro/outro shortened, verses shortened only as a last resort, a break added when a length is too long for the words), energy per section, instruments entering section by section, short hints for each section tag. |
| Song plan | `backend/song_plan.py` | Picks the style (your Style choice, then words in the brief, then the old recipe, then a default for the voice and lead) and fills only what nobody chose: your settings and what the planner read in the brief always win. |
| Lyric craft | `backend/lyric_craft.py` | Syllable counter for Devanagari (with Hindi schwa deletion: समझना 3, ज़िंदगी 3, दिल 1) and English; a checker for line length, missing hook, wrong script, a Hindi first-person verb that does not match the singer's gender, verses copying the chorus, stock phrases; the assembler that copies every chorus repeat word for word. |
| Songwriter | `backend/songwriter.py`, `LlmPlanner.draft_song_lyrics` | With Claude on: writes each section once from the song map (language, script, singer gender, style conventions, syllables per line, rhyme, the hook), the checker runs, one revision is asked for when there are real problems, then the sheet is assembled. Your own words are never sent and never changed. |
| Song compiler | `backend/song_compiler.py` | Caption in ACE-Step's recommended shape: genre words, mood, vocal character, instruments, the journey through the sections, production. Tempo, key and meter go in their parameters. Tagged lyric sheet (`[Chorus - soaring strings]`); instrumental pieces get section tags too (the accepted Daylight layout). |
| Engine profiles | `song_compiler.ENGINE_PROFILES`, `engine/run_takes.py` | `classic` (shift 1.0), `shift3` (default for styled songs), `lm` (+ 5Hz LM 1.7B), `xl` (4B XL turbo DiT), `xl_lm`. The engine loads only what a request names, refuses missing weights, never downloads, and never lets the LM rewrite the caption, lyrics or metadata. |
| Downloads | `scripts/fetch_models.py` | The one place optional weights are downloaded: `lm` (~3.6 GB), `xl` (~10 GB). Asks first, checks free disk, records the download. |
| UI | `app/web/` | Create: a Style picker (control C26). Song page: the song map (section times, hints, who comes in), the style row, the engine line, "Lyrics written for you" with the title. Settings: an editable Music engine panel (through `/api/settings/engine`, which refuses every planner key; planner settings stay API-only). |
| Listening batch | `app/experiments/listening_batch.py` | Old versus new, blind (below). |

Other fixes found on the way: exact lyrics get `[Intro]`/`[Outro]` tag lines when they have none (words unchanged)
and a length that fits them (8 lines no longer become a 152-second song with 90 seconds of nothing); section hints
never name an instrument that is not playing; "How full" now shapes the caption; an unpicked recipe no longer shows
as "Starting sound" on a styled song; "Story of the piece" is hidden for styled songs (the song map replaces it) and
flagged if you set it.

## Try it on your Mac

```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
git fetch origin && git checkout claude/intelligent-knuth-6jv48e
app/.venv/bin/python -m pytest app/tests -q -p no:cacheprovider     # 612 tests, fake engine, no render
scripts/start.sh && open http://127.0.0.1:8477/
```

Type a brief, optionally pick a Style, press Create. With Claude on (your saved setting), sung songs get lyrics
written for their sections; with the Basic planner, paste your own words.

### The listening batch (needs your OK: 16 renders, about 10 minutes)

```sh
cd app
.venv/bin/python -m experiments.listening_batch prepare --out ../runs/_listening/b1      # no GPU
.venv/bin/python -m experiments.listening_batch render ../runs/_listening/b1             # asks first
# listen to runs/_listening/b1/listening/*.mp3, fill sheet/sheet.csv
.venv/bin/python -m experiments.listening_batch reveal ../runs/_listening/b1
```

Eight briefs (Yamuna-style raag, sitar raag, Daylight-style wordless ensemble, cinematic orchestral, Thodi's
words, the Hindi chai song, a Hindi wedding dance song, an English piano ballad), each rendered by the old app and
the new pipeline with the same brief, length, words and seed, loudness-matched and labelled A/B at random. Add
`--conditions old,new,new_shift1` to separate the prompt change from the shift change, or `new_lm` / `new_xl`
after downloading those models.

### The showcase batch: 12 briefs, one take each (you asked for these 12 renders)

`app/experiments/showcase_diverse12.json` holds the twelve briefs exactly as you wrote them, and the values set from
them: style, lead and supports, tempo, meter, length, singer, hook, theme, and any sections the brief asks for
(`require_sections`). `prepare` was run in the cloud session. Claude, through the app's songwriter step, wrote the
eight lyric sheets, each supplied hook kept word for word in every chorus. `showcase/diverse12_2026-10-25/` holds
per take the brief, plan, lyrics, every Claude draft and its check, the caption, the exact engine request and seed.
**Nothing is rendered**: the cloud session has no Mac, no GPU and no ACE-Step weights. On the Mac:

```sh
cd app
.venv/bin/python -m experiments.showcase prepare     # re-checks requests against your ACE source; keeps the lyrics
.venv/bin/python -m experiments.showcase render      # resource checks, asks, 12 takes one at a time, no retries
.venv/bin/python -m experiments.showcase publish     # commits showcase/ (MP3 copies, results) and pushes this branch
```

`render` waits while ComfyUI, the app queue or another `run_takes.py` is busy, and records a failed take as
failed. It makes -16 LUFS / -1.5 dBTP MP3 listening copies and writes `technical_summary.md` (decoding, length,
channels, clipping, silence). Native FLACs stay in `runs/_showcase/`. It raises the render ledger by 12.

### The bigger engine (needs your OK: downloads)

```sh
python3 scripts/fetch_models.py lm      # 5Hz LM 1.7B, ~3.6 GB (you approved this one)
python3 scripts/fetch_models.py xl      # XL turbo 4B, ~10 GB (not yet approved)
```

Then pick the profile in Settings → Music engine. Memory: renders already peaked at 51-55 GB footprint on the
48 GB Mac with the 2B turbo alone; watch Activity Monitor on the first LM or XL render and never run one alongside
ComfyUI.

## ElevenLabs: what was used and what was not

The ElevenLabs research in `elevenlabs-rea/` is not used to build Raag Studio's engine. ElevenLabs' Prohibited Use
Policy (section 12) forbids reverse engineering their services and using their services or outputs to develop,
train, improve or benchmark competing products; their Music Terms forbid making their models available through
another app without written permission. The song pipeline was designed from ACE-Step's own documentation, your
accepted recipes (Thodi already used the section-by-section shape), songwriting practice and the genre library
already in the repo. No new ElevenLabs credits were spent.

For songs you simply want to keep, `scripts/personal/elevenlabs_render.py` turns a Raag Studio plan into an
ElevenLabs v2 composition plan and, only with `--render --max-credits N` and your `ELEVENLABS_API_KEY`, renders
it from your account (balance checked first, no automatic retry, a receipt per song). It previews by default, is
not called by the app, and should stay out of a public release.

## Checks run here

- 612 Python tests (565 after the first commit; new: `test_song_pipeline.py`, `test_listening_batch.py`,
  `test_personal_elevenlabs.py`, `test_showcase.py`) and 33 JS logic tests pass. Older tests that pin the classic compiler's
  contract run with `RAAG_SONG_PIPELINE=0`; three spec tests were updated for control C26 and the engine endpoint.
- The twelve showcase requests pass the same validator. The fake-engine path of `showcase render` (scratch folder
  only) was tested end to end: the -16 LUFS copy, the technical summary, and a failed take recorded and not retried.
- Every listening-batch request (32, across four conditions) passes `run_takes.validate_request` against the
  `GenerationParams` fields of the pinned ACE-Step source (`ca1e85fe`), cloned read-only for the check.
- The UI was driven in Chromium against the fake engine: Style picker (38 styles in 5 groups), a raag song map,
  a sung Bollywood song with pasted Hindi words, the engine setting saved, no horizontal scroll at phone width, no
  console errors.

## Honest limits

- Nobody has heard a note of the new pipeline. Better prompts, a song map and a recurring chorus are reasons to
  expect better songs, not proof. The listening batch is the test.
- The songwriter's prompts and checks are tested with a scripted model. Live Claude wrote the eight showcase lyric
  sheets; whether they sing well is unheard.
- Instrumental section tags (`[Chorus - main theme]` + `[Instrumental]`) follow the accepted Daylight layout, but
  whether ACE-Step honours them for pure instrumentals is untested.
- The syllable counter and the gender check are heuristics. They decide when to ask for a revision, never what
  the words are.
- Duet singing, rap flow and Hindi diction remain unverified, and so does English singing in this project.

## Decisions for you

1. Render the listening batch (16 takes; raises the ledger from 19 to 35)?
2. Download the 5Hz LM (approved) now, and the XL turbo (~10 GB, not yet approved)?
3. Should the song pipeline stay the default, or only when a style is picked?
