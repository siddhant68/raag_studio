# Music-quality review and ElevenLabs recommendation

Reviewed 24 October 2026, India time. Checkout: `8a182c2`. Reviewer inspected current source, read the live SQLite database in read-only mode, compared saved engine requests/results against accepted historical requests, and recompiled the stored sample-1 plan without rendering. No source/settings changes, paid calls, real renders, downloads, or speaker playback were performed.

This is a pipeline and evidence review. The reviewer did not audition the audio or claim a listening verdict. The user's current feedback is that the sample outputs are below the accepted examples in quality. Existing technical checks do not independently confirm or refute that judgment.

## Recommendation

ElevenLabs Music merits a small, monthly personal-use API pilot. Do not buy an expensive annual plan or assume that replacing the renderer will solve composition and lyric weaknesses. Keep ACE-Step as the existing local renderer and evaluate an additional renderer through a separate adapter.

For a public Raag Studio music-generation service, obtain written authorization for the intended use before launch. The current Music Terms distinguish using generated outputs from making the music models available through another app. An ordinary self-serve subscription is not sufficient evidence of permission for that product.

## Verified local findings

### 1. Claude is now active; the old authentication/default-planner blockage is historical

Read-only `data/raag.db` inspection returned `planner_provider = claude_cli` and `planner_smart_enabled = true`. The sample report records Claude planning with no fallback in all ten sample runs. Do not attribute these samples to the Basic planner.

The live planner evaluation report records 21/23 briefs fully right versus Basic 11/23, with qualifications about amended expectations. That measures plan-field adherence, not audio quality. There is still no demonstrated blind preference improvement in music.

### 2. The new batch used the same working renderer, but different requests

Sample `result.json` files identify the shared ACE-Step source, `acestep-v15-turbo`, MPS, Torch 2.11.0. Saved requests use 8 inference steps, shift 1.0, and `thinking=False`, like the accepted historical recipes. No evidence in these receipts suggests an accidental switch to the fake engine or a newly downgraded model.

This is not a controlled reproduction of the accepted pieces:

| Comparison | Accepted anchor | New sample |
| --- | --- | --- |
| Flute-led | Yamuna: 168 s, seed 24102633, flute plus tabla/tanpura/santoor | Sample 1: 60 s, seed 1464442656, accompaniment omitted from the submitted caption |
| Ensemble/wordless | Daylight: 132 s, piano/flute/guitar/strings/bass/percussion, choir, contrasting sections | Sample 3: 60 s, piano/strings/choir, generic slow-build arc |
| Hindi song | Thodi: 152 s, explicit verse/prechorus/recurring chorus/bridge/outro | Samples 9/10: 60 s, newly drafted lyrics, generic section assignment |

Each sample config received one take. These were breadth samples rather than a selection-and-refinement workflow. The effect of duration, seed, arrangement and selection must be tested separately; this review does not prove that short pieces are intrinsically worse.

### 3. The Yamuna-like sample lost its whole accompaniment

Exact saved engine request:

`runs/01M5PTEY5DG9NPKZBPF6KWH1FW/01M5PTEY5EH6YK0JR7NR27JGPH/request.json`

Its caption starts with an unaccompanied flute description and omits tabla, tanpura and santoor. The earlier compiler drop order discarded all three supports to fit the app's 512-character caption cap. This is documented in the sample report and independently visible in the saved request.

Commit `8a182c2` fixes that drop order. Independently recompiling the same stored plan now produces 508 characters, retains all three supports and the flowing-tabla pulse, and drops only flavour and fullness wording. The arrangement report shows no adjustments. The already generated sample audio has not been regenerated; updating the compiler cannot change an existing recording.

### 4. Musical intent is compressed too early

The plan schema exposes one lead, support roles, moods, BPM/key, and three broad arc choices. It has no explicit timed section list for instrument entrances, motif returns, verse/chorus contrast, countermelody or phrase-level lyric placement. Some such wishes can appear in notes without reaching the renderer.

The compiler emits predetermined sentences. This provides validation and repeatability, but it also narrows the musical decisions available compared with the handwritten accepted prompts. Preserve the rich creative plan separately and compile a renderer-specific representation with an explicit loss/unsupported report.

### 5. Songwriting is currently line generation followed by mechanical labels

Locations:

- `app/backend/providers/__init__.py:137`: lyric instructions explicitly request plain lines with no section tags.
- `app/backend/providers/__init__.py:493`: the drafting prompt supplies language, approximate line count and theme; it does not pass the full arrangement or explicitly require a recurring hook, section contrast, tempo-aware phrasing or a speaker viewpoint.
- `app/backend/compiler.py:615`: repeated identical stanzas are tagged as chorus; otherwise tags alternate Verse/Chorus by stanza position.

Sample 10 contains different words in each stanza labelled Chorus. By comparison, accepted Thodi repeats the title hook and central chorus with small variations. A stanza label alone does not create a recurring lyrical or melodic hook. Sample 9 also contains semantically awkward/incomplete phrasing such as its line about faith having "kept empty" without a clear object. These are text observations, not claims about what the model actually sang.

Improve original-lyric mode with a structured songwriting output: title/hook, section identities, repeated chorus, line lengths/breathing room, emotional development, Hindi naturalness review and fit to the intended duration. Preserve exact supplied lyrics unchanged, including permitted repetition; do not apply rewriting heuristics to that mode.

## ElevenLabs capabilities verified from current official sources

- Music v2.5 is available via API as `music_v2_5`. Explicitly set it: the compose endpoint still documents a v1 default. The compose API accepts either a prompt or a composition plan. [Capability overview](https://elevenlabs.io/docs/overview/capabilities/music), [compose API](https://elevenlabs.io/docs/api-reference/music/compose).
- Current v2/v2.5 composition plans are ordered chunks with text/lyrics, duration and positive/negative style directions. Do not reuse the older v1 sections schema by accident. [Composition guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans).
- Inpainting mixes newly generated chunks with referenced stored-audio chunks, so a targeted revision need not regenerate the entire song. This is a promising capability to evaluate, not a claim that Hindi pronunciation or singing identity is guaranteed. [Inpainting guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting).
- Short Audio Reference is documented on paid plans and guides style/sound rather than copying or remixing a recording. Any accepted-original reference would require a separate upload decision and screening. [Capability overview](https://elevenlabs.io/docs/overview/capabilities/music).
- The current upload endpoint describes existing-file inpainting uploads, screening, and an upload charge. The older research's blanket enterprise-upload assumption should be rechecked against the account rather than repeated as a current universal restriction. [Upload API](https://elevenlabs.io/docs/api-reference/music/upload).
- Composition-plan creation is documented as not costing credits, subject to tier rate limits. [Plan API](https://elevenlabs.io/docs/api-reference/music/create-composition-plan).

These are documented product capabilities. No ElevenLabs music was generated or compared in this review. There is no project-specific evidence yet that its Hindi singing beats ACE-Step or the accepted Thodi take.

## Cost and entitlement checks

The API pricing page checked on 24 October advertises Starter $6/month (first-month $1 offer), Creator $22/month (first-month $11), and Music at $0.15 per generated minute, excluding taxes. At that rate 10–15 generated minutes corresponds to $1.50–$2.25 of generation usage, not a promise about the final invoice, minimum subscription or edits/uploads. Other product use and the planner have their own costs.

Start with the cheapest eligible monthly plan for personal testing. Verify music API/model availability and the actual account allowance before a paid batch. The public API pricing and music-terms pages show different included-minute figures; do not promise one fixed allowance without checking the account. Creative-app credits are not automatically the same billing unit as API dollars. [API pricing](https://elevenlabs.io/pricing/api), [creative pricing](https://elevenlabs.io/pricing), [Music Terms](https://elevenlabs.io/music-terms).

Public-product limitation: sections 4.3 and 4.8 of the Music Terms require express written permission for making the models available through a third-party platform/app. Self-serve tiers mark Model Resale prohibited; enterprise arrangements are custom. Personal generation and ordinary output use are distinct from operating a public music-generation service. Confirm the proposed Raag Studio use with ElevenLabs before that launch. [Music Terms](https://elevenlabs.io/music-terms).

## Recommended application maturity work

1. **Establish an accepted-recipe benchmark.** Use the preserved Yamuna/Daylight/Thodi inputs and accepted audio as fixed anchors. Do not compare an altered 60-second single take to a selected 168-second piece and call the difference solely a model failure. Any new render remains subject to the user's current allowance; the recorded ledger is now 19 takes, not the old 9/12 count.
2. **Add a structured creative plan.** Record section purpose/duration, instrument entrances, lead/support relationships, lyric placement, recurring hook/motif intention, energy changes and transitions. Distinguish requested direction from verified acoustic adherence.
3. **Separate generation adapters.** Preserve ACE-Step and add an opt-in ElevenLabs adapter later. Each adapter declares its own duration, caption/plan, lyric, reference and edit capabilities. Do not squeeze the cloud plan through the ACE 512-character serializer.
4. **Build a bounded agent workflow.** Interpret brief -> compose/review plan and original lyrics -> generate candidates within a visible budget -> collect technical findings and explicit listener feedback -> revise selected sections when supported -> preserve the chosen result and recipe. Acoustic tools can support evidence; do not market their output as reliable automatic taste judgment.
5. **Run a small matched audition before committing to the platform.** Use three briefs: expressive bansuri ensemble, ensemble with wordless chorus, Hindi romantic song. Compare similar duration and intent, loudness-match audition copies, conceal provider labels where practical, and record listener preferences. Score hook/melody, arrangement, expressive playing, development, sung phrasing and diction separately.
6. **Add cost and failure discipline.** Store provider/model/request IDs, actual native format, plan/version, lyrics, original response and estimated/actual usage. Never call an MP3 converted to WAV a restored lossless source. Bound revisions and retries; a network timeout with an unknown submission outcome must not trigger an automatic duplicate paid generation.
7. **Keep release gates explicit.** A successful API response is not a quality win. Require listener evidence for Hindi quality claims, verify editing behavior on the chosen model/account, and resolve public-app authorization separately from the personal pilot.

## Immediate next action

Recommend a low-cost monthly personal ElevenLabs Music trial, conditional on API access being present in that account. Evaluate it before larger spend. In parallel, fix composition/lyric preparation and preserve full accepted-recipe intent in the current local path. A cloud engine can provide richer generation/editing capabilities; the producer workflow remains essential whichever renderer is selected.
