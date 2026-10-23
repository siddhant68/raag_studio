"""The honesty registry covers every control and capability row."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend import capabilities as cap

IDS = [f"C{i}" for i in range(1, 26)]


def test_every_control_id_has_an_entry_and_registry_is_consistent():
    assert cap.validate_registry() == []
    assert cap.control_ids() == IDS


@pytest.mark.parametrize("cid", IDS)
def test_control_has_class_and_wording(cid):
    assert cap.control_class(cid)
    assert set(cap.control_classes(cid)) <= {"a", "b", "c", "d", "n/a"}
    if cap.needs_class_label(cid):                       # (b)/(d) controls must show a class label + wording
        assert cap.ui_wording(cid) and cap.class_labels(cid)
        assert all(l["label"] and l["tooltip"] for l in cap.class_labels(cid))


def test_known_classes_match_the_prd():
    assert cap.control_class("C5") == "b" and cap.control_class("C3") == "a"
    assert cap.control_class("C8") == "a+d" and cap.control_class("C12") == "b"
    assert cap.control_class("C1") == "n/a" and cap.control_class("C21") == "a"
    assert cap.ui_wording("C3") == "exact" and cap.ui_wording("C8") == "target"
    assert cap.ui_wording("C12") == "left out of the request; may still appear"
    assert cap.ui_wording("C17") == "sent unchanged; listen to check"


def test_language_badges_cover_every_c15_option():
    assert cap.language_badge("hi")["badge"] == "experimental"
    assert cap.language_badge("en")["badge"] == "untested"
    assert cap.language_badge("ta")["badge"] == "experimental"
    assert cap.language_badge("en")["ui_wording"] == "untested"


def test_section_11_rows_present_and_unknown_ids_fail():
    assert len(cap.registry()["capabilities"]) == 25
    assert cap.get_capability("guidance_strength")["classes"] == ["unavailable"]
    assert cap.get_capability("write_lyrics")["ui_wording"] == "needs smart planner"
    with pytest.raises(KeyError):
        cap.get_control("C26")
