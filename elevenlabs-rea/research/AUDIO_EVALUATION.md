# Local audio evidence — provisional, no listener audition

24 October 2026 (India time). Original MP3s were read without modification. No uploads, model downloads or installations were used. Local analysis incurs no ElevenLabs credits. All taste, singer-identity and fluent Hindi diction scores remain `pending_listening`.

## Method and identity

Existing interpreter: `../tools/acestep-venv/bin/python` (Python 3.12). Existing multilingual model: `../tools/whisper-small-mlx`, identified by the selected inventory as `mlx-community/whisper-small-mlx` revision `45f3915923c7a79a5a5b5a7d909d39aeb0e5630e`. The actual model/config hashes and installed `mlx-whisper` version are preserved in each `asr_hi_unprompted.json`; the inventory revision is provenance, not a newly fetched model.

`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; an explicit existing local model directory prevents a fallback download. Hindi language and transcription task were selected. **No fixture, lyric text or initial prompt was fed to ASR.** An initial temperature-0, word-timestamp pass produced obvious repetitive-token hallucinations. It is retained unchanged, not treated as a lyric-fidelity failure. A second pass used the decoder's default temperature fallback, disabled previous-text conditioning and omitted word timestamps. That resolved the loops, while still producing uncertain spellings. These are two decodes from the same small model, not independent judges.

Scripts: `research/scripts/analyze_hindi_asr.py`, `asr_fallback_check.py`, `audio_metrics.py`. Per-experiment raw JSON retains segment timestamps and decoder statistics. Timestamps are ASR estimates and may include instrumental lead-ins or silence.

## E01: approximate Hindi content is recoverable, exactness unproven

The fallback decode recovers the intended verse in rough form at **0–29 seconds**, followed by a chorus at **29–55 seconds** and approximately the same chorus words again at **62–87 seconds**. This is evidence for approximate lyric content and textual recurrence; it does not establish recurring melody, hook quality, natural pronunciation or exact word preservation.

Examples needing human audition:

| Intended text | ASR observation | Review span |
| --- | --- | --- |
| खिड़की पे हल्की धूप रुकी | खिल की पे हलकी दूपरूकी | 0–17 s |
| कप में बची चाय की गर्मी | कप में बची चाए की गरनी | 17–23 s |
| दो पल यहीं मेरे पास ठहर | तो पल यही मेरे पास थे / तो पल यही मेरे पास तर | 36–42 s and 68–74 s |
| तेरी हँसी से सुबह बने | तेरी हसी से सुभा बने | 42–48 s and 74–80 s |

These discrepancies can arise from ASR limitations on music, orthography or actual sung pronunciation. The evidence does **not** distinguish those explanations. Do not present an ASR word-error rate against the fixture as a measured diction score. A fluent listener should check nasalization in हँसी, the vowel/consonant sequence in ठहर, and syllable clarity at phrase ends.

## E02: detailed arrangement prompt — no quality win established by ASR

The no-fixture fallback decode recovers approximate verse text at **0–33.16 seconds**, first chorus at **33.16–56.16 seconds**, and repeat at **56.16–81.16 seconds**. The same difficult phrase ठहर appears as थे है / थेर. At **68.16–76.16 seconds**, ASR emits `तेरी हसी से सुभा मने सुभा बने`, which could be a sung addition/repetition or a decoder error. Audition this span before claiming exact lyric fidelity or an added-word failure. The transcript alone does not establish that E02's requested higher hook, breathing space, final strings or harmonies occurred, nor that E02 is better than E01.

## E03: same supplied words, independent new-composition route

Approximate L1 verse text is recovered at **0–28 seconds**, first chorus at **30–55 seconds**, and repeated chorus at **60–83 seconds**. The second chorus's transcription is less stable (`मेरे नाम कर` becomes `मेरे दाव कर`, for example). The trailing **90.00–90.04-second** repetitive-token segment is an obvious decoder artifact and should be excluded from lyric evaluation. The shared words are broadly recognizable to ASR, but exactness remains unproven. The UI's separate project/no-reference route plus a different output hash establishes a distinct generated asset; this analysis does not establish a new melody, female voice, 104 BPM adherence or better diction.

## E13: natural-Hindi clarity instruction — result needs listening

This holds the E01 brief and L1 words while adding natural Hindi vowel/consonant and phrase-time instructions. In the first **0–25.26 seconds**, the small ASR model fails: it emits mixed-script nonsense, exhausts temperature fallback to 1.0, has average log probability about −1.73 and compression ratio 3.11. That span is **unusable transcription evidence**, not proof the song contains those words or has worse Hindi. The model approximately recovers the first chorus at **25.26–38.26 seconds** and repeat at **55.26–76.26 seconds**, with uncertain ठहर and other spellings. Its **85.26–89.99-second** repetition loop is also excluded. No clarity win or loss versus E01 is established by these outputs. A fluent listener should compare the first verse and matched chorus lines directly; ASR confidence is not a diction score.

## E07: auto-written song has a recurring textual hook

E07 used a story brief and **Auto lyrics**, not L1. Its independent, no-prompt Hindi decode repeatedly recovers **`एक और चाय`** around **32–35 s**, **38–41 s**, **74–78 s** and **81–84 s**. The surrounding approximate content concerns staying together, cups of tea and excuses to delay leaving, which is consistent with the original brief. This supports a recurring textual hook and broad story adherence. It does not prove a recurring melody, memorable hook, native-quality writing or exact audio alignment with the product's saved lyrics. The raw transcript includes likely recognition errors (`पासो`, for example); do not publish it as authoritative lyric copy. The first 30-second ASR segment is broad and truncated mid-word, so its internal timing is especially uncertain.

The later native UI inspection preserved the authoritative **displayed** generated lyrics in `experiments/E07/generated_lyrics.txt` and plan 32/18/24/16-second sections (Verse 1/Chorus/Verse 2/Final Chorus). This confirms a repeated hook phrase in the saved words, with most final-chorus lines changed. The native text review flags awkward lines for lyric editing; it is separate from listening-based diction. See `research/evidence/UI-E07.md`.

## E04: accepted style reference, audible transfer unverified

No-prompt ASR recovers rough L1 verse at **0–29.32 s**, first chorus at **29.32–54.32 s**, and the beginning of a repeated chorus at **54.32–76.32 s**. Its final **76.32–90.04 s** segment is a repeated-token hallucination and provides no trustworthy evidence of the last line or ending. The original 30-second crop was accepted by the product and a new asset generated; ASR cannot establish whether vocal distance, texture, pulse, melody or singer identity transferred. Reference influence and novelty require source-versus-result listening on the specifically requested attributes. This is a style-reference pipeline test, not a demonstrated source-preserving remix.

## E20: 150-second song broadly follows the expanded L2 sequence

The longer fixture supplies Verse 1, Chorus, Verse 2, Bridge and Final Chorus. ASR approximately recovers the first verse through **34.96 s**, chorus at **34.96–51.96 s**, second-verse content at **51.96–85.96 s**, bridge words at **85.96–99.96 s**, and returning chorus at **103.96–131.96 s**. This supports broad lyric-section order across a longer generated asset. The first segment is uncertain and repeats some words; the **133.96–150.04 s** tail loops and is unusable transcription evidence. Exact word coverage, intro/ending quality, verse contrast, bridge vulnerability and repeated chorus melody remain unverified. Full length alone does not establish satisfying musical development.

## E12: baseline replication — content recurs, superiority still unproven

The second baseline composition approximately recovers the verse at **9.44–25.10 s**, first chorus at **25.10–52.10 s**, and repeat at **55.10–74.10 s**. ASR emits additional ending-line fragments through **86.50 s**. Those could reflect the sung arrangement or decoder repetition; verify by audition. The intro decode (`McConnell`) is implausible and excluded. This is another successful generation using the baseline pipeline and approximate L1 recurrence, not replication of a perceptual quality effect.

## E18: built-in-voice conversion ran; singing preservation remains unknown

Root's native UI observation records a 15-second **mixed** E01 crop, built-in Roger target, Eleven Multilingual v2, stability 0.5, similarity 0.75, style 0, noise removal off and speaker boost on. It generated a downloadable output; balance 118,850→118,600 establishes **250 credits**. This is not an own-clone or multilingual identity test.

No-prompt ASR on the source crop hallucinates English translations despite Hindi being selected. The Roger result approximately recovers the opening Hindi chorus words but has uncertain endings. Thus the source/result ASR pair is unsuitable for scoring word preservation or improved diction. Raw results are retained separately and correctly linked in the ASR index.

Source duration is **15.000 s** and decoded output **15.0465 s**. A local pYIN diagnostic on 65–1000Hz returned medians near its 65Hz lower bound and median voiced probabilities around 0.01. **Reject these pitch estimates as unreliable**; the raw correlation/cents fields are diagnostic values, not evidence of preserved or altered notes. The mixed source has no isolated vocal reference and can make a tracker follow bass or other instruments. RMS/onset envelopes peak at about 23ms lag within a ±300ms search, which is only a gross timing observation, not syllable or note alignment. File: `experiments/E18/pitch_timing_analysis.json`.

The mechanism accepts and returns audio of roughly the same length. Singing versus speech, singer timbre, note contour, Hindi diction, expression, artifacts and personal identity remain unverified. A correctly sung isolated guide and listening are needed before making a singing-conversion recommendation.

## E04B: cinematic 6/8 reinterpretation request generated, source contour unproven

This stronger request used the same style-reference crop and unchanged L1, asking for a cinematic ballad in 6/8 with piano/strings/hand percussion and a recognizable chorus contour where supported. The exposed native UI plan retains L1 and those targets. ASR approximately recovers verse through 29s, chorus 29–53s and returning chorus 59–79s. Its 79–90.04-second tail is a repetition hallucination and excluded. These text observations cannot establish source-melody continuity, 6/8 rhythm, orchestration, timbre, novelty or quality. A plan saying “chorus contour kept clear” is an instruction, not measured melody preservation. This remains a stronger request rendered through style reference; true source-conditioned remix was not tested.

## E05: selected chorus changes, surrounding audio remains strongly similar

Fallback ASR finds the approximate same verse and two choruses, with first chorus around **29.26–54.26 seconds**. It again varies spellings, including outside the edited section. This variability reinforces that the decoder is not a gold transcript. It does not prove E05 fixed diction or preserved melody.

The existing UI input records selection **30–60 seconds**. Supplemental signal comparison decodes the E01 and E05 MP3s to mono 44.1 kHz, estimates lag within ±100 ms on a downsampled signal, and compares interiors away from boundaries:

| Interior span | Estimated best lag | Correlation at zero offset | Normalized RMS residual |
| --- | --- | --- | --- |
| Verse, 5–25 s | 0 ms | 0.99912 | 0.04189 |
| Edited chorus, 32–52 s | 0 ms | 0.33534 | 1.19749 |
| Final chorus, 65–85 s | 0 ms | 0.99835 | 0.05743 |

This supports a localized change with strong preservation of the tested surrounding spans. **Sample identity is not established**; equal-sample fractions outside the edit were zero, and MP3 encoding differences may explain residuals. These three bounded windows do not establish every outside sample is retained. Audible seams, lyric accuracy and artistic improvement need listening. Details: `experiments/E05/alignment_check.json`; parent analysis also retains `locality.json`.

## Technical measurements

Compact auditable indices: `research/audio_asset_index.csv` / `.json` contain every available audio asset's SHA-256, byte size, codec, duration, channels, bitrate and role (generated download, converted download, reference crop or source crop). Full ffprobe stream/container metadata is retained in `research/audio_probes/`. `research/asr_index.csv` / `.json` link every transcript to its audio and transcript hashes, actual local model hash, package version, no-prompt decoding mode and flags for low-confidence/high-repetition segments. They are rebuilt by `research/scripts/build_audio_index.py`. A flag is a review pointer, not an observed audio defect.

E01/E05 both decode to 3,970,944 mono samples at 44.1 kHz, approximately **90.044 seconds**, and have different SHA-256 hashes. Measurements for all available analyzed MP3s are in `research/audio_metrics.json` and the original per-experiment probe records. Float-decoded mono peaks exceed full scale (E01 about +1.64 dBFS, E05 about +1.70 dBFS). That flags headroom for later export review; it does not establish audible clipping or a perceptual defect. The originals remain untouched. No mastered replacement has been made.

## Required human checks

Listen to the original and edit at matched audition loudness, without replacing either original. Judge separately: actual singing versus speech, recurring tune, melodic hook, exact words, natural Hindi vowels/consonants, breathing/crowding, vocal emotion, requested chorus lift/harmonies/strings, and edit-boundary seams near 30/60 seconds. Until then, the strongest results here are approximate text recurrence and signal-based edit locality.
