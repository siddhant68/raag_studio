# What is actually available on this Mac

Audited 23 October 2026. This is local execution evidence and user feedback,
not a comparative benchmark of music models.

| Component | Local status | Demonstrated use | Limits |
| --- | --- | --- | --- |
| ACE-Step 1.5 turbo | Installed in `tools/ace-step-1.5`; isolated `tools/acestep-venv` | Original Hindi vocal song, source-conditioned cover experiments | Hindi diction imperfect; no note-by-note singer editor demonstrated |
| Native Apple MLX/MPS | Working through native host Python children | Fast local DiT and VAE inference | Restricted shell does not expose the same GPU; do not infer CPU-only hardware from that shell |
| Core ACE checkpoints | Turbo DiT, VAE, Qwen3 embedding model present | Cover and text-to-music with explicit metadata | Separate 5 Hz music LM weights are absent; the embedding model is not that LM |
| Sonic Pi 5.0.0 | Installed, working native engine | Original coded instrumental; fixed piano/pad/bass/drum backing | Does not synthesize realistic Hindi singing from lyrics by itself |
| torchaudio HDemucs | Installed pipeline and downloaded official checkpoint | Local vocal isolation | Separation cannot replace a mispronounced consonant |
| Earshot 0.3.0 | Installed in its own environment with cached CLAP/AST models | Loudness, true peak, clipping, broad acoustic hints | Does not certify taste, lyric accuracy or Hindi pronunciation |
| MLX Whisper small | Installed with local multilingual checkpoint | Unprompted singing transcription as supporting evidence | Singing ASR is fallible; transcription errors and omissions are not automatically performance errors |
| FFmpeg / FFprobe | Installed | Audio conversion, two-pass normalization, MP3/WAV export | Mastering does not compose a melody or repair wrong words |
| Rubber Band CLI | Installed | Independent pitch/time fitting of supplied phrases | Mixed-recording processing can introduce artifacts; musical matching still needs review |
| Composition / lyric / production skill snapshots | 159 vendor SKILL.md entries plus two separate guides | Selected guides read and used as procedures | Downloaded text is not a running plugin, DAW connection or additional singer |
| VoiceStudio, debpalash | Researched, not installed | No generation tested here | Default workflow is speech; no verified Hindi melody-preserving singing repair established |
| Ableton / REAPER / Mixxx custom MCP pipelines | Guides/snapshots researched | No successful production session established | Required DAW/fork/server/plugin setup is separate |
| Logic Pro Creator Studio | Application directory present | No music-generation workflow validated in this research | App presence does not establish a licence, MCP connection or automatic control |
| Connected Higgsfield audio tool | Speech-only capability in current tool description | No music generation performed through it | Its `generate_audio` tool explicitly excludes music and sound effects; do not substitute TTS for a singing/music model |

ACE source revision: `ca1e85fe9430179831e6bc6be790c332190a3866`.
ACE core model revision: `19671f406d603126926c1b7e2adc169acbcade22`.
Detailed installation records remain in
`../remix_studio_20261022/docs/INSTALL_AND_RUN.md` and its source/model receipts.

## User acceptance overrides our earlier automated assessments

| Work | User assessment | What it establishes |
| --- | --- | --- |
| First Ashes/Castamere mix | Felt concatenated | A join/crossfade is inadequate for the requested reinterpretation |
| Second beat-based remix | Felt random | More drums and fragment edits do not establish musical development |
| Later orchestral/source-preserving remix | Still bad | Models and skill installation did not fix the creative result |
| Original 2:32 `Thodi_Der_Aur.mp3` | Initially “amazing”; later described as “really good” relative to the hybrid | Preferred melodic/emotional baseline, with a known pronunciation concern |
| 53-second Sonic Pi + independently generated vocal | Music and voice clearer, but sounded read rather than sung; rejected | Clearer audio alone did not preserve musicality; this vocal approach is not the baseline to develop |

The hybrid vocal prompt emphasized narrow range, one-note-per-syllable phrasing,
minimal melisma and short phrases. Those constraints plausibly contributed to
the recitation-like delivery, but prompt, seed, arrangement and generation mode
all changed. This was not a controlled test that isolates one cause.

The original full-song generation omitted the optional 5 Hz LM. A comparison
with LM planning is a reasonable future experiment; there is no evidence here
that its absence caused the diction problem or that adding it will fix it.

## What a useful next pipeline must preserve

1. Retain the accepted original recording as the comparison baseline.
2. Identify the exact sung words/phrases that listeners hear as unclear.
3. Preserve melody, phrasing, emotional arc and timing while testing a correction.
4. Use a renderer/editor that exposes the needed control: bounded inpainting,
   a melody-conditioned replacement performance, or a real singer/editor.
5. Compare a short corrected passage with the baseline before rebuilding a song.
6. Treat transcription and meter checks as evidence with limits; human listening
   decides whether the correction is both clear and musical.

Sonic Pi is useful for an explicitly composed backing. It should not be added
automatically when a complete generated performance is already the accepted
musical result. No new audio, models, application installations, global skill
registrations or paid jobs were created during this research task.
