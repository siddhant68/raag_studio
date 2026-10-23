# STATUS (single source of truth for resumed sessions)

state: PHASE_1_BUILD
heartbeat_utc: 2026-10-23T22:19:52Z   # orchestrator updates this; see ORCHESTRATION.md for the lock rule
active_session: orchestrator-original

Spec: context_pack/docs/PRD_v2_MVP.md (milestones M0..M7). Decisions: context_pack/docs/IMPLEMENTATION_DECISIONS.md. Rules: ORCHESTRATION.md.

## Milestone board

| Milestone | Scope | State | Notes |
| --- | --- | --- | --- |
| Phase 0 | PRD critique + v2 plan + decisions | DONE | reviewed by orchestrator |
| M0 | Engine harness, preflight, measurements (GPU) | DONE (orchestrator re-ran preflight and ffprobe on all 5 takes: OK). AT-M0-08 [H] pending user. | owns app/engine/, scripts/preflight.py, context_pack/docs/ENGINE_MEASUREMENTS.md |
| M1 | Compiler, recipes, rule planner, capabilities.json (no GPU) | DONE (orchestrator re-ran 119 tests: pass). AT-M1-10 [H] pending user (context_pack/docs/M1_CAPTION_COMPARISON.md). | owns app/backend/{compiler,planner,plan_schema,capabilities}*, app/recipes/, app/tests/test_m1*, fixtures; creates app/.venv |
| M2 | Backend vertical slice (db, queue, worker, API, export) | DONE (orchestrator re-ran 321 tests: pass; ffprobe of 3 real takes OK; no stray processes). AT-M2-11 [H] pending user. API shapes: app/backend/API_NOTES.md | |
| M3 | No-build frontend, MVP-1 complete | IN PROGRESS (Sonnet agent launched; also does planner wiring + 1 real take; owns app/web, report -> reports/M3.md) | |
| M4 | Providers (claude -p / API OFF by default), chips/patch | DONE standalone (274 tests pass incl. M1; orchestrator re-ran). Wiring into API pending after M2: use backend.providers.registry get_planner(settings)/plan_with_status() in a thread. AT-M4-07 [H] pending user. | mechanical tests only |
| M5 | Lyrics duration fit, language labels, disk meter, prune, taste ledger | PARTIAL (lyric_fit + labels in M1; prune/disk meter in M2; taste ledger endpoint + UI in M3) | |
| M6 | Experiment harness only (no GPU arms) | DONE harness (E3/E4/E5 flagged engine_ready:false: run_takes only does text2music). No GPU arms run. | |
| Final | README run instructions, MORNING_SUMMARY.md | TODO | |

## Render ledger (cap ~12 takes; planned 9, see IMPLEMENTATION_DECISIONS.md)

| # | time | what | seed | output | verdict |
| --- | --- | --- | --- | --- | --- |
| 1-3 | 21:3xZ | M0 yamuna request, 3 takes, 168 s | 24103001/2/3 | runs/_m0/20261023T213344Z/yamuna3/ | technical OK (48k stereo 24-bit FLAC); not listened |
| 4 | 21:3xZ | M0 length 60 s | 24103060 | .../len60/ | technical OK |
| 5 | 21:4xZ | M0 length 240 s | 24103240 | .../len240/ | technical OK |

| 6-8 | 22:11Z | M2 real create via API: 'A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes', takes=3, 120 s | 41189026, 229770212, 150836115 | runs/01M5ND3X5WAH9EPB3H8YCP86PW/01M5ND3X5WAH9EPB3H8YCP86PY/ | technical OK (take 3: silence warning 5.08%); not listened; 68.5 s total |

Takes used: 8 of ~12. Remaining: M3 e2e (1 take), 3 spare.

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
