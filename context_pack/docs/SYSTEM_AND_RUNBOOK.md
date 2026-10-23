# Current system and operational runbook

Prepared 24 October 2026. Read the JSON inventory for current inspected facts;
prior experiment logs establish what actually ran. No new audio was rendered
while preparing this handoff.

## 1. Paths and versions

Shared workspace:
`/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation`

Dedicated app root: the `raag-studio` folder underneath that workspace.

| Component | Actual location / current version | Use and limitation |
| --- | --- | --- |
| ACE-Step source | `../tools/ace-step-1.5` | Existing pinned renderer; do not upgrade casually |
| ACE Python | `../tools/acestep-venv/bin/python`, Python 3.12.14 | Torch/torchaudio 2.11.0, Transformers 4.57.6, MLX 0.32.4, mlx-lm 0.29.1, Diffusers 0.39.0 |
| Core models | `../tools/ace-step-1.5/checkpoints` | Only turbo DiT, VAE, Qwen3 embedding; no separate 5 Hz music LM |
| Earshot | `../tools/earshot-main`, `../tools/earshot-venv`, `../tools/earshot.sh` | 0.3.0; dedicated analysis environment currently inherits Torch 2.14.0 / Transformers 5.20.2 |
| Sonic Pi | `/Applications/Sonic Pi.app`, 5.0.0 | Actual synth/sample playback and recording; not a realistic lyric-to-singer model |
| FFmpeg/FFprobe | `/opt/homebrew/bin/ffmpeg`, `/opt/homebrew/bin/ffprobe` | Version 9.0.1; conversion, decode checks and mastering |
| Rubber Band | `/opt/homebrew/bin/rubberband`, 4.0.0 | Separate CLI; do not assume FFmpeg has a Rubber Band filter |
| Whisper | `../tools/whisper-small-mlx`, mlx-whisper 0.4.3 in ACE environment | Fallible unprompted singing transcription |
| HDemucs | `../tools/hdemucs/hdemucs_high_trained.pt` | torchaudio local source separation; estimated stems |
| Agent Reach | `../tools/agent-reach-venv` | 1.6.0, isolated research environment; no global setup |

Paths beginning `../tools` are relative to the dedicated root. The fresh
inventory resolves all of these paths as present. MPS was available in the
authorized native-host probe; that is not a model render or performance test.
At audit time the video queue on port 8388 was empty, while 8188/8288 were
unreachable. Recheck before running; do not stop other people's jobs.

The current Earshot doctor check reports healthy CLI/data and cached CLAP/AST
weights. Its optional `mcp` import is missing in the dedicated Earshot environment;
this is not an active globally registered Earshot MCP server. Use the established
CLI/Python API. The full check is in `inventory/EARSHOT_DOCTOR_CURRENT.txt`.

ACE source revision: `ca1e85fe9430179831e6bc6be790c332190a3866`.
Core weight revision: `19671f406d603126926c1b7e2adc169acbcade22`.
See `inventory/ace_engine_source.json`, model receipts and checkpoint file list.
Large environments/weights are reused at their existing paths and are not
copied into this context archive.

## 2. Read-only checks

From the dedicated root:

```sh
python3 scripts/verify_context.py
python3 scripts/render_local.py --recipe yamuna --dry-run
../tools/acestep-venv/bin/python -c 'import torch; print(torch.backends.mps.is_available())'
../tools/earshot.sh doctor
```

The first two are lightweight and do not load music models. An environment
that returns MPS false may need a normal native Terminal or an available
authorized host-execution tool. Do not fall back to a long CPU render or
reinstall working packages without diagnosing the execution surface.

The established earlier jobs used a native host Python child process because
the restricted shell exposed different GPU/localhost behavior. This is an
execution-environment observation, not a required Node integration for the app.

## 3. Render a preserved recipe to a fresh directory

Only after resources are available, from a native Terminal:

```sh
../tools/acestep-venv/bin/python -u scripts/render_local.py --recipe yamuna
```

Other recipes: `daylight`, `thodi`, `moonlit`. Use `--seed NEW_INTEGER` for a
new take. The helper creates a new uniquely named folder under `runs/`, saves
the complete request/result and log, and refuses an existing output directory.
`--output` must remain under `runs/`. It forces offline model access and requires
MPS. It never writes into the accepted examples or original project folders.

This helper is newly prepared and its dry-run path was verified. It uses the
same established in-process ACE API and configuration as prior successful
scripts, but its actual generation branch was not rerun during handoff.

The historical scripts under `reference_source/` are copied unchanged and
contain original relative paths/output names. Treat them as implementation
evidence, not drop-in runnable scripts after relocation. Requests/results in
`recipes/` are the exact selected historical inputs, not rewritten approximations.

## 4. Inspect or finish audio

```sh
../tools/earshot.sh measure context_pack/examples/accepted/Yamuna_at_Dawn.mp3 --music
../tools/earshot.sh describe context_pack/examples/accepted/Yamuna_at_Dawn.mp3 --start 65 --end 77
/opt/homebrew/bin/ffprobe -v error -show_format -show_streams context_pack/examples/accepted/Yamuna_at_Dawn.mp3
```

For several descriptions, reuse one CPU process with `from earshot import api`
instead of reloading CLAP/AST on every CLI call. Keep offline mode and a few CPU
threads. Do not call the optional external LLM audio-upload path automatically.

The successful master/export implementations are preserved in
`reference_source/daylight/export_music.py` and
`reference_source/bansuri/review_and_export.py`. They use two-pass FFmpeg
loudness normalization, 48 kHz/24-bit WAV and 320 kbps MP3, and verify decoded
output. Adapt their paths to fresh `runs/` outputs. Readability and taste are
separate from loudness. Do not turn a normalization target into a musical-quality metric.

## 5. Sonic Pi

Open the installed app and run a Ruby score. The successful recorder attached
to an existing idle Spider server and sent `/start-recording`, `/run-code`,
`/stop-recording`, `/save-recording` through that active instance. Direct UDP
engine recording failed on this installation because the audio-engine transport
was TCP. Do not boot a competing headless engine.

The working score and recorder are preserved under
`reference_source/sonic_pi_hybrid/`. To make a new capture, copy both into a
fresh run directory first:

```sh
sonic_run_dir="$(mktemp -d "$PWD/runs/sonic-pi.XXXXXX")"
cp context_pack/reference_source/sonic_pi_hybrid/backing.rb "$sonic_run_dir/"
cp context_pack/reference_source/sonic_pi_hybrid/record_active.rb "$sonic_run_dir/"
"/Applications/Sonic Pi.app/Contents/Resources/app/server/native/ruby/bin/ruby" "$sonic_run_dir/record_active.rb"
```

This records the old instrumental score in a new location; it does not generate
singing. The recorder plays audible music through the active app. An earlier
audio restart loop was resolved with Preferences -> Audio -> Reset; that is
a past incident fix, not something to apply automatically to a working app.

## 6. Whisper and separation

The Hindi source's `check_sung_lyrics.py` demonstrates:

```python
mlx_whisper.transcribe(audio_path, path_or_hf_repo=local_model_path,
    language='hi', verbose=False, temperature=0,
    condition_on_previous_text=False)
```

Do not supply intended lyrics as a prompt when using ASR as independent evidence.
Save its uncorrected output in a fresh run. It can mishear singing; flagged
words still need listening.

`reference_source/sonic_pi_hybrid/separate_vocal.py` demonstrates the installed
torchaudio `HDEMUCS_HIGH_MUSDB_PLUS` checkpoint, CPU inference, 8-second chunks
and 1-second overlap. Adapt hardcoded paths before executing. Separation is
not melody-conditioned singing and cannot replace a wrong consonant.

## 7. Agent Reach research

Use the existing isolated Python. The prior launcher scopes its state to the
PRD research folder; the copied `reference_source/reach_local.py` similarly
uses its own local directory if relocated. Do not run global setup merely to
read public captions. The archived research received a YouTube rate-limit
response, so re-evaluate availability rather than retrying automatically.

Successful actions were `youtube search` and `youtube subtitle`, using the
public yt-dlp backend. There was no video-frame understanding, no independent
music listening from that tool, no browser login and no paid transcription.
Source links and paraphrases are already bundled, so repeating these requests
is unnecessary to review the PRD.

## 8. New machine or missing runtime

Use the pinned receipts, public source links and historical installation guide
to provision isolated environments. The package freeze records describe this
Mac, including read-only paths inherited from other runtimes; they are not a
portable one-command requirements specification. Keep compatible Torch and
torchaudio together. Verify models/licences and native GPU support before a job.

Do not download gigabytes of alternative models to understand the handoff.
The accepted MP3s, complete requests, code and research are already included.
External music API credentials and any standalone planner account are not
bundled and must never be invented or copied from unrelated projects.
