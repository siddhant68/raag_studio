"""New original ensemble piece, using the previously established native local API."""
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
engine = root.parents[1] / 'tools/ace-step-1.5'
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
caption = (root / 'caption.txt').read_text().strip()
lyrics = (root / 'wordless_vocals.txt').read_text().strip()
assert len(caption) <= 512

def safe(value):
    if isinstance(value, torch.Tensor):
        return {'shape': list(value.shape), 'dtype': str(value.dtype)}
    return str(value)

for index, seed in enumerate([24102601, 24102602], 1):
    out = root / 'takes' / f'take_{index:02d}_{seed}'
    out.mkdir(parents=True, exist_ok=False)
    params = GenerationParams(task_type='text2music',
        instruction=TASK_INSTRUCTIONS['text2music'], caption=caption, lyrics=lyrics,
        instrumental=False, vocal_language='en', bpm=88, keyscale='D major',
        timesignature='4', duration=132, inference_steps=8, seed=seed,
        thinking=False, use_cot_metas=False, use_cot_caption=False,
        use_cot_language=False, use_cot_lyrics=False,
        enable_normalization=True, normalization_db=-1.5,
        fade_in_duration=.08, fade_out_duration=3.0)
    config = GenerationConfig(batch_size=1, use_random_seed=False,
                              seeds=[seed], audio_format='wav')
    (out / 'request.json').write_text(json.dumps({
        'params': dataclasses.asdict(params), 'config': dataclasses.asdict(config),
        'engine': str(engine)}, indent=2, ensure_ascii=False))
    start = time.time()
    print(f'Generating Daylight take {index}, seed {seed}', flush=True)
    result = generate_music(handler, lm, params, config, save_dir=str(out))
    summary = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else vars(result)
    summary['elapsed_seconds'] = time.time() - start
    (out / 'result.json').write_text(json.dumps(summary, indent=2, default=safe))
    print(json.dumps({'take': str(out), 'success': summary.get('success'),
                      'error': summary.get('error'), 'elapsed_seconds': summary['elapsed_seconds'],
                      'audios': [x['path'] for x in summary.get('audios', [])]}), flush=True)
    if not summary.get('success'):
        raise RuntimeError(str(summary.get('error')))
