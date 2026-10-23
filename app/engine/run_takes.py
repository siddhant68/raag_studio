"""Render N takes of one ACE-Step request in a single process.

Usage (run with the shared ACE python, never with the API python):

    ACE_PYTHON run_takes.py REQUEST_JSON OUT_DIR [--dry-run]

OUT_DIR must be a fresh, non-existing path whose name ends in ".partial". The
script creates it and never renames it; on success the caller renames it.
Events are JSON lines on stdout, everything else goes to OUT_DIR/engine.log.
See REQUEST_CONTRACT.md for the full contract.

--dry-run validates the request and the output path and exits without
importing torch or touching the model.
"""
import argparse
import ast
import gc
import hashlib
import json
import os
import resource
import signal
import socket
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

# Offline and thread settings must be in place before torch/transformers load.
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='4')
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'raag-mplconfig'))

REQUEST_SCHEMA = 'raag-engine-request/1'
RESULT_SCHEMA = 'raag-engine-result/1'
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENGINE = ROOT.parent/'tools/ace-step-1.5'
CHECKPOINT = 'acestep-v15-turbo'
# Weight files this harness needs. ACE's own "main model present" check also
# demands the 5Hz LM (acestep-5Hz-lm-1.7B), which is deliberately not installed.
REQUIRED_WEIGHTS = ('acestep-v15-turbo/model.safetensors', 'vae/diffusion_pytorch_model.safetensors',
                    'Qwen3-Embedding-0.6B/model.safetensors')

MAX_CAPTION = 512
MAX_LYRICS = 4000
MIN_DURATION_S, MAX_DURATION_S = 10, 240   # 240 is the PRD cap until M0 measures it
MAX_SEEDS = 8
TOP_LEVEL_KEYS = {'schema', 'params', 'seeds', 'audio_format', 'meta'}
NO_COT = ('use_cot_metas', 'use_cot_caption', 'use_cot_language', 'use_cot_lyrics')

_events = sys.stdout       # replaced by a private dup of the real stdout in run()
_events_lock = threading.Lock()
_result = None             # ResultFile once the output directory exists


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def emit(event, **fields):
    """One JSON object per line on the real stdout, flushed immediately."""
    line = json.dumps({'event': event, 'ts': now_iso(), **fields}, ensure_ascii=False)
    with _events_lock:
        _events.write(line + '\n')
        _events.flush()


def log(message):
    print(f'{now_iso()} [run_takes] {message}', flush=True)


# ---------------------------------------------------------------- validation

def generation_param_fields(engine):
    """Names of the GenerationParams fields, read from source (no torch import)."""
    tree = ast.parse((engine/'acestep/inference.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == 'GenerationParams':
            return {n.target.id for n in node.body
                    if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    raise RuntimeError('GenerationParams not found in the ACE source')


def validate_request(request, known_fields):
    """Return a list of human-readable problems (empty list = valid)."""
    errors = []
    if not isinstance(request, dict):
        return ['request must be a JSON object']
    if request.get('schema') != REQUEST_SCHEMA:
        errors.append(f'schema must be "{REQUEST_SCHEMA}"')
    extra = sorted(set(request) - TOP_LEVEL_KEYS)
    if extra:
        errors.append(f'unknown top-level keys: {extra}')
    if request.get('audio_format', 'flac') not in ('flac', 'wav'):
        errors.append('audio_format must be "flac" or "wav"')
    if 'meta' in request and not isinstance(request['meta'], dict):
        errors.append('meta must be an object')

    seeds = request.get('seeds')
    if (not isinstance(seeds, list) or not 1 <= len(seeds) <= MAX_SEEDS
            or not all(isinstance(s, int) and not isinstance(s, bool) and 0 <= s < 2**31 for s in seeds)):
        errors.append(f'seeds must be a list of 1..{MAX_SEEDS} integers in [0, 2^31)')
    elif len(set(seeds)) != len(seeds):
        errors.append('seeds must be unique')

    params = request.get('params')
    if not isinstance(params, dict):
        errors.append('params must be an object')
        return errors
    if 'seed' in params:
        errors.append('params must not contain "seed"; use the top-level seeds list')
    unknown = sorted(set(params) - known_fields)
    if unknown:
        errors.append(f'unknown ACE params: {unknown}')
    if params.get('task_type', 'text2music') != 'text2music':
        errors.append('task_type must be "text2music"')
    for key in ('reference_audio', 'src_audio'):
        if params.get(key):
            errors.append(f'{key} must be null (text2music only)')
    caption = params.get('caption')
    if not isinstance(caption, str) or not caption.strip():
        errors.append('caption must be a non-empty string')
    elif len(caption) > MAX_CAPTION:
        errors.append(f'caption is {len(caption)} chars, limit {MAX_CAPTION}')
    lyrics = params.get('lyrics', '')
    if not isinstance(lyrics, str):
        errors.append('lyrics must be a string')
    elif len(lyrics) > MAX_LYRICS:
        errors.append(f'lyrics are {len(lyrics)} chars, limit {MAX_LYRICS}')
    duration = params.get('duration')
    if (isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not MIN_DURATION_S <= duration <= MAX_DURATION_S):
        errors.append(f'duration must be a number in [{MIN_DURATION_S}, {MAX_DURATION_S}] seconds')
    if params.get('thinking', False) is not False:
        errors.append('thinking must be false (the 5Hz LM is not installed)')
    for key in NO_COT:
        if params.get(key, False) is not False:
            errors.append(f'{key} must be false')
    return errors


def validate_out_dir(out_dir):
    if out_dir.name.startswith('.') or not out_dir.name.endswith('.partial'):
        return [f'OUT_DIR name must end in ".partial": {out_dir.name}']
    if out_dir.exists():
        return [f'OUT_DIR already exists (must be fresh): {out_dir}']
    if not out_dir.parent.is_dir():
        return [f'OUT_DIR parent does not exist: {out_dir.parent}']
    return []


def fail_validation(problems):
    emit('error', code='invalid_request', message='; '.join(problems), problems=problems)
    sys.exit(2)


# -------------------------------------------------------------------- result

class ResultFile:
    """result.json, rewritten atomically after every state change."""

    def __init__(self, path, data):
        self.path, self.data, self.lock = path, data, threading.Lock()

    def write(self, **changes):
        with self.lock:
            self.data.update(changes)
            tmp = self.path.with_name('result.json.tmp')
            tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False, default=str))
            os.replace(tmp, self.path)


def peak_rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20, 1)   # bytes on macOS


def checkpoint_listing(engine):
    """(relative path, size, mtime_ns) for every checkpoint file, plus a digest."""
    entries = sorted((str(p.relative_to(engine/'checkpoints')), p.stat().st_size, p.stat().st_mtime_ns)
                     for p in (engine/'checkpoints').rglob('*') if p.is_file())
    return len(entries), hashlib.sha256(json.dumps(entries).encode()).hexdigest()


def block_network(attempts):
    """Refuse every non-loopback TCP connect; record what was tried.

    ACE's initialize_service probes www.google.com and tries a model download
    when it thinks a component is missing. This is the safety net behind the
    in-process patch in run(); a clean run records no attempts.
    """
    loopback = ('127.0.0.1', '::1', 'localhost')
    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex

    def refused(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in loopback:
            attempts.append(f'{address[0]}:{address[1]}')
            log(f'BLOCKED outbound connection to {address[0]}:{address[1]}')
            return True
        return False

    def connect(self, address):
        if refused(self, address):
            raise OSError(101, 'network disabled by run_takes (offline)')
        return real_connect(self, address)

    def connect_ex(self, address):
        return 101 if refused(self, address) else real_connect_ex(self, address)

    socket.socket.connect, socket.socket.connect_ex = connect, connect_ex


def install_term_watcher(on_term):
    """Handle SIGTERM/SIGINT on a dedicated thread.

    The signals are blocked in the main thread (and every thread it starts) so a
    long native torch call cannot delay the handler.
    """
    wanted = {signal.SIGTERM, signal.SIGINT}
    signal.pthread_sigmask(signal.SIG_BLOCK, wanted)

    def watch():
        on_term(signal.sigwait(wanted))
    threading.Thread(target=watch, daemon=True, name='term-watcher').start()


# ----------------------------------------------------------------------- run

def render_take(index, seed, params_data, audio_format, out_dir, ace):
    """Render one seed; return the per-take record. Raises RuntimeError on failure."""
    params = ace['GenerationParams'](**params_data, seed=seed)
    config = ace['GenerationConfig'](batch_size=1, use_random_seed=False,
                                     seeds=[seed], audio_format=audio_format)
    started = time.time()
    result = ace['generate_music'](ace['handler'], ace['lm'], params, config, save_dir=str(out_dir))
    if not result.success or not result.audios:
        raise RuntimeError(str(result.error or result.status_message or 'generation failed'))
    audio = result.audios[0]
    tensor, sample_rate = audio['tensor'], audio['sample_rate']
    fmt, notes = audio_format, []
    if not audio['path'] or not Path(audio['path']).is_file():
        # Engine could not write the requested format: fall back to WAV.
        from acestep.audio_utils import AudioSaver
        audio['path'] = AudioSaver(default_format='wav').save_audio(
            tensor, str(out_dir/f'{audio["key"]}.wav'), sample_rate=sample_rate,
            format='wav', channels_first=True)
        fmt = 'wav'
        notes.append(f'engine could not write {audio_format}; wrote wav instead')
    final = out_dir/f'take_{index:02d}_s{seed}.{fmt}'
    os.replace(audio['path'], final)
    costs = result.extra_outputs.get('time_costs', {})
    record = {
        'index': index, 'seed': seed, 'file': final.name, 'format': fmt,
        'bytes': final.stat().st_size, 'sample_rate': sample_rate,
        'channels': int(tensor.shape[0]), 'duration_s': round(tensor.shape[-1]/sample_rate, 3),
        'wall_s': round(time.time() - started, 3),
        'pipeline_s': round(costs.get('pipeline_total_time', 0.0), 3),
        'time_costs': costs, 'engine_key': audio['key'], 'notes': notes,
    }
    del result, audio, tensor
    return record


def run(args, request, request_bytes, out_dir):
    global _events, _result
    engine = args.engine.resolve()
    params_data = dict(request['params'])
    seeds = request['seeds']
    audio_format = request.get('audio_format', 'flac')

    out_dir.mkdir(parents=False, exist_ok=False)
    # Keep stdout clean for events: library prints and logs go to engine.log.
    _events = os.fdopen(os.dup(1), 'w', buffering=1)
    log_fd = os.open(out_dir/'engine.log', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    (out_dir/'request.json').write_bytes(request_bytes)

    result = ResultFile(out_dir/'result.json', {
        'schema': RESULT_SCHEMA, 'status': 'running', 'started_at': now_iso(),
        'request_sha256': hashlib.sha256(request_bytes).hexdigest(),
        'requested_params': params_data, 'seeds': seeds, 'audio_format': audio_format,
        'meta': request.get('meta'), 'engine': {'source': str(engine), 'checkpoint': CHECKPOINT},
        'takes': [], 'notes': [],
    })
    result.write()
    _result = result

    def on_term(signum):
        name = signal.Signals(signum).name
        log(f'received {name}; exiting immediately, leaving {out_dir.name}')
        result.write(status='terminated', finished_at=now_iso(), peak_rss_mb=peak_rss_mb())
        emit('error', code='terminated', message=f'received {name}', partial_dir=str(out_dir))
        os._exit(128 + signum)

    install_term_watcher(on_term)
    run_started = time.time()

    def fail(code, message):
        log(f'{code}: {message}')
        result.write(status='failed', error={'code': code, 'message': message},
                     finished_at=now_iso(), peak_rss_mb=peak_rss_mb())
        emit('error', code=code, message=message)

    missing = [w for w in REQUIRED_WEIGHTS if not (engine/'checkpoints'/w).is_file()]
    if missing:
        fail('missing_checkpoint', f'not found under {engine/"checkpoints"}: {missing}')
        return 3
    network_attempts = []
    block_network(network_attempts)
    listing_before = checkpoint_listing(engine)

    emit('model_loading', checkpoint=CHECKPOINT, out_dir=str(out_dir))
    load_started = time.time()
    sys.path.insert(0, str(engine))
    import torch
    if not torch.backends.mps.is_available():
        fail('mps_unavailable', 'MPS is not available in this process; refusing to fall back to CPU')
        return 3
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.inference import generate_music, GenerationParams, GenerationConfig
    torch.set_num_threads(4)
    # Without the 5Hz LM folder ACE would "auto-download" the main model; tell it
    # the components we actually use are present (in-process, source untouched).
    import acestep.core.generation.handler.init_service_downloads as ace_downloads
    ace_downloads.check_main_model_exists = lambda checkpoint_path=None: True

    handler = AceStepHandler()
    status, ok = handler.initialize_service(
        project_root=str(engine), config_path=CHECKPOINT, device='mps',
        use_flash_attention=False, compile_model=False,
        offload_to_cpu=False, offload_dit_to_cpu=False)
    log(f'initialize_service ok={ok}: {status}')
    if not ok:
        fail('model_load_failed', str(status))
        return 3
    load_s = round(time.time() - load_started, 3)

    turbo = bool(handler.is_turbo_model())
    effective = GenerationParams(**params_data, seed=-1).to_dict()
    effective.pop('seed')
    notes = []
    if turbo and effective['guidance_scale'] != 1.0:
        notes.append(f'turbo model forces guidance_scale {effective["guidance_scale"]} -> 1.0 (no CFG)')
        effective['guidance_scale'] = 1.0
    try:
        resolved_dcw = handler._resolve_dcw_enabled(effective['dcw_enabled'])
        if resolved_dcw != effective['dcw_enabled']:
            notes.append(f'dcw_enabled {effective["dcw_enabled"]} resolved to {resolved_dcw} by the engine')
            effective['dcw_enabled'] = resolved_dcw
    except Exception as exc:                      # private helper; never fatal
        notes.append(f'could not resolve dcw_enabled: {exc}')
    result.write(effective_params=effective, notes=notes, model_load_s=load_s,
                 engine={'source': str(engine), 'checkpoint': CHECKPOINT, 'device': 'mps',
                         'turbo': turbo, 'torch': torch.__version__})
    emit('model_ready', load_s=load_s, device='mps', turbo=turbo, peak_rss_mb=peak_rss_mb())

    ace = {'handler': handler, 'lm': LLMHandler(), 'generate_music': generate_music,
           'GenerationParams': GenerationParams, 'GenerationConfig': GenerationConfig}
    takes = []
    for index, seed in enumerate(seeds, 1):
        emit('take_start', index=index, seed=seed, of=len(seeds))
        try:
            record = render_take(index, seed, params_data, audio_format, out_dir, ace)
        except Exception as exc:
            fail('take_failed', f'seed {seed}: {exc}')
            log(f'take {index} failed')
            import traceback
            traceback.print_exc()
            return 4
        record['peak_rss_mb'] = peak_rss_mb()
        takes.append(record)
        result.write(takes=takes, peak_rss_mb=record['peak_rss_mb'])
        emit('take_done', index=index, seed=seed, path=record['file'], format=record['format'],
             duration_s=record['duration_s'], wall_s=record['wall_s'],
             pipeline_s=record['pipeline_s'], bytes=record['bytes'])
        gc.collect()
        torch.mps.empty_cache()

    listing_after = checkpoint_listing(engine)
    total = round(time.time() - run_started, 3)
    result.write(status='ok', finished_at=now_iso(), total_wall_s=total,
                 checkpoints={'files': listing_before[0], 'unchanged': listing_before == listing_after},
                 network_attempts=network_attempts,
                 peak_rss_mb=peak_rss_mb())
    emit('done', takes=len(takes), total_wall_s=total, model_load_s=load_s,
         peak_rss_mb=peak_rss_mb(), partial_dir=str(out_dir))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('request', type=Path)
    parser.add_argument('out_dir', type=Path)
    parser.add_argument('--dry-run', action='store_true', help='validate only; never imports torch')
    parser.add_argument('--engine', type=Path, default=DEFAULT_ENGINE, help='ACE-Step source (read-only)')
    args = parser.parse_args()

    out_dir = args.out_dir.absolute()
    try:
        request_bytes = args.request.read_bytes()
        request = json.loads(request_bytes)
    except (OSError, ValueError) as exc:
        fail_validation([f'cannot read request JSON: {exc}'])
    problems = validate_out_dir(out_dir)
    if not (args.engine/'acestep/inference.py').is_file():
        fail_validation([f'ACE source not found at {args.engine}'])
    problems += validate_request(request, generation_param_fields(args.engine))
    if problems:
        fail_validation(problems)

    if args.dry_run:
        emit('dry_run_ok', seeds=request['seeds'], duration=request['params']['duration'],
             audio_format=request.get('audio_format', 'flac'), out_dir=str(out_dir),
             torch_imported='torch' in sys.modules)
        return 0
    try:
        return run(args, request, request_bytes, out_dir)
    except SystemExit:
        raise
    except BaseException as exc:
        import traceback
        traceback.print_exc()
        if _result is not None:
            _result.write(status='failed', finished_at=now_iso(),
                          error={'code': 'unexpected', 'message': f'{type(exc).__name__}: {exc}'})
        emit('error', code='unexpected', message=f'{type(exc).__name__}: {exc}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
