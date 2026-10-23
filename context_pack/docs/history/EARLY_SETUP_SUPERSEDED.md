# Sonic Pi and Earshot — 22 October 2026

Sonic Pi 5.0.0 (Apple silicon) is installed at `/Applications/Sonic Pi.app`.
The official installer's SHA-256 was verified against the Homebrew cask:
`3dd0b9873a74aa274d3723be098622fdea73896ceba29a1423af9e7b46a7c291`.
The first launch needed Preferences → Audio → Reset. The engine then reported
successful reinitialisation. Delhi Afterglow ran to completion and a stereo
48 kHz, 24-bit WAV was recorded and checked for a non-silent signal.

Earshot 0.3.0 is installed in `../tools/earshot-main` with its own environment
in `../tools/earshot-venv`. That environment reads existing Torch and Transformers
packages from the video_generation_v2 runtime; it does not modify that runtime.
If that runtime moves, recreate Earshot's environment or update its `.pth` file.

Both pinned listening models are downloaded and their weight checksums verified:

- CLAP: `laion/larger_clap_general`, revision `16c8cc3159a3c8a31e8ff5ef1f66b0d9ab3667db`.
- AST: `MIT/ast-finetuned-audioset-10-10-0.4593`, revision `f826b80d28226b62986cc218e5cec390b1096902`.

Run Earshot from the project root:

```sh
./tools/earshot.sh doctor
./tools/earshot.sh describe music/delhi_afterglow.mp3 --start 18 --end 28
./tools/earshot.sh measure music/delhi_afterglow.mp3 --music
```

The launcher uses three CPU threads and offline mode. The CLI and Python API
work in this session; no global MCP registration or audio upload was performed.
The first actual listening test completed: AST Music 0.70; the 10-second excerpt
measured -23.1 LUFS, with a true peak of -7.6 dBTP. Genre and mood labels are
unvalidated hints. Earshot provides model-based evidence, not human hearing or
a judgement of musical taste. Automatic tempo/key estimates need checking: the
known 80 BPM E-minor composition was measured near double tempo and relative G major.

For the proposed Ashes on the Fire / Rains of Castamere mashup, source recordings
are still missing. Official streaming/purchase links were found, but no authorized
free downloads were identified. No recordings were downloaded or mashup produced.

Official projects:
- https://sonic-pi.net/
- https://github.com/Leonxlnx/earshot
