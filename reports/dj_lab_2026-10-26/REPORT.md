# DJ Lab: real transitions and a usable local product

26 October 2026, India time. Implemented in this workspace. Open **http://127.0.0.1:8477/dj.html**.
Double-click `scripts/open_dj.command` if the server is stopped.

## Outcome

The local application now imports existing recordings and renders source-preserving DJ edits through an explicit
CPU audio worker. It has five actual techniques, an interactive cue editor, waveform players, same-position
matched-volume A/B switching, cue sheets, favorites, listening notes, recipe reuse and vertical video export.
The earlier October 25 prototype remains preserved separately. New product code is in this workspace; the
separate clean checkout under `local_genjutsu/repos` was not modified or pushed.

The user explicitly said the earlier Yamuna→Daylight transition was **smooth**. This accepts that transition's
smoothness, not the new edits or a general claim of professional DJ quality. All new musical preferences are
pending user listening. Browser playback was verified technically; I did not judge these recordings by ear.

## Eight curated auditions

Session: `runs/_dj_lab/club_session_20261026_v1/`. Each directory contains the actual plan, prepared source excerpts,
Rubber Band command/transform log, real deck/effect buses, native WAV master, untreated control, listening WAVs,
256-kbps MP3s, exact source/output hashes, loudness measurements and result metadata. The session's code snapshot
retains the renderer used for those takes. No new music model was used; seed/checkpoint/prompt are explicitly null.
Source lyrics are unchanged recordings, not newly generated text.

| Edit | Duration | Incoming entrance | Listening LUFS | MP3 dBTP |
| --- | ---: | ---: | ---: | ---: |
| One More Time → Losing It, pressure/drop | 53.76 s | 30.72 s | -17.88 | -1.88 |
| One More Time → Losing It, echo reveal | 53.76 s | 30.72 s | -17.89 | -1.88 |
| Kala Chashma → Nashe, pressure/drop | 37.65 s | 18.82 s | -16.00 | -3.29 |
| Kala Chashma → Nashe, original-tempo portal | 37.83 s | 18.13 s | -15.99 | -4.93 |
| Kala Chashma → One More Time, club switch | 42.11 s | 16.84 s | -15.99 | -2.35 |
| Nashe → Kala Chashma, short reel switch | 18.91 s | 9.85 s | -15.99 | -4.20 |
| Sunrise session, original bansuri → Daylight blend | 50.23 s | 16.74 s | -18.25 | -3.14 |
| Breathe, original Daylight → bansuri reel | 22.29 s | 10.77 s | -16.66 | -1.76 |

There is also one additional 22-second original-music render created by clicking **Use this recipe → Render preview**
in the real browser. Its immutable take ID is `4cf2798f4ef343f38af579685bdc53eb`. The browser's **Make reel video**
action successfully exported a second video for that take. This is an end-to-end product check, not an extra musical
arrangement counted among the eight curated auditions.

The listening ZIP contains all eight edited MP3s, all eight untreated comparisons, a local listening page and the
original-music vertical video. Extract the whole ZIP before opening `listen.html`; direct MP3s also work independently.
Native masters, imported full recordings and private logs remain in the local project rather than the listening ZIP.

## Actual musical/audio decisions

- **Pressure/drop:** establish the selected source passage, then repeat a specific four-beat source fragment. The
  final eight beats consist of 4 beats → two 1-beat repeats → two half-beat repeats → four quarter-beat repeats.
  The low band withdraws through that build, with a final eighth-beat gap before the incoming attack. No random
  cuts, new riser, noise sample or new drum kit is added. The complete preceding phrase is left intact.
- **Echo/reveal:** capture the final outgoing beat and send a band-limited, dotted-eighth echo across the next
  entrance. Five repetitions decay with 0.36 feedback. A dry stereo recording is the actual input, not a claimed vocal stem.
- **Tempo portal and reel switch:** preserve each recording's own speed. They provide a deliberate change of
  pulse across a short echo exit rather than forcing a long beat blend across a large tempo gap. Reel switch adds
  a quarter-beat withdrawal; its default selection is shorter.
- **Velvet blend:** eight beats of overlap, complementary zero-phase source bands, equal-power gain curves and a
  separated bass handover. Bands are labeled as bands, never as isolated bass/drum/vocal stems.
- Other moves use a constant chosen tempo and R3 global time stretching, retaining the earlier lesson about
  unnecessary R2 anchor maps introducing sidebands. Pitch is unchanged. More than 15% requested stretching fails
  with a suggestion to use Tempo portal. There is no automatic tempo ramp or pitch/harmonic matching feature.
- Each source passage is measured and adjusted conservatively. A/B exports share a target chosen to preserve
  true-peak headroom using constant gain. They are not all forced louder to -16 LUFS. The independent maximum
  difference between edited/control MP3 loudness was **0.01 LU**.

## Analysis findings and limits

The three longer supplied files decode to roughly 320, 400 and 173 seconds. The supplied Nashe file is only about
28 seconds. Every selection is bounded by its actual source duration; the renderer does not silently pad short clips.

Initial beat-tracker regression by beat index drifted through breakdowns, particularly on Daft Punk. The discarded
fit and raw beat points are retained in the analysis evidence. The selected constant pulse candidates were instead
checked using low-band transient periodicity, with estimates around **122.882**, **125.005**, **105.920** and
**97.455 BPM** for these particular files. These are measured candidates, not claimed authoritative release tempos.
Metrical ambiguity, pickups, exact downbeats, complete hooks and semantic phrase boundaries remain listening checks.
The UI exposes editable BPM/cues rather than claiming automatic hook recognition. The original Daylight pulse
detector also has a double-time candidate, so its editable demo tempo reuses the earlier analysis candidate.

A local MLX Whisper import was tried for an auxiliary source annotation and failed before loading its checkpoint
because this execution surface could not access a Metal device. No ASR transcript was invented, no model was
downloaded, and no heavy GPU generation or paid provider was run. This limitation does not prevent CPU editing.

The private commercial-song excerpts remain local/private. The two original-music demos and original-music video
provide material for demonstrating the product without including the downloaded commercial recordings in a public
code showcase. No publishing or remote push occurred.

## Product behavior and verification

- Streamed uploads accept five audio formats, at most 70 MB and 5 seconds–15 minutes. Empty/invalid inputs fail.
- CPU jobs execute sequentially with a six-job queue cap and a ten-minute worker timeout. Interrupted jobs are
  recorded on restart; they do not silently restart as successful renders. Worker process groups are owned by
  this service and stopped together during shutdown/failure.
- Audio downloads support byte ranges. Asset/take identifiers and export filenames are scoped; cross-origin
  mutation requests are rejected by the app's existing local-origin middleware.
- Recipe reuse creates a fresh output. Favoriting/reviewing changes only feedback metadata. Rendered source
  hashes and all existing audio are preserved. Source selections past the end fail before output creation.
- **55 audio tests passed:** 41 existing remix-lab tests plus 14 new DJ DSP/real-render checks. New checks include
  echo delays/decay, actual loop content, fractional-tempo timeline lengths, beat periodicity through a breakdown,
  boundary fades, corrupt hashes, invalid selections and real matched export behavior.
- **6 new API tests passed**, including a real uploaded WAV → CPU analysis → queued real preview → range download
  → favorite persistence path. Synthetic fixture signals are test evidence, not demo music.
- **7 JavaScript logic tests passed** for use-case timing, fixed/independent tempos, invalid cues and extreme stretch gaps.
- **237 targeted existing app tests passed**, with 8 API tests deselected by the same bounded regression command
  used in the earlier study. This is not a claim of running the entire application suite.
- Independent decoded-export audit passed **16/16 curated MP3s**: duration, finite audio, non-silence, sample peaks,
  mono compatibility, true peak, quiet final sample, hashes and pairwise loudness. See `independent_audit.json` in the session.
- Actual browser checks verified recipe reuse, a successful queued render, video-export completion, native audio
  playback (`readyState=4`, no media error), and A/B switching that resumes after a source change. That check caught
  and fixed a real bug: `preload=none` never triggered the awaited metadata callback. Comparison switching now
  explicitly loads metadata before seeking/resuming.
- Desktop and 390-pixel mobile layouts were inspected. Mobile document width matched its 390-pixel viewport with
  no horizontal overflow. Screenshots: `ui_desktop.png`, `ui_workbench.png`, `ui_mobile.png`.
- The 720×1280 H.264/AAC vertical video was probed for actual audio/video streams and duration. The displayed phase
  changes at the saved reveal time, and the animated waveform is derived from the real audio, not decorative motion.

## Reproduce

```sh
AUDIO_PY=/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/tools/acestep-venv/bin/python
# Existing source manifest; choose a fresh --out path for every run:
"$AUDIO_PY" scripts/dj_experiments.py --sources runs/_dj_lab/sources_20261026/sources.json --out runs/_dj_lab/my_new_session
"$AUDIO_PY" scripts/dj_worker.py render path/to/edited_plan.json runs/_dj_lab/my_new_take
# Video requires an existing finished take; use a new output filename:
"$AUDIO_PY" scripts/dj_worker.py visualizer runs/_dj_lab/my_new_take runs/_dj_lab/my_new_take/visualizer.mp4

app/.venv/bin/python -m pytest app/tests/test_dj_api.py -q
"$AUDIO_PY" -m unittest discover -s app/experiments/tests -p 'test_*lab.py' -q
node --test app/web/js/dj_logic.test.mjs
app/.venv/bin/python -m pytest app/tests/test_song_pipeline.py app/tests/test_showcase.py app/tests/test_m1_compiler.py app/tests/test_m1_lyric_fit.py app/tests/test_m1_lyrics.py app/tests/test_m6_splice.py -q -k 'not api'
```

## Next quality decision

Listen first to the pressure/drop and echo versions of One More Time→Losing It, then compare the Bollywood
pressure/drop and original-tempo versions. Mark the versions you prefer and any cue that cuts a vocal badly.
That feedback should drive the next arrangement revision. Professional-level hook selection, harmonic coherence,
processing transparency and crowd impact remain listening judgments, not consequences of a green test suite.

This implementation pass is complete. No quota/usage-limit signal was exposed, so no speculative recurring
wake-up automation was created. The current checkpoint records the work and exact outputs for a later continuation.
