# Voice identity, multilingual singing and diction: investigation brief

Added 24 October 2026 following the user's request for a deeper study. This is a feasibility map and experiment plan, not a working integration or an audition result.

## Questions the fresh session must answer

1. Can ElevenLabs Music generate a song using an existing own-voice clone directly? Which model/control actually supports this, if any?
2. Can a reference or Music Finetune influence vocal character? Is that merely a broad style or a reliable identity-preserving mechanism?
3. Can a voice-conversion path transfer an existing correctly sung performance to an eligible own voice while preserving pitch, timing and Hindi words?
4. Can exact Hindi words be made clearer without losing melody, expression or identity? Which prompt, lyric-layout, duration and local-edit choices help?
5. Can the correct VoiceStudio project contribute a speech pronunciation reference, voice cloning, conversion or genuine melody-conditioned singing? What is implemented today, rather than described in an archived proposal?
6. What remains unsupported or unproven for a user who wants to sing in a chosen language in their own voice?

## Current official evidence

**Professional Voice Cloning:** the current ElevenLabs product guide explicitly says this feature does not support singing and requires spoken training recordings. Creator entitlement to a professional speech clone therefore does not establish a Music singing-voice input. Inspect Music's actual selection/schema separately.

Source: https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning

**Voice Changer:** official documentation describes transforming existing audio with a cloned/designed voice, includes Hindi among supported speech languages, and accepts a voice ID. It does not establish singing preservation in the inspected overview. Treat use on singing as a separate short feasibility test, not a documented guarantee.

Source: https://elevenlabs.io/docs/overview/capabilities/voice-changer

**Music Finetunes:** documentation describes adapting instrumentation, genre, timbre and vocal style from uploaded audio. That is distinct from using a professional speech-clone ID. Inspect scope, eligible inputs and cost, but do not train a new model during this investigation without explicit additional direction and appropriate recordings.

Source: https://elevenlabs.io/docs/eleven-creative/products/music/finetunes

**Direct Music API:** the compose schema inspected in the preceding music review exposes prompt/composition plan, model and generation controls. No direct arbitrary speech `voice_id` linkage was established there. Absence from one inspected schema is a bounded observation; verify the current UI/model before drawing a universal conclusion.

Source: https://elevenlabs.io/docs/api-reference/music/compose

## Correct VoiceStudio identity matters

The user's named project is:

```text
https://github.com/debpalash/VoiceStudio
```

However, the local directory below currently identifies its origin as **github.com/msrbuilds/voice-studio.git**, with README title "Voice Studio by MSR":

```text
/Users/sidhandsome/Documents/voice-studio-trial/voice-studio
```

Do not label that installed application as debpalash/VoiceStudio. Its README describes multiple TTS engines, cloning and transcript-mediated dubbing. That is relevant comparative evidence for speech, not proof of melody-preserving singing.

A prior read-only review of the correct debpalash project is preserved here:

```text
/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio/context_pack/docs/research/VOICE_STUDIO_REVIEW.md
```

It was dated 23 October, pinned commit `f3d685ac293d9423a85c82c629c931e7da5c7a7b`, and did not install or test a full integration. It noted speech-oriented active capabilities, pronunciation-control limitations, and archived singing-design work lacking established Hindi melody-preserving repair. Recheck current source; neither discard useful old evidence nor promote a design document to a shipped feature.

Current primary entry points:

- https://github.com/debpalash/VoiceStudio/blob/main/docs/feature-catalog.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/README.md

Inspect the correct source identity/version first. Do not install its multi-model stack or modify the existing speech environment just to answer a feasibility question. Do not assume voice representations, embeddings or cloned models are portable across products.

## Experimental approach

Keep three outputs distinct:

| Track | Input | Required success |
| --- | --- | --- |
| Speech clone | Own/permissioned spoken sample plus text | Voice resemblance and clear speech; never scored as a song |
| Singing generation | Lyrics plus musical/voice directions | A coherent sung melody and intelligible words; voice identity only if actually supported |
| Singing conversion | Already sung phrase plus eligible target identity | Preserve notes/timing while changing timbre, with intelligible words and no major artifacts |

Use an existing eligible own-voice clone only when its ownership/consent and current availability are established. Do not search arbitrary private recordings for a usable voice. If no suitable own-voice sample/clone is available, document that specific missing input, use a licensed built-in voice only for mechanism testing where appropriate, and keep personal-identity conclusions pending. Do not spend the entire research session waiting for the user to record training material.

For Hindi clarity, compare script, word spacing/line breaks, section duration, delivery direction and syllable density one at a time. Preserve source words. Inspect any pronunciation dictionaries or markup only if the actual selected Music model uses them; speech-dictionary support does not establish music support.

For a potential later composite pipeline, the conceptual sequence is:

```text
Correctly sung guide performance
  -> optional separation if the source is a mix
  -> singing-compatible voice conversion, if validated
  -> alignment and remixture
  -> listening check for tune, diction, identity and artifacts
```

This is an investigation hypothesis. It is not permission to replace singing with a TTS reading, nor evidence that changing timbre repairs incorrect syllables. Defer actual application integration as requested by the user.

## Required findings

Conclude separately whether direct clone-to-Music, reference-conditioned identity, conversion of singing, cross-language singing, and word repair are supported, partially supported, unavailable on the tested route, or still unknown. Cite exact tested model/version and input requirements. Provide short before/after examples only when actually generated. Preserve negative results and listener limits.
