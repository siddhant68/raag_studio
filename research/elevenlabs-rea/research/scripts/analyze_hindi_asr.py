"""Local-only exploratory ASR; no lyric prompt and no model downloads."""
import os
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
import sys,json,pathlib,hashlib,time,importlib.metadata
import mlx_whisper
root=pathlib.Path(__file__).resolve().parents[2]
model=root.parent/'tools/whisper-small-mlx'
assert (model/'weights.npz').is_file() and (model/'config.json').is_file()
for item in sys.argv[1:]:
 audio=(root/item).resolve();eid=audio.name.split('-')[0];out=root/'experiments'/eid;out.mkdir(parents=True,exist_ok=True)
 if (out/'asr_hi_unprompted.json').exists():print(eid,'already analyzed');continue
 started=time.time()
 result=mlx_whisper.transcribe(str(audio),path_or_hf_repo=str(model),language='hi',task='transcribe',temperature=0.0,initial_prompt=None,condition_on_previous_text=False,word_timestamps=True,verbose=False)
 result['analysis_metadata']={'method':'mlx-whisper local multilingual small; Hindi language selected; no supplied lyrics or initial prompt','audio_file':str(audio),'audio_sha256':hashlib.sha256(audio.read_bytes()).hexdigest(),'model_path':str(model),'model_weights_sha256':hashlib.sha256((model/'weights.npz').read_bytes()).hexdigest(),'model_config_sha256':hashlib.sha256((model/'config.json').read_bytes()).hexdigest(),'package_version':importlib.metadata.version('mlx-whisper'),'decode_options':{'language':'hi','task':'transcribe','temperature':0.0,'initial_prompt':None,'condition_on_previous_text':False,'word_timestamps':True},'elapsed_s':time.time()-started,'limitations':['ASR on mixed singing may hallucinate or omit words.','Hindi output does not establish native diction.','ASR does not establish melody, hook quality, identity or listener enjoyment.','Segment and word boundaries are model estimates.']}
 (out/'asr_hi_unprompted.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 lines=[f"{s['start']:.2f}–{s['end']:.2f}: {s['text']}" for s in result['segments']]
 (out/'asr_hi_unprompted.txt').write_text('\n'.join(lines)+'\n')
 print(eid,'elapsed',round(time.time()-started,2));print('\n'.join(lines))
