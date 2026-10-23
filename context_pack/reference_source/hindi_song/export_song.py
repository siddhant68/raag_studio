"""Master a selected sung take and retain its source and objective checks."""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
import soundfile as sf

p=argparse.ArgumentParser()
p.add_argument('--take',required=True)
p.add_argument('--name',default='Thodi_Der_Aur')
a=p.parse_args()
root=Path(__file__).resolve().parent
take=root/'takes'/a.take
r=json.loads((take/'result.json').read_text())
assert r['success']
source=Path(r['audios'][0]['path'])
if not source.exists():source=take/source.name
ffmpeg='/opt/homebrew/bin/ffmpeg'
def run(args):
    return subprocess.run([ffmpeg,'-hide_banner','-y',*map(str,args)],
        check=True,capture_output=True,text=True)
def parse(log):return json.JSONDecoder().raw_decode(log[log.rfind('{'):])[0]

m=parse(run(['-i',source,'-af','loudnorm=I=-14.5:TP=-1.5:LRA=14:print_format=json','-f','null','-']).stderr)
f=('loudnorm=I=-14.5:TP=-1.5:LRA=14:linear=true:print_format=json'
   f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
   f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
wav=root/(a.name+'.wav')
master=run(['-i',source,'-af',f,'-ar','48000','-c:a','pcm_s24le',wav])
run(['-i',wav,'-c:a','libmp3lame','-b:a','320k','-metadata','title=Thodi Der Aur',
     '-metadata','comment=Original Hindi romantic AI-sung demo',root/(a.name+'.mp3')])
y,sr=sf.read(wav,dtype='float32',always_2d=True)
assert np.isfinite(y).all() and abs(y).max()<1
report={'selected_take':a.take,'native_audio':str(source),'duration_seconds':len(y)/sr,
    'sample_rate':sr,'channels':y.shape[1],'clipped_samples':int(np.sum(abs(y)>=1)),
    'peak_dbfs':float(20*np.log10(abs(y).max())),'normalization':parse(master.stderr)}
(root/(a.name+'_checks.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
