# E05 exploratory local ASR and alignment

Both no-fixture Hindi ASR passes are retained. Temperature-0 transcription contains loops; the default-temperature-fallback pass recovers approximate verse and repeated chorus text with uncertain spellings. It cannot establish a diction improvement.

`alignment_check.json` compares three interior windows. Zero-offset correlations are approximately 0.99912 before the selected chorus, 0.33534 inside it and 0.99835 after it. Bounded lag search peaks at 0 ms. This supports localized change and strong surrounding similarity; the files are not sample-identical. No seam or musical-quality audition was performed. See `research/AUDIO_EVALUATION.md`.
