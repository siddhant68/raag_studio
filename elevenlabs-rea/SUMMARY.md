# ElevenLabs Music investigation

24 October 2026, India time. Authenticated research in Siddhant's Workspace on Creator. **Actual spend: 13,750 credits. Account remaining: 117,250. Unspent research allowance: 26,250 of the 40,000 ceiling.** No further paid run is pending. Raag Studio integration remains deferred.

## Findings

**The lyrical-song workflows work operationally.** Custom Devanagari lyrics produced saved songs, editable section plans and downloadable audio. E01 kept the supplied words in its three-section plan. E03 used the same words in a fresh project with a different musical brief. This verifies the route for new music from existing lyrics; exact sung fidelity and melodic novelty still require listening.

**Brief-only writing produced a recurring textual hook.** E07's saved lyrics and independent ASR repeat “एक और चाय.” The generated Hindi also contains awkward lines, so automatic lyric writing needs an editorial pass. A recurring phrase is not proof of a memorable tune.

**Selected-section editing has the strongest measured preservation result.** E05 changed the first chorus while surrounding tested signal windows stayed strongly similar to E01: correlations 0.99912 and 0.99835 at zero estimated lag, versus 0.33534 inside the changed chorus. The MP3s are not sample-identical; audible seams and improvement remain unjudged. A client error occurred after submission, but the completed version survived in history and was recovered without resubmitting.

**Audio Reference accepted our new original recording and generated new songs.** E04 added an E01 excerpt to the baseline; E04B requested a cinematic 6/8 interpretation. Its exposed plan reflected piano, strings, percussion and the requested meter. No evidence yet proves that the source chorus melody or singer identity survived. Style guidance, musical conditioning and retaining recorded audio are distinct mechanisms; see [reference/remix map](research/REFERENCE_REMIX_MAP.md).

**A 150-second development test is saved.** E20 supplied a second verse, bridge and returning chorus. The saved plan also supplied the requested instrumental intro/outro and differentiated section styles. ASR broadly recovered the lyric order. Musical development, diction and enjoyment are pending listening. It was selected to test structure, not declared the best song.

**No Hindi clarity winner or personal cloned-singing result is established.** E13's clarity prompt generated audio, but unreliable ASR prevents a diction verdict. E18 converted a 15-second song excerpt to built-in Roger and cost exactly 250 credits; pitch tracking on the mixed source failed and was rejected as evidence. The inspected personal library had no Instant or Professional clone results. Direct speech-clone selection was not exposed in the inspected Music routes. [Voice findings](research/VOICE_AND_LANGUAGE_FINDINGS.md) separate documented PVC limits, Music style controls, conversion and the correct VoiceStudio implementation.

## Most useful demonstrated prompting patterns

1. Put exact words in **Custom lyrics** and musical instructions in **Prompt**. Specify one variant and fixed duration, then inspect the saved plan and preserve the original.
2. Repeat the actual chorus words and name the intended verse/chorus development. This produced editable structure and approximate textual recurrence; a repeated tune is still unverified.
3. Choose the workflow by what must stay: fresh project for new music; Audio Reference for sound guidance; selected-section editing for retaining surrounding recording.
4. Keep a concise baseline and compare one change at a time. The longer arrangement prompt, clarity addition and baseline repeat are available for audition, with no causal quality ranking claimed.

Exact submitted prompts, counterexamples and untested suggestions: [prompt playbook](research/PROMPT_PLAYBOOK.md). Example full song: [E20 original MP3](audio/E20-full-song.mp3). Start comparisons with [audition guide](research/AUDITION_GUIDE.md).

## Evidence and limits

REA MCP 6.7.0 was connected and verified separately from supported native Edge access. **No REA browser/network capture was obtained:** no existing authorized CDP endpoint was found. The exported REA bundle has zero page-evidence records. Native UI observations, local measurements, public documentation and source inspection are labelled separately. Request payloads, job transport and backend algorithms remain unknown.

There is no listening input in this session. All melody, hook quality, fluent diction, emotional delivery, identity and seam scores remain pending. ASR was run offline without the lyric fixture as a prompt, and its hallucination spans are preserved and excluded. Ten Music outputs plus one conversion output, exact inputs/IDs, original files, hashes, metadata, ASR and credit evidence are saved here.

The official [Music guide](https://elevenlabs.io/docs/eleven-creative/products/music) distinguishes style-reference guidance from remixing. The [inpainting guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting) describes conditioning and retained chunks; those API paths were not invoked here. Current [pricing](https://elevenlabs.io/pricing) supplied the Voice Changer estimate, subsequently confirmed by the live 250-credit debit.

## Next research pass

First audition E01/E02/E12, then E13/E20, source versus E05, and E01/E04/E04B. Use verified listening findings to choose one word repair or replication. For personal singing identity, obtain an eligible own-voice target and a correctly sung isolated guide before another conversion test. For a REA page trace, supply an existing authorized loopback browser endpoint. Do not spend the remaining allowance on more first takes before these gaps are resolved.

Full [capability matrix](research/CAPABILITY_MATRIX.csv), [experiment ledger](experiment_log.csv), [final billing evidence](research/evidence/FINAL_BILLING.md), [workflow map](research/WORKFLOW_MAP.md), [REA findings](research/REA_FINDINGS.md), and [continuation checkpoint](research/NEXT_SESSION.md).
