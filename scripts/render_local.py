"""Replay a preserved text-to-music request into a fresh local run directory.

Dry-run is lightweight. The actual branch requires the existing native ACE
environment and was not exercised while preparing this handoff.
"""
import argparse
import dataclasses
import datetime
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
RECIPES = ('yamuna', 'daylight', 'thodi', 'moonlit')
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--recipe', choices=RECIPES, required=True)
p.add_argument('--seed', type=int)
p.add_argument('--output', type=Path)
p.add_argument('--engine', type=Path, default=ROOT.parent/'tools/ace-step-1.5')
p.add_argument('--dry-run', action='store_true')
a = p.parse_args()
request_path = ROOT/'context_pack/recipes'/a.recipe/'request.json'
request = json.loads(request_path.read_text())
params_data, config_data = dict(request['params']), dict(request['config'])
if a.seed is not None:
    params_data['seed'] = a.seed
    config_data['seeds'] = [a.seed]
config_data.update(batch_size=1, use_random_seed=False, audio_format='wav')
assert params_data['task_type'] == 'text2music'
assert len(params_data['caption']) <= 512, 'Caption exceeds the current adapter budget'
assert len(params_data['lyrics']) <= 4096, 'Lyrics exceed the current adapter budget'
assert not params_data.get('thinking')
assert not any(params_data.get(k) for k in ['use_cot_caption','use_cot_lyrics','use_cot_language','use_cot_metas'])
assert (a.engine/'checkpoints/acestep-v15-turbo').is_dir(), 'Installed turbo weights not found'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out = a.output or ROOT/'runs'/f'{stamp}_{a.recipe}_{uuid.uuid4().hex[:8]}'
out = out.resolve()
if not out.is_relative_to((ROOT/'runs').resolve()):
    raise SystemExit('Output must be a fresh folder under this project\'s runs/')
if out.exists():
    raise SystemExit('Refusing to overwrite an existing run')
resolved = {'source_recipe':str(request_path),'engine':str(a.engine.resolve()),
            'output':str(out),'params':params_data,'config':config_data,
            'mode':'dry-run' if a.dry_run else 'real local generation'}
if a.dry_run:
    print(json.dumps(resolved,indent=2,ensure_ascii=False))
    raise SystemExit(0)

os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                  TOKENIZERS_PARALLELISM='false',OMP_NUM_THREADS='4',
                  MPLCONFIGDIR=str(ROOT/'data/matplotlib'))
sys.path.insert(0,str(a.engine.resolve()))
import torch
if not torch.backends.mps.is_available():
    raise SystemExit('Native MPS unavailable in this execution surface; no CPU render started')
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import generate_music, GenerationParams, GenerationConfig

torch.set_num_threads(4)
out.mkdir(parents=True,exist_ok=False)
(out/'request.json').write_text(json.dumps(resolved,indent=2,ensure_ascii=False))
started = time.time()
try:
    handler = AceStepHandler()
    status,ok = handler.initialize_service(project_root=str(a.engine.resolve()),
        config_path='acestep-v15-turbo',device='mps',use_flash_attention=False,
        compile_model=False,offload_to_cpu=False,offload_dit_to_cpu=False)
    (out/'initialization.txt').write_text(str(status))
    print(status,flush=True)
    if not ok:
        raise RuntimeError(str(status))
    result = generate_music(handler,LLMHandler(),GenerationParams(**params_data),
                            GenerationConfig(**config_data),save_dir=str(out))
    summary = dataclasses.asdict(result) if dataclasses.is_dataclass(result) else vars(result)
    def safe(value):
        if isinstance(value,torch.Tensor):
            return {'shape':list(value.shape),'dtype':str(value.dtype)}
        return str(value)
    summary['elapsed_seconds'] = time.time()-started
    (out/'result.json').write_text(json.dumps(summary,indent=2,default=safe))
    if not summary.get('success'):
        raise RuntimeError(str(summary.get('error')))
    print(json.dumps({'success':True,'output':str(out),
                      'audio':[x['path'] for x in summary.get('audios',[])]}),flush=True)
except Exception as exc:
    (out/'failure.json').write_text(json.dumps({'error':str(exc),
        'elapsed_seconds':time.time()-started},indent=2))
    raise
