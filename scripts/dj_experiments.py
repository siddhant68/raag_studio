#!/usr/bin/env python3
"""Bounded real-song experiment batch. Preserves every plan, source hash and arm."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sources",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    from app.experiments import dj_lab,remix_lab as lab
    sources={s["id"]:s for s in json.loads(args.sources.read_text())["sources"]}
    def deck(name,beat,beats):
        s=sources[name];grid=s["grid_candidates"]
        return {"name":s["name"],"path":s["path"],"sha256":s["sha256"],"bpm":grid["bpm"],"cue_s":grid["offset_s"]+beat*60/grid["bpm"],"beats":beats,"kind":"stereo_mix"}
    # Phrase candidates follow measured grids; title/hook semantics require ears.
    experiments=[
        ("01_one_more_time_pressure_drop","One More Time → Losing It · Pressure drop","loop_drop",125,deck("daft",64,64),deck("fisher",128,48)),
        ("02_one_more_time_echo_reveal","One More Time → Losing It · Echo reveal","echo_reveal",125,deck("daft",64,64),deck("fisher",128,48)),
        ("03_bollywood_pressure_drop","Kala Chashma → Nashe Si Chadh Gayi · Pressure drop","loop_drop",102,deck("kala",40,32),deck("nashe",8,32)),
        ("04_bollywood_tempo_portal","Kala Chashma → Nashe Si Chadh Gayi · Original tempos","echo_reset",102,deck("kala",40,32),deck("nashe",8,32)),
        ("05_bollywood_to_daft","Kala Chashma → One More Time · Club switch","loop_drop",114,deck("kala",144,32),deck("daft",128,48)),
        ("06_reel_switch","Nashe Si Chadh Gayi → Kala Chashma · Reel switch","reel_switch",102,deck("nashe",8,16),deck("kala",144,16)),
    ]
    manifest={"schema":"raag-dj-experiments/1","source_manifest":str(args.sources.resolve()),"source_manifest_sha256":lab.sha(args.sources),"sharing":"private_user_supplied","musical_review":"Pending user listening","takes":[],"failures":[]}
    (args.out/"code").mkdir()
    for f in (ROOT/"app/experiments/dj_lab.py",ROOT/"scripts/dj_experiments.py",ROOT/"app/experiments/remix_lab.py"):
        shutil.copyfile(f,args.out/"code"/f.name)
    for key,title,preset,bpm,a,b in experiments:
        plan={"schema":"raag-dj-plan/1","preset":preset,"target_bpm":bpm,"a":a,"b":b,"title":title,"sharing":"private_user_supplied","annotation_status":"Measured pulse-grid phrase candidates; not a claimed transcription or professional approval","models":[]}
        try:
            result=dj_lab.render(plan,args.out/key)
            friendly=args.out/f"{key}.mp3"
            shutil.copyfile(args.out/key/"master.mp3",friendly)
            record={"id":key,"title":title,"duration_s":result["duration_s"],"reveal_s":result["reveal_s"],"file":friendly.name,"preset":preset,"wall_s":result["wall_s"]}
            manifest["takes"].append(record)
            print(json.dumps(record),flush=True)
        except Exception as exc:
            manifest["failures"].append({"id":key,"error":str(exc)})
            print(json.dumps(manifest["failures"][-1]),flush=True)
        lab.dump(args.out/"manifest.json",manifest)


if __name__=="__main__":main()
