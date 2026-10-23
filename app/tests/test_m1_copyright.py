"""AT-M1-06: copyright strip and remix refusal."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend import compiler, copyright_policy as cp
from backend.plan_schema import Plan

CASES = [
    ("Make it like Ashes on the Fire, but peaceful flute", "Ashes on the Fire"),
    ("something like Ashes on the Fire with a quiet flute", "Ashes on the Fire"),
    ("sing in the voice of Arijit Singh with a flute", "Arijit Singh"),
    ("in the voice of Lata Mangeshkar, slow", "Lata Mangeshkar"),
    ("a song like 'Tum Hi Ho' but slower", "Tum Hi Ho"),
    ("sounds like Hans Zimmer", "Hans Zimmer"),
    ("sung by Kishore Kumar", "Kishore Kumar"),
]
NOT_NAMES = ["feels like rain on a quiet morning", "something like Raag Yaman at dawn", "in the style of a lullaby",
             "inspired by the monsoon", "like the river at dawn", "a peaceful flute"]


@pytest.mark.parametrize("text,name", CASES)
def test_names_are_stripped_and_noted(text, name):
    res = cp.sanitize(text)
    assert name not in res.text and name in [n["removed"] for n in res.notes]
    assert "mood, not the song" in res.notes[0]["message"]


@pytest.mark.parametrize("text", NOT_NAMES)
def test_ordinary_descriptions_are_left_alone(text):
    res = cp.sanitize(text)
    assert res.text == text and not res.changed


@pytest.mark.parametrize("text,target", [("remix Tum Hi Ho", "Tum Hi Ho"), ("Remix of Ashes on the Fire please", "Ashes on the Fire"),
                                         ("remix this song", "")])
def test_remix_flagged_unsupported_with_offer(text, target):
    res = cp.sanitize(text)
    assert [u["kind"] for u in res.unsupported] == ["remix"]
    assert "original piece" in res.unsupported[0]["message"]
    assert target not in res.text or not target


def test_at_m1_06_names_absent_from_caption_and_lyrics_prompt_and_note_recorded():
    plan = Plan.model_validate({
        "brief": "remix Tum Hi Ho, in the voice of Arijit Singh, like Ashes on the Fire",
        "voice_mode": "wordless", "lead": {"instrument": "piano"}, "voices": {"background": "choir"},
        "flavour": "like Ashes on the Fire but slower",
        "feeling": ["tender", "in the voice of Arijit Singh"],
        "lyrics": {"policy": "write", "topic": "a song in the voice of Arijit Singh about rain"},
        "avoid": ["Tum Hi Ho"],
    })
    out = compiler.compile(plan)
    rep = out["compile_report"]
    blob = " ".join([out["caption"], out["lyrics"], out["lyrics_prompt"] or ""])
    for name in ("Ashes on the Fire", "Arijit", "Tum Hi Ho"):
        assert name not in blob, name
    removed = {n["removed"] for n in rep["notes"]}
    assert {"Ashes on the Fire", "Arijit Singh", "Tum Hi Ho"} <= removed
    assert any(c["kind"] == "named_reference_stripped" for c in rep["conflicts"])
    assert [u["kind"] for u in rep["unsupported"]] == ["remix"]
    assert "original piece" in rep["unsupported"][0]["message"]
    assert "rain" in out["lyrics_prompt"]                       # the mood survives, the name does not


def test_exact_user_lyrics_are_never_edited_by_the_policy():
    text = "like Ashes on the Fire\nmera geet"
    plan = Plan.model_validate({"brief": "b", "voice_mode": "sung", "lead": {"instrument": "piano"},
                                "voices": {"language": "hi"}, "lyrics": {"policy": "exact", "text": text}})
    assert text in compiler.compile(plan)["lyrics"]
