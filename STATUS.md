# STATUS (single source of truth for resumed sessions)

state: PHASE_1_BUILD
heartbeat_utc: 2026-10-23T21:30:00Z   # orchestrator updates this; see ORCHESTRATION.md for the lock rule
active_session: orchestrator-original

Spec: context_pack/docs/PRD_v2_MVP.md (milestones M0..M7). Decisions: context_pack/docs/IMPLEMENTATION_DECISIONS.md. Rules: ORCHESTRATION.md.

## Milestone board

| Milestone | Scope | State | Notes |
| --- | --- | --- | --- |
| Phase 0 | PRD critique + v2 plan + decisions | DONE | reviewed by orchestrator |
| M0 | Engine harness, preflight, measurements (GPU) | TODO | owns app/engine/, scripts/preflight.py, context_pack/docs/ENGINE_MEASUREMENTS.md |
| M1 | Compiler, recipes, rule planner, capabilities.json (no GPU) | TODO | owns app/backend/{compiler,planner,plan_schema,capabilities}*, app/recipes/, app/tests/test_m1*, fixtures; creates app/.venv |
| M2 | Backend vertical slice (db, queue, worker, API, export) | TODO (needs M0+M1) | |
| M3 | No-build frontend, MVP-1 complete | TODO (needs M2) | |
| M4 | Providers (claude -p / API OFF by default), chips/patch | TODO | mechanical tests only |
| M5 | Lyrics duration fit, language labels, disk meter, prune, taste ledger | TODO | |
| M6 | Experiment harness only (no GPU arms) | TODO | |
| Final | README run instructions, MORNING_SUMMARY.md | TODO | |

## Render ledger (cap ~12 takes; planned 9, see IMPLEMENTATION_DECISIONS.md)

| # | time | what | seed | output | verdict |
| --- | --- | --- | --- | --- | --- |
| (none yet) | | | | | |

## Environment notes

- Disk: ~25 GiB free of 926 GiB at start. Check `df -h .` before writing big files.
- `caffeinate` (10h timeout) started by orchestrator. Closed lid still sleeps.
- ACE python (read-only, shared): /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/tools/acestep-venv/bin/python ; ACE source: .../tools/ace-step-1.5 ; ffmpeg /opt/homebrew/bin/ffmpeg ; ComfyUI video queue :8388 (check idle before rendering).
- Local git repo initialised in the project root; never push.

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
