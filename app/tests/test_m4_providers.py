"""M4: provider contract (AT-M4-01), claude -p provider with a stub executable (AT-M4-02),
Anthropic API provider with a MockTransport, registry/fallback, and AT-M4-06 (Write for me under Basic).

No real subprocess of `claude`, no network: every test uses a stub script or httpx.MockTransport.
"""
import copy
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
import pytest

from backend import compiler
from backend.plan_schema import INSTRUMENT_IDS, Plan
from backend.planner_base import (BriefCard, Controls, PlanPatch, PlannerInvalidOutput, PlannerTimeout,
                                  PlannerUnavailable, UnsupportedByPlanner)
from backend.planner_rules import BasicPlanner
from backend.providers import SYSTEM_PROMPT, llm_schema, LlmCardDraft
from backend.providers import registry
from backend.providers.anthropic_api import DEFAULT_MODEL, AnthropicApiPlanner
from backend.providers.claude_cli import DISALLOWED_TOOLS, ClaudeCliPlanner
from test_m4_support import GOOD_CARD, Api, Stub, envelope, text_response, tool_response

BRIEF = "a slow tender flute piece with tanpura and light tabla, about two minutes"
KEY = "sk-ant-TESTKEY-123456"


def card(**over):
    c = copy.deepcopy(GOOD_CARD)
    c.update(over)
    return c


# ---------------------------------------------------------------------------------------------
# AT-M4-01: provider contract
# ---------------------------------------------------------------------------------------------
def make_ok_cli(tmp_path):
    return Stub(tmp_path, [{"stdout": envelope(GOOD_CARD)}]).planner()


def make_ok_api(tmp_path):
    return Api([tool_response(GOOD_CARD)]).planner()


@pytest.mark.parametrize("make,name,label", [
    (make_ok_cli, "claude_cli", "Claude (local CLI)"),
    (make_ok_api, "anthropic_api", "Claude (API)"),
])
def test_at_m4_01_valid_card_contract(tmp_path, make, name, label):
    p = make(tmp_path)
    c = p.plan(BRIEF)
    assert isinstance(c, BriefCard) and isinstance(c.plan, Plan)
    assert (c.provider, c.provider_label, c.is_llm, c.fallback) == (name, label, True, False)
    assert c.plan.brief == BRIEF                       # brief text is the user's, not the model's
    assert c.plan.lead.instrument == "bansuri"
    assert [s.instrument for s in c.plan.supports] == ["tanpura", "tabla"]
    assert c.plan.provenance["lead"].source == "suggested"
    # the card compiles with the deterministic compiler
    comp = compiler.compile(c.plan)
    assert len(comp["caption"]) <= 512 and "flute" in comp["caption"].lower()
    assert any(label in n for n in c.notes)            # honest note naming the real provider


@pytest.mark.parametrize("make", [make_ok_cli, make_ok_api])
def test_at_m4_01_disabled_is_typed_error(tmp_path, make):
    p = make(tmp_path)
    p.enabled = False
    with pytest.raises(PlannerUnavailable) as ei:
        p.plan(BRIEF)
    assert ei.value.code == "planner_disabled"


def test_at_m4_01_timeout_is_typed_and_default_is_60(tmp_path):
    assert ClaudeCliPlanner().timeout_s == 60 and AnthropicApiPlanner().timeout_s == 60
    stub = Stub(tmp_path, [{"sleep": 30}])
    p = stub.planner(timeout_s=1)
    with pytest.raises(PlannerTimeout):
        p.plan(BRIEF)
    assert len(stub.calls) == 1                         # a timeout is not retried

    api = Api([httpx.ReadTimeout("slow")])
    with pytest.raises(PlannerTimeout):
        api.planner().plan(BRIEF)
    assert len(api.requests) == 1


def test_at_m4_01_timeout_kills_the_child_group(tmp_path):
    import time
    stub = Stub(tmp_path, [{"sleep": 30}])
    t0 = time.time()
    with pytest.raises(PlannerTimeout):
        stub.planner(timeout_s=1).plan(BRIEF)
    assert time.time() - t0 < 10                        # returned promptly, did not wait for the sleeper


def test_at_m4_01_registry_caps_timeout_at_60():
    p = registry.get_planner({"planner": {"provider": "claude_cli", "smart_enabled": True,
                                          "claude_cli": {"timeout_s": 600}}})
    assert p.primary.timeout_s == 60


@pytest.mark.parametrize("which", ["cli", "api"])
def test_at_m4_01_fallback_sets_flag_and_banner(tmp_path, which):
    if which == "cli":
        stub = Stub(tmp_path, [{"sleep": 30}])
        smart = stub.planner(timeout_s=1)
    else:
        smart = Api([httpx.ConnectTimeout("t")]).planner()
    fp = registry.FallbackPlanner(smart)
    out = fp.plan_with_status(BRIEF)
    assert out.fallback is True
    assert out.fallback_code == "planner_timeout"
    assert out.fallback_reason
    assert out.banner and smart.label in out.banner and "Basic planner" in out.banner
    assert out.card.provider == "basic" and out.card.provider_label == "Basic planner" and out.card.is_llm is False
    assert out.card.plan.lead.instrument == BasicPlanner().plan(BRIEF).plan.lead.instrument
    resp = out.to_response()
    assert resp["fallback"] is True and resp["fallback_reason"] and resp["requested_label"] == smart.label
    assert resp["provider_label"] == "Basic planner"
    assert out.card.notes[0] == out.banner


def test_at_m4_01_no_fallback_flag_on_success(tmp_path):
    fp = registry.FallbackPlanner(make_ok_api(tmp_path))
    out = fp.plan_with_status(BRIEF)
    assert out.fallback is False and out.fallback_reason is None and out.banner is None
    assert out.card.provider == "anthropic_api"


def test_at_m4_01_unexpected_provider_bug_still_falls_back():
    class Broken(AnthropicApiPlanner):
        def _transport(self, *a, **k):
            raise RuntimeError("boom")
    out = registry.FallbackPlanner(Broken(enabled=True, env={"ANTHROPIC_API_KEY": KEY})).plan_with_status(BRIEF)
    assert out.fallback and out.fallback_code == "planner_error" and "boom" not in (out.fallback_reason or "")


def test_blank_brief_is_a_value_error_not_a_fallback(tmp_path):
    fp = registry.FallbackPlanner(make_ok_api(tmp_path))
    with pytest.raises(ValueError):
        fp.plan_with_status("   ")


# ---------------------------------------------------------------------------------------------
# AT-M4-02: claude -p provider with a stub executable
# ---------------------------------------------------------------------------------------------
def test_at_m4_02_args_cwd_and_stdin(tmp_path):
    stub = Stub(tmp_path, [{"stdout": envelope(GOOD_CARD)}])
    p = stub.planner(model="sonnet")
    p.plan(BRIEF)
    (call,) = stub.calls
    argv = call["argv"]
    assert "-p" in argv
    assert argv[argv.index("--output-format") + 1] == "json"
    # --json-schema carries the BriefCard schema (the draft the model may fill)
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema == llm_schema(LlmCardDraft)
    assert "caption" not in schema["properties"] and "lyrics_text" not in schema["properties"]
    assert "lead" in schema["required"] and schema["additionalProperties"] is False
    # tool restrictions: all tools off, and every built-in tool explicitly disallowed
    assert argv[argv.index("--tools") + 1] == ""
    denied = argv[argv.index("--disallowedTools") + 1].split(",")
    assert set(DISALLOWED_TOOLS) <= set(denied) and {"Bash", "Write", "Edit", "WebFetch"} <= set(denied)
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    for flag in ("--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"):
        assert flag in argv
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert "--bare" not in argv                         # default keeps the subscription login usable
    assert argv[argv.index("--system-prompt") + 1] == SYSTEM_PROMPT
    # the prompt is on stdin, not in argv
    assert BRIEF in call["stdin"] and not any(BRIEF in a for a in argv)
    # cwd: a fresh, empty temp dir that is cleaned up afterwards
    assert call["cwd_listing"] == []
    cwd = Path(call["cwd"])
    assert not cwd.exists()
    assert Path(__file__).resolve().parents[1] not in cwd.resolve().parents
    assert "raag-claude-" in cwd.name


def test_at_m4_02_bare_flag_is_opt_in_and_keeps_api_key_only_then(tmp_path, monkeypatch):
    stub = Stub(tmp_path, [{"stdout": envelope(GOOD_CARD)}])
    stub.env["ANTHROPIC_API_KEY"] = KEY
    stub.planner().plan(BRIEF)
    assert stub.calls[-1]["has_api_key"] is False       # key scrubbed: subscription login is what runs
    stub.planner(bare=True).plan(BRIEF)
    assert "--bare" in stub.calls[-1]["argv"] and stub.calls[-1]["has_api_key"] is True


def test_at_m4_02_invalid_json_one_retry_then_success(tmp_path):
    stub = Stub(tmp_path, [{"stdout": "this is not json"}, {"stdout": envelope(GOOD_CARD)}])
    c = stub.planner().plan(BRIEF)
    assert c.provider == "claude_cli"
    assert len(stub.calls) == 2                         # exactly one retry
    assert "not valid" in stub.calls[1]["stdin"]        # the retry tells the model what was wrong


def test_at_m4_02_invalid_json_twice_raises_then_fallback(tmp_path):
    stub = Stub(tmp_path, [{"stdout": "nope"}])
    p = stub.planner()
    with pytest.raises(PlannerInvalidOutput):
        p.plan(BRIEF)
    assert len(stub.calls) == 2                         # first call + exactly one retry, never three

    sub = tmp_path / "b"
    sub.mkdir()
    stub2 = Stub(sub, [{"stdout": "nope"}])
    out = registry.FallbackPlanner(stub2.planner()).plan_with_status(BRIEF)
    assert out.fallback and out.fallback_code == "planner_invalid_output"
    assert len(stub2.calls) == 2
    assert out.card.provider == "basic"


def test_at_m4_02_schema_invalid_counts_as_invalid_json(tmp_path):
    bad = card(pace={"bucket": "slow", "bpm": 999})
    stub = Stub(tmp_path, [{"stdout": envelope(bad)}, {"stdout": envelope(GOOD_CARD)}])
    assert stub.planner().plan(BRIEF).plan.pace.bpm == 74
    assert len(stub.calls) == 2


def test_at_m4_02_result_string_and_fenced_json_accepted(tmp_path):
    env = json.dumps({"type": "result", "is_error": False, "result": "```json\n" + json.dumps(GOOD_CARD) + "\n```"})
    stub = Stub(tmp_path, [{"stdout": env}])
    assert stub.planner().plan(BRIEF).plan.lead.instrument == "bansuri"


def test_at_m4_02_provider_off_means_no_subprocess(tmp_path):
    stub = Stub(tmp_path, [{"stdout": envelope(GOOD_CARD)}])
    p = stub.planner(enabled=False)
    with pytest.raises(PlannerUnavailable):
        p.plan(BRIEF)
    with pytest.raises(PlannerUnavailable):
        p.patch(Plan.model_validate(BasicPlanner().plan(BRIEF).plan.model_dump()), "make it feel like rain on a roof")
    assert stub.calls == [] and p.calls == 0
    # settings with the toggle off (or missing) never even build a claude planner
    for settings in ({}, {"planner": {"provider": "claude_cli"}},
                     {"planner": {"provider": "claude_cli", "smart_enabled": False,
                                  "claude_cli": {"command": str(stub.bin)}}},
                     {"planner": "claude_cli"}):
        pl = registry.get_planner(settings, env=stub.env)
        assert isinstance(pl, BasicPlanner)
        pl.plan(BRIEF)
    assert stub.calls == []


def test_at_m4_02_subprocess_is_never_spawned_when_off(tmp_path, monkeypatch):
    import subprocess
    def boom(*a, **k):
        raise AssertionError("subprocess spawned while the planner is off")
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(subprocess, "run", boom)
    pl = registry.get_planner({"planner": {"provider": "claude_cli", "smart_enabled": False}})
    pl.plan(BRIEF)
    off = ClaudeCliPlanner(enabled=False)
    with pytest.raises(PlannerUnavailable):
        off.plan(BRIEF)


def test_at_m4_02_missing_binary_is_unavailable_and_falls_back(tmp_path):
    p = ClaudeCliPlanner(enabled=True, command=str(tmp_path / "no-such-claude"))
    with pytest.raises(PlannerUnavailable) as ei:
        p.plan(BRIEF)
    assert ei.value.code == "planner_binary_missing"
    assert registry.FallbackPlanner(p).plan_with_status(BRIEF).fallback_code == "planner_binary_missing"


def test_at_m4_02_nonzero_exit_is_unavailable(tmp_path):
    stub = Stub(tmp_path, [{"exit": 3, "stderr": "not logged in"}])
    with pytest.raises(PlannerUnavailable) as ei:
        stub.planner().plan(BRIEF)
    assert ei.value.code == "planner_cli_failed" and len(stub.calls) == 1


# ---------------------------------------------------------------------------------------------
# Anthropic API provider
# ---------------------------------------------------------------------------------------------
def test_api_request_shape_and_default_model():
    api = Api([tool_response(GOOD_CARD)])
    c = api.planner(key=KEY).plan(BRIEF)
    assert c.provider == "anthropic_api"
    (req,) = api.requests
    assert str(req.url) == "https://api.anthropic.com/v1/messages"
    assert req.headers["x-api-key"] == KEY and req.headers["anthropic-version"] == "2023-06-01"
    body = api.body()
    assert body["model"] == DEFAULT_MODEL == "claude-sonnet-5-5"
    assert body["tool_choice"] == {"type": "tool", "name": "submit_brief_card"}
    assert body["tools"][0]["input_schema"] == llm_schema(LlmCardDraft)
    assert body["system"] == SYSTEM_PROMPT
    assert BRIEF in body["messages"][0]["content"]
    assert "caption" not in body["tools"][0]["input_schema"]["properties"]


def test_api_model_is_configurable():
    api = Api([tool_response(GOOD_CARD)])
    api.planner(model="claude-haiku-9").plan(BRIEF)
    assert api.body()["model"] == "claude-haiku-9"
    p = registry.get_planner({"planner": {"provider": "anthropic_api", "smart_enabled": True,
                                          "anthropic_api": {"model": "my-model"}}}, env={"ANTHROPIC_API_KEY": KEY})
    assert p.primary.model == "my-model"


def test_api_disabled_or_keyless_makes_no_network_call():
    api = Api([tool_response(GOOD_CARD)])
    off = api.planner(enabled=False)
    with pytest.raises(PlannerUnavailable):
        off.plan(BRIEF)
    nokey = api.planner(key=None)
    with pytest.raises(PlannerUnavailable) as ei:
        nokey.plan(BRIEF)
    assert ei.value.code == "planner_key_missing"
    blank = api.planner(key="   ")
    with pytest.raises(PlannerUnavailable):
        blank.plan(BRIEF)
    # toggle off in settings: plain Basic, transport never touched
    pl = registry.get_planner({"planner": {"provider": "anthropic_api"}}, env={"ANTHROPIC_API_KEY": KEY},
                              http_transport=api.transport)
    assert isinstance(pl, BasicPlanner)
    pl.plan(BRIEF)
    assert api.requests == []


def test_api_off_means_httpx_client_is_not_even_built(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("httpx.Client built while the planner is off")
    monkeypatch.setattr(httpx, "Client", boom)
    with pytest.raises(PlannerUnavailable):
        AnthropicApiPlanner(enabled=False, env={"ANTHROPIC_API_KEY": KEY}).plan(BRIEF)
    registry.get_planner({"planner": {"provider": "anthropic_api"}}).plan(BRIEF)


def test_api_invalid_then_valid_is_one_retry(tmp_path):
    api = Api([tool_response({"voice_mode": "instrumental"}), tool_response(GOOD_CARD)])
    assert api.planner().plan(BRIEF).provider == "anthropic_api"
    assert len(api.requests) == 2
    assert "not valid" in api.body(1)["messages"][0]["content"]


def test_api_invalid_twice_raises_typed_error_then_fallback():
    api = Api([text_response("no json here")])
    with pytest.raises(PlannerInvalidOutput):
        api.planner().plan(BRIEF)
    assert len(api.requests) == 2
    api2 = Api([tool_response({"voice_mode": "instrumental"})])
    out = registry.FallbackPlanner(api2.planner()).plan_with_status(BRIEF)
    assert out.fallback and out.fallback_code == "planner_invalid_output" and len(api2.requests) == 2


def test_api_http_error_is_unavailable_without_retry_and_leaks_nothing():
    api = Api([httpx.Response(401, json={"type": "error", "error": {"type": "authentication_error",
                                                                     "message": "invalid x-api-key " + KEY}})])
    with pytest.raises(PlannerUnavailable) as ei:
        api.planner().plan(BRIEF)
    assert "401" in ei.value.message and KEY not in ei.value.message and "authentication_error" in ei.value.message
    assert len(api.requests) == 1


def test_api_key_never_logged_stored_or_in_errors(caplog, monkeypatch):
    """Production path: env=None, so the key lives only in os.environ and is read at call time."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    caplog.set_level(logging.DEBUG)
    api = Api([httpx.ConnectError("down")])
    p = AnthropicApiPlanner(enabled=True, transport=api.transport)
    out = registry.FallbackPlanner(p).plan_with_status(BRIEF)
    blob = json.dumps(out.to_response()) + caplog.text + repr(p) + repr(vars(p))
    assert KEY not in blob
    # read at call time: changing the environment changes what is sent
    api2 = Api([tool_response(GOOD_CARD)])
    p2 = AnthropicApiPlanner(enabled=True, transport=api2.transport)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-two")
    p2.plan(BRIEF)
    assert api2.requests[0].headers["x-api-key"] == "sk-two"
    assert "sk-two" not in repr(vars(p2))


def test_api_key_in_settings_is_ignored():
    api = Api([tool_response(GOOD_CARD)])
    settings = {"planner": {"provider": "anthropic_api", "smart_enabled": True,
                            "anthropic_api": {"api_key": "sk-from-settings"}}, "ANTHROPIC_API_KEY": "sk-also-no"}
    pl = registry.get_planner(settings, env={}, http_transport=api.transport)
    out = pl.plan_with_status(BRIEF)
    assert out.fallback and out.fallback_code == "planner_key_missing"
    assert api.requests == []


# ---------------------------------------------------------------------------------------------
# Registry, labels, status
# ---------------------------------------------------------------------------------------------
def test_registry_defaults_to_basic_and_labels_name_the_real_provider():
    assert isinstance(registry.get_planner(None), BasicPlanner)
    assert isinstance(registry.get_planner({}), BasicPlanner)
    assert isinstance(registry.get_planner({"planner": {"provider": "nonsense", "smart_enabled": True}}), BasicPlanner)
    assert registry.PROVIDER_LABELS == {"basic": "Basic planner", "claude_cli": "Claude (local CLI)",
                                        "anthropic_api": "Claude (API)"}
    assert registry.badge_for("basic") == "Basic planner" == BasicPlanner.label
    assert registry.badge_for("claude_cli") == ClaudeCliPlanner.label
    assert registry.badge_for("anthropic_api") == AnthropicApiPlanner.label
    cli = registry.get_planner({"planner": {"provider": "claude_cli", "smart_enabled": True}})
    assert isinstance(cli, registry.FallbackPlanner) and cli.label == "Claude (local CLI)" and cli.is_llm
    api = registry.get_planner({"planner": {"provider": "anthropic_api", "smart_enabled": True}})
    assert api.label == "Claude (API)" and api.name == "anthropic_api"
    flat = registry.get_planner({"planner_provider": "anthropic_api", "planner_smart_enabled": True})
    assert isinstance(flat, registry.FallbackPlanner)


def test_nothing_says_ai_under_basic(tmp_path):
    dead = Api([httpx.ConnectError("x")]).planner()
    out = registry.FallbackPlanner(dead).plan_with_status(BRIEF)
    strings = [registry.PROVIDER_LABELS["basic"], registry.PROVIDER_DESCRIPTIONS["basic"], BasicPlanner.label,
               out.card.provider_label, out.used_label, out.banner or "", registry.LYRICS_OFF_MESSAGE]
    strings += [r["label"] + " " + r["description"] for r in registry.provider_status({}) if r["id"] == "basic"]
    for s in strings:
        assert not re.search(r"\bAI\b|\bsmart\b.*\bBasic\b", s), s
    assert BasicPlanner().plan(BRIEF).is_llm is False


def test_provider_status_has_no_side_effects_and_no_key_value(monkeypatch):
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("spawn")))
    rows = registry.provider_status({}, env={"ANTHROPIC_API_KEY": KEY, "PATH": ""})
    assert [r["id"] for r in rows] == ["basic", "claude_cli", "anthropic_api"]
    assert rows[0]["active"] and rows[0]["available"] and not rows[0]["sends_data_to_anthropic"]
    assert rows[1]["available"] is False and rows[2]["available"] is True and rows[2]["sends_data_to_anthropic"]
    assert KEY not in json.dumps(rows)
    rows2 = registry.provider_status({"planner": {"provider": "claude_cli", "smart_enabled": True}}, env={})
    assert [r["active"] for r in rows2] == [False, True, False]


# ---------------------------------------------------------------------------------------------
# Patch: registry-wrapped providers return the same PlanPatch type
# ---------------------------------------------------------------------------------------------
def test_wrapped_providers_return_the_same_plan_patch_type(tmp_path):
    base_plan = BasicPlanner().plan(BRIEF).plan
    patch_obj = {"pace": {"bucket": "medium", "bpm": 90}, "feeling": ["rainy"], "summary": ["faster, rainy"]}
    api = Api([tool_response(patch_obj, "submit_plan_patch")])
    working = registry.FallbackPlanner(api.planner())
    broken = registry.FallbackPlanner(Api([httpx.ConnectError("x")]).planner())
    basic = registry.get_planner({})
    results = {
        "basic_chip": basic.patch(base_plan, "slower"),
        "wrapped_chip": working.patch(base_plan, "livelier"),
        "wrapped_free_text": working.patch(base_plan, "make it feel like rain on a tin roof"),
        "wrapped_fallback": broken.patch(base_plan, "make it feel like rain on a tin roof"),
    }
    for k, r in results.items():
        assert type(r) is PlanPatch, k
    # chips are applied by rules even with a smart provider on (no model call)
    assert results["wrapped_chip"].provider == "basic" and results["wrapped_chip"].applied == ["livelier"]
    assert len(api.requests) == 1                       # only the free-text request used the model
    ft = results["wrapped_free_text"]
    assert ft.provider == "anthropic_api" and ft.applied == ["free_text"]
    assert ft.plan.pace.bpm == 90 and ft.plan.pace.bucket == "medium" and ft.plan.feeling == ["rainy"]
    assert ft.plan.provenance["pace"].source == "suggested"
    assert ft.plan.brief == base_plan.brief and ft.plan.lyrics == base_plan.lyrics
    assert base_plan.pace.bpm != 90                      # the original plan object is untouched
    fb = results["wrapped_fallback"]
    assert fb.provider == "basic" and fb.plan == base_plan and fb.unsupported[0]["kind"] == "planner_fallback"
    out = broken.patch_with_status(base_plan, "make it feel like rain on a tin roof")
    assert out.fallback and out.used_label == "Basic planner" and out.to_response()["fallback"] is True


def test_free_text_patch_cannot_change_voice_lyrics_or_brief():
    base_plan = BasicPlanner().plan(BRIEF).plan
    evil = {"voice_mode": "sung", "lyrics": {"policy": "exact", "text": "x"}, "brief": "other", "lyrics_text": "zz",
            "key": "E minor"}
    api = Api([tool_response(evil, "submit_plan_patch")])
    p = api.planner().patch(base_plan, "make it a bit darker")
    assert p.plan.voice_mode == base_plan.voice_mode == "instrumental"
    assert p.plan.lyrics == base_plan.lyrics and p.plan.brief == base_plan.brief
    assert p.plan.key == "E minor" and p.applied == ["free_text"]
    assert any(u["kind"] == "patch_field_ignored" for u in p.unsupported)


def test_free_text_patch_off_list_instrument_rejected():
    base_plan = BasicPlanner().plan(BRIEF).plan
    api = Api([tool_response({"lead": {"instrument": "kazoo", "style": "singing"}}, "submit_plan_patch")])
    with pytest.raises(PlannerInvalidOutput):
        api.planner().patch(base_plan, "give it a funky sound")
    assert len(api.requests) == 2


# ---------------------------------------------------------------------------------------------
# AT-M4-06: "Write for me" under Basic is disabled with an explanation; smart providers draft lyrics
# ---------------------------------------------------------------------------------------------
def sung_plan():
    c = BasicPlanner().plan("a tender Hindi song with soft guitar and a female voice")
    assert c.plan.voice_mode == "sung" and c.plan.lyrics.policy == "write"
    return c


def test_at_m4_06_write_for_me_disabled_under_basic():
    basic = registry.get_planner({})
    st = registry.lyrics_status(basic)
    assert st["enabled"] is False and "smart planner" in st["reason"] and "Paste your own words" in st["reason"]
    c = sung_plan()
    assert c.needs_user_input == ["lyrics"]
    assert any(u["kind"] == "write_lyrics" for u in c.unsupported)
    with pytest.raises(UnsupportedByPlanner) as ei:
        basic.draft_lyrics(c.plan)
    assert ei.value.code == "write_lyrics_unsupported" and "Basic planner" in ei.value.message
    # the same holds when a smart provider is configured but switched off
    off = registry.get_planner({"planner": {"provider": "anthropic_api", "smart_enabled": False}})
    assert registry.lyrics_status(off)["enabled"] is False


def test_at_m4_06_smart_provider_enables_write_for_me_but_never_for_exact(tmp_path):
    api = Api([httpx.Response(200, json={"content": [{"type": "tool_use", "name": "submit_lyrics",
                                                      "input": {"text": "line one\r\nline two\n"}}]})])
    fp = registry.FallbackPlanner(api.planner())
    assert registry.lyrics_status(fp) == {"enabled": True, "reason": None}
    d = fp.draft_lyrics(sung_plan().plan)
    assert d.text == "line one\nline two" and d.provider == "anthropic_api"
    exact = BasicPlanner().plan("a tender Hindi song", Controls(lyrics_text="मेरे शब्द\nदूसरी पंक्ति")).plan
    assert exact.lyrics.policy == "exact"
    before = len(api.requests)
    with pytest.raises(UnsupportedByPlanner):
        fp.draft_lyrics(exact)
    assert len(api.requests) == before                  # nothing sent for exact lyrics


def test_draft_lyrics_failure_surfaces_the_smart_error_not_a_silent_substitute():
    fp = registry.FallbackPlanner(Api([httpx.ConnectTimeout("t")]).planner())
    with pytest.raises(PlannerTimeout):
        fp.draft_lyrics(sung_plan().plan)


def test_cli_failure_reason_comes_from_the_stdout_envelope_when_stderr_is_empty():
    from backend.providers.claude_cli import _envelope_error
    env = '{"type":"result","is_error":true,"result":"Failed to authenticate: OAuth session expired and could not be refreshed"}'
    assert "OAuth session expired" in _envelope_error(env)
    assert _envelope_error("") == "no message" and _envelope_error("[]") == "no message"
    assert _envelope_error("not json at all") == "not json at all"
