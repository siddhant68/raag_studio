# Showcase: diverse 12 (diverse12_2026-10-25)

**12 of 12 takes rendered**

Engine profile `shift3`: ACE-Step 1.5 turbo DiT (`acestep-v15-turbo`), shift 3.0, 8 steps, no 5Hz LM. One take per brief, rendered one after another, no retries. Lyrics written by Claude through the app's songwriter step, each supplied hook kept unchanged in every chorus. The lyric sheets carry section names only (the duet also names who sings); musical direction is in the caption.

Tempo, meter, arrangement and vocal assignments are what was **requested**; whether the engine followed them is for your ears. Every musical judgment below is **pending** until someone listens.

| # | Listen | Kind | Requested | Seed | Render | Checks | Brief / lyrics | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | [River waking up](audio/01_river_waking_up_bansuri_instrumental.mp3) | instrumental | 120 s, ~78 BPM, 4/4 | 1821732005 | rendered | passed | [brief](takes/01_river_waking_up/brief.md) | pending |
| 2 | [Midnight café](audio/02_midnight_cafe_jazz_sax_instrumental.mp3) | instrumental | 90 s, ~116 BPM, 4/4 | 1628324191 | rendered | passed | [brief](takes/02_midnight_cafe/brief.md) | pending |
| 3 | [Rise of the mountain](audio/03_rise_of_the_mountain_cinematic_orchestral_instrumental.mp3) | instrumental | 120 s, ~140 BPM, 4/4 | 965746278 | rendered | passed | [brief](takes/03_rise_of_the_mountain/brief.md) | pending |
| 4 | [Lanterns in the rain](audio/04_lanterns_in_the_rain_piano_cello_waltz_instrumental.mp3) | instrumental | 90 s, ~66 BPM, 3/4 | 841152641 | rendered | warning | [brief](takes/04_lanterns_in_the_rain/brief.md) | pending |
| 5 | [थोड़ी देर और](audio/05_thodi_der_aur_hindi_male_ballad.mp3) | Hindi male vocal | 150 s, ~76 BPM, 4/4 | 1905625906 | rendered | passed | [brief](takes/05_thodi_der_aur/brief.md), [lyrics](takes/05_thodi_der_aur/lyrics.txt) | pending |
| 6 | [बात अधूरी](audio/06_baat_adhuri_hindi_female_ghazal.mp3) | Hindi female vocal | 120 s, ~68 BPM, 6/8 | 309512692 | rendered | passed | [brief](takes/06_baat_adhuri/brief.md), [lyrics](takes/06_baat_adhuri/lyrics.txt) | pending |
| 7 | [यहीं कहीं](audio/07_yahin_kahin_duet_hindi_duet.mp3) | Hindi duet vocal | 150 s, ~88 BPM, 4/4 | 1756718358 | rendered | passed | [brief](takes/07_yahin_kahin_duet/brief.md), [lyrics](takes/07_yahin_kahin_duet/lyrics.txt) | pending |
| 8 | [Run Toward the Light](audio/08_run_toward_the_light_english_male_rock.mp3) | English male vocal | 120 s, ~132 BPM, 4/4 | 1561407237 | rendered | passed | [brief](takes/08_run_toward_the_light/brief.md), [lyrics](takes/08_run_toward_the_light/lyrics.txt) | pending |
| 9 | [My Own Sunrise](audio/09_my_own_sunrise_english_female_soul_pop.mp3) | English female vocal | 120 s, ~96 BPM, 4/4 | 619618584 | rendered | passed | [brief](takes/09_my_own_sunrise/brief.md), [lyrics](takes/09_my_own_sunrise/lyrics.txt) | pending |
| 10 | [आज की रात](audio/10_aaj_ki_raat_hindi_female_party.mp3) | Hindi female vocal | 120 s, ~124 BPM, 4/4 | 580143580 | rendered | passed | [brief](takes/10_aaj_ki_raat/brief.md), [lyrics](takes/10_aaj_ki_raat/lyrics.txt) | pending |
| 11 | [After the Rain](audio/11_after_the_rain_english_female_edm.mp3) | English female vocal | 150 s, ~126 BPM, 4/4 | 220652654 | rendered | passed | [brief](takes/11_after_the_rain/brief.md), [lyrics](takes/11_after_the_rain/lyrics.txt) | pending |
| 12 | [अपनी राह](audio/12_apni_raah_rap_hindi_male_rap.mp3) | Hindi male vocal | 120 s, ~92 BPM, 4/4 | 1456075399 | rendered | passed | [brief](takes/12_apni_raah_rap/brief.md), [lyrics](takes/12_apni_raah_rap/lyrics.txt) | pending |

Per take, in `takes/NN_slug/`: `brief.md` (brief as written and the requested targets), `plan.json`, `lyrics.txt` and `songwriter.json` (every Claude draft, its line check, any revision and notes), `caption.txt`, `request.json` (the exact engine request with its seed), `compile_report.json` (song map, anything left out of the caption), `take.json` (model, profile, timing, technical checks), `result.json` (the engine's own record, after rendering).

Rate in `ratings.csv` (1 to 5 per column, blank = not rated; leave the vocal columns blank for instrumentals). Technical results: `technical_summary.md`.

## Listen locally

This package is committed locally on `claude/intelligent-knuth-6jv48e`; it has not been uploaded. Open [listen_all.m3u](listen_all.m3u) in a music player, or use the twelve audio links above. Ratings stay blank until you listen.

## Reproduce (on the Mac)

```sh
git fetch origin claude/intelligent-knuth-6jv48e && git checkout claude/intelligent-knuth-6jv48e
cd app
.venv/bin/python -m experiments.showcase prepare     # keeps the saved lyrics; --rewrite-lyrics calls Claude again
.venv/bin/python -m experiments.showcase render      # checks GPU, disk, ComfyUI and other renders, asks, then renders
.venv/bin/python -m experiments.showcase publish --no-push  # local commit only
```

`render` needs the ACE-Step python and turbo weights next to the project (`../tools`, or `RAAG_TOOLS_DIR`); it downloads nothing. It waits while the ComfyUI video queue, the Raag Studio app queue or another `run_takes.py` is busy, and stops after 30 minutes of waiting. A take that fails is recorded as failed and is not retried.

Native 48 kHz FLAC renders stay on the Mac in `runs/_showcase/diverse12_2026-10-25/` (not committed). The MP3s here are listening copies normalised to -16 LUFS with a -1.5 dBTP true-peak ceiling.

## Local run outcome

12/12 rendered, 0 failed, exactly 12 new attempts; ledger 19 → 31. Total requested listening time: 24 minutes 30 seconds. Independent technical measurements: [technical_summary.md](technical_summary.md), [independent_qc.json](independent_qc.json). Input hashes and verified chorus counts: [input_audit.json](input_audit.json). No lyrics, requests, captions, plans or seeds changed. No new Claude calls, weight downloads or artistic retries.

Musical ratings and adherence remain pending. Check Hindi diction and connected singing; distinct male/female handoffs in #7; rap verses versus sung hook in #12; requested melody returns, arrangement, groove and meter; and complete endings. Preserved text concerns: #6 long couplets, #10 awkward ढोल phrase, #11 repeated “puddles”. This fixed-seed showcase does not establish a general quality advantage for shift3.
