# Critical review of the Raag Studio PRD (v0.1, 24 Oct 2026)

Reviewer stance: skeptical senior product + audio-ML. Review date: 24 Oct 2026.
Companion plan: `PRD_v2_MVP.md` (the revised, shorter product plan).

## 0. Verdict

The PRD is honest about engine limits in its prose but not in its structure.
It says "soft direction, review required" 70+ times and then still builds a
104-control product around those soft directions. What actually produced the
music Siddhant liked is much smaller than the PRD: **four hand-compacted
~500-character captions, explicit BPM/key/duration metadata, `instrumental` /
wordless-lyric switches, and several seeds per brief**. Nothing in the 104
fields has been shown to move the audio, and the one thing that is cheap,
proven and high-leverage (several takes per brief) defaults to **1** in the
catalogue.

Keep: the honesty principle, immutable versions, the brief-first flow, the
song-refrain vs background-choir distinction, exact-lyrics-as-input. Cut or
defer: most of the catalogue, all per-instrument mixing, durable-queue
ceremony, React build chain, the cloud/competitor material. Rebuild the core
around (1) a prompt **compiler** with proven templates, (2) **multi-take**,
(3) a small honest **refine** vocabulary, (4) a **taste ledger**.

## 1. Method and limits

Read: HANDOFF_PROMPT, AGENTS, README, PROJECT_CONTEXT, AUDIO_GUIDE and
AUDIO_CATALOGUE, the PRD, Control_Catalogue.csv, Research_Decisions,
Creative_Plan.schema, Example_Plans, Capability_Registry_Example,
IMPLEMENTATION_REVIEW, SYSTEM_AND_RUNBOOK, all `recipes/*/request.json` and
`result.json`, the ACE `INFERENCE.md` / `inference.py` copies, the Bansuri,
Daylight and Hindi-song receipts, research docs, and (outside the pack, read
only) the real engine logs under `../music/bansuri_journeys_20261024/`.
Environment probes were read-only (`python3 --version`, `node --version`,
`ls`, `ps`, `curl` to the local video queue port, `claude --help`).

Not done, by instruction: no model was run, nothing installed, no existing
file modified. **I did not listen to any audio.** Taste statements below rely
on `AUDIO_CATALOGUE.json` user quotes only. Where I say "unverified" I mean
no receipt in the pack establishes it.

## 2. Measured facts that change the plan

### 2.1 Real render times (from `recipes/*/result.json`, `extra_outputs.time_costs`)

| Recipe | Audio length | Caption chars | Pipeline total | DiT diffusion | VAE decode | `elapsed_seconds` | Real-time factor |
|---|---|---|---|---|---|---|---|
| yamuna (flute_focus) | 168 s | 509 | 17.2 s | 4.3 s | 12.8 s | 23.3 s | 0.10 |
| daylight take 1 | 132 s | 504 | 14.6 s | 4.1 s | 10.4 s | 16.1 s | 0.11 |
| thodi take 1 | 152 s | 493 | 17.0 s | 4.1 s | 12.9 s | 20.8 s | 0.11 |
| moonlit | 144 s | 508 | 17.2 s | 7.4 s | 9.8 s | 31.4 s | 0.12 |
| hybrid vocal | 44 s | 491 | 7.5 s | 1.4 s | 6.1 s | 9.2 s | 0.17 |

Model init is about 6 s (`flute_focus.log`: 01:26:49.8 init start, 01:26:55.97
"generate_music" begins). Normalise + save after decode adds about 5 s
(01:27:14 to 01:27:19). So **a 2-3 minute piece is a 20-30 s job once the
model is loaded, and a 3-take batch is about 1.5-2 minutes including a cold
start.** Moonlit's diffusion stage was 1.7x slower than the others
(7.4 s vs 4.1-4.3 s); cause not logged (contention is a guess, not a finding).
Peak memory is not recorded anywhere (`allocated=0.00GB` in the log is the
CUDA-style counter and is meaningless on MLX). The log reports "37.4 GB
unified memory, tier=unlimited" on a 48 GB machine. Behaviour above 168 s
(up to the 600 s API cap) is unmeasured; attention cost may be super-linear.

Consequence: the PRD's fear of "long renders" (queue, cancel, progress,
budget ceilings) is mostly misplaced; the real cost is **human listening
time**, not machine time.

### 2.2 Captions sit at the budget ceiling

All five preserved captions are 491-509 characters. The 512-character figure
is a docstring ("< 512 characters", `inference.py` line 61), not an enforced
check at that layer; what the text encoder does past that is unknown. In
practice the accepted prompts were hand-compressed to exactly this budget, so
**a compiler with a drop-order is the product's core**, and the PRD does not
specify one.

### 2.3 Turbo does not use CFG; recipes record a lie

`flute_focus.log` line 44: "Turbo model detected: overriding guidance_scale
7.0 -> 1.0 (turbo does not use CFG)". Every `request.json` nevertheless
records `guidance_scale: 7.0`. Receipts store the requested value, not the
effective one. Consequence for "avoid": with no CFG there is no negative
prompt channel, so "no singing" can only work as a positive text hint or via
the structural `instrumental` flag and `[Instrumental]` lyric.

### 2.4 Unexplored upstream defaults

`INFERENCE.md`: "set `shift=3.0` for turbo". Every accepted recipe used
`shift: 1.0`. Might be better, might be worse; nobody listened. It is an A/B
candidate, not a change to make silently.

### 2.5 The evidence set is tiny and narrow

Accepted: Yamuna (82 BPM, D major), Daylight (88, D major), Thodi (76,
D major). All slow-to-medium, tender, major key, acoustic, 132-168 s. The
only other piece is Moonlit (104 BPM, G major), unreviewed. **Nothing about
fast, dark, electronic, minor, rock, cinematic-loud or sub-60 s material has
a single data point.** Templates drawn from these four are valid only in that
region.

## 3. Findings, ranked by severity

Severity: **Critical** = would make the product misleading or waste the build;
**High** = large quality/usefulness loss; **Medium** = real but bounded;
**Low** = polish.

### F01 (Critical): The catalogue is not an MVP; "P0" is 57 controls

Evidence: `Control_Catalogue.csv`: 104 rows, **57 P0**, 39 P1, 8 P2. The
HANDOFF says "avoid 104 visible controls on first load" and "A small
functional slice", yet 57 are P0 (12 lyric fields, 10 voice fields, 8
instrument fields, 10 intent fields). Row 2 `view` ("Controls view") is UI
state, not a music control; row 87 `job.budget` is a cost ceiling for a local
free engine.

Why it matters: each exposed soft control is a promise the engine cannot keep
and a decision a self-described beginner cannot make. The evidence that any
single one changes the output is zero; the evidence that prompt compaction
(fewer instruments) mattered is one confounded case (F06).

Recommendation: collapse to the 25-control set in `PRD_v2_MVP.md` section 4.
Every other row is stored as planner-internal, deferred with a named
prerequisite, or cut (Appendix A has a disposition for all 104).

### F02 (Critical): Multi-take is the dominant quality lever and the PRD defaults it to one

Evidence: catalogue row 86: `job.takes ... 1; 2; User bounded, default 1, P0`;
PRD section 12 step 9 "Render the agreed number of takes within the job
budget". Receipts: 14.6-17.2 s pipeline per take (Table 2.1). Daylight already
used two seeds and Thodi three; the accepted pieces are "take 01" of small
sets, i.e. the user's wins came from sampling, not from field-level control.

Why it matters: diffusion music has high take-to-take variance (different
melody, different voice, different instrumentation). Three takes cost ~70 s.
The user can pick the one with the melody he likes ("such a melody") which no
control can specify.

Recommendation: default **3 takes per Create**, one engine process, seeds
random (stored). Show them as T1/T2/T3 with a one-click favourite and a
reason tag. Do not auto-rank by Earshot (F06, F11).

### F03 (Critical): Over-promises that must be removed or relabelled

Each below: PRD text, why it cannot be honoured, change.

| # | PRD / catalogue text | Problem | Change |
|---|---|---|---|
| a | `instruments.priority` "Essential ... generation must be reviewed for that requirement" (PRD line 83) and "An optional selected instrument must never displace an explicitly essential one during prompt compression" (line 93) | Fine as a compiler rule, but "Essential" as a user-facing choice implies engine obedience. Flute dominance in Yamuna was achieved by wording ("Bansuri is the loud clear melodic lead in every section") plus removing 3 instruments, once. | Internal compiler rank only. User sees one "lead" star. |
| b | `instruments.presence`, `.density`, `.register`, `.tone`, `bansuri.breathing` etc. | Seven overlapping words for "how prominent / how busy". All map to a few adjectives in the caption. | Merge into: lead star + "How full" + "Playing style". |
| c | `choir.target_count` "Requested singer count" (schema allows up to 1000) | Not honourable; model has no count concept. Example plan 3 literally requests 100. | Cut. Map numbers in the brief to a scale word (small / choir / big choir) and say "approximate". |
| d | `harmony.progression`, `harmony.modulation`, `melody.range`, `melody.counterline`, `rhythm.syncopation`, `rhythm.pattern` | With LM off there is no chord, note or pattern conditioning. These are decorative adjectives. | Cut. |
| e | `harmony.raga`, `rhythm.tala` (P2) | PRD itself says experimental. The user will type "raga" in the brief anyway. | No control. Let words in the brief pass into the caption; never claim raga adherence. |
| f | `Intent.avoid` and `lyrics.forbidden_words` | No CFG on turbo (2.3). "No X" in the caption may even prime X. | Planner-side omission plus structural switches (`instrumental`). One free-text "Avoid", labelled "we leave this out; the engine can still add it". |
| g | `project.locks` "Keep these choices" | PRD admits lock != waveform lock; the actual meaning is just "do not re-plan this field". | No lock UI. Fields the user touched are auto-pinned (provenance `user`). |
| h | `mix.part_gain/pan/reverb/eq/compression/delay/automation` (7 rows, P1) | Stereo mix only. HDemucs (hdemucs_high) separates **4** stems (drums, bass, other, vocals); flute and tabla stay together in "other". | Cut all 7. Backlog: 4-stem "Stem lab" only, labelled estimated. |
| i | `reference.keep_melody`, `reference.hum`, `structure.cue_points` | Need conditioning we do not have. | Backlog with named prerequisites. |
| j | PRD line 113 "Wordless choir switches the engine's instrumental boolean off" | Incomplete. In Daylight the wordless choir exists because the **lyrics field contains `Ooh, ooh, aah` lines in `[Chorus]`** with `[Instrumental]` tags in other sections. The flag alone gives no choir. | Compiler emits a wordless-lyric skeleton from a template (R2). |
| k | PRD line 248 "Optional transcription checks flag omissions/repetitions against locked lyrics" | See F07: the local Whisper-small output on the accepted Hindi take is near-gibberish. | Cut from MVP. |
| l | PRD line 250 "Do not reuse video latency estimates or promise a universal seconds-per-song rate" | We now have the numbers (2.1). | Show "about 25 s per take, measured". |
| m | Acceptance scenario: "any suspected voice content is flagged, not hidden" | The only detector is Earshot tags; in the Yamuna first pass they produced "voice-like alternatives" that the receipt itself calls "not proof of unwanted singing". | Say so; no automatic flag. Human listens. |
| n | Control `rhythm.feel` "Half-time" | A prompt word; may or may not change drum feel. | Keep as brief vocabulary only. |
| o | `export.sample_rate`, `master.target_lufs`, `master.true_peak` as user controls | Real ops, but beginners have no use for them. | Fixed preset (48 kHz, -16 LUFS, -1.5 dBTP, as the accepted exports); producer drawer shows it read-only. |

### F04 (High): The compiler, the actual product core, is unspecified

Evidence: PRD section 12 step 7 says "Compile a compact engine request: lead
identity, mood/style, essential support, rhythm and two or three defining
developments", and calls "few key instructions" a heuristic "that needs
evaluation". But the four accepted captions already share a clear grammar:

1. Format + lead ("Instrumental Indian bamboo flute solo with gentle tabla,
   tanpura drone and sparse santoor.")
2. A lead-priority sentence ("Bansuri is the loud clear melodic lead in every
   section.")
3. Tone + 4-5 technique terms ("Rich breathy flute tone, expressive meend
   pitch slides, delicate grace notes, fluid fast runs...")
4. One melody/emotion sentence ("Beautiful recurring melody, tender and
   luminous.")
5. Arc in 4-5 beats ("Spacious solo opening, flowing tabla pulse, exposed
   flute interlude, ... peaceful cadence.")
6. "82 BPM, D major." (also passed as metadata)
7. Voice constraint tail ("Strictly no voices.")

Recommendation: specify this grammar as slot-filled templates with a
documented **drop order** under the budget (optional support, then technique
terms, then arc beats beyond three, then mood adjectives; never the lead, the
voice constraint, or BPM/key), plus golden tests (v2 M1).

### F05 (High): "Refine" is under-specified, and the cheapest honest options are not even named

Evidence: PRD F10 "Text revision with declared scope: new take versus actual
audio operation"; Capability_Registry: `"repaint": "documented, pilot
needed"`. The registry omits the other engine paths visible in
`inference.py` / `INFERENCE.md`:

- `retake_seed` + `retake_variance` ("variance-preserving noise mixing for
  variation generation", `inference.py` 179-182): a native "more like this"
  knob. Present in every `request.json` at 0.0; never exercised.
- `task_type: cover` with `audio_cover_strength` (turbo-capable; actually used
  in the rejected remix pipeline: "`cover-nofsq` at strength 1.0 preserved the
  arranged guide much more closely", LOCAL_SETUP/REMIX_LEARNINGS). Duration is
  locked to the source.
- `flow_edit_morph` (cover + caption: "paint the source audio toward the
  user's caption"). Upstream issue-level feature, v1 limits noted in code.
- `repaint` with `repaint_mode` / `repaint_strength` / crossfade frames. The
  research notes the Scenario skill's warning that repaint "can change the
  voice".
- Explicitly **not** available: `lego`, `extract`, `complete` (base only).

What "refine" can honestly mean on a text-to-music model: (1) another take;
(2) edit the plan and make new takes (a new related piece, not a modified
one); (3) retake_variance variation of a liked take (experimental);
(4) cover-based re-arrangement keeping structure (experimental);
(5) repaint of a span with local splice and sample-equality outside the span
(experimental, voice may change); (6) real audio ops: trim, fade, gain.
Never: "keep this melody", "make the flute louder".

Seeds are not a similarity dial. Diffusion seeds are independent noise; seed
24102633 is not "near" 24102632. The date-coded seed convention (24102601 =
24 Oct, take 01) is human bookkeeping only.

Recommendation: v2 section 6 defines the refine vocabulary and labels
experimental paths until a blind listening pilot passes (M6).

### F06 (High): The "what worked" story is one confounded anecdote

Evidence:
- Yamuna first pass (seed 24102631) vs the refinement (24102633): **seed,
  caption wording, and instrument list all changed** (cello and sitar removed,
  "virtuoso Hindustani ... murki ... taans" vs "Rich breathy flute tone ...").
  The user praised the result ("such a melody man"), which is evidence for that
  take, not for the "fewer layers" rule.
- The Earshot flute-query z-scores used to justify the refinement (first pass
  2.8 / 1.7 / 3.7 -> focus 3.4 / 5.4 / 4.6, `COMPOSITION.md`) also give
  **Moonlit Raas, a 7-instrument piece never refined, 3.8 / 4.3 / 4.0**. The
  metric barely separates "focused" from "busy" (three readings each). The receipts disclaim
  this themselves ("cannot certify ... musical beauty").
- Hindi: Roman vs Devanagari "no clear transcription improvement" changed
  script and seed together (the README admits this).
- The hybrid's "one note per syllable, narrow range, no melisma, dry a cappella,
  no reverb" caption (recipes/hybrid_vocal) is the only vocal prompt that
  produced a rejected, recitation-like result; LOCAL_SETUP says those
  constraints "plausibly contributed". Weak, but it is the only vocal-style
  contrast on file.

Recommendation: ship recipes R1-R3 as **starting points that Siddhant already
liked**, not as proven rules. Bake in the one defensible rule: name a single
lead explicitly and keep the support list short. Do not write "fewer
instruments is better" into the UI. Add a taste ledger so the app learns from
real A/B outcomes (v2 section 5).

### F07 (High): Exact lyrics: the promise ends at "sent unchanged"; checks and edge cases are missing

Evidence:
- `recipes/thodi/transcription.json` (Whisper-small, Hindi forced): "तरी चाए का
  आद़ब यान लाए, तेरी चाए का आद़ा प्याना अब भी मेज़ पे रख्ठा है ..." followed by a
  long run of repeated characters. Intended: "तेरी चाय का आधा प्याला अब भी मेज़
  पे रखा है". The user called this take "amazing". The ASR is not a usable gate
  for Hindi singing (and ASR cannot separate singer error from ASR error;
  the receipts say so). The song "retained more of the bridge" was used to pick
  take 01, which is a weak selection signal that happened to agree with the
  listener.
- The Thodi lyrics themselves were **AI-written** by the same process the
  PRD calls "Write for me"; no user-supplied exact lyrics have ever been
  rendered. "Use my words exactly" is entirely untested for singing quality.
- Example_Plans[3] ("exact" Hindi lyric) has **2 lines** with no duration.
  PRD only defines the *overlong* case ("Long exact lyrics trigger a
  duration-fit check"). The beginner case is the opposite: a short couplet.
  Thodi is 26 lyric lines over 152 s (about 5.8 s per line including
  instrumental intro/outro); 2 lines gives nothing close to a song, so the
  model will pad, repeat or improvise.
- Structure tags ([Verse], [Chorus]) are text the model sees. The PRD says tags
  are separate from lexical content; fine, but the exact-lyrics test must
  strip tag lines and compare byte-for-byte, otherwise tags get "preserved"
  as lyrics or lost.

Recommendation: "exact" means: the compiler guarantees `lyrics` minus tag lines
is byte-identical to the user's text (unit-testable). Sung adherence is
declared unverified, UI says "listen". Add under-length handling: <8 lines
suggests a ~45-60 s sketch or an explicit user-approved repeat of lines. Label
Hindi **experimental** (one heard take; diction imperfect), and mitigate with
3 takes. Drop ASR from the MVP.

### F08 (High): The planner is hand-waved, and everything interesting depends on it

Evidence: IMPLEMENTATION_REVIEW #1; PRD section 13 "planner uses an
explicitly configured LLM API or local model". Environment probes: no
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` in the environment; `claude` 2.1.260
exists at `~/.local/bin/claude` (supports `-p`, `--output-format`,
`--json-schema`, `--allowedTools/--disallowedTools`, `--bare`, `--model`);
`ollama` binary is installed but its server is not running (`ollama list`
fails to connect), no local LLM weights were found in the HF cache;
`mlx-lm 0.29.1` is in the ACE venv with no model; the ACE LM (5 Hz) is not
installed.

Everything the user actually asked for from free text (analogies, stories,
"write for me" lyrics, refine-by-text) is language work. A rule-based planner
can only map keywords. Evaluation and a recommendation are in section 6.

### F09 (High): The accepted-take workflow does not exist in the PRD: no taste ledger

Evidence: the only ground truth the project has is Siddhant's one-line
verdicts. PRD section 15 "Technical checks" vs "Listener feedback" panels are
good, but there is no storage design that turns favourites into defaults, no
reason tags, no cross-take comparison protocol beyond "blind level-matched".

Recommendation: store per take: favourite, rating (love / fine / no) and
optional reason tags (melody, instrument, voice, rhythm, diction, too busy,
too plain). Use it to (a) show "you liked R1 4 times", (b) re-weight which
recipe is the default, (c) feed the A/B pilots. Cheap, high value.

### F10 (Medium): Stems and mix are a false P1

Evidence: PRD F13 "Estimated stem extraction and real mix controls for
available tracks"; hdemucs_high is a 4-source model. Flute vs tabla vs
santoor vs tanpura cannot be separated; "other" is one bucket. The
`Advanced mix` group (7 rows) therefore has no valid target for the very
instruments the product is about.

Recommendation: cut `Advanced mix`; backlog a "Stem lab" with 4 labelled
stems (drums, bass, vocals, other), clearly "estimated", only after MVP-2.

### F11 (Medium): Quality gates measure the wrong thing

Evidence: AUDIO_GUIDE: "No clipping, favourable tags and a good loudness
level did not make the rejected music good." The PRD keeps technical checks
(good) but also proposes instrument tags as "hints". Earshot's flute z-score
failed to distinguish refined from busy (F06).

Recommendation: automated checks gate only *breakage*: decode OK, finite
samples, duration within tolerance, silent-fraction, clipped-sample fraction,
true peak. Everything else is human. Do not auto-rank takes.

### F12 (Medium): Over-built architecture for a personal, single-user, 25-second job

Evidence: IMPLEMENTATION_REVIEW #3 (JSON-pointer locks, stable IDs),
#9 (durable queue, idempotency, startup recovery, best-effort cancel),
PRD "React/TypeScript". Facts: jobs run ~25 s per take; Python 3.14.7 system,
3.12.14 ACE venv (the ACE venv already carries FastAPI 0.159.1 and uvicorn
0.54.0); Node v26.3.0 (very new; no reason to take on a bundler); user is one
person on localhost.

Recommendation: one SQLite jobs table, a **subprocess-per-job** worker (which
makes cancel a real `kill`, memory release automatic, and restart recovery a
10-line startup sweep), idempotency by a client key, FastAPI + a no-build
static frontend. Details in v2 section 9. Keep restart safety and the
no-overwrite rule; drop plan-diffing, pointer locks, per-field provenance for
100 fields.

### F13 (Medium): Operational risks the PRD does not mention

Evidence and recommendation:
- **Disk is 98% used** (`df`: 25 GiB free of 926 GiB). A 168 s take: WAV
  48 kHz stereo is tens of MB; with native WAV + 24-bit master + MP3 per take
  and 3 takes per Create, a heavy week can be several GB. Guard: refuse to
  start under 5 GiB free; store native as FLAC; make masters only on export;
  prune non-favourite natives on request.
- **Shared Mac.** A ComfyUI process (pid 85254, `--offline`) is resident; the
  video queue API on port 8388 responded `{"queue_running": [], "queue_pending": []}`
  (8188/8288 not listening). Gate render start on `GET :8388/queue` being
  idle; treat connection-refused as idle.
- **Network attempts at init.** `flute_focus.log` line 8: "Main model not
  found, starting auto-download..." then fell back to the local dir because HF
  was unreachable. Always set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`
  (as every reference script does); add a test that no download is attempted.
- **Native-only GPU.** SYSTEM_AND_RUNBOOK: a restricted shell may expose no
  MPS. Worker must check `torch.backends.mps.is_available()` and refuse CPU.
- **Python split.** API (own venv inside this root) vs worker (ACE venv python
  3.12, read-only). Do not import torch in the API.
- **Receipts store requested, not effective params** (2.3); store both.

### F14 (Medium): Copyright and "remix a famous song"

Evidence: the user's history is a failed remix of Attack on Titan / Game of
Thrones excerpts (AUDIO_GUIDE: "private context examples, not original
compositions we claim to own"); PRD has `Intent.inspiration` ("Mood/theme/
reference with provenance") and lyric mode "Inspired, never copied" for "a
reference".

Risks: the user will type "make it like Ashes on the Fire" or paste
famous lyrics; a text-to-music model cannot honour "remix this song" (the
text path has no source), and `cover` on someone else's recording is exactly
the path that was rejected and carries rights problems.

Recommendation: planner-side rule: strip named songs/artists/"in the voice
of" from the caption; show "I used the mood, not the song" with the
extracted descriptors; no audio upload/cover of third-party songs in MVP-1/2;
"Write for me" must not take a copyrighted lyric as input (paste detected as
"Use my words exactly" requires the user to assert it is theirs/public domain
- one checkbox). Model-weight licence for any sharing of outputs is
unresolved (the research says to check; no receipt does). Treat the app as
personal-use until that is resolved.

### F15 (Medium): Schema and example-plan defects

Evidence and fixes:
- `Creative_Plan.schema.json`: `choir.target_count` max 1000 though marked
  approximate; `choir.scale` has `solo` / `duet` that duplicate a
  `voices.lead`; `duration_seconds` 10-600 mirrors the API but the ACE doc says
  instrumentals "30-180 seconds works well" and nothing above 168 s was ever
  run; no `seed`, `recipe_id`, `takes`, `parent_take_id`, or compiled
  `caption`/`effective_params` fields; array-index locks.
- `Example_Plans[1]` (Yamuna-like) omits tanpura and states 180 s / bpm 82
  while the accepted recipe is 168 s with tanpura.
- `Example_Plans[3]`: two-line exact lyric, no duration (F07).
- `Capability_Registry_Example`: `en: "wordless voices only; lexical singing
  not evaluated"` is the right honesty but is not wired to the UI; `cover`,
  `retake`, `flow_edit` not listed; `lyrics_character_budget 4096` is
  also a docstring figure.

Recommendation: v2 section 7 has a corrected, smaller plan schema.

### F16 (Low): Non-product material inflating the document

Section 10 (Joey Nato observations as table of "friendly app choices"),
section 16 ("exciting options"), S1-S12 competitor sources, and
Research_Decisions' competitor table do not change any MVP decision. The Joey
Nato material is legitimately useful in one narrow way: **relationships over
inventory** (what leads, what answers, what leaves). That is already the
compiler's job. Move the rest to a "ideas" appendix; do not let it appear as
controls.

### F17 (Low): Name, personas and goals

"Secondary users: video creators ... producers" and "future hosted service"
add scope pressure for nothing. The user said it is a personal app. Cut.

### F18 (Low): Duration default and range

All accepted pieces are 132-168 s. Default Auto = 150 s, presets 60/120/180,
hard cap 240 s until timing above 168 s is measured (M0).

## 4. Answers to the six review questions (short)

1. **Daily use**: brief, voice mode, length, versions, instrument chips with a
   lead, pace/how-full chips, favourite, change-request text, another take,
   export. About 9 things. Everything else is noise, duplicate, or impossible
   (Appendix A). Minimal surface: `PRD_v2_MVP.md` section 4.
2. **Reliability**: Appendix B (classes a-d for every major feature).
3. **What made good music**: section 5 above; templates in v2 section 5.
4. **Planner**: section 6 above; recommendation: one interface, rule-based
   baseline always on, `claude -p` as optional smart provider, API key
   second, local MLX LLM deferred.
5. **Risks**: F13, F14, F07 plus section 8 above.
6. **MVP cut and stack**: `PRD_v2_MVP.md` sections 12-13 and 3.

## 5. What good music looked like here: extractable patterns

From the three accepted recipes plus the rejected hybrid and the unreviewed
Moonlit (evidence is n=1 per item; these are *defaults to try*, not laws):

| Pattern | Evidence | Bake in as |
|---|---|---|
| Name **one** lead and say it plainly; keep support to 2-3 named instruments with softening adjectives (gentle, sparse) | Yamuna flute_focus: "Bansuri is the loud clear melodic lead in every section"; support "gentle tabla, tanpura drone and sparse santoor" | Compiler slot 2; planner caps support list at 3 by default |
| Describe the *arc* in 4-5 beats using section words the user can understand | All captions end with an arc sentence; Daylight uses `[Intro]..[Outro]` lyric tags | Arc templates (steady, slow build, quiet middle then bloom) |
| Pass metadata explicitly: bpm, keyscale, timesignature "4", duration, vocal_language, `inference_steps 8`, LM off | All receipts | Fixed adapter defaults |
| Tempo 76-88, D major, 132-168 s | 3 of 3 accepted | Default region; "Lively" (>= 100) marked unproven |
| Instrumental = `instrumental:true` + lyrics `[Instrumental]` + a "no voices" tail | Yamuna | R1 |
| Wordless choir = `instrumental:false` + lyric lines of `Ooh/Aah` in chorus sections + `[Instrumental]` elsewhere + "wordless mixed-choir ooh/aah" in caption | Daylight | R2 skeleton |
| Sung Hindi = Devanagari lyrics with section tags, `vocal_language: hi`, warm male lead "singing clear Hindi", "no rap", restrained instrumentation | Thodi | R3 |
| Avoid dry a-cappella / one-note-per-syllable / no-reverb vocal instructions | Hybrid_vocal caption; user: "lyrics were not music, just someone reading" | Compiler never emits those phrases for sung modes |
| Several seeds per brief; keep the user's pick; do not trust a classifier to pick | Daylight (2), Thodi (3); take 01 chosen by ASR retention and later liked, but ASR is garbage on Hindi singing | 3 takes, human pick |
| Engine post: normalisation -1.5 dB, fade_in 0.04-0.08, fade_out 2-3 s; export: two-pass loudnorm to about -16 LUFS, MP3 320k, WAV 24-bit 48 kHz | export scripts and master_checks.json | Fixed finishing preset |

Style recipes to ship (id, status):
- **R1 Flute focus (Yamuna)**: instrumental, bansuri lead, tabla + tanpura +
  sparse santoor, 82 BPM D major, 168 s. Status: user-accepted take.
- **R2 Warm ensemble with wordless choir (Daylight)**: piano hook answered by
  flute, guitar, strings, round bass, soft groove, wordless choir chorus,
  88 BPM D major, 132 s. Status: user-accepted.
- **R3 Hindi romantic ballad (Thodi)**: 76 BPM D major, warm male lead,
  guitar/piano/bass/brushed drums/strings, 152 s. Status: accepted with
  diction caveat; **experimental**.
- **R4 Playful Indian fusion (Moonlit)**: 104 BPM G major. Status: **unrated**;
  ship only after the user rates it (do not transfer Yamuna's approval).
- Negative lesson L1 (not a recipe): the hybrid vocal style is blocked.

Two further honest knobs: `shift` (upstream says 3.0 for turbo, recipes used
1.0) and `retake_variance` are *experiments* (v2 M6), not defaults.

## 6. Planner evaluation

| Option | What it can do | Cost / risk | Verdict |
|---|---|---|---|
| Rule-based baseline | Alias dictionary (EN/HI/Roman) for ~15 instruments, voice-mode keywords ("no singing", "song", "Hindi"), duration regex, mood lexicon to recipe + chips; deterministic, offline, testable | Cannot handle analogies ("like missing the last train"), cannot write lyrics, cannot rewrite refine requests beyond keyword chips | Always available; labelled "Basic planner". Mandatory so the app never fakes AI. |
| Anthropic API via env key | Best structured-output reliability; clean terms; per-call cost (tiny) | `ANTHROPIC_API_KEY` is not set; needs the user to create/pay | Supported provider #2; do not block on it. |
| Local `claude -p` CLI | Present now (`claude 2.1.260`); `--json-schema`, tools can be disabled, no key; runs under the user's login | Latency (seconds to tens of seconds), non-deterministic, uses subscription quota; **verify Anthropic's current terms for automated/app use of a subscription login before relying on it**; must run from an empty temp dir with `--bare` so the user's memory/CLAUDE.md/hooks do not leak into the planner prompt; sends the brief to Anthropic | Supported provider #1 for MVP-1/2, **opt-in toggle**, visible badge "Smart planner (Claude CLI)". |
| Local LLM (MLX / Ollama) | Offline, free | No weights present; ollama server down; 7-8B quality is weak for nuanced Hindi lyrics; multi-GB download (needs the user's consent) and GPU/RAM contention with ACE | Defer behind the same interface (MVP-3 candidate). |

Recommended design (v2 section 8): a single `Planner.plan(brief, controls,
context) -> BriefCard` interface; the LLM only fills a small, schema-validated
card (voice mode, lead, 2-3 supports, feeling words, arc, pace, recipe id,
optional <=120-char flavour clause, lyric policy/topic, rewritten refine
patch). **A deterministic compiler writes the final caption, never the LLM**
(budget guarantee, drop order, exact-lyrics protection, copyright strip).
Failure or timeout of the smart planner falls back to the rule-based card with
a visible banner. "Write for me" lyrics are disabled when no smart provider is
configured (no template lyrics pretending to be AI).

## 7. Reliability classification summary

(Full matrix in Appendix B.) Classes: **(a)** real engine input or real audio
operation; **(b)** soft prompt direction that may be ignored; **(c)** needs
score/stems/multitrack we do not have; **(d)** unverified/aspirational.

Genuinely (a): duration, bpm, keyscale, timesignature (metadata), seed,
`instrumental`, lyrics text and language code, steps, number of takes,
cover/repaint inputs (as inputs), trim/fade/gain/loudnorm/format conversion,
splice with assert-equal outside a region. Even for (a) engine inputs the
*adherence* of the output (is it really 82 BPM / D major / 168 s?) is unmeasured
except duration (ffprobe in AUDIO_CATALOGUE: 168.000000).

## 8. Risks (queue, memory, restart, copyright, lyrics)

| Risk | Real situation | Mitigation |
|---|---|---|
| Queueing on a shared Mac | ComfyUI resident, video queue on :8388 (idle now) | Single worker; pre-start gate on :8388; cap queue depth; show "Mac busy" |
| Long renders | 20-30 s per take at 130-170 s; unknown at 240-600 s | Cap 240 s in MVP; measure in M0; progress as phase + elapsed |
| Memory | Not measured; ACE reports 37.4 GB budget; ComfyUI may load video models later | Measure peak RSS in M0; one process at a time; per-job subprocess frees memory |
| Restart safety | Jobs are short | SQLite state machine; startup sweep; partial dirs renamed on success only |
| Cancel | Subprocess kill is real | Document: queued = instant, running = SIGTERM then SIGKILL after 3 s |
| Disk | 25 GiB free, 98% used | Guard + FLAC native + prune |
| Copyright / remix | F14 | Strip names, no third-party audio, personal-use stance |
| Lyric exactness | F07 | Input-exact only; Hindi experimental; 3 takes |
| Prompt injection via brief to smart planner | LLM could emit a hostile card | Schema validation, instrument allow-list, caption built by code, lyrics never LLM-rewritten in exact mode |

## 9. What the PRD got right (keep)

- Brief is the only required input; Auto everywhere else (PRD section 1.1).
- Creative request vs actual audio edit (section 1.3); capability classes (section 11).
- Song refrain vs background choir wording (section 7).
- Immutable versions; never overwrite a favourite; save request, seed,
  plan, native output, master (AGENTS.md).
- Human acceptance separate from technical checks (section 15).
- Exact lyrics as an immutable source with a hash.
- Single heavy worker; fresh `runs/` folder; no mocked success.

---

## Appendix A: disposition of all 104 controls

Codes: **V** = visible control in v2 (id in brackets); **D** = Producer drawer;
**P** = stored/derived by planner, no UI; **M** = merged into another control;
**L** = later, with named prerequisite; **X** = cut (impossible or no value).

| # | key | Disposition | Note |
|---|---|---|---|
| 1 | brief | V [C1] | |
| 2 | view | X | UI state, not a music control |
| 3 | mode | V [C2] | |
| 4 | purpose | P | derive duration/loop hint from brief |
| 5 | mood | V [C7] | chips; free text still works |
| 6 | energy | M -> C9/C10 | pace + arc cover it |
| 7 | palette | P | follows instruments + recipe |
| 8 | duration_seconds | V [C3] | |
| 9 | avoid | V [C12] | planner-side omission |
| 10 | inspiration | M -> C1 | plus copyright strip |
| 11 | instruments.ids | V [C6] | validated list only |
| 12 | instruments.role | M -> C6 | lead star only |
| 13 | instruments.priority | P | compiler rank |
| 14 | instruments.presence | X | duplicate of role/how full |
| 15 | instruments.tone | P | adjectives from recipe |
| 16 | instruments.delivery | V [C11] | one control for the lead |
| 17 | instruments.density | M -> C9 | |
| 18 | instruments.register | P | |
| 19 | instruments.articulation | L | needs evidence per instrument |
| 20 | bansuri.ornaments | M -> C11 | |
| 21 | bansuri.breathing | X | |
| 22 | guitar.technique | L | |
| 23 | strings.technique | L | |
| 24 | brass.technique | L | |
| 25 | synth.kind | L | |
| 26 | instrument.sections | L | needs timeline/stems |
| 27 | instrument.relationship | P | planner decides answer/support |
| 28 | voices.lead | V [C13] | |
| 29 | voices.tone | P | |
| 30 | voices.register | P | |
| 31 | voices.delivery | P | spoken/rap mode cut |
| 32 | choir.enabled | M -> C14 | |
| 33 | choir.scale | V [C14] | four values |
| 34 | choir.target_count | X | not honourable |
| 35 | choir.content | P | derived from mode |
| 36 | choir.relationship | P | |
| 37 | choir.presence | P | |
| 38 | choir.sections | L | needs timeline |
| 39 | choir.distribution | X | SATB claim |
| 40 | voices.vibrato | X | |
| 41 | voices.melisma | X | and the hybrid evidence argues against over-constraining |
| 42 | voices.duet_pattern | X | |
| 43 | lyrics.policy | V [C16] | Write / Exact in MVP |
| 44 | lyrics.text | V [C17] | |
| 45 | lyrics.language | V [C15] | |
| 46 | lyrics.script | P | detect; never transliterate user text |
| 47 | lyrics.topic | M -> C1 | |
| 48 | lyrics.perspective | P | LLM writing detail |
| 49 | lyrics.style | P | |
| 50 | lyrics.hook | P | |
| 51 | lyrics.locked_lines | X | exact mode covers it |
| 52 | lyrics.allowed_changes | L | with "Adapt" policy |
| 53 | lyrics.explicitness | X | fixed "clean" |
| 54 | lyrics.forbidden_words | M -> C12 | |
| 55 | lyrics.imagery | P | |
| 56 | lyrics.rhyme | P | |
| 57 | lyrics.pronunciation | L | needs a Hindi evaluation |
| 58 | lyrics.languages_by_section | L | |
| 59 | lyrics.repeat_policy | P | fixed "preserve" |
| 60 | tempo.bpm | V [C8] + D [C22] | chips + exact BPM |
| 61 | rhythm.feel | X | prompt word only |
| 62 | rhythm.busyness | M -> C9 | |
| 63 | melody.character | P | recipe/planner |
| 64 | melody.variation | X | |
| 65 | arrangement.density | V [C9] | |
| 66 | arrangement.arc | V [C10] | |
| 67 | ending.kind | P | part of arc template; End fade [C25] is the real op |
| 68 | rhythm.meter | X | only 4/4 validated |
| 69 | rhythm.syncopation | X | |
| 70 | rhythm.pattern | X | |
| 71 | harmony.key | D [C23] | real metadata |
| 72 | harmony.colour | X | |
| 73 | harmony.progression | X | impossible (LM off) |
| 74 | harmony.modulation | X | impossible |
| 75 | melody.range | X | |
| 76 | melody.counterline | X | |
| 77 | structure.sections | P | compiled from arc; lyric tags |
| 78 | structure.climax | M -> C10 | |
| 79 | structure.silence | X | |
| 80 | transition.kind | X | |
| 81 | export.format | V [C21] | |
| 82 | export.sample_rate | P | fixed 48 kHz |
| 83 | master.target_lufs | P | fixed preset |
| 84 | master.true_peak | P | fixed preset |
| 85 | master.fade | D [C25] | end fade seconds |
| 86 | job.takes | V [C4] | default 3 |
| 87 | job.budget | X | replaced by disk/GPU guard |
| 88 | project.favourite | V [C18] | |
| 89 | project.locks | X | auto-pin user-touched fields |
| 90-96 | mix.part_* (7) | X | stereo only; revisit as 4-stem lab |
| 97 | reference.hum | L | needs conditioning model |
| 98 | reference.keep_melody | X | impossible on text path |
| 99 | structure.cue_points | L | |
| 100 | harmony.raga | X | words in brief only |
| 101 | rhythm.tala | X | words in brief only |
| 102 | novelty.budget | X | |
| 103 | ending.loop | L | real op (crossfade loop), later |
| 104 | repair.region | L | M6 pilot, experimental |

Counts over the 104 rows: **V 18, D 2, M 10 (merged into a V control),
P 25 (planner-internal, no UI), L 14 (later), X 35 (cut)**. These map to the
25 controls C1-C25 in v2; C5 (sound recipe), C19 (change request), C20
(another / more like this), C24 (seed) are new and have no catalogue row,
which is itself a finding: the catalogue modelled settings, not the actions a
beginner repeats daily (listen, pick, change, try again).

## Appendix B: reliability matrix (a/b/c/d)

| Feature | Class | Basis |
|---|---|---|
| Duration target | (a) | engine input; ffprobe on all accepted files shows exact duration |
| Seed, number of takes | (a) | engine input |
| BPM, key, time signature | (a) input / (d) adherence | passed as metadata; no measurement that output matches (BPM estimators fallible per LOCAL_SETUP) |
| `instrumental` flag + `[Instrumental]` | (a) | Yamuna/Moonlit; whether voices leak is a listening question |
| Wordless choir via vowel lyrics | (a) input / (b) result | Daylight |
| Sung lyrics, Devanagari, `hi` | (a) input / (d) diction | Thodi; ASR garbled |
| Sung English lexical lyrics | (d) | not evaluated anywhere |
| Lead instrument identity (bansuri etc.) | (b) | caption word; Earshot tags fallible |
| Support instruments, "sparse", "gentle" | (b) | |
| Ornaments / virtuosity | (b), (d) for quality | |
| Arc / sections / climax | (b) | tags and words; boundaries not guaranteed |
| Choir scale words | (b) | |
| Exact headcount | (d), cut | |
| Avoid / negative | (b), weak | no CFG on turbo |
| Raga / tala | (d) | |
| Exact notes, chords, melody keep | (c) | |
| Per-instrument fader/pan/EQ | (c) | stereo only; 4-stem estimate max |
| Stem separation | (a) operation, (c) for instruments | HDemucs 4 sources |
| Trim, fade, gain, loudnorm, MP3/WAV | (a) | ffmpeg; reference scripts |
| Splice with sample-equal outside region | (a) | local op |
| Repaint content quality / singer retention | (d) | pilot |
| Cover-based refine | (d) | used in rejected remix; never evaluated for self-refinement |
| retake_variance variation | (d) | untested |
| flow_edit_morph | (d) | untested, v1 limits |
| Lego / extract / complete | unavailable | base checkpoint only |
| Guidance scale | unavailable | overridden to 1.0 on turbo |
| ASR lyric check | (a) runs / (d) value | garbled on Hindi sung |
| Earshot checks | (a) technical only | taste excluded by its own docs |
| LLM planning, lyric writing | software, not engine | needs a provider (F08) |
| Copyright detection | none | rule-based name stripping only |
