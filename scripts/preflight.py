"""Report whether this Mac is ready for a music render. Stdlib only.

    python3 scripts/preflight.py [--json]

Exit code is non-zero when free disk is below 5 GiB or MPS is unavailable.
A busy video queue is reported (video_queue.state == "busy") but is not an
error: the caller decides to wait.

MPS is probed by running the shared ACE python in a subprocess, because this
script's own python has no torch.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(os.environ.get('RAAG_TOOLS_DIR', ROOT.parent/'tools'))
ACE_PYTHON = TOOLS/'acestep-venv/bin/python'
ACE_SOURCE = TOOLS/'ace-step-1.5'
QUEUE_URL = os.environ.get('RAAG_VIDEO_QUEUE_URL', 'http://127.0.0.1:8388/queue')
MIN_DISK_GIB = 5.0
REQUIRED_CHECKPOINTS = (
    'acestep-v15-turbo/config.json', 'acestep-v15-turbo/model.safetensors',
    'acestep-v15-turbo/silence_latent.pt', 'vae/config.json',
    'vae/diffusion_pytorch_model.safetensors', 'Qwen3-Embedding-0.6B/config.json',
    'Qwen3-Embedding-0.6B/model.safetensors', 'Qwen3-Embedding-0.6B/tokenizer.json',
)
MPS_PROBE = ('import json, torch; print(json.dumps({"torch": torch.__version__, '
             '"mps": bool(torch.backends.mps.is_available())}))')


def probe_mps():
    """Ask the ACE python whether MPS is available. Never falls back to CPU."""
    if not ACE_PYTHON.is_file():
        return {'available': False, 'detail': f'ACE python not found at {ACE_PYTHON}'}
    try:
        done = subprocess.run([str(ACE_PYTHON), '-c', MPS_PROBE], capture_output=True,
                              text=True, timeout=60, env={**os.environ, 'OMP_NUM_THREADS': '4'})
        info = json.loads(done.stdout.strip().splitlines()[-1])
        return {'available': info['mps'], 'torch': info['torch'], 'detail': 'probed with ACE python'}
    except Exception as exc:  # timeout, crash, bad output: report as unavailable
        return {'available': False, 'detail': f'probe failed: {type(exc).__name__}: {exc}'}


def check_video_queue():
    """idle: refused or empty queue. busy: running/pending jobs. unknown: anything else."""
    try:
        with urllib.request.urlopen(QUEUE_URL, timeout=2) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ConnectionRefusedError):
            return {'state': 'idle', 'running': 0, 'pending': 0, 'detail': 'connection refused (no server)'}
        return {'state': 'unknown', 'detail': f'unreachable: {exc.reason}'}
    except Exception as exc:
        return {'state': 'unknown', 'detail': f'{type(exc).__name__}: {exc}'}
    running = len(data.get('queue_running', data.get('running', [])) or [])
    pending = len(data.get('queue_pending', data.get('pending', [])) or [])
    return {'state': 'busy' if running or pending else 'idle', 'running': running, 'pending': pending,
            'detail': QUEUE_URL}


def check_checkpoints():
    base = ACE_SOURCE/'checkpoints'
    files = {name: (base/name).is_file() for name in REQUIRED_CHECKPOINTS}
    return {'dir': str(base), 'all_present': all(files.values()), 'files': files}


def collect():
    free_gib = round(shutil.disk_usage(ROOT).free/2**30, 2)
    mps = probe_mps()
    ffmpeg = shutil.which('ffmpeg') or shutil.which('ffmpeg', path='/opt/homebrew/bin')
    ffprobe = shutil.which('ffprobe') or shutil.which('ffprobe', path='/opt/homebrew/bin')
    report = {
        'mps': mps['available'],
        'mps_detail': mps,
        'disk_free_gib': free_gib,
        'video_queue': check_video_queue(),
        'ace_python': {'path': str(ACE_PYTHON), 'exists': ACE_PYTHON.is_file()},
        'checkpoints': check_checkpoints(),
        'ffmpeg': {'ffmpeg': ffmpeg, 'ffprobe': ffprobe, 'exists': bool(ffmpeg and ffprobe)},
    }
    problems = []
    if free_gib < MIN_DISK_GIB:
        problems.append(f'disk free {free_gib} GiB < {MIN_DISK_GIB} GiB')
    if not mps['available']:
        problems.append(f'MPS unavailable ({mps["detail"]})')
    report['problems'] = problems
    report['ok'] = not problems
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true', help='print one JSON object')
    args = parser.parse_args()
    report = collect()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f'MPS            : {report["mps"]}  ({report["mps_detail"]["detail"]})')
        print(f'Disk free      : {report["disk_free_gib"]} GiB (need {MIN_DISK_GIB})')
        queue = report['video_queue']
        print(f'Video queue    : {queue["state"]}  ({queue["detail"]})')
        print(f'ACE python     : {report["ace_python"]["exists"]}  {report["ace_python"]["path"]}')
        print(f'Checkpoints    : {"all present" if report["checkpoints"]["all_present"] else "MISSING"}')
        print(f'ffmpeg/ffprobe : {report["ffmpeg"]["exists"]}')
        print('READY' if report['ok'] else 'NOT READY: ' + '; '.join(report['problems']))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
