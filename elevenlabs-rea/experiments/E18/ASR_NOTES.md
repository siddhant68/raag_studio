# E18 conversion ASR and pitch/timing diagnostic

Source and converted output were transcribed independently, offline, without any lyric prompt. Source ASR hallucinates English despite Hindi selection; converted ASR roughly recovers opening chorus words with uncertain endings. No objective diction improvement/preservation score is justified.

`pitch_timing_analysis.json` retains local pYIN diagnostics. Reject the pitch results: estimates cluster near 65Hz lower bound with very low voiced probabilities, and source is a full mix. Source 15.000 s/output 15.0465 s and approximately 23ms envelope lag are gross timing measurements only. No note, syllable, identity or singing-quality preservation established. See `research/AUDIO_EVALUATION.md`.
