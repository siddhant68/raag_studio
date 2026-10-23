"""Original Hindi text-to-music, using the installed local ACE-Step turbo."""
import argparse, dataclasses, json, os, time
from pathlib import Path

os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
    TOKENIZERS_PARALLELISM='false', MPLCONFIGDIR='/tmp/acestep-matplotlib',
    OMP_NUM_THREADS='4')
import torch
from acestep.handler import AceStepHandler
from acestep.llm_inference import LLMHandler
from acestep.inference import generate_music, GenerationParams, GenerationConfig
from acestep.constants import TASK_INSTRUCTIONS

p=argparse.ArgumentParser()
p.add_argument('--seeds',type=int,nargs='+',default=[22102611,22102612])
p.add_argument('--duration',type=float,default=152)
p.add_argument('--lyrics-file',default='lyrics_hi.txt')
p.add_argument('--take-prefix',default='take')
a=p.parse_args()
root=Path(__file__).resolve().parent
workspace=root.parents[1]
engine=workspace/'tools/ace-step-1.5'
caption=(root/'caption.txt').read_text().strip()
lyrics=(root/a.lyrics_file).read_text().strip()
assert len(caption)<=512
assert torch.backends.mps.is_available(), 'Run in the native host environment with MPS.'
torch.set_num_threads(4)
handler=AceStepHandler()
status,ok=handler.initialize_service(project_root=str(engine),
    config_path='acestep-v15-turbo',device='mps',use_flash_attention=False,
    compile_model=False,offload_to_cpu=False,offload_dit_to_cpu=False)
print(status,flush=True)
if not ok:raise RuntimeError(status)
lm=LLMHandler()  # Optional 5Hz LM is not installed; metadata is specified directly.

def safe(o):
    if isinstance(o,torch.Tensor):return {'shape':list(o.shape),'dtype':str(o.dtype)}
    return str(o)

for index,seed in enumerate(a.seeds,1):
    out=root/'takes'/f'{a.take_prefix}_{index:02d}_{seed}'
    out.mkdir(parents=True,exist_ok=False)
    params=GenerationParams(task_type='text2music',
        instruction=TASK_INSTRUCTIONS['text2music'],caption=caption,lyrics=lyrics,
        instrumental=False,vocal_language='hi',bpm=76,keyscale='D major',
        timesignature='4',duration=a.duration,inference_steps=8,seed=seed,
        thinking=False,use_cot_metas=False,use_cot_caption=False,
        use_cot_language=False,use_cot_lyrics=False,
        enable_normalization=True,normalization_db=-1.5,
        fade_in_duration=.04,fade_out_duration=2.0)
    config=GenerationConfig(batch_size=1,use_random_seed=False,seeds=[seed],audio_format='wav')
    (out/'request.json').write_text(json.dumps({'params':dataclasses.asdict(params),
        'config':dataclasses.asdict(config),'engine':str(engine)},indent=2,ensure_ascii=False))
    start=time.time()
    print('Generating original Hindi song',seed,flush=True)
    result=generate_music(handler,lm,params,config,save_dir=str(out))
    summary=dataclasses.asdict(result) if dataclasses.is_dataclass(result) else vars(result)
    summary['elapsed_seconds']=time.time()-start
    (out/'result.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=safe))
    print(json.dumps({'take':str(out),'success':summary.get('success'),
        'error':summary.get('error'),'elapsed_seconds':summary['elapsed_seconds'],
        'audios':[x['path'] for x in summary.get('audios',[])]}),flush=True)
    if not summary.get('success'):raise RuntimeError(str(summary.get('error')))
