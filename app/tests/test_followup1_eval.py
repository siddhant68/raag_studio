"""The independent planner-evaluation harness: well-formed fixture, offline, honest scoring, recorded-plan path."""
import json
import socket
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from experiments import eval_planner  # noqa: E402
from backend.planner_rules import BasicPlanner  # noqa: E402


def test_fixture_is_independent_and_covers_the_handoff_dimensions():
    briefs = eval_planner.load()
    assert len(briefs) >= 20 and len({b["id"] for b in briefs}) == len(briefs)
    original = {json.loads(ln)["brief"].lower() for ln in (APP / "tests/fixtures/briefs.jsonl").read_text("utf-8").splitlines() if ln.strip()}
    assert not [b["id"] for b in briefs if b["brief"].lower() in original]          # none borrowed from the author's set
    dims = {d for b in briefs for d in b["dimensions"]}
    assert {"lead_support", "exclusion", "story", "progression", "entrances", "conflict", "voice", "lyrics", "duration",
            "copyright", "compact"} <= dims


def test_basic_planner_is_scored_without_any_network_and_without_a_pass_mark(monkeypatch):
    def no_net(*a, **k):
        raise AssertionError("the evaluation must not open a network connection")
    monkeypatch.setattr(socket.socket, "connect", no_net)
    briefs = eval_planner.load()
    planner = BasicPlanner()
    out = eval_planner.evaluate({b["id"]: planner.plan(b["brief"]) for b in briefs}, briefs)
    assert out["all_compile"] and out["briefs_scored"] >= 20
    # an honest harness does not hand the keyword planner a perfect score on briefs it was not written against
    assert out["briefs_fully_right"] < out["briefs_scored"]
    assert out["by_dimension"]["progression"]["right"] < out["by_dimension"]["progression"]["of"]


def test_recorded_plans_are_scored_like_live_ones(tmp_path, capsys):
    briefs = eval_planner.load()
    planner = BasicPlanner()
    recorded = {b["id"]: planner.plan(b["brief"]).model_dump(mode="json") for b in briefs}
    path = tmp_path / "plans.json"
    path.write_text(json.dumps(recorded), "utf-8")
    result = tmp_path / "out.json"
    assert eval_planner.main(["--plans", str(path), "--json", str(result)]) == 0
    live = eval_planner.evaluate({b["id"]: planner.plan(b["brief"]) for b in briefs}, briefs)
    assert json.loads(result.read_text("utf-8"))["by_dimension"] == live["by_dimension"]


def test_missing_recorded_plan_is_an_error_not_a_silent_skip(tmp_path):
    path = tmp_path / "plans.json"
    path.write_text("{}", "utf-8")
    with pytest.raises(SystemExit):
        eval_planner.main(["--plans", str(path)])


def test_live_run_where_every_plan_falls_back_scores_nothing(tmp_path, monkeypatch, capsys):
    """A provider that never answers must not produce a 'smart planner' score made of Basic plans."""
    from backend.planner_base import PlannerUnavailable
    from backend.providers import registry
    from backend.providers.claude_cli import ClaudeCliPlanner

    class Dead(ClaudeCliPlanner):
        def _transport(self, *a, **k):
            raise PlannerUnavailable("Failed to authenticate: OAuth session expired", code="planner_cli_failed")
    monkeypatch.setattr(registry, "ClaudeCliPlanner", lambda **kw: Dead(**kw))
    rec = tmp_path / "plans.json"
    assert eval_planner.main(["--live", "claude_cli", "--record", str(rec)]) == 2
    assert not rec.exists()
    out = capsys.readouterr().out
    assert "nothing was scored" in out and "OAuth session expired" in out
