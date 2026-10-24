# Hands-off investigation: REA of ElevenLabs Music for lyrical songs

Prepared 24 October 2026, India time, for Siddhant Pathak.

## Mission

Apply **REA = Reverse Engineer Anything** to ElevenLabs Music through computer/browser use. Learn how its mature product turns a user's intention, lyrics and reference audio into a song and supports useful revisions. Investigate effective prompting through small controlled experiments. Produce evidence-backed findings and a reusable prompt playbook.

This is a research task. **Do not integrate with, modify, or rebuild Raag Studio yet.** Do not clone ElevenLabs' branding or product. The user wants to understand implementation patterns and creative workflows that improve results; access to proprietary model weights, training data or server-side algorithms is outside what this investigation can establish.

Working root:

```text
/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/elevenlabs-rea
```

Read this file, `RECON_NOTES.md`, `PROMPT_LAB.md`, `VOICE_AND_PRONUNCIATION.md`, and `experiment_log.csv`. Keep research outputs here. Act autonomously within the scope and operating budget below; finish useful unblocked work instead of repeatedly asking whether to continue.

## User priorities, in order

1. **Supplied lyrics -> completely new music** following the user's style, mood, vocal and arrangement instructions. Distinguish exact lyric preservation from permitted adaptation.
2. **Reference song -> a meaningful new interpretation or remix.** Establish which reference workflow transfers broad sound/style, which conditions musical continuity, and which actually preserves or changes existing audio.
3. **A brief -> a compelling original lyrical song.** Hindi romantic songs first, with memorable hooks, sung melody and clear words; English is a useful comparison.
4. **Targeted revision:** improve a chorus, one lyric or diction problem, vocal delivery, arrangement or ending while retaining the parts the user wants.
5. Discover prompt formulations and interaction patterns that make these workflows accessible to a beginner.
6. Deeply evaluate pronunciation and whether a person can sing in their own cloned voice and chosen language. Distinguish direct music generation, speech cloning, reference conditioning and conversion of an existing sung performance. Investigate the correct `debpalash/VoiceStudio` repository as a feasibility comparison, without building an integration now.

The user explicitly narrowed the task to lyrical songs and reference/remix workflows as the potential way to attract users, then requested deeper end-to-end capability research, a larger cap, and voice-cloning/multilingual-singing research. Inspect speech or voice-conversion controls only when they answer that singing question. Inspect music fine-tuning eligibility and behavior claims if relevant, but do not launch training or spend the budget on unrelated voice agents, video or instrumental-only showcases.

## Important context

Siddhant owns a Creator subscription. Extracted text from his uploaded screenshot showed **131,000 total and remaining credits**, **0 used**, Creator as the current plan, and renewal on November 24. This is screenshot evidence, not live account verification. Recheck the selected workspace and balance in the browser before spending.

Earlier original Hindi song `Thodi Der Aur` had pleasing melody and emotion but imperfect diction. A later clearer-voice hybrid failed because it sounded like speech over music. Therefore **melodic singing, a memorable recurring hook, natural phrasing, and intelligible Hindi must be judged separately**. Technical audio validity does not establish any of them.

An optional read-only reference is:

```text
/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation/raag-studio/context_pack/examples/accepted/Thodi_Der_Aur.mp3
```

Do not overwrite or automatically upload that accepted file. Prefer a fresh original song generated in this ElevenLabs investigation as the reference for controlled remix tests. Do not download commercial songs or copy famous lyrics to manufacture a reference.

## What preparation actually established

- A cached **rea-agents 6.7.0** installation from `morluto/rea` exists; exact paths and diagnostics are in `RECON_NOTES.md`.
- The named local `/Users/sidhandsome/Documents/REA` folder currently has no visible contents. Previous user-specific REA learnings were not recovered in the bounded search. Do not claim the user's prior work never existed or that the cache is their complete repository.
- Read-only REA doctor found missing Codex registration and missing installed skill identity. REA tools were not advertised to the preparation session.
- The preparation session had no supported browser-control tool, so it **did not explore the authenticated ElevenLabs UI, perform REA page captures, render audio, spend credits or verify prompt performance**.
- Official public documentation was read to choose useful hypotheses. Those claims are not substitutes for account-specific observation.

Keep these distinctions intact. Your first useful contribution is live observation, not repeating documentation and calling it a completed REA investigation.

## Bootstrap: browser and REA without a setup spiral

1. Read applicable workspace instructions and the browser/computer-use skill available in your session. Discover the actual current tool inventory. Use the supported connected browser and existing signed-in account; do not assume another session's handles or tool names exist.
2. Select the user's ElevenLabs Music tab/workspace by observed URL/title. Verify account plan, available model, initial credits and any visible generation-cost estimate. Preserve unsaved work; create a fresh research project if supported. Do not change billing or global account preferences.
3. Read the installed REA skill and relevant references at the paths in `RECON_NOTES.md`. Prefer an existing connected REA server; tool availability in the active session is what matters.
4. If REA is absent, diagnose once. The cached public launcher can run `doctor --client <actual-client> --json` without acquiring a newer package. Do not assume Codex if this is a Claude session.
5. If registration needs repair, prepare the **client-scoped dry-run** and show its exact paths/backups/changes. The REA skill explicitly requires approval before setup writes configuration or installs Hopper. Follow that instruction if the scope is not already authorized in your session. Do not silently edit global configuration, broaden permissions, install a native engine, or loop through setup. Keep this one-time setup issue separate from ordinary research actions.
6. After an approved registration repair, reconnect/restart as required and verify the tools actually appear. A healthy CLI does not prove the current agent is connected.
7. Browser actions must follow the active browser skill's permitted control surface. Use REA for supported passive/static evidence without substituting an unauthorized browser driver. When policy and installed instructions differ, session instructions govern.

If login needs the user's interaction, provide the exact selected browser/page and a single clear request. Continue public-source review, hypothesis planning, template preparation and already-authorized local analysis while waiting. If browser access is genuinely unavailable, record that blocker and finish supported work; do not pretend public docs are live UI exploration.

Web research does not need Hopper/Ghidra/IDA. Do not install those packages because doctor lists them as informational missing providers.

## Hands-off operating budget — expanded after the user's latest direction

The user explicitly said the research cap can increase and asked for a deep end-to-end study. Use **40,000 included credits or one-third of the verified starting balance, whichever is smaller** as this handoff's proposed operating ceiling. At the screenshot's 131,000 balance that leaves at least 91,000. The 40,000 figure is the preparing agent's concrete limit implementing that direction, not a claim that the user supplied this exact number. A newer user instruction overrides it.

- Spend existing included balance only. Do not purchase credits, enable overage, upgrade, start new training or subscribe to anything else. Do not publish outputs or voice models.
- Record starting balance, each cost estimate and actual balance change. Uploads, multiple variants and edits may consume credits too. UI credits and API dollars are separate meters; do not convert blindly.
- Start with one variant and 60–90 seconds per condition. Include one 120–180 second lyrical-song development test after a promising approach emerges; avoid judging full-song development only from short snippets.
- Prioritize the core experiments in `PROMPT_LAB.md`; all proposed tests are not mandatory paid runs.
- Inspect a cost estimate before each credit-consuming action. If cost is unknown or the action could exceed the remaining ceiling, perform only free inspection and mark the test unrun.
- Suggested allocation ceilings: 8,000 credits for initial songwriting/prompt comparisons; 12,000 for lyrics-to-new-music and reference/remix behavior; 12,000 for diction, language, voice-identity feasibility and section repair; 8,000 for replication and a developed final song. These are flexible within the overall ceiling, not extra budgets.
- Reserve budget for targeted editing and replication. Save a checkpoint at 20,000 credits, summarize findings, then continue useful planned work without another approval when still within scope and cap. Do not spend everything on unrelated first takes or spend remaining credits simply because they exist.
- On an ambiguous submit/timeout, inspect generation history before retrying. Never double-submit just because the UI is slow.

Proceed without per-click confirmations within those bounds. Genuine login, new payment, setup-approval or out-of-scope requirements are exceptions; identify their source precisely.

## Research method

### Phase A: map the lyrical-song workflows before paying for experiments

Use computer interaction to inspect the actual controls, defaults, help, validation and available actions. Record a concise feature map with URLs and time. Study:

- Prompt-only creation and auto-written lyrics.
- Supplied lyrics: dedicated input versus text embedded in the brief; exact-words controls; section labels; instructions that may accidentally be sung.
- Structure and timing: intro, verses, prechorus, chorus, bridge, instrumental gaps and ending.
- Vocal direction, language, duet/harmonies and timing of vocal entrances.
- Reference import and supported reference purposes; style guidance versus reuse of an existing recording.
- Follow-up edits, section regeneration, alternative versions, extension and undo/lineage.
- Multilingual lyric handling, pronunciation aids, custom-voice eligibility, vocal isolation/stem export, and which voice controls belong to Music versus speech tools.
- Cost estimates, queue/progress/failure states, retained inputs, downloads and history.

Do not infer model internals from a polished UI. Separate which transformations are visibly client-side, which are sent to the service, and which remain unknown.

### Phase B: trace one complete path with REA evidence

Question: **How does a user-entered lyrical-song instruction become a stored song and then a targeted revision?**

Start from the actual supported REA browser discovery/passive observation tools. Inspect their current schemas rather than copying guessed arguments from a guide. Reuse an already authorized browser endpoint if one is available; do not expose a browser-debugging port to the network or restart the user's browser behind their back.

Capture only the selected origin/workflow. Candidate trace:

```text
Brief + lyric input
  -> visible structure/style controls
  -> submitted request or observable state change
  -> asynchronous generation job
  -> playable asset + saved input/version
  -> section edit + new asset/version
```

Use actual observed field names in the final trace. If request payloads or initiating code are not exposed by supported tooling, leave them unknown. A discovered endpoint string is not proof it was called; an observed request is not proof of the server's composition algorithm.

If allowed and useful, analyze a narrowly selected client-delivered script or a sanitized saved capture through REA. Preserve Evidence IDs, source digests, coverage, truncation and limitations. Work summary-first; do not download the entire website or dump huge bundles into context. Preserve only relevant sanitized metadata; no cookies, credentials, authorization headers, personal messages or unrelated workspace content in artifacts. Do not replay private endpoints or bypass controls.

Label ordinary browser observations as browser observations. Label results as REA-backed only when actual REA evidence exists. Keep documented, observed, inferred, experimentally tested and unknown claims distinguishable.

### Phase C: prompting and reference experiments

Run the highest-value experiments from `PROMPT_LAB.md` inside the cost ceiling. Keep lyric text, model, duration, voice direction and other settings fixed when testing one prompt change. Capture any automatically rewritten brief or composition plan if the product exposes it.

Do not compare two completely different songs and attribute their quality difference to one word. Generation is stochastic; one promising pair is an exploratory result, not a universal best practice. Repeat one useful contrast if affordable.

The most valuable questions are:

1. Can a user provide exact Hindi words and reliably get a melodious song rather than recitation?
2. Does explicit section/hook direction improve chorus recognition and emotional development?
3. Can the same lyrics receive a clearly different melody/arrangement without reusing the first song?
4. What does a short audio reference actually influence? Which instructions conflict with it?
5. Can a controlled reinterpretation retain specified musical anchors while changing selected ones?
6. Can a chorus or lyric correction be localized, with the retained audio demonstrably preserved?
7. Does Music actually accept an existing cloned voice, or is a separate conversion/conditioning workflow needed? What evidence supports the answer on this model/account?
8. Can a reference voice be retained across Hindi/English singing while pitch, rhythm and lyric fidelity remain acceptable? Do pronunciation improvements preserve musicality?

Use user-owned, permissioned, or newly generated references. If a platform rejects a reference, record the limitation and continue with a permitted reference; do not disguise or perturb it to evade screening. No upload of accepted local historical masters is required for this task.

### Phase D: evaluate and write reusable findings

For each generated artifact, retain the exact prompt, supplied lyrics, exposed structure/styles, model, duration, asset/version IDs, parent/reference relationship, cost and output path or stable project location. Save original outputs before audition normalization or analysis.

Evaluate separately:

- Sung melody versus spoken/recited delivery.
- Hook/chorus recurrence and memorability.
- Exact lyric coverage, additions/omissions and Hindi naturalness/diction.
- Phrase breathing, syllable crowding and timing.
- Vocal character and emotional delivery.
- Arrangement development and lyric/instrument interaction.
- Reference fidelity on the specifically requested attributes.
- Degree of novelty on the attributes explicitly asked to change.
- Edit locality, audible seams and unintended changes.

Reference fidelity and originality are distinct scores: a completely new tune and a recognizable reinterpretation have different goals. Do not penalize a new-composition test for correctly changing the melody.

If your environment genuinely supports listening, report that capability and your actual observations. If not, provide timestamps, lyric/ASR discrepancies and concise audition questions, leave taste scores pending, and do not claim to have heard the songs. ASR and broad acoustic classifiers support evidence; they do not establish melody quality, singer identity, perfect diction or human enjoyment.

### Phase E: answer the end-to-end capability question

Produce a capability matrix covering original lyric writing, exact-words composition, new melody for existing words, reference-guided new composition, reinterpretation/conditioning, retained-audio edits, extension, pronunciation repair, voice identity, multilingual singing, export/stems, versions and billing/recovery. For every row report the tested entry point, required inputs/entitlement, what's preserved, what changes, known limitations, and evidence status. Mark public-doc claims and unrun features explicitly. Completeness means every requested question has a supported status; it does not mean every marketing feature must receive an expensive generation.

## Deliverables

Create under this research root:

1. `research/WORKFLOW_MAP.md`: actual UI flows, settings, defaults, limits, and observation dates.
2. `research/REA_FINDINGS.md`: evidence-linked behavior trace, relevant client-side findings, supported conclusions, unknowns and scope limits.
3. `research/PROMPT_PLAYBOOK.md`: tested prompt patterns by use case, exact successful/unsuccessful examples, conditions and counterexamples. Mark untested suggestions explicitly.
4. `research/REFERENCE_REMIX_MAP.md`: distinguish style reference, conditioning, retained-audio edits, new music for unchanged words, and true source-derived reinterpretation; record availability on this account and observed limitations.
5. Updated `experiment_log.csv`, plus per-experiment `experiments/E##/` folders containing inputs, results and notes. Keep generated audio in `audio/` if authorized downloads are available.
6. `research/LEARNINGS.md`: concise reusable REA lessons, tool/version identity, failed approaches and recovery, and avoidable credit waste.
7. `research/NEXT_SESSION.md`: completed checklist, remaining budget, current browser/project state, unresolved tests and exact continuation point.
8. `SUMMARY.md`: direct answer to what worked for lyrical songs, references/remixes and prompting; total spend; listening limits; top next experiments.
9. `research/VOICE_AND_LANGUAGE_FINDINGS.md`: direct singing-clone versus conversion feasibility, Hindi diction experiments, correct VoiceStudio repo identity, and remaining input/verification requirements.
10. `research/CAPABILITY_MATRIX.csv`: end-to-end feature and preservation matrix, with evidence and confidence for each requested capability.

A missing feature should be marked unavailable-on-this-account only after checking the relevant observed route; a missing button on one page is a bounded observation. Do not present unrun experiments as failed or successful.

No Raag Studio code, integration PRD, adapter, UI redesign, or new model installation is a deliverable in this phase. Brief general implications can be recorded for later; integration decisions are deferred by the user.

## Finish condition

End with a compact evidence-backed summary, the best demonstrated prompt patterns, example outputs where permitted, exact credit spend, remaining uncertainties and a recommendation for the next research pass. If a prerequisite blocks live research, finish the useful preparation and name the single concrete blocker instead of repeatedly retrying or claiming a completed investigation.
