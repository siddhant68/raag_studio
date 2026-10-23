"""Render two distinct original bansuri-led pieces with the established local engine."""
import argparse
import dataclasses
import json
import os
import time
from pathlib import Path
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                  TOKENIZERS_PARALLELISM='false', MPLCONFIGDIR='/tmp/acestep-matplotlib',
                  OMP_NUM_THREADS='4')
import torch
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import generate_music, GenerationParams, GenerationConfig
from acestep.constants import TASK_INSTRUCTIONS

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--track')
parser.add_argument('--variant', default='native')
parser.add_argument('--seed', type=int)
parser.add_argument('--caption-file')
args = parser.parse_args()
engine = root.parents[1]/'tools/ace-step-1.5'
assert torch.backends.mps.is_available(), 'Native MPS execution required'
torch.set_num_threads(4)
handler = AceStepHandler()
status, ok = handler.initialize_service(project_root=str(engine),
    config_path='acestep-v15-turbo', device='mps', use_flash_attention=False,
    compile_model=False, offload_to_cpu=False, offload_dit_to_cpu=False)
print(status, flush=True)
if not ok:
    raise RuntimeError(status)
lm = LLMHandler()

def safe(value):
    if isinstance(value, torch.Tensor):
        return {'shape': list(value.shape), 'dtype': str(value.dtype)}
    return str(value)

for track in json.loads((root/'tracks.json').read_text()):
    if args.track and track['id'] != args.track:
        continue
    if args.seed is not None:
        track['seed'] = args.seed
    if args.caption_file:
        track['caption'] = Path(args.caption_file).read_text().strip()
    assert len(track['caption']) <= 512
    out = root/track['id']/args.variant
    out.mkdir(parents=True, exist_ok=False)
    params = GenerationParams(task_type='text2music',
        instruction=TASK_INSTRUCTIONS['text2music'], caption=track['caption'],
        lyrics='[Instrumental]', instrumental=True, vocal_language='en',
        bpm=track['bpm'], keyscale=track['key'], timesignature='4',
        duration=track['duration'], inference_steps=8, seed=track['seed'],
        thinking=False, use_cot_metas=False, use_cot_caption=False,
        use_cot_language=False, use_cot_lyrics=False,
        enable_normalization=True, normalization_db=-1.5,
        fade_in_duration=.08, fade_out_duration=3.0)
    config = GenerationConfig(batch_size=1, use_random_seed=False,
                              seeds=[track['seed']], audio_format='wav')
    (out/'request.json').write_text(json.dumps({
        'params': dataclasses.asdict(params), 'config': dataclasses.asdict(config),
        'engine': str(engine)}, indent=2))
    start = time.time()
    print('Generating '+track['title'], flush=True)
    result = generate_music(handler, lm, params, config, save_dir=str(out))
    summary = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else vars(result)
    summary['elapsed_seconds'] = time.time()-start
    (out/'result.json').write_text(json.dumps(summary, indent=2, default=safe))
    print(json.dumps({'track': track['title'], 'success': summary.get('success'),
                      'error': summary.get('error'), 'elapsed_seconds': summary['elapsed_seconds'],
                      'audios': [x['path'] for x in summary.get('audios', [])]}), flush=True)
    if not summary.get('success'):
        raise RuntimeError(str(summary.get('error')))
