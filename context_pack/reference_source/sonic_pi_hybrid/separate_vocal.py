"""Isolate the generated voice before combining it with the fixed Sonic Pi backing."""
import json,time
from pathlib import Path
import numpy as np,soundfile as sf,torch,torchaudio

root=Path(__file__).resolve().parent
torch.set_num_threads(4)
model_path=root.parents[1]/'tools/hdemucs/hdemucs_high_trained.pt'
bundle=torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS
model=bundle._model_factory_func()
model.load_state_dict(torch.load(model_path,map_location='cpu',weights_only=True))
model.eval()
take=root/'takes/vocal_01_23102601'
source=Path(json.loads((take/'result.json').read_text())['audios'][0]['path'])
if not source.exists():source=take/source.name
y,sr=sf.read(source,dtype='float32',always_2d=True)
x=torch.from_numpy(y.T.copy())
if sr!=bundle.sample_rate:x=torchaudio.functional.resample(x,sr,bundle.sample_rate)
# Standardize once, then overlap chunks so cut boundaries are blended.
mean=x.mean();std=x.std().clamp_min(1e-6)
x=(x-mean)/std
size=round(8.0*bundle.sample_rate);overlap=round(1.0*bundle.sample_rate)
step=size-overlap
output=torch.zeros_like(x);weights=torch.zeros(x.shape[-1])
start=time.time()
with torch.inference_mode():
 for offset in range(0,x.shape[-1],step):
  chunk=x[:,offset:offset+size];n=chunk.shape[-1]
  if n<size:chunk=torch.nn.functional.pad(chunk,(0,size-n))
  stems=model(chunk.unsqueeze(0))[0]
  voice=stems[model.sources.index('vocals'),:,:n]
  w=torch.ones(n)
  fade=min(overlap,n)
  if offset>0:w[:fade]=torch.linspace(.001,1,fade)
  if offset+n<x.shape[-1]:w[-fade:]=torch.linspace(1,.001,fade)
  output[:,offset:offset+n]+=voice*w
  weights[offset:offset+n]+=w
  print('Separated',round((offset+n)/bundle.sample_rate,1),'seconds',flush=True)
output=output/weights.clamp_min(1e-6)*std
if bundle.sample_rate!=48000:output=torchaudio.functional.resample(output,bundle.sample_rate,48000)
sf.write(root/'Vocal_Isolated.wav',output.T.numpy(),48000,subtype='PCM_24')
(root/'separation.json').write_text(json.dumps({'source':str(source),
 'model':'torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS','torch':torch.__version__,
 'torchaudio':torchaudio.__version__,'device':'cpu','chunk_seconds':8,
 'overlap_seconds':1,'elapsed_seconds':time.time()-start,
 'limit':'Separation removes accompaniment; it does not repair mispronounced words.'},indent=2))
print('Vocal separation complete',time.time()-start,flush=True)
