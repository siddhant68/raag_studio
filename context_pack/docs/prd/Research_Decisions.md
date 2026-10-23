# Research decisions

Checked 24 October 2026. This is a primary-source feature review, not a logged-in trial or an audio-quality benchmark. Source identifiers and full links are in the PRD.

## Existing applications and what to derive

| Product | Documented pattern | Decision for our product |
| --- | --- | --- |
| Suno Studio 2.0 | Conversational production, alternate takes, MIDI and real track effects/automation | Do not claim natural-language production is new. Borrow clear editing scope and version comparison; leave a full DAW to a later stage |
| SOUNDRAW | Beginner-friendly instrument/intensity/length adjustment and section editing | Offer compact controls with understandable labels and a richer optional view |
| Stable Audio | Full-mix and experimental agent multitrack workflows, mixing and track/section regeneration | Separate a new performance from a track edit; real mixing operations must not pretend to be generation |
| Eleven Music | Structured section plans and inpainting references | Use a neutral plan and engine adapters; exact section timing/audio preservation depend on the adapter |
| AIVA | Audio/MIDI influence, editable generated compositions | Allow a future score route when note control matters; do not infer vocal-language quality from composition features |
| Udio | Timeline sections and take comparisons; current notice disables downloads | Use its UX as research, not a promised local-export backend |
| ACE-Step local interface | Natural-language captions, lyrics, metadata and checkpoint-dependent tasks | Build on the proven local route; adapt controls to the installed checkpoint rather than exposing every upstream feature |

These patterns make a useful personal application plausible. They do not prove a defensible commercial market gap. A commercial version would need user interviews and a direct comparison of onboarding, accepted-result rate, Indian-instrument control, total cost and edit preservation.

## Joey Nato exploration

Agent Reach was fetched from GitHub at `beabda7486e9a666360b18cdb5c0e759c2c4d20f` and installed in `tools/agent-reach-venv`, independently of the music runtime. A small launcher scopes its private state to the research folder. No global skill was registered and no browser login/session was used.

Public YouTube search found the supplied Ashes video and related material. Full English caption text was obtained for **YouSeeBIGGIRL/T:T** and **La Signora Battle Theme**. We analyzed those plus the user-supplied Ashes transcript. A concurrently launched Raiden caption attempt returned HTTP 429 / `RATE_LIMITED`; no retries or alternate-backend attempts followed. The separate successful Signora request had already been launched before that response was inspected.

The additional material reinforces three product decisions: foreground/background roles should be explicit; change over time matters more than an instrument checklist; and rhythmic feel, note activity and BPM must be separate. Both videos discuss orchestral and electronic combinations, and contrast between instrumental/vocal layers. The Signora captions are particularly useful for positional detail and changes in groove.

Captions are not score analysis. Some instrument and voice labels are uncertain or mistranscribed. Do not reproduce those errors as technical definitions. The PRD paraphrases relevant observations and links the videos; full retrieved transcripts are not included in the delivery bundle.

## How much detail to expose

The control catalogue contains 104 proposed fields. This is a product vocabulary, not a recommendation to send 104 instructions to a model. Each field has a UI purpose, a default, a release stage and an execution classification. Only the short brief is universally required.

Store the rich plan, compile a small set of priorities for the chosen model, and retain omitted optional details for later editing. This is a proposed design policy to test. Avoid asserting an experimentally established optimum prompt length, universal limit on instruments, or numerical adherence confidence.

## Local evidence retained

Yamuna at Dawn is now a listener-approved melodic anchor, following approval of Daylight. Earlier poor remixes and rejected spoken-like Hindi replacement establish that clearer audio, more tools and more processing do not automatically make better music. Accepted recordings should remain immutable throughout future experiments.

The current engine has not validated exact ensemble counts, professional instrument technique, perfect Hindi pronunciation, native multitrack mixing, strict raga adherence or note-for-note preservation. No new render was run for this specification.
