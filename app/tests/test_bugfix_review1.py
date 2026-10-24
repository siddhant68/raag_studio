"""Regression tests for the four bugs found in the first independent review (reports/BUGFIX_REVIEW1.md).

1. choir had no ROLE entry (KeyError -> 500) and a choir lead was rendered as an instrumental piece "Strictly no voices."
2. refine from a take used the latest plan instead of the selected take's plan.
3. PATCH /controls with null (back to Auto) dropped the stored control but kept the old value and its "you" provenance.
4. "What changed" entries had three different shapes; one schema {field, from, to, source} now.

All of it runs through the HTTP API with the fake engine (RAAG_ENGINE=fake); nothing is rendered for real.
"""
import pytest

from test_m2_support import client_for, wait_job

# These tests pin the classic template compiler's contract (its caption slots, "Auto" = the Basic planner's card,
# recipe resets). The song pipeline has its own tests in test_song_pipeline.py.
CLASSIC = {"RAAG_SONG_PIPELINE": "0"}

from backend import compiler
from backend.plan_schema import INSTRUMENT_IDS, Plan
from backend.planner_base import Controls
from backend.planner_rules import ROLE, BasicPlanner

QUIET = "A peaceful melody for a quiet morning"
CHANGE_KEYS = {"field", "from", "to", "source"}


def create(c, brief=QUIET, **controls):
    body = {"brief": brief, "duration": 10, "takes": 1}
    voice = controls.pop("voice", None)
    if voice:
        body["voice"] = voice
    if "lyrics" in controls:
        body["lyrics"] = controls.pop("lyrics")
    if controls:
        body["controls"] = controls
    r = c.post("/api/songs", json=body)
    assert r.status_code == 202, r.text
    data = r.json()
    wait_job(c, data["job_id"])
    return data


def caption_of(c, song_id, round_id):
    detail = c.get(f"/api/songs/{song_id}").json()
    return next(r for r in detail["rounds"] if r["id"] == round_id)["request"]["caption"]


def slot(report, name):
    return next((t for n, t in report["slots"] if n == name), "")


# --------------------------------------------------------------------------- bug 1: choir
def test_every_allow_listed_instrument_has_a_role():
    assert set(ROLE) == set(INSTRUMENT_IDS)


@pytest.mark.parametrize("controls", [{"instruments": ["choir"]}, {"lead": "choir"}])
def test_choir_with_voice_auto_infers_wordless_voices(tmp_path, controls):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, **controls)                            # was: KeyError('choir') / instrumental plan
        plan = data["plan"]
        assert plan["voice_mode"] == "wordless"
        prov = plan["provenance"]["voice_mode"]
        assert prov["source"] == "suggested" and "choir" in prov["reason"]
        assert plan["voices"]["background"] == "choir"
        report = data["compile_report"]
        assert "Strictly no voices" not in slot(report, "tail")
        caption = caption_of(c, data["song_id"], data["round_id"])
        assert "Strictly no voices" not in caption
        params = c.get(f"/api/songs/{data['song_id']}").json()["rounds"][0]["request"]["engine_request"]["params"]
        assert params["instrumental"] is False


def test_choir_support_with_explicit_instrumental_is_a_reported_conflict(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, voice="instrumental", instruments=["choir", "tabla"])
        assert data["plan"]["voice_mode"] == "instrumental"
        assert any(x["kind"] == "instrumental_with_choir" for x in data["compile_report"]["conflicts"])
        assert any("choir" in n.lower() and "instrumental" in n.lower() for n in data["card"]["notes"])
        assert "choir" not in caption_of(c, data["song_id"], data["round_id"]).lower()


def test_choir_lead_with_explicit_instrumental_never_says_choir_leads(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, voice="instrumental", lead="choir", instruments=["piano"])
        assert data["plan"]["voice_mode"] == "instrumental"
        conflicts = [x for x in data["compile_report"]["conflicts"] if x["kind"] == "instrumental_with_choir"]
        assert conflicts and "lead" in conflicts[0]["detail"]
        assert any("choir" in n.lower() for n in data["card"]["notes"])
        caption = caption_of(c, data["song_id"], data["round_id"])
        assert "choir" not in caption.lower() and "choir" not in slot(data["compile_report"], "lead_priority").lower()
        assert caption.endswith("Strictly no voices.")                              # the tail now fits the piece


def test_compiler_resolves_instrumental_choir_lead_without_a_planner():
    plan = BasicPlanner().plan(QUIET, Controls(voice="instrumental")).plan
    d = plan.model_dump(mode="json")
    d["lead"]["instrument"], d["supports"] = "choir", []
    out = compiler.compile(Plan.model_validate(d))["compile_report"]
    assert any(x["kind"] == "instrumental_with_choir" for x in out["conflicts"])
    assert "choir" not in " ".join(t for _, t in out["slots"]).lower()


@pytest.mark.parametrize("role", ["instruments", "lead"])
def test_every_allow_listed_instrument_as_support_and_lead_gives_a_plan_or_a_4xx(tmp_path, role):
    with client_for(tmp_path, **CLASSIC) as c:
        for inst in INSTRUMENT_IDS:
            ctl = {"instruments": [inst]} if role == "instruments" else {"lead": inst}
            r = c.post("/api/songs", json={"brief": QUIET, "controls": ctl, "duration": 10, "takes": 1})
            assert r.status_code < 500, (role, inst, r.text)
            body = r.json()
            if r.status_code != 202:
                assert 400 <= r.status_code < 500 and body["error"]["message"], (role, inst, body)
                continue
            plan = body["plan"]
            if inst == "choir":
                assert plan["voice_mode"] == "wordless", (role, inst)
            else:
                assert plan["voice_mode"] == "instrumental", (role, inst)
            if role == "lead":
                assert plan["lead"]["instrument"] == inst
                assert inst not in [s["instrument"] for s in plan["supports"]], (role, inst)
            elif inst != plan["lead"]["instrument"]:                  # picking the recipe's own lead as a support is a no-op
                assert inst in [s["instrument"] for s in plan["supports"]], (role, inst)
            tail = slot(body["compile_report"], "tail")
            assert ("Strictly no voices" in tail) == (plan["voice_mode"] == "instrumental"), (role, inst, tail)
            wait_job(c, body["job_id"])


def test_patching_choir_in_and_out_follows_the_same_rule(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c)
        sid = data["song_id"]
        assert data["plan"]["voice_mode"] == "instrumental"
        r = c.patch(f"/api/songs/{sid}/controls", json={"lead": "choir"})
        assert r.status_code == 200, r.text
        assert r.json()["plan"]["voice_mode"] == "wordless"
        assert r.json()["plan"]["provenance"]["voice_mode"]["source"] == "suggested"
        r = c.patch(f"/api/songs/{sid}/controls", json={"lead": None})            # back to Auto: the inference goes too
        plan = r.json()["plan"]
        assert plan["lead"]["instrument"] != "choir" and plan["voice_mode"] == "instrumental"
        c.patch(f"/api/songs/{sid}/controls", json={"voice": "instrumental"})
        r = c.patch(f"/api/songs/{sid}/controls", json={"lead": "choir"})          # explicit Instrumental is kept
        assert r.json()["plan"]["voice_mode"] == "instrumental"
        assert any(x["kind"] == "instrumental_with_choir" for x in r.json()["compile_report"]["conflicts"])


# --------------------------------------------------------------------------- bug 2: refine from a take
def test_refine_from_take_uses_that_takes_plan_not_the_latest(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, brief="A peaceful bansuri at dawn", lead="bansuri")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        rev1 = c.get(f"/api/songs/{sid}").json()["plans"][0]
        patched = c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"}).json()
        assert patched["plan_rev"] == 2 and patched["plan"]["lead"]["instrument"] == "piano"

        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["warmer"], "from_take": t1["id"],
                                                     "takes": 1})
        assert r.status_code == 202, r.text
        out = r.json()
        assert out["plan"]["lead"]["instrument"] == "bansuri"                   # was: piano
        assert out["plan_rev"] == 3                                              # monotonic per song
        assert "warm" in out["plan"]["feeling"]
        wait_job(c, out["job_id"])
        detail = c.get(f"/api/songs/{sid}").json()
        new_plan = detail["plans"][-1]
        assert new_plan["rev"] == 3 and new_plan["controls"] == rev1["controls"]
        assert new_plan["provenance"]["lead"]["source"] == rev1["provenance"]["lead"]["source"] == "you"
        refine_round = detail["rounds"][-1]
        assert refine_round["parent_take_id"] == t1["id"] and refine_round["plan_id"] == new_plan["id"]
        caption = caption_of(c, sid, out["round_id"]).lower()
        assert "flute" in caption and "piano" not in caption


def test_refine_without_from_take_still_uses_the_latest_plan(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, brief="A peaceful bansuri at dawn", lead="bansuri")
        sid = data["song_id"]
        c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"})
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["warmer"], "takes": 1})
        assert r.status_code == 202, r.text
        assert r.json()["plan"]["lead"]["instrument"] == "piano" and r.json()["plan_rev"] == 3
        wait_job(c, r.json()["job_id"])


def test_another_from_take_reuses_that_takes_plan_and_foreign_take_is_404(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, brief="A peaceful bansuri at dawn", lead="bansuri")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        c.patch(f"/api/songs/{sid}/controls", json={"lead": "piano"})
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "from_take": t1["id"], "takes": 1})
        assert r.status_code == 202 and r.json()["plan_id"] == data["plan_id"]
        wait_job(c, r.json()["job_id"])
        other = create(c, brief="A quiet piano night")
        foreign = c.get(f"/api/songs/{other['song_id']}").json()["takes"][0]["id"]
        bad = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["warmer"], "from_take": foreign})
        assert bad.status_code == 404 and bad.json()["error"]["code"] == "take_not_found"


# --------------------------------------------------------------------------- bug 3: null resets
def auto_plan(brief, **remaining) -> dict:
    """What the planner gives for the brief and the controls that are still set (the definition of 'Auto')."""
    return BasicPlanner().plan(brief, Controls(**remaining)).plan.model_dump(mode="json")


# (id, controls at create, voice/lyrics body extras, patch, plan getter, provenance key, remaining controls)
RESET_CASES = [
    ("lead", {"lead": "piano"}, {}, {"lead": None}, lambda p: p["lead"]["instrument"], "lead", {}),
    ("instruments", {"instruments": ["cello", "piano"]}, {}, {"instruments": None}, lambda p: p["supports"], "supports", {}),
    ("pace", {"pace": "lively"}, {}, {"pace": None}, lambda p: p["pace"], "pace", {}),
    ("bpm", {"bpm": 112}, {}, {"bpm": None}, lambda p: p["pace"], "pace", {}),
    ("key", {"key": "G minor"}, {}, {"key": None}, lambda p: p["key"], "key", {}),
    ("fullness", {"fullness": "full"}, {}, {"fullness": None}, lambda p: p["fullness"], "fullness", {}),
    ("arc", {"arc": "steady"}, {}, {"arc": None}, lambda p: p["arc"], "arc", {}),
    ("style", {"style": "ornate"}, {}, {"style": None}, lambda p: p["lead"]["style"], "lead", {}),
    ("feeling", {"feeling": ["tender", "yearning"]}, {}, {"feeling": None}, lambda p: p["feeling"], "feeling", {}),
    ("duration", {"duration_s": 120}, {}, {"duration_s": None}, lambda p: p["duration_s"], "duration_s", {}),
    ("voice", {}, {"voice": "wordless"}, {"voice": None}, lambda p: (p["voice_mode"], p["voices"], p["lyrics"]),
     "voice_mode", {}),
    ("background", {"background": "big"}, {"voice": "wordless"}, {"background": None}, lambda p: p["voices"]["background"],
     "voices", {"voice": "wordless"}),
    ("singer", {"singer": "female"}, {"voice": "sung", "lyrics": "Tera naam\nMera dil"}, {"singer": None},
     lambda p: p["voices"]["singer"], "voices", {"voice": "sung", "lyrics_text": "Tera naam\nMera dil"}),
    ("language", {"language": "en"}, {"voice": "sung", "lyrics": "Tera naam\nMera dil"}, {"language": None},
     lambda p: p["voices"]["language"], "voices", {"voice": "sung", "lyrics_text": "Tera naam\nMera dil"}),
]


@pytest.mark.parametrize("case", RESET_CASES, ids=[x[0] for x in RESET_CASES])
def test_null_reset_recomputes_the_field_as_auto_and_drops_you_provenance(tmp_path, case):
    name, controls, body_extra, patch, getter, prov_key, remaining = case
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, **controls, **body_extra)
        sid = data["song_id"]
        assert data["plan"]["provenance"][prov_key]["source"] == "you", "setup: the control must start as 'you'"
        explicit = getter(data["plan"])

        r = c.patch(f"/api/songs/{sid}/controls", json=patch)
        assert r.status_code == 200, r.text
        out = r.json()
        expected = getter(auto_plan(QUIET, **remaining))
        assert getter(out["plan"]) == expected, (name, getter(out["plan"]), expected)
        assert getter(out["plan"]) != explicit, "setup: Auto must differ from the explicit value"
        assert out["plan"]["provenance"][prov_key]["source"] != "you", out["plan"]["provenance"][prov_key]
        stored = c.get(f"/api/songs/{sid}").json()["plans"][-1]
        assert stored["controls"].get(next(iter(patch))) is None
        assert getter(stored["plan"]) == expected and stored["provenance"][prov_key]["source"] != "you"

        # the next round is built from the reset plan
        nxt = c.post(f"/api/songs/{sid}/rounds", json={"kind": "another", "takes": 1})
        assert nxt.status_code == 202, nxt.text
        assert nxt.json()["plan_id"] == out["plan_id"] and getter(nxt.json()["plan"]) == expected
        wait_job(c, nxt.json()["job_id"])
        rnd = c.get(f"/api/songs/{sid}").json()["rounds"][-1]
        params = rnd["request"]["engine_request"]["params"]
        plan = out["plan"]
        assert params["bpm"] == plan["pace"]["bpm"] and params["keyscale"] == plan["key"]
        assert params["duration"] == plan["duration_s"] and params["instrumental"] == (plan["voice_mode"] == "instrumental")


def test_reset_leaves_other_explicit_controls_and_chip_changes_alone(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, lead="piano", key="G minor", fullness="full")
        sid = data["song_id"]
        r = c.patch(f"/api/songs/{sid}/controls", json={"key": None})
        plan = r.json()["plan"]
        assert plan["lead"]["instrument"] == "piano" and plan["fullness"] == "full"
        assert plan["provenance"]["lead"]["source"] == "you" and plan["provenance"]["fullness"]["source"] == "you"
        assert plan["key"] != "G minor" and plan["provenance"]["key"]["source"] != "you"
        assert r.json()["changes"] == [{"field": "key", "from": "G minor", "to": plan["key"], "source": "rule"}]
        # a reset together with a new value in one PATCH
        r = c.patch(f"/api/songs/{sid}/controls", json={"fullness": None, "arc": "steady"})
        plan = r.json()["plan"]
        assert plan["arc"] == "steady" and plan["provenance"]["arc"]["source"] == "you"
        assert plan["fullness"] != "full" and plan["provenance"]["fullness"]["source"] != "you"
        assert plan["lead"]["instrument"] == "piano"


def test_resetting_one_of_two_explicit_pace_controls_keeps_the_other(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, pace="lively", bpm=112)
        sid = data["song_id"]
        plan = c.patch(f"/api/songs/{sid}/controls", json={"bpm": None}).json()["plan"]
        assert plan["pace"]["bucket"] == "lively" and plan["pace"]["bpm"] == 108       # bucket default, still yours
        assert plan["provenance"]["pace"]["source"] == "you"


# --------------------------------------------------------------------------- bug 4: one change-entry schema
def assert_change_entries(entries, sources):
    assert entries, "expected at least one change"
    for e in entries:
        assert isinstance(e, dict) and set(e) == CHANGE_KEYS, e
        assert e["source"] in sources and isinstance(e["field"], str) and e["field"]


def test_refine_chip_changes_use_the_standard_schema(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, brief="A peaceful bansuri at dawn, gentle tabla")
        sid = data["song_id"]
        t1 = c.get(f"/api/songs/{sid}").json()["takes"][0]
        r = c.post(f"/api/songs/{sid}/rounds", json={"kind": "refine", "chips": ["less_busy", "slower", "warmer"],
                                                     "from_take": t1["id"], "takes": 1})
        assert r.status_code == 202, r.text
        changes = r.json()["card"]["changes"]
        assert_change_entries(changes, {"chip"})
        assert {"fullness", "pace", "feeling"} <= {e["field"] for e in changes}
        pace = next(e for e in changes if e["field"] == "pace")
        assert pace["to"] < pace["from"]
        wait_job(c, r.json()["job_id"])
        stored = c.get(f"/api/songs/{sid}").json()["plans"][-1]["card"]["changes"]
        assert stored == changes


def test_patch_controls_changes_use_the_standard_schema(tmp_path):
    with client_for(tmp_path, **CLASSIC) as c:
        data = create(c, brief="A peaceful bansuri at dawn")
        sid = data["song_id"]
        r = c.patch(f"/api/songs/{sid}/controls", json={"fullness": "full", "bpm": 90, "instruments": ["tabla"]})
        assert r.status_code == 200
        changes = r.json()["changes"]
        assert_change_entries(changes, {"you"})
        by = {e["field"]: e for e in changes}
        assert by["fullness"]["to"] == "full" and by["pace"]["to"] == 90 and by["supports"]["to"] == ["tabla"]
        assert not [e for e in changes if not isinstance(e, dict)]                # was: ["bpm", "fullness"]
        stored = c.get(f"/api/songs/{sid}").json()["plans"][-1]["card"]["changes"]
        assert stored == changes
        # a null reset is reported too, as an automatic ('rule') change
        r = c.patch(f"/api/songs/{sid}/controls", json={"fullness": None})
        assert_change_entries(r.json()["changes"], {"rule"})
        assert r.json()["changes"][0]["field"] == "fullness" and r.json()["changes"][0]["from"] == "full"
        # nothing changed: an empty list, never strings
        assert c.patch(f"/api/songs/{sid}/controls", json={"fullness": None}).json()["changes"] == []


def test_every_chip_produces_only_standard_entries():
    planner = BasicPlanner()
    plan = planner.plan("A tender song in English with a female singer", Controls(voice="wordless")).plan
    for chip in ("less busy", "more melodic", "slower", "livelier", "warmer", "brighter", "different lead",
                 "more voices", "fewer voices"):
        res = planner.patch(plan, chip)
        for e in res.changes:
            assert set(e) == CHANGE_KEYS and e["source"] == "chip", (chip, e)


def test_smart_planner_free_text_changes_use_the_standard_schema():
    from backend.providers import LlmPatchDraft, apply_patch_draft
    from backend import copyright_policy
    plan = BasicPlanner().plan(QUIET).plan
    draft = LlmPatchDraft.model_validate({"key": "E minor", "fullness": "spare"})
    res = apply_patch_draft(plan, draft, "make it sadder", copyright_policy.sanitize("make it sadder"),
                            provider="anthropic_api", label="Smart planner")
    assert_change_entries(res.changes, {"you"})
    assert {e["field"] for e in res.changes} == {"key", "fullness"}
