# Long overlap listening experiment

User rejected the previous short incoming fades. This study introduces the incoming deck 32 or 64 beats before the existing handover. At 125 BPM these are 15.36 and 30.72 seconds. A third trial uses Kala Chashma into One More Time with 32 beats at 114 BPM (16.84 seconds).

Both decks play during the overlap. B's mids/highs rise to a clearly audible level before the final exit. Its bass enters over the final eight beats, during the existing outgoing loop's bass withdrawal. Previous outgoing and effects buses are preserved. The incoming source is prepared continuously from real earlier material, without a splice at the old cue.

These are pulse-grid candidates, not verified phrase/downbeat annotations. Full stereo mixes may contain competing vocals or harmonies; EQ does not separate vocals. Long overlap alone cannot guarantee musical compatibility. The 16-bar trial starts its incoming fade at the preview beginning because the outgoing excerpt is only 16 bars long. Original outputs and app defaults are unchanged.

Reproduce with scripts/dj_overlap_study.py, using a fresh output directory. Outputs, matched previous comparisons, incoming/outgoing buses, source preparation logs and per-render measurements are under runs/_dj_lab/overlap_study_20261026_v1. Script checks decoded duration/waveform validity, MP3 true peak <= -1 dBTP, and comparison loudness within 0.15 LU. Listening acceptance remains pending.
