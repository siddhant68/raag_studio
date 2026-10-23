# app/engine

`run_takes.py` renders one ACE-Step 1.5 turbo request as N serial takes in one
process (model loaded once). It reproduces the call path of the accepted
renders (`context_pack/reference_source/*/generate_*.py`, `scripts/render_local.py`):
`AceStepHandler.initialize_service(device='mps', ...)` then
`generate_music(handler, LLMHandler(), GenerationParams, GenerationConfig(batch_size=1, seeds=[seed]))`.

- Contract, events, exit codes: `REQUEST_CONTRACT.md`
- Measurements: `context_pack/docs/ENGINE_MEASUREMENTS.md`
- Pre-flight gate: `scripts/preflight.py`

Run (native shell, MPS required; check the :8388 video queue is idle first):

```sh
python3 scripts/preflight.py
ACE_PYTHON=../tools/acestep-venv/bin/python
$ACE_PYTHON app/engine/run_takes.py REQUEST.json runs/some_dir.partial --dry-run   # validate only, no torch
$ACE_PYTHON app/engine/run_takes.py REQUEST.json runs/some_dir.partial             # real render
mv runs/some_dir.partial runs/some_dir                                             # caller, on success only
```

Differences from the historical scripts, all deliberate:

| Historical | Here | Why |
| --- | --- | --- |
| `initialize_service` unguarded | in-process patch of ACE's `check_main_model_exists`, plus a refuse-all-outbound-TCP guard | ACE treats the missing `acestep-5Hz-lm-1.7B` folder as "main model missing": it probes www.google.com:443, tries a Hugging Face download and re-copies code files into `checkpoints/`. Observed in the engine.log of an aborted pre-patch run (lines quoted in reports/M0.md). No ACE source or checkpoint is modified. |
| `audio_format='wav'` (16-bit PCM) | `flac` default (24-bit, smaller) | PRD 5.2; measured in ENGINE_MEASUREMENTS.md |
| `guidance_scale=7.0` in receipts | recorded as requested 7.0, effective 1.0 | turbo ignores CFG; the engine overrides it |
| files named `<uuid>.wav` | `take_NN_s<seed>.flac` | stable names for the store |
| none | SIGTERM thread, `.partial` protocol, JSONL events, atomic `result.json` | worker integration (PRD 9) |

The script touches only OUT_DIR. It does not write to the ACE source or
checkpoints, and reads them via the shared ACE python (never upgraded here).
Only edit `MAX_DURATION_S` (currently 240) if M0 measurements say so.
