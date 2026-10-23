"""Independent local ASR evidence, without priming with the intended lyrics."""
import json, os, time
from pathlib import Path
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import mlx_whisper

root=Path(__file__).resolve().parent
model=root.parents[1]/'tools/whisper-small-mlx'
for take in sorted((root/'takes').iterdir()):
    if not (take/'result.json').exists():continue
    if (take/'transcription.json').exists():continue
    info=json.loads((take/'result.json').read_text())
    audio=info['audios'][0]['path']
    start=time.time()
    result=mlx_whisper.transcribe(audio,path_or_hf_repo=str(model),
        language='hi',verbose=False,temperature=0,condition_on_previous_text=False)
    result['elapsed_seconds']=time.time()-start
    result['limits']='Unprompted local ASR with language specified as Hindi. Singing transcription is fallible; not human listening approval.'
    (take/'transcription.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str))
    print(take.name,result['text'],flush=True)
