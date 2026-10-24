# Local showcase — 25 October 2026

Updated: 2026-10-24T20:37:16+00:00

12/12 new attempts consumed; 12 rendered, 0 failed; ledger 31. Unattempted: [].

Prepared revision: `3f08f2ff069ff610b04171b423c5e290979dbba1`. Profile shift3: ACE-Step 1.5 turbo, shift 3.0, eight steps, no 5Hz LM. One sequential attempt per brief; no retries.

Input audit: all twelve saved plans, requests and seeds verified. Eight lyric sheets match saved songwriter sheets; every chorus starts with the unchanged hook. Preparation changed only prepared_at/app_commit in take.json. All lyrics, captions, plans and requests remained byte-identical. Original snapshots and full hashes: `runs/_showcase/diverse12_2026-10-25/input_audit_before.json` and `pre_prepare/`.

Preflight: MPS true (Torch 2.11.0), required weights present, ffmpeg/ffprobe available, plugged into AC power, app and ComfyUI queues idle, no competing render. Initial disk 124.85 GiB free. Tests: 28 showcase tests passed; pip check clean. No dependencies installed.

| Ledger attempt | Brief | Finished UTC | Seed | Request SHA256 | Native output | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 1 River waking up | 2026-10-24T20:30:53+00:00 | 1821732005 | 20eb219d5a94c170d9ef54ce12f3710036bd42035437a4991a32f51e7dc60cf5 | runs/_showcase/diverse12_2026-10-25/01_river_waking_up/take_01_s1821732005.flac | rendered |
| 21 | 2 Midnight café | 2026-10-24T20:31:25+00:00 | 1628324191 | b3ba4eca2ee2e91016622fd331f67b9949de66787ffa05e6f01506a74f3e4171 | runs/_showcase/diverse12_2026-10-25/02_midnight_cafe/take_01_s1628324191.flac | rendered |
| 22 | 3 Rise of the mountain | 2026-10-24T20:32:04+00:00 | 965746278 | 9112f2fe658a203bce6f1ae0ca9f75cb6a45c8609b86c928b992a2b1788d6fb6 | runs/_showcase/diverse12_2026-10-25/03_rise_of_the_mountain/take_01_s965746278.flac | rendered |
| 23 | 4 Lanterns in the rain | 2026-10-24T20:32:36+00:00 | 841152641 | 64c3bd2191f0157b2b02b82829cee9a88b5b6f34be19c8f27010911935b41616 | runs/_showcase/diverse12_2026-10-25/04_lanterns_in_the_rain/take_01_s841152641.flac | rendered |
| 24 | 5 थोड़ी देर और | 2026-10-24T20:33:15+00:00 | 1905625906 | e16393c116bd9a77beb00e5be976efe45322c85ed83dd5420a6af30d172990c7 | runs/_showcase/diverse12_2026-10-25/05_thodi_der_aur/take_01_s1905625906.flac | rendered |
| 25 | 6 बात अधूरी | 2026-10-24T20:33:44+00:00 | 309512692 | 86d9bb899de946ee6b03f47d24b99bea78651958b83acf25224f87727aeb6efa | runs/_showcase/diverse12_2026-10-25/06_baat_adhuri/take_01_s309512692.flac | rendered |
| 26 | 7 यहीं कहीं | 2026-10-24T20:34:23+00:00 | 1756718358 | a0c5a293f79ac33fd1fd5e57e3378e2ccda48fc4eeefb6627f5f438c3f3a9f51 | runs/_showcase/diverse12_2026-10-25/07_yahin_kahin_duet/take_01_s1756718358.flac | rendered |
| 27 | 8 Run Toward the Light | 2026-10-24T20:34:54+00:00 | 1561407237 | 206b3234473b120843bcb3736693906b47084de74a54bf1abfd1c53db8995af1 | runs/_showcase/diverse12_2026-10-25/08_run_toward_the_light/take_01_s1561407237.flac | rendered |
| 28 | 9 My Own Sunrise | 2026-10-24T20:35:29+00:00 | 619618584 | d7d6dbf55e60a590e2b1a7d6c81c8847c7d308103c3f420969437e7dd3594a90 | runs/_showcase/diverse12_2026-10-25/09_my_own_sunrise/take_01_s619618584.flac | rendered |
| 29 | 10 आज की रात | 2026-10-24T20:36:03+00:00 | 580143580 | 8d73718c9dbd25cdc3b67d37fd8bc2081f096f3a34c38f5e9d23e9c7a6f34b1b | runs/_showcase/diverse12_2026-10-25/10_aaj_ki_raat/take_01_s580143580.flac | rendered |
| 30 | 11 After the Rain | 2026-10-24T20:36:39+00:00 | 220652654 | ad1e14686eda7ecbf04f31c99ad86d4a7a30a12f4953144dc3c6611a70847dd3 | runs/_showcase/diverse12_2026-10-25/11_after_the_rain/take_01_s220652654.flac | rendered |
| 31 | 12 अपनी राह | 2026-10-24T20:37:15+00:00 | 1456075399 | f6eb82f4cde2dd13ac7fb251190ae0e4accafed601c0c7f92740910b114cf74f | runs/_showcase/diverse12_2026-10-25/12_apni_raah_rap/take_01_s1456075399.flac | rendered |

Batch CLI exit: 0. Full CLI log: `runs/_showcase/diverse12_2026-10-25/render_cli.log`.

Listening pending. Known text concerns preserved: #6 long couplet lines; #10 awkward ढोल phrase; #11 repeated “puddles”. Duet separation, Hindi diction, rap flow, genre, melody, meter and musical adherence require listening. Ratings remain blank. This fixed-seed diversity batch does not establish a general shift3 advantage.

## Final verification and package

12/12 rendered; 0 failed; exactly 12 new attempts, no retries; ledger 19 → 31. Batch elapsed 428 s; combined engine wall time 340.6 s. Maximum engine process RSS 14137.8 MiB (process RSS is not total unified-memory usage). Native audio 265.57 MiB; listening MP3s 33.66 MiB; native run folder including logs/snapshots/helpers 266.20 MiB; package approximately 34.25 MiB; remaining disk 113.82 GiB.

Keep-awake PID 3798 (7200-second cap), batch PID 3799, supervisor PID 3789; the owned keep-awake process stopped at completion. Other services were left running. No additional render remains alive.

Independent measured QC: `showcase/diverse12_2026-10-25/independent_qc.json`; detailed raw ffmpeg logs: `runs/_showcase/diverse12_2026-10-25/independent_logs/`. Verified actual engine identity, fixed seed/request hash, shift/steps/no-LM, unchanged checkpoint listing, output hashes, full decoding, duration, 48 kHz stereo, sample peak, silence, integrated loudness and true peak. Shared engine source is an installed snapshot without a Git repository; exact source location is captured in result.json. Requests/results and original byte hashes provide reproduction evidence.

Independent target discrepancies: []. Silence warnings: [{"take": 4, "kind": "native", "fraction": 0.06761481111111112}, {"take": 4, "kind": "listening", "fraction": 0.06549536666666667}]. Outbound network attempts: [].

Listening package: `showcase/diverse12_2026-10-25/README.md`, `audio/`, `listen_all.m3u`, empty `ratings.csv`. Native audio: `runs/_showcase/diverse12_2026-10-25/NN_slug/take_01_sSEED.flac`. Run command from app/: `.venv/bin/python -m experiments.showcase render --yes`. A completed take is skipped on subsequent runs; do not clear its status to regenerate. No remote push or merge to master.

Engine source content inventory: `showcase/diverse12_2026-10-25/engine_source_manifest.json` (597 Python files plus the three required checkpoint configuration hashes). Final app and ComfyUI queues idle. Listening copies measured -16.27 to -16.25 LUFS; highest true peak -1.77 dBTP. Native track 4 silence 6.76%, copy 6.55%; all other silence measurements below 5%.
