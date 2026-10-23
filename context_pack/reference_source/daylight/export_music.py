"""Finish one coherent performance without splicing unrelated takes."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf

p = argparse.ArgumentParser()
p.add_argument('--take', default='take_01_24102601')
a = p.parse_args()
root = Path(__file__).resolve().parent
result = json.loads((root/'takes'/a.take/'result.json').read_text())
assert result['success']
native = Path(result['audios'][0]['path'])
ffmpeg = '/opt/homebrew/bin/ffmpeg'

def run(args):
    return subprocess.run([ffmpeg, '-hide_banner', '-y', *map(str,args)],
                          check=True, capture_output=True, text=True)

analysis = run(['-i',native,'-af','loudnorm=I=-16:TP=-1.5:LRA=16:print_format=json',
                '-f','null','-'])
measure = json.JSONDecoder().raw_decode(analysis.stderr[analysis.stderr.rfind('{'):])[0]
filt = ('loudnorm=I=-16:TP=-1.5:LRA=16:linear=true:print_format=json'
        f":measured_I={measure['input_i']}:measured_TP={measure['input_tp']}"
        f":measured_LRA={measure['input_lra']}:measured_thresh={measure['input_thresh']}"
        f":offset={measure['target_offset']}")
wav = root/'Daylight.wav'
master = run(['-i',native,'-af',filt,'-ar','48000','-c:a','pcm_s24le',
              '-metadata','title=Daylight',wav])
mp3 = root/'Daylight.mp3'
run(['-i',wav,'-c:a','libmp3lame','-b:a','320k',
     '-metadata','title=Daylight',
     '-metadata','comment=Original AI-generated ensemble with wordless chorus',mp3])
y,sr = sf.read(wav,dtype='float32',always_2d=True)
assert np.isfinite(y).all() and abs(y).max()<1
decoded = run(['-i',mp3,'-f','null','-'])
check = run(['-i',mp3,'-af','loudnorm=I=-16:TP=-1.5:LRA=16:print_format=json','-f','null','-'])
checks = {'selected_take':a.take,'native':str(native),'duration_seconds':len(y)/sr,
          'sample_rate':sr,'channels':y.shape[1],'finite':True,
          'clipped_samples':int((abs(y)>=1).sum()),
          'first_pass':measure,
          'master':json.JSONDecoder().raw_decode(master.stderr[master.stderr.rfind('{'):])[0],
          'decoded_mp3':json.JSONDecoder().raw_decode(check.stderr[check.stderr.rfind('{'):])[0]}
(root/'master_checks.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
