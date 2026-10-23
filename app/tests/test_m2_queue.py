"""Queue and worker behaviour: AT-M2-06 (cancel), AT-M2-07 (gates), retry policy, failures, depth cap, recovery rules."""
import http.server
import json
import os
import threading
import time

import pytest

from test_m2_support import client_for, create_body, wait_job

from backend.db import now_iso


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_for(fn, timeout=20, what="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {what}")


def post_song(c, **extra):
    r = c.post("/api/songs", json=create_body(**extra))
    assert r.status_code == 202, r.text
    return r.json()


# --------------------------------------------------------------------------- AT-M2-06
def test_at_m2_06_cancel_queued_and_running(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_TAKE_S", "30")                 # a "slow" engine
    with client_for(tmp_path) as c:
        a = post_song(c)
        running = wait_for(lambda: (j := c.get(f"/api/jobs/{a['job_id']}").json())["state"] == "running"
                           and j["worker_pid"] and j, what="job A running with a pid")
        pid = running["worker_pid"]
        assert alive(pid)
        b = post_song(c)                                          # waits behind A (one heavy job at a time)
        assert c.get(f"/api/jobs/{b['job_id']}").json()["state"] == "queued"
        assert c.get("/api/system").json()["queue"] == {"queued": 1, "running": 1, "depth": 2, "cap": 5,
                                                         "running_job_id": a["job_id"]}

        t0 = time.time()
        rb = c.post(f"/api/jobs/{b['job_id']}/cancel")            # queued: immediate
        assert rb.status_code == 200 and rb.json()["state"] == "cancelled" and time.time() - t0 < 1.0

        t0 = time.time()
        ra = c.post(f"/api/jobs/{a['job_id']}/cancel")            # running: real kill
        assert ra.status_code == 200 and ra.json()["state"] == "cancelled", ra.json()
        assert time.time() - t0 < 5.0
        assert not alive(pid)
        assert not list((tmp_path / "runs").glob("*/*.partial")) and not list((tmp_path / "runs").glob("*/*/"))
        assert c.svc.db.one("SELECT COUNT(*) FROM takes")[0] == 0
        assert c.post(f"/api/jobs/{a['job_id']}/cancel").status_code == 409     # already over
        assert c.post("/api/jobs/NOPE/cancel").status_code == 404


def test_cancel_escalates_to_sigkill_when_engine_ignores_sigterm(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_TAKE_S", "30")
    monkeypatch.setenv("RAAG_FAKE_IGNORE_TERM", "1")
    with client_for(tmp_path) as c:
        a = post_song(c)
        job = wait_for(lambda: (j := c.get(f"/api/jobs/{a['job_id']}").json())["state"] == "running"
                       and j["worker_pid"] and j)
        pid = job["worker_pid"]
        time.sleep(0.5)                                           # let the engine install its signal handlers
        t0 = time.time()
        r = c.post(f"/api/jobs/{a['job_id']}/cancel")
        assert r.json()["state"] == "cancelled" and not alive(pid)
        assert 0.9 <= time.time() - t0 < 5.0                      # waited out the 1 s test grace, then SIGKILL


# --------------------------------------------------------------------------- AT-M2-07
class FakeComfy(http.server.BaseHTTPRequestHandler):
    busy = True

    def do_GET(self):
        body = json.dumps({"queue_running": [["id"]] if FakeComfy.busy else [], "queue_pending": []}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_at_m2_07_mac_busy_waits_then_runs(tmp_path):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeComfy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    FakeComfy.busy = True
    try:
        with client_for(tmp_path) as c:
            url = f"http://127.0.0.1:{server.server_address[1]}/queue"
            assert c.put("/api/settings", json={"video_queue_url": url}).status_code == 200
            assert c.get("/api/system").json()["video_queue"]["state"] == "busy"
            job = post_song(c)["job_id"]
            waiting = wait_for(lambda: (j := c.get(f"/api/jobs/{job}").json())["reason"] == "mac_busy" and j,
                               what="reason mac_busy")
            assert waiting["state"] == "queued" and waiting["phase"] == "waiting"
            assert "video generator is busy" in waiting["progress"]["message"]
            time.sleep(1.0)
            assert c.get(f"/api/jobs/{job}").json()["state"] == "queued"        # still waiting, nothing started
            assert c.svc.db.one("SELECT attempts FROM jobs WHERE id=?", (job,))[0] == 0
            FakeComfy.busy = False                                              # the video queue drains
            done = wait_job(c, job)
            assert done["state"] == "succeeded" and done["reason"] is None
    finally:
        server.shutdown()


def test_at_m2_07_low_disk_rejects_submission_with_clear_error(tmp_path):
    with client_for(tmp_path) as c:
        c.svc.probe.disk_free_gib = lambda: 2.0
        r = c.post("/api/songs", json=create_body())
        assert r.status_code == 507
        err = r.json()["error"]
        assert err["code"] == "insufficient_disk" and "2.0 GiB" in err["message"] and "5.0 GiB" in err["message"]
        assert c.svc.db.one("SELECT COUNT(*) FROM songs")[0] == 0 and c.svc.db.one("SELECT COUNT(*) FROM jobs")[0] == 0
        assert c.get("/api/system").json()["disk_free_gib"] == 2.0
        c.svc.probe.disk_free_gib = lambda: 50.0
        assert c.post("/api/songs", json=create_body()).status_code == 202


def test_disk_falling_below_limit_before_start_fails_the_job(tmp_path):
    with client_for(tmp_path) as c:
        values = iter([50.0])                                    # first call (submit) fine, then 1 GiB
        c.svc.probe.disk_free_gib = lambda: next(values, 1.0)
        job = post_song(c)["job_id"]
        done = wait_job(c, job)
        assert done["state"] == "failed" and "1.0 GiB" in done["error"]


def test_unknown_video_queue_state_waits_instead_of_risking_memory(tmp_path):
    with client_for(tmp_path) as c:
        c.svc.probe.video_queue = lambda url: {"state": "unknown", "detail": "weird"}
        job = post_song(c)["job_id"]
        waiting = wait_for(lambda: (j := c.get(f"/api/jobs/{job}").json())["reason"] == "video_queue_unknown" and j)
        assert waiting["state"] == "queued"
        c.svc.probe.video_queue = lambda url: {"state": "idle"}
        assert wait_job(c, job)["state"] == "succeeded"


def test_queue_depth_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_TAKE_S", "30")
    with client_for(tmp_path) as c:
        c.put("/api/settings", json={"queue_depth_cap": 2})
        first = post_song(c)
        post_song(c)
        r = c.post("/api/songs", json=create_body())
        assert r.status_code == 429 and r.json()["error"]["code"] == "queue_full"
        c.post(f"/api/jobs/{first['job_id']}/cancel")
        assert c.post("/api/songs", json=create_body()).status_code == 202


# --------------------------------------------------------------------------- jobs: phases, failure, retry policy
def test_phases_and_progress_are_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_TAKE_S", "0.6")
    monkeypatch.setenv("RAAG_FAKE_LOAD_S", "0.4")
    with client_for(tmp_path) as c:
        job = post_song(c)["job_id"]
        seen = []
        deadline = time.time() + 30
        while time.time() < deadline:
            j = c.get(f"/api/jobs/{job}").json()
            seen.append((j["phase"], j["progress"].get("take_index")))
            if j["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.05)
        phases = [p for p, _ in dict.fromkeys(seen)]
        assert j["state"] == "succeeded"
        for expected in ("loading_model", "rendering", "checking", "done"):
            assert expected in phases, phases
        assert (("rendering", 1) in seen) and (("rendering", 2) in seen)
        assert j["progress"]["takes_completed"] == 2 and j["elapsed_s"] > 0


def test_engine_failure_fails_the_job_and_keeps_partial_for_the_sweep(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_FAIL", "1")
    with client_for(tmp_path) as c:
        data = post_song(c)
        job = wait_job(c, data["job_id"])
        assert job["state"] == "failed" and "take_failed" in job["error"] and job["attempts"] == 1
        runs = tmp_path / "runs" / data["song_id"]
        assert (runs / f"{data['round_id']}.partial").is_dir() and not (runs / data["round_id"]).exists()
        assert c.svc.db.one("SELECT COUNT(*) FROM takes")[0] == 0
    # the next boot sweeps it
    with client_for(tmp_path) as c2:
        assert not list((tmp_path / "runs").glob("*/*.partial"))


def test_technical_failure_gets_exactly_one_retry_with_a_new_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_BAD_FIRST", "1")              # take 1 comes out 2 s short on the first attempt
    with client_for(tmp_path) as c:
        data = post_song(c)
        job = wait_job(c, data["job_id"])
        assert job["state"] == "succeeded"
        assert job["progress"]["technical_failures"] == [1]
        retry = job["progress"]["retry"]
        assert retry["attempted"] and retry["ok"] and retry["for_ordinals"] == [1]
        detail = c.get(f"/api/songs/{data['song_id']}").json()
        takes = detail["takes"]
        assert len(takes) == 3                                   # 2 requested + 1 replacement; the failed one is kept
        bad = next(t for t in takes if t["technical_checks"]["status"] == "failed")
        good = next(t for t in takes if t["retry_of"] == bad["id"])
        assert bad["ordinal"] == good["ordinal"] == 1 and bad["seed"] != good["seed"]
        assert good["seed"] == retry["new_seeds"][0] and good["technical_checks"]["status"] == "passed"
        assert "duration" in bad["technical_checks"]["failures"]
        assert bad["technical_checks"]["label"].startswith("Technical checks")
        round_dir = tmp_path / "runs" / data["song_id"] / data["round_id"]
        assert (round_dir / "retry1_result.json").is_file()
        assert not list((tmp_path / "runs").glob("*/*.partial"))


def test_no_retry_when_disabled_and_none_needed_otherwise(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_BAD_FIRST", "1")
    with client_for(tmp_path) as c:
        c.put("/api/settings", json={"retry_on_technical_failure": False})
        data = post_song(c)
        job = wait_job(c, data["job_id"])
        assert job["state"] == "succeeded" and job["progress"]["retry"] is None
        assert len(c.get(f"/api/songs/{data['song_id']}").json()["takes"]) == 2


def test_job_timeout_kills_the_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_TAKE_S", "30")
    with client_for(tmp_path) as c:
        c.put("/api/settings", json={"job_timeout_s": 1})
        job = wait_job(c, post_song(c)["job_id"])
        assert job["state"] == "failed" and "too long" in job["error"]


# --------------------------------------------------------------------------- recovery rules (unit level)
def _force_running(svc, job_id, attempts):
    svc.db.execute("UPDATE jobs SET state='running', attempts=?, started_at=?, phase='rendering' WHERE id=?",
                   (attempts, now_iso(), job_id))


def test_recover_requeues_once_then_fails_and_cleans_the_store(tmp_path):
    # no lifespan: the worker is not running, so we can stage the post-crash state by hand
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from test_m2_support import make_config
    app = create_app(make_config(tmp_path))
    svc = app.state.svc
    c = TestClient(app, base_url="http://127.0.0.1:8477")
    data = c.post("/api/songs", json=create_body()).json()
    job_id, sid, rid = data["job_id"], data["song_id"], data["round_id"]
    partial = tmp_path / "runs" / sid / f"{rid}.partial"
    final = tmp_path / "runs" / sid / rid
    stray = tmp_path / "runs" / sid / "other-round"
    partial.mkdir(parents=True)
    (partial / "take_01_s1.flac").write_bytes(b"half")
    final.mkdir(parents=True)                                   # a final folder with no succeeded row
    (final / "take_01_s2.flac").write_bytes(b"orphan")
    stray.mkdir(parents=True)

    _force_running(svc, job_id, attempts=1)
    report = svc.recover()
    job = svc.job_view(job_id)
    assert job["state"] == "queued" and job["attempts"] == 1 and "re-queued" in job["error"]
    assert report["requeued"] == [job_id]
    assert not partial.exists()                                 # swept
    assert not final.exists() and not stray.exists()            # quarantined, never reused
    quarantined = list((tmp_path / "runs" / "_quarantine").iterdir())
    assert len(quarantined) == 2 and any((q / "take_01_s2.flac").is_file() for q in quarantined if q.is_dir())

    _force_running(svc, job_id, attempts=2)                     # interrupted a second time
    report = svc.recover()
    job = svc.job_view(job_id)
    assert job["state"] == "failed" and report["failed"] == [job_id]
    assert "Interrupted by a restart" in job["error"] and "giving up" in job["error"]
    assert svc.db.one("SELECT COUNT(*) FROM takes")[0] == 0


def test_recover_leaves_succeeded_rounds_alone(tmp_path):
    with client_for(tmp_path) as c:
        data = post_song(c)
        wait_job(c, data["job_id"])
        final = tmp_path / "runs" / data["song_id"] / data["round_id"]
        names = sorted(p.name for p in final.iterdir())
        report = c.svc.recover()
        assert report["quarantined"] == [] and sorted(p.name for p in final.iterdir()) == names
        exports = tmp_path / "runs" / data["song_id"] / "exports"
        exports.mkdir(exist_ok=True)
        assert c.svc.recover()["quarantined"] == []             # exports/ is never treated as a round


def test_cancel_requested_before_restart_is_honoured(tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    from test_m2_support import make_config
    app = create_app(make_config(tmp_path))
    c = TestClient(app, base_url="http://127.0.0.1:8477")
    data = c.post("/api/songs", json=create_body()).json()
    _force_running(app.state.svc, data["job_id"], attempts=1)
    app.state.svc.db.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (data["job_id"],))
    app.state.svc.recover()
    assert app.state.svc.job_view(data["job_id"])["state"] == "cancelled"
