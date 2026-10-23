# Raag Studio: orchestration, user decisions and resume protocol

Written 2026-10-24 by the orchestrator session. Read this first if you are a resumed session.

## Roles

- **Orchestrator (you, a Claude session)**: preserves context. Does NOT write app code itself except trivial glue. Plans, dispatches, reviews, merges decisions, updates `STATUS.md`.
- **Dev sub-agents**: always spawned with the Agent tool, `model: "sonnet"` (user requirement: Sonnet only for development). One milestone (or one non-overlapping slice) per agent. Never two writers on the same files.
- **Review**: after each dev agent finishes, the orchestrator verifies by running the acceptance checks itself (tests, curl, file existence), not by trusting the agent's report.

## Decisions the user already made (2026-10-24, user asleep afterwards)

| Topic | Decision |
| --- | --- |
| Planner | Rule-based baseline now, behind a pluggable provider interface. Label it honestly as a baseline, never as an LLM producer. Provider config (env var names only) documented; nothing blocked on a key. |
| Unattended permissions | (1) Install deps ONLY inside this root (venv + node_modules here; never touch shared ACE/video envs). (2) Run real ACE-Step renders. (3) Download optional 5Hz LM weights is allowed. (4) `git init` and local commits in this root; NEVER push. |
| Render cap | About 12 real ACE renders overnight. Log every render in `STATUS.md` render ledger. Before each render check no other generation job is running (see SYSTEM_AND_RUNBOOK.md). One render at a time. |
| Resume | Keep Mac awake + app-level scheduled task `raag-studio-resume` restarts a fresh session periodically. |
| Not allowed | Paying for services, publishing, sending messages, training voices, editing projects outside this root, upgrading shared environments. |
| Prior user rules | Free-text brief is the only required input. Create runs without a plan-approval step. Beginner-friendly. No fictitious faders or locks. Keep `context_pack/examples` and `recipes` immutable. |

LM download: DECIDED SKIP (see context_pack/docs/IMPLEMENTATION_DECISIONS.md). Disk is tight and the plan keeps the LM off.

Render budget: counted per TAKE (cap ~12). Planned spend is in IMPLEMENTATION_DECISIONS.md (9 planned, 3 spare). Planner: only Basic (rules) is enabled; claude -p / API providers are built but OFF.

## Resume protocol (every resumed session follows this)

1. `cat STATUS.md`. Check `heartbeat_utc`. If it is less than 25 minutes old, another session is active: do nothing, exit with a one-line note.
2. Otherwise take the lock: set `heartbeat_utc` to now and `active_session: resumed`.
3. Read the "Next actions" list in `STATUS.md` and the matching milestone in `context_pack/docs/PRD_v2_MVP.md` (once it exists; before that, see Phase 0 below).
4. Dispatch Sonnet dev sub-agents for the next unblocked milestone(s). Brief each with: the milestone text, files owned, acceptance checks, constraints from this file, and the instruction to write a short report to `reports/<milestone>.md`.
5. Verify, update `STATUS.md` (done / in progress / blockers / render ledger / decisions changed), commit locally with the attribution line required by the session instructions.
6. Refresh the heartbeat at least every 15 minutes during long work.
7. When all milestones are done, set `state: COMPLETE` in `STATUS.md`, write the final morning summary to `MORNING_SUMMARY.md`, and delete/disable the scheduled task `raag-studio-resume`.

## Phases

- **Phase 0 (DONE 2026-10-24)**: critique of the PRD by a sub-agent -> `context_pack/docs/PRD_CRITIQUE.md` and `PRD_v2_MVP.md`. Orchestrator reviews, edits, and records accepted/rejected changes in `context_pack/docs/IMPLEMENTATION_DECISIONS.md`.
- **Phase 1+**: milestones M0..Mn from the reviewed `PRD_v2_MVP.md`. Source of truth for ordering is `STATUS.md`.

## Honesty rules (from AGENTS.md, repeated because they matter)

- Never call mocked generation a real render. Save plan, prompt, lyrics, checkpoint, seed, request, native output, master for every take.
- A test that passes is not a listener verdict. Human-listening items are labelled "needs user" and left pending.
- If blocked on something only the user can supply, write it in `STATUS.md` under "Needs user" and continue independent work.
