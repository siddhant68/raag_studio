"""DJ Lab's local import, CPU job queue, immutable previews and feedback API.

Audio processing lives in an isolated Python subprocess. No numpy/model import
is performed by the web server. Commercial source files never enter git/public
showcase directories and the server has no publishing operation.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from . import media

ROOT=Path(__file__).resolve().parents[2]
IDS=re.compile(r"^[a-f0-9]{32}$")
PRESETS={
    "tease_blend": {"name": "Tease & handover", "description": "A four-bar overlap, tightening incoming repeats and a gradual volume handover.", "use_case": "Club · Bollywood · rhythmic entrances"},
    "bass_swap":{"name":"Velvet blend","description":"An eight-beat blend with one bass owner.","use_case":"Warm-up · lounge · continuous mixes"},
    "loop_drop":{"name":"Pressure → drop","description":"A four-beat fragment tightens before the next entrance.","use_case":"Club · dance floor · reveal"},
    "echo_reveal":{"name":"Echo & reveal","description":"The outgoing phrase echoes into the next track.","use_case":"Parties · hook changes"},
    "echo_reset":{"name":"Tempo portal","description":"An echo exit connects two tracks at their own tempos.","use_case":"Bollywood ↔ dance · genre changes"},
    "reel_switch":{"name":"Reel switch","description":"A short setup, a brief breath, then a recognizable entrance.","use_case":"Reels · outfit changes · before/after"},
}


def now():return datetime.now(timezone.utc).isoformat()


def atomic_json(path,value):
    tmp=path.with_suffix(".partial")
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    tmp.replace(path)


def checked_id(value):
    if not IDS.fullmatch(value):raise HTTPException(404,"Item not found")
    return value


class RenderBody(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)
    a_id:str
    b_id:str
    preset:str="echo_reveal"
    a_cue_s:float=Field(ge=0)
    b_cue_s:float=Field(ge=0)
    a_bpm:float=Field(ge=60,le=180)
    b_bpm:float=Field(ge=60,le=180)
    target_bpm:float=Field(ge=60,le=180)
    a_beats:int=32
    b_beats:int=32
    title:str=Field(default="My transition",min_length=1,max_length=120)


class FeedbackBody(BaseModel):
    model_config=ConfigDict(extra="forbid")
    verdict:str
    notes:str=Field(default="",max_length=3000)


class DJService:
    def __init__(self,data_dir,runs_dir,audio_python=None):
        self.data=Path(data_dir)/"dj"
        self.runs=Path(runs_dir)/"_dj_lab"/"previews"
        self.assets=self.data/"assets"
        self.jobs=self.data/"jobs"
        self.feedback=self.data/"feedback"
        for path in (self.assets,self.jobs,self.feedback):path.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="raag-dj")
        configured=audio_python or os.environ.get("RAAG_AUDIO_PYTHON")
        self.python=Path(configured) if configured else ROOT.parent/"tools/acestep-venv/bin/python"
        self.closed=False
        self.process=None
        for path in self.jobs.glob("*.json"):
            j=json.loads(path.read_text())
            if j.get("state") in ("queued","running"):
                j.update(state="interrupted",message="Server restarted. Submit a new preview; earlier results are preserved.",finished_at=now())
                atomic_json(path,j)

    def close(self):
        self.closed=True
        with self.lock:
            if self.process and self.process.poll() is None:
                try:os.killpg(self.process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        self.pool.shutdown(wait=True,cancel_futures=False)

    def _read(self,path):
        if not path.is_file():raise HTTPException(404,"Item not found")
        return json.loads(path.read_text())

    def asset(self,aid):
        aid=checked_id(aid)
        return self._read(self.assets/aid/"asset.json")

    def job(self,jid):return self._read(self.jobs/f"{checked_id(jid)}.json")

    def _queue(self,operation,aid=None,plan=None):
        if not self.python.is_file():raise HTTPException(503,"Audio runtime unavailable. Set RAAG_AUDIO_PYTHON to a Python with numpy, scipy and soundfile.")
        with self.lock:
            jobs=[self._read(p) for p in self.jobs.glob("*.json") if not p.name.endswith("_plan.json")]
            if operation=="analyze":
                existing=next((j for j in jobs if j.get("operation")=="analyze" and j.get("asset_id")==aid and j.get("state") in ("queued","running")),None)
                if existing:return existing
            if sum(j["state"] in ("queued","running") for j in jobs)>=6:raise HTTPException(409,"Six DJ jobs are already queued. Wait for a preview to finish.")
            jid=uuid.uuid4().hex
            record={"id":jid,"operation":operation,"asset_id":aid,"state":"queued","created_at":now(),"message":"Waiting for the CPU audio worker","engine":"deterministic_dj"}
            if plan:record["plan"]=plan
            atomic_json(self.jobs/f"{jid}.json",record)
            self.pool.submit(self._work,jid)
            return record

    def _work(self,jid):
        path=self.jobs/f"{jid}.json"
        record=self._read(path)
        if self.closed:
            record.update(state="interrupted",message="Server is stopping",finished_at=now())
            atomic_json(path,record);return
        try:
            messages={"analyze":"Measuring audio","render":"Preparing decks, rendering automation and checking exports","visualizer":"Making the vertical waveform video"}
            record.update(state="running",started_at=now(),message=messages[record["operation"]])
            atomic_json(path,record)
            if record["operation"]=="visualizer":
                output=self.runs/record["asset_id"]
                args=["visualizer",str(output),str(output/"visualizer.mp4")]
            elif record["operation"]=="analyze":
                asset=self.asset(record["asset_id"])
                source=self.assets/asset["id"]/asset["filename"]
                output=self.assets/asset["id"]/"analysis.json"
                args=["analyze",str(source),str(output)]
            else:
                plan_path=self.jobs/f"{jid}_plan.json"
                atomic_json(plan_path,record["plan"])
                output=self.runs/jid
                args=["render",str(plan_path),str(output)]
            env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1","OMP_NUM_THREADS":"2","OPENBLAS_NUM_THREADS":"2","NUMBA_CACHE_DIR":str(self.data/"numba_cache")}
            with self.lock:
                if self.closed:raise RuntimeError("Server is stopping")
                proc=subprocess.Popen([str(self.python),str(ROOT/"scripts/dj_worker.py"),*args],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                self.process=proc
            stdout,stderr=proc.communicate(timeout=600)
            (self.jobs/f"{jid}.log").write_bytes(stdout+b"\n"+stderr)
            if proc.returncode:
                detail=stderr.decode(errors="replace").strip().splitlines()
                raise RuntimeError(detail[-1] if detail else "Audio worker failed")
            if record["operation"]=="analyze":
                asset.update(analysis=self._read(output),status="ready")
                atomic_json(self.assets/asset["id"]/"asset.json",asset)
            elif record["operation"]=="render":
                result=self._read(output/"result.json")
                record["result_id"]=jid
                record["duration_s"]=result["duration_s"]
            record.update(state="succeeded",finished_at=now(),message="Ready to listen")
        except Exception as exc:
            with self.lock:
                if self.process and self.process.poll() is None:
                    try:os.killpg(self.process.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    self.process.communicate()
            record.update(state="failed",finished_at=now(),message=str(exc)[:600])
            if record["operation"]=="analyze":
                asset=self.asset(record["asset_id"])
                asset.update(status="ready" if asset.get("analysis") else "analysis_failed",error=record["message"])
                atomic_json(self.assets/asset["id"]/"asset.json",asset)
        finally:
            with self.lock:self.process=None
            atomic_json(path,record)

    def import_file(self,source,name=None,sharing="private_user_supplied",analysis=None):
        """Internal import used by the streamed upload and local experiment script."""
        source=Path(source)
        info=media.probe(source)
        duration=info["duration_s"]
        if not 5<=duration<=900:raise HTTPException(422,"Choose audio between 5 seconds and 15 minutes")
        ext=source.suffix.lower()
        if ext not in (".mp3",".wav",".flac",".m4a",".ogg"):raise HTTPException(422,"Unsupported audio format")
        aid=uuid.uuid4().hex
        folder=self.assets/aid;folder.mkdir()
        filename="source"+ext
        shutil.copyfile(source,folder/filename)
        record={"id":aid,"name":(name or source.stem)[:200],"filename":filename,"sha256":media.sha256_file(folder/filename),"duration_s":duration,"sharing":sharing,"created_at":now(),"status":"ready" if analysis else "imported","kind":"stereo_mix"}
        if analysis:record["analysis"]=analysis
        atomic_json(folder/"asset.json",record)
        return record

    def render(self,body):
        if body.preset not in PRESETS:raise HTTPException(422,"Choose a supported transition technique")
        plan={"schema":"raag-dj-plan/1","preset":body.preset,"title":body.title,"target_bpm":body.target_bpm,"created_at":now(),"models":[],"sharing":"original_generated_sources","annotation_status":"User-selected cues and tempo estimates; musical review pending"}
        for role in ("a","b"):
            asset=self.asset(getattr(body,f"{role}_id"))
            if asset["status"]!="ready":raise HTTPException(409,"Analyze both sources before rendering")
            bpm,cue,beats=[getattr(body,f"{role}_{key}") for key in ("bpm","cue_s","beats")]
            if beats not in (8,16,24,32,48,64):raise HTTPException(422,"Choose 8, 16, 24, 32, 48 or 64 beats")
            if cue+beats*60/bpm>asset["duration_s"]-.005:raise HTTPException(422,f"Deck {role.upper()}: passage runs past the end. Choose an earlier cue or fewer beats.")
            if body.preset not in ("echo_reset","reel_switch") and abs(body.target_bpm/bpm-1)>.15:raise HTTPException(422,"Tempo gap needs more than 15% stretching. Choose Tempo portal.")
            plan[role]={"asset_id":asset["id"],"path":str((self.assets/asset["id"]/asset["filename"]).resolve()),"name":asset["name"],"sha256":asset["sha256"],"bpm":bpm,"cue_s":cue,"beats":beats,"kind":asset["kind"]}
            if asset["sharing"]!="original_generated_sources":plan["sharing"]="private_user_supplied"
        if body.preset=="tease_blend" and min(body.a_beats,body.b_beats)<24:
            raise HTTPException(422,"Tease & handover needs at least 24 beats on each deck")
        return self._queue("render",plan=plan)

    def catalog(self):
        assets=[self._read(p) for p in self.assets.glob("*/asset.json")]
        jobs=[self._read(p) for p in self.jobs.glob("*.json") if not p.name.endswith("_plan.json")]
        takes=[]
        for path in self.runs.glob("*/result.json"):
            take=self._read(path);take["id"]=path.parent.name
            take["created_at"]=path.stat().st_mtime
            take["has_visualizer"]=(path.parent/"visualizer.mp4").is_file()
            recipe=path.parent/"app_recipe.json"
            if recipe.is_file():take["recipe"]=self._read(recipe)
            else:
                plan=self._read(path.parent/"plan.json")
                if all(plan[r].get("asset_id") for r in ("a","b")):
                    take["recipe"]={"preset":plan["preset"],"target_bpm":plan["target_bpm"]}
                    for role in ("a","b"):
                        take["recipe"][role+"_id"]=plan[role]["asset_id"]
                        for key in ("bpm","cue_s","beats"):take["recipe"][role+"_"+key]=plan[role][key]
            if (self.feedback/f"{take['id']}.json").exists():take["feedback"]=self._read(self.feedback/f"{take['id']}.json")
            takes.append(take)
        return {"assets":sorted(assets,key=lambda a:a["created_at"],reverse=True),"jobs":sorted(jobs,key=lambda j:j["created_at"],reverse=True)[:30],"takes":sorted(takes,key=lambda t:t["created_at"],reverse=True),"presets":PRESETS,"runtime_available":self.python.is_file(),"engine":"deterministic_dj"}


def router(service):
    routes=APIRouter(prefix="/api/dj",tags=["DJ Lab"])

    @routes.get("/catalog")
    def catalog():return service.catalog()

    @routes.post("/import",status_code=202)
    async def upload(request:Request,name:str="My source",extension:str="mp3"):
        extension=extension.lower()
        if extension not in ("mp3","wav","flac","m4a","ogg"):raise HTTPException(422,"Unsupported audio format")
        incoming=service.data/f"upload_{uuid.uuid4().hex}.{extension}"
        count=0
        try:
            with incoming.open("xb") as f:
                async for chunk in request.stream():
                    count+=len(chunk)
                    if count>70*1024*1024:raise HTTPException(413,"Maximum upload is 70 MB")
                    f.write(chunk)
            if not count:raise HTTPException(422,"Choose a non-empty audio file")
            try:asset=await asyncio.to_thread(service.import_file,incoming,name)
            except media.MediaError as exc:raise HTTPException(422,str(exc))
            job=service._queue("analyze",aid=asset["id"])
            return {"asset":asset,"job":job,"engine":"deterministic_dj"}
        finally:incoming.unlink(missing_ok=True)

    @routes.post("/assets/{aid}/analyze",status_code=202)
    def analyze(aid:str):
        service.asset(aid)
        return service._queue("analyze",aid=aid)

    @routes.get("/assets/{aid}/audio")
    def source_audio(aid:str):
        asset=service.asset(aid)
        return FileResponse(service.assets/aid/asset["filename"])

    @routes.post("/renders",status_code=202)
    def render(body:RenderBody):return service.render(body)

    @routes.get("/jobs/{jid}")
    def job(jid:str):return service.job(jid)

    @routes.get("/takes/{tid}/{filename}")
    def take_file(tid:str,filename:str):
        checked_id(tid)
        if filename not in ("master.mp3","control.mp3","master.wav","plan.json","result.json","visualizer.mp4"):raise HTTPException(404,"File not found")
        base=(service.runs/tid).resolve()
        path=(base/filename).resolve()
        if path.parent!=base or not path.is_file():raise HTTPException(404,"File not found")
        return FileResponse(path,filename=f"raag_{tid[:8]}_{filename}")

    @routes.post("/takes/{tid}/visualizer",status_code=202)
    def visualizer(tid:str):
        checked_id(tid)
        if not (service.runs/tid/"result.json").is_file():raise HTTPException(404,"Preview not found")
        with service.lock:
            if (service.runs/tid/"visualizer.mp4").exists():raise HTTPException(409,"Reel video already exists. Download it from the preview.")
            if any(j.get("asset_id")==tid and j.get("operation")=="visualizer" and j.get("state") in ("queued","running") for j in service.catalog()["jobs"]):raise HTTPException(409,"Reel video is already queued")
            return service._queue("visualizer",aid=tid)

    @routes.post("/takes/{tid}/feedback")
    def feedback(tid:str,body:FeedbackBody):
        checked_id(tid)
        if not (service.runs/tid/"result.json").is_file():raise HTTPException(404,"Preview not found")
        if body.verdict not in ("favorite","keep","revise","reject","unrated"):raise HTTPException(422,"Unknown verdict")
        record={**body.model_dump(),"updated_at":now(),"take_id":tid}
        with service.lock:atomic_json(service.feedback/f"{tid}.json",record)
        return record

    return routes
