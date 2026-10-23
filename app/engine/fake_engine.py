"""FAKE engine for tests only. Selected by RAAG_ENGINE=fake; never produces real music.

Same command line, same JSONL events, same OUT_DIR protocol as run_takes.py
(see REQUEST_CONTRACT.md), but each "take" is a plain sine tone written by ffmpeg.
Every artefact says so: result.json has engine.fake = true, the audio carries a
"FAKE ENGINE" comment tag, and the API labels every response engine:"fake".

    python fake_engine.py REQUEST_JSON OUT_DIR

Test switches (environment):
  RAAG_FAKE_LOAD_S=0      seconds to "load the model"
  RAAG_FAKE_TAKE_S=0.2    seconds per take
  RAAG_FAKE_BAD_FIRST=1   make take 1 of a first attempt too short (technical failure, to test the retry)
  RAAG_FAKE_FAIL=1        fail with take_failed on take 1 (exit 4)
  RAAG_FAKE_IGNORE_TERM=1 ignore SIGTERM (to test the SIGKILL escalation)
"""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def emit(event, **fields):
    print(json.dumps({'event': event, 'ts': now_iso(), **fields}), flush=True)


def ffmpeg():
    return shutil.which('ffmpeg') or shutil.which('ffmpeg', path='/opt/homebrew/bin') or 'ffmpeg'


def write_sine(path, seed, seconds, fmt):
    freq = 200 + seed % 300
    codec = ['-c:a', 'flac', '-sample_fmt', 's32'] if fmt == 'flac' else ['-c:a', 'pcm_s16le']
    cmd = [ffmpeg(), '-y', '-v', 'error', '-f', 'lavfi', '-i', f'sine=frequency={freq}:sample_rate=48000:duration={seconds}',
           '-af', 'volume=2,pan=stereo|c0=c0|c1=c0', '-ar', '48000', *codec,
           '-metadata', 'comment=FAKE ENGINE TEST AUDIO (not a real render)', str(path)]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    request_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2]).absolute()
    request_bytes = request_path.read_bytes()
    request = json.loads(request_bytes)
    if not out_dir.name.endswith('.partial') or out_dir.exists():
        emit('error', code='invalid_request', message=f'OUT_DIR must be a fresh *.partial path: {out_dir}',
             problems=['bad out dir'])
        return 2
    params, seeds = request['params'], request['seeds']
    meta = request.get('meta') or {}
    fmt = request.get('audio_format', 'flac')
    out_dir.mkdir()
    (out_dir/'request.json').write_bytes(request_bytes)
    log = (out_dir/'engine.log').open('a')
    log.write(f'{now_iso()} [fake_engine] FAKE ENGINE: test audio only\n')
    log.flush()
    effective = dict(params, guidance_scale=1.0)
    result = {'schema': 'raag-engine-result/1', 'status': 'running', 'started_at': now_iso(),
              'request_sha256': hashlib.sha256(request_bytes).hexdigest(), 'seeds': seeds, 'meta': meta,
              'requested_params': params, 'effective_params': effective,
              'notes': ['FAKE ENGINE: sine tones for tests, not music'],
              'engine': {'source': 'fake', 'checkpoint': 'fake', 'device': 'fake', 'turbo': True, 'fake': True},
              'network_attempts': [], 'takes': []}

    def save(**changes):
        result.update(changes)
        tmp = out_dir/'result.json.tmp'
        tmp.write_text(json.dumps(result, indent=2))
        os.replace(tmp, out_dir/'result.json')

    def on_term(signum, _frame):
        save(status='terminated', finished_at=now_iso())
        emit('error', code='terminated', message=f'received {signal.Signals(signum).name}', partial_dir=str(out_dir))
        os._exit(128 + signum)

    if os.environ.get('RAAG_FAKE_IGNORE_TERM') == '1':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    else:
        signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    save()

    started = time.time()
    emit('model_loading', checkpoint='fake', out_dir=str(out_dir))
    time.sleep(float(os.environ.get('RAAG_FAKE_LOAD_S', '0')))
    load_s = round(time.time() - started, 3)
    emit('model_ready', load_s=load_s, device='fake', turbo=True, peak_rss_mb=1.0)
    takes = []
    for index, seed in enumerate(seeds, 1):
        emit('take_start', index=index, seed=seed, of=len(seeds))
        t0 = time.time()
        time.sleep(float(os.environ.get('RAAG_FAKE_TAKE_S', '0.2')))
        if os.environ.get('RAAG_FAKE_FAIL') == '1' and index == 1:
            save(status='failed', finished_at=now_iso(), error={'code': 'take_failed', 'message': 'fake failure'})
            emit('error', code='take_failed', message=f'seed {seed}: fake failure requested by RAAG_FAKE_FAIL')
            return 4
        seconds = float(params['duration'])
        if os.environ.get('RAAG_FAKE_BAD_FIRST') == '1' and index == 1 and not meta.get('retry'):
            seconds = max(1.0, seconds - 2.0)          # breaks the duration check on purpose
        name = f'take_{index:02d}_s{seed}.{fmt}'
        write_sine(out_dir/name, seed, seconds, fmt)
        wall = round(time.time() - t0, 3)
        record = {'index': index, 'seed': seed, 'file': name, 'format': fmt, 'bytes': (out_dir/name).stat().st_size,
                  'sample_rate': 48000, 'channels': 2, 'duration_s': seconds, 'wall_s': wall, 'pipeline_s': wall,
                  'time_costs': {}, 'notes': ['fake']}
        takes.append(record)
        save(takes=takes)
        emit('take_done', index=index, seed=seed, path=name, format=fmt, duration_s=seconds, wall_s=wall,
             pipeline_s=wall, bytes=record['bytes'])
    total = round(time.time() - started, 3)
    save(status='ok', finished_at=now_iso(), total_wall_s=total, model_load_s=load_s, peak_rss_mb=1.0)
    emit('done', takes=len(takes), total_wall_s=total, model_load_s=load_s, peak_rss_mb=1.0, partial_dir=str(out_dir))
    return 0


if __name__ == '__main__':
    sys.exit(main())
