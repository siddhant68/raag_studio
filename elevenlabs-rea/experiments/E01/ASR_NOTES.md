# E01 exploratory local ASR

Hindi transcription used an existing multilingual MLX Whisper small model, offline, with no lyric/fixture prompt. `asr_hi_unprompted.json` retains the temperature-0 pass including repetitive-token hallucinations. `asr_hi_fallback.json` is the follow-up using the default temperature fallback and no previous-text conditioning.

Fallback output approximately recovers the verse and both repeated chorus texts. Several intended words differ in ASR, especially ठहर (36–42 s and 68–74 s). This is an audition pointer, not a confirmed pronunciation defect. See `research/AUDIO_EVALUATION.md` for method, limitations and timestamps. Melody, diction quality, hook and identity remain pending listening.
