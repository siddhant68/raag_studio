# Voice identity, Hindi diction and singing feasibility

Public documentation and source inspection, 24 October 2026 (India time). This report does not claim an audio audition or a successful conversion. It complements the authenticated UI and generation experiments recorded elsewhere. This source-study track spent **0 credits**, installed no models, and changed no voice profiles.

## What the evidence supports

| Question | Supported status | Boundary / missing proof |
| --- | --- | --- |
| Use an existing speech clone directly in Music | No direct linkage in inspected composer/editor or public compose schema | Bounded route inspection; absence does not prove every possible route impossible |
| Professional Voice Clone as a singing model | Explicitly unsupported in the PVC product guide | PVC accepts spoken recordings; Creator entitlement does not establish singing support |
| Music Finetune for vocal character | Documented stylistic adaptation, including vocal style | No guarantee of exact singer identity; separate training and identifier, not a speech clone |
| Reference audio as identity clone | Unproven | Style/timbre influence and stable personal identity are distinct success conditions |
| Convert an already sung performance in ElevenLabs | Built-in Roger mechanism test generated audio; singing preservation unproven | E18 used a mixed source; no reliable vocal-pitch reference or listening; personal identity not tested |
| Hindi/English singing in the same own voice | Unproven; eligible own-voice target not established in selected library | Separate Instant/Professional filters settled to No voices found; other workspaces/external targets not assessed |
| Fix a wrong sung syllable by changing timbre | Not established | A correct replacement performance or lyric-aware local regeneration is needed; a timbre change alone does not demonstrate a word correction |
| VoiceStudio as a ready Hindi singing repair solution | Not established at inspected revision | Active conversion reconstructs speech from transcript; archived singing designs do not establish current melody-preserving execution |

## ElevenLabs: separate the routes

**Professional Voice Cloning.** The current [PVC guide](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning) explicitly says “Professional Voice Clones do not currently support singing.” It requires spoken training recordings. This is a product limitation for that cloning route, rather than a claim about all possible audio conversion.

**Music generation.** The [compose schema](https://elevenlabs.io/docs/api-reference/music/compose) describes prompt or composition-plan input and `music_v1`, `music_v2`, and `music_v2_5`. It exposes `finetune_id`; no speech `voice_id` field appears in the inspected request. `seed` applies to composition plans and does not guarantee exact reproducibility. These are API observations, not evidence of which Music model the website uses or account entitlements.

**Music Finetunes.** The [finetune guide](https://elevenlabs.io/docs/eleven-creative/products/music/finetunes) describes conditioning stylistic patterns, including timbre and vocal style, with language and structure directed by the prompt. That is weaker than guaranteed identity cloning. Its upload requirements are distinct from ordinary reference audio: up to 50 tracks, 10–600 seconds each, up to 30 MB per track and 250 minutes total. Training eligibility, price and actual account controls must be inspected before any experiment; this task does not authorize training.

**Voice Changer.** The [capability guide](https://elevenlabs.io/docs/overview/capabilities/voice-changer) documents Hindi, multilingual performance transfer, and cloned/designed target voices supplied by `voice_id`. It recommends `eleven_multilingual_sts_v2`; the English model only supports English. Its five-minute limit and duration-based billing are documented, but website credits must be read from the actual estimate. The [API request](https://elevenlabs.io/docs/api-reference/speech-to-speech/convert) takes source audio and a target voice, with model, seed and optional noise removal. It does not expose a lyric editor, F0/MIDI conditioning or a note-preservation contract in the inspected schema.

There is an official [Singing Voice Changer marketing page](https://elevenlabs.io/voice-changer/singing) advertising singing voices and multilingual use. Its FAQ also uses TTS language. Treat that as a marketing claim that motivates a test, not measured evidence of melody preservation, own-voice identity or Hindi accuracy. The [technical product guide](https://elevenlabs.io/docs/eleven-creative/playground/voice-changer) emphasizes speaking cadence and performance transfer. These sources support different claim strengths; neither should silently override the other.

## Live mechanism follow-up: E18 and Finetunes

The root investigation subsequently ran Voice Changer on a 15-second mixed E01 crop with built-in **Roger**, **Eleven Multilingual v2**, stability 0.5, similarity 0.75, style 0, noise removal off and speaker boost on. The output downloaded and decoded to about 15.0465 seconds. Native UI balance 118,850→118,600 confirms 250 credits. This demonstrates an available audio-in/audio-out mechanism on the account, **not successful own-voice singing**. Source ASR is unreliable; the local pitch tracker follows low-confidence pitches near its lower limit. No note-contour, diction or identity success is established. Exact settings/evidence: `experiments/E18/input.json`, `result.json`, `pitch_timing_analysis.json`; see `AUDIO_EVALUATION.md`.

The live Finetune form showed **Music v2**, one free training remaining, and **1–240 minutes** total audio. This differs from the public guide's 250-minute limit; record the account form as the operative observed validation and retain the discrepancy. No training was launched. This does not create or establish a speech-clone-to-Music linkage.

Native inspection found no direct speech-clone picker in the Music composer or section editor. My Voices with an empty search separately settled to **No voices found** under the Instant Voice Clone filter, then under Professional Voice Clone. Default voices briefly appeared during loading and were not counted as filtered results. This establishes a missing eligible target on that selected-workspace route, not absence from all workspaces or external services. No own-voice sample was sought or clone created. Evidence: `research/evidence/UI-VOICE-FINETUNE.md`.

## Correct VoiceStudio identity and implementation

Repository: [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio). `git ls-remote` resolved HEAD to **`a40fb8fb984f68b7bd882e4f96604e31b22fc1bc`** during this inspection. This differs from the 23 October review's pinned revision `f3d685ac293d9423a85c82c629c931e7da5c7a7b`. Selected files were read from immutable raw URLs at the new revision, never imported or executed. The recursive GitHub tree returned 4,213 entries with `truncated: false`; that is path inventory, not exhaustive code analysis. Copies and SHA-256 hashes are in `voice_sources/source-manifest.json`.

The [feature catalog](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/docs/feature-catalog.md) and [engine guide](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/docs/engines/README.md) describe speech engines, cloning, dubbing and vocal isolation. Broad language coverage is not a singing-quality measurement. This repository is distinct from `msrbuilds/voice-studio`; the existing application with that origin must not be relabeled as the debpalash project.

The active [`POST /convert` implementation](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/backend/api/routers/voice_convert.py) runs ASR without word timestamps, cleans the transcript, calls the selected cloning-capable TTS backend with the target profile reference, and optionally time-stretches the resulting take toward the source duration. No source melody/F0 is carried through this inspected path. The stretch preserves the newly generated audio's pitch while changing duration; it does not recover source notes. Therefore this path is evidence of transcript-mediated speech conversion, not singing voice conversion.

An optional [`services/rvc.py`](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/backend/services/rvc.py) contains RVC post-processing with selectable F0 method, semitone shift and an external `.pth` model plus optional index. It is disabled by default, requires the separate library and model, and can return the original file when unavailable or when inference fails. In the inspected [dubbing renderer](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/backend/api/routers/dub_generate.py), it processes an already synthesized TTS segment. Its presence does not show preservation of the original song melody, successful execution on this Mac, or a ready own-voice singing model.

The archived [singing ADR](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/docs/adr/SPIKE-02-singing.md) states that the early OmniVoice-singing variant lacked F0/MIDI conditioning and could not follow a source melody. It points to a historical SoulX-Singer plan and includes a “feature shipped” historical note, but those statements do not establish active code or a current supported route. No SoulX path was present in the complete current filename inventory; the inspected registry and active conversion/dubbing entry points did not establish that route. This is a bounded negative result, not a claim that all code or upstream engines are incapable of singing.

## Pronunciation controls and useful next tests

VoiceStudio's [pronunciation core](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/backend/services/pronunciation.py) applies global/per-language respellings and inline replacements before speech synthesis. Its `entries_for_language` skips IPA/CMU rows in this path; `inert_entries_for_language` reports them, and the [regression test](https://github.com/debpalash/VoiceStudio/blob/a40fb8fb984f68b7bd882e4f96604e31b22fc1bc/tests/test_pronunciation_inert_1949.py) pins that behavior. Engine-specific inline markup is separate. None of this establishes Hindi phoneme control in ElevenLabs Music or note-preserving repair of an existing sung word.

The following remain **test hypotheses**, not demonstrated wins:

1. For Music, preserve original Devanagari words and change only the natural-clear-Hindi phrasing instruction. Compare vowels/consonants, breath spacing, lyric coverage and sung melody independently.
2. Compare a fixed phrase at two allotted durations before changing lyric spelling. This tests crowding; it does not prove a tempo or script is universally better.
3. For conversion, use a short correctly pronounced, already-sung isolated phrase and an existing eligible target voice. Retain source and result; compare note contour, timing, consonant onsets, artifacts and identity. Avoid noise removal as an uncontrolled extra variable.
4. Only after that mechanism works, compare matched Hindi and English phrases. Personal-identity conclusions require an established own-voice target; a built-in voice only tests the mechanism.
5. For a wrong source word, compare a selected-section lyric regeneration or correctly performed replacement guide. Score the changed word and all surrounding retained audio; do not infer local preservation merely from a shorter edit selection.

No fluent-listener diction scores, singing-quality scores or identity scores were produced by this public/source track. Any paid tests, costs and account-specific controls belong in the shared experiment log and UI findings.
