"""Recipes are data: they load, validate, compile, and match the preserved requests."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[2]

import pytest

from backend import compiler
from backend.plan_schema import RECIPE_IDS

REQ = {"r1_flute_focus": "yamuna", "r2_warm_ensemble": "daylight", "r3_hindi_ballad": "thodi", "r4_fusion": "moonlit"}


def original(recipe_id):
    return json.loads((ROOT / "context_pack/recipes" / REQ[recipe_id] / "request.json").read_text("utf-8"))["params"]


def test_four_recipes_exist_and_r4_hidden():
    for rid in RECIPE_IDS:
        r = compiler.load_recipe(rid)
        assert r["id"] == rid and (ROOT / r["evidence"]).exists()
    assert compiler.load_recipe("r4_fusion")["status"] == "unrated"
    assert [r["id"] for r in compiler.list_recipes()] == list(RECIPE_IDS[:3])
    assert len(compiler.list_recipes(include_hidden=True)) == 4


@pytest.mark.parametrize("rid", RECIPE_IDS)
def test_defaults_validate_and_compile_without_drops(rid):
    out = compiler.compile(compiler.default_plan(rid))
    rep = out["compile_report"]
    assert len(out["caption"]) <= 512 and rep["dropped"] == [] and rep["conflicts"] == []


@pytest.mark.parametrize("rid", RECIPE_IDS)
def test_params_match_preserved_request(rid):
    orig, got = original(rid), compiler.compile(compiler.default_plan(rid))["params"]
    assert set(got) | {"seed"} == set(orig)
    for key, val in got.items():
        if key not in ("caption", "lyrics"):
            assert val == orig[key], key


def test_recipes_carry_provenance():
    p = compiler.default_plan("r1_flute_focus")
    assert p.provenance["lead"].source == "recipe" and "Yamuna" in compiler.load_recipe("r1_flute_focus")["source_piece"]


def test_daylight_skeleton_reproduces_original_lyrics_exactly():
    assert compiler.compile(compiler.default_plan("r2_warm_ensemble"))["lyrics"] == original("r2_warm_ensemble")["lyrics"]


def test_to_engine_request_contract():
    out = compiler.compile(compiler.default_plan("r1_flute_focus"))
    req = compiler.to_engine_request(out, [24102701, 24102702, 24102703])
    assert req["schema"] == "raag-engine-request/1" and req["seeds"] == [24102701, 24102702, 24102703]
    assert "seed" not in req["params"] and req["params"]["caption"] == out["caption"]
    assert req["params"]["thinking"] is False and req["params"]["inference_steps"] == 8
    for bad in ([], [1, 1], [1.5], [True]):
        with pytest.raises(ValueError):
            compiler.to_engine_request(out, bad)
    bad = json.loads(json.dumps(out))
    bad["params"]["caption"] = "x" * 513
    with pytest.raises(compiler.CompileError):
        compiler.to_engine_request(bad, [1])


def test_effective_params_differ_only_in_guidance_scale():
    out = compiler.compile(compiler.default_plan("r1_flute_focus"))
    assert out["params"]["guidance_scale"] == 7.0 and out["effective_params"]["guidance_scale"] == 1.0
    diff = {k for k in out["params"] if out["params"][k] != out["effective_params"][k]}
    assert diff == {"guidance_scale"}
    assert out["params"]["shift"] == 1.0 and out["params"]["normalization_db"] == -1.5


def test_requests_pass_the_m0_engine_validator_when_present():
    import importlib.util
    path = ROOT / "app/engine/run_takes.py"
    if not path.exists():
        pytest.skip("app/engine/run_takes.py not present")
    spec = importlib.util.spec_from_file_location("run_takes_m0", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                                  # validation path must not import torch
    known = set(compiler.ENGINE_DEFAULTS)
    for rid in RECIPE_IDS:
        req = compiler.to_engine_request(compiler.compile(compiler.default_plan(rid)), [24103001, 24103002], audio_format="flac")
        assert mod.validate_request(req, known) == []
