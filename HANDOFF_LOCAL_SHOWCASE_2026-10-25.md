# Local handoff: render the prepared 12-song trial

You are the local agent on Siddhant's Mac. Execute the prepared musical trial, verify its outputs, and leave a listening package. The cloud agent prepared plans and real Claude lyrics but could not render because its environment had no Mac GPU or ACE weights. Do not redo product planning or songwriting.

## Workspace and starting evidence

Project root:
`/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio`

Remote: `https://github.com/siddhant68/raag_studio.git`
Branch: `claude/intelligent-knuth-6jv48e`
Prepared commit: `3f08f2f` (verify the full revision locally).
Batch: `showcase/diverse12_2026-10-25/`

At handoff creation, the Mac checkout was clean on master. I fetched the remote branch and inspected its showcase script and README without checking it out. The fetched branch points to 3f08f2f. No renders were launched for this handoff. Recheck current state rather than relying on these observations.

Read AGENTS.md, the batch README, its technical_summary.md, STATUS.md, app/experiments/showcase.py, the showcase spec it references, and the engine run_takes.py before running anything. Use this handoff for the current scope; the older MORNING_SUMMARY.md has stale render counts and planner status.

## Required outcome

Render all 12 prepared briefs once each with the real local engine, sequentially, using their saved seeds, lyrics and requests. Profile: shift3, ACE-Step 1.5 turbo, shift 3.0, eight steps, no 5Hz LM. Do not change settings, rewrite lyrics, regenerate seeds, add variations, or retry failed takes to improve results. This is a diversity showcase, not a controlled shift 1 vs 3 comparison.

The requested items are:
1. River waking up — bansuri instrumental, 120 s, 78 BPM, 4/4.
2. Midnight café — instrumental, 90 s, 116 BPM, 4/4.
3. Rise of the mountain — instrumental, 120 s, 140 BPM, 4/4.
4. Lanterns in the rain — instrumental, 90 s, 66 BPM, 3/4.
5. थोड़ी देर और — Hindi male vocal, 150 s, 76 BPM, 4/4.
6. बात अधूरी — Hindi female vocal, 120 s, 68 BPM, 6/8.
7. यहीं कहीं — Hindi duet, 150 s, 88 BPM, 4/4.
8. Run Toward the Light — English male vocal, 120 s, 132 BPM, 4/4.
9. My Own Sunrise — English female vocal, 120 s, 96 BPM, 4/4.
10. आज की रात — Hindi female vocal, 120 s, 124 BPM, 4/4.
11. After the Rain — English female vocal, 150 s, 126 BPM, 4/4.
12. अपनी राह — Hindi male rap, 120 s, 92 BPM, 4/4.

All tempo, meter, instrument, form and voice assignments are targets. Musical adherence and quality require listening.

## Execution

1. Inspect git status, current branch, free disk, render ledger and live generation queues/processes. Preserve unrelated edits. Do not stash, reset, clean or force checkout automatically. If the checkout is dirty, resolve through a separate checkout or another reversible approach, accounting for the sibling tools paths and project-local venv.
2. Fetch and switch to the prepared branch. If a local branch already exists, inspect divergence and update only by fast-forward; do not reset it. Preserve this handoff, which may be untracked when switching.

```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
git status --short
git fetch origin claude/intelligent-knuth-6jv48e
git switch claude/intelligent-knuth-6jv48e
git rev-parse HEAD
git merge-base --is-ancestor 3f08f2f HEAD
```

3. Inspect the branch-specific dependency instructions. Reuse app/.venv; install missing dependencies inside the project only. Shared ACE runtimes and weights remain read-only. Run the relevant showcase tests after discovering their actual filenames; broader tests are needed only if you modify implementation.
4. Check real preflight from the project root: `python3 scripts/preflight.py --json`. Require MPS, existing ACE Python and weights, ffmpeg, adequate disk, and no competing GPU job. Do not fall back to CPU or download weights. The default paths are sibling `../tools`; RAAG_TOOLS_DIR can override if necessary. ACE uses substantial unified memory; never overlap it with video/image rendering. Stop only processes you own. Keep the plugged-in Mac awake with a time-limited caffeinate you own; record its PID and stop it when done. Muted speakers are fine.
5. Audit the saved batch before prepare: all 12 plans/requests/seeds present, eight lyric sheets present, chorus hooks preserved. Save hashes of lyrics and requests in a local run log so changes are reviewable. Prepare retains saved lyrics, but can rebuild requests: inspect any differences and stop if they change the fixed trial unintentionally. Never use --rewrite-lyrics.

```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio/app
.venv/bin/python -m experiments.showcase prepare
.venv/bin/python -m experiments.showcase render --yes
```

The user requested this local experiment run; --yes suppresses the script's redundant interactive confirmation. The budget is 12 new take attempts, one per prepared brief, no retries. The cloud note expects ledger 19 -> 31, but verify the live ledger and record actual increments; do not invent counts. A failed attempt still counts.

## Output verification and recovery

Native outputs belong in `runs/_showcase/diverse12_2026-10-25/`; listening MP3s belong in `showcase/diverse12_2026-10-25/audio/`. Preserve native audio and exact provenance. The script creates listening copies targeting -16 LUFS and -1.5 dBTP; independently measure achieved values and report discrepancies. Never substitute fake audio. Use run_takes.py through the batch, not the older unguarded render_local.py.

For each take verify actual engine identity, seed, effective shift/steps/no-LM settings, output existence, decodability, requested duration, sample rate/channels, clipping/silence checks, and any network-attempt record. Capture timing and technical results; retain errors and logs for failures. Technical success does not prove correct Hindi diction, duet separation, rap flow, melody, genre or meter.

The current script only schedules takes marked not_rendered; rendered and failed entries are skipped. It refuses to overwrite an existing native final or .partial folder. If interrupted, inspect processes, take.json, native files and logs before resuming. A crash can leave valid audio before metadata is saved. Recover metadata or mark the consumed attempt failed as evidence warrants; preserve files. Do not delete folders or set statuses back merely to trigger another generation. A process exit code of zero does not prove 12 successes: failures and timeout/early-stop cases must be audited from per-take metadata. Resource waits stop after about 30 minutes; record the blocker and resume only unattempted work when resources become available.

Persist progress after each attempt in STATUS.md and a dedicated reports/LOCAL_SHOWCASE_2026-10-25.md. Include attempt number, time, seed, request hash, output path and status. If context runs low, leave precise next steps and IDs of attempted/unattempted takes. Never start another batch while an earlier process is alive.

## Lyrics already prepared

There are eight real Claude lyric sets, 10 prior calls including two revisions. Do not spend new Claude calls. Original prompts for these old calls were reconstructed afterwards and are labelled as such; never describe them as directly captured. Keep all drafts, checks and revision notes.

Known text concerns to flag for listening, without editing: #6 has long couplet lines; #10 has an awkward Hindi phrase involving ढोल; #11 repeats “puddles”. All eight hooks reportedly open every chorus unchanged; verify the saved sheets. Duet labels indicate intent, not verified singer separation.

## Package and finish

Update the generated README and technical_summary.md with actual outcomes. Keep ratings.csv blank until the user listens. Provide links to the 12 listening copies or explicitly list failed/missing items, plus native paths and reproduction details. Leave human verdicts pending and explain that this fixed-seed showcase does not establish a general quality advantage for shift3.

Local commits are authorized by the earlier project instructions. Inspect staged paths to exclude models, runtime environments, databases, private logs and native FLACs. The script's `publish` command pushes by default. For this handoff, use `publish --no-push` if its staged scope is correct, or make an explicit local commit of the intended files. Do not push merely because the cloud notes proposed it; the current request is a local experiment handoff. Prepare the result for review and ask about uploading only after local work is complete, unless the user separately authorizes pushing.

Do not merge into master. Report actual success/failure counts, tests/checks performed, total new attempts, disk usage, output locations and listening questions. Stop your own keep-awake process and leave no unowned cleanup actions.
