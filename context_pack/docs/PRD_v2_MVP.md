# Raag Studio: revised product plan (v2, MVP-first)

Status: recommendation from the critical review (`PRD_CRITIQUE.md`). Supersedes
the working-set parts of `prd/Music_Studio_PRD.md` for implementation
purposes; the old PRD stays as history. 24 Oct 2026.

Conventions used below. Test labels: **[M]** mechanical, CPU only, any agent
can run; **[M-GPU]** mechanical but needs a native terminal with Apple MPS
(a restricted sandbox may not expose the GPU; do not fall back to CPU);
**[H]** needs a human to listen or judge, nobody else may sign it off.
Capability classes: **(a)** real engine input or real audio operation;
**(b)** soft prompt direction, may be ignored; **(c)** needs score/stems/
multitrack we do not have; **(d)** unverified/aspirational.

---

## 1. Product in one paragraph, and the principles that decide disputes

Raag Studio is a **personal, local, single-user** web app on Siddhant's Mac.
He types what he feels or imagines. The app plans, writes one compact
engine request from proven templates, renders **three** real ACE-Step turbo
takes in about two minutes, lets him play, heart and compare them, ask for
changes in plain words, and export MP3/WAV. It keeps every take forever
(immutable) and learns which sounds he loves.

Principles:

1. **The brief is the only required input.** Everything else is Auto.
2. **Three takes beat thirty knobs.** A take costs about 25 s. Sampling is the
   quality lever we can prove; controls are not.
3. **Never claim control we do not have.** Each control carries its
   capability class in the plan view; no instrument faders, headcounts, melody
   locks, raga guarantees.
4. **Exact lyrics means "sent unchanged"**; whether it was *sung* correctly is
   a listening question and the UI says so.
5. **Human taste decides.** Machine checks catch breakage only. Never auto-rank
   takes. Never transfer approval from one recording to another.
6. **No mocked success.** A fake engine exists only for unit tests and is
   visibly labelled in every response and screen.
7. **Local and reversible.** Everything inside this root; fresh run folders;
   favourites never overwritten; stop only processes the app started.

## 2. Persona and daily flow

**Persona (only one): Siddhant**, music beginner, expresses feelings, stories,
analogies; likes Indian acoustic instruments; Hindi and English; judges by
whether the melody moves him ("such a melody man"). He will not learn BPM or
key vocabulary and should never have to.

**Daily flow (the whole product):**

1. Type a brief ("the quiet right after rain, someone playing flute on the
   ghat, tabla barely there"). Optionally tap a **sound I liked** card.
2. Press **Create**. See the plan summary appear (what leads, what supports,
   voice mode, length) with provenance tags, and a progress strip:
   `queued -> loading model -> take 1/3 -> take 2/3 -> take 3/3 -> checking`.
3. Listen to T1, T2, T3. Heart one or more. Optionally tap a reason (melody,
   too busy, voice, ...).
4. Say what to change ("less busy, slower, more flute") or tap a chip;
   press **Make new versions**, or **Another take** unchanged.
5. Export the keeper as MP3 or WAV. Later: find it in the library with its
   plan, seed and exact request.

## 3. Stack and environment decision

Facts checked (read-only): system `python3` 3.14.7 (Homebrew; python@3.12 also
installed); ACE venv Python 3.12.14 with torch 2.11.0, MLX 0.32.4, FastAPI
0.159.1, uvicorn 0.54.0; Node v26.3.0 / npm 11.16.0; SQLite 3.53.4; FFmpeg
9.0.1 at `/opt/homebrew/bin`; `claude` 2.1.260 at `~/.local/bin`; no
`ANTHROPIC_API_KEY`; disk 25 GiB free (98% used); ComfyUI resident, video
queue API at `:8388` idle.

Decision: **FastAPI + SQLite (WAL) + filesystem store + a no-build static
frontend (HTML + ES modules, hand-written, offline, no CDN).**

Why, and why not React:
- One user, localhost, about 25 controls, one audio player. A bundler,
  `node_modules` and a TypeScript toolchain on a very new Node cost more than
  the whole UI. Vendored files only; works offline.
- Python is where everything else lives: engine, ffmpeg orchestration,
  planner providers, tests.
- Revisit React only if a timeline/waveform editor lands (backlog).

Layout (all inside `raag-studio/`):

```
app/backend/        FastAPI app, planner, compiler, queue, db, exports
app/engine/         run_takes.py  (runs under the ACE python, never in the API process)
app/web/            index.html, app.css, js/*.js  (served as static files)
app/recipes/        r1_flute_focus.json, r2_warm_ensemble.json, r3_hindi_ballad.json, r4_fusion.json
app/tests/          pytest (backend), fixtures/briefs.jsonl
data/raag.db        SQLite;  data/server.pid ; data/settings.json
runs/<song_id>/<round_id>/   native audio, previews, request.json, result.json, log
scripts/            preflight.py, start.sh, stop.sh (stop kills only the pid in data/server.pid)
```

Python environments: the API runs in its **own venv inside `app/.venv`**
(Python 3.12 from Homebrew to match ACE; fastapi, uvicorn, pydantic, httpx,
pytest; no torch). The worker is a **subprocess using
`../tools/acestep-venv/bin/python`** read-only. Do not import torch in the
API; do not upgrade the shared venv. Bind `127.0.0.1:8477` only (configurable).

## 4. Final control set: 25 controls, 9 always visible

All Auto unless stated. "Class" is the honesty label shown on hover.

**Create screen (always visible, 5 inputs + the Create button)**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C1 | Brief (required) | free text | planner input | n/a |
| C2 | Voice | Auto / Instrumental / Wordless voices / Sung words | `instrumental`, lyrics skeleton | (a) input, (b) result |
| C3 | Length | Auto (about 2:30) / about 1 min / about 2 min / about 3 min | `duration` (cap 240 s until M0 measures) | (a) |
| C4 | Versions | 1-4, default 3 | number of seeds | (a) |
| C5 | Sound I liked | none / Flute focus / Warm ensemble / Hindi ballad / Fusion (unrated) | recipe template (section 5) | (b) |

**Shape it (one disclosure, all optional)**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C6 | Instruments | chip picker, validated list of 15 (section 5.4); tap = include, star = lead | lead + up to 3 supports | (b) |
| C7 | Feeling | multi chips: peaceful, tender, yearning, joyful, epic, dark (+ words from brief) | mood adjectives | (b) |
| C8 | Pace | Slow / Medium / Lively (Lively = unproven) | `bpm` bucket 68-78 / 80-96 / 100-116 | (a) input, (d) adherence |
| C9 | How full | Spare / Balanced / Full | support count and wording | (b) |
| C10 | Story of the piece | Steady / Slow build / Quiet middle then bloom | arc sentence + section tags | (b) |
| C11 | Playing style (lead) | Simple / Singing / Ornate | lead-technique terms | (b) |
| C12 | Avoid | free text | planner omission, never "no X" in caption body; structural flags | (b), weak (turbo has no CFG) |

**Voices (shown only if C2 includes voices)**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C13 | Singer | Auto / Male / Female / Duet | lead-voice phrase | (b) |
| C14 | Background voices | None / Light harmonies / Choir / Big choir (approximate, label says so) | choir phrase + wordless lyric lines | (b) |
| C15 | Language | Hindi (experimental) / English (sung: untested) / other (experimental) | `vocal_language` | (a) input, (d) diction |

**Lyrics (shown only if C2 = Sung words)**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C16 | Lyrics source | Write for me (needs smart planner) / Use my words exactly | policy | n/a |
| C17 | My lyrics | text (when "exactly") | `lyrics`, sha256 stored | (a) input, (d) sung adherence |

**After listening**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C18 | Favourite + rating | heart; love/fine/no; reason tags | feedback events | n/a |
| C19 | Change request | free text + chips (section 6) | plan patch, new round | (b) |
| C20 | Another take / More like this | two buttons; "More like this" hidden until E2 passes | new seeds / `retake_variance` | (a) / (d) |
| C21 | Export | MP3 or WAV (24-bit 48 kHz) | ffmpeg | (a) |

**Details drawer (collapsed, labelled "for later")**

| ID | Control | Values | Maps to | Class |
|---|---|---|---|---|
| C22 | Exact BPM | 60-140 | `bpm` | (a) input, (d) adherence |
| C23 | Key | list (D major default family) | `keyscale` | (a) input, (d) adherence |
| C24 | Seed | read-only; "reuse seed" | `seed` | (a); not a similarity dial |
| C25 | End fade seconds | 0-8 | ffmpeg afade on export | (a) |

Total 25. Visible without opening anything: C1-C5 plus, after a render,
C18-C21 = 9. Fixed, non-controls: 48 kHz, -16 LUFS / -1.5 dBTP export,
engine normalisation -1.5 dB with 0.04-0.08 s fade in and 2-3 s fade out.

**Explicitly cut (35 catalogue rows) or deferred (14)** with reasons:
`PRD_CRITIQUE.md` Appendix A. Standing rule: a new control needs (i) a
capability class (a) path or (ii) a blind-listening result showing it changes
what he likes.

## 5. Style recipes, the compiler, and the taste ledger

### 5.1 Recipes are data

`app/recipes/*.json` hold: id, display name, status (`accepted` /
`accepted_with_caveat` / `unrated`), evidence pointer (the preserved
`recipes/<x>/request.json`), slots for the compiler, default metadata,
and lyric skeleton. R1-R3 are Siddhant's accepted pieces turned into
parameterised templates; they are **starting points that he liked, not proven
rules**.

| Recipe | Status | Defaults |
|---|---|---|
| R1 Flute focus (Yamuna) | accepted | instrumental; lead bansuri; tabla gentle, tanpura drone, santoor sparse; 82 BPM, D major; 168 s |
| R2 Warm ensemble + wordless choir (Daylight) | accepted | piano hook answered by flute, fingerpicked guitar, legato strings, round bass, soft groove; wordless choir in chorus via vowel lyric lines; 88 BPM, D major; 132 s |
| R3 Hindi ballad (Thodi) | accepted with diction caveat, **experimental** | warm male lead, Hindi, guitar/piano/bass/brushed drums/strings; 76 BPM, D major; 152 s |
| R4 Fusion (Moonlit) | **unrated**; hidden until Siddhant rates it | 104 BPM, G major; tabla/ghatam, santoor, sitar, violin answers; 144 s |

Blocked style L1: no dry a-cappella / "one note per syllable" / "no melisma" /
"no reverb" wording for sung modes (that vocal prompt produced the rejected
"someone reading" result; weak causal evidence, but it is the only contrast
on file).

### 5.2 Compiler: deterministic, code-built, budgeted

Input: a validated plan (section 7). Output: `caption`, `lyrics`, `params`,
and a `compile_report` (char count, dropped items in order, warnings,
conflicts). The LLM never writes the final caption in MVP-1/2.

Caption grammar (slots in order, derived from the accepted captions):

1. Format + lead + support ("Instrumental Indian bamboo flute solo with gentle
   tabla, tanpura drone and sparse santoor.")
2. Lead-priority sentence ("Bansuri is the loud clear melodic lead in every
   section.")
3. Tone + up to 4-5 technique terms from C11
4. One melody/feeling sentence (from C7 plus recipe)
5. Arc in 3-5 beats (from C10)
6. "NN BPM, <key>."
7. Voice-constraint tail ("Strictly no voices." for instrumental)
8. Optional <= 120-char flavour clause (smart planner or user words)

Budget: hard cap 512 characters (`len(caption)`); target <= 510. **Drop order**
when over budget: flavour clause, the "how full" sentence (the supports' presence words carry it; changed 2026-10-24
after a Yamuna-style plan lost all three named supports to it), optional supports (lowest rank first),
technique terms beyond three, arc beats beyond three, mood adjectives. **Never
dropped**: lead instrument, lead-priority sentence, voice-constraint tail,
BPM/key. If those alone exceed the cap: return `OverBudget` (never truncate).
Lyrics hard cap 4000 characters (docstring says 4096), never truncated.

Voice modes:
- Instrumental: `instrumental=True`, `lyrics="[Instrumental]"`, `vocal_language="en"`.
- Wordless: `instrumental=False`, lyric skeleton like Daylight (`[Intro]
  [Instrumental]`, `[Verse] [Instrumental]`, `[Chorus]` with `Ooh/Aah` lines,
  ...). A wordless request can never set `instrumental=True`.
- Sung: `instrumental=False`, `vocal_language` from C15, lyrics = user text
  (exact) or LLM draft, with `[Verse]/[Chorus]` tag lines inserted by code in
  separate lines. Exact text is byte-preserved apart from tag lines and
  newline normalisation.

Engine defaults (fixed): `task_type=text2music`, `inference_steps=8`,
`thinking=False`, all `use_cot_*=False`, `shift=1.0` (until E1),
`timesignature="4"`, `enable_normalization=True`, `normalization_db=-1.5`,
`fade_in_duration=0.04-0.08`, `fade_out_duration=2-3`, `audio_format="flac"`
native (halves disk; M0 verifies), `batch_size=1` serial (as every reference
script), `use_random_seed=False` with an explicit seed list. Receipts store
**requested and effective** parameters (effective `guidance_scale=1.0` for
turbo).

Conflicts the compiler resolves and reports (never silently): instrumental +
choir (voices dropped, user told); wordless + sung lyric (lyric kept only if
Sung); exact lyrics + duration mismatch (section 5.3); two simultaneous leads
(second becomes support); named song/artist in brief (stripped, reported).

### 5.3 Lyric duration fit (heuristic from one data point)

Thodi: 26 lyric lines over 152 s, about 5.8 s per line including instrumental
intro/outro. Rule of thumb for the planner: `suggested_seconds = round(5.8 *
lines / 4) * 4`, clamp 45-240. Under 8 lines: offer (1) a short sketch of
45-60 s, (2) user-approved repeats (explicit and recorded), (3) go back and
add lines. Never silently repeat or delete lines. Over 40 lines: suggest the
cap and warn. Mark in the UI as an estimate.

### 5.4 Validated instrument list for C6 (15)

bansuri/flute, tabla, tanpura, santoor, sitar, ghatam, violin, cello, strings,
piano, acoustic guitar, bass, light drums/percussion, choir (via C14), harmonium
(aliased, unvalidated). Evidence exists only for the first nine in recipes and
the user's liking; the rest are plausible. Other instruments can be typed in
the brief and pass into the caption as plain words; no control claims them.

### 5.5 Taste ledger

Every take can receive: favourite, rating (love / fine / no), reason tags
(melody, instrument, voice, rhythm, diction, too busy, too plain, wrong mood),
free note. Stored as append-only events. Views: per recipe "loved N of M
takes", per instrument lead, per pace bucket. Uses: default recipe suggestion,
input to blind A/B pilots (M6), honest evidence that grows with use. No take is
auto-ranked.

## 6. Refine: what it can honestly mean

The change-request box (C19) and its chips always produce a **new plan
revision and new takes** unless a real audio op is chosen. Wording shown to the
user: *"These are new performances from an updated plan. They will not be exact
edits of T2."*

| Action | Mechanism | Class | Ships in |
|---|---|---|---|
| Another take | same plan, new random seeds | (a) | MVP-1 |
| Change request / chips | patch the plan, recompile, new seeds | (b) | MVP-1 (chips, rules) / MVP-2 (free text, smart planner) |
| End fade, trim end, export | ffmpeg | (a) | MVP-1 |
| More like this | `retake_variance` (and `retake_seed`) on a liked take's seed | (a) input / (d) effect | after E2 passes |
| Re-arrange keeping structure | `task_type=cover` with `audio_cover_strength` 0.5-0.8 on a take + new caption (duration locked) | (d) | after E3 passes |
| Redo a section | `repaint` with `explicit` mask + local splice, assert samples equal outside the region | (a) splice / (d) content, voice may change | after E4 passes |
| Edit toward words | `flow_edit_morph` over cover | (d) | after E5 passes |
| Never | keep melody, louder flute, exact doubling, lego/extract/complete | (c) | not offered |

Chip to patch table (rules provider can execute these without an LLM):

| Chip | Patch |
|---|---|
| Less busy | How full one step down; drop lowest-ranked optional support; tail "sparse accompaniment" |
| More melodic | lead delivery = Singing; add "memorable recurring melody" |
| Slower / Livelier | BPM -8 / +8 (clamped to C8 range) |
| Warmer / Brighter | swap tone adjectives |
| Different lead | promote next support to lead; old lead becomes support |
| More voices / Fewer voices | C14 one step |

Seeds are independent noise: "nearby seed" gives nothing similar. The app
never offers seed nudging.

## 7. Data model and plan schema

Entities (SQLite; ids are ULIDs; `plans`, `requests`, `takes` are immutable;
only `feedback` is appended):

- `songs(id, title, brief, created_at, archived)`
- `plans(id, song_id, rev, source, card_json, controls_json, provenance_json,
  brief_sha256, created_at)` where `source` is `rules | claude_cli | anthropic_api | user_edit | recipe`
- `rounds(id, song_id, plan_id, kind, parent_take_id, request_text, created_at)`
  with `kind` in `create | another | refine | variation | cover | repaint`
- `requests(id, round_id, compiled_json, compile_report_json, lyrics_sha256, sha256)`
- `jobs(id, round_id, idempotency_key UNIQUE, state, attempts, pid, phase,
  progress_json, error, queued_at, started_at, finished_at)` with `state` in
  `queued | running | succeeded | failed | cancelled | interrupted`
- `takes(id, round_id, ordinal, seed, native_path, preview_path, duration_s,
  sample_rate, channels, requested_params_json, effective_params_json,
  timings_json, checks_json, engine_rev, created_at)`
- `feedback(id, take_id, kind, value_json, created_at)` (favourite, rating, tags, note)
- `exports(id, take_id, format, fade_out_s, trim_end_s, loudness_json, path, sha256, created_at)`
- `settings(key, value_json)` (planner provider, ports, thresholds)

File store: `runs/<song_id>/<round_id>/take_<n>.flac`, `preview_<n>.mp3`,
`request.json`, `result.json`, `engine.log`; written to a `.partial` folder
and renamed on success only. Exports under `runs/<song_id>/exports/`.

Plan `controls` (user-set) and `card` (planner-suggested) are kept separate;
each field carries provenance `you | suggested | recipe | rule` plus the
reason string. User-touched fields are auto-pinned (no separate lock UI).
Lyrics policy `exact` stores the source text and hash immutably.

Minimal plan JSON (replaces `Creative_Plan.schema.json` for MVP; unknown fields
rejected, unknown instrument ids rejected):

```json
{
  "schema_version": "2.0",
  "brief": "string, required, non-blank",
  "recipe_id": "r1_flute_focus | r2_warm_ensemble | r3_hindi_ballad | r4_fusion | null",
  "voice_mode": "instrumental | wordless | sung",
  "duration_s": 150,
  "lead": { "instrument": "bansuri", "style": "singing | simple | ornate" },
  "supports": [ { "instrument": "tabla", "role": "rhythm|drone|harmony|answer|texture", "presence": "sparse|gentle|full" } ],
  "feeling": ["peaceful", "tender"],
  "pace": { "bucket": "slow|medium|lively", "bpm": 82 },
  "key": "D major",
  "arc": "steady | slow_build | quiet_middle_bloom",
  "fullness": "spare | balanced | full",
  "voices": { "singer": "auto|male|female|duet", "background": "none|light|choir|big", "language": "hi|en|..." },
  "lyrics": { "policy": "none|write|exact", "text": null, "topic": null },
  "avoid": ["crowded accompaniment"],
  "flavour": "string <= 120 chars, optional",
  "notes_for_user": ["why the planner chose X"],
  "takes": 3
}
```

## 8. Planner design

One interface, three providers, one deterministic compiler.

```
Planner.plan(brief, controls, context) -> BriefCard     # schema-validated
Planner.patch(plan, request_text)      -> PlanPatch     # for C19
Planner.draft_lyrics(plan)             -> LyricsDraft   # smart only
```

Providers:
1. **Basic planner (rules)**: always on. Alias dictionary (English, Devanagari,
   Roman Hindi) for the 15 instruments; voice keywords ("no singing",
   "instrumental", "song", "Hindi", "ooh"); duration regex; mood lexicon to
   recipe and chips; chip patches. Cannot read analogies, cannot write lyrics.
   UI badge: "Basic planner". If nothing matches, falls back to R1 or R2 and says
   which words it matched.
2. **Smart planner via local `claude -p`** (opt-in toggle in Settings): runs
   in an empty temp cwd with `--bare`, tools disallowed, `--json-schema` of the
   BriefCard, 60 s timeout, one retry on invalid JSON, then fallback to Basic
   with a visible banner. Sends only the brief and control state to
   Anthropic. Verify Anthropic's current terms for automated use of a
   subscription login before relying on it; the API-key provider is the clean
   alternative.
3. **Smart planner via Anthropic API**: env `ANTHROPIC_API_KEY`; same schema
   and fallbacks. Not configured today.
4. Deferred: local MLX/Ollama model behind the same interface.

Hard rules: the LLM fills the card only; code builds the caption; exact lyrics
never pass through the LLM; instrument ids must be in the allow-list; briefs
are treated as untrusted text (prompt injection yields at worst a bad but
valid card); named songs/artists are stripped before compile with a note; "Write
for me" is disabled (not faked) under Basic.

## 9. Architecture: jobs, worker, restart, cancel, resources

```
Browser -> FastAPI (127.0.0.1:8477) -> SQLite jobs table -> one worker loop
       -> subprocess: ACE-python app/engine/run_takes.py <request.json> <out.partial>
       -> JSONL events on stdout -> API (SSE to browser) -> ffmpeg previews/checks -> files + rows
```

- **One heavy job at a time.** Queue depth cap 5.
- **Subprocess per round**: loads the model once (about 6 s), renders N takes
  serially, exits. Memory is freed by the OS; **cancel is a real kill**
  (SIGTERM, SIGKILL after 3 s); a crash cannot take the API down.
- **Pre-start gates**: MPS available (else fail with a clear message, never CPU);
  disk free >= 5 GiB; `GET :8388/queue` idle (connection refused counts as
  idle; busy keeps the job queued with reason `mac_busy`); free memory sanity
  check recorded.
- **Env for the worker**: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`,
  `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=4`; checkpoint directory is
  read-only to the app.
- **Idempotency**: `Idempotency-Key` header or client UUID; duplicate POST
  returns the existing job.
- **Restart recovery**: on boot, `running` rows become `interrupted`; any with
  `attempts < 2` go back to `queued` (attempt +1), others become `failed` with
  reason; `.partial` directories are deleted; a final directory without a
  `succeeded` row is quarantined, never reused.
- **Technical failure policy**: one automatic retry with a new seed for a
  take that fails checks; creative dissatisfaction never retries.
- **Progress**: phases and elapsed time from the worker JSONL (a per-step bar
  is not worth it for 25 s jobs).
- **Technical checks per take (breakage only)**: ffprobe decode OK; duration
  within 0.25 s of requested; sample rate 48 kHz, 2 ch; silent fraction < 5%
  (ffmpeg `silencedetect`); clipped fraction < 0.1% and true peak <= -1.0 dBTP
  (`astats`/`ebur128`). Shown as "Technical checks" separate from "Your
  verdict".
- **Disk hygiene**: previews are MP3 192 kbps for the player; native FLAC
  kept; masters (WAV 24-bit) only on export; prune action removes native
  audio of non-favourite takes older than N days (confirmed, never favourites).
- **Start/stop**: `scripts/start.sh` writes `data/server.pid`;
  `scripts/stop.sh` kills only that pid.

## 10. API sketch (JSON, localhost)

```
POST   /api/songs                      {brief, voice?, duration?, takes?, recipe?, shape?, idempotency_key} -> 202 {song_id, round_id, job_id, plan}
POST   /api/songs/{id}/plan            plan-only, no render -> {plan, compile_report}
GET    /api/songs                      list;  GET /api/songs/{id}  -> song + plans + rounds + takes + feedback
POST   /api/songs/{id}/rounds          {kind: another|refine|variation|cover|repaint, from_take?, request_text?, patch?, takes?, idempotency_key} -> 202 job
PATCH  /api/songs/{id}/controls        user edits (creates a new plan revision)
GET    /api/jobs/{id}                  state, phase, progress, error
POST   /api/jobs/{id}/cancel
GET    /api/events                     SSE: job progress, take_done
GET    /api/takes/{id}/audio           Range-capable stream (preview or native)
POST   /api/takes/{id}/feedback        {favourite?, rating?, tags?, note?}
POST   /api/takes/{id}/exports         {format: mp3|wav, end_fade_s?, trim_end_s?} -> export record + file url
GET    /api/system                     {mps, disk_free_gib, video_queue, engine_rev, planner_provider, version}
GET/PUT /api/settings                  planner provider and thresholds
POST   /api/admin/prune                {older_than_days, confirm:true}  never touches favourites
```

## 11. Engine-capability honesty table (single source: `app/backend/capabilities.json`)

The UI reads this file; tests assert every control id has an entry.

| Capability | Class | What we do | UI wording |
|---|---|---|---|
| Length | (a) | pass `duration`; verify with ffprobe | exact |
| Seed, take count | (a) | explicit seeds, serial | exact |
| BPM, key, meter | (a) input, (d) adherence | pass metadata; do not claim measured match | "target" |
| Instrumental / wordless / sung | (a) input, (b) result | `instrumental` + lyric skeleton | "request" |
| Lead and supports named | (b) | caption words | "creative direction" |
| Ornate / virtuosic | (b), (d) quality | technique words | "direction, not skill" |
| Arc and sections | (b) | caption beats and tags | "plan; boundaries not guaranteed" |
| Choir size words | (b) | scale words; no counts | "approximate" |
| Exact headcount | (d) | not offered | n/a |
| Avoid | (b), weak | omission + structural flags | "left out of the request; may still appear" |
| Raga, tala | (d) | words only, no control | n/a |
| Hindi singing | (a) input, (d) diction | `vocal_language=hi`, Devanagari | "experimental" |
| English sung words | (d) | untested | "untested" |
| Exact lyrics | (a) input, (d) sung adherence | byte-preserved text | "sent unchanged; listen to check" |
| Write lyrics | software (LLM) | smart planner only | "needs smart planner" |
| Faders, pan, EQ per instrument | (c) | not offered | n/a |
| Stems | (a) op, (c) for instruments | backlog: 4 estimated stems | "estimated" |
| Chords, exact notes, keep melody | (c) | not offered | n/a |
| Trim, fade, gain, loudness, format | (a) | ffmpeg | exact |
| Splice outside a region unchanged | (a) | sample-equality test | exact |
| Repaint / cover / retake / flow-edit | (d) | experiments E2-E5 | "experimental" |
| lego / extract / complete | unavailable | base checkpoint only | n/a |
| Guidance strength | unavailable | turbo forces 1.0 | n/a |
| Copyright clearance | none | name stripping only | "personal use" |
| Machine quality scores | not offered | checks are breakage-only | n/a |

## 12. Milestones and acceptance tests

Each milestone lists deliverables and tests. A sub-agent can execute all
**[M]** tests; **[M-GPU]** tests need a native terminal; **[H]** are signed
off only by Siddhant (record the answer in `data/acceptance.md`; an agent may
prepare the listening sheet but never fill the verdict).

### M0: Engine harness and measurements (no UI)

Deliverables: `app/engine/run_takes.py`, `scripts/preflight.py`,
`context_pack/docs/ENGINE_MEASUREMENTS.md`.

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M0-01 | [M] | `preflight.py --json` | keys `mps, disk_free_gib, video_queue, ace_python, checkpoints`; exit != 0 if disk < 5 GiB or MPS false |
| AT-M0-02 | [M] | `run_takes.py --dry-run req.json` | rejects caption > 512, lyrics > 4000, non-fresh out dir, `thinking=true`; does not import torch |
| AT-M0-03 | [M-GPU] | 1 take, yamuna request, new seed | exit 0; JSONL has `model_ready`, `take_done`, `done`; FLAC decodes; duration 168.0 +/- 0.25 s; 48 kHz, 2 ch; silent < 5%; clipped < 0.1% |
| AT-M0-04 | [M-GPU] | 3 takes in one process | model loaded once (second take starts < 1 s after first ends); `effective_params.guidance_scale == 1.0`; records wall time and peak RSS in ENGINE_MEASUREMENTS.md |
| AT-M0-05 | [M-GPU] | run with offline env | succeeds; checkpoint dir listing unchanged; no download attempted |
| AT-M0-06 | [M-GPU] | length scaling: 60/120/180/240 s | times recorded; if 240 s exceeds 120 s pipeline time or fails, MVP cap becomes 180 s |
| AT-M0-07 | [M] | SIGTERM mid-run | no final dir; `.partial` remains for sweep; process exits < 5 s |
| AT-M0-08 | [H] | listen to one take | "not broken, sounds like music": yes/no |

### M1: Compiler, recipes, rule planner (pure Python, no GPU)

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M1-01 | [M] | golden compile of R1-R3 default plans | caption <= 512; lead string present; bpm/key/duration equal recipe; R1 `instrumental` True and lyrics `[Instrumental]`; R2 False with only `Ooh/Aah` lines plus tags; R3 non-tag lyric lines equal the Thodi lyric |
| AT-M1-02 | [M] | exact-lyrics property test, 200 random multiline unicode strings | after removing code-inserted tag lines and normalising newlines, output == input exactly; sha256 matches |
| AT-M1-03 | [M] | over-budget plan (lead + 8 supports + 6 beats + 5 techniques) | caption <= 512; `dropped` in documented order; lead/voice tail/BPM-key kept; lead alone > cap returns `OverBudget`, no truncation |
| AT-M1-04 | [M] | conflict cases (instrumental+choir; wordless+instrumental flag; two leads) | conflict listed in `compile_report`; resolution applied; wordless never sets `instrumental=True` |
| AT-M1-05 | [M] | avoid handling | avoid terms absent from the caption body (allowed only inside the single voice tail) |
| AT-M1-06 | [M] | copyright strip: "like Ashes on the Fire", "in the voice of <artist>", "remix <song>" | names absent from caption and lyrics prompt; note recorded; "remix" flagged unsupported |
| AT-M1-07 | [M] | rule planner on `fixtures/briefs.jsonl` (30 briefs incl. Devanagari and Roman Hindi aliases) | >= 90% field accuracy; 100% on explicit "no singing/instrumental" and explicit durations |
| AT-M1-08 | [M] | lyric duration fit | 26 lines -> 152 +/- 16 s; 2 lines -> `too_short` with options, no auto-repeat; 80 lines -> cap + warning |
| AT-M1-09 | [M] | plan validation | unknown field rejected; unknown instrument rejected; blank brief rejected |
| AT-M1-10 | [H] | read three compiled captions next to the originals | "same intent?" yes/no each |

### M2: Backend vertical slice

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M2-01 | [M] | fresh DB bootstrap | tables exist, WAL on, `user_version` set |
| AT-M2-02 | [M] | POST empty brief / valid / duplicate key | 422 / 202 / same job id, exactly one job row and one run dir |
| AT-M2-03 | [M] | fake-engine mode | only with `RAAG_ENGINE=fake`; every response carries `engine:"fake"`; fake takes can never be exported as "real" |
| AT-M2-04 | [M-GPU] | real create: "A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes", takes=3 | job succeeds < 5 min; 3 takes, distinct seeds, each 120 +/- 0.25 s; plan voice=instrumental; request, requested and effective params, `engine_rev` stored |
| AT-M2-05 | [M] | `kill -9` server mid-job (slow fake engine) | after restart job re-queued once; no duplicate takes; `.partial` swept; second interruption -> failed with reason |
| AT-M2-06 | [M] | cancel queued and running | queued: immediate; running: worker pid gone within 5 s; state cancelled |
| AT-M2-07 | [M] | mock `:8388` busy / disk 2 GiB | job waits with reason `mac_busy` and starts when idle / submit rejected with clear error |
| AT-M2-08 | [M] | audio endpoint | Range returns 206 with correct Content-Range; sha256 of native file unchanged by favourite/export |
| AT-M2-09 | [M] | feedback and prune | feedback appends; takes/files untouched; prune refuses favourites and requires `confirm` |
| AT-M2-10 | [M] | export mp3 and wav | decodes; duration within 50 ms; integrated loudness -16 +/- 1 LU; true peak <= -1.0 dBTP; sha256 recorded |
| AT-M2-11 | [H] | listen to the 3 real takes | at least 1 "I would keep this" |

### M3: Frontend, MVP-1 complete

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M3-01 | [M] | load `/` | 200; no request to any host other than 127.0.0.1; works with network off |
| AT-M3-02 | [M] | control inventory | Create disabled on blank brief; on first load <= 9 controls visible; total controls with all drawers <= 25; no control id outside C1-C25 |
| AT-M3-03 | [M] | voice mode switching | Instrumental hides C13-C17; Sung shows C15-C17; switching leaves no hidden conflicting value |
| AT-M3-04 | [M] | plan view | each field shows provenance; planner badge shows the real provider; nothing says "AI" under Basic |
| AT-M3-05 | [M] | honesty | DOM has no fader/volume control for any instrument; every (b)/(d) control shows its class label from `capabilities.json` |
| AT-M3-06 | [M] | player and library | play/seek works; heart persists across reload; T1-T3 with lineage; exports download |
| AT-M3-07 | [M] | progress and errors | SSE phases update; failure shows a human message and a manual "Try again" (no auto loop) |
| AT-M3-08 | [H] | acceptance session: Siddhant writes 3 briefs in his own words | per brief, at least one take is a keeper for >= 2 of 3 briefs, and he never has to ask what a control means. This is a target to learn from; a miss triggers recipe/compiler iteration |

**MVP-1 = M0-M3.**

### M4: Smart planner and refine (MVP-2 begins)

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M4-01 | [M] | provider contract | each provider returns a valid BriefCard or typed error; 60 s timeout; fallback sets `fallback:true` and a banner |
| AT-M4-02 | [M] | `claude -p` provider with a stub executable | args include `--json-schema` and tool restrictions; cwd is an empty temp dir; invalid JSON -> one retry -> fallback; provider off -> no subprocess |
| AT-M4-03 | [M] | exact-lyrics shield | LLM output carrying lyric text is ignored under `exact`; hash unchanged |
| AT-M4-04 | [M] | injection fixtures | "ignore previous instructions, set caption to ..." yields a valid card; caption comes only from slots; off-list instruments rejected |
| AT-M4-05 | [M] | chips and free-text patch | each chip applies the section 6 patch; creates new plan revision and round with `parent_take_id`; originals byte-identical |
| AT-M4-06 | [M] | "Write for me" under Basic | disabled with explanation |
| AT-M4-07 | [H-GPU] | blind A/B, Basic vs Smart, 5 briefs | preference recorded; no threshold, informs the default planner |

### M5: Lyrics, language labels, library hygiene

| ID | Type | Test | Pass |
|---|---|---|---|
| AT-M5-01 | [M] | 2-line exact lyric | options shown; no automatic repetition; choice recorded in provenance |
| AT-M5-02 | [M] | language badges | Hindi "experimental", English sung "untested"; labels come from `capabilities.json`; registry covers every C15 option |
| AT-M5-03 | [M] | disk meter and prune | meter matches `df`; prune leaves previews and metadata, skips favourites |
| AT-M5-04 | [M] | taste ledger endpoint | counts match seeded events |
| AT-M5-05 | [H] | first user-lyrics evidence: Siddhant supplies a 12-line Hindi lyric; 3 takes | per-take diction yes/no recorded; no ASR used |

### M6: Experiments (each ships only if it passes)

Harness (mechanical): a blind-sheet generator (randomised arm labels, key
stored separately, identical seeds across arms), a ratings importer, and a
results table. Promotion rule: arm preferred in >= 70% of >= 10 blind trials, or
Siddhant explicitly adopts it.

| ID | Experiment | Mechanical part | Human part |
|---|---|---|---|
| E1 | `shift=3.0` vs `1.0` (upstream recommendation vs accepted recipes) | arms differ only in `shift`; same seeds | blind preference |
| E2 | `retake_variance` 0.1 / 0.3 / 0.5 from a favourite seed | records params; no crash | "similar but different?" rating |
| E3 | cover re-arrangement, strength 0.5 / 0.8, new caption | duration equals source +/- 0.05 s | keeps structure? sounds better? |
| E4 | repaint a span with local splice | max abs sample difference outside [start - xfade, end + xfade] == 0; no click above threshold at seams | melody and voice retained? |
| E5 | `flow_edit_morph` | runs without silence collapse (peak > -40 dBFS) | follows the words? |

### M7+: Backlog (not scheduled)

4-stem Stem lab (drums/bass/vocals/other, estimated); seamless loop export;
waveform and section cards; "Adapt my lyrics" with diffs; humming input;
other engines (score-conditioned, paid APIs); local MLX planner; more
instruments with evidence; hosted/multi-user variants.

## 13. MVP-1, MVP-2, backlog at a glance

| | Scope | Planner | Needs GPU tests |
|---|---|---|---|
| **MVP-1** (M0-M3) | brief -> 3 real takes -> play, heart, versions, export, plan view with provenance, chips refine, Another take | Basic (rules) | M0, M2, M3 |
| **MVP-2** (M4-M6) | Smart planner (Claude CLI / API), free-text change requests, Write-for-me lyrics, exact-lyrics flow, language labels, taste ledger, prune, promoted experiments | Basic + Smart | M4-M6 |
| **Backlog** | stems, loops, waveform, humming, alt engines, local LLM, hosted | n/a | n/a |

If Siddhant approves `claude -p` now (open question 1), pull the provider tasks
of M4 forward into M2/M3: it is the highest-value planner addition and keeps
the free-text box honest for analogy-heavy briefs.

## 14. Open questions only the user can answer

1. **Planner**: may the app call your local `claude -p` (opt-in, sends only your
   brief text to Anthropic, uses your subscription), will you provide an API key,
   or stay with the Basic planner for now? Without one of these, Write-for-me
   lyrics and free-text change requests stay off.
2. **Hindi at launch**: OK to ship Hindi as labelled "experimental" (one heard
   take, diction imperfect) and prioritise instrumental/wordless first?
3. **Ratings**: will you give one-tap love/fine/no on takes? The taste ledger
   and every A/B experiment depend on it.
4. **Moonlit Raas**: have you listened and what is the verdict? It decides
   whether R4 ships as an accepted recipe.
5. **Beyond slow and tender**: do you want fast, dark, electronic or cinematic
   music day to day? We have zero accepted examples there; each style needs a
   listening session before it gets a recipe.
6. **Scope of use**: strictly personal, never published? (Model-weight and
   output licence terms are unresolved; it also decides how strict the
   named-song policy must be.) Confirm that "remix a famous song" should be
   declined with an offer of an original piece in that mood.
7. **Storage**: only 25 GiB is free. Is auto-pruning native audio of
   non-favourite takes after N days (suggest 14) acceptable, and where should
   exports go?

## 15. Non-goals for MVP-1/2

DAW features; instrument faders; exact headcount; melody/chord control; raga
or tala guarantees; third-party audio upload or remixing; hosting, accounts or
publishing; training or voice cloning; automatic ranking of takes; a machine
"quality score".
