# Installation and operation

All paths below are the actual local workspace as of 22 October 2026. Optional
tools are labelled separately from installed/tested components. Do not install
all researched projects blindly: several address different roles or require
paid software.

## Existing working audio tools

Workspace:
`/Users/sidhandsome/Documents/local-video-generation/qwen-image-generation`

| Component | Local path / version | Evidence |
| --- | --- | --- |
| Sonic Pi | `/Applications/Sonic Pi.app`, 5.0.0 arm64 | Native playback and WAV recording worked in the earlier session |
| Earshot | `tools/earshot-main`, 0.3.0 | Local CPU measurements and CLAP/AST analysis ran |
| Earshot Python | `tools/earshot-venv/bin/python` | Separate environment; uses existing video libraries read-only |
| Earshot wrapper | `tools/earshot.sh` | Sets offline mode and 3 CPU threads |
| ffmpeg | `/opt/homebrew/bin/ffmpeg`, 9.0.1 | WAV/MP3 conversion and loudness export worked |
| Rubber Band CLI | `/opt/homebrew/bin/rubberband`, 4.0.0 | Independent time/pitch processing worked |
| ACE-Step source | `tools/ace-step-1.5` | Pinned source revision in research receipts |
| ACE-Step Python | `tools/acestep-venv/bin/python` | Inference dependencies installed; MPS and MLX initialization succeeded |
| ACE-Step core models | `tools/ace-step-1.5/checkpoints` | 16 files, 6.337 GB; LFS SHA256 checked |

## Sonic Pi

Official download: <https://sonic-pi.net/>. Use the Apple Silicon build on this
Mac. The native app is already installed. If its audio server repeatedly
reinitializes, the earlier successful fix was Preferences → Audio → Reset.
This is a confirmed fix for that incident, not a universal troubleshooting rule.

Open a `.rb` file in Sonic Pi and click Run; Stop halts playback. The project
contains a playback script for its final WAV. Edit its folder path if moved.
Sonic Pi is a synthesis/live-coding environment, not a vocal song-generation
model or a full studio DAW. Loading and playing a finished WAV is playback,
not evidence that Sonic Pi composed or mixed it.

Bundled samples used by the guide live in:
`/Applications/Sonic Pi.app/Contents/Resources/etc/samples/`.
Headless recording scripts are under:
`/Applications/Sonic Pi.app/Contents/Resources/app/server/ruby/bin/`.
Do not boot a second headless server against an active native audio server.

## Earshot

Official source: <https://github.com/Leonxlnx/earshot>.

From the workspace:

```sh
tools/earshot.sh doctor
tools/earshot.sh measure music/remix_studio_20261022/remix/A_Crown_of_Ash_and_Rain.wav
tools/earshot.sh describe music/remix_studio_20261022/remix/A_Crown_of_Ash_and_Rain.wav --start 40 --end 50
```

Run `--help` for the current CLI. For several analyses, one Python process
using `from earshot import api` avoids reloading models each time. Broad tags
are fallible; exact levels and clipping measurements have a different role.
`llm --yes-upload` is not part of the local workflow and must not be used
without explicit permission to upload the audio.

## ACE-Step: installed inference environment

Official source: <https://github.com/ace-step/ACE-Step-1.5>.
Official skills: <https://github.com/ace-step/ace-step-skills>.

The pinned repository was extracted into `tools/ace-step-1.5`. A separate
Python 3.12 virtual environment was created in `tools/acestep-venv`.
Existing site-packages are referenced read-only through a `.pth` file; packages
that need different versions are installed inside this new environment.
The original video and Earshot environments were not upgraded or replaced.
See `logs/acestep-environment-freeze.txt` and both pip installation logs.

Compatibility choices established during setup:

- torch 2.11.0, torchaudio 2.11.0 and torchvision 0.26.0 form the isolated trio.
- transformers 4.57.6 satisfies this source's `<4.58` requirement.
- diffusers 0.39.0, mlx 0.32.4 and mlx-lm 0.29.1 are installed locally.
- TorchAO 0.16 warns that compiled extensions are incompatible with this torch
  version; quantization is not used on MPS, so it is not the inference path.
- Optional LoKr/training/Lightning extras are not installed. Their startup
  warnings concern training capabilities, not the cover run used here.
- The separately downloaded 5 Hz music LM is not needed for source-conditioned
  cover generation. The core DiT, embedding model and VAE are present.
- The model loader reported native MLX DiT and MLX VAE active on MPS.

The restricted shell could import the runtime but could not bind localhost
port 8001 and did not expose the native GPU. The host Node runtime's Python
child process reported MPS available. We therefore run the official in-process
Python inference API from that native host. No audio is uploaded to a remote
generation service. This is an explicit adaptation of the downloaded skill's
REST-script workflow to the available execution surface.

### Run the project again

From an ordinary native Terminal, with the workspace as working directory:

```sh
EARSHOT_OFFLINE=1 EARSHOT_THREADS=3 tools/earshot-venv/bin/python music/remix_studio_20261022/scripts/build_guide.py

tools/acestep-venv/bin/python -u music/remix_studio_20261022/scripts/generate_cover.py \
  --guide music/remix_studio_20261022/remix/arrangement_guide.wav \
  --output music/remix_studio_20261022/remix/takes/new_take \
  --strength 1.0 --task-type cover-nofsq --seed 22102603 --steps 8

tools/earshot-venv/bin/python music/remix_studio_20261022/scripts/finish_master.py --take new_take
```

The second command must run where Python sees `torch.backends.mps.is_available()`
as true. Otherwise it may fall back to CPU; verify the startup log. Do not reuse
an output folder for a different approved take. Generation parameters and
results are written in the selected take folder.

For a small test, substitute `fusion_guide.wav` as input. The model uses the
arranged guide and `remix/caption.txt`; it does not reconstruct both complete
songs from their titles. Exact model/source revisions and seeds matter.

The selected final render is `full_02`, source-preserving `cover-nofsq` at
strength 1.0. At that setting the result closely reconstructs the arranged
guide; do not claim a completely new instrumental performance. The musical
transformation comes primarily from the phrase arrangement, pitch/time fitting,
register changes, added harmony/pulse, transitions and final gain/width automation.
`finish_master.py` adds section dynamics and uses two-pass loudness normalization.

### Optional REST server

In an unrestricted native Terminal:

```sh
music/remix_studio_20261022/scripts/start_ace.sh
```

This binds **127.0.0.1:8001**, not an externally exposed interface. The server
script is supplied for normal local operation, but it could not bind in the
restricted shell during this session. Stop with Ctrl-C. The official
`acestep/scripts/acestep.sh` wrapper can then use the local API. Read its
`--help` and `config.example.json`; use a local API URL, native API mode,
`thinking:false` and `use_format:false` for the no-LM cover route. The source
snapshot preserves the complete wrapper instructions without silently
registering or editing it globally.

## Clean installation on another Mac

Use a fresh Python 3.12 environment, the pinned ACE-Step source revision,
and the original engine's current installation guide under
`tools/ace-step-1.5/docs/en/INSTALL.md`. The source snapshot archive is included
in this project. The ordinary upstream route is `uv sync` and the macOS launcher.
It installs more UI/training packages than this inference-only setup.
Use the documented macOS scripts, not Linux CUDA wheel indexes.

For a controlled inference-only rebuild, the file
`scripts/requirements-inference.txt` lists the main packages used here.
Install them in a clean environment and add the extracted engine to PYTHONPATH
or install it editable with `--no-deps`. The environment freeze records the
actual shared-library setup; it is a provenance record, not a promise that
every listed video package is needed by music inference.

The 6.337 GB core model is `ACE-Step/Ace-Step1.5` at the revision recorded in
`research/ace-model-revision.json`. Download the three directories
`acestep-v15-turbo/`, `vae/`, and `Qwen3-Embedding-0.6B/` into the engine's
`checkpoints/`. Compare LFS checksums against the receipts. The project archive
does not duplicate those large weights or virtual environments.

## Use the downloaded composition/lyric skills

Their original README files contain installation instructions. For the current
project we load the pinned files explicitly from `research/vendor/`. This avoids
global changes and preserves all their reference tables and templates.
In clients supporting the Agent Skills convention, the composition and lyric
skill folders can be copied to a project skill directory, or installed using
the repositories' documented plugin route. A restart/new session may be needed
for discovery. No new global registration is claimed here.

The lyric library is available for future songs; this instrumental remix does
not need new lyrics or sung vocals. Loading lyrics skills is not the same thing
as installing a singing model.

## Optional production/DJ tools: downloaded, not installed

- Ableton MCP Pro: install Ableton Live 11+, Python and the supplied remote
  script, enable the control surface, then register its MCP server. Read the
  pinned README. A Max for Live alternative has its own edition requirements.
- Ableton Skills: install a separate Ableton MCP server, then reference the
  provided skill files from your coding agent. This pack supplies no server.
- Bitwize Music Skills: follow its README setup/configure workflow. Suno
  generation/service access remains separate; do not assume a public official
  Suno API is provided by this repository.
- Mixxx AI DJ: use the author's MCP-enabled Mixxx fork and its build guide.
  Merely installing standard Mixxx does not expose the named MCP tools.
- DJ Claude: see its pinned README for Node/Strudel and browser/native audio
  modes. Optional text-to-pattern generation may require an API key.

These options are reference routes, not verified installations on this Mac.
