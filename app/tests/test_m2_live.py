"""Tests that need a real uvicorn process: AT-M2-05 (kill -9 mid-job) and the SSE stream (/api/events)."""
import json
import os
import threading
import time

import httpx

from test_m2_support import BRIEF, LiveServer, create_body


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait_until(fn, timeout=40, what="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"timed out waiting for {what}")


def job_of(base, job_id):
    return httpx.get(f"{base}/api/jobs/{job_id}", timeout=10).json()


def test_at_m2_05_kill9_requeues_once_then_fails(tmp_path):
    env = {"RAAG_FAKE_TAKE_S": "2.5"}                  # two takes -> about 5 s of "rendering"
    runs = tmp_path / "runs"
    server = LiveServer(tmp_path, **env).start()
    servers = [server]
    try:
        r = httpx.post(f"{server.base}/api/songs", json=create_body(), timeout=10)
        assert r.status_code == 202
        data = r.json()
        job_id, sid, rid = data["job_id"], data["song_id"], data["round_id"]

        # ---- first interruption: kill -9 while take 1 renders
        running = wait_until(lambda: (j := job_of(server.base, job_id))["state"] == "running"
                             and j["worker_pid"] and j["phase"] == "rendering" and j, what="running")
        engine_pid = running["worker_pid"]
        assert alive(engine_pid)
        assert (runs / sid / f"{rid}.partial").is_dir()
        server.kill9()

        server = LiveServer(tmp_path, port=server.port, **env).start()
        servers.append(server)
        # recovery already ran at boot: the engine orphan is gone, the job was re-queued exactly once
        assert not alive(engine_pid)
        done = wait_until(lambda: (j := job_of(server.base, job_id))["state"] == "succeeded" and j, timeout=60,
                          what="re-queued job to succeed")
        assert done["attempts"] == 2
        detail = httpx.get(f"{server.base}/api/songs/{sid}", timeout=10).json()
        assert len(detail["takes"]) == 2                                      # no duplicate takes
        assert len({t["seed"] for t in detail["takes"]}) == 2
        assert not list(runs.glob("*/*.partial"))                             # swept / renamed
        assert [d.name for d in (runs / sid).iterdir() if d.name != "exports"] == [rid]
        assert not (runs / "_quarantine").exists()
        stale_errors = detail["rounds"][0]["job"]["error"]
        assert stale_errors is None                                           # success clears the interruption note

        # ---- second job, interrupted TWICE: re-queued once, then failed with a reason
        r = httpx.post(f"{server.base}/api/songs", json=create_body(brief=BRIEF + " again"), timeout=10)
        job2, sid2, rid2 = r.json()["job_id"], r.json()["song_id"], r.json()["round_id"]
        wait_until(lambda: (j := job_of(server.base, job2))["state"] == "running" and j["phase"] == "rendering" and j)
        server.kill9()
        server = LiveServer(tmp_path, port=server.port, **env).start()
        servers.append(server)
        j = wait_until(lambda: (j := job_of(server.base, job2))["state"] == "running" and j["attempts"] == 2
                       and j["phase"] == "rendering" and j, what="second attempt running")
        assert j["attempts"] == 2
        server.kill9()                                                        # second interruption
        server = LiveServer(tmp_path, port=server.port, **env).start()
        servers.append(server)
        failed = job_of(server.base, job2)
        assert failed["state"] == "failed" and failed["attempts"] == 2
        assert "Interrupted by a restart" in failed["error"] and "giving up" in failed["error"]
        d2 = httpx.get(f"{server.base}/api/songs/{sid2}", timeout=10).json()
        assert d2["takes"] == []
        assert not list(runs.glob("*/*.partial")) and not (runs / sid2 / rid2).exists()
        # the failed job never blocks the queue
        r = httpx.post(f"{server.base}/api/songs", json=create_body(brief=BRIEF + " third"), timeout=10)
        wait_until(lambda: job_of(server.base, r.json()["job_id"])["state"] == "succeeded", timeout=60)
    finally:
        for s in servers:
            s.stop()


def test_sse_stream_reports_job_progress_and_take_done(tmp_path):
    server = LiveServer(tmp_path, RAAG_FAKE_TAKE_S="0.5").start()
    events, ready = [], threading.Event()

    def reader():
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("GET", f"{server.base}/api/events") as resp:
                    assert resp.headers["content-type"].startswith("text/event-stream")
                    name, data = None, None
                    for line in resp.iter_lines():
                        if line.startswith(": connected"):
                            ready.set()
                        elif line.startswith("event:"):
                            name = line[6:].strip()
                        elif line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                        elif line == "" and name:
                            events.append((name, data))
                            name, data = None, None
        except httpx.HTTPError:
            pass                                   # the server was stopped at the end of the test
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    try:
        assert ready.wait(10)
        r = httpx.post(f"{server.base}/api/songs", json=create_body(), timeout=10)
        job_id = r.json()["job_id"]
        wait_until(lambda: any(n == "takes_ready" for n, _ in events), timeout=30, what="takes_ready event")
        names = [n for n, _ in events]
        assert names[0] == "hello" and events[0][1]["engine"] == "fake"
        jobs = [d for n, d in events if n == "job" and d["id"] == job_id]
        phases = [d["phase"] for d in jobs]
        for expected in ("queued", "starting", "loading_model", "rendering", "checking", "done"):
            assert expected in phases, phases
        assert [d["state"] for d in jobs][-1] == "succeeded"
        done = [d for n, d in events if n == "take_done"]
        assert [d["index"] for d in done] == [1, 2] and all(d["job_id"] == job_id and d["engine"] == "fake" for d in done)
        ready_ev = next(d for n, d in events if n == "takes_ready")
        assert len(ready_ev["takes"]) == 2 and ready_ev["engine"] == "fake"
    finally:
        server.stop()
