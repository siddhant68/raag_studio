# Implementation decisions (orchestrator review of PRD_CRITIQUE.md / PRD_v2_MVP.md)

24 Oct 2026. Reviewer: orchestrator session. Source reports were written by a sub-agent; the orchestrator read `PRD_v2_MVP.md` in full and the critique's outline and top findings. The critique's per-control appendix was not re-audited line by line.

## Accepted

- `PRD_v2_MVP.md` replaces the 104-control PRD as the working spec (25 controls, 9 visible first). The old PRD stays as history.
- Stack: FastAPI + SQLite (WAL) + filesystem store + no-build static frontend; API venv at `app/.venv` (Python 3.12); engine worker is a subprocess using the shared ACE python read-only. Never import torch in the API process.
- Default 3 takes per round; human picks; no auto-ranking; machine checks are breakage-only.
- The compiler is deterministic code with a documented slot grammar and drop order; the planner (LLM or rules) only fills a validated plan card.
- "Refine" = new takes from a patched plan, never edits. Cover/repaint/retake/flow-edit stay experiments (M6), not offered until proven.
- Capability registry (`capabilities.json`) is the single source for UI honesty labels; tests assert coverage.
- Hindi labelled "experimental"; English sung "untested". R4 (Moonlit) hidden until the user rates it.
- Famous-song / "remix X" requests are declined with an offer of an original piece in that mood; artist/song names stripped from the caption.

## Changed by the orchestrator

1. **Planner**: the user chose "rule-based now, pluggable later". So Basic (rules) is the only provider enabled. The `claude -p` and Anthropic-API providers are implemented behind the interface (M4) but OFF by default, require an explicit Settings toggle, and are never enabled by an agent. `PRD_v2_MVP.md` section 13's "pull forward M4" suggestion is NOT adopted. The critique flags that automated use of a subscription login may conflict with terms; leave it for the user.
2. **Render budget** (user cap: about 12 real renders). Counted per take, not per command. Planned spend:
   - M0: one 3-take run with the yamuna request (serves AT-M0-03/04/05, run under the offline env) = 3
   - M0-06 length scaling: 60 s and 240 s only (the 168 s point is already known from the 3-take run) = 2
   - M2-04 real create with takes=3 = 3
   - M3 end-to-end UI render with takes=1 = 1
   - Total 9; 3 spare for one retry of a failed run. Anything beyond needs a ledger entry justifying it.
   - M6 experiments (E1-E5) need blind human ratings: build the harness only, run no GPU arms overnight.
3. **5Hz LM download: skipped.** The user allowed it, but the plan keeps `thinking=False` (LM off), disk has about 25 GiB free, and nothing in the plan needs the LM. Revisit only if the user asks.
4. **Open question 7 (storage)**: prune is a manual, confirmed action only; no automatic deletion. Native audio stored as FLAC if M0 verifies the engine supports it, else WAV.
5. **Receipts** record requested AND effective parameters (turbo forces guidance 1.0; historical receipts say 7.0).
6. **Version control**: `git init` in the project root; `.gitignore` already exists; ignore `runs/`, `data/*.db`, `app/.venv`. Never push.

## Open questions deferred to the user (recorded in STATUS.md "Needs user")

1. Planner: ok to enable `claude -p` or supply an API key? (default: stay Basic)
2. Will you give one-tap love/fine/no ratings? (built either way)
3. Moonlit Raas verdict (decides R4)
4. Interest in music beyond slow/tender (fast, dark, electronic, cinematic needs listening sessions per style)
5. Personal use only? (licence terms of model weights/outputs unresolved)
6. Prune after N days: acceptable? (default: manual only)

## Process guarantees

- Tests labelled [H] (human) are never signed off by an agent; they stay "pending user" in STATUS.md.
- GPU tests ([M-GPU]) must run from a native shell; if MPS is unavailable in the agent's sandbox, record the blocker and do not fall back to CPU.
