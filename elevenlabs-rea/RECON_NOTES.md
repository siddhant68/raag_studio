# Preparation evidence and source index

Prepared 24 October 2026, India time. These notes document reconnaissance for a future live investigation; they do not claim that ElevenLabs was explored through an authenticated browser.

## Account evidence

The user's screenshot `image(1).png` was resolved to the supplied file identity and read through extracted image text. It states Creator is the current plan, 121k monthly plan credits, 131,000 total and remaining credits, 0 used, and renewal on November 24. No account or billing settings were changed. A live balance must be checked before experimental spending.

## Local REA installation evidence

Verified cached package directory:

```text
/Users/sidhandsome/.npm/_npx/a1722018f28f9df2/node_modules/rea-agents
```

Its package metadata reports name `rea-agents`, version `6.7.0`, repository `git+https://github.com/morluto/rea.git`, and public launcher `scripts/rea.mjs`. This is a cached distribution, not a recovered complete source checkout or confirmed active MCP connection. A global `rea` executable was not found on the preparation shell's PATH.

Read these existing files rather than installing everything again:

- `skills/reverse-engineer-anything/SKILL.md` (skill version 42)
- `skills/reverse-engineer-anything/references/runtime-observation.md`
- `skills/reverse-engineer-anything/references/evidence-workflows.md`
- `skills/reverse-engineer-anything/references/connection-and-recovery.md`

All are relative to the cached package directory. The original cache may be cleaned later; discover an existing equivalent before treating this path as permanent.

Read-only diagnostic actually run:

```sh
/opt/homebrew/bin/node \
  /Users/sidhandsome/.npm/_npx/a1722018f28f9df2/node_modules/rea-agents/scripts/rea.mjs \
  doctor --client codex --json
```

Relevant result:

- Exit 1; Node 26.3.0 is healthy for this installed release.
- Codex registration at `/Users/sidhandsome/.codex/config.toml`: missing/config drift.
- Installed skill identity missing.
- Live REA server identity unknown; tools absent from this session's advertised inventory.
- Native engines listed as informational unavailable providers. They are not required for the website research and were not installed.

Do not run an unpinned latest package as a routine repair: its prerequisites and schemas can differ. If setup repair is needed, the installed guide provides the client-scoped dry-run and approval workflow. Reading a cached skill is not proof that the skill is installed for the active client.

## Search boundary and missing prior learnings

`/Users/sidhandsome/Documents/REA` exists but currently contains no visible files; a bounded search there found no Markdown/project files. No REA-specific prior learning document was recovered from selected Documents/Codex, local-video-generation or agent skill locations. The user says prior repo/learnings exist; retain that as unresolved, rather than claiming they never existed. A similarly named old cinematic `Codex/2026-09-12/rea` directory contains video/audio work and was not established as the REA framework checkout.

No user configuration was rewritten and no missing historical workspace was recreated. Do not overwrite recovered prior work if the next session locates it.

## Browser limitation

The preparation session loaded the Browser skill but had no associated browser-control tool available. Therefore no logged-in page, UI control, browser network observation, script trace, generation or audio audition was performed. Public documentation and the account screenshot are distinct evidence sources.

## Working REA lessons from the installed guide

- Route a website to browser/runtime evidence; native disassemblers are not a prerequisite.
- Reuse connected tools when present. Distinguish missing registration, stale identity, a missing PATH executable, missing engine and active-client reconnection problems.
- Read actual advertised schemas. Treat tool catalog availability and operation availability separately.
- Begin with one workflow/question, inspect small summaries, follow specific evidence gaps, and preserve IDs/coverage rather than repeatedly requesting full bundles.
- Passive observations do not mean the tool performed actions. Runtime visibility does not establish server implementation or whole-program execution.
- Keep observed facts, inference, documented behavior and unknowns separate. Preserve limitations and incomplete coverage.

These are extracted operating principles from the installed framework, not recovered user-authored historical lessons or a claim of successful analysis of ElevenLabs.

## Official source index

Read the current sources when needed; do not assume UI and API options match:

1. REA canonical repository: https://github.com/morluto/rea
2. REA official site/guides: https://rea.tools/
3. Music capability overview: https://elevenlabs.io/docs/overview/capabilities/music
4. Music UI workflows: https://elevenlabs.io/docs/eleven-creative/products/music
5. Prompting guide: https://elevenlabs.io/docs/overview/capabilities/music/best-practices
6. Composition plans: https://elevenlabs.io/docs/eleven-api/guides/how-to/music/composition-plans
7. Inpainting/conditioning: https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting
8. Compose API: https://elevenlabs.io/docs/api-reference/music/compose
9. Upload API: https://elevenlabs.io/docs/api-reference/music/upload
10. Music Terms: https://elevenlabs.io/music-terms

Documentation-backed hypotheses to verify live:

- The prompting guide discusses musical identity, production/delivery vocabulary, chronological arrangement instructions, supplied words and vocal timing. More detail is not invariably better. Test rather than copy those assertions into results.
- The UI guide describes lyric/section editing, reference use and regeneration. Inspect what is actually available on this account.
- The composition guide distinguishes v2/v2.5 chunk plans from the older v1 format. The selected model and visible UI behavior matter.
- The inpainting guide distinguishes retained audio chunks from newly generated/conditioned chunks; these are different preservation mechanisms.
- Audio Reference is documented as short style/sound guidance, not general-purpose copying or genre transformation. Stronger remix claims need their own successful tests.

No best prompt, successful remix, exact-lyric guarantee or Hindi-quality win has been established yet. The original prompts in `PROMPT_LAB.md` are proposed controlled experiments.

## Latest user direction

The user requested an increased cap for deep end-to-end music research and added unclear pronunciation, cloned voices and singing in one's chosen language as priorities. The handoff now proposes a 40,000-credit ceiling, bounded by one-third of the live starting balance. No credits were spent in preparation.

New voice research distinguishes ElevenLabs Professional Voice Cloning, Music Finetunes, and Voice Changer. See `VOICE_AND_PRONUNCIATION.md` for the exact current evidence and separate feasibility questions. Professional Voice Cloning's current product guide expressly excludes singing; that is not a finding that every possible conversion or music-conditioning route is impossible.
