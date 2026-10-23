"""M3 part A: the planner registry is wired into create / plan / refine, off the event loop, Basic by default.

No real LLM, no network, no real `claude`: smart providers are exercised only with a stub executable.
"""
import asyncio
import subprocess
import threading
import time

import httpx
import pytest

from test_m2_support import BRIEF, client_for, create_body, wait_job
from test_m4_support import Stub

from backend.planner_rules import BasicPlanner
from backend.providers.registry import FallbackPlanner


def test_default_planner_is_basic_and_smart_is_off(tmp_path):
    with client_for(tmp_path) as c:
        body = c.get("/api/settings").json()
        assert body["settings"]["planner_provider"] == "basic"
        assert body["settings"]["planner_smart_enabled"] is False
        planner = body["planner"]
        assert planner["provider"] == "basic" and planner["label"] == "Basic planner"
        assert planner["smart_enabled"] is False
        by_id = {p["id"]: p for p in planner["providers"]}
        assert by_id["basic"]["active"] is True
        assert by_id["claude_cli"]["active"] is False and by_id["anthropic_api"]["active"] is False
        assert planner["write_for_me"]["enabled"] is False and planner["write_for_me"]["reason"]
        assert "never turns them on" in planner["how_to_enable"] or "This page never" in planner["how_to_enable"]
        assert c.get("/api/system").json()["planner_provider"] == "basic"

        r = c.post("/api/songs", json=create_body())
        card = r.json()["card"]
        assert card["provider"] == "basic" and card["provider_label"] == "Basic planner" and card["is_llm"] is False
        assert card["planner_status"]["fallback"] is False
        assert card["planner_status"]["used_provider"] == "basic"
        wait_job(c, r.json()["job_id"])


def test_choosing_a_smart_provider_without_the_toggle_runs_no_subprocess_and_no_network(tmp_path, monkeypatch):
    import inspect
    import socket

    def guard(original):
        """Fail if the call comes from planner code; anything else (the render worker, the test client) is untouched."""
        def wrapper(*a, **k):
            for frame in inspect.stack()[1:]:
                name = frame.filename.replace("\\", "/")
                if "/backend/providers/" in name or "/backend/planner_" in name:
                    raise AssertionError(f"planner code started a subprocess or network call ({name})")
            return original(*a, **k)
        return wrapper
    with client_for(tmp_path) as c:
        # The user picks claude_cli but has NOT switched smart planners on.
        assert c.put("/api/settings", json={"planner_provider": "claude_cli"}).status_code == 200
        r = c.get("/api/settings").json()
        assert r["planner"]["provider"] == "basic"                      # effective provider is still Basic
        assert r["settings"]["planner_provider"] == "claude_cli"
        # From here on, any process spawn or HTTP client use by the planning path fails the test.
        monkeypatch.setattr(subprocess, "Popen", guard(subprocess.Popen))
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", guard(httpx.HTTPTransport.handle_request))
        monkeypatch.setattr(socket.socket, "connect", guard(socket.socket.connect))
        assert isinstance(c.svc.planner(), BasicPlanner)
        r = c.post("/api/songs", json=create_body(takes=1))
        assert r.status_code == 202, r.text
        assert r.json()["card"]["provider"] == "basic"
        assert c.get("/api/system").json()["planner_provider"] == "basic"


def test_fallback_banner_data_reaches_the_card_and_the_stored_plan(tmp_path):
    stub = Stub(tmp_path, [{"exit": 1, "stderr": "boom"}])             # a `claude` that always fails
    with client_for(tmp_path) as c:
        c.svc.planner = lambda: FallbackPlanner(stub.planner(), BasicPlanner())
        r = c.post("/api/songs", json=create_body(takes=1))
        assert r.status_code == 202, r.text
        data = r.json()
        card = data["card"]
        st = card["planner_status"]
        assert st["fallback"] is True
        assert st["reason"] and st["code"] and st["banner"]
        assert "Claude (local CLI)" in st["banner"] and "Basic planner" in st["banner"]
        assert st["requested_provider"] == "claude_cli" and st["used_provider"] == "basic"
        assert card["provider"] == "basic" and card["provider_label"] == "Basic planner"   # the badge names who really planned
        assert len(stub.calls) >= 1                                                      # the stub was used, and only the stub
        wait_job(c, data["job_id"])
        detail = c.get(f"/api/songs/{data['song_id']}").json()
        assert detail["plans"][0]["card"]["planner_status"]["fallback"] is True

        # plan-only path carries it too
        p = c.post(f"/api/songs/{data['song_id']}/plan", json={}).json()
        assert p["card"]["planner_status"]["fallback"] is True and p["card"]["planner_status"]["banner"]

        # refine path: chips go through the rules table, so a chip never needs the model; the status is still stored
        song = data["song_id"]
        r2 = c.post(f"/api/songs/{song}/rounds", json={"kind": "refine", "chips": ["slower"], "takes": 1})
        assert r2.status_code == 202, r2.text
        assert "planner_status" in r2.json()["card"]
        wait_job(c, r2.json()["job_id"])


def test_planner_runs_in_a_worker_thread_not_on_the_event_loop(tmp_path):
    seen = {}

    class Spy(BasicPlanner):
        def plan(self, brief, controls=None, context=None):
            seen["thread"] = threading.current_thread().name
            try:
                asyncio.get_running_loop()
                seen["on_loop"] = True
            except RuntimeError:
                seen["on_loop"] = False
            time.sleep(0.8)                                              # a slow smart provider
            return super().plan(brief, controls, context)

    with client_for(tmp_path) as c:
        c.svc.planner = lambda: Spy()
        result = {}

        def create():
            result["r"] = c.post("/api/songs", json=create_body(takes=1))
        t = threading.Thread(target=create)
        t.start()
        time.sleep(0.2)
        t0 = time.time()
        assert c.get("/api/settings").status_code == 200                 # still answered while the planner sleeps
        assert time.time() - t0 < 0.6
        t.join(timeout=20)
        assert result["r"].status_code == 202
        assert seen["on_loop"] is False
        wait_job(c, result["r"].json()["job_id"])


def test_new_read_only_endpoints(tmp_path):
    with client_for(tmp_path) as c:
        rec = c.get("/api/recipes").json()
        ids = [r["id"] for r in rec["recipes"]]
        assert ids == ["r1_flute_focus", "r2_warm_ensemble", "r3_hindi_ballad"]      # R4 hidden until rated
        assert rec["hidden_count"] == 1
        assert next(r for r in rec["recipes"] if r["id"] == "r3_hindi_ballad")["experimental"] is True

        caps = c.get("/api/capabilities").json()
        assert [f"C{i}" for i in range(1, 26)] == list(caps["controls"])
        assert caps["controls"]["C8"]["labels"] and caps["controls"]["C1"]["labels"] == []
        assert caps["controls"]["C15"]["needs_label"] is True

        ins = c.get("/api/instruments").json()["instruments"]
        assert len(ins) == 15 and {i["id"] for i in ins} >= {"bansuri", "tabla"}

        led = c.get("/api/ledger").json()
        assert led["totals"]["takes"] == 0 and led["by_recipe"] == {}


def test_ledger_counts_match_seeded_feedback(tmp_path):
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json=create_body(takes=3, duration=10)).json()
        wait_job(c, r["job_id"])
        takes = c.get(f"/api/songs/{r['song_id']}").json()["takes"]
        assert len(takes) == 3
        c.post(f"/api/takes/{takes[0]['id']}/feedback", json={"favourite": True, "rating": "love"})
        c.post(f"/api/takes/{takes[1]['id']}/feedback", json={"rating": "no"})
        led = c.get("/api/ledger").json()
        assert led["totals"] == {"takes": 3, "loved": 1, "fine": 0, "no": 1, "favourites": 1, "unrated": 1}
        assert led["by_lead"]["bansuri"]["takes"] == 3 and led["by_lead"]["bansuri"]["loved"] == 1
        assert sum(v["takes"] for v in led["by_recipe"].values()) == 3
