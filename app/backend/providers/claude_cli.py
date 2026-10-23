"""Smart planner via the local `claude -p` CLI (PRD v2 section 8, provider 2). OFF unless enabled in Settings.

Invocation (flags checked against `claude --help`, v2.1.x):

    claude -p --output-format json --json-schema <BriefCard schema> --tools "" \
           --disallowedTools <all built-in tools> --permission-mode dontAsk --no-session-persistence \
           --disable-slash-commands --strict-mcp-config --system-prompt <rules> [--model M] [--bare]

  * the prompt goes in on stdin (never in argv: variadic flags would swallow it, and argv is visible to `ps`);
  * cwd is a fresh EMPTY temporary directory, removed afterwards, so no CLAUDE.md or project is picked up;
  * 60 s timeout (process group is killed), exactly one retry on invalid JSON, then PlannerInvalidOutput;
  * `--bare` is OFF by default: with --bare the CLI never reads the subscription login (OAuth/keychain), only
    ANTHROPIC_API_KEY. Turn `bare` on only if you want API-key auth for this provider;
  * unless `bare`, ANTHROPIC_API_KEY is removed from the child's environment so the subscription login is used;
  * with the provider disabled no subprocess is spawned (checked before anything else).

Only the brief (copyright-stripped) and the control state are sent. Exact lyrics are never sent.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
from typing import Any, Mapping, Optional

from ..planner_base import PlannerInvalidOutput, PlannerTimeout, PlannerUnavailable
from . import DEFAULT_TIMEOUT_S, PROVIDER_CLAUDE_CLI, LlmPlanner, extract_json

# Every built-in tool name we know of; `--tools ""` already disables all of them, this is belt and braces
# and what the tests assert on.
DISALLOWED_TOOLS = (
    "Bash", "Edit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "NotebookEdit", "Task", "Agent",
    "TodoWrite", "MultiEdit", "PowerShell",
)
LABEL = "Claude (local CLI)"


class ClaudeCliPlanner(LlmPlanner):
    name = PROVIDER_CLAUDE_CLI
    label = LABEL

    def __init__(self, *, enabled: bool = False, command: str = "claude", model: Optional[str] = None,
                 timeout_s: float = DEFAULT_TIMEOUT_S, bare: bool = False,
                 env: Optional[Mapping[str, str]] = None, extra_args: Optional[list[str]] = None):
        super().__init__(enabled=enabled, timeout_s=timeout_s)
        self.command = command
        self.model = model
        self.bare = bare
        self._env = env                     # None -> os.environ at call time
        self.extra_args = list(extra_args or [])

    # ---- availability (no subprocess) ------------------------------------------------------
    def resolved_command(self) -> Optional[str]:
        if os.sep in self.command:
            return self.command if os.access(self.command, os.X_OK) else None
        return shutil.which(self.command, path=(self._env or os.environ).get("PATH"))

    def _check_ready(self) -> None:
        if self.resolved_command() is None:
            raise PlannerUnavailable(f"The 'claude' command was not found ({self.command}).",
                                     code="planner_binary_missing")

    # ---- argv ------------------------------------------------------------------------------
    def build_argv(self, system: str, schema: dict) -> list[str]:
        argv = [self.resolved_command() or self.command, "-p", "--output-format", "json",
                "--json-schema", json.dumps(schema, separators=(",", ":"), ensure_ascii=False),
                "--tools", "",
                "--disallowedTools", ",".join(DISALLOWED_TOOLS),
                "--permission-mode", "dontAsk",
                "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config",
                "--system-prompt", system]
        if self.model:
            argv += ["--model", self.model]
        if self.bare:
            argv.append("--bare")
        argv += self.extra_args
        return argv

    def _child_env(self) -> dict[str, str]:
        env = dict(self._env if self._env is not None else os.environ)
        if not self.bare:
            env.pop("ANTHROPIC_API_KEY", None)      # use the subscription login, never carry a key needlessly
        return env

    # ---- one round trip --------------------------------------------------------------------
    def _transport(self, system: str, user: str, schema: dict, tool_name: str) -> Any:
        with tempfile.TemporaryDirectory(prefix="raag-claude-") as cwd:       # empty by construction
            argv = self.build_argv(system, schema)
            try:
                proc = subprocess.Popen(argv, cwd=cwd, env=self._child_env(), stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                        encoding="utf-8", start_new_session=True)
            except (FileNotFoundError, PermissionError) as e:
                raise PlannerUnavailable(f"Could not start the 'claude' command ({type(e).__name__}).",
                                         code="planner_binary_missing") from e
            try:
                out, err = proc.communicate(user, timeout=self.timeout_s)
            except subprocess.TimeoutExpired as e:
                _kill_group(proc)
                try:
                    proc.communicate(timeout=5)
                except Exception:       # noqa: BLE001 - nothing more to do for a dead process
                    pass
                raise PlannerTimeout(f"{LABEL} did not answer within {self.timeout_s:g} s.") from e
            if proc.returncode != 0:
                raise PlannerUnavailable(f"{LABEL} exited with code {proc.returncode}: {_short(err)}",
                                         code="planner_cli_failed")
        return parse_cli_output(out)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def _short(s: str, n: int = 200) -> str:
    return " ".join((s or "").split())[:n] or "no message"


def parse_cli_output(stdout: str) -> Any:
    """`claude -p --output-format json` prints one JSON envelope. With --json-schema the validated object is in
    `structured_output`; older/other builds put JSON text in `result`. Both are accepted."""
    if not stdout or not stdout.strip():
        raise PlannerInvalidOutput("empty answer")
    try:
        env = json.loads(stdout)
    except ValueError:
        return extract_json(stdout)             # plain JSON text without an envelope
    if isinstance(env, list):                   # tolerate an event array: use the last result event
        results = [e for e in env if isinstance(e, dict) and e.get("type") == "result"]
        if not results:
            raise PlannerInvalidOutput("no result in answer")
        env = results[-1]
    if not isinstance(env, dict):
        raise PlannerInvalidOutput("answer is not a JSON object")
    if env.get("is_error"):
        raise PlannerUnavailable(f"{LABEL} reported an error: {_short(str(env.get('result', '')))}",
                                 code="planner_cli_failed")
    so = env.get("structured_output")
    if isinstance(so, dict):
        return so
    res = env.get("result")
    if isinstance(res, dict):
        return res
    if isinstance(res, str):
        return extract_json(res)
    if "type" not in env and "result" not in env:
        return env                              # the object itself
    raise PlannerInvalidOutput("answer has no structured output")
