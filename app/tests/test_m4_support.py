"""Shared helpers for the M4 tests (no tests in here): a stub `claude` executable and an httpx MockTransport."""
import json
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.providers import anthropic_api

GOOD_CARD = {
    "voice_mode": "instrumental",
    "lead": {"instrument": "bansuri", "style": "singing"},
    "supports": [{"instrument": "tanpura", "role": "drone", "presence": "gentle"},
                 {"instrument": "tabla", "role": "rhythm", "presence": "sparse"}],
    "feeling": ["tender", "warm"],
    "pace": {"bucket": "slow", "bpm": 74},
    "key": "D major",
    "arc": "slow_build",
    "fullness": "balanced",
    "matched": ["flute", "tender"],
    "notes": [],
}

STUB_SOURCE = '''#!{py}
import json, os, sys, time
d = os.environ["STUB_DIR"]
with open(os.path.join(d, "scenario.json")) as f:
    scenario = json.load(f)
log = os.path.join(d, "calls.jsonl")
n = 0
if os.path.exists(log):
    with open(log) as f:
        n = len(f.read().splitlines())
stdin = sys.stdin.read()
rec = {{"argv": sys.argv[1:], "cwd": os.getcwd(), "cwd_listing": sorted(os.listdir(".")), "stdin": stdin,
        "has_api_key": "ANTHROPIC_API_KEY" in os.environ}}
with open(log, "a") as f:
    f.write(json.dumps(rec) + "\\n")
step = scenario[min(n, len(scenario) - 1)]
if "sleep" in step:
    time.sleep(step["sleep"])
if "exit" in step:
    sys.stderr.write(step.get("stderr", "boom"))
    sys.exit(step["exit"])
sys.stdout.write(step["stdout"])
'''


def envelope(card) -> str:
    return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "",
                       "structured_output": card})


class Stub:
    """A fake `claude` executable. scenario: list of steps {stdout}|{sleep}|{exit}; the last repeats."""

    def __init__(self, tmp_path: Path, scenario):
        self.dir = tmp_path / "stub"
        self.dir.mkdir()
        self.bin = self.dir / "claude"
        self.bin.write_text(STUB_SOURCE.format(py=sys.executable))
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR)
        (self.dir / "scenario.json").write_text(json.dumps(scenario))
        self.env = dict(os.environ, STUB_DIR=str(self.dir))

    @property
    def calls(self) -> list[dict]:
        p = self.dir / "calls.jsonl"
        if not p.exists():
            return []
        return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]

    def planner(self, **kw):
        from backend.providers.claude_cli import ClaudeCliPlanner
        kw.setdefault("enabled", True)
        return ClaudeCliPlanner(command=str(self.bin), env=self.env, **kw)


class Api:
    """httpx.MockTransport recording requests. responses: list of callables/values; the last repeats."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []
        self.transport = httpx.MockTransport(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        i = min(len(self.requests), len(self.responses) - 1)
        self.requests.append(request)
        r = self.responses[i]
        if isinstance(r, Exception):
            raise r
        if callable(r):
            return r(request)
        return r

    def planner(self, key="sk-ant-TESTKEY-123456", **kw):
        kw.setdefault("enabled", True)
        env = {"ANTHROPIC_API_KEY": key} if key is not None else {}
        return anthropic_api.AnthropicApiPlanner(env=env, transport=self.transport, **kw)

    def body(self, i=0) -> dict:
        return json.loads(self.requests[i].content)


def tool_response(card, tool_name="submit_brief_card") -> httpx.Response:
    return httpx.Response(200, json={
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5",
        "content": [{"type": "tool_use", "id": "toolu_1", "name": tool_name, "input": card}],
        "stop_reason": "tool_use"})


def text_response(text) -> httpx.Response:
    return httpx.Response(200, json={"id": "msg_1", "type": "message", "role": "assistant",
                                     "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"})
