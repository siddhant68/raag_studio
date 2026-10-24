# Engine request contract: `raag-engine-request/1`

Interface between the Raag Studio worker and `run_takes.py`. The worker
(M2) builds the request from a compiled plan; the engine never sees a plan.

```
ACE_PYTHON app/engine/run_takes.py REQUEST_JSON OUT_DIR [--dry-run] [--engine ACE_SOURCE_DIR]
```

`ACE_PYTHON` is `tools/acestep-venv/bin/python` (shared, read-only). The API
process must never import torch; it only spawns this script.

## Request file

```json
{
  "schema": "raag-engine-request/1",
  "params": { "...ACE GenerationParams, WITHOUT seed...": "..." },
  "seeds": [24103001, 24103002, 24103003],
  "audio_format": "flac",
  "meta": { "round_id": "free-form, echoed into result.json" }
}
```

| Key | Required | Rule |
| --- | --- | --- |
| `schema` | yes | exactly `raag-engine-request/1` |
| `params` | yes | object; same keys as `recipes/*/request.json` `params` minus `seed`. Unknown keys are rejected (checked against the `GenerationParams` fields in the ACE source). Omitted keys take ACE defaults. |
| `seeds` | yes | 1 to 8 unique integers in [0, 2^31). One take per seed, rendered serially in this order. |
| `audio_format` | no | `flac` (default) or `wav`. |
| `meta` | no | object, copied to `result.json` untouched. |
| `model` | no | `{"dit": "acestep-v15-turbo" \| "acestep-v15-xl-turbo", "lm": {"name": "acestep-5Hz-lm-1.7B" (or 0.6B/4B), "backend": "mlx" \| "pt"}}`. Absent = the turbo DiT without an LM (every request before the song pipeline). Weights must already be on disk: nothing is downloaded during a render (`python3 scripts/fetch_models.py` is the only download path). |

Other top-level keys are rejected. Validation of `params`:

- `seed` must be absent (a seed inside `params` is an error).
- `task_type` must be `text2music`; `reference_audio` and `src_audio` must be null/empty.
- `caption`: non-empty string, at most 512 characters (`len()`).
- `lyrics`: string, at most 4000 characters (never truncated).
- `duration`: number in [10, 240] seconds (240 is `MAX_DURATION_S` in `run_takes.py`; see `context_pack/docs/ENGINE_MEASUREMENTS.md`).
- `thinking` is true exactly when `model.lm` is given (the LM writes audio codes; it is loaded only then).
- `use_cot_metas/caption/language/lyrics` must be false: the LM never rewrites the caption, lyrics, language or
  metadata the app compiled.
- the named DiT/LM folders must contain `config.json` and `*.safetensors` (checked in `--dry-run` too).

All validation (including `OUT_DIR`) happens before torch is imported or any
file is created. A bad request prints one `error` event with
`code: "invalid_request"` and a `problems` list, and exits 2.

## OUT_DIR

Must be a path that does **not exist**, whose parent exists, and whose name ends in
`.partial`. The script creates it. **The script never renames it.** On
success (exit 0 and a `done` event) the caller renames `X.partial` to `X`.
On any failure or kill the `.partial` directory stays for the caller to sweep;
a final directory must never exist for a failed run.

Contents:

| File | When | Notes |
| --- | --- | --- |
| `request.json` | at start | byte-for-byte copy of the request file |
| `engine.log` | at start | everything the ACE libraries print (stdout and stderr), plus `[run_takes]` lines |
| `result.json` | at start, rewritten after every take | see below; `status`: `running`, `ok`, `failed`, `terminated` |
| `take_NN_s<seed>.flac` | per take | `NN` is the 1-based take index; `.wav` instead of `.flac` if `audio_format` is `wav` or the engine could not write FLAC (then `take_done.format` says `wav` and `result.json` takes[].notes explains) |

Native audio is 48 kHz stereo. FLAC written by the engine is 24-bit; the
engine's WAV writer is 16-bit PCM (see ENGINE_MEASUREMENTS.md).

## stdout: JSON lines

Only events are written to stdout (library noise is redirected to
`engine.log`). Every event has `event` and `ts` (UTC ISO-8601, milliseconds).

| event | extra fields |
| --- | --- |
| `model_loading` | `checkpoint`, `out_dir` |
| `model_ready` | `load_s`, `device` (`mps`), `turbo`, `peak_rss_mb` |
| `take_start` | `index`, `seed`, `of` |
| `take_done` | `index`, `seed`, `path` (file name **relative to OUT_DIR**, because the caller renames the directory), `format`, `duration_s` (from the audio tensor), `wall_s` (whole take incl. normalise, fade, encode, write), `pipeline_s` (engine-reported DiT+VAE time), `bytes` |
| `error` | `code`, `message` (and `problems` for `invalid_request`) |
| `done` | `takes`, `total_wall_s`, `model_load_s`, `peak_rss_mb`, `partial_dir` |
| `dry_run_ok` | `seeds`, `duration`, `audio_format`, `out_dir`, `torch_imported` (always false); `--dry-run` only |

`error` codes: `invalid_request`, `missing_checkpoint`, `mps_unavailable`,
`model_load_failed`, `take_failed`, `terminated`, `unexpected`.
After an `error` event no `done` event follows.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | all takes written (`done` emitted) |
| 1 | unexpected exception |
| 2 | invalid request or OUT_DIR (nothing created) |
| 3 | environment: missing weights, MPS unavailable, model failed to load |
| 4 | a take failed (earlier finished takes remain in the `.partial` dir) |
| 143 / 130 | killed by SIGTERM / SIGINT (128 + signal) |

## result.json (`raag-engine-result/1`)

Key fields: `status`, `started_at`, `finished_at`, `request_sha256`, `seeds`, `meta`,
`requested_params` (exactly what was asked), `effective_params`, `notes`,
`engine` (`source`, `checkpoint`, `device`, `turbo`, `torch`), `model_load_s`,
`total_wall_s`, `peak_rss_mb`, `checkpoints` (`files`, `unchanged`),
`network_attempts` (must be `[]`), and `takes[]` (`index`, `seed`, `file`,
`format`, `bytes`, `sample_rate`, `channels`, `duration_s`, `wall_s`,
`pipeline_s`, `time_costs`, `engine_key`, `peak_rss_mb`, `notes`).

**Requested vs effective.** `effective_params` is the full `GenerationParams`
set (defaults filled in, no seed; seeds are per take) after the engine's own
overrides:

- Turbo forces `guidance_scale` to `1.0` (no CFG). A request that says `7.0`
  (as every historical receipt does) is recorded as requested `7.0`,
  effective `1.0`, with a note. Recipes/compilers should simply send `1.0`.
- `dcw_enabled: null` resolves to `true` on turbo.

Receipts must store both blocks.

## Signals

SIGTERM and SIGINT are handled on a dedicated thread, so a long native torch
call cannot delay them. The process writes `result.json` status
`terminated`, emits an `error` event (`code: "terminated"`), and exits
immediately (measured 0.02 to 0.04 s). The `.partial` directory is left in
place. The worker should still escalate to SIGKILL after 3 s as policy.

## Environment the script sets itself

`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `TOKENIZERS_PARALLELISM=false`,
`OMP_NUM_THREADS=4`, `torch.set_num_threads(4)`, `MPLCONFIGDIR` (temp dir).

Guards that go beyond the historical scripts (see README.md for why):

1. Weights check: turbo DiT, VAE and Qwen3 embedding `.safetensors` must exist,
   else `missing_checkpoint` (exit 3). Nothing is fetched.
2. In-process patch of ACE's "main model present" check, so `initialize_service`
   does not try to auto-download the (deliberately absent) 5Hz LM.
3. Outbound TCP connections to non-loopback addresses are refused and recorded
   in `result.json` `network_attempts`.
4. If MPS is unavailable the script exits 3 (`mps_unavailable`); it never falls back to CPU.

## Caller checklist (worker)

1. `scripts/preflight.py --json`: proceed only if `ok` and `video_queue.state == "idle"`.
2. `--dry-run` (cheap) or validate with the same rules in the API.
3. Spawn the script, read stdout line by line, treat EOF without `done` as failure.
4. On `done` + exit 0: rename `.partial`, then run ffprobe/ffmpeg technical checks.
5. On anything else: leave the `.partial` for the boot sweep.
