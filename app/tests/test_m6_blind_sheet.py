"""M6 harness: engine request files per arm (identical seeds, only the tested parameter differs) and a
randomised blind sheet whose key is stored separately."""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from backend import compiler
from experiments import blind_sheet as bs
from test_m6_support import BRIEFS, e_items, make_exp, read_json

ROOT = Path(__file__).resolve().parents[2]


def load_requests(exp_dir):
    exp = read_json(exp_dir / "experiment.json")
    return exp, {arm: [read_json(exp_dir / rel) for rel in rels] for arm, rels in exp["requests"].items()}


# ------------------------------------------------------------------ arms differ only in the tested parameter
@pytest.mark.parametrize("exp_id", sorted(bs.EXPERIMENTS))
def test_arms_differ_only_in_the_tested_parameter_and_seeds_are_identical(tmp_path, exp_id):
    out = make_exp(tmp_path, exp_id, seeds=(11, 22, 33))
    exp, reqs = load_requests(out)
    defn = bs.EXPERIMENTS[exp_id]
    arm_ids = [a.id for a in defn.arms]
    assert list(reqs) == arm_ids
    tested = {k for a in defn.arms for k in a.params}
    assert set(exp["tested_params"]) == tested
    for i in range(len(BRIEFS)):
        per_arm = {a: reqs[a][i] for a in arm_ids}
        first = per_arm[arm_ids[0]]
        for a, req in per_arm.items():
            assert req["seeds"] == [11, 22, 33]                       # identical seeds across arms
            assert req["schema"] == first["schema"] and req.get("audio_format") == first.get("audio_format")
            diff = {k for k in set(req["params"]) | set(first["params"]) if req["params"].get(k) != first["params"].get(k)}
            assert diff <= tested, (a, diff - tested)                 # nothing but the tested parameter differs
            for k, v in defn.arms[arm_ids.index(a)].params.items():
                assert req["params"][k] == v                          # and the tested parameter has the arm's value
            assert req["meta"]["arm"] == a and req["meta"]["plan_index"] == i
        if len(arm_ids) > 1:
            assert any(per_arm[a]["params"] != first["params"] for a in arm_ids[1:])
    # the caption is the compiler's, same for every arm
    caps = {reqs[a][0]["params"]["caption"] for a in arm_ids}
    assert caps == {compiler.compile(bs.load_specs([e_items(exp_id)[0]])[0].plan)["caption"]}


def test_e1_shift_values_and_validator_acceptance(tmp_path):
    out = make_exp(tmp_path, "E1")
    _, reqs = load_requests(out)
    assert {a: r[0]["params"]["shift"] for a, r in reqs.items()} == {"shift_1.0": 1.0, "shift_3.0": 3.0}
    path = ROOT / "app/engine/run_takes.py"
    if not path.exists():
        pytest.skip("engine not present")
    spec = importlib.util.spec_from_file_location("run_takes_m0_m6", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    known = set(compiler.ENGINE_DEFAULTS)
    for exp_id in ("E1", "E2"):
        out2 = make_exp(tmp_path, exp_id, name=f"v_{exp_id}")
        _, reqs2 = load_requests(out2)
        for rs in reqs2.values():
            for r in rs:
                assert mod.validate_request(r, known) == [], exp_id
    # E3-E5 are written but flagged: the M0 validator rejects cover/repaint today
    out3 = make_exp(tmp_path, "E3", name="v_E3")
    exp3, reqs3 = load_requests(out3)
    assert exp3["engine_ready"] is False and "rejects" in exp3["engine_notes"]
    assert mod.validate_request(next(iter(reqs3.values()))[0], known) != []


def test_e2_shares_one_retake_seed_and_varies_only_variance(tmp_path):
    out = make_exp(tmp_path, "E2", seeds=(5,))
    exp, reqs = load_requests(out)
    vals = {a: r[0]["params"]["retake_variance"] for a, r in reqs.items()}
    assert vals == {"retake_variance_0.1": 0.1, "retake_variance_0.3": 0.3, "retake_variance_0.5": 0.5}
    assert len({r[0]["params"]["retake_seed"] for r in reqs.values()}) == 1
    assert reqs["retake_variance_0.1"][0]["params"]["retake_seed"] == exp["retake_seed"] not in (None, 5)
    out_b = make_exp(tmp_path, "E2", seeds=(5,), name="e2b", retake_seed=999)
    assert load_requests(out_b)[0]["retake_seed"] == 999


def test_e3_e4_e5_request_shapes(tmp_path):
    _, r3 = load_requests(make_exp(tmp_path, "E3"))
    p = r3["cover_strength_0.5"][0]["params"]
    assert p["task_type"] == "cover" and p["src_audio"] == "/data/takes/fav.flac" and p["duration"] == 150.0
    assert r3["cover_strength_0.8"][0]["params"]["audio_cover_strength"] == 0.8
    _, r4 = load_requests(make_exp(tmp_path, "E4"))
    p = r4["repaint_splice"][0]["params"]
    assert (p["task_type"], p["chunk_mask_mode"], p["repainting_start"], p["repainting_end"]) == (
        "repaint", "explicit", 40.0, 50.0)
    assert p["repaint_wav_crossfade_sec"] == 0.0 and r4["repaint_splice"][0]["audio_format"] == "wav"
    exp5, r5 = load_requests(make_exp(tmp_path, "E5"))
    assert r5["flow_edit_morph"][0]["params"]["flow_edit_morph"] is True
    assert r5["cover"][0]["params"]["flow_edit_morph"] is False
    assert r5["cover"][0]["params"]["flow_edit_source_caption"] == "Gentle flute and tanpura, slow."


def test_input_validation(tmp_path):
    items = e_items("E1")
    with pytest.raises(ValueError):
        bs.create_experiment("E9", items, [1], tmp_path / "a")
    with pytest.raises(ValueError):
        bs.create_experiment("E1", items, list(range(9)), tmp_path / "b")              # > 8 seeds
    with pytest.raises(ValueError):
        bs.create_experiment("E1", items, [1, 1], tmp_path / "c")                      # duplicate seeds
    with pytest.raises(ValueError):
        bs.create_experiment("E1", [], [1], tmp_path / "d")
    with pytest.raises(ValueError, match="source_audio"):
        bs.create_experiment("E3", [{"brief": BRIEFS[0]}], [1], tmp_path / "e")
    with pytest.raises(ValueError, match="span"):
        bs.create_experiment("E4", [{"brief": BRIEFS[0], "source_audio": "x.wav"}], [1], tmp_path / "f")
    with pytest.raises(ValueError, match="source_caption"):
        bs.create_experiment("E5", [{"brief": BRIEFS[0], "source_audio": "x.flac"}], [1], tmp_path / "g")
    for n in "abcdefg":
        assert not (tmp_path / n).exists()                                              # nothing half-written


def test_fresh_folder_required(tmp_path):
    out = make_exp(tmp_path, "E1")
    with pytest.raises(FileExistsError):
        bs.create_experiment("E1", e_items("E1"), [1], out)
    with pytest.raises(FileNotFoundError):
        bs.create_experiment("E1", e_items("E1"), [1], tmp_path / "nope" / "x")


# ------------------------------------------------------------------ the sheet
def test_key_is_stored_separately_and_not_leaked_into_the_sheet(tmp_path):
    out = make_exp(tmp_path, "E1")
    key = read_json(out / "key" / "key.json")
    sheet_files = sorted((out / "sheet").iterdir())
    assert [p.name for p in sheet_files] == ["sheet.csv", "sheet.json"]
    blob = "".join(p.read_text("utf-8") for p in sheet_files)
    for secret in ("shift", "3.0", "control", "requests/", "plan01", "retake", "cover", "params"):
        assert secret.lower() not in blob.lower(), secret      # neither arm names, values nor the tested parameter
    for arm_id in key["arms"]:
        assert arm_id not in blob
    for t in key["trials"].values():
        assert str(t["seed"]) not in blob
    sheet = read_json(out / "sheet" / "sheet.json")
    assert set(sheet) == {"version", "sheet_id", "experiment", "title", "labels", "primary", "questions",
                          "instructions", "trials"}
    assert sheet["labels"] == ["A", "B"]
    for row in sheet["trials"]:
        assert set(row) == {"trial", "brief", "files"}
        assert set(row["files"].values()) == {f"listening/{row['trial']}_A", f"listening/{row['trial']}_B"}
    assert key["sheet_id"] == sheet["sheet_id"]
    # arms appear only in key/ and experiment.json (operator files)
    assert "shift_3.0" in (out / "key" / "key.json").read_text() and "shift_3.0" in (out / "experiment.json").read_text()


def test_every_plan_seed_pair_is_a_trial_and_labels_cover_all_arms(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(101, 202))
    key = read_json(out / "key" / "key.json")
    assert len(key["trials"]) == len(BRIEFS) * 2
    pairs = {(t["plan_index"], t["seed"]) for t in key["trials"].values()}
    assert pairs == {(p, s) for p in range(len(BRIEFS)) for s in (101, 202)}
    for tid, t in key["trials"].items():
        assert sorted(t["labels"]) == ["A", "B"] and sorted(t["labels"].values()) == ["shift_1.0", "shift_3.0"]
        for arm_id, rel in t["requests"].items():
            assert (out / rel).is_file() and f"/{arm_id}/" in rel
    assert sorted(key["trials"]) == [f"T{i:02d}" for i in range(1, 7)]


def test_two_arm_orientation_is_balanced(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(1, 2, 3, 4, 5, 6, 7, 8))
    key = read_json(out / "key" / "key.json")
    a_is_3 = sum(1 for t in key["trials"].values() if t["labels"]["A"] == "shift_3.0")
    n = len(key["trials"])
    assert n == 24 and a_is_3 == 12                       # an "always A" rater gets exactly half each


def test_deterministic_per_rng_seed(tmp_path):
    a = make_exp(tmp_path, "E1", rng_seed=7, name="a")
    b = make_exp(tmp_path, "E1", rng_seed=7, name="b")
    c = make_exp(tmp_path, "E1", rng_seed=8, name="c")

    def snapshot(d):
        return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}
    sa, sb = snapshot(a), snapshot(b)
    assert sa.keys() == sb.keys()
    for k in sa:
        if k != "key/key.json" and k != "sheet/sheet.json" and k != "sheet/sheet.csv":
            assert sa[k] == sb[k], k
    assert sa["key/key.json"] == sb["key/key.json"]                    # byte-identical for the same rng seed
    assert sa["sheet/sheet.json"] == sb["sheet/sheet.json"] and sa["sheet/sheet.csv"] == sb["sheet/sheet.csv"]
    kc = read_json(c / "key" / "key.json")
    ka = read_json(a / "key" / "key.json")
    assert {t: v["labels"] for t, v in ka["trials"].items()} != {t: v["labels"] for t, v in kc["trials"].items()} \
        or {t: (v["plan_index"], v["seed"]) for t, v in ka["trials"].items()} != \
           {t: (v["plan_index"], v["seed"]) for t, v in kc["trials"].items()}
    assert ka["sheet_id"] != kc["sheet_id"]


def test_assign_labels_three_arms_is_a_permutation_each_time():
    labs = bs.assign_labels(["x", "y", "z"], 30, 3, "E2")
    assert all(sorted(l.values()) == ["x", "y", "z"] and sorted(l) == ["A", "B", "C"] for l in labs)
    assert labs == bs.assign_labels(["x", "y", "z"], 30, 3, "E2")
    assert len({tuple(l.values()) for l in labs}) > 1


def test_csv_sheet_is_fillable_and_has_question_columns(tmp_path):
    import csv
    out = make_exp(tmp_path, "E3")
    rows = list(csv.DictReader((out / "sheet" / "sheet.csv").read_text("utf-8").splitlines()))
    assert list(rows[0]) == ["trial", "brief", "reference", "A", "B", "choice", "keeps_structure_A",
                             "keeps_structure_B", "notes"]
    out2 = make_exp(tmp_path, "E4")
    rows2 = list(csv.DictReader((out2 / "sheet" / "sheet.csv").read_text("utf-8").splitlines()))
    assert list(rows2[0]) == ["trial", "brief", "reference", "A", "melody_voice_retained_A", "notes"]


def test_stage_audio_uses_neutral_names(tmp_path):
    out = make_exp(tmp_path, "E1", seeds=(101,))
    key = read_json(out / "key" / "key.json")
    outputs = tmp_path / "outputs"
    for arm in key["arms"]:
        for i in range(len(BRIEFS)):
            d = outputs / arm / f"plan{i + 1:02d}.partial"
            d.mkdir(parents=True)
            (d / "take_01_s101.flac").write_bytes(f"{arm}|{i}".encode())
    res = bs.stage_audio(out, outputs)
    assert res["missing"] == [] and len(res["copied"]) == len(BRIEFS) * 2
    for tid, t in key["trials"].items():
        for lab, arm in t["labels"].items():
            assert (out / "listening" / f"{tid}_{lab}.flac").read_bytes() == f"{arm}|{t['plan_index']}".encode()
    assert not any("shift" in p.name for p in (out / "listening").iterdir())


def test_cli_create_and_list(tmp_path, capsys):
    plans = tmp_path / "plans.json"
    plans.write_text(json.dumps(BRIEFS[:2]))
    rc = bs.main(["create", "E1", "--plans", str(plans), "--seeds", "1,2,3,4,5", "--out", str(tmp_path / "cli"),
                  "--rng-seed", "3"])
    assert rc == 0 and json.loads(capsys.readouterr().out)["trials"] == 10
    assert bs.main(["list"]) == 0
