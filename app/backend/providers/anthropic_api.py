"""Smart planner via the Anthropic Messages API (PRD v2 section 8, provider 3). OFF unless enabled in Settings.

  * httpx POST to {base_url}/v1/messages; the key is read ONLY from the environment variable
    ANTHROPIC_API_KEY at call time, held in a local variable for the request, never logged, never stored on
    the object, never put in an error message, never accepted from settings;
  * structured output through a forced tool call (`tool_choice` -> the card tool); the tool input is the card;
  * 60 s timeout, exactly one retry on an invalid card, then PlannerInvalidOutput (the caller falls back to Basic);
  * with the provider disabled, or the key missing, no network call is made.

Default model id is configurable (settings `planner.anthropic_api.model`).
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import httpx

from ..planner_base import PlannerInvalidOutput, PlannerTimeout, PlannerUnavailable
from . import DEFAULT_TIMEOUT_S, PROVIDER_ANTHROPIC_API, LlmPlanner, extract_json

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"
KEY_ENV = "ANTHROPIC_API_KEY"
MAX_TOKENS = 2000
LABEL = "Claude (API)"


class AnthropicApiPlanner(LlmPlanner):
    name = PROVIDER_ANTHROPIC_API
    label = LABEL

    def __init__(self, *, enabled: bool = False, model: str = DEFAULT_MODEL, timeout_s: float = DEFAULT_TIMEOUT_S,
                 base_url: str = DEFAULT_BASE_URL, env: Optional[Mapping[str, str]] = None,
                 transport: Optional[httpx.BaseTransport] = None):
        super().__init__(enabled=enabled, timeout_s=timeout_s)
        self.model = model or DEFAULT_MODEL
        self.base_url = base_url.rstrip("/")
        self._env = env                     # None -> os.environ at call time (the key is never copied here)
        self._transport_obj = transport     # tests inject httpx.MockTransport

    def _key(self) -> str:
        key = (self._env if self._env is not None else os.environ).get(KEY_ENV, "").strip()
        if not key:
            raise PlannerUnavailable(f"{KEY_ENV} is not set in the environment.", code="planner_key_missing")
        return key

    def key_present(self) -> bool:
        return bool((self._env if self._env is not None else os.environ).get(KEY_ENV, "").strip())

    def _check_ready(self) -> None:
        self._key()

    def build_body(self, system: str, user: str, schema: dict, tool_name: str) -> dict:
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "tools": [{"name": tool_name, "description": "Submit the filled-in JSON object.",
                       "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": tool_name},
        }

    def _transport(self, system: str, user: str, schema: dict, tool_name: str) -> Any:
        key = self._key()
        headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
        body = self.build_body(system, user, schema, tool_name)
        try:
            with httpx.Client(transport=self._transport_obj, timeout=self.timeout_s) as client:
                resp = client.post(f"{self.base_url}/v1/messages", headers=headers, json=body)
        except httpx.TimeoutException as e:
            raise PlannerTimeout(f"{LABEL} did not answer within {self.timeout_s:g} s.") from e
        except httpx.HTTPError as e:
            raise PlannerUnavailable(f"{LABEL} could not be reached ({type(e).__name__}).",
                                     code="planner_network_error") from None
        finally:
            key = ""                        # drop the only reference we held
            headers = {}
        if resp.status_code != 200:
            raise PlannerUnavailable(f"{LABEL} returned HTTP {resp.status_code}{_err_type(resp)}.",
                                     code="planner_http_error")
        try:
            payload = resp.json()
        except ValueError as e:
            raise PlannerInvalidOutput("response is not JSON") from e
        return parse_messages_response(payload, tool_name)


def _err_type(resp: httpx.Response) -> str:
    try:
        t = resp.json().get("error", {}).get("type")
        return f" ({str(t)[:60]})" if t else ""
    except (ValueError, AttributeError):
        return ""


def parse_messages_response(payload: Any, tool_name: str) -> Any:
    """The forced tool call's input; falls back to JSON text if the model answered in text."""
    if not isinstance(payload, dict):
        raise PlannerInvalidOutput("response is not an object")
    blocks = payload.get("content")
    if not isinstance(blocks, list):
        raise PlannerInvalidOutput("response has no content")
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == tool_name:
            inp = b.get("input")
            if isinstance(inp, dict):
                return inp
            raise PlannerInvalidOutput("tool input is not an object")
    for b in blocks:
        if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
            return extract_json(b["text"])
    raise PlannerInvalidOutput("response has no tool call")
