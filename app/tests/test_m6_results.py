"""M6 harness: ratings import, de-blinding, per-arm counts, promotion rule, markdown table."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from experiments import results as res
from experiments.ratings_import import RatingsError, deblind, import_ratings, RawRatings
from test_m6_support import fill_csv_with, make_exp, read_json


# ------------------------------------------------------------------ promotion rule edge cases
@pytest.mark.parametrize("succ,trials,expected", [
    (9, 9, False),          # 9 trials never promote, even unanimous
    (8, 9, False),
    (0, 0, False),
    (7, 10, True),          # exactly 70% of exactly 10 promotes
    (6, 10, False),
    (10, 10, True),
    (7, 11, False),         # 63.6%
    (8, 11, True),          # 72.7%
    (14, 20, True),
    (13, 20, False),
    (69, 100, False),
    (70, 100, True),
])
def test_passes_rule_edge_cases(succ, trials, expected):
    assert res.passes_rule(succ, trials) is expected


def test_passes_rule_rejects_nonsense():
    with pytest.raises(ValueError):
        res.passes_rule(11, 10)
    with pytest.raises(ValueError):
        res.passes_rule(-1, 10)


def test_promotion_verdicts():
    assert res.promotion(7, 10)["promoted"] and res.promotion(7, 10)["via"] == "rule"
    p9 = res.promotion(9, 9)
    assert not p9["promoted"] and "only 9 blind trials, need 10" in p9["verdict"]
    p6 = res.promotion(6, 10)
    assert not p6["promoted"] and "60%" in p6["verdict"]
    ad = res.promotion(1, 3, adopted=True)                      # explicit adoption needs no counts
    assert ad["promoted"] and ad["via"] == "adoption" and "adopted by the user" in ad["verdict"]
    assert res.promotion(8, 10, adopted=True)["via"] == "rule"  # a pass is reported as a pass
    ctl = res.promotion(10, 10, control=True)
    assert not ctl["promoted"] and "control" in ctl["verdict"]


# ------------------------------------------------------------------ de-blinding
def synthetic_key(n=10):
    """A hand-made key: odd trials have A=cand, B=ctl; even trials the reverse."""
    trials = {}
    for i in range(1, n + 1):
        labels = {"A": "cand", "B": "ctl"} if i % 2 else {"A": "ctl", "B": "cand"}
        trials[f"T{i:02d}"] = {"plan_index": 0, "seed": i, "take_index": 1, "labels": labels, "requests": {}}
    return {"version": "raag-blind-key/1", "sheet_id": "abc", "experiment": "E1", "title": "t",
            "primary": {"kind": "preference"}, "questions": [], "rng_seed": 0,
            "arms": {"cand": {"params": {}, "control": False}, "ctl": {"params": {}, "control": True}},
            "trials": trials}


def test_deblind_maps_labels_to_arms_correctly():
    key = synthetic_key(4)
    raw = RawRatings(choices={"T01": "A", "T02": "A", "T03": "B", "T04": "tie"})
    d = deblind(raw, key)
    # T01 A=cand -> cand; T02 A=ctl -> ctl; T03 B=ctl -> ctl; T04 tie
    assert d.wins == {"cand": 1, "ctl": 2}
    assert d.ties == 1 and d.preference_trials == 4
    assert d.per_trial["T01"]["choice"] == "cand" and d.per_trial["T02"]["choice"] == "ctl"
    assert d.per_trial["T04"]["choice"] == "tie"


def test_blank_trials_are_skipped_not_counted():
    key = synthetic_key(4)
    d = deblind(RawRatings(choices={"T01": "A"}), key)
    assert d.preference_trials == 1 and d.skipped == ["T02", "T03", "T04"]


def test_choice_labels_are_case_insensitive_and_tie_words():
    key = synthetic_key(3)
    d = deblind(RawRatings(choices={"T01": "a", "T02": "NEITHER", "T03": "tie"}), key)
    assert d.wins["cand"] == 1 and d.ties == 2


def test_problems_are_reported_together():
    key = synthetic_key(3)
    with pytest.raises(RatingsError) as ei:
        deblind(RawRatings(choices={"T01": "C", "T99": "A", "T02": "A"}, adopted=["nope"]), key)
    msg = " | ".join(ei.value.problems)
    assert "T01" in msg and "T99" in msg and "nope" in msg and len(ei.value.problems) == 3


# ------------------------------------------------------------------ file formats
def test_csv_and_json_give_the_same_tallies(tmp_path):
    key = synthetic_key(4)
    kp = tmp_path / "key.json"
    kp.write_text(json.dumps(key))
    cp = tmp_path / "r.csv"
    cp.write_text("trial,brief,A,B,choice,notes\nT01,x,,,A,\nT02,x,,,B,hmm\nT03,x,,,tie,\nT04,x,,,,\n")
    jp = tmp_path / "r.json"
    jp.write_text(json.dumps({"ratings": [{"trial": "T01", "choice": "A"}, {"trial": "T02", "choice": "B"},
                                          {"trial": "T03", "choice": "tie"}, {"trial": "T04"}]}))
    dc, dj = import_ratings(cp, kp), import_ratings(jp, kp)
    assert dc.wins == dj.wins == {"cand": 2, "ctl": 0}          # T01 A=cand, T02 B=cand
    assert dc.ties == dj.ties == 1 and dc.skipped == dj.skipped == ["T04"]
    jl = tmp_path / "list.json"
    jl.write_text(json.dumps([{"trial": "T01", "choice": "B"}]))
    assert import_ratings(jl, kp).wins == {"cand": 0, "ctl": 1}


def test_adoption_from_json_and_argument(tmp_path):
    kp = tmp_path / "key.json"
    kp.write_text(json.dumps(synthetic_key(2)))
    jp = tmp_path / "r.json"
    jp.write_text(json.dumps({"adopted": ["cand"], "ratings": []}))
    assert import_ratings(jp, kp).adopted == ["cand"]
    assert import_ratings(jp, kp, adopted=["cand", "ctl"]).adopted == ["cand", "ctl"]
    with pytest.raises(RatingsError):
        import_ratings(jp, kp, adopted=["bogus"])


def test_duplicate_rows_and_bad_json_are_rejected(tmp_path):
    kp = tmp_path / "key.json"
    kp.write_text(json.dumps(synthetic_key(2)))
    cp = tmp_path / "r.csv"
    cp.write_text("trial,choice\nT01,A\nT01,B\n")
    with pytest.raises(RatingsError, match="duplicate"):
        import_ratings(cp, kp)
    jp = tmp_path / "r.json"
    jp.write_text(json.dumps([{"trial": "T01", "choice": "A"}, {"trial": "T01", "choice": "B"}]))
    with pytest.raises(RatingsError, match="duplicate"):
        import_ratings(jp, kp)
    cp.write_text("brief,choice\nx,A\n")
    with pytest.raises(RatingsError, match="trial"):
        import_ratings(cp, kp)
    bad_key = tmp_path / "bad.json"
    bad_key.write_text("{}")
    with pytest.raises(RatingsError):
        import_ratings(jp, bad_key)


# ------------------------------------------------------------------ end to end with a real generated sheet
@pytest.mark.parametrize("share,promoted", [(10, True), (7, True), (6, False)])
def test_end_to_end_ten_trials(tmp_path, share, promoted):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3, 4), name=f"e{share}")      # 3 plans x 4 seeds = 12 trials
    key = read_json(out / "key" / "key.json")
    assert len(key["trials"]) == 12
    # rate only the first 10 trials; leave the last two blank
    rows = {"n": 0}

    def pick(row, kt):
        rows["n"] += 1
        if rows["n"] > 10:
            return ""
        want = "shift_3.0" if rows["n"] <= share else "shift_1.0"
        return [lab for lab, a in kt["labels"].items() if a == want][0]
    filled = fill_csv_with(out, pick)
    r, md = res.results_from_files(out / "key" / "key.json", filled)
    arm = {a["arm"]: a for a in r["arms"]}
    assert arm["shift_3.0"]["successes"] == share and arm["shift_3.0"]["trials"] == 10
    assert arm["shift_1.0"]["successes"] == 10 - share
    assert arm["shift_3.0"]["promoted"] is promoted and arm["shift_1.0"]["promoted"] is False
    assert len(r["skipped_trials"]) == 2
    assert "| shift_3.0 | candidate |" in md and "| shift_1.0 | control |" in md
    assert ("PROMOTED by the rule" in md) == promoted


def test_end_to_end_nine_trials_never_promote_but_adoption_does(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3))                            # 9 trials
    key = read_json(out / "key" / "key.json")
    assert len(key["trials"]) == 9
    filled = fill_csv_with(out, lambda row, kt: [l for l, a in kt["labels"].items() if a == "shift_3.0"][0])
    r, md = res.results_from_files(out / "key" / "key.json", filled)
    cand = [a for a in r["arms"] if a["arm"] == "shift_3.0"][0]
    assert (cand["successes"], cand["trials"], cand["promoted"]) == (9, 9, False)
    assert "only 9 blind trials, need 10" in md and r["promoted_arms"] == []
    r2, md2 = res.results_from_files(out / "key" / "key.json", filled, adopted=["shift_3.0"])
    assert r2["promoted_arms"] == ["shift_3.0"] and "adopted by the user" in md2
    assert "Explicitly adopted by the user: shift_3.0." in md2


def test_ties_count_as_trials_but_not_wins(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3, 4))
    n = {"i": 0}

    def pick(row, kt):
        n["i"] += 1
        if n["i"] <= 7:
            return [l for l, a in kt["labels"].items() if a == "shift_3.0"][0]
        return "tie" if n["i"] <= 10 else ""
    r, md = res.results_from_files(out / "key" / "key.json", fill_csv_with(out, pick))
    cand = [a for a in r["arms"] if a["arm"] == "shift_3.0"][0]
    assert (cand["successes"], cand["trials"], cand["promoted"]) == (7, 10, True)     # 3 ties still count
    assert r["ties"] == 3 and "Ties: 3." in md


def test_always_picking_A_does_not_promote_either_arm(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3, 4))
    r, _ = res.results_from_files(out / "key" / "key.json", fill_csv_with(out, lambda row, kt: "A"))
    cand = [a for a in r["arms"] if a["arm"] == "shift_3.0"][0]
    assert cand["successes"] == 6 and cand["trials"] == 12 and not cand["promoted"]   # balanced orientation


# ------------------------------------------------------------------ question experiments
def test_question_experiment_yes_rates_and_promotion(tmp_path):
    out = make_exp(tmp_path, "E2", seeds=(1, 2, 3, 4))                         # 3 plans x 4 = 12 trials, 3 arms
    key = read_json(out / "key" / "key.json")
    assert key["primary"] == {"kind": "question", "name": "similar_but_different"}
    p = out / "sheet" / "sheet.csv"
    rows = list(csv.DictReader(p.read_text("utf-8").splitlines()))
    answered = 0
    for r in rows:
        kt = key["trials"][r["trial"]]
        for lab, arm in kt["labels"].items():
            # arm 0.3: always yes; arm 0.1: yes in 5 of the first 10; arm 0.5: never
            if arm == "retake_variance_0.3":
                v = "yes"
            elif arm == "retake_variance_0.1":
                answered += 1
                v = "yes" if answered <= 5 else "no"
            else:
                v = "no"
            r[f"similar_but_different_{lab}"] = v
    filled = out / "filled.csv"
    with filled.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    r, md = res.results_from_files(p.parent.parent / "key" / "key.json", filled)
    by = {a["arm"]: a for a in r["arms"]}
    assert by["retake_variance_0.3"]["trials"] == 12 and by["retake_variance_0.3"]["promoted"]
    assert by["retake_variance_0.5"]["successes"] == 0 and not by["retake_variance_0.5"]["promoted"]
    assert by["retake_variance_0.1"]["successes"] == 5 and not by["retake_variance_0.1"]["promoted"]
    assert r["promoted_arms"] == ["retake_variance_0.3"]
    assert "Yes: similar_but_different" in md


def test_secondary_question_is_information_only(tmp_path):
    out = make_exp(tmp_path, "E3", seeds=(1, 2, 3, 4))
    key = read_json(out / "key" / "key.json")
    p = out / "sheet" / "sheet.csv"
    rows = list(csv.DictReader(p.read_text("utf-8").splitlines()))
    for r in rows:
        kt = key["trials"][r["trial"]]
        r["choice"] = [l for l, a in kt["labels"].items() if a == "cover_strength_0.8"][0]
        for lab in kt["labels"]:
            r[f"keeps_structure_{lab}"] = "yes"
    filled = out / "f.csv"
    with filled.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    r, md = res.results_from_files(out / "key" / "key.json", filled)
    assert r["promoted_arms"] == ["cover_strength_0.8"]                   # from the preference, not the question
    assert r["other_questions"]["keeps_structure"]["cover_strength_0.5"] == {"yes": 12, "answered": 12}
    assert "information only" in md


def test_bad_yes_no_and_unknown_question_rejected(tmp_path):
    out = make_exp(tmp_path, "E4", seeds=(1,))
    p = out / "sheet" / "sheet.csv"
    rows = list(csv.DictReader(p.read_text("utf-8").splitlines()))
    rows[0]["melody_voice_retained_A"] = "maybe"
    f = out / "bad.csv"
    with f.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(RatingsError, match="yes or no"):
        res.results_from_files(out / "key" / "key.json", f)
    j = out / "q.json"
    j.write_text(json.dumps([{"trial": "T01", "answers": {"made_up": {"A": "yes"}}}]))
    with pytest.raises(RatingsError, match="unknown question"):
        res.results_from_files(out / "key" / "key.json", j)


def test_cli_results_writes_markdown(tmp_path, capsys):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3, 4))
    filled = fill_csv_with(out, lambda row, kt: [l for l, a in kt["labels"].items() if a == "shift_3.0"][0])
    md = tmp_path / "results.md"
    rc = res.main(["--key", str(out / "key" / "key.json"), "--ratings", str(filled), "--out", str(md)])
    assert rc == 0 and "PROMOTED by the rule (12/12)" in md.read_text("utf-8")
    bad = tmp_path / "bad.csv"
    bad.write_text("trial,choice\nT01,Z\n")
    assert res.main(["--key", str(out / "key" / "key.json"), "--ratings", str(bad)]) == 2
