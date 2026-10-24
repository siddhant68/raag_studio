# Raag Studio: handoff 2 (end of the follow-up session, 24 October 2026, India time)

Supersedes the "what is implemented / next tasks" parts of `HANDOFF_NEXT_SESSION_2026-10-24.md` (keep that file as history and for read order,
musical evidence, runtime and boundaries, which are all still valid). Latest commit: `8a182c2` (local only, never push). Suite: **404 passing**
(`app/.venv/bin/python -m pytest app/tests -q -p no:cacheprovider`; strip proxy env vars if HTTPX fails on SOCKS). Working tree was clean.

## State of the running system
- App: `http://127.0.0.1:8477` (pid in `data/server.pid`; `scripts/start.sh`, `scripts/stop.sh`; start with the full path, shell cwd is often not the project).
  Real engine. **The smart planner is ON in the app's saved settings** (Claude local CLI, `smart_enabled: true`), enabled by the user in chat on
  2026-10-24 knowing brief text goes to Anthropic. Switch off: `PUT /api/settings {"planner_provider":"basic","planner_smart_enabled":false}`.
  Agents must not change this on their own. The `claude` login is required (`claude auth status`); it had expired once.
- Data: `data/raag.db` (do not delete), audio under `runs/`. 14 real takes exist (4 earlier + 10 new samples), each with FLAC + mp3 preview.
- **Render ledger: 19 takes used.** The user raised the old ~12 cap in chat for the 10-sample batch. Any further rendering needs a fresh user OK and a ledger row in
  `STATUS.md`. Nobody has listened to any of the 14 app-made takes; every verdict on them is technical only.

## What was done this session (all in `reports/FOLLOWUP1.md`, addenda 1 to 5)
1. **Requested vs effective arrangement.** `compile_report.arrangement {requested, effective, adjustments[]}` (compiler `_arrangement`); the plan table and summary show
   the effective lead/supports/voices with an "Adjusted" line explaining the departure. Stored plans are never rewritten.
2. **Selected take / retry.** "Another take" sends `from_take`; "Try again" sends new `from_round` (reuses the failed round's own plan and parent). `takes` is no longer sent by
   the browser (base plan's own count). Verified in the built-in browser.
3. **P2:** `recipe_id` reset recomputes recipe-supplied fields but keeps `you` provenance (controls and chips); `POST /plan` with a null is 422 `reset_not_supported` (use PATCH);
   sung Choir lead names the choir once; "What changed" browser-checked incl. legacy stored shapes; README/HANDOFF_PROMPT/STATUS entry points corrected.
4. **Planner evaluation.** `app/tests/fixtures/eval_briefs_v2.jsonl` (24 independent briefs) + `python -m experiments.eval_planner` (offline; `--plans` scores recorded plans;
   `--live claude_cli --record ...` calls the provider, refuses to score an all-fallback run). Results: Basic 11/23 briefs fully right (75% field accuracy), **Claude CLI 21/23 (95%)**.
   Two expectations (e17, e19) were corrected after the first run because "write_lyrics unsupported" is Basic-specific; disclosed. Misses: arc choice for "awkward then warm"
   (debatable) and instrument entrance timing (plan format has no such field).
5. **CLI failure reason** is now read from the CLI's stdout error envelope (it used to say "no message").
6. **Page refreshes planner state on focus**, so "Write for me" unlocks without a manual reload; settings help text follows the setting.
7. **"Write for me" was never wired** (create returned 422 `needs_user_input`). `jobs.py _draft_lyrics`: a sung plan with policy write and no text is drafted once by the smart
   planner, stored in the plan (provenance suggested), shown as "Lyrics drafted for you", reused by later rounds; failure is refused with the reason (409); exact words are never touched.
8. **Sample batch** (sub-agent, via the live app): 10 takes, all technically OK (see `reports/SAMPLES_2026-10-24.md`). Samples **9 and 10 are the sung Hindi ones** (male, female) with
   Claude-drafted lyrics. 8 of 10 have silence warnings of 5 to 15% (under the 40% failure line).
9. **Caption budget fix.** Sample 1 (Yamuna-like) lost tabla, tanpura and santoor because the drop order removed named supports before the "how full" sentence. Now flavour, then the
   fullness sentence, then supports. Recompiled stored plans: only sample 1 changes (508 chars, ensemble kept). **Sample 1's audio was not re-rendered and is still a bare solo.**

## Open items, in suggested order
1. **Human listening** (the real test; nothing here proves the music is good). Listen to the 10 samples (Library) and mark Love/Fine/No with tags. Check: Yamuna-likeness of 1 (bare solo!),
   wordless voices (3, 5, 8), and especially Hindi diction and singer gender on 9 and 10. Sample 9 and 10 lyrics are Claude-written; the first live draft was in a woman's voice although the
   brief asked for a man, so lyric-to-singer agreement is a known risk (consider telling the lyric prompt the singer gender).
2. Re-render a true Yamuna-style take (needs the user's OK, a ledger row; the fix is already live) and compare with `context_pack/examples/accepted/Yamuna_at_Dawn.mp3`.
3. **Blind Basic-versus-smart listening comparison** (M4, `app/experiments/blind_sheet.py`): not run. Plan-matching scores do not show the music is better.
4. Product gaps seen: words typed into the brief as lyrics are not treated as exact lyrics (planner asks for lyrics, ignores them; exact words belong in the lyrics control): add a hint or
   detection. The plan schema cannot express instrument entrance timing ("tabla after the first minute"). No UI to switch planner (API only, by design).
5. Silence warnings on 8 of 10 takes: check by ear whether tails are dead air; the silence policy (warn over 5%, fail over 40%) may need tuning.
6. Not built (unchanged): stems, loop export, waveform edit, humming input, More like this, cover/repaint, local LLM planner. Hindi singing stays experimental; English singing untested.

## Rules that still hold
Never push. Never delete the DB, runs or `context_pack/examples|recipes`. Do not enable or disable providers or spend renders without the user. No ACE render while ComfyUI runs on :8388 (the app
checks). Tests use a labelled fake engine; use isolated temp data and a different port (e.g. 8479 with `RAAG_ENGINE=fake RAAG_DATA_DIR=... RAAG_RUNS_DIR=...`) for browser checks. Do not claim musical
success from technical checks, ASR or classifiers.

## Quick commands
```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
scripts/start.sh            # then open http://127.0.0.1:8477/
scripts/stop.sh
python3 scripts/preflight.py --json            # before any real render
cd app && .venv/bin/python -m experiments.eval_planner --plans ../reports/eval_claude_cli_plans_v2.json
```
