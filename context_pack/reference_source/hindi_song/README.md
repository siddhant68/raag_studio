# थोड़ी देर और — Thodi Der Aur

Original Hindi romantic AI-sung demo, 2:32. Start with `Thodi_Der_Aur.mp3`.
`Thodi_Der_Aur.wav` is the 48 kHz/24-bit stereo master.
`Thodi_Der_Aur_Alternate.mp3` is a different generated performance of the same lyric.
`Lyrics.md` contains the Hindi lyric and Romanized reading.

The creative direction is an intimate acoustic romantic ballad with an expanding
chorus. The central image is an unfinished cup of tea at sunset; the speaker
asks his lover to stay a little longer. The brief, lyric specification and
caption record the writing decisions and reference study. The reference is the
broad emotional palette of the Kabir Singh soundtrack; none of its audio,
melody or lyrics was fed to the generator. No named singer's voice was targeted.

## What was generated

All three native takes are text-to-music generations from the original lyrics:

| Take | Seed | Lyric input | Disposition |
| --- | --- | --- | --- |
| take_01 | 22102611 | Devanagari | Main demo; selected because local ASR retained more of the bridge and several verse/refrain phrases |
| take_02 | 22102612 | Devanagari | Alternate performance; different delivery of the same song |
| roman_01 | 22102613 | Romanized Hindi | Pronunciation experiment; no clear transcription improvement |

Generation used the installed local ACE-Step 1.5 turbo model, native MLX/MPS,
eight steps, 76 BPM, working key D major, 4/4 and 152-second target duration.
The optional 5 Hz LM was not installed or used; all metadata and the lyric were
specified directly. Requests, native WAVs and results are preserved in `takes/`.
The main master uses two-pass EBU R128 loudness normalization, without added
instruments or manual vocal editing. The alternate is encoded from its native take.

## Review evidence and limitations

Earshot descriptions provide broad, fallible acoustic/romantic/music hints;
they do not certify musical appeal or accurate Hindi. Local Whisper-small ASR
was added to independently check lyric delivery. It was given the audio and
Hindi language code, without the intended words as an initial prompt.
Its per-take transcripts recognize parts of the intended lyric but contain
omissions, misspellings and apparent repetitions. Singing ASR can hallucinate;
these transcripts do not prove which errors are in the performance. Exact
lyric adherence, Hindi pronunciation and musical quality need listener review.
No human listening approval is claimed. The main export is a demo, not a claim
of a release-ready vocal production.

`Thodi_Der_Aur_checks.json` records the main export's normalization and
finite/clipping checks. `final_measurements.json` records the delivered audio's
measurements. Native takes, ASR outputs and Earshot descriptions are retained.

## Run again on this Mac

From `/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation`:

```sh
tools/acestep-venv/bin/python -u music/thodi_der_aur_20261022/generate_song.py \
  --seeds 22102621 --take-prefix new

tools/earshot-venv/bin/python music/thodi_der_aur_20261022/export_song.py \
  --take new_01_22102621 --name New_Demo

tools/acestep-venv/bin/python music/thodi_der_aur_20261022/check_sung_lyrics.py
```

Use a native Terminal where torch detects MPS. The restricted execution shell
does not expose the GPU; during this session the scripts ran in a native Node
child process. The generator creates new take folders and refuses to overwrite
an existing folder. The transcription script skips takes already transcribed.

The original installation guide is in
`../remix_studio_20261022/docs/INSTALL_AND_RUN.md`. ACE model revision and
package pins are documented in that project. The additional ASR packages were
installed only into `tools/acestep-venv`: mlx-whisper 0.4.3, tiktoken 0.14.0,
more-itertools 11.2.1. ASR model: `mlx-community/whisper-small-mlx`, revision
`45f3915923c7a79a5a5b5a7d909d39aeb0e5630e`; weight SHA256 verified against the
model repository. See `asr-model-revision.json` and `asr-model-check.json`.
The 481 MB model remains in `tools/whisper-small-mlx`; it is excluded from the
song project ZIP. Generation and transcription ran locally; no audio was sent
to an external generation or critique service.

## Learning from this trial

Original text-conditioned generation did produce recognizable Hindi lyric
fragments in independent ASR, unlike the remix's source-reconstruction objective.
That establishes some vocal conditioning, not complete lyric fidelity or good
singing. Native-script versus Romanized input is worth comparing, but changing
script and seed together does not isolate a causal effect. More skill files or
meter readings cannot establish that one performance is musically better.

The lyric-writing skill has no Hindi-specific language layer. Its intent,
imagery and structure guidance were used; Mandarin/Cantonese tone rules were
explicitly excluded. Listener preference remains the decisive next evaluation.
