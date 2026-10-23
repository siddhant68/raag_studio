# Complete music-project context

## Current objective

Siddhant wants an application for people with little music knowledge. A required
free-text brief should drive a complete editable configuration. Users may
optionally choose instruments, performances, voice/choir scale, lyrics policy,
language, mood, rhythm and musical development. The AI decides unspecified
details. An independent agent will review the proposed product and implement
it inside the `raag-studio` root.

The product was requested after listener-approved original music, especially
**Yamuna at Dawn**. This is a music-generation application project, not a request
to resume the unsuccessful famous-song remix as the main product.

## How we reached this point

1. Siddhant asked for a free Mac alternative to Logic Pro that agents could operate.
2. Sonic Pi and Earshot were installed and tested. `Delhi Afterglow` demonstrated coded instrumental generation/playback/recording, not a realistic singing model.
3. He requested a transformative mix of Attack on Titan's Ashes on the Fire and Game of Thrones' Rains of Castamere. Three substantially different attempts failed his musical brief.
4. Music workflow research downloaded 159 vendor `SKILL.md` files across eight repositories, plus Nous and Earshot guides. The guides supply procedures, not new trained music models or professional taste.
5. ACE-Step 1.5 turbo was installed locally, with the existing Apple MLX/MPS path. An original 2:32 Hindi romantic song, Thodi Der Aur, was received positively, with unclear pronunciation in places.
6. A Sonic Pi backing plus separately generated, separated Hindi vocal made parts clearer but sounded spoken/recited to the user. It was rejected as a replacement for the accepted song.
7. VoiceStudio was researched because the user asked about `debpalash/VoiceStudio`, not ACE Studio. No dependable Hindi melody-preserving singing repair route was established, and that app was not installed for the experiment.
8. A research sub-agent and a local inventory examined music generation, score-conditioned approaches, singing synthesis, managed APIs and actual skills. Findings are preserved in `research/`.
9. Daylight, an original ensemble with wordless chorus, was accepted as “very enjoyable.”
10. The next request asked for more expressive, Krishna-inspired bansuri. Moonlit Raas and Yamuna at Dawn were generated. A single bounded refinement of Yamuna reduced competing layers and yielded the delivered flute-focus take. The user then said “yamuna at dawn is such a melody man.”
11. That success prompted the application idea. A 12-page proposed PRD and 104-field catalogue were created. They are not implemented application code.

## Listening evidence

The authoritative mapping is `../examples/AUDIO_CATALOGUE.json` and its human
guide. There are three accepted examples, four rejected examples, one delivered
but unreviewed piece, and an instrumental component. These are taste labels
for the user's brief, not universal judgments about objective quality.

The accepted Yamuna recording is from **seed 24102633**, folder `flute_focus`,
not its earlier `native` take. Daylight is take 01 / seed 24102601. The accepted
Hindi song is take 01 / seed 22102611, not the hybrid, alternate or Romanized
experiment. Exact requests/results are bundled in `../recipes/`.

The initial user path called `sonic-pi-2026-10-22-04-35-25.wav` was our Sonic Pi
test, not Ashes. Correct remix source excerpts were later located and used.
Do not mistake filename assumptions for music provenance.

## What made the later work worth developing

Joint full-performance song/music generation produced the user's preferred
results. Extra tools, clipping checks, BPM estimates, new beats and skill files
did not salvage the rejected remixes. The Sonic Pi hybrid shows that clear
speech is not equivalent to melodic singing.

For the bansuri work, a focused lead role and less competing accompaniment
were a useful refinement. The acoustic hints improved and the user liked the
delivered melody. This is one successful case; it does not establish a universal
rule, an optimal prompt length, strict raga adherence or professional flute technique.

## Non-negotiable product intent

- The brief is required; everything else can be Auto.
- Keep beginner and advanced settings as views of one consistent plan.
- Selected instruments need roles, priority and musical relationships.
- Distinguish the repeated song chorus from background choir.
- Treat requested ensemble headcount and virtuosity as approximate creative targets.
- Exact lyrics preserve source wording, order and permitted repetition. Performed adherence is still a listening check.
- Hindi and English are initial writing priorities; singing/diction validation is separate from writing capability.
- Store rich intent but compile a compact request suitable for the engine.
- Preserve favourite audio. Recipe reuse does not guarantee identical melody/audio.
- Actual mix faders require usable tracks; prompt instructions are not independent mixing controls.
- Keep human acceptance separate from technical checks and fallible models.

## Research and implementation boundary

Agent Reach was used to search Joey Nato's public videos and retrieve captions
for YouSeeBIGGIRL/T:T and La Signora, alongside the user-provided Ashes transcript.
A concurrent Raiden caption attempt returned rate limiting; further requests
stopped. Full third-party transcripts are not redistributed in this pack.
The paraphrased production lessons and source links are in the PRD.

The earlier research considered Suno, Udio, Eleven Music, Stable Audio, YuE2,
HeartMuLa, LeVo/SongGeneration and singing editors. Documentation review is not
a listening benchmark or a completed integration. Recheck changing provider
capabilities and terms before implementation. No paid music API or planner
credential was supplied for a standalone app by this conversation.

## Stale statements that must not mislead the next agent

- `history/EARLY_SETUP_SUPERSEDED.md` says source music is missing and no remix exists. That described the early setup only; later attempts are in this pack.
- The older remix LEARNINGS/REVIEW may say acceptance is pending. The user's later verdict was rejection, “still bad.”
- The earlier Hindi/Daylight/Yamuna READMEs say human acceptance is pending. The current catalogue records the later user feedback and supersedes that status.
- A historical installation guide refers ambiguously to a separately downloaded music LM. The fresh checkpoint inventory contains only turbo DiT, VAE and Qwen embedding. The separate 5 Hz music LM is absent.
- Earlier reports about Earshot's presence in the ACE environment are historical. The fresh package inventory now resolves Earshot 0.3.0 there too; prefer the dedicated Earshot environment for the established analysis workflow.
- Historical notes about shell DNS/GPU visibility are environment-specific. A fresh authorized native-host probe reports MPS available. Probe the execution surface you actually use before making hardware claims.

Authority order: current user direction; this handoff's corrected context and
current inventory; current PRD as a proposal to review; actual request/result
receipts; historical notes. Original technical logs remain evidence of what
ran, but they never override a later explicit listener verdict.
