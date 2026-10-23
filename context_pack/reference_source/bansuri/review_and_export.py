"""Check the generated flute focus and deliver conservative full-performance masters."""
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from earshot import api

root = Path(__file__).resolve().parent
ffmpeg = '/opt/homebrew/bin/ffmpeg'
report = {'tracks': {}, 'limits': 'Music/voice/instrument descriptions are unvalidated acoustic hints, not tests of virtuosity, divine qualities, exact ornaments, raga, beauty or listener preference.'}
parser = argparse.ArgumentParser()
parser.add_argument('--track')
args = parser.parse_args()
if (root/'review_and_checks.json').exists():
    report = json.loads((root/'review_and_checks.json').read_text())

def run(args):
    return subprocess.run([ffmpeg, '-hide_banner', '-y', *map(str,args)],
                          check=True, capture_output=True, text=True)

def parse(log):
    return json.JSONDecoder().raw_decode(log[log.rfind('{'):])[0]

for track in json.loads((root/'tracks.json').read_text()):
    if args.track and args.track != track['id']:
        continue
    folder = root/track['id']
    result = json.loads((folder/track.get('selected_native','native')/'result.json').read_text())
    assert result['success']
    native = Path(result['audios'][0]['path'])
    y,sr = sf.read(native,dtype='float32',always_2d=True)
    assert np.isfinite(y).all() and abs(y).max()<1
    review = {'title':track['title'],'native':str(native),'windows':{}}
    duration = len(y)/sr
    for label,start in [('opening',8),('development',duration*.39),('finale',duration*.75)]:
        print(track['title']+' '+label,flush=True)
        description = api.describe(str(native),start=start,end=start+12,top=4)
        match = api.match(str(native),
            'A solo Indian bamboo bansuri flute plays expressive flowing melodies with tabla and gentle stringed accompaniment.',
            alts=['Orchestral string music with no flute.','A basic electronic flute playing repeated short notes over a dance beat.','A singer singing over instruments.'],
            start=start,end=start+12)
        review['windows'][label] = {'description':description,'flute_match':match}
        print(match['summary'],flush=True)
    measured = parse(run(['-i',native,'-af','loudnorm=I=-16:TP=-1.5:LRA=18:print_format=json','-f','null','-']).stderr)
    filt = ('loudnorm=I=-16:TP=-1.5:LRA=18:linear=true:print_format=json'
            f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
            f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
            f":offset={measured['target_offset']}")
    wav = root/(track['filename']+'.wav')
    master = run(['-i',native,'-af',filt,'-ar','48000','-c:a','pcm_s24le',
                  '-metadata','title='+track['title'],wav])
    mp3 = root/(track['filename']+'.mp3')
    run(['-i',wav,'-c:a','libmp3lame','-b:a','320k',
         '-metadata','title='+track['title'],
         '-metadata','comment=Original AI-generated bansuri-led instrumental',mp3])
    decoded_measure = parse(run(['-i',mp3,'-af','loudnorm=I=-16:TP=-1.5:LRA=18:print_format=json','-f','null','-']).stderr)
    y,sr = sf.read(wav,dtype='float32',always_2d=True)
    checks = {'duration_seconds':len(y)/sr,'sample_rate':sr,'channels':y.shape[1],
              'finite':bool(np.isfinite(y).all()),'clipped_samples':int((abs(y)>=1).sum()),
              'master':parse(master.stderr),'decoded_mp3':decoded_measure}
    assert checks['finite'] and checks['clipped_samples']==0
    assert float(decoded_measure['input_tp'])<0
    review['checks'] = checks
    report['tracks'][track['id']] = review
    (root/'review_and_checks.json').write_text(json.dumps(report,indent=2,default=str))
    print(json.dumps({'title':track['title'],'seconds':len(y)/sr,'mp3_lufs':decoded_measure['input_i'],'mp3_dbtp':decoded_measure['input_tp']}),flush=True)
