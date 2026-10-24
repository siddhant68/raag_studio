# Raag Studio: fresh-session handoff after implementation and independent review

Prepared 24 October 2026, India time, for Siddhant Pathak.

## 1. Your mission

You are continuing an existing local AI-music application. **Do not start over or treat the old handoff as an unimplemented project.** Read this document, verify the current checkout, and complete the correctness and quality work below. The user wants an application through which a music beginner can make music approaching the quality of our accepted examples.

The immediate user request was to preserve full context because the implementation agent's conversation was heavily populated. This document captures the implementation, independent review, fixes, remaining work, musical history, and operating instructions. Creating this handoff did not implement the next tasks, enable a provider, or generate music.

Project root on this Mac:

```text
/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
```

Keep new code, dependencies, reports, state, and outputs inside that root. Work through the ordered backlog in section 9. Make ordinary local fixes autonomously, verify behavior, and report concrete results. Avoid asking the user to repeat information already preserved here.

## 2. Read order and source precedence

Read these in order, selectively rather than loading every archive:

1. This document, then `AGENTS.md` and applicable ancestor instructions.
2. `context_pack/docs/IMPLEMENTATION_DECISIONS.md`: accepted choices, including the latest Choir decision.
3. `reports/BUGFIX_REVIEW1.md`: detailed causes, fixes, and residual risks from review round 1.
4. `context_pack/docs/PRD_v2_MVP.md`: current working product specification. `PRD_CRITIQUE.md` explains its reduction in scope.
5. `context_pack/examples/AUDIO_GUIDE.md` and `AUDIO_CATALOGUE.json`: exact user verdicts and audio provenance.
6. `app/backend/API_NOTES.md`, `app/backend/providers/README.md`, `app/engine/README.md`, and the relevant implementation files.
7. `STATUS.md`, `MORNING_SUMMARY.md`, `reports/M0.md` through `reports/M4_M6.md`, and `ORCHESTRATION.md` for historical execution evidence and operating rules.
8. `context_pack/docs/SYSTEM_AND_RUNBOOK.md`, `ENGINE_MEASUREMENTS.md`, and `context_pack/inventory/SYSTEM_INVENTORY.json` for tools and measured engine behavior.

Important stale-document warnings:

- `HANDOFF_PROMPT.md`, the beginning of the root README, and some older context documents say there is no implemented app. That describes the original handoff baseline and is now false. Preserve useful history; do not rebuild the app on that basis.
- `STATUS.md` says COMPLETE for the original milestone sequence, but contains outdated next-action paragraphs and a later bugfix appendix. Completion of that sequence does not close the backlog in this document.
- The morning summary's 344-test count predates the bugfix commit. The current implementation agent reports 376 passing tests.
- Claims that nobody has listened concern the new application-generated takes. The historical Yamuna, Daylight, and Thodi examples have explicit user acceptance.
- The old runbook recommends `scripts/render_local.py` for real rendering. Later engine findings supersede that recommendation: use the app or `app/engine/run_takes.py`, which includes the offline guard.
- Inventory and free-disk/queue observations are dated snapshots. Recheck before resource-intensive work.

Current user instructions take precedence. Do not silently reverse an explicitly recorded user choice on the strength of a review suggestion. When code and documentation disagree, inspect the code and describe the discrepancy.

`ORCHESTRATION.md` records the earlier Claude orchestrator's Sonnet-only development delegation requirement, heartbeat protocol, and ownership rules. Preserve the user's development-model preference if continuing that workflow; do not claim an unavailable model or tool ran. Do not reactivate the old hourly resume automation simply because the historical document describes it. Check for another active writer before making implementation changes.

## 3. What Siddhant wants

Siddhant is a beginner in music terminology but has strong preferences when listening. He wants a knowledgeable producer experience rather than a DAW questionnaire.

- A natural-language brief is the primary and only universally required input. It can describe a feeling, scene, story, instrument, or analogy.
- The application fills a coherent configuration automatically. Everything else can stay Auto.
- Optional controls cover instruments, lead/support roles, expressive playing, mood, rhythm, pace, development, voices/chorus, language, lyrics, length, and ending.
- Beginner explanations should communicate the musical consequence of a choice. Producer detail should be optional.
- Lyrics modes should eventually include original writing, exact supplied words, and permitted adaptation. Broad inspiration is different from copying existing lyrics or recordings.
- Create should proceed without an extra plan-approval gate. Users can inspect a plan, compare takes, favourite/rate, request revisions, and export.
- Technical controls must match real capabilities. A stereo generation path does not support independent flute-volume faders, guaranteed choir headcounts, exact melody locks, or true instrument stems.

The original PRD contains a 104-field creative vocabulary. The current reviewed MVP reduces that to 25 controls, with 9 initially visible. The full vocabulary is long-term context, not an instruction to cram 104 simultaneous directions into the model.

The long-term target includes songs. Our current strongest evidence supports instrumental and wordless music first. Hindi singing is experimental; pronunciation is unresolved. English singing is untested in this project. Writing lyrics in a language and reliably synthesizing sung pronunciation in that language are separate capabilities.

## 4. Musical history and acceptance evidence

All paths below are relative to the project root. Actual playable copies already exist; do not regenerate them to reconstruct context.

| Example | Exact evidence | Lesson |
| --- | --- | --- |
| `context_pack/examples/accepted/Yamuna_at_Dawn.mp3` | Strongly liked: "yamuna at dawn is such a melody man". Refined `flute_focus` take; seed **24102633**; 168 s; requested 82 BPM, D major. | Primary instrumental anchor: exposed expressive bansuri, gentle tabla, tanpura, sparse santoor. Use the refined take, not the earlier larger ensemble. |
| `context_pack/examples/accepted/Daylight.mp3` | "Very enjoyable". Selected take 01; seed **24102601**; 132 s; requested 88 BPM, D major. | Coherent multi-instrument arrangement, rhythm, and wordless vocal structure. |
| `context_pack/examples/accepted/Thodi_Der_Aur.mp3` | Initially "amazing"; later preferred over the replacement. Seed **22102611**; 152 s; requested 76 BPM, D major. | Original Hindi romantic melody and emotion worked. Some words were unclear. Acceptance does not mean pronunciation was solved. |
| `context_pack/examples/rejected/01_Concatenation_Feedback.mp3` | First Ashes on the Fire / Rains of Castamere remix felt concatenated. | Sequential playback with a smooth join did not meet the creative brief. |
| `context_pack/examples/rejected/02_Random_Mix_Feedback.mp3` | More chopped/beat-based remix felt random. | More effects and edits did not establish thematic development. |
| `context_pack/examples/rejected/03_Model_Remix_Still_Rejected.mp3` | Later model workflow was still rejected. | Successful execution and downloaded skills did not establish musical quality. |
| `context_pack/examples/rejected/04_Sonic_Pi_Hybrid_Recitation_Feedback.mp3` | Music and voice clearer, but words sounded read, with no sung melody. | Do not replace the accepted Hindi song with speech over accompaniment and call it an improvement. |
| `context_pack/examples/unreviewed/Moonlit_Raas.mp3` | No explicit listener verdict. | Do not infer approval from the user's praise of Yamuna. Its recipe remains hidden. |
| `context_pack/examples/components/Sonic_Pi_Backing.mp3` | Component, not an accepted full song. | Actual coded accompaniment; not evidence of a lyric-to-singing engine. |

The initial remix brief was to merge recognizable themes from Attack on Titan and Game of Thrones into something substantially transformed with coherent transitions. Those attempts failed musically. This application evolved from the success of original compositions instead.

Yamuna and Daylight were rendered with ACE-Step, not Sonic Pi. Sonic Pi was genuinely used in the rejected Hindi hybrid. VoiceStudio at `https://github.com/debpalash/VoiceStudio` was researched, not installed for these experiments; it is not ACE Studio. Do not claim either product repaired the singing.

Preserved exact requests/results are under `context_pack/recipes/{yamuna,daylight,thodi,moonlit,hybrid_vocal}/`. Selected original source scripts are in `context_pack/reference_source/`. Native historical masters remain at the source paths indexed in `AUDIO_CATALOGUE.json`; portable MP3 copies are inside the project.

Earshot provides measurements and fallible acoustic descriptions. Whisper can mishear singing. Neither certifies taste, virtuosity, melody quality, or exact pronunciation. Do not supply intended lyrics as an ASR prompt and then present the matching transcript as independent proof of diction. Human acceptance remains distinct from technical checks.

## 5. What is implemented

Architecture:

```text
No-build browser UI
  -> FastAPI service + SQLite WAL + filesystem assets
  -> selected planner fills a validated structured plan
  -> deterministic compiler builds the bounded ACE request
  -> durable queue runs one heavy render subprocess at a time
  -> native FLAC, previews, technical checks, feedback, exports
```

Code map:

| Path | Responsibility |
| --- | --- |
| `app/backend/main.py` | FastAPI factory, routes, lifespan, local-origin protections |
| `app/backend/jobs.py` | Service orchestration, plan revisions, controls, rounds, feedback, recovery |
| `app/backend/db.py`, `storage.py` | SQLite schema/immutability and output paths |
| `app/backend/plan_schema.py`, `planner_base.py` | Plan/control contracts, provenance, common change schema |
| `app/backend/planner_rules.py` | Basic keyword planner and quick-change rules |
| `app/backend/providers/` | Claude CLI/API planners, validation, fallback, lyric drafting interface |
| `app/backend/compiler.py` | Caption slots/budget, conflicts, lyrics and engine-parameter compilation |
| `app/backend/queue_worker.py` | Heavy-job queue, subprocess progress, cancellation, technical retry |
| `app/backend/media.py`, `exports.py` | Decode/technical checks, previews, MP3/WAV export |
| `app/backend/ui_api.py`, `capabilities*` | UI metadata, capability labels, recipes, taste ledger |
| `app/engine/run_takes.py` | Real guarded ACE-Step text-to-music harness |
| `app/engine/fake_engine.py` | Explicitly labelled sine-tone test renderer |
| `app/web/` | Hand-written HTML/CSS/JavaScript, no React or npm build |
| `app/recipes/` | MVP recipe definitions; distinct from immutable historical receipts |
| `app/tests/` | Python tests plus Node-tested UI logic |
| `app/experiments/` | Experiment/listening-sheet harness; not proof of working edit capabilities |
| `data/raag.db` | Persistent local app state; do not delete to reset a test |
| `runs/<song>/<round>/` | Fresh native audio, previews, engine request/result/log |

Implemented user flows: brief-only creation, optional controls, plan/provenance display, default 3 takes, progress/SSE with polling fallback, playback, favourites/ratings, quick-change refinements, another take, MP3/WAV export, library, settings/storage display, and manual native-audio pruning.

Refine means **new audio generated from a patched plan**, not a waveform edit or a promise to preserve the original performance. Plan revisions and requests are immutable. Keep favourites and their audio intact.

Default planner is **Basic keyword rules**. It cannot interpret arbitrary stories/analogies or write original lyrics. Claude CLI and Anthropic API providers exist but remain OFF. Their mocked/contract tests do not establish real provider behavior. Current UI cannot enable them.

Provider code keeps exact supplied lyric text outside the LLM prompt, validates model fields, builds captions in code, and exposes fallback status. Preserve those properties during follow-up work. Keys belong in environment configuration, never the database, source code, logs, or this handoff.

Not built as product features: stems, loop export, waveform editing, humming input, More like this, cover/repaint/flow-edit, or a local LLM planner. Some experiment files exist, but the current real engine contract accepts text2music only. E3/E4/E5 are flagged `engine_ready: false`.

Current silence policy: above 5% is a warning; above 40% is a technical failure. A normal quiet tail should not cause gratuitous retries. Technical retries are not taste-based retries.

## 6. Git baseline and verification history

Last checked local commits, newest first:

| Commit | Meaning |
| --- | --- |
| `9d4f027` | Recorded user decision: deliberate Choir selection overrides instrumental wording when Voice is Auto |
| `4fc6e64` | Four review bugs fixed; 32 additional Python regression tests; reported suite 376 |
| `a8185ac` | M3 frontend/planner wiring and morning summary; 344-test baseline |

The working tree was clean before this handoff was added. Recheck `git status` and recent commits when you start because another session may have continued. Local commits are allowed; **never push**.

Independent review before the fixes reproduced these four bugs:

1. Selecting Choir as a support raised `KeyError('choir')`; Choir lead on Auto could compile contradictory instrumental/no-voices wording.
2. Refining an older selected take used the latest song plan rather than that take's plan.
3. PATCH reset with null removed a control override but retained the old effective value and user provenance.
4. Change producers and UI disagreed on `from/to` versus `old/new`; manual edits used a third shape, giving misleading change explanations.

The implementation agent fixed them in `4fc6e64` and independently reported a full **376 passing** run. See `reports/BUGFIX_REVIEW1.md` for exact tests, before/after evidence, and qualifications.

The review session subsequently inspected the changes and independently ran:

```sh
app/.venv/bin/python -m pytest -q -p no:cacheprovider \
  app/tests/test_bugfix_review1.py app/tests/test_m3_logic.py
```

Result: **33 passed in 44.64 s**, one Starlette deprecation warning. The existing JS hook includes the new formatter tests. This was not an independent rerun of the full 376-test suite. Before the fixes, the reviewer verified all 344 baseline tests across the initial run and an isolated rerun of three live tests affected by a proxy setting.

No real music was rendered during either review. There has been no post-fix independent browser validation. The implementation agent behaviorally rechecked Choir and reset-to-Auto through the API; its take-branching and formatter verification relied on regression tests. Do not turn those results into claims that all UI behavior or musical output was validated.

### Current fixed behavior to preserve

- Every allow-listed instrument is covered as lead and support. Choir has a role mapping; duplicate lead/support entries from default recipes were also addressed.
- With Voice Auto, a deliberate Choir pick yields voices and an explanation, even if the brief says instrumental/no voices. A sung brief stays sung. This precedence is an explicitly recorded user decision; do not reopen it casually.
- Explicit Voice Instrumental wins over a Choir pick; voices are omitted and the conflict is reported.
- `from_take` resolves the selected take's own round/plan and preserves its controls/provenance when branching. Ownership validation remains enforced.
- API `kind: another` plus `from_take` reuses that take's plan. Without `from_take`, it uses the latest plan.
- Null control resets call the active planner to recompute the relevant Auto fields while retaining other explicit controls. With a smart planner enabled this can cause a provider call; surface that honestly.
- Standard changes are `{field, from, to, source}`, where source is `chip`, `you`, or `rule`. The formatter also understands legacy stored shapes. Do not migrate immutable history by overwriting it.

## 7. Existing real renders and human checks

The recorded ledger has **9 real takes used out of an approximately 12-take allowance**. Count takes, not commands. Reconcile with `STATUS.md` and actual outputs before spending more; do not interpret a fresh session as a fresh budget.

Existing application-era outputs:

- M0 raw engine checks: `runs/_m0/20261023T213344Z/`. Three 168 s Yamuna-request takes with new seeds, one 60 s take, one 240 s take. These are not the accepted historical Yamuna performance.
- M2 API create: `runs/01M5ND3X5WAH9EPB3H8YCP86PW/01M5ND3X5WAH9EPB3H8YCP86PY/`. Brief: "A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes". Three 120 s takes, seeds 41189026 / 229770212 / 150836115; total reported 68.5 s.
  - `preview_01_s41189026.mp3`
  - `preview_02_s229770212.mp3`
  - `preview_03_s150836115.mp3` (5.08% silence warning)
- M3 app render: `runs/01M5NEXVHMGTJWE12SE7N4FCNB/01M5NEXVHN2M6VGQJQE2PAE8ZS/preview_01_s1512086130.mp3`. Brief: "the quiet right after rain, someone playing flute on the ghat, tabla barely there"; 90 s.

These paths were checked as present during handoff preparation. Their technical checks passed, but no human musical verdict is recorded. Preserve that distinction.

Human acceptance items remain open: M0 sounds-like-music check; M1 caption/intent comparison; M2 keeping at least one take; M3 three user-written briefs; M4 blind Basic-versus-smart comparison after authorized activation; M5 Hindi diction. Exact identifiers and sheets are in the PRD and morning summary.

## 8. Runtime, installation, and commands

Machine: Apple M5 Pro MacBook Pro, 48 GiB unified memory, macOS. Versions below are inventory snapshots, not a request to upgrade.

| Component | Location/use |
| --- | --- |
| API Python | `app/.venv/bin/python`, Python 3.12; pinned dependencies in `app/requirements.txt` |
| Shared ACE Python | `../tools/acestep-venv/bin/python` |
| Shared ACE source | `../tools/ace-step-1.5`; source revision indexed as `ca1e85fe9430179831e6bc6be790c332190a3866` |
| Weights | `../tools/ace-step-1.5/checkpoints`; turbo DiT, VAE, Qwen3 embedding. Weight revision indexed as `19671f406d603126926c1b7e2adc169acbcade22` |
| Earshot | `../tools/earshot.sh`, dedicated `earshot-venv` and `earshot-main`; 0.3.0 |
| Sonic Pi | `/Applications/Sonic Pi.app`, 5.0.0; actual synthesis/sample playback and recording |
| FFmpeg / FFprobe | `/opt/homebrew/bin/ffmpeg`, `/opt/homebrew/bin/ffprobe`; inventory 9.0.1 |
| Rubber Band | `/opt/homebrew/bin/rubberband`; inventory 4.0.0 |
| Whisper | `../tools/whisper-small-mlx`; mlx-whisper in ACE environment |
| HDemucs | `../tools/hdemucs/hdemucs_high_trained.pt`; estimated source separation |
| Agent Reach | `../tools/agent-reach-venv`; research environment, inventory 1.6.0 |

The optional 5 Hz music LM is absent. Qwen3 embedding is not that LM. Although download was previously allowed, the implementation decision was to skip it because it was unnecessary and disk was tight. Do not download it as routine setup.

ACE environment snapshot: Torch/torchaudio 2.11.0, Transformers 4.57.6, MLX 0.32.4, mlx-lm 0.29.1. Earshot has a different environment with different package versions. Reuse them read-only; do not mix or upgrade shared environments. Install new app dependencies only inside this project.

### Start and stop the existing app

```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
scripts/start.sh
open http://127.0.0.1:8477/
```

```sh
scripts/stop.sh
```

Server PID/log: `data/server.pid`, `data/server.log`. Stop only services you own. The normal app uses the real engine when `RAAG_ENGINE` is unset; never accidentally leave fake mode enabled for user work. Prefer isolated temporary data/runs directories for tests. Do not start competing workers against the user's database for a smoke test.

### Tests and baseline verification

```sh
app/.venv/bin/python -m pytest app/tests -q -p no:cacheprovider
```

Tests use a labelled fake sine-tone engine and temporary directories; passing tests do not imply real music generation. Some tests launch local fake servers. If HTTPX fails before connection because injected SOCKS proxies require missing `socksio`, remove proxy variables for that local test process only rather than modifying the shared environment:

```sh
env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
    -u http_proxy -u https_proxy -u all_proxy \
    app/.venv/bin/python -m pytest app/tests -q -p no:cacheprovider
```

`NO_PROXY` alone did not fix the review session's HTTPX proxy-construction failure. Diagnose the actual failure first. Do not erase required networking configuration globally.

`python3 scripts/verify_context.py` checks the original context manifest. Intentional implementation edits to baseline files can yield hash mismatches. Review them; never restore old files blindly to make that historical manifest pass.

### Real-engine safeguards

Before any authorized real render:

```sh
python3 scripts/preflight.py --json
```

Check the result, not only the exit code: a busy video queue is reported but does not itself make this preflight script exit nonzero. Confirm available disk, native MPS, core weights, FFmpeg, and no conflicting heavy job. The worker monitors the video queue on port 8388; that is not a universal reservation of the Mac. Ports 8188/8288 may host other work, so inspect current activity without stopping unrelated services.

Restricted execution surfaces may report MPS or localhost differently from native Terminal. Diagnose that before reinstalling anything. Do not silently fall back to CPU generation.

Use the API/worker or `app/engine/run_takes.py`; its contract is in `app/engine/REQUEST_CONTRACT.md`. Engine output must be a fresh `*.partial` directory. Validate with `--dry-run` before an unfamiliar request; successful callers finalize the directory. Do not run historical scripts with hardcoded output paths over approved results.

The harness patches ACE's model-presence check in process and blocks outbound TCP, preventing an absent optional LM from triggering downloads or checkpoint writes. Historical `scripts/render_local.py` lacks this complete guard and should not be used for real rendering.

Measured, small-sample behavior: model load about 5–9 s; 168 s take about 21–26 s wall; 240 s take about 32 s. These are observations, not SLAs. Peak RSS was about 13.8 GiB, while macOS peak footprint including GPU-mapped/compressed pages was reported at 51–55 GB. Do not describe that as 55 GB resident RAM. Never overlap an ACE render with a ComfyUI generation.

Current recipes use 8 steps, LM off, requested shift 1.0. Turbo forces effective guidance 1.0 even when an old request says 7.0; record both requested and effective values. Caption budget is 512 characters in the wrapper; lyrics are separate. The duration cap is 240 s.

Native output is 48 kHz stereo, 24-bit FLAC. Exports use whole-mix FFmpeg processing. They are not independent instrument controls. API rendering writes files and does not require audible speaker playback; browser playback and Sonic Pi recording can be audible.

## 9. Ordered next tasks and acceptance criteria

### P1: Display the effective arrangement truthfully

Open correctness issue: explicit Instrumental + Choir lead still stores/displays Choir as the lead, while the compiler substitutes the recipe lead and reports the conflict. Thus the plan table and actual generation request disagree. This is not resolved merely because a warning exists lower on the page.

Make the resolved arrangement the clear primary description of what will generate. Preserve the original requested choice with a clear explanation, for example: "Choir omitted because Instrumental is selected; Bansuri will lead." Avoid silently replacing the user's requested value in historical records. Prefer one consistent requested-versus-effective representation that handles other compiler adjustments too.

Acceptance:

- Explicit Instrumental + Choir lead shows the actual fallback lead and no voices in the effective arrangement.
- The initial request and conflict remain inspectable.
- The plan, submitted request, and displayed explanation agree on lead/voice/supports.
- Auto + Choir keeps the recorded precedence behavior; explicit Instrumental still wins.
- Exact lyrics, immutable history, and existing favourites are preserved.

Relevant files: `compiler.py` conflict resolution, service/API plan/report shapes, `app/web/js/song.js`, `logic.js`.

### P1: Finish selected-take behavior in the browser

Verified remaining gap: `app/web/js/song.js` binds Another take to `startRound({kind: "another"}, ...)`. `startRound` adds the latest plan's take count but does not add `from_take`. The backend fix therefore does not make the button use the selected take.

Wire the selected take's ID when the UI offers another version of that take. Make the base take/plan visible. Review take-count semantics rather than accidentally inheriting a conflicting latest-plan default. Review Try again separately: it should retry the intended failed round/request rather than quietly switch to an unrelated latest plan.

Acceptance: after a newer Piano plan exists, select an older Bansuri take and press Another take. Verify the outgoing request has the correct `from_take`, the round uses the Bansuri plan, lineage is correct, and the UI explains the starting point. Verify the latest-plan path when no take is selected. Do this with the fake engine and isolated state first.

### P2: Close reset semantics and browser-verification gaps

- Resetting `recipe_id` to Auto currently copies only the new recipe ID/provenance, leaving other recipe defaults behind. Decide and document a coherent reset: recompute recipe-derived fields while preserving explicit user overrides and explainable prior user edits. Do not simply apply every default and erase unrelated choices.
- `POST /api/songs/{id}/plan` cannot reset controls; PATCH can. A documented PATCH-only reset contract is acceptable if all clients honor it and no control gets stuck. Do not promise null resets on an endpoint that ignores them.
- Browser-check actual What changed rendering for refinements and manual edits, including legacy stored entries. Unit-tested formatting is not a browser check.
- Exercise selecting an older take, Auto reset, and compiler conflict display in the real UI with fake generation. Regression coverage should test meaningful behavior, not just response status or absence of crashes.
- Clean up sung-Choir caption duplication after correctness: a Choir lead currently repeats choir as both ensemble and background in clumsy wording.
- Repair contradictory entry-point documentation so a future agent/user can find the current run instructions immediately. Preserve the old handoff as dated history rather than treating it as current status.

### Next major milestone: interpretation and listening quality

The previous review's product feedback was: users can plausibly reach the accepted instrumental territory through the recipes, but the default keyword planner does not yet deliver arbitrary story-to-arrangement understanding. Good full songs are less predictable. Do not add dozens of controls before establishing that users can repeatedly obtain music they want to keep.

Prepare the existing smart-planner path for evaluation, but **do not silently enable it**. `IMPLEMENTATION_DECISIONS.md` explicitly records "rule-based now, pluggable later" and says smart providers are off and never enabled by an agent. `app/backend/providers/README.md` repeats that rule. The later review recommended smart planning; it did not itself change that user choice. Build remaining local wiring, configuration UX, fixture-based evaluation, and accurate provider/fallback disclosure without live provider calls. If live activation is still needed, present one concrete decision explaining those exact recorded constraints; do not block unrelated local work on it.

Use fresh independently written briefs rather than only the planner author's 36-brief fixture set. That set's 100% score was acknowledged as optimistic. Evaluate:

- Lead/support identification, explicit exclusions and priorities.
- Emotional progression, instrument entrances, and coherent arrangement intent.
- Auto versus explicit controls and conflict resolution.
- Voice mode, original-lyric availability, and exact-word preservation.
- Revisions preserving unrelated choices and using the selected take's plan.
- Provider timeout/unavailability and truthful fallback labeling.
- Compact compilation retaining essential intent within the caption budget.

After authorized provider access and only within the remaining render allowance, prepare a small listening trial covering expressive flute-led instrumental, ensemble with wordless voices, and a Hindi romantic song. Reuse existing unreviewed app takes where useful before spending the remaining approximately three takes. Do not allocate six comparison renders against a three-take remainder. New experiments need an explicit ledger entry and budget reconciliation.

Compare with the exact accepted anchors and preserve the actual outputs. Judge melody/memorability, expressive playing, arrangement coherence, rhythm, transitions, and emotional progression; add sung phrasing and diction for songs. Report technical checks and human ratings separately. If you cannot listen, leave the verdict pending and provide concise listening instructions.

Keep instrumental/wordless creation as the strongest current product promise. Full songs remain experimental until listening evidence supports a stronger claim. A more capable planner can improve intent and lyric preparation; it does not by itself prove better rendered singing.

## 10. Research and skill material already available

Do not repeat the entire web research or install every discovered tool. The project includes 159 vendor `SKILL.md` files across eight pinned snapshots plus separate Nous and Earshot guides. They are reference procedures, not registered tools, trained musical judgment, new synthesis engines, or paid service access.

Start with:

- `context_pack/docs/research/AI_MUSIC_RESEARCH.md`
- `context_pack/docs/research/LOCAL_SETUP_AND_LESSONS.md`
- `context_pack/docs/research/LOCAL_SKILLS.md` and `SKILLS_INVENTORY.json`
- `context_pack/docs/research/VOICE_STUDIO_REVIEW.md`
- `context_pack/inventory/SKILL_PATH_MAP.json` and `vendor_source_manifest.json`

Relevant composition guides include melody, development, arrangement architecture, orchestration, and vocal direction. Lyric guides cover intent, imagery, structure, and rhyme. Read selected files when they solve a concrete task; do not load every genre archive. English respelling/phoneme advice is not a validated Hindi singing solution.

Vendor families include ace-step, Bitwize/Suno, music-composition-skills, lyric-writing-skills, Ableton skills/MCP, DJ Claude/Strudel, and Mixxx. Ableton/Mixxx integrations were researched, not established as working on this machine. Suno-oriented guides do not provide a Suno API.

Joey Nato's production commentary informed the original configuration vocabulary: registers, taiko intensity, legato versus short articulations, motif reprise, string/choir doubling, entrances, builds, synth/orchestral combinations, and transitions. Public captions for additional videos were obtained through Agent Reach; that was transcript research, not independent listening or score analysis. Archived research includes links/paraphrases. One subtitle request was rate-limited; do not blindly repeat it.

Agent Reach uses public backends such as yt-dlp for YouTube search/subtitles. Its availability does not imply it watches or understands video frames or hears the soundtrack. Its copied launcher lives in `context_pack/reference_source/reach_local.py`; use the isolated environment if more targeted research is justified.

## 11. Boundaries and finish requirements

- Preserve `context_pack/examples/` and historical `context_pack/recipes/` unchanged. Do not overwrite accepted masters, reuse an existing output directory, delete the user's database, or auto-prune to obtain space.
- No paid services, external publishing, messaging, voice training, edits to unrelated projects, or shared environment upgrades as routine implementation work.
- Keep provider activation and credentials consistent with explicit user decisions. Do not infer API entitlement from a ChatGPT/Claude subscription.
- Manual pruning remains the accepted default. Commercial/public use, Moonlit's verdict, broader style preferences, and any new retention policy are still unresolved; they need not block ordinary local fixes.
- Never stop another person's generation service. Stop only processes owned by your session/project after verifying ownership.
- Do not mark human-listening acceptance criteria passed from file duration, peak, ASR, classifier output, or unit tests.
- Preserve requested/effective engine parameters, plan, lyrics, checkpoint, seed, request/result, native output, preview/export, and verification evidence for new takes.

At completion, update current README/status and write a concise follow-up report under `reports/` with changed behavior, meaningful checks, remaining issues, any exact render paths/seeds/budget used, and clear listening limitations. Keep historical evidence dated. Commit locally if appropriate; never push. Finish with working run commands and the concrete next user action, without claiming subjective musical success from tests.

## 12. Suggested first actions in the fresh session

1. Confirm root, `git status`, current commits, and no concurrent writer. Read the short source list above.
2. Reproduce effective-plan/Choir disagreement and missing `from_take` in the UI without a real render.
3. Implement and verify the correctness tasks, including the browser path and coherent reset semantics.
4. Update stale entry-point documentation and the next-task list so the next handoff is simpler.
5. Prepare independent smart-planner evaluation and listening materials while preserving the current off-by-default decision and remaining render budget.

Do not spend the first session rebuilding already completed milestones, reinstalling the renderer, or trying the rejected famous-song remix again.
