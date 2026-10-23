"""AT-M1-09: plan validation."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from pydantic import ValidationError

from backend.plan_schema import INSTRUMENT_IDS, Plan

BASE = {"brief": "a quiet flute", "voice_mode": "instrumental", "lead": {"instrument": "bansuri"}}


def make(**kw):
    return Plan.model_validate({**BASE, **kw})


def test_valid_minimal_plan_has_defaults():
    p = make()
    assert p.schema_version == "2.0" and p.takes == 3 and p.duration_s == 150


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        make(colour="blue")
    with pytest.raises(ValidationError):
        make(lead={"instrument": "bansuri", "volume": 11})


def test_unknown_instrument_rejected():
    with pytest.raises(ValidationError):
        make(lead={"instrument": "theremin"})
    with pytest.raises(ValidationError):
        make(supports=[{"instrument": "kazoo"}])


def test_all_fifteen_instruments_accepted():
    assert len(INSTRUMENT_IDS) == 15
    for inst in INSTRUMENT_IDS:
        make(lead={"instrument": inst})


@pytest.mark.parametrize("brief", ["", "   ", "\n\t "])
def test_blank_brief_rejected(brief):
    with pytest.raises(ValidationError):
        make(brief=brief)


def test_other_hard_rules():
    with pytest.raises(ValidationError):
        make(duration_s=9)
    with pytest.raises(ValidationError):
        make(duration_s=241)
    with pytest.raises(ValidationError):
        make(key="H sharp")
    with pytest.raises(ValidationError):
        make(voice_mode="sung")                                   # sung needs a lyrics policy
    with pytest.raises(ValidationError):
        make(lyrics={"policy": "exact", "text": "  "})
    with pytest.raises(ValidationError):
        make(supports=[{"instrument": "tabla"}, {"instrument": "tabla"}])
    with pytest.raises(ValidationError):
        make(schema_version="1.0")


def test_provenance_per_field():
    p = make(provenance={"lead": {"source": "you", "reason": "starred"}, "pace": {"source": "recipe"}})
    assert p.provenance["lead"].source == "you"
    with pytest.raises(ValidationError):
        make(provenance={"lead": {"source": "oracle"}})
    with pytest.raises(ValidationError):
        make(provenance={"not_a_field": {"source": "you"}})
    assert make().with_provenance("duration_s", "rule", "clamped").provenance["duration_s"].reason == "clamped"
