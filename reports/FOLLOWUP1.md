# Follow-up 1: correctness work from HANDOFF_NEXT_SESSION_2026-10-24.md

2026-10-24. No real render was made (the real engine was never started); the user's database and runs folder were untouched
(browser checks used an isolated fake-engine server on port 8478 with scratch data, now stopped). Nothing was committed to a
remote.

**Verification:** full suite `397 passed` (376 before; +17 in `test_followup1.py`, +4 in `test_followup1_eval.py`; also 4 new node tests in
`logic.test.mjs`, which run inside the existing `test_m3_logic.py` hook and so are not extra pytest items). Tests use the fake sine-tone engine; they do not show that any
music is good.

## P1: effective arrangement is the primary description
- Cause: explicit Instrumental + Choir lead kept `lead = choir` in the plan table while the compiler used the recipe lead.
- `compiler.py` `_arrangement()` adds `compile_report.arrangement {requested, effective, adjustments[]}` (computed after the budget
  fitting, so supports dropped for length are included). The stored plan is not rewritten.
- `logic.js` `effectivePlan`/`arrangementNotes`; the plan table and summary line show the effective lead/supports/background with an
  "Adjusted" line: "You asked for Choir as the lead. Choir is voices and Voice is Instrumental, so choir was left out; Bansuri leads instead."
  Provenance of the user's pick is kept. Auto + Choir keeps the recorded precedence (no adjustment).
- Checked in the built-in browser (isolated server): the Choir+Instrumental song shows Bansuri leads, no voices, the Adjusted note and the
  conflict line; the three views agree with the stored request caption (no "choir").
- A bug in my first version (`eff["mode"]`) was caught by the existing suite, fixed and covered by a new test.

## P1: selected take and retry in the browser
- `song.js`: **Another take** sends `{kind:"another", from_take:<selected>}`; no `takes` is sent, so the base plan's own version count is
  used (it used to send the latest plan's count). The note under "What next?" names the take's plan version and warns when it is not
  the newest; round lineage reads "Another take of round 1, T1: that take's own plan (plan version 1) ...".
- **Try again** previously switched to the latest plan. New API field `from_round` (kind `another` only) reuses the failed round's plan
  and parent take. Not combinable with `from_take`; foreign round is 404.
- Browser-verified: with a plan v2 (Piano) newer than take T1 (plan v1), the outgoing body was `{"kind":"another","from_take":...}`
  and the round used plan 1, parent T1, Bansuri caption. With a deliberately failed round (fake failure) on plan 1 while latest was 6,
  Try again sent `{"kind":"another","from_round":...}` and the new round used plan 1 with the same parent.
- Take-count semantics: the base plan's count, never the latest plan's.

## P2
- **recipe_id back to Auto** recomputes the fields the recipe supplies and keeps anything whose provenance is `you` (control or chip).
  Voice fields are deliberately not recipe-reset. Documented in `API_NOTES.md`.
- **`POST /plan` with null** is now 422 `reset_not_supported` pointing to PATCH (it used to ignore the null silently). No client used it.
- **Sung Choir lead caption** names the choir once ("choir harmonies in the chorus over felt piano ...").
- **What changed** checked in the browser for a chip refinement, a manual BPM/key edit, a reset to Auto, and a plan row seeded with the
  legacy shapes (field-name strings, `{old,new,chip}`): no "undefined" or "none -> none".
- **Docs:** README opens with the current entry point and keeps the baseline as dated history; `HANDOFF_PROMPT.md` has a dated banner;
  `STATUS.md` has a current-state section.

## Smart-planner preparation (no provider was enabled or called)
- `app/tests/fixtures/eval_briefs_v2.jsonl`: 24 briefs I wrote for this purpose (stories, exclusions, entrances, conflicts, exact words,
  lengths, a named-song request), none copied from the planner author's set. `python -m experiments.eval_planner` (from `app/`) scores
  a planner per dimension, offline; `--plans` scores recorded smart-planner cards. It asserts no pass mark.
- **Basic baseline:** 11 of 23 scored briefs fully right, 75% field accuracy (61 checks), every plan compiles (`reports/eval_basic_planner_v2.json`).
  Weak: progression 1/6, exclusion 1/3 ("keep the flute out of it" still adds flute), lead/support 2/5 (it misses "the cello is the star").
  The author's own 36-brief set scores far higher, which is the optimism the handoff warned about. These are my expectations; a smart
  planner should be compared on the same file, and the human blind comparison is still the real test.
- Decision still needed from you (not blocking): the smart providers stay OFF per IMPLEMENTATION_DECISIONS.md; enabling one sends brief text
  to Anthropic and is your call.

## Remaining
- Browser checks were done in the built-in pane at desktop width only, by script plus screenshot; not repeated on a phone width or
  with assistive tech.
- Choir lead with a non-choir background in sung mode is not promoted to a choir background (wording only was fixed).
- Human listening is all still pending: the four existing unreviewed app takes, then the 3-take trial after provider authorisation.
  To listen: open the Library, play `runs/01M5ND3X5WAH9EPB3H8YCP86PW/.../preview_0*.mp3` and the M3 take, and mark Love/Fine/No with
  tags; technical checks passing says nothing about the music.

## Files changed
`app/backend/compiler.py`, `jobs.py`, `schemas.py`, `API_NOTES.md`; `app/web/js/logic.js`, `song.js`; new `app/tests/test_followup1.py`,
`test_followup1_eval.py`, `tests/fixtures/eval_briefs_v2.jsonl`, `app/experiments/eval_planner.py`; tests/js/logic.test.mjs; README.md,
HANDOFF_PROMPT.md, STATUS.md, this report, `reports/eval_basic_planner_v2.json`.

## Run
```sh
scripts/start.sh && open http://127.0.0.1:8477/     # real engine; scripts/stop.sh to stop
```

## Addendum: authorised live evaluation of the Claude CLI planner (2026-10-24)
You decided to enable the smart planner (Claude CLI) for evaluation, knowing brief text goes to Anthropic. I ran it through the evaluation
harness only (`python -m experiments.eval_planner --live claude_cli --record ...`); the app's persisted Settings were **not** changed,
so the app itself still uses Basic. Only the 24 evaluation briefs I wrote were sent (no user briefs, no lyrics).

**Result: no smart plan was obtained.** All 24 calls failed at once with `Failed to authenticate: OAuth session expired and could not
be refreshed` (the local `claude` login has expired; the CLI exits 1 with an empty stderr). All 24 fell back to Basic and were labelled as
fallbacks, which is the intended truthful behaviour. No API key was used or requested. Nothing was rendered.
Fixes made because of this: (1) the provider hid the real reason (it only read stderr); it now reads the CLI's stdout error envelope, so
the banner/reason says why; (2) the harness refuses to score a run in which every plan fell back (it would have scored Basic under the
provider's name) and keeps no plans file; a mixed run is flagged as mixing. Tests added for both. A probe I ran to find the cause sent
one trivial prompt ("Reply with the word ok."), nothing else.

**What I need from you:** sign in again in an interactive terminal (run `claude`, then `/login`). I cannot do that for you and will not
handle credentials. Then re-run, from `app/`:
`.venv/bin/python -m experiments.eval_planner --live claude_cli --record ../reports/eval_claude_cli_plans_v2.json --json ../reports/eval_claude_cli_v2.json`
(about 24 calls, up to 60 s each). To use it in the app itself, Settings must be switched on by you (`PUT /api/settings`
`planner_provider: claude_cli`, `planner_smart_enabled: true`), which stays your action per IMPLEMENTATION_DECISIONS.md.

## Addendum 2: live Claude CLI result (2026-10-24, after re-login)
24 calls, 0 fallbacks (`reports/eval_claude_cli_plans_v2.meta.json`), every plan validated and compiled. Plans: `reports/eval_claude_cli_plans_v2.json`;
score: `reports/eval_claude_cli_v2.json`. Only my 24 evaluation briefs were sent. App Settings were not changed (still Basic). Nothing rendered.

| | Basic | Claude CLI |
| --- | --- | --- |
| briefs fully right (of 23 scored) | 11 | **21** |
| field accuracy (61 checks) | 75% | **95%** |
| lead/support | 2/5 | 5/5 |
| exclusions | 1/3 | 3/3 |
| progression | 1/6 | 4/6 |
| duration | 2/4 | 4/4 |
| voice | 3/5 | 5/5 |
| entrances | 0/1 | 0/1 |

**Expectation corrected after seeing results (disclosed):** for e17 and e19 (sung briefs with no lyrics supplied) I had expected the
Basic-specific flag `write_lyrics unsupported`. The smart planner correctly set lyrics policy "write" with no text and `needs_user_input: ["lyrics"]`,
so I changed those two expectations to `needs_user_input` includes lyrics. Basic is unchanged at 11/23 either way; Claude was 19/23 before and is 21/23 after.

**Remaining Claude misses:**
- e09 ("awkward at first, then warm"): chose `slow_build` where I expected `quiet_middle_bloom`. My expectation is debatable; not a clear error.
- e11 ("only flute, tabla enters after the first minute"): the plan format has no entrance-timing field, so the planner could only write a note
  ("begins as solo bansuri") and gave tabla `gentle`. This is a limit of the plan schema, not of the planner. Whether the music honours it is untested.

**Observations that matter for the product:**
- Words typed inside the brief as lyrics (e20) are not treated as exact lyrics: the planner asked for lyrics and said it ignored them. By design exact words go in the
  lyrics control, but a beginner will likely type them in the brief. Worth a UI hint or detection (not done).
- e15 (self-contradictory "instrumental only, with a big choir singing"): it chose a wordless choir and said so in a note, consistent with the recorded choir precedence.
- This measures whether the plan matches the brief. It does not show the music is better. The blind Basic-versus-smart listening comparison (M4) is still the real test and is unrun.
