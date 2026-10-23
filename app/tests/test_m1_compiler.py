"""AT-M1-01 (golden), AT-M1-03 (budget), AT-M1-04 (conflicts), AT-M1-05 (avoid)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[2]

import pytest

from backend import compiler
from backend.compiler import OverBudget, compile as compile_plan, default_plan
from backend.plan_schema import Plan

TAG = re.compile(r"^\[[^\[\]]+\]$")
VOWEL = re.compile(r"^(?:(?:ooh|aah)(?:, )?)+$", re.I)
LEAD_WORDS = {"r1_flute_focus": "bansuri", "r2_warm_ensemble": "piano", "r3_hindi_ballad": "guitar"}


def request_params(name):
    return json.loads((ROOT / "context_pack/recipes" / name / "request.json").read_text("utf-8"))["params"]


def make(**kw):
    base = {"brief": "test", "voice_mode": "instrumental", "lead": {"instrument": "bansuri", "style": "singing"},
            "pace": {"bucket": "medium", "bpm": 82}}
    return Plan.model_validate({**base, **kw})


# ------------------------------------------------------------------ AT-M1-01
@pytest.mark.parametrize("rid,name", [("r1_flute_focus", "yamuna"), ("r2_warm_ensemble", "daylight"),
                                      ("r3_hindi_ballad", "thodi")])
def test_at_m1_01_golden_defaults(rid, name):
    out, orig = compile_plan(default_plan(rid)), request_params(name)
    p = out["params"]
    assert len(out["caption"]) <= 512
    assert LEAD_WORDS[rid] in out["caption"].lower()
    assert (p["bpm"], p["keyscale"], p["duration"]) == (orig["bpm"], orig["keyscale"], orig["duration"])
    assert p["instrumental"] == orig["instrumental"] and p["vocal_language"] == orig["vocal_language"]
    assert p["timesignature"] == "4" and p["inference_steps"] == 8 and p["thinking"] is False
    lines = [ln for ln in out["lyrics"].split("\n") if ln.strip()]
    if rid == "r1_flute_focus":
        assert p["instrumental"] is True and out["lyrics"] == "[Instrumental]"
        assert "Strictly no voices." in out["caption"]
    elif rid == "r2_warm_ensemble":
        assert p["instrumental"] is False
        body = [ln for ln in lines if not TAG.match(ln)]
        assert body and all(VOWEL.match(ln) for ln in body)
    else:
        assert p["instrumental"] is False and p["vocal_language"] == "hi"
        got = [ln for ln in out["lyrics"].split("\n") if not TAG.match(ln)]
        want = [ln for ln in orig["lyrics"].split("\n") if not TAG.match(ln)]
        assert got == want


def test_r1_reproduces_the_accepted_yamuna_caption_exactly():
    assert compile_plan(default_plan("r1_flute_focus"))["caption"] == request_params("yamuna")["caption"]


def test_compile_is_deterministic():
    a, b = compile_plan(default_plan("r2_warm_ensemble")), compile_plan(default_plan("r2_warm_ensemble"))
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_wordless_never_sets_instrumental_true():
    for bg in ("light", "choir", "big", "none"):
        out = compile_plan(make(voice_mode="wordless", voices={"background": bg}))
        assert out["params"]["instrumental"] is False and out["lyrics"] != "[Instrumental]"


def test_sung_without_lyrics_is_an_error_not_a_guess():
    with pytest.raises(compiler.LyricsMissing):
        compile_plan(make(voice_mode="sung", lyrics={"policy": "write"}, voices={"language": "hi"}))


# ------------------------------------------------------------------ AT-M1-03
def long_recipe():
    return {"slots": {"arcs": {"slow_build": [{"text": t} for t in (
        "a very spacious quiet solo opening", "slowly flowing percussion pulse", "an exposed unaccompanied interlude",
        "intricate improvised passages", "a rising wave of intensity", "a peaceful resolving cadence")]}}}


FILL = ["tabla", "tanpura", "santoor", "sitar", "ghatam", "violin", "cello", "strings"]
PHASE = {"flavour": 0, "support": 1, "technique": 2, "beat": 3, "mood": 4}


def over_budget_plan(**kw):
    return make(arc="slow_build", supports=[{"instrument": i, "presence": "gentle"} for i in FILL],
                feeling=["tender", "luminous", "peaceful"], flavour="a long flavourful clause about misty river mornings",
                **kw)


def test_at_m1_03_over_budget_drops_in_documented_order():
    out = compile_plan(over_budget_plan(), recipe=long_recipe())
    rep = out["compile_report"]
    assert len(out["caption"]) <= 512 and rep["char_count"] == len(out["caption"])
    budget_drops = [d for d in rep["dropped"] if d["reason"] == "over_budget"]
    assert budget_drops and budget_drops[0]["kind"] == "flavour"
    phases = [PHASE[d["kind"]] for d in budget_drops]
    assert phases == sorted(phases)                                  # never goes back to an earlier phase
    sup = [d["item"] for d in budget_drops if d["kind"] == "support"]
    assert sup == FILL[::-1][:len(sup)]                              # lowest rank (last in list) first
    assert "Indian bamboo flute solo" in out["caption"]               # never dropped
    assert "Bansuri is the loud clear melodic lead in every section." in out["caption"]
    assert out["caption"].endswith("82 BPM, D major. Strictly no voices.")


def test_at_m1_03_later_phases_and_floors():
    plan = make(arc="slow_build", feeling=["tender", "luminous", "peaceful"], flavour="some flavour",
                fullness="spare")
    out = compile_plan(plan, recipe=long_recipe(), max_chars=400)
    drops = [(d["kind"], d["item"]) for d in out["compile_report"]["dropped"] if d["reason"] == "over_budget"]
    kinds = [k for k, _ in drops]
    assert kinds == sorted(kinds, key=PHASE.get) and kinds[0] == "flavour"
    assert {"technique", "beat", "mood"} <= set(kinds)
    assert kinds.count("technique") == 2                              # 5 terms -> keeps the first 3
    assert kinds.count("beat") == 3                                   # 6 beats -> keeps the first 3
    assert [i for k, i in drops if k == "technique"] == ["octave turns", "lyrical sustained notes with natural breaths"][::-1]
    assert len(out["caption"]) <= 400
    assert kinds.count("mood") == 4                                  # 3 feeling words, then the 'how full' phrase
    assert "A very spacious quiet solo opening" in out["caption"] and "intricate improvised" not in out["caption"]


def test_at_m1_03_over_budget_error_never_truncates():
    with pytest.raises(OverBudget) as exc:
        compile_plan(over_budget_plan(), recipe=long_recipe(), max_chars=100)
    e = exc.value
    assert e.char_count > 100 and e.cap == 100 and len(e.caption) == e.char_count   # whole core reported, not cut
    assert "Bansuri is the loud clear melodic lead" in e.caption and e.caption.endswith("Strictly no voices.")
    with pytest.raises(ValueError):
        compile_plan(make(), max_chars=513)


# ------------------------------------------------------------------ AT-M1-04
def kinds(out):
    return [c["kind"] for c in out["compile_report"]["conflicts"]]


def test_at_m1_04_instrumental_plus_choir():
    out = compile_plan(make(supports=[{"instrument": "tabla"}, {"instrument": "choir"}],
                            voices={"background": "choir"}))
    assert kinds(out).count("instrumental_with_choir") == 1
    assert "choir" not in out["caption"].lower() and out["params"]["instrumental"] is True
    assert out["lyrics"] == "[Instrumental]"
    assert "tabla" in out["caption"].lower()


def test_at_m1_04_wordless_plus_instrumental_flag():
    plan = make(voice_mode="wordless", voices={"background": "choir"})
    out = compile_plan(plan, instrumental_flag=True)
    assert "instrumental_flag_vs_voice_mode" in kinds(out)
    assert out["params"]["instrumental"] is False
    assert "Ooh" in out["lyrics"]
    assert "instrumental_flag_vs_voice_mode" not in kinds(compile_plan(plan, instrumental_flag=False))


def test_at_m1_04_two_leads_second_becomes_support():
    out = compile_plan(make(supports=[{"instrument": "sitar", "role": "lead"}, {"instrument": "tabla", "role": "rhythm"}]))
    assert "two_leads" in kinds(out)
    assert "Bansuri is the loud clear melodic lead" in out["caption"]
    assert "answering sitar" in out["caption"] and "Sitar is the" not in out["caption"]


def test_at_m1_04_wordless_sung_lyric_only_kept_if_sung():
    plan = make(voice_mode="wordless", voices={"background": "choir"},
                lyrics={"policy": "exact", "text": "tere bina\nkuch nahin"})
    out = compile_plan(plan)
    assert "lyrics_ignored" in kinds(out) and "tere bina" not in out["lyrics"]
    sung = make(voice_mode="sung", voices={"language": "hi"}, lyrics={"policy": "exact", "text": "tere bina\nkuch nahin"})
    assert "tere bina" in compile_plan(sung)["lyrics"]


def test_at_m1_04_wordless_without_voices_gets_light_harmonies_and_is_reported():
    out = compile_plan(make(voice_mode="wordless", voices={"background": "none"}))
    assert "wordless_without_voices" in kinds(out) and "ooh/aah" in out["caption"]


def test_sung_modes_never_emit_blocked_vocal_wording():
    plan = make(voice_mode="sung", voices={"language": "hi"}, lyrics={"policy": "exact", "text": "a\nb"},
                flavour="dry a cappella, no reverb")
    out = compile_plan(plan)
    assert "cappella" not in out["caption"].lower() and "reverb" not in out["caption"].lower()
    assert any(d["reason"] == "blocked_style_L1" for d in out["compile_report"]["dropped"])


# ------------------------------------------------------------------ AT-M1-05
def body(out):
    return " ".join(t for n, t in out["compile_report"]["slots"] if n != "tail").lower()


def test_at_m1_05_avoid_terms_absent_from_caption_body():
    base = default_plan("r1_flute_focus").model_dump()
    for term in ("tabla", "no tabla", "santoor", "tanpura drone", "voices", "singing"):
        out = compile_plan({**base, "avoid": [term]})
        word = term.replace("no ", "").split()[0]
        assert word not in body(out), term
        assert f"no {word}" not in out["caption"].lower().replace("strictly no voices", "")


def test_at_m1_05_avoid_removes_support_and_dependent_beat():
    out = compile_plan({**default_plan("r1_flute_focus").model_dump(), "avoid": ["tabla"]})
    d = out["compile_report"]["dropped"]
    assert {"kind": "support", "item": "tabla", "reason": "avoid"} in d
    assert any(x["kind"] == "beat" and "tabla" in x["item"] for x in d)
    assert "tabla" not in out["caption"].lower()


def test_at_m1_05_avoid_voice_word_allowed_only_inside_the_voice_tail():
    out = compile_plan({**default_plan("r1_flute_focus").model_dump(), "avoid": ["voices"]})
    assert "voices" not in body(out) and out["caption"].endswith("Strictly no voices.")


def test_at_m1_05_avoid_drums_on_ensemble_and_lead_protected():
    out = compile_plan({**default_plan("r2_warm_ensemble").model_dump(), "avoid": ["drums"]})
    assert "groove" not in out["caption"].lower() and "drum" not in out["caption"].lower()
    out = compile_plan({**default_plan("r1_flute_focus").model_dump(), "avoid": ["flute"]})
    assert "avoid_vs_lead" in kinds(out) and "bansuri" in out["caption"].lower()


def test_at_m1_05_avoid_voice_conflicting_with_voice_mode_is_reported():
    out = compile_plan({**default_plan("r2_warm_ensemble").model_dump(), "avoid": ["choir"]})
    assert "avoid_vs_voice_mode" in kinds(out) and out["params"]["instrumental"] is False
