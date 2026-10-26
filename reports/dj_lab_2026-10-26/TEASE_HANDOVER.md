# Tease & handover shipped in DJ Lab

The user approved the Kala → Nashe rhythmic tease and then the gradual deck-volume handover on 26 October 2026. This behavior is now the `tease_blend` preset and the Club default.

- Both decks overlap for 16 beats (four bars).
- The final eight overlap beats tease the incoming release passage with 2-beat, 1-beat and half-beat repeats, using real source slices with short anti-click ramps.
- B volume follows sin(overlap_progress × π/2)^1.25; A follows cos(overlap_progress × π/2). B bass opens during the final eight beats as A's loop exit withdraws its bass.
- At the outgoing end, B releases into its continuous passage at full volume.
- The existing loop tightening and exit withdrawal remain, with the requested A volume fade applied.

Choose at least 24 beats for both decks. B's cue is the beginning of the overlap, not the later release; release is 16 beats into the selected B passage. No extra source pre-roll is invented. The UI duration estimate, API validation and saved recipe reflect the overlap. `reveal_s` marks the release; `overlap_start_s` marks the audible entrance. The other five techniques retain their behavior.

A real Kala → Nashe job was completed through the live API: `71e17bf0a540480593645d299ed23030`, 28.235 seconds, visible in the local listening room. It uses the approved overlap/release material with a shorter post-transition tail (32 incoming beats) than the offline 40-beat study. Commercial source audio remains local and ignored by git.

Verification: known-signal tests check monotonic volume curves, overlapping buses, exact repeat schedule, post-release signal preservation and invalid short passages. Real ffmpeg/rubberband renders verify timing, MP3 waveform validity, true peak and level-matched comparisons. API tests exercise import, analysis, rendering, playback, recipe/catalog persistence and video export for this preset as well as echo reveal. Listening approval concerns the supplied Kala/Nashe example; other source combinations need auditioning.
