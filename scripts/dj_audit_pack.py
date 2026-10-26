#!/usr/bin/env python3
"""Independent decoded-export audit and a portable listening pack for a DJ batch."""
import argparse
import html
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser();p.add_argument('session',type=Path);args=p.parse_args()
    from app.experiments import remix_lab as lab
    import numpy as np
    out=args.session;audits=[];cards=[]
    with zipfile.ZipFile(out/'Raag_DJ_Lab_Listening_Pack.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for folder in sorted(out.glob('[0-9][0-9]_*')):
            if not folder.is_dir():continue
            result=json.loads((folder/'result.json').read_text())
            record={'id':folder.name,'title':result['title'],'duration_s':result['duration_s'],'reveal_s':result['reveal_s'],'arms':{}}
            for arm in ('master','control'):
                audio=lab.decode(folder/f'{arm}.mp3');checks=lab.waveform_checks(audio,round(result['duration_s']*lab.SR))
                loudness=lab.loudness(folder/f'{arm}.mp3')
                record['arms'][arm]={'checks':checks,'loudness':loudness,'sha256':lab.sha(folder/f'{arm}.mp3')}
                assert not checks['failures'],record
                assert loudness['input_tp']<=-1,record
                assert result['files'][f'{arm}.mp3']==lab.sha(folder/f'{arm}.mp3')
            a,b=[record['arms'][k]['loudness']['input_i'] for k in ('master','control')]
            record['loudness_difference_lu']=round(abs(a-b),2)
            assert abs(a-b)<=.25,record
            # Endpoints should close quietly; this tests actual decoded audio.
            record['last_sample_peak']=float(np.max(np.abs(audio[-1])))
            assert record['last_sample_peak']<.001,record
            record['sharing']=result['sharing'];audits.append(record)
            mp3=folder.name+'.mp3';comparison='comparisons/'+folder.name+'_control.mp3'
            z.write(folder/'master.mp3',mp3);z.write(folder/'control.mp3',comparison)
            title=html.escape(result['title'])
            cards.append(f'<article><h2>{title}</h2><p>{result["duration_s"]:.1f}s · incoming at {result["reveal_s"]:.1f}s</p><audio controls preload="none" src="{mp3}"></audio><p><a href="{mp3}">Download edit</a> · <a href="{comparison}">Untreated comparison</a></p></article>')
        page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raag Studio — DJ listening pack</title><style>body{max-width:850px;margin:40px auto;padding:0 24px;background:#101211;color:#f1f1df;font:16px/1.6 system-ui}h1{font-size:40px}article{background:#191c1a;border:1px solid #343a34;border-radius:12px;padding:22px;margin:20px 0}h2{font-size:22px}a{color:#d5ef78}audio{width:100%}p{color:#aab4aa}</style><h1>Two songs. One moment.</h1><p>Extract this entire ZIP, then open listen.html. These are real source edits. Compare at the same volume; use your listening verdict to decide what stays. Commercial-song experiments are private reference edits; original-music demos are separately labeled in the app.</p>'''+''.join(cards)+'</html>'
        z.writestr('listen.html',page)
        (out/'listen.html').write_text(page)
        if (out/'08_breathe_reel.mp4').exists():z.write(out/'08_breathe_reel.mp4','Original_Music_Reel_Demo.mp4')
        z.writestr('README.txt','Extract all files before opening listen.html. MP3s can also be played directly. Each edit has a separately linked untreated comparison. No source recording is overwritten. Listening judgments are pending. Use DJ Lab inside Raag Studio for editable cues, techniques, recipe reuse and reviews.\n')
    lab.dump(out/'independent_audit.json',{'takes':audits,'passed':len(audits),'failed':0,'scope':'Independent export and level checks, not musical approval'})
    print(json.dumps({'takes':len(audits),'mp3_exports_checked':len(audits)*2,'zip_bytes':(out/'Raag_DJ_Lab_Listening_Pack.zip').stat().st_size,'maximum_pair_difference_lu':max(a['loudness_difference_lu'] for a in audits)}))

if __name__=='__main__':main()
