# Bugfix report: independent review round 1 (4 bugs)

Agent: Sonnet dev sub-agent, 2026-10-24. No render, real engine never started (tests use `RAAG_ENGINE=fake`), no git commands, STATUS.md untouched.

**Tests:** `NO_PROXY=127.0.0.1,localhost app/.venv/bin/python -m pytest app/tests -q` = **376 passed** (344 before, +32 in `app/tests/test_bugfix_review1.py`). The 4 new node tests for the change formatter live in `app/tests/js/logic.test.mjs` and run through the existing `test_m3_logic.py` hook (node: 21 -> 25 pass), so they are inside the 376 only as part of that existing test.

Method: for bugs 2 to 4 the regression tests were written first and run against the unfixed code (24 of 32 failed, 8 passed = the tests that cover behaviour that already worked). Bug 1 was reproduced with a script against the unfixed code before any edit (the tests were written right after the first fix; see the note under bug 1).

## Bug 1 [P1] choir: REPRODUCED

- `POST /api/songs` with `controls {"instruments":["choir"]}`: `KeyError('choir')` (500). Confirmed.
- `controls {"lead":"choir"}`, voice Auto: 202, `voice_mode instrumental`, caption `Instrumental choir piece with ... Choir is the loud clear melodic lead ... Strictly no voices.` Confirmed.
- Root cause: `ROLE` in `planner_rules.py` had 14 entries (no `choir`) and `ROLE[i]` was unguarded; the planner treated choir only as a word in the brief (popped from instruments, turned into background voices), never as a control pick, so the voice inference ignored it and the compiler happily rendered a choir lead as an instrumental piece.
- Change:
  - `planner_rules.py`: `ROLE["choir"] = "harmony"`, `assert set(ROLE) == set(INSTRUMENT_IDS)` at import, `ROLE.get(i, "texture")` at the lookup. New `choir_pick_of(ctl)`. With Voice Auto, a choir lead or support makes the voice mode `wordless` (provenance `suggested`, reason "you picked choir as the lead/a supporting sound, and a choir is voices, so I added wordless voices") and background voices `choir`. A sung brief stays sung (choir becomes background). Explicit Voice Instrumental + choir pick: stays instrumental and a note says the voices are left out.
  - `compiler.py` (`_resolve`): instrumental + choir LEAD is now a reported conflict `instrumental_with_choir` ("choir was chosen as the lead of an instrumental piece" / "voices dropped; X leads instead"). The recipe's lead takes over (else first non-choir support, else bansuri) with the chosen playing style, so "Strictly no voices." never sits next to a choir lead. Choir support in instrumental was already dropped and reported.
  - `jobs.patch_controls`: adding or removing a choir pick while Voice is not explicit moves the voice mode too (see bug 3 mechanism), so PATCH and create agree.
- Tests: `test_every_allow_listed_instrument_has_a_role`; choir support and choir lead with Auto -> wordless, `suggested`, reason names choir, not "Strictly no voices", `instrumental=False` in the engine request; explicit Instrumental + choir support and + choir lead -> 202, conflict in `compile_report.conflicts`, note in `card.notes`, caption has no choir; compiler-only test (supplied plan); **every one of the 15 allow-listed instruments as support and as lead through `POST /api/songs` with voice Auto** (30 calls, each 202 with a valid plan or a 4xx with a message, never 5xx; non-choir -> instrumental, choir -> wordless; the lead is never also a support; tail matches the voice mode); PATCH choir in/out/explicit-instrumental.
- Note: the 14 other instruments all had a ROLE. The all-instruments test found one more bug of the same family (fixed, tiny): picking only a lead (e.g. `lead: tabla`) left that instrument in the recipe's default supports too (plan listed tabla as lead and as support; the compiler silently ignored the duplicate with a warning). `_lead_and_supports` now removes the lead from recipe-default supports.

## Bug 2 [P2] refine from_take used the latest plan: REPRODUCED (test failed before the fix: lead piano, not bansuri)

- Root cause: `Service.create_round` always loaded `latest_plan(song_id)`; `from_take` was only ownership-checked and stored as `parent_take_id`.
- Change (`jobs.py create_round`): with `from_take`, the base plan row is take -> round -> `plan_id` (ownership 404 unchanged). The chip patch is applied to that plan; the new revision stores that plan's controls and keeps its provenance (chip stamps on top). Revision number stays `MAX(rev)+1` per song (monotonic). Without `from_take` nothing changed (latest plan). `kind: another` with `from_take` now reuses that take's plan row (same rule); the UI never sends it, the API doc is updated.
- Tests: refine from the bansuri take after a piano revision -> bansuri lead, rev 3, `controls` equal to rev 1, lead provenance `you`, `parent_take_id` set, caption has flute and no piano; refine without `from_take` still piano and rev 3; `another` + `from_take` reuses the take's plan id; a take of another song is still 404.

## Bug 3 [P2] null reset kept value and 'you' provenance: REPRODUCED (14 parametrised cases + 3 more failed before the fix)

- Root cause: `patch_controls` popped the key from the stored controls but `apply_controls` only handled non-null values, so the plan kept the old field value and its provenance.
- Change (`jobs.py`): new `adopt_auto(d, auto, key, merged)`. For every `null` key the service asks the active planner for the plan it would make for the plan's brief and the controls that are STILL set, and copies only that control's field(s) and their provenance into the patched plan. Shared fields keep a still-set sibling (pace bucket + BPM, lead + style, singer/background/language) because the auto plan already honours remaining controls. Lead reset takes the auto supports unless `instruments` is still set (then only the new lead is removed from supports). Other fields and chip changes are untouched. Unknown keys (also with null) are now 422 `invalid_controls` (before, `{"nonsense": null}` was silently accepted). The response and the stored card note "Back to Auto: ...".
- Tests (parametrised, 14 cases): lead, instruments, pace, bpm, key, fullness, arc, style, feeling, duration, voice, background, singer, language. Each: the field equals what the Basic planner gives as Auto for the remaining controls, provenance source is no longer `you`, stored `controls_json` lacks the key, and the next round (`another`) uses the same plan id and its engine request carries the reset bpm/key/duration/instrumental. Plus: other explicit controls survive a reset; reset + new value in one PATCH; resetting BPM while pace bucket stays set keeps `you`.

## Bug 4 [P2] "What changed" showed `none -> none`: REPRODUCED by reading the code and by test

- Root cause: refine entries were `{field, from, to, chip}` but `song.js` read `old/new`; `patch_controls` stored a sorted list of field-name strings; the smart-planner free-text patch used a third shape `{field, old, new, chip}`.
- Change: one schema `{field, from, to, source: chip|you|rule}`, built only by `planner_base.change_entry` (validates `source`). Producers: Basic chips (`planner_rules._change`, `source chip`; the chip id is no longer in the entry, it stays in `card.applied` and `request_text`), smart free-text patch (`providers/__init__.py apply_patch_draft`, `source you`, lead/supports/pace flattened to ids and BPM), and `patch_controls` via new `planner_base.plan_changes(old, new, source_of)` (field-by-field diff; `you` while the resulting provenance is `you`, else `rule`). `less_busy` now reports supports as a list before/after (was `"tabla" -> null`); `different_lead` also reports the supports change. The PATCH response has a new top-level `changes`, and `card.changes` is stored with the plan. The plan-only endpoint reports no changes. `API_NOTES.md` documents the schema, the PATCH reset/choir semantics and the from_take base-plan rule.
- Frontend: `logic.js` `formatChange` / `formatChanges` (labels, arrays as comma lists, null as "Auto", instrument ids through `nameOf`, BPM, length, voice words, source label "quick change / you / automatic"; also reads the two older stored shapes so existing plans never show "undefined"). `song.js` renders `c.text` plus the source. The old `fmt()` helper is gone.
- Tests: refine response and stored card (exact key set, `source chip`, pace drops); PATCH response and stored card (`you`, then `rule` for a reset, empty list when nothing changed); every chip yields only standard entries; smart free-text entries; 4 node tests for the formatter (the `none -> none` case, lists, Auto, labels, legacy shapes).

## Decisions the orchestrator should know

1. Choir with Voice Auto beats brief words like "instrumental"/"no voices": a deliberate control pick is the more specific instruction; the reason string says what happened and how to undo it (set Voice to Instrumental). If you would rather the brief's strong "instrumental" win, it is one condition in `BasicPlanner._voice`.
2. With explicit Instrumental + choir lead, the stored plan keeps the user's pick (`lead = choir`, provenance `you`); the compiler swaps in the recipe lead for the caption and reports the conflict, and the planner note says so. So the plan table can say "Choir leads" while the conflict line under "What was sent to the music model" says Bansuri leads instead.
3. A reset to Auto calls the ACTIVE planner (`_plan_from_body`). Under Basic it is deterministic and offline. If a smart planner is switched on, a PATCH with a null makes one extra planner call (it falls back to Basic on failure like any other call).
4. `kind: another` + `from_take` now means "that take's plan". Say so if you prefer "another" to always use the latest plan.
5. The `chip` key of change entries was removed (source is `chip`); only `song.js` read it.

## Residual risk / same-class findings not fixed

- Sung mode with a choir lead (`voice: sung`, `lead: choir`): the caption reads "... with choir harmonies in the chorus over choir, felt piano ..." (choir appears as lead ensemble and as background). Valid and not broken, only clumsy wording; left alone.
- `POST /api/songs/{id}/plan` cannot reset a control (it merges new controls over stored ones and re-plans from scratch); only PATCH takes null. No stale value results because the whole plan is regenerated.
- Resetting `recipe_id` to Auto restores only the recipe id and its provenance, not the other recipe defaults.
- Smart planners (LLM output) can still return a choir lead with Instrumental; the compiler safety net catches it and reports the conflict. Not exercised with a real LLM.
- Bug 3 and 4 are verified through the API with the fake engine; the song view change rendering was checked in node only, not in a browser pane.

## Files changed

`app/backend/planner_rules.py`, `app/backend/planner_base.py`, `app/backend/compiler.py`, `app/backend/jobs.py`, `app/backend/providers/__init__.py`, `app/backend/API_NOTES.md`, `app/web/js/logic.js`, `app/web/js/song.js`, `app/tests/js/logic.test.mjs`, new `app/tests/test_bugfix_review1.py`, this report.
