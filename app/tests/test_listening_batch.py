"""Listening batch: blind requests for old-versus-new, the key kept apart, and unblinding of a filled sheet.

Nothing is rendered here (render needs the Mac); the requests are checked against the engine validator.
"""
import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import listening_batch as lb  # noqa: E402

EXPECTED_STYLE = {"yamuna": "raag_bansuri", "rooftop_sitar": "raag_sitar", "daylight": "warm_cinematic_acoustic",
                  "cinematic": "cinematic_orchestral", "thodi": "hindi_acoustic_ballad",
                  "chai_bollywood": "bollywood_romantic", "sangeet_dance": "bollywood_dance", "last_train": "pop_ballad"}


def test_every_brief_lands_in_the_intended_style():
    for b in lb.load_briefs():
        new = lb.plan_for(b, "new")
        old = lb.plan_for(b, "old")
        assert new.pipeline == "song" and new.genre == EXPECTED_STYLE[b["id"]], b["id"]
        assert old.pipeline == "classic" and old.genre is None
        assert new.voice_mode == old.voice_mode == b["voice"]
        assert new.duration_s == old.duration_s == b["duration_s"]
        if b["voice"] == "sung":                                         # the words are held constant
            assert new.lyrics.text == old.lyrics.text == b["lyrics_text"] and new.lyrics.policy == "exact"


def test_prepare_writes_blind_requests_and_a_separate_key(tmp_path):
    out = tmp_path / "b1"
    m = lb.prepare(out, ["old", "new", "new_lm"], seeds=1, only=None, rng_seed=7)
    assert m["renders"] == 3 * len(m["briefs"])
    sheet = list(csv.DictReader(open(out / "sheet" / "sheet.csv", encoding="utf-8")))
    assert len(sheet) == m["renders"]
    sheet_text = (out / "sheet" / "sheet.csv").read_text()
    for word in ("old", "new_lm", "classic", "shift3"):                   # the sheet never names a condition
        assert f",{word}," not in sheet_text
    key = json.loads((out / "key" / "key.json").read_text())
    orders = set()
    for trial, k in key.items():
        conds = [v["condition"] for v in k["labels"].values()]
        assert sorted(conds) == ["new", "new_lm", "old"]
        orders.add(tuple(conds))
        seeds = {json.loads((out / "requests" / f"{trial}_{lab}.json").read_text())["seeds"][0] for lab in k["labels"]}
        assert seeds == {k["seed"]}                                        # same seed for every condition of a trial
        for lab, v in k["labels"].items():
            req = json.loads((out / "requests" / f"{trial}_{lab}.json").read_text())
            assert req["meta"] == {"batch_trial": trial}                  # nothing in the request names the condition
            if v["condition"] == "old":
                assert "model" not in req and req["params"]["shift"] == 1.0
            elif v["condition"] == "new_lm":
                assert req["model"]["lm"]["name"] == "acestep-5Hz-lm-1.7B" and req["params"]["thinking"] is True
            else:
                assert "model" not in req and req["params"]["shift"] == 3.0
    assert len(orders) > 1                                                # labels are shuffled
    with pytest.raises(SystemExit):
        lb.prepare(out, ["old", "new"], seeds=1, only=None, rng_seed=7)    # never overwritten


def test_reveal_unblinds_the_ratings(tmp_path):
    out = tmp_path / "b2"
    lb.prepare(out, ["old", "new"], seeds=1, only=["yamuna", "thodi"], rng_seed=3)
    key = json.loads((out / "key" / "key.json").read_text())
    rows = list(csv.DictReader(open(out / "sheet" / "sheet.csv", encoding="utf-8")))
    for r in rows:                                                       # this listener prefers "new"
        cond = key[r["trial"]]["labels"][r["label"]]["condition"]
        r["rating_1_to_5"] = "4" if cond == "new" else "2"
        r["favourite_x"] = "x" if cond == "new" else ""
    with open(out / "sheet" / "sheet.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=lb.SHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    text = lb.reveal(out)
    assert "| new | 4.00 (2) | 2 |" in text and "| old | 2.00 (2) | 0 |" in text
    assert "Fewer than 8 rated trials" in text and (out / "results.md").is_file()


def test_unknown_condition_or_brief_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        lb.prepare(tmp_path / "x", ["old", "nonsense"], seeds=1, only=None, rng_seed=1)
    with pytest.raises(SystemExit):
        lb.prepare(tmp_path / "y", ["old", "new"], seeds=1, only=["no_such_brief"], rng_seed=1)
