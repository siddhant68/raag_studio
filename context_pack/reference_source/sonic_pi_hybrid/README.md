# Thodi Der Aur: Sonic Pi hybrid test

23 October 2026. This is a new 53.23-second arrangement of the original song's
hook, not a replacement for the previously accepted full song.

Start with `Thodi_Der_Aur_Sonic_Pi_Test.mp3`. To hear Sonic Pi's contribution
alone, play `Sonic_Pi_Backing.mp3`. The corresponding 24-bit/48 kHz WAVs and
the isolated generated vocal are preserved in this folder.

## What Sonic Pi actually did

`backing.rb` performs a fixed 16-bar arrangement in Sonic Pi 5.0.0 at 76 BPM,
working key D major. It contains piano arpeggios, a quiet sustained pad, sine
bass, restrained kick/snap/hat pulses and original plucked intro/coda fills.
The opening has two instrumental bars before the vocal enters. Chord voicings,
note order, timing, part entrances and dynamics are specified in Ruby.

The WAV was captured from the already-running native Sonic Pi engine. This
is actual Sonic Pi synthesis and sample playback; ACE-Step did not re-render
or replace its backing. No commercial song recording was used.

The first capture attempt addressed the engine over UDP, following the bundled
headless example. This Sonic Pi installation communicates with SuperSonic over
TCP, so that attempt played the score but failed to record. The corrected
controller sends recording commands through the existing Spider API, whose
studio object uses the engine's correct transport. The failed log is retained.
The successful capture was 54.26 seconds; 0.736 seconds of recording/scheduler
lead-in was removed. The app and its original engine were left running.

## What generated the singing

ACE-Step 1.5 turbo generated two separate 44.2-second, short-phrase vocal trials
using the original Hindi hook, 8 steps, seeds 23102601/23102602, D major,
76 BPM, language `hi`. The prompt requested dry a cappella singing, fewer
embellishments and clear syllables. No named singer was targeted.

Take 01 was retained because its unprompted local ASR exposed more separately
recognizable phrases. That is a text-delivery observation, not a musical rating.
The installed torchaudio HDemucs model then isolated its vocal, reducing residual
accompaniment before mixing with the fixed Sonic Pi backing. Separation took
about 16.4 seconds on CPU. Model source and content fingerprint are recorded in
`separation-model.json`; the weights are not bundled.

The vocal is centered, high-passed at 75 Hz, brought forward, and placed after
the two-bar intro. The backing ducks by at most 2 dB during vocal activity.
The final mix uses two-pass loudness normalization. See `mix_report.json` and
`final_measurements.json` for exact settings and measurements.
The standalone backing export is raised to -15 LUFS for convenient comparison;
its level inside the vocal mix remains -23 LUFS before ducking/mastering.

## Pronunciation outcome

Shorter phrases and separation give us better control over the arrangement and
vocal audibility, but do not establish repaired Hindi pronunciation. ASR before
and after separation still produces approximations of several words. ASR itself
is fallible on singing; no human listening approval of this test is claimed.
The generator did not follow an explicit syllable-to-note score. Exact vocal
melody/chord fit and diction remain listening checks. This experiment proves
we can retain an editable Sonic Pi accompaniment and mix an independent vocal;
it does not prove that ACE-Step has become a precise Hindi singing synthesizer.

## VoiceStudio: the repo the user meant

The relevant project is https://github.com/debpalash/VoiceStudio, not ACE Studio.
`VOICE_STUDIO_REVIEW.md` records the source inspection and limits. The app was
not installed or used to generate this test. Its speech tools and respelling
dictionary could support a Hindi pronunciation guide, but a reliable,
melody-preserving Hindi singing correction workflow was not established.

## Run again

From the workspace, with Sonic Pi already open and idle:

```sh
"/Applications/Sonic Pi.app/Contents/Resources/app/server/native/ruby/bin/ruby" \
  music/sonic_pi_hindi_20261023/record_active.rb

tools/acestep-venv/bin/python music/sonic_pi_hindi_20261023/generate_vocals.py \
  --seeds 23102611 --take-prefix new_vocal
```

The recording controller refuses to overwrite its output. Use a fresh project
folder for a new recording. It attaches only to an existing UDP Spider server;
it does not boot another Sonic Pi engine. The score can also be loaded and run
directly in Sonic Pi, using its Record control to capture it.

`separate_vocal.py` loads the first selected native vocal and the official
`tools/hdemucs/hdemucs_high_trained.pt` model using the installed torchaudio 2.11.
`mix_hybrid.py` creates the two listening exports. Native GPU generation and
local Whisper transcription ran from the host's Python child process; the
restricted shell does not expose MPS. The existing music installation guide is
in `../remix_studio_20261022/docs/INSTALL_AND_RUN.md`.

All generation, separation, transcription and mixing here ran locally. The
original accepted song and earlier projects were left unchanged. Rebuildable
`Hybrid_Premaster.wav` is omitted from the portable ZIP; final audio, source
recordings, scripts, lyrics, logs, research and checks are included.
