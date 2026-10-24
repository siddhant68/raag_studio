# Raag Studio

A local AI-music application: a feeling or a little story in, takes you can play, compare, change and export out.
**The app is implemented and runs.** Current run commands are in [Run](#run) below; current state and the next tasks
are in `STATUS.md` (section "Song pipeline"); the newest report is `reports/SONG_PIPELINE.md` (styles, song maps,
the songwriter, engine profiles, the old-versus-new listening batch).

Start here if you are a new agent: `reports/SONG_PIPELINE.md`, then `HANDOFF_NEXT_SESSION_2_2026-10-24.md` and
`HANDOFF_NEXT_SESSION_2026-10-24.md` (read order, decisions, musical history), `context_pack/docs/IMPLEMENTATION_DECISIONS.md`.

## History: the original handoff baseline (dated 24 October 2026, before any code existed)

The text between here and "Run" describes the project as it was handed over, **before the application was built**.
Where it says nothing is implemented, that is no longer true. `HANDOFF_PROMPT.md` is the same dated baseline.
Do not rebuild the app on that basis.

Prepared 24 October 2026 for Siddhant Pathak. `HANDOFF_PROMPT.md` was the copy-pasteable instruction for the agent that built it.

## Read order (baseline)

1. `HANDOFF_PROMPT.md`: mission, user requirements, musical history and completion criteria.
2. `context_pack/docs/PROJECT_CONTEXT.md`: decisions, experiments, accepted/rejected evidence and correction of stale notes.
3. `context_pack/examples/AUDIO_GUIDE.md`: what to hear and how the user judged it; playable files are included.
4. `context_pack/docs/prd/Music_Studio_PRD.md` or its PDF: the original proposed product (the working spec is now `context_pack/docs/PRD_v2_MVP.md`).
5. `context_pack/docs/SYSTEM_AND_RUNBOOK.md`: exact installation paths and safe operational commands (its advice to render with `scripts/render_local.py` is superseded: use the app or `app/engine/run_takes.py`).
6. `context_pack/docs/IMPLEMENTATION_REVIEW.md`: specification gaps that were to be resolved during implementation.
7. `context_pack/docs/research/` and `context_pack/third_party/`: supporting sources and downloaded guides.

## Folder contract

| Path | Purpose |
| --- | --- |
| `app/` | All future frontend/backend application source |
| `scripts/` | Context verification and fresh-output recipe rendering helpers |
| `data/` | Future local app state, database and imported assets |
| `runs/` | New generated takes, logs and exports |
| `context_pack/` | Preserved specifications, research, examples, recipes and inventory |

(Baseline statement, now superseded: the handoff task itself implemented no backend or frontend. They exist now under `app/`.)

## Verify without generating music

From this folder:

```sh
python3 scripts/verify_context.py
python3 scripts/render_local.py --recipe yamuna --dry-run   # dry run only; never use this script for a real render
```

The second command validates the preserved request and prints the resolved
engine/output settings. It does not import Torch, load models or generate audio.
Actual rendering needs the existing ACE Python and native Apple GPU access;
see the runbook before starting it. New renders always use a fresh run folder.

The handoff includes audio examples and source/configuration evidence. Large
model weights and Python environments remain in their existing shared locations
and are indexed explicitly. It is a self-contained context pack, not an offline
installation image for a different computer.

`context_pack/inventory/FILE_MANIFEST.json` records every bundled file hash.
The portable ZIP is at this project root and excludes itself from its contents.
It preserves this handoff baseline; the project can evolve independently after
archiving. Do not delete existing approved source projects.

## Run

Raag Studio is a FastAPI app plus a hand-written web page, both on `127.0.0.1:8477` (this computer only). Renders
run ACE-Step turbo in a subprocess (shared ACE python, Apple GPU only, never CPU). The API uses its own venv,
`app/.venv` (Python 3.12; packages in `app/requirements.txt`). The page has no build step and makes no outside requests.

```sh
python3 scripts/preflight.py        # GPU, disk >= 5 GiB, :8388 video queue idle, weights, ffmpeg
scripts/start.sh                    # background server; pid in data/server.pid, log in data/server.log
open http://127.0.0.1:8477/         # the app: Create, Library, Settings
scripts/stop.sh                     # stops only the pid in data/server.pid (checks it is uvicorn)
```

Using it: type a feeling or a little story and press **Create** (everything else is optional and stays Auto).
You get a plan (what leads, what supports, with a reason for each choice), a progress strip, then your takes.
Play them, mark favourites, say what to change with the quick chips, ask for **Another take**, and save MP3 or WAV.
The Library keeps every song with its plan, seeds and the exact request that was sent.

- Data: `data/raag.db` (SQLite, WAL). Audio: `runs/<song_id>/<round_id>/` (native FLAC, MP3 previews,
  request.json, result.json, engine.log), exports in `runs/<song_id>/exports/`. Override with
  `RAAG_DATA_DIR`, `RAAG_RUNS_DIR`, `RAAG_PORT`.
- One render at a time; a render waits (reason `mac_busy`) while the ComfyUI video queue on `:8388` is busy.
- API reference: `app/backend/API_NOTES.md` (plus the read-only `/api/recipes`, `/api/capabilities`, `/api/instruments`,
  `/api/ledger`, `/api/storage` added in M3, see `reports/M3.md`). Reports: `reports/M2.md`, `reports/M3.md`.
- Tests (CPU only, fake engine, temp dirs; no real render): `app/.venv/bin/python -m pytest app/tests -q`
  (includes the UI logic tests, which run `node --test`). The fake engine (`RAAG_ENGINE=fake`) exists only for tests,
  labels every response `engine:"fake"`, shows a red banner in the page, and is never a real render. Without that
  variable the app always uses the real engine.

### Song pipeline (styles, song maps, songwriter)

New songs pick a **Style** (38 presets, Hindi and English, sung and instrumental; or Auto from the brief's words)
and get a **song map**: the sections, their rough times, energy and who comes in. The caption follows ACE-Step's
own guide (genre, mood, voice, instruments, the section journey, production; tempo/key/meter as parameters) and the
lyrics carry section tags. With Claude on, sung songs get lyrics written section by section and checked (syllables,
hook, script, Hindi singer-gender agreement), with every chorus repeated word for word. Classic plans and the four
accepted recipes compile exactly as before; `song_pipeline: false` (Settings → Music engine, or
`RAAG_SONG_PIPELINE=0`) keeps new songs on the classic template unless a style or a new instrument is chosen.

Engine profiles (Settings → Music engine): `auto` (classic plans: shift 1.0; styled songs: shift 3.0), `classic`,
`shift3`, `lm` (+ 5Hz LM 1.7B), `xl` (XL turbo 4B), `xl_lm`. LM and XL weights are downloaded only by
`python3 scripts/fetch_models.py lm|xl` (asks first); a render never downloads.

Old-versus-new blind listening: `cd app && .venv/bin/python -m experiments.listening_batch prepare|render|reveal`
(see `reports/SONG_PIPELINE.md`). Personal ElevenLabs renders of a plan: `scripts/personal/elevenlabs_render.py`
(preview by default; never called by the app; personal use only).

### Status and limits (honest list)

- The default planner is **Basic rules** (keywords on this computer). It cannot read stories or analogies and cannot
  write lyrics. Smart planners (`claude -p`, Anthropic API) are built and **off by default**; the web page cannot turn
  them on. Turning one on is a deliberate `PUT /api/settings` that you make yourself, and it sends your brief text to
  Anthropic. (On the Mac the Claude CLI planner was switched on by the user on 2026-10-24.)
- **Nobody has listened to the song pipeline yet** (built in a cloud session without a GPU). Run the listening batch.
- **No take made by this application has a recorded human verdict yet** (the historical Yamuna, Daylight and Thodi examples do; see `context_pack/examples/AUDIO_GUIDE.md`). "Technical checks passed" only means the file is not broken
  (right length, not silent, not clipped). Whether it is good music is your verdict.
- Hindi singing is **experimental** and English sung words are **untested**. Exact lyrics are sent unchanged; only
  listening tells you whether they were sung correctly. Instrumental and wordless voices come first.
- Controls are creative direction, not guarantees: no per-instrument volume, no exact singer counts, no melody lock.
- "More like this", cover, repaint and similar edits are not offered (experiments).
- Instrumental section tags and the 5Hz LM / XL profiles are untested by ear; LM and XL also raise memory use.
- Disk is tight (about 30 GiB free). Clean-up of old full-quality audio is manual and asks first; nothing is deleted
  automatically.
- The page was checked by hand in Chrome and the built-in browser at desktop and phone widths; there is no automated
  browser test, and keyboard use and screen readers were not tested with real assistive tools.
