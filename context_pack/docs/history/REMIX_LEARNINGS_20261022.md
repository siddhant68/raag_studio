# What we learned

## User's musical brief

The result must be recognisable and substantially transformed. Sid wants the
reaction “I heard it somewhere, but this is so cool.” Mere joins, continuous
playback of each source in turn, or arbitrary chopped fragments do not satisfy
that brief. He described attempt 1 as concatenation and attempt 2 as a random
mix. Both are rejected creative baselines.

## Confirmed assets and setup

- Both supplied song files are approximately 30-second excerpts, not full songs.
- The initially named `sonic-pi-2026-10-22-04-35-25.wav` was our earlier Sonic Pi
  test recording, not Ashes. The correct local file is `ashes_on_the_fire.mp3`.
- Sonic Pi 5.0.0 arm64 was installed. Its initial audio restart loop was resolved
  using Preferences → Audio → Reset. Playback and WAV recording worked.
- Earshot 0.3.0 is installed with pinned, hash-checked local CLAP and AST models.
- ffmpeg is installed. Its build has no Rubber Band filter. The separate
  `rubberband` CLI is installed and supports independent pitch/time adjustment.
- The original video runtime must remain unchanged. Added audio packages use
  separate environments; existing libraries are only referenced read-only.

## Failures to avoid

1. Beat/BPM and global key estimators are fallible, especially with orchestral
   music, rubato and half/double-time interpretations. A tempo number is not a
   verified bar grid or phrase map.
2. Random re-triggering can destroy the interval and rhythm patterns that make
   a theme recognisable. Preserve an identifiable statement before varying it.
3. A constant bass pedal, loud new drums and repeated effects cannot replace
   harmonic planning and actual thematic development.
4. High-passing a low cello melody can remove its identity. Choose a register
   and instrument for the melody before making space with EQ.
5. Simultaneous dense orchestral sources fight for attention. Give the melody,
   answering line, ostinato and low end distinct jobs and registers.
6. “No clipping”, target LUFS and broad genre labels establish limited technical
   facts. They do not establish good harmony, groove, taste or recognisability.
7. Earshot is not human hearing. Its documentation explicitly excludes taste
   and lyric/language judgement. Local classifier results remain hints.
8. A text skill adds procedure and musical criteria. It does not add an actual
   singing voice; an audio renderer or performer is still needed.

## New approach

Use an explicit arrangement specification. Name what each source contributes,
preserve longer contours, choose one underlying pulse, limit decorative new
material, and develop the same motifs. Plan a quieter passage and instrument
exits. Use a local music model to explore reorchestration of a deliberately
arranged guide. Keep its native output separate from any later restoration of
recognisable source phrases. Report which parts are model-generated versus
sampled. Do not call the result professional until there is listening evidence.

The new guide interprets the selected Castamere contour as a 12-beat cell and
the Ashes phrase as 16 beats on a 102 BPM pulse. This is an arranging choice,
not a claim that either entire source has been definitively transcribed.
Their cycles meet over a 12-bar development section. The quiet cello statement
returns in a higher string register, rather than being chopped into an unrelated
percussion instrument.

## Practical technical lessons

- Short sample loudness measurements need at least a 400 ms measurement window.
- ffmpeg loudnorm JSON is followed by console text; parse one JSON object rather
  than treating the entire stderr tail as JSON.
- Native libraries such as torch and torchaudio need matching versions.
- Shell DNS is unavailable in this session; the host Node runtime can download
  repository snapshots, models and dependencies. Record SHA256 and revisions.
- Keep hosted audio uploads separate from local analysis. No consent to send
  these recordings to an external audio-critique service has been given.
- New tools being present does not prove musical improvement; retain user
  acceptance as an explicit separate status.

## Final render lesson

ACE-Step's generic dataclass instruction must be replaced with the official
task-specific instruction. `cover-nofsq` at strength 1.0 preserved the arranged
guide much more closely than the earlier cover configuration; it also left
little evidence of independent reorchestration. Preserve that distinction in
describing the final remix. Its creative changes come mostly from the explicit
arrangement and final section automation. Final selection: `full_02`; user
listening acceptance is still pending.
