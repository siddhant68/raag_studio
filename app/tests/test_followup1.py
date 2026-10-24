"""Follow-up 1 (handoff 2026-10-24): requested-versus-effective arrangement, and rounds that start from the right plan.

Everything runs through the HTTP API with the fake engine (RAAG_ENGINE=fake); nothing is rendered for real.
"""
import pytest

from test_m2_support import client_for, wait_job
from test_bugfix_review1 import create, caption_of

from backend import compiler
from backend.planner_base import Controls
from backend.planner_rules import BasicPlanner

BANSURI = "A peaceful bansuri at dawn"


def arrangement(report):
    return report["arrangement"]


# --------------------------------------------------------------------------- P1: effective arrangement
def test_instrumental_with_choir_lead_reports_the_real_lead_and_no_voices(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, voice="instrumental", lead="choir")
        arr = arrangement(data["compile_report"])
        assert arr["requested"]["lead"] == "choir"                       # what the user asked for stays inspectable
        assert arr["effective"]["lead"] != "choir"
        assert arr["effective"]["voice_mode"] == "instrumental" and arr["effective"]["background"] == "none"
        adj = [a for a in arr["adjustments"] if a["field"] == "lead"]
        assert len(adj) == 1 and adj[0]["requested"] == "choir" and adj[0]["effective"] == arr["effective"]["lead"]
        assert "Instrumental" in adj[0]["reason"]
        # the stored plan is untouched: history keeps the user's pick
        stored = c.get(f"/api/songs/{data['song_id']}").json()["plans"][0]["plan"]
        assert stored["lead"]["instrument"] == "choir"
        # plan, request and explanation agree: the caption describes the effective lead, not choir
        caption = caption_of(c, data["song_id"], data["round_id"]).lower()
        assert "choir" not in caption
        params = c.get(f"/api/songs/{data['song_id']}").json()["rounds"][0]["request"]["engine_request"]["params"]
        assert params["instrumental"] is True


def test_effective_lead_is_what_the_caption_names(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, voice="instrumental", lead="choir", instruments=["tabla"])
        eff = arrangement(data["compile_report"])["effective"]
        caption = caption_of(c, data["song_id"], data["round_id"]).lower()
        words = {"bansuri": "flute", "tabla": "tabla", "piano": "piano"}
        assert words.get(eff["lead"], eff["lead"]) in caption
        assert "tabla" in eff["supports"] and eff["lead"] not in eff["supports"]


def test_auto_voice_with_choir_lead_keeps_the_recorded_precedence_and_needs_no_adjustment(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief="instrumental only, no voices", lead="choir")
        assert data["plan"]["voice_mode"] == "wordless"                  # recorded user decision
        arr = arrangement(data["compile_report"])
        assert arr["effective"]["lead"] == "choir" and arr["effective"]["voice_mode"] == "wordless"
        assert not [a for a in arr["adjustments"] if a["field"] == "lead"]


def test_nothing_adjusted_means_requested_equals_effective(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI)
        arr = arrangement(data["compile_report"])
        assert arr["adjustments"] == []
        assert arr["requested"]["lead"] == arr["effective"]["lead"]
        assert arr["requested"]["supports"] == arr["effective"]["supports"]


def test_dropped_supports_are_listed_with_their_reason():
    plan = BasicPlanner().plan(BANSURI, Controls.model_validate({"voice": "instrumental", "instruments": ["choir", "tabla"]})).plan
    out = compiler.compile(plan)["compile_report"]["arrangement"]
    gone = [a for a in out["adjustments"] if a["field"] == "supports"]
    assert [a["requested"] for a in gone] == ["choir"] and "Instrumental" in gone[0]["reason"]
    assert "choir" not in out["effective"]["supports"]


def test_over_budget_support_drop_is_reported_as_an_adjustment():
    plan = BasicPlanner().plan(BANSURI, Controls.model_validate({"instruments": ["tabla", "santoor", "tanpura"]})).plan
    out = compiler.compile(plan, max_chars=420)["compile_report"]
    left = [a for a in out["arrangement"]["adjustments"] if a["field"] == "supports"]
    dropped = [d["item"] for d in out["dropped"] if d["kind"] == "support"]
    assert dropped and sorted(a["requested"] for a in left) == sorted(dropped)
    assert all(a["reason"] == "it did not fit the prompt length" for a in left)


# --------------------------------------------------------------------------- P1: selected take / retry
def test_another_from_selected_older_take_uses_its_plan_and_lineage(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, lead="bansuri")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"})
        # exactly the body the browser now sends: kind + from_take, no `takes`
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_take": t1["id"]})
        assert r.status_code == 202, r.text
        assert r.json()["plan_id"] == data["plan_id"] and r.json()["plan"]["lead"]["instrument"] == "bansuri"
        wait_job(c, r.json()["job_id"])
        detail = c.get(f"/api/songs/{sid}").json()
        rnd = detail["rounds"][-1]
        assert rnd["parent_take_id"] == t1["id"] and rnd["plan_id"] == data["plan_id"] and rnd["kind"] == "another"
        caption = rnd["request"]["caption"].lower()
        assert "flute" in caption and "piano" not in caption


def test_another_without_a_selected_take_uses_the_latest_plan(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, lead="bansuri")
        sid = data["song_id"]
        c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"})
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another"})
        assert r.status_code == 202 and r.json()["plan"]["lead"]["instrument"] == "piano"
        wait_job(c, r.json()["job_id"])
        assert c.get(f"/api/songs/{sid}").json()["rounds"][-1]["parent_take_id"] is None


def test_take_count_comes_from_the_base_plan_when_takes_is_omitted(tmp_path):
    with client_for(tmp_path) as c:
        body = {"brief": BANSURI, "duration": 10, "takes": 1}
        data = c.post("/api/songs", json=body).json()
        wait_job(c, data["job_id"])
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_take": t1["id"]})
        wait_job(c, r.json()["job_id"])
        assert len(c.get(f"/api/songs/{sid}").json()["rounds"][-1]["request"]["seeds"]) == 1


def test_retry_repeats_the_failed_rounds_own_plan_not_the_newest(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, lead="bansuri")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        first = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_take": t1["id"]}).json()
        wait_job(c, first["job_id"])
        c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"})        # a newer plan now exists
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_round": first["round_id"]})
        assert r.status_code == 202, r.text
        assert r.json()["plan_id"] == data["plan_id"] and r.json()["plan"]["lead"]["instrument"] == "bansuri"
        wait_job(c, r.json()["job_id"])
        rnd = c.get(f"/api/songs/{sid}").json()["rounds"][-1]
        assert rnd["parent_take_id"] == t1["id"]                              # lineage of the failed round is kept


def test_from_round_is_validated(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI)
        sid = data["song_id"]
        other = create(c, brief="A quiet piano night")
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        foreign = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_round": other["round_id"]})
        assert foreign.status_code == 404 and foreign.json()["error"]["code"] == "round_not_found"
        both = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_round": data["round_id"], "from_take": t1["id"]})
        assert both.status_code == 422 and both.json()["error"]["code"] == "ambiguous_base"
        wrong = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["warmer"], "from_round": data["round_id"]})
        assert wrong.status_code == 422 and wrong.json()["error"]["code"] == "from_round_needs_another"


# --------------------------------------------------------------------------- P2: recipe_id back to Auto
def test_recipe_reset_recomputes_recipe_fields_and_keeps_your_choices(tmp_path):
    from test_bugfix_review1 import auto_plan
    from backend.jobs import RECIPE_FIELDS
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, recipe_id="r2_warm_ensemble", key="G minor", lead="piano")
        sid = data["song_id"]
        before = data["plan"]
        assert before["recipe_id"] == "r2_warm_ensemble" and before["provenance"]["recipe_id"]["source"] == "you"
        r = c.patch(f"/api/songs/{sid}/controls", json={"recipe_id": None})
        assert r.status_code == 200, r.text
        after = r.json()["plan"]
        auto = auto_plan(BANSURI, key="G minor", lead="piano")
        assert after["recipe_id"] == auto["recipe_id"] != "r2_warm_ensemble"
        assert after["provenance"]["recipe_id"]["source"] != "you"
        # your own choices are exactly as they were, with their provenance
        assert after["key"] == "G minor" and after["provenance"]["key"]["source"] == "you"
        assert after["lead"]["instrument"] == "piano" and after["provenance"]["lead"]["source"] == "you"
        # everything else the recipe supplied is what Auto gives for the controls still set
        for field in ("supports", "feeling", "pace", "fullness", "arc"):
            assert after[field] == auto[field], field
            assert after["provenance"][field]["source"] != "you", field
        assert set(RECIPE_FIELDS) >= {"supports", "feeling", "pace", "fullness", "arc", "key", "lead"}
        assert "piano" not in [s["instrument"] for s in after["supports"]]
        # the stored controls lost recipe_id and nothing else
        stored = c.get(f"/api/songs/{sid}").json()["plans"][-1]["controls"]
        assert "recipe_id" not in stored and stored["key"] == "G minor" and stored["lead"] == "piano"


def test_recipe_reset_keeps_a_chip_change_made_after_the_recipe(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, recipe_id="r2_warm_ensemble")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        slower = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["slower"], "from_take": t1["id"], "takes": 1}).json()
        wait_job(c, slower["job_id"])
        pace = slower["plan"]["pace"]
        assert slower["plan"]["provenance"]["pace"]["source"] == "you"
        r = c.patch(f"/api/songs/{sid}/controls", json={"recipe_id": None})
        assert r.status_code == 200, r.text
        assert r.json()["plan"]["pace"] == pace                                 # the chip's slower pace survives
        assert r.json()["plan"]["provenance"]["pace"]["source"] == "you"


def test_plan_endpoint_refuses_null_resets_and_patch_still_resets(tmp_path):
    with client_for(tmp_path) as c:
        data = create(c, brief=BANSURI, lead="piano")
        sid = data["song_id"]
        for body in ({"controls": {"lead": None}}, {"shape": {"lead": None}}, {"voice": None}, {"recipe_id": None}):
            r = c.post(f"/api/songs/{sid}/plan", json=body)
            assert r.status_code == 422 and r.json()["error"]["code"] == "reset_not_supported", (body, r.text)
            assert "PATCH" in r.json()["error"]["message"]
        assert len(c.get(f"/api/songs/{sid}").json()["plans"]) == 1             # nothing was stored by the refusals
        ok = c.post(f"/api/songs/{sid}/plan", json={"controls": {"key": "G minor"}})
        assert ok.status_code == 200 and ok.json()["plan"]["lead"]["instrument"] == "piano"
        reset = c.patch(f"/api/songs/{sid}/controls", json={"lead": None})
        assert reset.status_code == 200 and reset.json()["plan"]["lead"]["instrument"] != "piano"


# --------------------------------------------------------------------------- P2: sung choir wording
def test_sung_choir_lead_names_the_choir_once():
    ctl = Controls.model_validate({"voice": "sung", "lead": "choir", "lyrics_text": "Dil ki baat\nsuno zara\n"})
    plan = BasicPlanner().plan("a tender song of waiting at dawn", ctl).plan
    out = compiler.compile(plan)
    caption = out["caption"].lower()
    assert caption.count("choir") == 1, caption                  # was: "choir harmonies ... over choir, felt piano"
    assert "over choir" not in caption and "over felt piano" in caption
    assert out["compile_report"]["arrangement"]["effective"]["background"] == "choir"


def test_sung_without_a_choir_lead_is_worded_as_before():
    ctl = Controls.model_validate({"voice": "sung", "background": "choir", "lyrics_text": "Dil ki baat\nsuno zara\n"})
    plan = BasicPlanner().plan("a tender song of waiting at dawn", ctl).plan
    caption = compiler.compile(plan)["caption"].lower()
    assert caption.count("choir") == 1 and "choir harmonies in the chorus over fingerpicked" in caption


def test_wordless_without_background_voices_is_an_adjustment():
    plan = BasicPlanner().plan(BANSURI, Controls.model_validate({"voice": "wordless"})).plan.model_copy(deep=True)
    plan.voices.background = "none"
    arr = compiler.compile(plan)["compile_report"]["arrangement"]
    bg = [a for a in arr["adjustments"] if a["field"] == "voices.background"]
    assert bg and bg[0]["requested"] == "none" and bg[0]["effective"] == "light" and "wordless" in bg[0]["reason"]
