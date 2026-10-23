"""AT-M2-02 (create / validation / idempotency), AT-M2-03 (fake engine labelling) and the rest of the song API."""
import hashlib
import threading
from pathlib import Path

import pytest

from test_m2_support import (BRIEF, client_for, create_and_wait, create_body, make_config, wait_job)

from backend.main import create_app
from backend.settings import Config


def run_dirs(tmp_path):
    """Final round folders: runs/<song>/<round> (no .partial, no exports, no quarantine)."""
    runs = tmp_path / "runs"
    return [d for song in runs.iterdir() if song.is_dir() and song.name != "_quarantine"
            for d in song.iterdir() if d.is_dir() and d.name != "exports"]


# --------------------------------------------------------------------------- AT-M2-02
def test_at_m2_02_empty_valid_duplicate(tmp_path):
    with client_for(tmp_path) as c:
        for bad in ({"brief": ""}, {"brief": "   "}, {}, {"brief": 5}):
            r = c.post("/api/songs", json=bad)
            assert r.status_code == 422, bad
            assert r.json()["error"]["code"] == "invalid_request"
        assert c.get("/api/songs").json()["songs"] == []             # nothing was created

        headers = {"Idempotency-Key": "client-uuid-1"}
        r1 = c.post("/api/songs", json=create_body(), headers=headers)
        assert r1.status_code == 202
        first = r1.json()
        assert {"song_id", "round_id", "job_id", "plan"} <= set(first)
        assert first["plan"]["voice_mode"] == "instrumental"
        r2 = c.post("/api/songs", json=create_body(), headers=headers)
        assert r2.status_code == 202
        assert r2.json()["job_id"] == first["job_id"] and r2.json()["song_id"] == first["song_id"]
        assert r2.json()["replayed"] is True
        wait_job(c, first["job_id"])
        r3 = c.post("/api/songs", json=create_body(), headers=headers)         # replay after completion too
        assert r3.json()["job_id"] == first["job_id"]

        assert c.svc.db.one("SELECT COUNT(*) FROM jobs")[0] == 1
        assert c.svc.db.one("SELECT COUNT(*) FROM songs")[0] == 1
        assert len(run_dirs(tmp_path)) == 1


def test_body_idempotency_key_and_concurrent_duplicates(tmp_path):
    with client_for(tmp_path) as c:
        out = []

        def post():
            out.append(c.post("/api/songs", json=create_body(idempotency_key="same-key")).json()["job_id"])
        threads = [threading.Thread(target=post) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        assert len(set(out)) == 1
        wait_job(c, out[0])
        assert c.svc.db.one("SELECT COUNT(*) FROM jobs")[0] == 1
        assert len(run_dirs(tmp_path)) == 1


def test_create_stores_plan_request_and_job(tmp_path):
    with client_for(tmp_path) as c:
        data, job, detail = create_and_wait(c)
        plan = detail["plans"][0]
        assert plan["source"] == "rules" and plan["rev"] == 1
        assert plan["card"]["provider"] == "basic" and plan["card"]["is_llm"] is False
        assert plan["provenance"]["voice_mode"]["source"] == "suggested"
        rnd = detail["rounds"][0]
        assert rnd["kind"] == "create" and rnd["job"]["state"] == "succeeded"
        req = rnd["request"]
        assert req["engine_request"]["schema"] == "raag-engine-request/1"
        assert len(req["seeds"]) == 2 and req["engine_request"]["params"]["duration"] == 10
        assert req["sha256"] == hashlib.sha256(
            __import__("json").dumps(req["engine_request"], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        assert len(detail["takes"]) == 2
        for t in detail["takes"]:
            assert t["requested_params"]["seed"] == t["seed"]
            assert t["effective_params"]["guidance_scale"] == 1.0 and t["requested_params"]["guidance_scale"] == 7.0
            assert t["engine_rev"] == "fake-engine-1"
            assert t["technical_checks"]["label"].startswith("Technical checks")
        assert {t["seed"] for t in detail["takes"]} == set(req["seeds"])


def test_controls_and_supplied_plan(tmp_path):
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json=create_body(voice="wordless", takes=1,
                                                  shape={"lead": "piano", "instruments": ["cello"], "pace": "slow"}))
        assert r.status_code == 202, r.text
        plan = r.json()["plan"]
        assert plan["voice_mode"] == "wordless" and plan["lead"]["instrument"] == "piano"
        assert plan["pace"]["bucket"] == "slow" and plan["takes"] == 1
        assert plan["provenance"]["voice_mode"]["source"] == "you"
        bad = c.post("/api/songs", json=create_body(shape={"lead": "kazoo"}))
        assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_controls"
        supplied = dict(plan, brief="my own plan", takes=1)
        r = c.post("/api/songs", json={"brief": "my own plan", "plan": supplied})
        assert r.status_code == 202 and r.json()["card"]["provider"] == "user"
        assert c.get(f"/api/songs/{r.json()['song_id']}").json()["plans"][0]["source"] == "user_edit"


def test_sung_without_lyrics_is_a_clear_422(tmp_path):
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json=create_body(voice="sung"))
        assert r.status_code == 422
        err = r.json()["error"]
        assert err["code"] == "needs_user_input" and "lyrics" in err["message"].lower()
        assert c.svc.db.one("SELECT COUNT(*) FROM songs")[0] == 0


def test_plan_only_does_not_render(tmp_path):
    with client_for(tmp_path) as c:
        data, job, _ = create_and_wait(c)
        r = c.post(f"/api/songs/{data['song_id']}/plan", json={"controls": {"fullness": "spare"}})
        assert r.status_code == 200
        body = r.json()
        assert body["plan_rev"] == 2 and body["plan"]["fullness"] == "spare" and body["compile_report"]["char_count"] > 0
        assert c.svc.db.one("SELECT COUNT(*) FROM jobs")[0] == 1          # no new job
        assert c.svc.db.one("SELECT COUNT(*) FROM rounds")[0] == 1
        assert c.post("/api/songs/NOPE/plan", json={}).status_code == 404


def test_patch_controls_makes_a_new_plan_revision(tmp_path):
    with client_for(tmp_path) as c:
        data, _, _ = create_and_wait(c)
        r = c.patch(f"/api/songs/{data['song_id']}/controls", json={"fullness": "full", "bpm": 90})
        assert r.status_code == 200
        body = r.json()
        assert body["plan_rev"] == 2 and body["plan"]["fullness"] == "full" and body["plan"]["pace"]["bpm"] == 90
        detail = c.get(f"/api/songs/{data['song_id']}").json()
        assert [p["rev"] for p in detail["plans"]] == [1, 2]
        assert detail["plans"][1]["source"] == "user_edit"
        assert detail["plans"][1]["provenance"]["fullness"]["source"] == "you"
        assert detail["plans"][0]["plan"]["fullness"] == "balanced"          # revision 1 untouched
        assert c.patch(f"/api/songs/{data['song_id']}/controls", json={"lead": "kazoo"}).status_code == 422
        assert c.patch(f"/api/songs/{data['song_id']}/controls", json={"nonsense": 1}).status_code == 422
        # the next 'another' round uses the latest revision
        r = c.post(f"/api/songs/{data['song_id']}/rounds", json={"kind": "another"})
        assert r.json()["plan_rev"] == 2 and r.json()["plan"]["fullness"] == "full"


def test_rounds_another_refine_and_experimental(tmp_path):
    with client_for(tmp_path) as c:
        data, _, detail0 = create_and_wait(c)
        sid = data["song_id"]
        t1 = detail0["takes"][0]
        before = {t["id"]: (t["native_sha256"], t["seed"]) for t in detail0["takes"]}

        another = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "takes": 1})
        assert another.status_code == 202
        assert another.json()["plan_id"] == data["plan_id"]                    # same plan, no new revision
        assert set(another.json()["seeds"]).isdisjoint({s for _, s in before.values()})
        wait_job(c, another.json()["job_id"])

        refine = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["less_busy"],
                                                          "from_take": t1["id"]})
        assert refine.status_code == 202, refine.text
        assert refine.json()["plan_rev"] == 2
        assert "less_busy" in refine.json()["card"]["applied"]
        wait_job(c, refine.json()["job_id"])

        detail = c.get(f"/api/songs/{sid}").json()
        kinds = [r["kind"] for r in detail["rounds"]]
        assert kinds == ["create", "another", "refine"]
        refine_round = detail["rounds"][2]
        assert refine_round["parent_take_id"] == t1["id"] and refine_round["request_text"] == "less busy"
        assert len(detail["takes"]) == 2 + 1 + 2
        for t in detail["takes"]:
            if t["id"] in before:                                            # originals byte-identical
                assert t["native_sha256"] == before[t["id"]][0]
                assert hashlib.sha256(Path(c.svc.storage.abs(
                    c.svc.get_take(t["id"])["native_path"])).read_bytes()).hexdigest() == before[t["id"]][0]

        # nothing to change / unsupported free text
        nothing = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "request_text": "make it sound like rain"})
        assert nothing.status_code == 422 and nothing.json()["error"]["code"] == "nothing_to_change"
        assert c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine"}).status_code == 422

        for kind in ("variation", "cover", "repaint"):
            r = c.post(f"/api/songs/{sid}/rounds", json={"kind": kind, "from_take": t1["id"]})
            assert r.status_code == 501
            assert "experimental" in r.json()["error"]["message"] and "not enabled" in r.json()["error"]["message"]
        assert c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_take": "NOPE"}).status_code == 404
        assert c.post("/api/songs/NOPE/rounds", json={"kind": "another"}).status_code == 404


def test_song_list_and_not_found(tmp_path):
    with client_for(tmp_path) as c:
        data, _, _ = create_and_wait(c)
        songs = c.get("/api/songs").json()["songs"]
        assert len(songs) == 1 and songs[0]["id"] == data["song_id"] and songs[0]["take_count"] == 2
        assert songs[0]["latest_job"]["state"] == "succeeded"
        assert c.get("/api/songs/NOPE").status_code == 404
        assert c.get("/api/jobs/NOPE").status_code == 404
        assert c.get("/api/takes/NOPE").status_code == 404
        assert c.get("/api/takes/NOPE/audio").status_code == 404
        assert c.get("/api/nothing-here").json()["error"]["code"] == "not_found"


def test_settings_and_system(tmp_path):
    with client_for(tmp_path) as c:
        s = c.get("/api/settings").json()["settings"]
        assert s["planner_provider"] == "basic" and s["min_disk_gib"] == 5.0 and s["queue_depth_cap"] == 5
        r = c.put("/api/settings", json={"queue_depth_cap": 3, "silence_warn_fraction": 0.1})
        assert r.status_code == 200 and r.json()["settings"]["queue_depth_cap"] == 3
        assert c.get("/api/settings").json()["settings"]["silence_warn_fraction"] == 0.1
        assert c.put("/api/settings", json={"nope": 1}).status_code == 422
        assert c.put("/api/settings", json={"queue_depth_cap": -1}).status_code == 422
        assert c.put("/api/settings", json={"video_queue_url": "http://evil.example/q"}).status_code == 422
        # choosing a smart provider alone changes nothing: it runs only with planner_smart_enabled=true
        chosen = c.put("/api/settings", json={"planner_provider": "claude_cli"})
        assert chosen.status_code == 200 and chosen.json()["settings"]["planner_smart_enabled"] is False
        assert c.put("/api/settings", json={"planner_provider": "gpt"}).status_code == 422
        assert c.put("/api/settings", json={"planner_smart_enabled": "yes"}).status_code == 422
        so = c.get("/api/system").json()
        assert so["planner_provider"] == "basic" and so["planner_setting"] == "claude_cli"
        r = c.post("/api/songs", json=create_body())
        assert r.status_code == 202 and r.json()["card"]["provider"] == "basic" and r.json()["card"]["is_llm"] is False
        c.put("/api/settings", json={"planner_provider": "basic"})
        sysinfo = c.get("/api/system").json()
        assert {"mps", "disk_free_gib", "video_queue", "engine_rev", "planner_provider", "version",
                "capabilities", "queue"} <= set(sysinfo)
        assert sysinfo["engine"] == "fake" and sysinfo["mps"] is None
        assert sysinfo["planner_provider"] == "basic" and sysinfo["capabilities"]["controls"] == 25
        assert sysinfo["video_queue"]["state"] == "idle"


# --------------------------------------------------------------------------- AT-M2-03
def test_at_m2_03_fake_only_with_env_var(tmp_path, monkeypatch):
    assert Config.from_env({"RAAG_ENGINE": "fake"}).is_fake
    assert Config.from_env({}).engine == "real" and not Config.from_env({}).is_fake
    assert Config.from_env({"RAAG_ENGINE": ""}).engine == "real"
    with pytest.raises(ValueError):
        Config.from_env({"RAAG_ENGINE": "mock"})
    with pytest.raises(ValueError):
        Config.from_env({"RAAG_ENGINE": "fakee"})

    # Real mode with no ACE python available: the job FAILS clearly and nothing fake is ever produced.
    empty_tools = tmp_path / "no_tools"
    empty_tools.mkdir()
    monkeypatch.setenv("RAAG_TOOLS_DIR", str(empty_tools))
    with client_for(tmp_path / "real", engine=None) as c:
        assert c.config.engine == "real"
        r = c.post("/api/songs", json=create_body())
        assert r.status_code == 202 and r.json()["engine"] == "real" and r.json()["job"]["engine"] == "real"
        job = wait_job(c, r.json()["job_id"])
        assert job["state"] == "failed" and "ACE python not found" in job["error"]
        assert c.svc.db.one("SELECT COUNT(*) FROM takes")[0] == 0
        assert c.get("/api/system").json()["engine"] == "real"


def test_every_response_is_labelled_fake_and_exports_stay_fake(tmp_path):
    with client_for(tmp_path) as c:
        data, job, detail = create_and_wait(c)
        take = detail["takes"][0]
        responses = [
            c.get("/api/songs"), c.get(f"/api/songs/{data['song_id']}"), c.get(f"/api/jobs/{data['job_id']}"),
            c.get(f"/api/takes/{take['id']}"), c.get("/api/system"), c.get("/api/settings"),
            c.get("/api/nothing"), c.get("/api/songs/NOPE"), c.post("/api/songs", json={"brief": ""}),
            c.post(f"/api/takes/{take['id']}/feedback", json={"favourite": True}),
            c.post(f"/api/songs/{data['song_id']}/plan", json={}),
            c.post("/api/admin/prune", json={"older_than_days": 1}),
        ]
        for r in responses:
            assert r.headers["content-type"].startswith("application/json")
            assert r.json()["engine"] == "fake", r.request.url
        assert job["engine"] == "fake" and all(t["engine"] == "fake" and "FAKE" in t["notice"] for t in detail["takes"])
        audio = c.get(take["audio_url"])
        assert audio.headers["x-raag-engine"] == "fake"

        ex = c.post(f"/api/takes/{take['id']}/exports", json={"format": "mp3"})
        assert ex.status_code == 201
        body = ex.json()
        assert body["engine"] == "fake" and "FAKE" in body["notice"] and "_FAKE." in body["filename"]
        download = c.get(body["url"])
        assert download.status_code == 200 and "_FAKE." in download.headers["content-disposition"]
        assert download.headers["content-type"] == "audio/mpeg"
        # the file itself says so (tag survives the export)
        import subprocess
        tags = subprocess.run(["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format_tags=comment",
                               "-of", "csv=p=0", str(c.svc.storage.abs(c.svc.db.one("SELECT path FROM exports")[0]))],
                              capture_output=True, text=True).stdout
        assert "FAKE" in tags
        listed = c.get(f"/api/songs/{data['song_id']}").json()["exports"]
        assert listed[0]["engine"] == "fake"


# --------------------------------------------------------------------------- security
def test_local_only_guards(tmp_path):
    with client_for(tmp_path) as c:
        assert c.get("/api/settings", headers={"Host": "evil.example"}).status_code == 400
        r = c.post("/api/songs", json=create_body(), headers={"Origin": "https://evil.example"})
        assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden_origin"
        ok = c.put("/api/settings", json={"queue_depth_cap": 4}, headers={"Origin": "http://127.0.0.1:8477"})
        assert ok.status_code == 200


def test_web_dir_placeholder_and_static(tmp_path):
    with client_for(tmp_path) as c:                          # app/web/ does not exist yet in M2
        if not c.config.web_dir.is_dir():
            r = c.get("/")
            assert r.status_code == 200 and "Raag Studio" in r.text and "not installed" in r.text
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>hello ui</h1>")
    config = make_config(tmp_path / "with_web")
    config.web_dir = web
    from fastapi.testclient import TestClient
    with TestClient(create_app(config), base_url="http://127.0.0.1:8477") as c:
        assert "hello ui" in c.get("/").text
        assert c.get("/api/settings").status_code == 200      # API routes still win over the static mount
