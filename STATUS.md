# STATUS (single source of truth for resumed sessions)

state: COMPLETE
heartbeat_utc: 2026-10-23T22:48:35Z   # orchestrator updates this; see ORCHESTRATION.md for the lock rule
active_session: idle

Spec: context_pack/docs/PRD_v2_MVP.md (milestones M0..M7). Decisions: context_pack/docs/IMPLEMENTATION_DECISIONS.md. Rules: ORCHESTRATION.md.

## Song pipeline (2026-10-24, cloud session; branch claude/intelligent-knuth-6jv48e)

Built: style presets (38), 56 instruments, song maps (forms fitted to tempo and length), the songwriter step with a
lyric check and one revision, the song compiler (ACE-Step-guide captions, tagged lyrics, meter), engine profiles
(classic / shift3 / lm / xl / xl_lm) with LM and XL support in run_takes.py, scripts/fetch_models.py, Style picker
(C26), song map on the song page, Settings → Music engine, the old-versus-new listening batch, and a personal
ElevenLabs script kept outside the app. Details, checks and limits: `reports/SONG_PIPELINE.md`.
Tests: 612 Python + 33 JS pass (fake engine). **No render, no listening, ledger unchanged at 19.**

Showcase diverse12 (requested 2026-10-24 for 2026-10-25): 12 briefs, one take each, profile shift3. Prepared in the
cloud session: plans, eight Claude-written lyric sheets (hooks kept word for word), captions, engine requests and
seeds in `showcase/diverse12_2026-10-25/`. **Not rendered** (no Mac or GPU in the cloud session); rendering adds 12
takes to the ledger (19 -> 31). Run `experiments.showcase render`, then `publish`, on the Mac.

Next, in order:
0. User: render the showcase (`cd app && .venv/bin/python -m experiments.showcase render`), then `publish`; listen
   and fill `showcase/diverse12_2026-10-25/ratings.csv`.
1. User: render the listening batch (16 takes; `app/experiments/listening_batch.py`), listen blind, `reveal`.
2. User OK given for the 5Hz LM: `python3 scripts/fetch_models.py lm`, then a small `new` vs `new_lm` batch.
3. Decide on XL turbo (~10 GB download, more memory).
4. With Claude on: create two sung songs with "Write for me" (Hindi and English) and read the lyric check notes.
5. Tune presets and hints from what the listening says (one change at a time).

## Milestone board

| Milestone | Scope | State | Notes |
| --- | --- | --- | --- |
| Phase 0 | PRD critique + v2 plan + decisions | DONE | reviewed by orchestrator |
| M0 | Engine harness, preflight, measurements (GPU) | DONE (orchestrator re-ran preflight and ffprobe on all 5 takes: OK). AT-M0-08 [H] pending user. | owns app/engine/, scripts/preflight.py, context_pack/docs/ENGINE_MEASUREMENTS.md |
| M1 | Compiler, recipes, rule planner, capabilities.json (no GPU) | DONE (orchestrator re-ran 119 tests: pass). AT-M1-10 [H] pending user (context_pack/docs/M1_CAPTION_COMPARISON.md). | owns app/backend/{compiler,planner,plan_schema,capabilities}*, app/recipes/, app/tests/test_m1*, fixtures; creates app/.venv |
| M2 | Backend vertical slice (db, queue, worker, API, export) | DONE (orchestrator re-ran 321 tests: pass; ffprobe of 3 real takes OK; no stray processes). AT-M2-11 [H] pending user. API shapes: app/backend/API_NOTES.md | |
| M3 | No-build frontend, MVP-1 complete | DONE (orchestrator re-ran 344 tests; screenshots reviewed; start/stop smoke test OK). AT-M3-08 [H] pending user. | |
| M4 | Providers (claude -p / API OFF by default), chips/patch | DONE standalone (274 tests pass incl. M1; orchestrator re-ran). Wiring into API pending after M2: use backend.providers.registry get_planner(settings)/plan_with_status() in a thread. AT-M4-07 [H] pending user. | mechanical tests only |
| M5 | Lyrics duration fit, language labels, disk meter, prune, taste ledger | PARTIAL (lyric_fit + labels in M1; prune/disk meter in M2; taste ledger endpoint + UI in M3) | |
| M6 | Experiment harness only (no GPU arms) | DONE harness (E3/E4/E5 flagged engine_ready:false: run_takes only does text2music). No GPU arms run. | |
| Final | README run instructions, MORNING_SUMMARY.md | DONE (README Run + MORNING_SUMMARY.md; scheduled task disabled) | |

## Render ledger (cap ~12 takes; planned 9, see IMPLEMENTATION_DECISIONS.md)

| # | time | what | seed | output | verdict |
| --- | --- | --- | --- | --- | --- |
| 1-3 | 21:3xZ | M0 yamuna request, 3 takes, 168 s | 24103001/2/3 | runs/_m0/20261023T213344Z/yamuna3/ | technical OK (48k stereo 24-bit FLAC); not listened |
| 4 | 21:3xZ | M0 length 60 s | 24103060 | .../len60/ | technical OK |
| 5 | 21:4xZ | M0 length 240 s | 24103240 | .../len240/ | technical OK |

| 6-8 | 22:11Z | M2 real create via API: 'A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes', takes=3, 120 s | 41189026, 229770212, 150836115 | runs/01M5ND3X5WAH9EPB3H8YCP86PW/01M5ND3X5WAH9EPB3H8YCP86PY/ | technical OK (take 3: silence warning 5.08%); not listened; 68.5 s total |

| 9 | 22:43Z | M3 real create: 'the quiet right after rain, someone playing flute on the ghat, tabla barely there', takes=1, 90 s | 1512086130 | runs/01M5NEXVHMGTJWE12SE7N4FCNB/ | technical OK; not listened |
| 10 | 11:24Z | Sample batch #1: 'Early light on the river, mist lifting off the water while somebody pl...' voice instrumental, lead bansuri, +tabla/tanpura/santoor, pace medium, 82 BPM, D major, arc quiet_middle_bloom, takes=1, 60 s | 1464442656 | runs/01M5PTEY5DG9NPKZBPF6KWH1FW/01M5PTEY5EH6YK0JR7NR27JGPH/ | technical OK (silence warning 8.3%); not listened; NOTE: compiler dropped all 3 supports from the caption (prompt length) |
| 11 | 11:25Z | Sample batch #2: 'A long slow evening on a rooftop, the sitar answering itself while the...' voice instrumental, lead sitar, +tanpura/tabla, pace slow, arc steady, takes=1, 45 s | 1730395788 | runs/01M5PTH2Z67Q11YP1NDGQMWKB2/01M5PTH2Z78KXC58VSQMZ30BCR/ | technical OK (silence warning 5.0%); not listened |
| 12 | 11:26Z | Sample batch #3: 'Snow falling on an empty railway platform, a piano thinking aloud and ...' voice wordless, background choir, lead piano, +strings, pace slow, arc slow_build, takes=1, 60 s | 2024929443 | runs/01M5PTJCM69DPJZ5A2K894HPK2/01M5PTJCM69DPJZ5A2K894HPK4/ | technical OK; not listened |
| 13 | 11:27Z | Sample batch #4: 'One lamp left on in a big old house, a cello sitting with a memory and...' voice instrumental, lead cello, +piano, pace slow, takes=1, 45 s | 942881118 | runs/01M5PTKN36WXDQSH1881DJJR16/01M5PTKN37FR4RHDBXNB033FKB/ | technical OK (silence warning 7.2%); not listened |
| 14 | 11:27Z | Sample batch #5: 'Courtyard after the guests leave, a harmonium hummed over by someone i...' voice wordless, background light, lead harmonium, +tabla, pace medium, takes=1, 45 s | 776996050 | runs/01M5PTMXF12KQ4G50C3Y22S0MW/01M5PTMXF24K4W5J890P87WZDS/ | technical OK (silence warning 15.0%); not listened |
| 15 | 11:28Z | Sample batch #6: 'Market morning waking up, shutters going up and a santoor sparkling ov...' voice instrumental, lead santoor, +tanpura/tabla, pace lively, takes=1, 45 s | 1970479362 | runs/01M5PTP47RKB5B5ZHAS82KZBQG/01M5PTP47SQ72BVBDYV5H9DTGB/ | technical OK (silence warning 6.6%); not listened |
| 16 | 11:29Z | Sample batch #7: 'A long drive with the windows down at golden hour, a violin singing ov...' voice instrumental, lead violin, +acoustic_guitar, pace medium, takes=1, 45 s | 1862648708 | runs/01M5PTQ54Z0QZ2B4KMGNMN8RSA/01M5PTQ550F8475A3R4JEZNMW6/ | technical OK (silence warning 9.8%); not listened |
| 17 | 11:29Z | Sample batch #8: 'Dawn at the top of a mountain temple, a vast chorus rising slowly out ...' voice auto, lead choir, +strings/piano, pace slow, arc slow_build, takes=1, 60 s | 45544930 | runs/01M5PTRBQVS12C994NS0DWDTG4/01M5PTRBQW24JKJ5V8RT7FZT4Y/ | technical OK (silence warning 5.1%); not listened |
| 18 | 11:30Z | Sample batch #9: 'Waiting by the window before sunrise for someone who said they would c...' voice sung, sung hi male, lyrics drafted by Claude, lead harmonium, +tabla, pace slow, takes=1, 60 s | 837194008 | runs/01M5PTT02RQHABNM4PDHKN6VW5/01M5PTT02SPXQ2V3BRNQQMVRGY/ | technical OK; not listened |
| 19 | 11:31Z | Sample batch #10: 'Rain on the roof and a name she keeps almost saying, a Hindi ballad of...' voice sung, sung hi female, lyrics drafted by Claude, lead piano, +acoustic_guitar/strings, pace slow, takes=1, 60 s | 35329925 | runs/01M5PTVMVD9D4WPYSYR1R8C8SH/01M5PTVMVECP0V0P1WHQGPRFGZ/ | technical OK (silence warning 5.3%); not listened |

Takes used: 19 (9 of the original ~12, plus the 10-take sample batch the user approved on 2026-10-24; cap raised by the user).

**User decision 2026-10-24 (in chat): raise the cap for a sample batch of 10 real takes (about 19 total), 8 instrumental/wordless and 2 sung Hindi with Claude-drafted lyrics. Batch ledger rows are appended below by the sample agent; reports/SAMPLES_2026-10-24.md has the details.**

## Environment notes

- Disk: ~25 GiB free of 926 GiB at start. Check `df -h .` before writing big files.
- `caffeinate` (10h timeout) started by orchestrator. Closed lid still sleeps.
- ACE python (read-only, shared): /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/tools/acestep-venv/bin/python ; ACE source: .../tools/ace-step-1.5 ; ffmpeg /opt/homebrew/bin/ffmpeg ; ComfyUI video queue :8388 (check idle before rendering).
- Local git repo initialised in the project root; never push.

## Engine facts learned in M0 (see context_pack/docs/ENGINE_MEASUREMENTS.md)

- Load 4.9 s; 168 s take ~21-26 s wall; 240 s take 31.6 s wall -> keep the 240 s cap. Engine FLAC is 24-bit, ~25 MB per 168 s.
- Peak footprint 51-55 GB on a 48 GiB Mac: NEVER overlap an ACE render with a ComfyUI job (preflight checks :8388).
- ACE tries to auto-download the missing 5Hz LM; run_takes.py patches that in-process and blocks outbound TCP. scripts/render_local.py is NOT guarded: do not use it.
- Silence check is fragile (take with a 7.6 s quiet tail measured 4.5% vs 5% limit): M2 must make the silence floor/threshold sensible (-50 dB, 0.5 s used) and treat it as a warning, not a hard failure.
- take_done.path in run_takes.py events is relative to OUT_DIR (caller renames .partial).
- Two aborted pre-patch loads touched checkpoints/ (re-copied two identical code files, one Google TCP probe). No weights changed; sizes match inventory.

## Needs user (morning)

1. Planner: enable `claude -p` or provide an API key? (default Basic rules only)
2. One-tap love/fine/no ratings on takes: will you use them?
3. Moonlit Raas verdict (decides R4 recipe).
4. Music beyond slow/tender?
5. Personal use only? (model/output licence unresolved)
6. Prune native audio of non-favourites after N days? (default manual only)
7. All [H] listening tests in PRD_v2_MVP.md are pending you.

## Blockers

- (none)

## Next after M2 lands

1. Verify M2 myself (pytest, one curl round trip with RAAG_ENGINE=fake; check ledger entry for real 3 takes).
2. Wire M4 registry into settings/planning path (small follow-up agent), then M3 frontend agent (owns app/web/), then integration test with ONE real take (last planned render), then README + MORNING_SUMMARY.md.

## Resume hint

If M0/M1 show IN PROGRESS but no sub-agent is running (new session), check reports/M0.md and reports/M1.md and the files each owns; verify with their acceptance tests, then re-dispatch only the missing parts.

## Post-release bugfix round 1 (2026-10-24)

Four reviewer-reported bugs (choir crash, refine from_take plan, null reset to Auto, change-entry schema) fixed with 32 regression tests; suite = 376 passing (orchestrator re-ran; reproduced choir and reset fixes via API). Report: reports/BUGFIX_REVIEW1.md. Open design calls for the user: (1) choir pick overrides 'instrumental' words in the brief when Voice is Auto; (2) explicit Instrumental + choir lead keeps the user's pick in the plan table but compiles with the recipe lead (conflict is reported).

## Current state and next tasks (updated 2026-10-24, follow-up 1)

Local, uncommitted-to-remote; never push. Suite: 404 passing (`app/.venv/bin/python -m pytest app/tests -q -p no:cacheprovider`;
strip proxy env vars if HTTPX fails on SOCKS). Render budget unchanged: **9 of ~12 takes used, ~3 remain; follow-up 1 rendered nothing.**
Report: `reports/FOLLOWUP1.md`. Done there: effective-arrangement display, selected-take Another take, Try again keeps the failed
round's plan, recipe reset, `/plan` null refusal, sung-Choir wording, independent planner evaluation set + Basic baseline.
Next: (1) human listening on the existing unreviewed app takes (paths in the handoff, section 7), (2) the user's decision on enabling a
smart planner (still OFF; see IMPLEMENTATION_DECISIONS.md), then record smart-planner plans and score them with
`python -m experiments.eval_planner --plans ...` from `app/`, (3) only then spend the remaining ~3 takes on a listening trial.
Smart-planner evaluation: authorised by the user and run 2026-10-24 (Claude CLI, 24 calls, 0 fallbacks): 21/23 briefs fully right vs Basic 11/23
(reports/FOLLOWUP1.md Addendum 2). App Settings still Basic; enabling it in the app is the user's action. Blind listening comparison not yet run.
