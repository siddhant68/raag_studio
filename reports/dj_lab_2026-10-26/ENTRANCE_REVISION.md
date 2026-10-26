# Incoming entrance revision — 26 October 2026

User feedback: the first song exits well, but the second starts abruptly. This is the authoritative verdict for the initial demos; export/test passes did not establish musical acceptance.

Code inspection confirms the cause: loop/drop and echo cuts place the second deck at the handover at full prepared level, with only a 3 ms edge ramp. That is an intentional cut, not a prepared blend.

The new isolated study preserves the outgoing/effect buses and changes the incoming preparation only. It renders a continuous preceding source passage plus the selected incoming passage in one stretch operation, avoiding a separately processed join at the handover. The lead enters without bass, first with a 700 Hz high-pass texture. Over the final four lead beats it opens toward the 180 Hz complementary high band. Gain reaches 0.70 at the original focus point and 1.0 four beats later; bass rises smoothly over those four beats. The two sources therefore share a prepared texture before the original first-song exit.

Four candidates: Daft→FISHER with 8 and 16 beat leads, Kala→Nashe with an 8 beat lead, and Kala→Daft with an 8 beat lead. The short Nashe source has only enough real material before its selected entrance for an 8-beat lead; no invented padding or random repeated lead is used.

Outputs: runs/_dj_lab/entrance_study_20261026_v1/. Each take preserves its previous-version comparison, new WAV/MP3, actual incoming bus, identical outgoing bus, source plan, automation description and matched-level measurements. Existing takes and app defaults remain unchanged pending listening feedback. This tests the identified entrance problem; it is not a claim of DJ-level musical approval.

Technique reference: https://www.native-instruments.com/blogs/blog/dj-transitions — phrase preparation, filter entry and bass handover. Pulse/downbeat accuracy and harmonic compatibility still need listening; longer overlap can expose vocal/key clashes. No model or paid call is used.

Reproduce with the existing audio Python: python scripts/dj_entrance_study.py (choose a fresh output path in the script before a second run).
