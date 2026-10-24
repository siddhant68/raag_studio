"""Showcase batch: the spec, prepare (scripted songwriter), render through the FAKE engine into a scratch folder,
the refusal to put test audio into showcase/, failures recorded without retry, and publish never on master.

Nothing here is a real render; the fake engine writes sine tones and every artefact says so.
"""
import copy
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import lyric_craft, song_blueprint, song_plan, songwriter  # noqa: E402
from backend.providers import LlmPlanner  # noqa: E402
from experiments import showcase  # noqa: E402

SPEC = showcase.load_spec()
BY_N = {t["n"]: t for t in SPEC["takes"]}


class Scripted(LlmPlanner):
    name, label = "scripted", "Scripted"

    def __init__(self, answers):
        super().__init__(enabled=True)
        self.answers, self.seen = list(answers), []

    def _transport(self, system, user, schema, tool_name):
        self.seen.append({"system": system, "user": user, "tool": tool_name})
        return self.answers.pop(0)


class Refuses(LlmPlanner):
    name, label = "refuses", "Refuses"

    def __init__(self):
        super().__init__(enabled=True)

    def _transport(self, system, user, schema, tool_name):
        raise AssertionError("the songwriter must not be called when lyrics are saved")


HINDI_LINES = ["खिड़की पे धूप रुकी है", "चाय की खुशबू ठहरी है", "शाम की बातें बाकी हैं", "दिल की धड़कन धीमी है",
               "रस्ते पे बारिश गिरी है", "छत पे हवा चली है", "आँगन में चुप बैठी है", "गलियों में रात ढली है"]


def _answer(t, chorus_first=None):
    """A complete answer for take t: the chorus starts with `chorus_first` (the supplied hook by default)."""
    bp = song_plan.blueprint_for(showcase.plan_for_take(t))
    secs, used = [], 0
    for s in bp.lyric_slots:
        if s["uid"] == "chorus":
            head = list(t["hook"] if chorus_first is None else chorus_first)
            lines = (head + ["साथ रहे ये पल यहीं", "धीरे धीरे रात ढले"])[: s["lines"]]
        else:                                                   # every section different from the others
            lines = [HINDI_LINES[(used + i) % len(HINDI_LINES)] + ("" if used + i < len(HINDI_LINES) else " फिर")
                     for i in range(s["lines"])]
            used += s["lines"]
        secs.append({"uid": s["uid"], "lines": lines})
    return {"title": t["hook"][0], "hook": t["hook"][0], "sections": secs}


def _spec_with(*ns):
    spec = copy.deepcopy(SPEC)
    spec["takes"] = [copy.deepcopy(BY_N[n]) for n in ns]
    return spec


# ------------------------------------------------------------------------------------------------ the spec
def test_spec_is_twelve_briefs_one_take_each():
    assert [t["n"] for t in SPEC["takes"]] == list(range(1, 13))
    assert SPEC["takes_per_brief"] == 1 and SPEC["profile"] == "shift3"
    assert len({t["slug"] for t in SPEC["takes"]}) == 12
    for t in SPEC["takes"]:
        assert len(t["flavour"]) <= 120 and t["targets"]
        if t["voice"] == "sung":
            assert len(t["hook"]) == 2 and t["theme"] and t["language"] in ("hi", "en")
    assert sum(t["voice"] == "sung" for t in SPEC["takes"]) == 8


@pytest.mark.parametrize("n", range(1, 13))
def test_every_brief_keeps_its_requested_values_and_sections(n):
    t = BY_N[n]
    plan = showcase.plan_for_take(t)
    assert plan.pipeline == "song" and plan.genre == t["genre"]
    assert (plan.duration_s, plan.pace.bpm, plan.meter) == (t["duration_s"], t["bpm"], t["meter"])
    assert plan.voice_mode == t["voice"] and plan.lead.instrument == t["lead"]
    assert [s.instrument for s in plan.supports] == [s["instrument"] for s in t["supports"]]
    assert plan.flavour == t["flavour"] and plan.provenance["flavour"].source == "you"
    bp = song_plan.blueprint_for(plan)
    kinds = [s.kind for s in bp.sections]
    for need in t.get("require_sections", []):
        assert need in kinds, (n, need, bp.summary())
    if t["voice"] == "sung":                                   # every lyrical song has a returning chorus
        assert kinds.count("chorus") >= 2, bp.summary()
        assert plan.voices.singer == t["singer"] and plan.voices.language == t["language"]


def test_edm_keeps_verse_pre_chorus_returning_chorus_and_breakdown_at_150s():
    lay, info = song_blueprint.fit_form("edm", bpm=126, target_s=150, require=("pre_chorus", "chorus", "bridge"))
    names = [st.name for st, _, _ in lay]
    assert names.count("Chorus") == 2 and "Pre-Chorus" in names and "Breakdown" in names
    assert info["lines_per_verse"] == 4                         # intro and outro gave way, not the sung verse


def test_required_hook_helpers():
    hook = ["थोड़ी देर और मेरे पास रह", "जो कह न सके, वो आज कह"]
    assert songwriter.hook_present({"chorus": ["कुछ और", *hook, "फिर"]}, hook)
    assert songwriter.hook_present({"chorus": [hook[0] + "  ", hook[1]]}, hook)           # spacing aside
    assert not songwriter.hook_present({"chorus": [hook[1], hook[0]]}, hook)              # order matters
    fixed = songwriter.enforce_hook({"chorus": ["एक", "दो", "तीन", "चार"], "verse_1": ["x"]}, hook)
    assert fixed["chorus"] == [*hook, "एक", "दो"] and fixed["verse_1"] == ["x"]


# ------------------------------------------------------------------------------------------------ prepare
def test_prepare_instrumentals_writes_requests_seeds_ratings_and_readme(tmp_path):
    show, runs = tmp_path / "show", tmp_path / "runs"
    spec = _spec_with(1, 2, 3, 4)
    out = showcase.prepare(spec, show_dir=show, runs_dir=runs)
    assert [s for _, s in out["prepared"]] == ["prepared"] * 4
    seeds = []
    for t in spec["takes"]:
        d = show / "takes" / showcase.take_dir_name(t)
        for f in ("brief.md", "plan.json", "caption.txt", "request.json", "compile_report.json", "take.json"):
            assert (d / f).is_file(), f
        req = json.loads((d / "request.json").read_text())
        info = json.loads((d / "take.json").read_text())
        assert req["params"]["shift"] == 3.0 and req["params"]["thinking"] is False and "model" not in req
        assert req["params"]["instrumental"] is True and req["params"]["duration"] == t["duration_s"]
        assert req["params"]["bpm"] == t["bpm"] and req["seeds"] == [info["seed"]]
        assert info["render"]["status"] == "not_rendered" and info["listening"]["verdict"] == "pending"
        assert "not guaranteed" in (d / "brief.md").read_text()
        seeds.append(info["seed"])
    full = showcase.prepare(_spec_with(1), show_dir=tmp_path / "again", runs_dir=runs)
    assert full["prepared"] == [(1, "prepared")]
    assert json.loads((tmp_path / "again/takes/01_river_waking_up/take.json").read_text())["seed"] == seeds[0]
    rows = list(csv.DictReader(open(show / "ratings.csv", encoding="utf-8")))
    assert [r["take"] for r in rows] == ["1", "2", "3", "4"]
    assert list(rows[0]) == showcase.RATING_FIELDS
    assert all(not r[k] for r in rows for k in showcase.RATING_FIELDS[3:])        # every rating blank
    readme = (show / "README.md").read_text()
    assert "Not rendered yet" in readme and "| pending |" in readme and "(no audio yet)" in readme


def test_prepare_song_keeps_the_hook_and_saves_every_draft(tmp_path):
    t = BY_N[5]
    wrong = ["थोड़ी देर और पास रह", "जो कह न सके वो कह"]                      # the songwriter changed the hook twice
    p = Scripted([_answer(t, chorus_first=wrong), _answer(t, chorus_first=wrong)])
    showcase.prepare(_spec_with(5), show_dir=tmp_path / "show", runs_dir=tmp_path / "runs", planner=p)
    assert len(p.seen) == 2 and "word for word" in p.seen[0]["user"] and t["hook"][0] in p.seen[0]["user"]
    d = tmp_path / "show/takes/05_thodi_der_aur"
    rec = json.loads((d / "songwriter.json").read_text())
    assert [x["stage"] for x in rec["drafts"]] == ["draft", "revision"]
    assert any("hook" in m for m in rec["drafts"][1]["asked_to_fix"])
    assert rec["notes"] and "put it at the start of the chorus" in rec["notes"][0]
    sheet = (d / "lyrics.txt").read_text()
    choruses = [lines for tag, lines in lyric_craft.parse_tagged(sheet) if "Chorus" in tag]
    assert len(choruses) >= 2 and all(c[:2] == t["hook"] for c in choruses)
    assert "[Verse 1]" in sheet and " - " not in sheet                         # section names only, no direction
    plan = json.loads((d / "plan.json").read_text())
    assert plan["lyrics"]["text"] == sheet.rstrip("\n") and plan["require_sections"] == ["bridge"]
    req = json.loads((d / "request.json").read_text())
    assert req["params"]["lyrics"] == plan["lyrics"]["text"] and req["params"]["vocal_language"] == "hi"


def test_prepare_keeps_saved_lyrics(tmp_path):
    t = BY_N[5]
    show = tmp_path / "show"
    showcase.prepare(_spec_with(5), show_dir=show, runs_dir=tmp_path / "runs", planner=Scripted([_answer(t)]))
    first = (show / "takes/05_thodi_der_aur/lyrics.txt").read_text()
    showcase.prepare(_spec_with(5), show_dir=show, runs_dir=tmp_path / "runs", planner=Refuses())
    assert (show / "takes/05_thodi_der_aur/lyrics.txt").read_text() == first


def test_duet_sheet_names_who_sings(tmp_path):
    t = BY_N[7]
    showcase.prepare(_spec_with(7), show_dir=tmp_path / "show", runs_dir=tmp_path / "r", planner=Scripted([_answer(t)]))
    sheet = (tmp_path / "show/takes/07_yahin_kahin_duet/lyrics.txt").read_text()
    assert "[Verse 1 - male vocal]" in sheet and "[Verse 2 - female vocal]" in sheet and "- duet]" in sheet


# ------------------------------------------------------------------------------------------------ render
def _fake(spec, tmp_path, **kw):
    return showcase.render(spec, show_dir=tmp_path / "show", runs_dir=tmp_path / "runs", yes=True,
                           engine_cmd=[sys.executable, str(showcase.FAKE_ENGINE)], check=lambda: {}, fake=True, **kw)


def test_fake_render_into_a_scratch_folder_makes_a_loudness_matched_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_LOAD_S", "0")
    spec = _spec_with(2)
    showcase.prepare(spec, show_dir=tmp_path / "show", runs_dir=tmp_path / "runs")
    assert _fake(spec, tmp_path)["rendered"] == 1
    info = json.loads((tmp_path / "show/takes/02_midnight_cafe/take.json").read_text())
    r = info["render"]
    assert r["status"] == "rendered" and r["fake_engine"] is True and r["engine"]["fake"] is True
    c = r["listening_copy"]
    assert (tmp_path / "show/audio/02_midnight_cafe.mp3").is_file() and c["decode_ok"]
    assert abs(c["integrated_lufs"] - showcase.TARGET_LUFS) < 1.5 and c["true_peak_dbtp"] <= showcase.MAX_COPY_TP
    assert c["clipped_fraction"] == 0
    assert (tmp_path / "runs/02_midnight_cafe").is_dir()                      # native output kept, never overwritten
    summary = json.loads((tmp_path / "show/technical_summary.json").read_text())
    assert summary["takes"][0]["status"] == "rendered" and summary["takes"][0]["channels"] == 2
    assert "1 of 1 takes rendered" in (tmp_path / "show/README.md").read_text()
    assert _fake(spec, tmp_path) == {"rendered": 0}                            # never rendered twice


def test_test_engine_audio_never_goes_into_showcase(tmp_path):
    with pytest.raises(SystemExit, match="never written into showcase"):
        showcase.render(_spec_with(1), show_dir=showcase.ROOT / "showcase" / "x", runs_dir=tmp_path, fake=True)


def test_a_failed_take_is_recorded_and_not_retried(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_FAIL", "1")
    spec = _spec_with(1, 2)
    showcase.prepare(spec, show_dir=tmp_path / "show", runs_dir=tmp_path / "runs")
    out = _fake(spec, tmp_path)
    assert out["rendered"] == 0
    for t in spec["takes"]:
        info = json.loads((tmp_path / "show/takes" / showcase.take_dir_name(t) / "take.json").read_text())
        assert info["render"]["status"] == "failed"
    monkeypatch.delenv("RAAG_FAKE_FAIL")
    assert _fake(spec, tmp_path) == {"rendered": 0}                            # failures stay failures
    assert "Failed takes (not retried)" in (tmp_path / "show/technical_summary.md").read_text()
    assert not list((tmp_path / "show").glob("audio/*.mp3"))


def test_render_does_not_start_when_the_machine_is_not_ready(tmp_path):
    spec = _spec_with(1)
    showcase.prepare(spec, show_dir=tmp_path / "show", runs_dir=tmp_path / "runs")
    out = showcase.render(spec, show_dir=tmp_path / "show", runs_dir=tmp_path / "runs", yes=True,
                          engine_cmd=["false"], check=lambda: {"mps": False, "disk_free_gib": 2.0,
                                                                "video_queue": {"state": "busy"}})
    assert out["rendered"] == 0 and len(out["blockers"]) >= 3
    assert not (tmp_path / "runs").exists() or not list((tmp_path / "runs").iterdir())


def test_render_refuses_takes_that_were_not_prepared(tmp_path):
    with pytest.raises(SystemExit, match="not prepared"):
        _fake(_spec_with(1), tmp_path)


# ------------------------------------------------------------------------------------------------ publish
@pytest.mark.parametrize("branch", ["master", "main", ""])
def test_publish_never_commits_on_master(monkeypatch, branch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=branch + "\n", stderr="")
    monkeypatch.setattr(showcase.subprocess, "run", fake_run)
    with pytest.raises(SystemExit, match="refusing to publish"):
        showcase.publish(SPEC, showcase.paths(SPEC)[1])
    assert len(calls) == 1                                                     # only the branch was read


def test_listening_copies_are_not_ignored_by_git():
    rel = f"showcase/{SPEC['id']}/audio/01_river_waking_up.mp3"
    out = subprocess.run(["git", "-C", str(showcase.ROOT), "check-ignore", "-q", rel])
    assert out.returncode == 1                                                 # 1 = not ignored
    native = subprocess.run(["git", "-C", str(showcase.ROOT), "check-ignore", "-q",
                             f"runs/_showcase/{SPEC['id']}/01_river_waking_up/take_1.flac"])
    assert native.returncode == 0
