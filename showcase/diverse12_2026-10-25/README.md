# Showcase: diverse 12 (diverse12_2026-10-25)

**Not rendered yet.** Plans, lyrics, captions, engine requests and seeds are fixed; the audio has to be made on the Mac with the local ACE-Step model (commands below). There is no audio in this folder yet, and nothing here is fake audio.

Engine profile `shift3`: ACE-Step 1.5 turbo DiT (`acestep-v15-turbo`), shift 3.0, 8 steps, no 5Hz LM. One take per brief, rendered one after another, no retries. Lyrics written by Claude through the app's songwriter step, each supplied hook kept unchanged in every chorus. The lyric sheets carry section names only (the duet also names who sings); musical direction is in the caption.

Tempo, meter, arrangement and vocal assignments are what was **requested**; whether the engine followed them is for your ears. Every musical judgment below is **pending** until someone listens.

| # | Listen | Kind | Requested | Seed | Render | Checks | Brief / lyrics | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | River waking up (no audio yet) | instrumental | 120 s, ~78 BPM, 4/4 | 1821732005 | not_rendered | - | [brief](takes/01_river_waking_up/brief.md) | pending |
| 2 | Midnight café (no audio yet) | instrumental | 90 s, ~116 BPM, 4/4 | 1628324191 | not_rendered | - | [brief](takes/02_midnight_cafe/brief.md) | pending |
| 3 | Rise of the mountain (no audio yet) | instrumental | 120 s, ~140 BPM, 4/4 | 965746278 | not_rendered | - | [brief](takes/03_rise_of_the_mountain/brief.md) | pending |
| 4 | Lanterns in the rain (no audio yet) | instrumental | 90 s, ~66 BPM, 3/4 | 841152641 | not_rendered | - | [brief](takes/04_lanterns_in_the_rain/brief.md) | pending |
| 5 | थोड़ी देर और (no audio yet) | Hindi male vocal | 150 s, ~76 BPM, 4/4 | 1905625906 | not_rendered | - | [brief](takes/05_thodi_der_aur/brief.md), [lyrics](takes/05_thodi_der_aur/lyrics.txt) | pending |
| 6 | बात अधूरी (no audio yet) | Hindi female vocal | 120 s, ~68 BPM, 6/8 | 309512692 | not_rendered | - | [brief](takes/06_baat_adhuri/brief.md), [lyrics](takes/06_baat_adhuri/lyrics.txt) | pending |
| 7 | यहीं कहीं (no audio yet) | Hindi duet vocal | 150 s, ~88 BPM, 4/4 | 1756718358 | not_rendered | - | [brief](takes/07_yahin_kahin_duet/brief.md), [lyrics](takes/07_yahin_kahin_duet/lyrics.txt) | pending |
| 8 | Run Toward the Light (no audio yet) | English male vocal | 120 s, ~132 BPM, 4/4 | 1561407237 | not_rendered | - | [brief](takes/08_run_toward_the_light/brief.md), [lyrics](takes/08_run_toward_the_light/lyrics.txt) | pending |
| 9 | My Own Sunrise (no audio yet) | English female vocal | 120 s, ~96 BPM, 4/4 | 619618584 | not_rendered | - | [brief](takes/09_my_own_sunrise/brief.md), [lyrics](takes/09_my_own_sunrise/lyrics.txt) | pending |
| 10 | आज की रात (no audio yet) | Hindi female vocal | 120 s, ~124 BPM, 4/4 | 580143580 | not_rendered | - | [brief](takes/10_aaj_ki_raat/brief.md), [lyrics](takes/10_aaj_ki_raat/lyrics.txt) | pending |
| 11 | After the Rain (no audio yet) | English female vocal | 150 s, ~126 BPM, 4/4 | 220652654 | not_rendered | - | [brief](takes/11_after_the_rain/brief.md), [lyrics](takes/11_after_the_rain/lyrics.txt) | pending |
| 12 | अपनी राह (no audio yet) | Hindi male vocal | 120 s, ~92 BPM, 4/4 | 1456075399 | not_rendered | - | [brief](takes/12_apni_raah_rap/brief.md), [lyrics](takes/12_apni_raah_rap/lyrics.txt) | pending |

Per take, in `takes/NN_slug/`: `brief.md` (brief as written and the requested targets), `plan.json`, `lyrics.txt` and `songwriter.json` (every Claude draft, its line check, any revision and notes), `caption.txt`, `request.json` (the exact engine request with its seed), `compile_report.json` (song map, anything left out of the caption), `take.json` (model, profile, timing, technical checks), `result.json` (the engine's own record, after rendering).

Rate in `ratings.csv` (1 to 5 per column, blank = not rated; leave the vocal columns blank for instrumentals). Technical results: `technical_summary.md`.

## Download

```sh
# just this folder
git clone --filter=blob:none --no-checkout --branch claude/intelligent-knuth-6jv48e https://github.com/siddhant68/raag_studio.git raag_showcase
cd raag_showcase && git sparse-checkout set showcase/diverse12_2026-10-25 && git checkout claude/intelligent-knuth-6jv48e
open showcase/diverse12_2026-10-25/audio        # macOS

# or one file
curl -LO https://raw.githubusercontent.com/siddhant68/raag_studio/refs/heads/claude/intelligent-knuth-6jv48e/showcase/diverse12_2026-10-25/audio/01_river_waking_up_bansuri_instrumental.mp3
```

## Reproduce (on the Mac)

```sh
git fetch origin claude/intelligent-knuth-6jv48e && git checkout claude/intelligent-knuth-6jv48e
cd app
.venv/bin/python -m experiments.showcase prepare     # keeps the saved lyrics; --rewrite-lyrics calls Claude again
.venv/bin/python -m experiments.showcase render      # checks GPU, disk, ComfyUI and other renders, asks, then renders
.venv/bin/python -m experiments.showcase publish     # commits showcase/ and pushes this branch (never master)
```

`render` needs the ACE-Step python and turbo weights next to the project (`../tools`, or `RAAG_TOOLS_DIR`); it downloads nothing. It waits while the ComfyUI video queue, the Raag Studio app queue or another `run_takes.py` is busy, and stops after 30 minutes of waiting. A take that fails is recorded as failed and is not retried.

Native 48 kHz FLAC renders stay on the Mac in `runs/_showcase/diverse12_2026-10-25/` (not committed). The MP3s here are listening copies normalised to -16 LUFS with a -1.5 dBTP true-peak ceiling.
