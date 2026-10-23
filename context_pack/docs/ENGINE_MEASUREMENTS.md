# Engine measurements (M0)

Measured 2026-10-24 (UTC 21:33 to 21:38) on the Apple M5 Pro Mac (Mac17,9, 48 GiB
unified memory, macOS 26.5.1), ACE python 3.12.14 / torch 2.11.0, ACE-Step 1.5
turbo checkpoint, MPS, `batch_size=1`, `inference_steps=8`, `thinking=False`,
offline env, via `app/engine/run_takes.py`. Raw evidence:
`runs/_m0/20261023T213344Z/` (events `run*_events.jsonl`, `/usr/bin/time -l`
output `run*_time.txt`, per-run `result.json`/`engine.log`, `verify.json` per take).

Prompt for all takes: the Yamuna request (`recipes/yamuna/request.json` params, new
seeds). Only 5 takes were rendered, so every number below is a single sample
(or 3 for the 168 s case); treat as typical, not as a distribution.

## Timings

| Run | Duration | Takes | Model load | Per-take wall | Engine pipeline (DiT + VAE) | Realtime factor (duration / wall) |
| --- | --- | --- | --- | --- | --- | --- |
| A | 168 s | 3 in one process | 4.9 s | 24.6, 26.1, 20.8 s (mean 23.8) | 14.8, 13.8, 12.7 s | 6.8x, 6.4x, 8.1x |
| B | 60 s | 1 | 8.5 s | 8.0 s | 6.7 s | 7.5x |
| C | 240 s | 1 | 8.5 s | 31.6 s | 23.6 s | 7.6x |

- "Wall" is the whole take as the worker sees it (`take_start` to `take_done`):
  engine pipeline plus normalisation, fade, tensor copy, encode and write. About
  8 to 12 s of the 168 s take's wall time is outside the engine's own
  `pipeline_total_time`.
- Model load: 4.9 s (run A, files warm in the page cache) and 8.5 s twice; the
  PRD estimate of about 6 s holds. Use "about 5 to 9 s" for UI copy.
- Whole run A (load + 3 x 168 s): 76.6 s, 504 s of music in 77 s.
- Between takes in one process: `take_done` to next `take_start` was 0.056 s and
  0.055 s, so the model is not reloaded.
- The accepted historical render of the same 168 s request took 23.3 s
  (`recipes/yamuna/result.json`); the harness matches it.
- Engine breakdown per take (seconds):

| Duration | DiT diffusion (8 steps) | VAE decode | pipeline total |
| --- | --- | --- | --- |
| 60 s | 1.3 | 5.4 | 6.7 |
| 168 s | 4.1, 5.2, 5.5 | 10.8, 8.6, 7.3 | 14.8, 13.8, 12.7 |
| 240 s | 6.2 | 17.5 | 23.6 |

VAE decode is the larger and more variable part. A 3-take round at the default
length (about 168 s) costs about 5 s (load) + 3 x 24 s = 77 s; at 240 s it
would be about 8 + 3 x 32 = 104 s.

## Length scaling and the 240 s cap

The 240 s take worked: exit 0, 240.000 s, 48 kHz stereo, silent 2.6%, clipped 0%.
Engine pipeline time was 23.6 s against the PRD threshold of 120 s.

Recommendation: **keep the 240 s cap** (the PRD rule to drop to 180 s applies
only if 240 s exceeds 120 s pipeline time or fails; it did neither, and wall time
is 31.6 s). Only the 60, 168 and 240 s points were measured (the user capped
renders); 120 s and 180 s lie between measured points and the scaling is
close to linear (pipeline 6.7 to 14 to 23.6 s), so no surprise is expected.
`MAX_DURATION_S = 240` in `run_takes.py` stays.

## Memory

| Run | peak RSS (`getrusage`, in process) | `/usr/bin/time -l` max RSS | peak memory footprint | swaps |
| --- | --- | --- | --- | --- |
| A (3 x 168 s) | 14,136.7 MB (13.8 GiB) | 14,823,374,848 B | 53.7 GB | 0 |
| B (60 s) | 14,136.7 MB | 14,823,440,384 B | 51.2 GB | 0 |
| C (240 s) | 14,136.8 MB | 14,823,555,072 B | 54.6 GB | 0 |

- RSS peaks while the model loads (13.8 GiB) and does not grow with take count or
  length (run A: identical after take 1, 2 and 3), so serial takes are safe.
- macOS "peak memory footprint" (includes GPU-mapped and compressed pages) was
  51 to 55 GB, above the 48 GiB of RAM, with 0 swaps. `vm_stat` during run C
  showed 24% system-wide memory free and Pageouts 69,695 (cumulative since boot).
  The render fits, but it leaves little headroom: do not run it alongside a
  ComfyUI video generation. This is why the queue gate and one-job-at-a-time
  rules in PRD section 9 are mandatory.
- The ComfyUI process on :8388 was resident but idle (empty queue) throughout.

## Audio format and size (FLAC vs WAV)

FLAC is writable by the engine (`audio_format="flac"`, soundfile backend); no
fallback to WAV was needed. Facts from ffprobe:

| Format | Codec / depth | Size of the 168 s take 1 | Source |
| --- | --- | --- | --- |
| FLAC (engine) | flac, 24-bit (s32 container), 48 kHz, 2 ch | 25,041,331 B (23.9 MiB) | engine render |
| WAV (engine writer) | `pcm_s16le`, 16-bit | 32,256,078 B (30.8 MiB) | same samples re-encoded with ffmpeg; the engine's own WAV writer was checked on a 3 s synthetic tensor and also gives `pcm_s16le` |
| WAV 24-bit | `pcm_s24le` | 48,384,102 B (46.1 MiB) | same samples re-encoded with ffmpeg |

So engine FLAC is 22% smaller than the engine's own 16-bit WAV and 48% smaller than a
24-bit WAV, while carrying 24-bit precision. Sizes per take: 60 s = 9.1 MB,
168 s = 25.0 to 25.5 MB, 240 s = 37.1 MB (about 0.155 MB per second). 3 takes of
168 s = 76 MB. Storage plan: native FLAC is sufficient; no WAV master is
needed before export.
(The accepted historical WAVs were not re-rendered, so no engine-WAV render was
done in M0 to stay inside the render budget; the WAV numbers are derived as above.)

## Requested vs effective parameters

Requested `guidance_scale` 7.0 (as in every historical receipt). The turbo model
overrides it: `result.json` records `requested_params.guidance_scale = 7.0`,
`effective_params.guidance_scale = 1.0`, with the note
"turbo model forces guidance_scale 7.0 -> 1.0 (no CFG)". Also resolved by the
engine: `dcw_enabled` null -> true on turbo. All other parameters were applied
as requested (full effective set is in each `result.json`). Seeds are recorded
per take (24103001, 24103002, 24103003; 24103060; 24103240).

## Offline behaviour and an ACE quirk the harness works around

- The environment is offline (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`). The
  three real runs recorded `network_attempts: []` (non-loopback connections are
  refused and logged), `engine.log` contains no download/google/huggingface lines,
  and `ls -lR checkpoints` was byte-identical before and after run A (and the
  in-process listing digest was unchanged for B and C).
- Without the harness patch, ACE's `initialize_service` considers the main model
  missing because the 5Hz LM folder (`acestep-5Hz-lm-1.7B`) is not installed. It
  then opens a TCP connection to www.google.com:443 to pick a download mirror,
  attempts a Hugging Face `snapshot_download`, and re-copies two code files into
  `checkpoints/acestep-v15-turbo/`. The historical scripts did the same silently.
  `run_takes.py` avoids all of that (see `app/engine/README.md`).

## Technical checks of the five takes (ffprobe / ffmpeg, breakage-only)

| Take | Dur | Err | Rate/ch | Silent (< -50 dB, >= 0.5 s) | Clipped (|x| >= 0.999) | Sample peak | True peak | LUFS-I | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 s24103001 | 168.000 | 0.000 | 48k/2 | 4.52% | 0 | 0.8414 | -1.5 dBTP | -15.7 | pass |
| A2 s24103002 | 168.000 | 0.000 | 48k/2 | 2.78% | 0 | 0.8414 | -1.4 | -18.5 | pass |
| A3 s24103003 | 168.000 | 0.000 | 48k/2 | 0.89% | 0 | 0.8414 | -1.5 | -17.9 | pass |
| B s24103060 | 60.000 | 0.000 | 48k/2 | 2.16% | 0 | 0.8414 | -1.5 | -16.0 | pass |
| C s24103240 | 240.000 | 0.000 | 48k/2 | 2.59% | 0 | 0.8414 | -1.5 | -16.7 | pass |

Watch item for the M2 checks: take A1 passed with only 0.5 point of margin. Its
silence is one block, 160.4 s to 168.0 s (7.6 s): the last 7.6 s are below
-50 dB (this includes the engine's 3 s fade-out). The "silent fraction < 5%" check is
threshold-dependent (the PRD does not give a floor; this report used -50 dB,
0.5 s minimum). At that floor a short track with a similar tail would exceed 5%
(a 60 s track with a 3 s tail sits exactly at 5%). The accepted Yamuna MP3 measures 2.5% with the same
settings. Decide the floor in M2 and consider measuring silence excluding the
final fade-out, or trimming the silent tail. The checks say nothing about
musical quality; nobody has listened to these takes yet (AT-M0-08 pending).
