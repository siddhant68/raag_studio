# Lyrical-song prompt laboratory

These are original proposed experiments, not observed winning ElevenLabs prompts. Select a small core set within `HANDOFF.md`'s budget. The goal is to learn what works, not to validate every sentence below by generating a separate song.

## Shared lyric fixture L1

Original short Hindi words for controlled tests. Preserve the words and the intended chorus repetition; store each actual input verbatim. If a UI offers separate sections, place text in those sections rather than blindly pasting instructions into lyric lines.

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

This fixture tests singing and structure, not literary perfection. Use the same exact text when measuring the effect of arrangement direction. If the lyric editor automatically changes it, record the before/after instead of hiding the change.

## Core queue

| ID | Question | Controlled comparison | Priority |
| --- | --- | --- | --- |
| E01 | What does a concise musical brief produce for exact supplied Hindi words? | L1, 90 s, one variant, no reference | First |
| E02 | Does explicit chorus contrast and vocal phrasing help? | Same L1/model/duration; change only arrangement/delivery detail | First |
| E03 | Can identical lyrics get deliberately new music? | Same L1 and duration; new project without audio reference, change musical direction | First |
| E04 | How much can an original reference guide the result? | Best earlier output as permitted short reference; retain chosen style settings, compare with an equivalent no-reference request if budget permits | First |
| E05 | Can an edit remain local? | Best earlier song; revise only its chorus, keep other sections | First |
| E06 | Can a phrase be repaired while preserving music? | One original line/section, small delivery or pronunciation correction; verify retained portions | Second |
| E07 | Does brief-only lyric writing create a real hook? | New original Hindi song from a concise story brief; inspect chorus repetition before rendering if possible | Second |
| E08 | Is form lost between the prompt and lyric editor? | Inspect same words as dedicated lyrics versus embedded in brief; paid rendering only if inspection leaves a useful question | Second |
| E09 | Can a short hook be developed into a whole song? | Extend a selected strong section with a contrasting verse and final chorus | Optional |
| E10 | Which script helps Hindi diction? | Same content in Devanagari versus carefully checked Roman Hindi; matched settings; do not substitute English words | Optional |
| E11 | Does short versus detailed prompting differ? | Same lyrics/controls; concise evocative brief versus longer production instructions | Optional |
| E12 | Does the finding repeat? | Repeat the most promising contrast, with exposed seed held constant if supported | Reserve |
| E13 | Which Hindi clarity instruction helps without losing melody? | Same original words/melody target: neutral versus natural clear Hindi delivery versus over-enunciated control | Deep study |
| E14 | Can a vocal character carry across languages? | Own/permissioned identity and matched phrase purpose; Hindi/English sung and speech conditions kept separate | Deep study |
| E15 | Does lyric density or tempo cause unclear words? | Fixed Hindi words and model; change only allotted phrase time or tempo in separate comparisons | Deep study |
| E16 | Can one unclear sung word be repaired locally? | Small section repair with exact words, preserved tune target and retained surrounding audio | Deep study |
| E17 | Does Music expose the user's existing voice clone? | UI/schema inspection first; no assumption that speech voice IDs work in Music | Deep study |
| E18 | Can conversion preserve an already-sung performance? | Short permitted sung phrase before/after supported Voice Changer route; inspect timing and pitch as well as timbre | Deep study |
| E19 | What can the correct VoiceStudio actually contribute? | Code/docs inspection of debpalash/VoiceStudio; speech clone versus melody-conditioned singing/repair | Feasibility only |
| E20 | Does the best recipe sustain a full song? | Develop to 120–180 seconds, recurring hook, contrasting verse/bridge, final chorus and ending | Deep study |
| E21 | Which important findings replicate? | Repeat two useful comparisons within reserve; retain negative results | Reserve |

Uncontrolled randomness limits causal conclusions. If seed control is unavailable, state that. Avoid reporting one sample as statistically convincing evidence.

## E01: concise baseline

Use the dedicated lyric input for L1 where available. Main prompt:

```text
A tender Hindi acoustic-pop love song, 76 BPM. Warm expressive male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Intimate, hopeful and unhurried. Sing the supplied Hindi lyrics as a flowing melody, using the chorus as a memorable returning hook.
```

Use 90 seconds if supported and inspect the lyric layout before generating. Do not add every imaginable musical term.

## E02: arrangement and sung-phrasing variant

Keep L1, model, duration and other controls identical to E01. Replace only the prompt:

```text
A tender Hindi acoustic-pop love song at 76 BPM with warm male singing, fingerpicked acoustic guitar, felt piano, gentle bass and brushed drums. Begin with a short guitar introduction. Keep the verse low and intimate, with breathing space between lines. Let the chorus open into a higher, sustained melodic hook; repeat that chorus tune when its words return. Add soft strings and restrained backing harmonies to the final chorus. End with a gentle instrumental resolution. Sing the provided words naturally and clearly, with connected melodic phrases rather than spoken delivery.
```

Questions: Is the verse/chorus contrast audible? Does a chorus tune return? Do the extra instructions crowd out natural performance? Is the final chorus different in the requested way?

## E03: same words, completely new music

Start a new composition using L1, not a remix/edit of E01 and not an audio-reference flow. Preserve duration for comparison.

```text
Compose a fresh melody for the supplied Hindi lyrics as an uplifting electronic-pop song at 104 BPM. Female lead singing, syncopated bass, light electronic drums, shimmering keys and a wide chorus. Make the verse rhythmically playful and the chorus easy to remember and sing back. Keep all lyric words and the repeated chorus unchanged. Give this a distinctly new tune and groove rather than reproducing another recording.
```

Questions: Did the words remain unchanged? Did the musical direction actually change? Did a faster tempo make syllables rushed? Did the model introduce an instrumental section where it needed room for words? This is a new-composition test: recognizable similarity to E01 is not a success criterion.

## E04: reference guidance versus reinterpretation

First inspect which reference options the actual UI offers. Record their explanations and entitlements. Prefer a new original output from this experiment as the source. Keep an immutable source copy and identify the selected reference span.

Test these intentions separately; they are not interchangeable:

**Style-guided new song:**

```text
Use the reference for its intimate vocal distance, warm acoustic texture and relaxed pulse. Compose a new song with the supplied lyrics and a fresh melodic hook. Keep the arrangement spacious. The reference guides the sound and mood; avoid reusing its lyric content.
```

**Reinterpretation of our original source:**

```text
Reinterpret this original song as a gentle cinematic waltz. Retain the supplied lyrics and the recognizable chorus contour where the workflow supports it. Change the groove to 6/8, replace the acoustic-pop backing with piano, bowed strings and light hand percussion, and create a gradual final-chorus lift. Preserve the intimate emotional delivery.
```

The second test intentionally requests a stronger transformation. Do not assume the style-reference upload feature supports it. If it does not, record the failed hypothesis and inspect whether the existing-song/conditioning/editor workflow is the appropriate route. Do not report a different composition as a source-preserving remix merely because the prompt used the word remix.

## E05: localized chorus revision

Use the actual section-edit workflow, not a whole-song creation field:

```text
Change only the selected chorus: give its final two lines a more open melodic lift, add quiet backing harmonies, and let the strings enter underneath. Keep its exact lyric words. Preserve the verse, intro and ending as they are.
```

Record selection boundaries, old/new versions and billed scope. Compare audio outside the selected span if downloads and alignment are available. A changed encoding or sample offset requires alignment before waveform comparison. A smoother song does not prove the untouched sections are identical.

## E06: line-level delivery repair

Choose an actual unclear line after listening or an independently flagged line requiring review. Do not invent a pronunciation fault from the intended text alone.

```text
In the selected phrase, make the Hindi words easier to understand with natural vowel lengths and cleaner consonant onsets. Keep the existing words, melody, timing and intimate delivery as closely as this editor supports. Avoid changing the surrounding sections.
```

This is a preservation target, not a guarantee. Check whether the voice, tune or timing changed. Do not replace singing with speech to obtain a better transcript score.

## E07: original lyrics and song from a story

```text
Write and sing an original Hindi romantic song about two people who keep finding excuses to stay together for another cup of tea. Use simple, natural Hindi and one short recurring chorus hook. Warm male vocal, acoustic guitar, soft piano and restrained strings, about 90 seconds. Let the verse notice small everyday details, the chorus admit the feeling, and the final return feel warmer. Keep the singing melodic and leave breathing room between phrases.
```

Inspect whether the product exposes lyrics before committing to audio. Record weak Hindi phrasing and whether editing it is easy. Do not treat a different poem in each stanza as a repeated chorus.

## Proposed reusable prompt structure

Use this as a hypothesis to refine, not a universal proven recipe:

```text
TASK: new song / new music for exact lyrics / reference-guided song / selected-section edit.
MUSICAL IDENTITY: genre, emotional intention, groove/tempo, main instruments.
VOCALS: language, delivery, phrasing and relationship to backing voices.
WORDS: dedicated exact lyric text or an original-writing brief.
DEVELOPMENT: ordered section changes and recurring hook intention.
REFERENCE: what to retain, what to change, and which reference mechanism is selected.
REVISION SCOPE: selected span and preservation targets.
ENDING: emotional and musical resolution.
```

Keep instructions in the interface's appropriate fields. Discover whether parentheses, square brackets or other notation become audible; do not assume another product's markup syntax is interchangeable. Promote a pattern to the final playbook only with actual output evidence or mark it documented/untested.

## Scoring and decision rule

Record separate 1–5 listener scores for sung melody, recurring hook, lyric fidelity, diction, phrasing, emotional delivery and musical development. Add reference fidelity and requested novelty only where relevant. Use `pending_listening` for unavailable judgments, not zero.

A useful result is a repeatable improvement tied to a specific instruction and supported workflow. A technically valid file, a guessed note about a singer's emotion, or a text prompt that merely sounds professional is not enough.

## Deep-study additions: pronunciation and personal singing voice

Read `VOICE_AND_PRONUNCIATION.md` before the E13–E19 track. Do not assume any voice clone is eligible for singing or that a VoiceStudio artifact can be imported into ElevenLabs.

For a clarity-only prompt variant, keep the music/words fixed and try:

```text
Sing the supplied Devanagari Hindi naturally, with accurate vowel lengths, distinct consonants and breathing space between phrases. Keep the melodic phrasing and emotional delivery. Give longer syllables enough musical time rather than rushing or turning the line into spoken narration.
```

For the optional Roman-Hindi condition, have a fluent reviewer check the transliteration before comparing; otherwise mark it an unreviewed transliteration, not an exact phonetic reference. Use an original fixture rather than rewriting famous lyrics.

For a conversion-only test, begin with an already sung, correctly pronounced short phrase and an eligible existing permissioned voice. Test the actual supported controls. Compare source versus result for melody contour, note duration, syllable intelligibility, consonant timing, register, vibrato and recognizable vocal identity. A changed timbre is not evidence that wrong words were corrected; a better transcript is not evidence that the performance stayed melodic.

Do not synthesize a spoken TTS reading over a backing track and score that as successful cloned singing. Record separately if a tool only produces speech, approximate chant, or an uncontrolled singing effect.
