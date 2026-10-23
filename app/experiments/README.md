# Experiment harness (M6)

Mechanical side of experiments E1-E5 (PRD v2 section 12/M6). **No GPU arm has been run and nothing here
renders audio.** The harness writes engine request files and a blind listening sheet, imports your ratings,
applies the promotion rule, and provides the E4 splice and E3/E5 mechanical checks.

Run from `app/`: `.venv/bin/python -m experiments.<module> ...`

| Experiment | Arms (only these parameters differ) | Question for you |
| --- | --- | --- |
| E1 | `shift` 1.0 (control) vs 3.0 | which do you prefer (A/B) |
| E2 | `retake_variance` 0.1 / 0.3 / 0.5, shared `retake_seed`, seeds = favourite seed(s) | similar but different? |
| E3 | `audio_cover_strength` 0.5 / 0.8 (cover, duration locked to source) | keeps structure? which is better |
| E4 | repaint a span (explicit mask) + `splice_repaint` | melody and voice retained? |
| E5 | `flow_edit_morph` off (control) / on, over cover | follows the words? |

## Workflow

1. `python -m experiments.blind_sheet create E1 --plans plans.json --seeds 11,12 --out ../runs/_experiments/e1 --rng-seed 7`
   `plans.json` is a list of briefs, plan dicts, or `{"brief"|"plan": ..., "source_audio": "...", "source_duration_s": 150,
   "span": [40, 50], "xfade_s": 0.05, "source_caption": "...", "source_lyrics": "..."}` (E2-E5 need `source_audio`).
   Creates (folder must not exist): `requests/<arm>/planNN.json` (engine requests, one per arm and plan, identical
   seeds), `sheet/sheet.csv` + `sheet.json` (what you rate; labels A/B shuffled, orientation balanced, reproducible
   per `--rng-seed`), `key/key.json` (label to arm; do not open until done), `experiment.json` (operator manifest).
   Up to 8 seeds per run, trials = plans x seeds; promotion needs at least 10 rated trials.
2. Render each request with `run_takes.py` into `outputs/<arm>/planNN.partial` (a human/orchestrator step, GPU).
3. `python -m experiments.blind_sheet stage <exp_dir> <outputs_root>` copies takes to `listening/T01_A.flac` ...
   (neutral names). Listen. Fill `choice` (A/B/tie, blank = skip) and any `<question>_<label>` yes/no columns in
   `sheet/sheet.csv`.
4. `python -m experiments.results --key <exp_dir>/key/key.json --ratings sheet.csv [--adopt ARM] [--out results.md]`
   prints the markdown table (de-blinding is `experiments.ratings_import`; CSV or JSON accepted).

## Promotion rule

An arm is promoted when preferred in >= 70% of >= 10 blind trials (integer test `successes*10 >= trials*7`), or you
explicitly adopt it (`--adopt`). Ties count as trials and as no win; blank trials are skipped. 9 trials never pass,
7/10 passes, 6/10 does not. Control arms are never promoted. For question experiments the same rule is applied to
the "yes" rate of the primary question per arm. Passing a test is not a listener verdict until you have listened.

## Limits

- E3, E4, E5 use `task_type` cover/repaint with `src_audio`, which `app/engine/run_takes.py` currently rejects
  (contract `raag-engine-request/1` is text2music only). Their requests are written and flagged
  `engine_ready: false`; the engine contract must be extended in a later milestone before they can run.
- `splice_repaint` is not wired to the engine. Linear crossfade, 16-bit PCM wav only (E4 requests ask for wav).
  Mechanical checks: `max_abs_diff_outside` (must be 0), `seam_click_metric`, `duration_matches` (E3, +/- 0.05 s),
  `peak_dbfs` / `not_silent` (E5, > -40 dBFS).
