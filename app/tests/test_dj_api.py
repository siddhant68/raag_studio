"""DJ Lab behavior: imports, errors, file scope, persistence and a real CPU job."""
import json
from pathlib import Path
import struct
import time
import wave

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.backend.dj_api import DJService,RenderBody,router,atomic_json
from app.backend.main import LocalOnlyMiddleware


@pytest.fixture
def studio(tmp_path):
    svc=DJService(tmp_path/"data",tmp_path/"runs")
    app=FastAPI();app.include_router(router(svc));app.add_middleware(LocalOnlyMiddleware,port=8477)
    with TestClient(app,base_url="http://127.0.0.1:8477") as c:
        yield c,svc,tmp_path
    svc.close()


def fixture_audio(path):
    import math
    rate=16000
    with wave.open(str(path),"wb") as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(b"".join(struct.pack('<hh',int(2000*math.sin(2*math.pi*220*i/rate)),int(2000*math.sin(2*math.pi*220*i/rate))) for i in range(rate*10)))


def test_empty_catalog_labels_the_real_editing_engine(studio):
    c,svc,_=studio
    x=c.get('/api/dj/catalog').json()
    assert x['assets']==[] and x['takes']==[] and x['engine']=='deterministic_dj'
    assert set(x['presets'])=={'bass_swap','loop_drop','echo_reveal','echo_reset','reel_switch','tease_blend'}


def test_invalid_upload_is_rejected_without_leaking_a_temporary_file(studio):
    c,svc,_=studio
    assert c.post('/api/dj/import?extension=mp3',content=b'not audio').status_code==422
    assert c.post('/api/dj/import?extension=exe',content=b'bad').status_code==422
    assert c.post('/api/dj/import',content=b'').status_code==422
    assert not list(svc.data.glob('upload_*'))


def test_cross_origin_upload_blocked(studio):
    c,_,_=studio
    assert c.post('/api/dj/import',content=b'data',headers={'Origin':'https://unrelated.example'}).status_code==403


def test_file_and_job_scope_rejects_arbitrary_paths(studio):
    c,_,_=studio
    for url in ['/api/dj/jobs/not-an-id','/api/dj/assets/nope/audio','/api/dj/takes/'+'a'*32+'/secret.txt']:
        assert c.get(url).status_code==404


@pytest.mark.parametrize("preset", ["echo_reveal", "tease_blend"])
def test_real_import_analysis_and_preview_job(studio,preset):
    c,svc,tmp=studio
    if not svc.python.is_file():pytest.skip('Audio runtime not installed')
    f=tmp/'fixture.wav';fixture_audio(f)
    r=c.post('/api/dj/import?name=Test%20tone&extension=wav',content=f.read_bytes())
    assert r.status_code==202,r.text
    aid=r.json()['asset']['id'];jid=r.json()['job']['id']
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        job=c.get(f'/api/dj/jobs/{jid}').json()
        if job['state'] in ('failed','succeeded'):break
        time.sleep(.05)
    assert job['state']=='succeeded',job
    assert c.get(f'/api/dj/assets/{aid}/audio',headers={'Range':'bytes=0-100'}).status_code==206
    payload=dict(a_id=aid,b_id=aid,preset=preset,a_cue_s=.1,b_cue_s=.1,a_bpm=120,b_bpm=120,target_bpm=120,a_beats=8,b_beats=8,title='Real fixture preview')
    if preset=='tease_blend':
        assert c.post('/api/dj/renders',json=payload).status_code==422
        payload.update(a_beats=24,b_beats=24,a_bpm=180,b_bpm=180,target_bpm=180)
    bad={**payload,'a_cue_s':9}
    assert c.post('/api/dj/renders',json=bad).status_code==422
    bad={**payload,'preset':'fake_stem_magic'}
    assert c.post('/api/dj/renders',json=bad).status_code==422
    r=c.post('/api/dj/renders',json=payload);assert r.status_code==202,r.text
    jid=r.json()['id'];deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        job=c.get(f'/api/dj/jobs/{jid}').json()
        if job['state'] in ('failed','succeeded'):break
        time.sleep(.05)
    assert job['state']=='succeeded',job
    before=(svc.runs/jid/'master.mp3').read_bytes()
    assert c.post(f'/api/dj/takes/{jid}/feedback',json={'verdict':'favorite','notes':'fixture only'}).status_code==200
    catalog=c.get('/api/dj/catalog').json()
    assert catalog['takes'][0]['feedback']['verdict']=='favorite'
    assert before==(svc.runs/jid/'master.mp3').read_bytes()
    assert c.get(f'/api/dj/takes/{jid}/master.mp3').status_code==200
    assert c.post(f'/api/dj/takes/{jid}/feedback',json={'verdict':'made_up'}).status_code==422
    video=c.post(f'/api/dj/takes/{jid}/visualizer',json={})
    assert video.status_code==202,video.text
    video_job=video.json()['id'];deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        v=c.get(f'/api/dj/jobs/{video_job}').json()
        if v['state'] in ('failed','succeeded'):break
        time.sleep(.05)
    assert v['state']=='succeeded',v
    assert c.get(f'/api/dj/takes/{jid}/visualizer.mp4',headers={'Range':'bytes=0-100'}).status_code==206
    assert c.post(f'/api/dj/takes/{jid}/visualizer',json={}).status_code==409
    # Queueing after a render must ignore the persisted *_plan.json entry.
    assert c.post(f'/api/dj/assets/{aid}/analyze').status_code==202


def test_restart_marks_incomplete_jobs_without_touching_completed_previews(tmp_path):
    a=DJService(tmp_path/'d',tmp_path/'r');a.close()
    atomic_json(a.jobs/('b'*32+'.json'),{'id':'b'*32,'state':'running'})
    atomic_json(a.jobs/('c'*32+'.json'),{'id':'c'*32,'state':'succeeded'})
    b=DJService(tmp_path/'d',tmp_path/'r')
    try:
        assert b.job('b'*32)['state']=='interrupted'
        assert b.job('c'*32)['state']=='succeeded'
    finally:b.close()
