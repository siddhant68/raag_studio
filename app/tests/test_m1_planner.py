"""AT-M1-07 (rule planner accuracy on fixtures/briefs.jsonl) plus planner honesty and chip patches."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend import compiler
from backend.planner_base import Controls, Planner, UnsupportedByPlanner
from backend.planner_rules import BasicPlanner

FIXTURE = Path(__file__).parent / "fixtures" / "briefs.jsonl"
PLANNER = BasicPlanner()


def load_briefs():
    return [json.loads(ln) for ln in FIXTURE.read_text("utf-8").splitlines() if ln.strip()]


def checks(exp: dict, card) -> dict[str, bool]:
    """field -> passed, for every expectation present in the fixture row."""
    p = card.plan
    sup = [s.instrument for s in p.supports]
    out: dict[str, bool] = {}
    simple = {
        "voice_mode": p.voice_mode, "recipe_id": p.recipe_id, "lead": p.lead.instrument, "duration_s": p.duration_s,
        "pace_bucket": p.pace.bucket, "bpm": p.pace.bpm, "key": p.key, "arc": p.arc, "fullness": p.fullness,
        "language": p.voices.language, "singer": p.voices.singer, "background": p.voices.background,
        "fallback": card.fallback, "supports_count": len(sup),
    }
    for k, got in simple.items():
        if k in exp:
            out[k] = got == exp[k]
    if "supports_include" in exp:
        out["supports_include"] = set(exp["supports_include"]) <= set(sup)
    if "supports_exclude" in exp:
        out["supports_exclude"] = not set(exp["supports_exclude"]) & set(sup)
    if "support_presence" in exp:
        out["support_presence"] = all(next((s.presence for s in p.supports if s.instrument == i), None) == v
                                      for i, v in exp["support_presence"].items())
    if "feeling_include" in exp:
        out["feeling_include"] = set(exp["feeling_include"]) <= set(p.feeling)
    if "avoid_include" in exp:
        out["avoid_include"] = set(exp["avoid_include"]) <= {a.lower() for a in p.avoid}
    if "unsupported_kinds" in exp:
        out["unsupported_kinds"] = set(exp["unsupported_kinds"]) <= {u["kind"] for u in card.unsupported}
    if "needs_user_input" in exp:
        out["needs_user_input"] = set(exp["needs_user_input"]) <= set(card.needs_user_input)
    if "name_absent" in exp:
        d = p.model_dump(mode="json")
        d.pop("brief"), d.pop("notes_for_user")
        out["name_absent"] = exp["name_absent"] not in json.dumps(d, ensure_ascii=False)
    return out


def test_fixture_is_realistic_and_covers_hindi():
    briefs = load_briefs()
    assert len(briefs) >= 30
    text = " ".join(b["brief"] for b in briefs)
    assert any("ऀ" <= ch <= "ॿ" for ch in text)                  # Devanagari
    assert "gaana" in text and "bina gaane" in text and "dheema" in text      # Roman Hindi
    assert sum("explicit_instrumental" in b["tags"] for b in briefs) >= 10
    assert sum("explicit_duration" in b["tags"] for b in briefs) >= 12


def test_at_m1_07_rule_planner_accuracy():
    total = passed = 0
    must_be_perfect: list[str] = []
    failures: list[str] = []
    for b in load_briefs():
        card = PLANNER.plan(b["brief"])
        res = checks(b["expected"], card)
        for field, ok in res.items():
            total += 1
            passed += ok
            if not ok:
                failures.append(f"{b['id']} {field}: {b['brief']!r}")
            if (field == "voice_mode" and "explicit_instrumental" in b["tags"]) or \
               (field == "duration_s" and "explicit_duration" in b["tags"]):
                if not ok:
                    must_be_perfect.append(f"{b['id']} {field}")
    accuracy = passed / total
    assert not must_be_perfect, f"explicit no-singing / explicit duration must be 100%: {must_be_perfect}"
    assert accuracy >= 0.90, f"field accuracy {accuracy:.3f} ({passed}/{total}); misses: {failures}"


def test_every_fixture_brief_gives_a_valid_plan_that_compiles_or_asks_for_lyrics():
    for b in load_briefs():
        card = PLANNER.plan(b["brief"])
        if card.plan.voice_mode == "sung":
            with pytest.raises(compiler.LyricsMissing):
                compiler.compile(card.plan)
        else:
            out = compiler.compile(card.plan)
            assert len(out["caption"]) <= 512
            assert out["params"]["duration"] == card.plan.duration_s


def test_basic_planner_is_honest_about_what_it_is():
    card = PLANNER.plan("a peaceful bansuri at dawn, no singing")
    assert isinstance(PLANNER, Planner)
    assert (PLANNER.name, card.provider, card.is_llm) == ("basic", "basic", False)
    assert card.provider_label == "Basic planner" and "AI" not in card.provider_label
    assert any("not an AI" in n for n in card.notes)


def test_write_lyrics_unsupported_under_basic_and_says_so():
    with pytest.raises(UnsupportedByPlanner) as exc:
        PLANNER.draft_lyrics(PLANNER.plan("a hindi song about chai").plan)
    assert "smart planner" in exc.value.message
    card = PLANNER.plan("a Hindi song about chai")
    assert card.needs_user_input == ["lyrics"] and card.unsupported[0]["kind"] == "write_lyrics"
    assert card.plan.lyrics.policy == "write" and card.plan.lyrics.text is None
    mine = PLANNER.plan("a Hindi song about chai", Controls(lyrics_text="chai ka pyala\nmeri subah"))
    assert mine.plan.lyrics.policy == "exact" and mine.needs_user_input == [] and mine.plan.provenance["lyrics"].source == "you"


def test_fallback_says_which_words_matched_and_never_picks_r4():
    nothing = PLANNER.plan("Something beautiful")
    assert nothing.fallback and nothing.matched == [] and "started from the Flute focus recipe" in " ".join(nothing.notes)
    some = PLANNER.plan("a fusion piece, moonlit night, flute and santoor, lively")
    assert some.plan.recipe_id != "r4_fusion" and "flute" in some.matched
    assert "Words I understood" in some.notes[0]
    for b in load_briefs():
        assert PLANNER.plan(b["brief"]).plan.recipe_id != "r4_fusion"


def test_controls_override_and_get_provenance_you():
    card = PLANNER.plan("a peaceful flute", Controls(voice="wordless", duration_s=90, lead="sitar", pace="lively",
                                                      recipe_id="r2_warm_ensemble", takes=2, avoid=["drums"]))
    p = card.plan
    assert (p.voice_mode, p.duration_s, p.lead.instrument, p.pace.bucket, p.takes) == ("wordless", 90, "sitar", "lively", 2)
    assert p.recipe_id == "r2_warm_ensemble" and p.avoid == ["drums"]
    assert all(p.provenance[f].source == "you" for f in ("voice_mode", "duration_s", "lead", "pace", "takes", "avoid"))
    assert p.provenance["feeling"].source == "suggested"


def test_blank_brief_rejected():
    with pytest.raises(ValueError):
        PLANNER.plan("   ")


def test_duration_regex_cases():
    from backend.planner_rules import parse_duration
    cases = {"two and a half minutes": 150, "90 seconds": 90, "2:30": 150, "डेढ़ मिनट": 90, "half a minute": 30,
             "3 mins": 180, "ek minute": 60, "do minute": 120, "1.5 minutes": 90, "five minutes": 240, "तीन मिनट": 180}
    for text, want in cases.items():
        assert parse_duration(text)[0] == want, text
    assert parse_duration("120 bpm piano")[0] is None and parse_duration("at 10:30 pm")[0] is None


# ---------------------------------------------------------------- chips (PRD section 6)
@pytest.fixture
def plan():
    return compiler.default_plan("r1_flute_focus")


def patch(plan, text):
    before = plan.model_dump_json()
    res = PLANNER.patch(plan, text)
    assert plan.model_dump_json() == before                         # the old revision is never mutated
    return res


def test_less_busy(plan):
    res = patch(plan, "less busy")
    p = res.plan
    assert p.fullness == "spare"
    assert [s.instrument for s in p.supports] == ["tabla", "tanpura"] and res.applied == ["less_busy"]
    assert "new performances" in res.notice and p.provenance["fullness"].source == "you"
    again = patch(patch(res.plan, "less busy").plan, "less busy")
    assert again.plan.supports == []                                    # keeps going until nothing is left
    assert "Already as spare" in patch(again.plan, "less busy").unsupported[0]["message"]


def test_more_melodic(plan):
    p = patch(plan.model_copy(update={"lead": plan.lead.model_copy(update={"style": "simple"})}), "more melodic").plan
    assert p.lead.style == "singing" and p.feeling[0] == "memorable"
    assert "Memorable recurring melody" in compiler.compile(p)["caption"]


def test_slower_and_livelier_clamp_to_c8_range(plan):
    slow = patch(plan, "slower").plan
    assert (slow.pace.bpm, slow.pace.bucket) == (74, "slow")
    assert patch(slow, "slower").plan.pace.bpm == 68
    assert patch(patch(slow, "slower").plan, "slower").applied == []
    lively = patch(plan, "livelier").plan
    assert (lively.pace.bpm, lively.pace.bucket) == (90, "medium")
    top = patch(patch(patch(lively, "livelier").plan, "livelier").plan, "livelier").plan
    assert top.pace.bpm == 114 and patch(patch(top, "livelier").plan, "livelier").plan.pace.bpm == 116


def test_warmer_brighter_swap_tone_words(plan):
    warm = patch(plan, "warmer").plan
    assert "warm" in warm.feeling and "luminous" not in warm.feeling
    bright = patch(warm, "brighter").plan
    assert "bright" in bright.feeling and "warm" not in bright.feeling
    assert compiler.compile(bright)["caption"]


def test_different_lead_promotes_next_support(plan):
    p = patch(plan, "different lead").plan
    assert p.lead.instrument == "tabla" and p.supports[0].instrument == "bansuri"
    assert {s.instrument for s in p.supports} == {"bansuri", "tanpura", "santoor"}
    assert compiler.compile(p)["caption"]


def test_more_and_fewer_voices_step_c14():
    p = compiler.default_plan("r2_warm_ensemble")
    more = patch(p, "more voices").plan
    assert more.voices.background == "big"
    fewer = patch(p, "fewer voices").plan
    assert fewer.voices.background == "light"
    assert patch(fewer, "fewer voices").plan.voices.background == "light"          # wordless keeps at least light
    instr = patch(compiler.default_plan("r1_flute_focus"), "more voices")
    assert instr.applied == [] and "instrumental" in instr.unsupported[0]["message"]


def test_free_text_needs_smart_planner_and_chip_ids_work(plan):
    res = patch(plan, "make the flute much louder and add rain sounds")
    assert res.applied == [] and res.unsupported[0]["kind"] == "free_text" and res.plan == plan
    assert patch(plan, "less_busy").applied == ["less_busy"]
