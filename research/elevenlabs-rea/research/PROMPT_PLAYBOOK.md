# Lyrical-song prompt playbook — tested pipelines, listening pending

24 October 2026 (India time). All generated Music runs below used the website's **v2.5**, one variant, dedicated Custom lyrics except E07 Auto lyrics. These are exact submitted examples and observed input/plan/asset outcomes. **No prompt is established as an audible quality winner.** Randomness was uncontrolled (no exposed seed); single samples do not support causal superiority claims.

The reproducible beginner workflow is: select one variant, choose an explicit duration, put instructions in the Music prompt and exact words in Custom lyrics, inspect the cost, generate once, then inspect the saved section plan and preserve the original download. This pipeline worked for E01/E02/E03/E13/E20. It establishes usable product routes, not guaranteed sung exactness. Section labels produced editable sections in E01; do not assume arbitrary markup will stay silent.

## Exact lyrics fixture

L1 is the original Hindi verse plus twice-repeated chorus used to hold words constant in E01/E02/E03/E04/E13. Use the dedicated lyric field:

```text
[Verse]
खिड़की पे हल्की धूप रुकी
तेरी हँसी फिर याद आई
कप में बची चाय की गर्मी
चुपके से तेरी बात सुनाई

[Chorus]
थोड़ा सा दिन मेरे नाम कर
दो पल यहीं मेरे पास ठहर
तेरी हँसी से सुबह बने
फिर चाहे शाम उतरती रहे

[Chorus]
थोड़ा सा दिन मेरे नाम कर
दो पल यहीं मेरे पास ठहर
तेरी हँसी से सुबह बने
फिर चाहे शाम उतरती रहे
```

Stored-plan success: E01 retained these words and expanded into Verse/Chorus/Chorus 2, 30 seconds each. Its per-section styles included verse intimacy, chorus lift and a returning final hook. Where the expansion executes is unknown. Audio ASR approximately recovered the words and chorus recurrence, but uncertain ठहर and other spellings require listening. No exact-lyric guarantee follows.

## E01: Concise acoustic baseline

90 seconds; L1; no reference. Generated and downloaded; saved words/styles inspected. Use as the baseline, not a proven best prompt.

Exact submitted Music prompt:

```text
A tender Hindi acoustic-pop love song, 76 BPM. Warm expressive male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Intimate, hopeful and unhurried. Sing the supplied Hindi lyrics as a flowing melody, using the chorus as a memorable returning hook.
```

## E02: Ordered arrangement and melodic phrasing

90 seconds; identical L1/model; detailed arrangement/delivery changed. Generated. ASR suggests chorus-text recurrence and a possible repeated final line; hook, phrasing, strings and harmonies need audition.

Exact submitted Music prompt:

```text
A tender Hindi acoustic-pop love song at 76 BPM with warm male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Begin with a short guitar introduction. Keep the verse low and intimate, with breathing space between lines. Let the chorus open into a higher, sustained melodic hook; repeat that chorus tune when its words return. Add soft strings and restrained backing harmonies to the final chorus. End with a gentle instrumental resolution. Sing the provided words naturally and clearly, with connected melodic phrases rather than spoken delivery.
```

## E03: Same words with fresh musical direction

90 seconds; L1 in a new independent project, no reference. Generated a distinct asset. Female voice/electronic groove/new tune are requested attributes, not listening-verified outcomes. This is the route for completely new music rather than editing an existing recording.

Exact submitted Music prompt:

```text
Compose a fresh melody for the supplied Hindi lyrics as an uplifting electronic-pop song at 104 BPM. Female lead singing, syncopated bass, light electronic drums, shimmering keys and a wide chorus. Make the verse rhythmically playful and the chorus easy to remember and sing back. Keep all lyric words and the repeated chorus unchanged. Give this a distinctly new tune and groove rather than reproducing another recording.
```

## E04: Style reference with exact words

90 seconds; L1 and baseline brief, plus a 0–30-second WAV crop of E01. Reference accepted, influence UI value 1. This intentionally holds the text brief constant to test reference presence. Audible transfer and novelty remain pending; no stronger remix conclusion follows.

Exact submitted Music prompt:

```text
A tender Hindi acoustic-pop love song, 76 BPM. Warm expressive male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Intimate, hopeful and unhurried. Sing the supplied Hindi lyrics as a flowing melody, using the chorus as a memorable returning hook.
```

## E07: Original song from a story brief

90 seconds; Lyrics Auto, no supplied L1. Generated title एक और चाय. Saved generated lyrics are in `experiments/E07/generated_lyrics.txt`; exposed plan uses Verse 1 32s, Chorus 18s, Verse 2 24s and Final Chorus 16s. Independent ASR recovered the phrase एक और चाय at least four times. The final chorus retains hook words while changing most lines, so this is not an exact repeated full chorus. Textual editing is needed for awkward lines such as “दिल आराम से कहो” and “हर शाम थोड़ा सा कम है”; melodic memorability and vocal delivery need listening.

Exact submitted Music prompt:

```text
Write and sing an original Hindi romantic song about two people who keep finding excuses to stay together for another cup of tea. Use simple, natural Hindi and one short recurring chorus hook. Warm male vocal, acoustic guitar, soft piano and restrained strings, about 90 seconds. Let the verse notice small everyday details, the chorus admit the feeling, and the final return feel warmer. Keep the singing melodic and leave breathing room between phrases.
```

## E13: Natural Hindi clarity addition

90 seconds; baseline plus clarity instruction, L1 unchanged. Generated. Small-ASR first-verse failure is not a prompt failure or proof of worse diction. No superiority over E01 established.

Exact submitted Music prompt:

```text
A tender Hindi acoustic-pop love song, 76 BPM. Warm expressive male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Intimate, hopeful and unhurried. Sing the supplied Hindi lyrics as a flowing melody, using the chorus as a memorable returning hook. Sing the supplied Devanagari Hindi naturally, with accurate vowel lengths, distinct consonants and breathing space between phrases. Keep the melodic phrasing and emotional delivery. Give longer syllables enough musical time rather than rushing or turning the line into spoken narration.
```

## E20: Develop a longer song with a repeated hook

150 seconds; Custom L2 with Verse 1, Chorus, Verse 2, Bridge, Final Chorus. Generated. Independent ASR approximately recovers these lyric blocks in the requested order and the returning chorus; its beginning and ending include unusable transcription spans. Selected because the structure was useful to test, not because E02 won an audition. The saved plan adds an 8s instrumental intro and 16s outro around five lyrical sections (28/22/28/18/30s), with differentiated verse, bridge and final-chorus styles. All L2 words remain in the displayed plan. Musical development remains listener-pending.

Exact submitted Music prompt:

```text
A tender Hindi acoustic-pop love song at 76 BPM with warm male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Develop the supplied exact words over 150 seconds. Begin with a brief guitar intro. Verse 1 is low and intimate; let the chorus open into a higher sustained memorable tune. Bring that same chorus melody back at the end. Verse 2 adds gentle rhythmic movement. The bridge becomes sparse and vulnerable. Add soft strings and quiet backing harmonies in the final chorus, then end with a gentle instrumental resolution. Sing connected melodic phrases with natural clear Hindi, accurate vowel lengths and breathing space. Keep all supplied lyric words unchanged.
```

Exact dedicated L2 lyrics:

```text
[Verse 1]
खिड़की पे हल्की धूप रुकी
तेरी हँसी फिर याद आई
कप में बची चाय की गर्मी
चुपके से तेरी बात सुनाई

[Chorus]
थोड़ा सा दिन मेरे नाम कर
दो पल यहीं मेरे पास ठहर
तेरी हँसी से सुबह बने
फिर चाहे शाम उतरती रहे

[Verse 2]
बाहर की गलियाँ जाग उठीं
हमने घड़ी से नज़र चुराई
तूने कहा बस एक प्याली
मैंने फिर से चाय बनाई

[Bridge]
रहने दे बातें कल की अभी
इस पल को थोड़ा जी लें हम
जो बात जुबाँ तक आ न सकी
आँखों से आज कहें हम

[Final Chorus]
थोड़ा सा दिन मेरे नाम कर
दो पल यहीं मेरे पास ठहर
तेरी हँसी से सुबह बने
फिर चाहे शाम उतरती रहे
```

## E05: target a section through editor controls

This test did not submit a whole-song replacement prompt. The editor selected Chorus 30–60 seconds and appended three style pills while keeping words unchanged:

```text
higher sustained final lines
quiet backing harmonies
soft strings
```

Generate caused a client error, but history contained a persisted edited composition after recovery. The agent inspected state instead of submitting again. Signal comparison supports a changed selected chorus and strongly similar tested surrounding audio, with zero estimated lag. It does not establish sample identity or audible improvement. Use the section route when retention matters; a fresh prompt alone does not guarantee localized edits.

## E04B: stronger reinterpretation request through the same style-reference route

90 seconds, L1 unchanged, same E01 0–30s reference crop, influence UI value 1. Exact submitted prompt:

```text
Create a new interpretation of this original song as a gentle cinematic ballad in 6/8. Retain the supplied lyrics and the recognizable chorus contour where the workflow supports it. Replace the acoustic-pop backing with piano, bowed strings and light hand percussion, and create a gradual final-chorus lift. Preserve the intimate emotional delivery.
```

The request generated a new asset and an exposed plan with 72 BPM, 6/8, piano, bowed strings, light hand percussion and final-chorus lift. The plan includes “chorus contour kept clear.” This verifies the requested target reached the editable plan; it does not prove the sung notes match E01. The source remains a style reference, so true source-conditioned remix and recorded-audio preservation are unproven. Publish was disabled in this observed reference-derived project, with no reason exposed. Download sidebar offered Vocals & Instrumental Generate and Stems Generate; neither was rendered.

## E12: repeat the baseline before promoting a recipe

E12 reused the E01 brief and L1 for another 90-second generation. ASR approximately recovered the verse and both choruses, with possible extra ending-line repetition that needs audition. This replicates a functioning pipeline and broad text recurrence; it does not replicate a quality advantage. No seed control was exposed.

## E18: conversion controls are a separate mechanism

This was audio-in/audio-out, not a Music prompt: 15-second mixed E01 source crop; built-in Roger; Eleven Multilingual v2; stability 0.5, similarity 0.75, style 0, noise removal off, speaker boost on. The result downloaded and cost 250 credits. No successful singing, diction, note-contour or personal-identity transfer is established. The source contains backing music and local pitch estimates are unreliable. An isolated correctly sung guide plus an eligible own-voice target is the more informative future test. Speech-clone selection and Music style reference must not be conflated.

## Patterns supported by workflow evidence

- Separate musical instructions and supplied words. Custom lyrics preserved L1 in the visible plan and accepted five L2 sections in a longer generation.
- State language, sung delivery and musical identity. The UI accepted genre/tempo/instruments/vocal directions and exposed expanded section styles; actual adherence needs audition.
- Repeat the exact chorus words when recurrence is required. E01/E02/E03/E07 provide approximate ASR textual recurrence; they do not establish the same tune returned.
- Choose the mechanism first. A new project with unchanged lyrics requests new composition; Audio Reference requests sonic guidance; selected-section generation tests retention. These are different tasks.
- Preserve the original and version. E05's source/result downloads allowed a bounded locality measurement after the client error.
- Reserve budget conservatively, inspect refreshed Subscription usage, and inspect history after ambiguous submits. Do not equate a stale balance popup with free generation.

## Untested suggestions and unanswered comparisons

The following remain hypotheses: Roman Hindi versus Devanagari; fewer syllables/slower phrases; targeted word repair; true source-conditioned reinterpretation with recognizable contour; selected extension; English/Hindi identity transfer; replication of a useful prompt-quality contrast. Neither over-enunciation nor a longer technical prompt is demonstrated to help. No pronunciation-dictionary or SSML syntax is established for Music. Keep dialect/phonetic respellings out of an exact-words test unless adaptation is explicitly allowed and separately recorded.

E04B refines the proposed ambiguous waltz/6/8 brief into a cinematic ballad in 6/8 and renders it through style reference. Source-contour continuity remains unverified. For conversion, begin with correctly sung words and a validated eligible target identity. The selected workspace's separate Instant and Professional clone filters settled to “No voices found”; no own-voice target was established. A speech reading over backing music is not evidence of cloned singing.

## What did not establish success

E13's poor ASR is a failed measurement span, not a failed generation. E04's accepted reference is not proof of a successful remix. E05's crash is not proof of a failed billed job. An exact stored plan is not an exact sung transcript. All artistic listener scores remain pending; there are no demonstrated acoustically successful/unsuccessful prompt rankings yet.

Evidence: experiment_log.csv; per-experiment prompt/input/result files; research/evidence/UI-E01.md and UI-EDITOR-E01.md (native browser observations); AUDIO_EVALUATION.md and asr_index.csv (local analysis). REA MCP connectivity is separately verified, but no REA browser/network trace supports these UI findings because an existing CDP route was unavailable.
