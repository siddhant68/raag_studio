# Raag Studio: dedicated project and agent handoff

Prepared 24 October 2026 for Siddhant Pathak.

**Start with `HANDOFF_PROMPT.md`.** It is a copy-pasteable instruction for an
independent agent to review the plan and implement the application.

## Read order

1. `HANDOFF_PROMPT.md`: mission, user requirements, musical history and completion criteria.
2. `context_pack/docs/PROJECT_CONTEXT.md`: decisions, experiments, accepted/rejected evidence and correction of stale notes.
3. `context_pack/examples/AUDIO_GUIDE.md`: what to hear and how the user judged it; playable files are included.
4. `context_pack/docs/prd/Music_Studio_PRD.md` or its PDF: the current proposed product.
5. `context_pack/docs/SYSTEM_AND_RUNBOOK.md`: exact installation paths and safe operational commands.
6. `context_pack/docs/IMPLEMENTATION_REVIEW.md`: specification gaps to resolve during implementation.
7. `context_pack/docs/research/` and `context_pack/third_party/`: supporting sources and downloaded guides.

## Folder contract

| Path | Purpose |
| --- | --- |
| `app/` | All future frontend/backend application source |
| `scripts/` | Context verification and fresh-output recipe rendering helpers |
| `data/` | Future local app state, database and imported assets |
| `runs/` | New generated takes, logs and exports |
| `context_pack/` | Preserved specifications, research, examples, recipes and inventory |

No application backend or frontend has been implemented by the handoff task.
`app/README.md` is an implementation entry point, not a working server.

## Verify without generating music

From this folder:

```sh
python3 scripts/verify_context.py
python3 scripts/render_local.py --recipe yamuna --dry-run
```

The second command validates the preserved request and prints the resolved
engine/output settings. It does not import Torch, load models or generate audio.
Actual rendering needs the existing ACE Python and native Apple GPU access;
see the runbook before starting it. New renders always use a fresh run folder.

The handoff includes audio examples and source/configuration evidence. Large
model weights and Python environments remain in their existing shared locations
and are indexed explicitly. It is a self-contained context pack, not an offline
installation image for a different computer.

`context_pack/inventory/FILE_MANIFEST.json` records every bundled file hash.
The portable ZIP is at this project root and excludes itself from its contents.
It preserves this handoff baseline; the project can evolve independently after
archiving. Do not delete existing approved source projects.

## Run

The backend (M2) is a FastAPI app on `127.0.0.1:8477`; renders run ACE-Step turbo in a subprocess
(shared ACE python, MPS only, never CPU). Use only the app venv for the API:
`app/.venv` (Python 3.12; packages pinned in `app/requirements.txt`).

```sh
python3 scripts/preflight.py        # MPS, disk >= 5 GiB, :8388 video queue idle, weights, ffmpeg
scripts/start.sh                    # background server; pid in data/server.pid, log in data/server.log
curl -s http://127.0.0.1:8477/api/system
scripts/stop.sh                     # kills only the pid in data/server.pid (checks it is uvicorn)
```

- Data: `data/raag.db` (SQLite, WAL). Audio: `runs/<song_id>/<round_id>/` (native FLAC, MP3 previews,
  request.json, result.json, engine.log), exports in `runs/<song_id>/exports/`. Override with
  `RAAG_DATA_DIR`, `RAAG_RUNS_DIR`, `RAAG_PORT`.
- One render at a time; a render waits (reason `mac_busy`) while the ComfyUI video queue on `:8388` is busy.
- API reference for the web UI: `app/backend/API_NOTES.md`. M2 report: `reports/M2.md`.
- Tests (CPU only, fake engine, temp dirs; no real render): `app/.venv/bin/python -m pytest app/tests -q`.
  The fake engine (`RAAG_ENGINE=fake`, `app/engine/fake_engine.py`) exists only for tests, labels every response
  `engine:"fake"`, and is never a real render. Without that variable the app always uses the real engine.
