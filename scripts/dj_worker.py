#!/usr/bin/env python3
"""Isolated CPU audio worker used by DJ Lab and reproducible CLI jobs."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("operation",choices=["analyze","render","visualizer"])
    p.add_argument("input",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    os.environ.setdefault("NUMBA_CACHE_DIR",str(ROOT/"runs/_dj_lab/numba_cache"))
    from app.experiments import dj_lab
    if args.operation=="analyze":
        result=dj_lab.analyze(args.input)
        args.output.write_text(json.dumps(result,indent=2)+"\n")
    elif args.operation=="render":
        result=dj_lab.render(json.loads(args.input.read_text()),args.output)
    else:
        from app.experiments import dj_video
        result=dj_video.render(args.input,args.output)
    print(json.dumps({k:result[k] for k in ("engine","duration_s")}),flush=True)

if __name__=="__main__":main()
