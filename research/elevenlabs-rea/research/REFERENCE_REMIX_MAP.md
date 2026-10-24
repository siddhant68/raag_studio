# Reference and remix mechanisms

24 October 2026 IST. Operational and acoustic evidence are deliberately separate.

| Intent | Mechanism | What is preserved | Evidence here |
|---|---|---|---|
| Exact words, new music | Fresh project + Custom lyrics, no audio reference | Stored words/section labels | E01/E03 and repeatE12 generated. L1 retained; exact sung words/new melodic novelty await listening. |
| Sound/style guidance | Composer Audio Reference | Desired palette/mood/groove, not a guaranteed source slice or melody | E04 accepted0–30s E01 reference, influence1, sameP1/L1; generated new project. Audible influence unverified. |
| Stronger reinterpretation request | Same style-reference route with new6/8cinematic brief | Requested lyrics and chorus contour; actual contour retention unknown | E04B generated with separate saved project; exposed plan72BPM,6/8,piano/strings/handpercussion. A plan label “chorus contour kept clear” is not measured melody identity. |
| Musical conditioning | Documented generation chunk with conditioning_ref and strength | Model-guided continuity; regenerated audio | Public API documented, no authenticated request/capture or UI conditioning selector established. Unrun. |
| Retained recording with selected changes | Selected project section styles and regeneration | Surrounding audio should remain | E05 changed30–60sChorus. Interior retained windows correlate>.998 at0 ms lag; edited window~.335. Not sample-identical and seams not auditioned. |
| Voice conversion | Existing performance → separate Voice Changer target voice | Performance/timing target | E18 returns15sconverted audio; exact 250-credits. Mixed source and failed pitch tracking prevent singing-preservation conclusion. |

The [Music product guide](https://elevenlabs.io/docs/eleven-creative/products/music) describes Audio Reference as sound/style guidance rather than copying/remixing the source. The [inpainting guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting) distinguishes regenerated conditioning from stored audio chunks inserted unchanged. These are documented API semantics, not evidence that the web editor submitted those exact fields.

E04B deliberately requests more preservation than a style reference promises. Successful generation means the request was accepted; it does not prove a recognizable source-derived remix. Compare E01→E04B by listening separately for chorus contour, meter, arrangement, vocal identity and changed elements. E04→E04B changes musical direction while retaining source/words/model/duration, with random generation uncontrolled.

For beginners, choose the entry point by the intended preservation: retain words in Custom lyrics; point to sound with Audio Reference; retain portions of an existing recording through section editing. Do not promise personal singing identity from an audio-reference upload or a curated vocal-style name.

Preservation unknowns: no conditioning API test, no whole-track style conversion of retained source, no note-level control, no exact melodic-fidelity metric, no listener seam assessment. Reference source file/hash and requested changes are in experiments/E04 and E04B; E05 alignment is reproducible locally.
