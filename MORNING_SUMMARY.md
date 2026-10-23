# Morning summary (written 2026-10-24 by the orchestrator session)

## What exists now

A working local app. It builds, runs real ACE-Step turbo renders, and the tests pass (344). Start it:

```sh
cd /Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio
scripts/start.sh && open http://127.0.0.1:8477/      # stop with scripts/stop.sh
```

You type a feeling or story, press Create, get a plan with reasons, 3 takes, a player, hearts/ratings, change chips, Another take, MP3/WAV export, a library, a settings page. Full details and limits: `README.md`.

## Please listen to these (nobody has heard any of them)

All made by the app through the real engine; technical checks only (right length, 48 kHz stereo, not silent/clipped).

| What | Where |
| --- | --- |
| "A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes" x3 | `runs/01M5ND3X5WAH9EPB3H8YCP86PW/01M5ND3X5WAH9EPB3H8YCP86PY/preview_0{1,2,3}_*.mp3` (take 3 had a mild silence warning, 5.08%) |
| "the quiet right after rain, someone playing flute on the ghat, tabla barely there", 90 s | `runs/01M5NEXVHMGTJWE12SE7N4FCNB/*/preview_01_*.mp3` |
| Raw M0 engine tests (Yamuna request, new seeds, 168 s x3, plus 60 s and 240 s) | `runs/_m0/20261023T213344Z/` |

Or open the app Library and play them there. Rate them love / fine / no in the app; that feeds the taste ledger.

## Numbers that matter

- A take takes about 20-30 s to render (168 s of music in ~25 s; 240 s in ~32 s). 3 takes in about a minute.
- A render uses 51-55 GB on your 48 GB Mac: never run it alongside a ComfyUI video job (the app waits automatically if :8388 is busy).
- Real takes rendered: 9 of the ~12 cap.

## Decisions I made for you (change any of them)

- Planner is **Basic keyword rules** only. It cannot read analogies or write lyrics. The `claude -p` and Anthropic API planners are built but OFF; the web page cannot enable them.
- Skipped the optional 5Hz LM download (nothing needs it; disk was ~25 GiB free).
- Default 3 takes per Create; the app never auto-ranks; "technical checks" are about breakage, not quality.
- Hindi labelled experimental, English sung words "untested", "Moonlit" recipe hidden until you rate it, requests to remix famous songs are declined with an offer of an original.
- Pruning old audio is manual and asks first.
- No React: FastAPI + SQLite + hand-written web page (no build step, no internet).

## Questions for you

1. Planner: allow `claude -p` (your Claude login, sends only your brief text to Anthropic), or give an API key, or stay with Basic rules? Without one, "write lyrics for me" and free-text change requests stay off.
2. Will you rate takes (love/fine/no)? The experiments and the taste ledger depend on it.
3. Your verdict on `context_pack/examples/unreviewed/Moonlit_Raas.mp3` (decides whether the Fusion recipe ships).
4. Do you want music beyond slow and tender (fast, dark, cinematic)? We have no accepted examples there yet.
5. Is this strictly personal use? (Model/output licence terms are unresolved.)
6. Auto-prune old non-favourite audio after N days, or keep it manual?

## Human checks still pending (agents cannot sign these off)

AT-M0-08 (one take "sounds like music"), AT-M1-10 (`context_pack/docs/M1_CAPTION_COMPARISON.md`: do the compiled captions match the intent of the originals), AT-M2-11 (keep at least one of the 3 takes), AT-M3-08 (try 3 briefs in your own words), AT-M4-07 (blind Basic vs smart planner, only when a smart provider is on), AT-M5-05 (12-line Hindi lyric, diction check). Blind-listening experiment sheets can be generated with `app/experiments/` (see its README) for E1 (`shift` 3.0 vs 1.0 is the most promising untested lever).

## Known weak spots (honest)

- The 36-brief planner test set was written by the same agent that wrote the planner, so its 100% is optimistic. Real briefs will expose gaps.
- Not done from the PRD: stem separation, loop export, waveform editor, humming input, "More like this", cover/repaint/flow-edit (experiments are prepared but flagged not engine-ready), local-LLM planner.
- `scripts/render_local.py` (older handoff script) has no network guard: use the app or `app/engine/run_takes.py` instead.
- Two early aborted engine loads made one outbound connection probe and re-copied two identical code files into the shared ACE `checkpoints/` folder; no weights were changed or downloaded.
- The UI was checked in the built-in browser and by tests, not with a screen reader.

## Housekeeping

- Local git repo with one commit per milestone; nothing pushed anywhere.
- The hourly scheduled task `raag-studio-resume` was disabled when the work finished.
- `caffeinate` (10 h) may still be running; it stops by itself.
- Reports per milestone: `reports/M0.md` ... `reports/M4_M6.md`. Spec and critique: `context_pack/docs/PRD_v2_MVP.md`, `PRD_CRITIQUE.md`, `IMPLEMENTATION_DECISIONS.md`.
