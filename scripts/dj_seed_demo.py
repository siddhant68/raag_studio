#!/usr/bin/env python3
"""Adopt private experiments and add original-music demos to the local DJ Lab."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser();p.add_argument('session',type=Path);args=p.parse_args()
    from app.backend.dj_api import DJService,atomic_json
    from app.experiments import dj_lab as dj,remix_lab as lab
    service=DJService(ROOT/'data',ROOT/'runs')
    adopted={};source_assets={}
    previous=json.loads((ROOT/'runs/_dj_lab/sources_20261026/sources.json').read_text())
    existing=service.catalog()['assets']
    defaults={'daft':64,'fisher':128,'kala':40,'nashe':8}
    try:
        for s in previous['sources']:
            asset=next((a for a in existing if a['sha256']==s['sha256']),None)
            if not asset:
                analysis=dj.analyze(s['path']);grid=s['grid_candidates']
                analysis['bpm']=round(grid['bpm'],3);analysis['grid_offset_s']=grid['offset_s']
                asset=service.import_file(s['path'],s['name'],analysis=analysis)
                asset['suggested_cue_s']=grid['offset_s']+defaults[s['id']]*60/grid['bpm']
                atomic_json(service.assets/asset['id']/'asset.json',asset)
            source_assets[s['sha256']]=asset
        manifest=json.loads((args.session/'manifest.json').read_text())
        for item in manifest['takes']:
            source=args.session/item['id'];tid=uuid.uuid4().hex
            target=service.runs/tid;shutil.copytree(source,target)
            plan=json.loads((source/'plan.json').read_text())
            recipe={'preset':plan['preset'],'target_bpm':plan['target_bpm']}
            for role in ('a','b'):
                asset=source_assets[plan[role]['sha256']]
                recipe[role+'_id']=asset['id']
                for key in ('bpm','cue_s','beats'):recipe[role+'_'+key]=plan[role][key]
            atomic_json(target/'app_recipe.json',recipe)
            adopted[item['id']]=tid
        old=json.loads((ROOT/'runs/_remix_learning/study_20261025_verified/sources.json').read_text())
        originals={}
        for sid,title in [('yamuna','Yamuna at Dawn'),('daylight','Daylight')]:
            source=ROOT/old[sid]['path'];analysis=dj.analyze(source)
            analysis['bpm']=old[sid]['estimated_bpm']
            asset=next((a for a in existing if a['sha256']==lab.sha(source)),None)
            if not asset:
                asset=service.import_file(source,title,sharing='original_generated_sources',analysis=analysis)
                asset['suggested_cue_s']=old[sid]['beats_s'][0]
                atomic_json(service.assets/asset['id']/'asset.json',asset)
            originals[sid]=asset
        def deck(sid,beats):
            a=originals[sid]
            return {'asset_id':a['id'],'name':a['name'],'path':str(service.assets/a['id']/a['filename']),'sha256':a['sha256'],'bpm':old[sid]['estimated_bpm'],'cue_s':old[sid]['beats_s'][0],'beats':beats,'kind':'stereo_mix'}
        for name,preset,a,b in [
            ('07_sunrise_session','bass_swap',deck('yamuna',32),deck('daylight',48)),
            ('08_breathe_reel','reel_switch',deck('daylight',16),deck('yamuna',16)),
        ]:
            title={'07_sunrise_session':'Sunrise session · Bansuri meets Daylight','08_breathe_reel':'Breathe · A short original-music reel'}[name]
            plan={'schema':'raag-dj-plan/1','preset':preset,'title':title,'target_bpm':86,'a':a,'b':b,'sharing':'original_generated_sources','models':[],'annotation_status':'Source pulse candidates; musical review pending'}
            folder=args.session/name
            if not folder.exists():dj.render(plan,folder)
            tid=uuid.uuid4().hex;shutil.copytree(folder,service.runs/tid)
            shutil.copyfile(folder/'master.mp3',args.session/f'{name}.mp3')
            adopted[name]=tid
            if name=='08_breathe_reel':
                from app.experiments import dj_video
                dj_video.render(service.runs/tid,service.runs/tid/'visualizer.mp4')
                shutil.copyfile(service.runs/tid/'visualizer.mp4',args.session/'08_breathe_reel.mp4')
            print(json.dumps({'id':name,'take_id':tid,'duration_s':json.loads((folder/'result.json').read_text())['duration_s']}),flush=True)
        atomic_json(args.session/'app_adoption.json',{'takes':adopted,'assets':{sha:a['id'] for sha,a in source_assets.items()},'url':'http://127.0.0.1:8477/dj.html'})
    finally:service.close()

if __name__=='__main__':main()
