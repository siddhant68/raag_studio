# Review tasks before implementation

The PRD is intentionally richer than the first build. Review it and record
decisions, then implement a working local slice. This is not a demand to expose
104 controls or integrate every researched model.

## Resolve these concrete gaps

1. **Planner access:** no app LLM credential/model endpoint was configured. A chat subscription does not supply API access. Implement a provider interface and visible configuration; any local rule-based fallback must be honestly labelled and cannot claim general lyric/composition reasoning.
2. **Full configuration contract:** `Creative_Plan.schema.json` covers the core plan/examples, not the complete 104-field catalogue. Turn chosen MVP controls into typed fields; add semantic validation and explicit defaults. Do not silently accept fields the compiler ignores.
3. **Locks and identifiers:** sample JSON pointers use array positions for illustration. Bind production locks to stable instrument/section/line IDs so reordering does not lock the wrong object. Keep source text and lyric hashes immutable.
4. **Inference versus control:** do not expose turbo CFG guidance as a strength slider; do not advertise a renderer task simply because a different checkpoint supports it. Resolve against the actual installed API/model.
5. **Choir modes:** distinguish instrumental, wordless voices and lexical lyrics. Do not set `instrumental=True` while requesting choir and then blame the output for ignoring it. Exact singer count stays approximate.
6. **Lyrics fit:** define exact/adapt/write/inspired policies. Exact text remains unchanged; duration/repetition conflicts need an explicit product resolution. Include line-level edit permissions and clear differences between display text and pronunciation hints.
7. **Editing scope:** version one can make a whole new take. Region repair is a separately tested pilot. A favourite and a config lock do not guarantee unchanged melody or singer in a new render.
8. **Stem capability:** native generated audio is stereo. Separation is estimated and may not isolate every requested instrument. Only usable isolated parts justify independent gain/pan/effects.
9. **Durable job state:** decide worker ownership, startup recovery, interrupted jobs, duplicate submissions and best-effort cancel. Persist requests before a heavy job. A browser disconnect must not create a second paid job.
10. **Resources and isolation:** use a single heavy worker initially, recheck shared video queues/memory, and keep new app dependencies inside this dedicated root. Record server ports/PIDs and stop only owned services.
11. **Prompt compilation:** 512-character local-caption budget, separate lyrics, explicit metadata, essential-versus-optional priorities. Reject/report overflow of essential intent; do not silently truncate lyrics. The best number of instructions has not been experimentally established.
12. **Language quality:** Hindi/English text drafting are launch priorities. Generation accepts more language codes, but per-language singing and pronunciation need evaluation. Do not advertise an untested global-quality ranking.
13. **Actual comparisons:** user verdicts are ground truth for preference. Define listening feedback separately from decode/clipping/ASR/tag checks. Do not optimize classifier scores as if they measured beauty.
14. **Infrastructure boundaries:** local personal app first. Cloud, multitenancy, publicly accessible downloads and distribution are separate scopes. No automatic external publishing.
15. **Reference truth:** recipe reuse, style reference, waveform preservation and score preservation are different. State which path the app actually executes.

## Suggested implementation order

1. Review/fix core schema, field provenance, deterministic validation and the capability registry.
2. Implement the simple UI and plan inspection with useful defaults and clear fallbacks.
3. Integrate an actual configured planner when available; keep unavailable capabilities explicit.
4. Implement durable storage and one real local rendering worker using fresh output folders.
5. Add playback/favourites/versioning/export and error recovery.
6. Check brief-only creation, exact lyrics, choir flag consistency, manual locks, duplicate jobs and output preservation.
7. Run one bounded new local smoke render if resources/native execution permit it; do not overwrite accepted references.
8. Document working commands and remaining gaps. Then expand advanced control/repair based on tested capability.

## Required distinction in the final implementation report

Separate: implemented and exercised; implemented but unexercised; mocked or
fallback behavior; proposed only; blocked by a specific missing resource. A
static front end and simulated progress are not a completed music generator.

The user's current request is to prepare this handoff. The next independent
agent should act on the review-and-implementation instruction when this prompt
is supplied as its task. No application implementation or new music render was
performed while constructing the pack.
