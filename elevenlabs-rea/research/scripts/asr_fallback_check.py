import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import mlx_whisper,json,pathlib,time,sys,hashlib,importlib.metadata
root=pathlib.Path(__file__).resolve().parents[2]
a=root/(sys.argv[1] if len(sys.argv)>1 else 'audio/E01-original.mp3');m=root.parent/'tools/whisper-small-mlx'
eid=a.name.split('-')[0]
t=time.time()
r=mlx_whisper.transcribe(str(a),path_or_hf_repo=str(m),language='hi',task='transcribe',initial_prompt=None,condition_on_previous_text=False,verbose=False)
r['analysis_metadata']={'reason':'Default temperature fallback prevents previously observed degenerate repeated-token loops; no initial lyric prompt','audio_file':str(a),'audio_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'model_path':str(m),'model_weights_sha256':hashlib.sha256((m/'weights.npz').read_bytes()).hexdigest(),'mlx_whisper_version':importlib.metadata.version('mlx-whisper'),'initial_prompt':None,'condition_on_previous_text':False,'word_timestamps':False,'elapsed_s':time.time()-t,'limitation':'Same small model; not independent listening or gold transcript.'}
p=root/'experiments'/eid/(sys.argv[2] if len(sys.argv)>2 else 'asr_hi_fallback.json');p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('\n'.join(f"{s['start']:.2f}–{s['end']:.2f}: {s['text']}" for s in r['segments']))
