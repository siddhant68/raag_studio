# Independent agent handoff: review and implement Raag Studio

You are taking over a real local AI-music project for **Siddhant Pathak**.
Your task is to understand the prior experiments and user feedback, critically
review the proposed product, and implement a usable local music application.
Do not stop at a generic architecture discussion or a visual mockup.

## Workspace and authority

The dedicated project root on the current Mac is:

`/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio`

Keep all new implementation, app dependencies, data and generation outputs
inside this folder. If you received a ZIP on another machine, use its extracted
`raag-studio` folder as the root and reconfigure external runtime paths.
Read `AGENTS.md`. Existing music/video tools and approved source projects are
shared resources outside this root: reuse them read-only and do not upgrade or
rearrange them as a routine part of building the app.

The user wants initiative and dislikes unnecessary confirmation loops. Resolve
ordinary implementation choices yourself, document assumptions, review the
specification, then build. Ask only for a genuine unresolved requirement or
credential; continue independent work while a missing provider is unresolved.
Do not turn missing planner credentials into fake claims of AI generation.

## Read these before implementing

1. `context_pack/docs/PROJECT_CONTEXT.md` for the corrected history.
2. `context_pack/examples/AUDIO_GUIDE.md`, and listen to the actual files if your environment supports it.
3. `context_pack/docs/prd/Music_Studio_PRD.md`, its PDF, `Control_Catalogue.csv`, and `Research_Decisions.md`.
4. `context_pack/docs/SYSTEM_AND_RUNBOOK.md` and current `inventory/SYSTEM_INVENTORY.json`.
5. `context_pack/docs/IMPLEMENTATION_REVIEW.md` and `context_pack/recipes/`.
6. Relevant files under `context_pack/docs/research/` and selected third-party guides. Do not execute every vendor setup.

Run `python3 scripts/verify_context.py` first. The pack contains specifications,
audio, receipts and research, not a completed frontend/backend. `app/README.md`
is only a proposed entry point.

## What the user wants

Siddhant describes himself as a beginner in music. He can express a feeling,
instrument, story or analogy but does not know producer vocabulary. He wants
an app that behaves like a knowledgeable producer and makes coherent decisions.

The **free-text requirements box is the main and only universally required
input**. From it, populate the entire editable configuration. Other fields
should remain Auto unless specified. Do not force a genre/BPM/key questionnaire.

Optional controls should cover:

- Instruments, their roles, priority, tone, register and performance style.
- Background voices/choir: none, solo, duet, small group, chamber, large/massed choir; approximate headcount and how voices relate to instruments.
- Instrument-only, wordless voices, sung lyrics and explicitly spoken/rap modes.
- Lyrics: write original lyrics, use the user's text exactly, adapt allowed parts, or use broad inspiration without copying/paraphrasing a famous song.
- Language, mood, rhythm/groove, melodic character, section development and endings.
- Beginner explanations plus optional producer detail; avoid 104 visible controls on first load.
- A player, favourites, versions, downloads, and text requests to refine a take.

The plan should explain its defaults and distinguish user choices from AI
suggestions. The user can ignore advanced controls. A Create action should
interpret and generate without requiring an extra plan approval step; Plan
only remains available for inspection.

## Prior work and what actually succeeded

**Accepted anchors:**

1. `context_pack/examples/accepted/Yamuna_at_Dawn.mp3`: the strongest current instrumental anchor. User: “yamuna at dawn is such a melody man.” This is the refined `flute_focus` take, **seed 24102633**, 168 seconds, 82 BPM/D-major request, local ACE-Step turbo. The selected prompt prioritizes exposed bansuri, gentle tabla, tanpura and sparse santoor. Do not use the earlier larger-ensemble native take as the accepted recipe.
2. `.../accepted/Daylight.mp3`: 132 seconds, selected take 01, **seed 24102601**, 88 BPM/D-major request. Multi-instrument arrangement with wordless vocal structure. User: “very enjoyable.”
3. `.../accepted/Thodi_Der_Aur.mp3`: original 152-second Hindi romantic song, take 01, **seed 22102611**, 76 BPM/D-major request. User initially said “amazing” and later described this earlier version as really good. Hindi pronunciation was unclear in places; that issue remains unresolved.

**Rejected examples:**

- `rejected/01_Concatenation_Feedback.mp3`: first Ashes/Castamere mix felt concatenated.
- `rejected/02_Random_Mix_Feedback.mp3`: chopped/beat-based version felt random.
- `rejected/03_Model_Remix_Still_Rejected.mp3`: later source-preserving/orchestral model workflow was still rejected.
- `rejected/04_Sonic_Pi_Hybrid_Recitation_Feedback.mp3`: actual Sonic Pi backing plus separately generated and separated Hindi vocal. User found music and voice clearer, but the lyric sounded read rather than sung, with no melody. Do not develop it as the preferred Hindi baseline.

`unreviewed/Moonlit_Raas.mp3` has no explicit listener verdict. The standalone
Sonic Pi backing is a component, not an independently accepted/rejected song.
Read the audio catalogue; do not transfer approval between versions.

No clipping, favourable tags and a good loudness level did not make the rejected
music good. Earshot cannot certify taste, language, sung-word accuracy or
virtuosity. If you cannot actually listen, state that limitation and use the
preserved user feedback; do not claim listening based on a meter/classifier.

## Current working setup

The machine is an Apple M5 Pro MacBook Pro with 48 GB unified memory. The
handoff's native-host probe reports MPS available. A restricted execution tool
can expose different GPU access; that does not mean the Mac has no GPU.

The installed working renderer is **ACE-Step 1.5 turbo**, through Python with
native MLX/MPS. Core weights: turbo DiT, VAE and Qwen3 embedding. The optional
5 Hz music LM is **not installed**. The embedding model is not that LM.
Existing accepted pieces used explicit metadata, eight steps and LM off.

Other local tools: Sonic Pi 5.0.0; Earshot 0.3.0; FFmpeg/FFprobe; Rubber Band
CLI; MLX Whisper small; torchaudio HDemucs. Agent Reach is installed in a
separate research environment. Exact current paths/versions are in the runbook
and inventory. Environments have different package versions; do not mix them.

Sonic Pi produced a real editable instrumental in the rejected hybrid. It was
not used to render Daylight or the accepted Yamuna piece. Earshot supplies
limited acoustic/technical evidence. Whisper is a fallible singing transcription
aid. HDemucs separates estimated sources; it does not repair consonants.

VoiceStudio (`debpalash/VoiceStudio`) was researched, not installed for this
work. ACE Studio is a different product. Ableton/REAPER/Mixxx/DJ integrations
were researched, not validated here. Do not silently install them all.

The pack includes the existing **159 vendor skill files across eight snapshots**
and the Nous/Earshot guides. They are downloaded procedures, not additional
music models or automatically active integrations. Useful starting material:
melody, orchestration, arrangement, lyric intent and exact engine docs. Review
language assumptions; English pronunciation advice is not a Hindi phoneme model.

## The proposed plan and its technical limits

The PRD's working name is **Raag Studio**. It is a proposal to review, not a
finished contract that must be followed blindly. It contains a 104-field
vocabulary and staged priorities, not 104 simultaneous prompt instructions.

Keep a rich internal plan, then compile a compact, prioritized request for the
selected engine. The current local wrapper budget is 512 caption characters;
keep authoritative lyrics separate. Preserve essential choices or report an
unsupported/over-budget requirement instead of silently discarding it.

Separate:

1. Actual audio operations: trim, export, whole-mix fades/gain.
2. Engine inputs: seed, checkpoint, duration/language metadata.
3. Soft creative direction: bansuri, legato, ornate runs, large choir.
4. Operations needing score/tracks: exact notes, independent instrument levels, exact doubling.
5. Unverified targets: perfect Hindi diction, exact 100-person choir, unchanged singer/melody during generated repair.

Do not expose a real flute-volume fader when only a stereo mix exists. Do not
claim a configuration lock freezes the waveform. Turbo overrides CFG guidance;
"higher guidance" is not a meaningful obedience control on this checkpoint.
Base-only layer/extract tasks are not automatically available from turbo weights.

Preserve exact lyric source text and permitted repetition. Show proposed text
changes. Do not rewrite ASR output to match intended lyrics and use that as
evidence of correct pronunciation. Writing quality, accepted language codes
and evaluated singing quality are separate statuses. Initial writing priorities
are Hindi and English; broader singing support needs evaluation.

Joey Nato research informs producer choices such as instrument entrances,
register, legato/pizzicato, motif returns, choir relationships and dynamics.
Full extra caption text was obtained through Agent Reach for YouSeeBIGGIRL
and La Signora. It was not score analysis or audio listening. A rate-limited
caption request was stopped. Paraphrases/links are in the PRD.

## Review first, then implement

Write a concise review in `context_pack/docs/IMPLEMENTATION_DECISIONS.md` or a
new app design document. Resolve the concrete gaps listed in
`IMPLEMENTATION_REVIEW.md`. Then proceed with a functional local MVP:

1. Brief-only creation and optional Auto controls, with a clear responsive interface.
2. Structured plan, provenance, stable identifiers, locks and conflict handling.
3. Instruments, voices/choir and lyric policies that compile to valid local requests.
4. An explicit planner interface. A chat subscription is not app API access. Use configured credentials/model if available; otherwise implement a clearly identified baseline/rule-based mode and provider configuration, without pretending it is a general LLM producer. Continue independent UI/engine work.
5. A durable single-worker queue for the shared Mac, idempotency, progress, restart behavior and best-effort cancellation.
6. Real ACE generation into a fresh `runs/` folder, not mocked success.
7. Player, immutable versions/favourites, MP3/WAV export and useful failure states.
8. Meaningful checks for exact lyrics, plan compilation, queue duplication, file output and preservation. Do not compare regenerated audio byte-for-byte across runtimes.
9. End-to-end validation of at least one small permitted local render after preflight, if native execution/resources allow it. Record the exact request and output. If blocked, finish other implementation and report the specific blocker without claiming success.
10. Clear start/stop instructions and implementation status in the project README.

Prefer a small functional slice before adding cloud adapters, waveform editing,
MIDI, hundreds of technique options, training or a complete DAW. React/TypeScript,
FastAPI, SQLite and a filesystem asset store are proposed, not mandatory if an
equally practical approach fits the environment.

Do not pay for services, publish externally, send messages, train voices or
alter unrelated projects as a routine step. Local reversible implementation
and ordinary fixes are within the requested work. Stop only services you own.
Recheck resource availability; the inventory's empty queue is a point-in-time
observation, not a permanent reservation.

## Finish with evidence

Provide the implemented app path/URL and run commands, what actually works,
validation performed, the exact generated example if any, remaining limitations,
and decisions that changed the PRD. Keep user acceptance separate from tests.
Do not report this context bundle or a static UI as a completed music application.
