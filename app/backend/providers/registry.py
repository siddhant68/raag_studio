"""Planner registry: pick the provider from settings and wrap smart providers in an automatic Basic fallback.

    from backend.providers.registry import get_planner
    planner = get_planner(settings)                  # BasicPlanner, or FallbackPlanner(smart, Basic)
    out = planner.plan_with_status(brief, controls)  # PlanOutcome: card + fallback + fallback_reason + banner
    card = out.card

Settings shape (all keys optional; anything missing means "Basic planner"):

    {"planner": {
        "provider": "basic" | "claude_cli" | "anthropic_api",
        "smart_enabled": false,                       # explicit master toggle; must be true for a smart provider
        "claude_cli":    {"command": "claude", "model": null, "timeout_s": 60, "bare": false},
        "anthropic_api": {"model": "claude-sonnet-5-5", "timeout_s": 60}}}

A plain string `settings["planner"] = "claude_cli"` or flat keys `planner_provider` / `planner_smart_enabled`
are also read. No API key is ever read from settings: the Anthropic key comes only from the environment.
With the toggle off (or provider "basic") the returned planner is a plain BasicPlanner: no subprocess and no
network call is possible.
"""
from __future__ import annotations

import logging
import shutil
from typing import Any, Mapping, Optional

import httpx
from pydantic import BaseModel

from ..planner_base import (BriefCard, Controls, LyricsDraft, PlanPatch, Planner, PlannerError, UnsupportedByPlanner)
from ..planner_rules import BasicPlanner
from ..plan_schema import Plan
from . import PROVIDER_ANTHROPIC_API, PROVIDER_CLAUDE_CLI
from .anthropic_api import DEFAULT_MODEL, KEY_ENV, AnthropicApiPlanner
from .claude_cli import ClaudeCliPlanner

log = logging.getLogger("raag.planner")

PROVIDER_BASIC = "basic"
PROVIDER_IDS = (PROVIDER_BASIC, PROVIDER_CLAUDE_CLI, PROVIDER_ANTHROPIC_API)
# Badges always name the real provider. Nothing in the Basic strings claims to be an AI.
PROVIDER_LABELS = {PROVIDER_BASIC: "Basic planner", PROVIDER_CLAUDE_CLI: "Claude (local CLI)",
                   PROVIDER_ANTHROPIC_API: "Claude (API)"}
PROVIDER_DESCRIPTIONS = {
    PROVIDER_BASIC: "Keyword rules on this computer. Nothing is sent anywhere.",
    PROVIDER_CLAUDE_CLI: "Claude through the local claude command. Your brief and settings go to Anthropic.",
    PROVIDER_ANTHROPIC_API: "Claude through the Anthropic API (key from the environment). Your brief and settings go to Anthropic.",
}
LYRICS_OFF_MESSAGE = ("Writing lyrics for you needs a smart planner, which is off. Paste your own words "
                      "(\"Use my words exactly\"), or choose Instrumental or Wordless voices.")


def badge_for(provider_id: str) -> str:
    return PROVIDER_LABELS.get(provider_id, PROVIDER_LABELS[PROVIDER_BASIC])


# ---------------------------------------------------------------------------------------------
# Settings parsing
# ---------------------------------------------------------------------------------------------
def _planner_settings(settings: Optional[Mapping[str, Any]]) -> dict:
    s = settings or {}
    p = s.get("planner")
    if isinstance(p, str):
        out: dict = {"provider": p}
    elif isinstance(p, Mapping):
        out = dict(p)
    else:
        out = {}
    out.setdefault("provider", s.get("planner_provider", PROVIDER_BASIC))
    out.setdefault("smart_enabled", s.get("planner_smart_enabled", False))
    return out


def selected_provider(settings: Optional[Mapping[str, Any]]) -> str:
    """The provider that will actually run: a smart one only with an explicit `smart_enabled: true`."""
    p = _planner_settings(settings)
    prov = p.get("provider")
    if prov in (PROVIDER_CLAUDE_CLI, PROVIDER_ANTHROPIC_API) and p.get("smart_enabled") is True:
        return prov
    return PROVIDER_BASIC


def _timeout(cfg: Mapping[str, Any]) -> float:
    try:
        t = float(cfg.get("timeout_s", 60))
    except (TypeError, ValueError):
        return 60.0
    return min(max(t, 1.0), 60.0)       # 60 s is the cap in the PRD


# ---------------------------------------------------------------------------------------------
# Outcomes (the Planner interface keeps returning BriefCard / PlanPatch; these add the fallback facts)
# ---------------------------------------------------------------------------------------------
class PlanOutcome(BaseModel):
    card: BriefCard
    fallback: bool = False
    fallback_reason: Optional[str] = None
    fallback_code: Optional[str] = None
    banner: Optional[str] = None
    requested_provider: str = PROVIDER_BASIC
    requested_label: str = PROVIDER_LABELS[PROVIDER_BASIC]
    used_provider: str = PROVIDER_BASIC
    used_label: str = PROVIDER_LABELS[PROVIDER_BASIC]

    def to_response(self) -> dict:
        """JSON for the API: the card plus {"fallback": bool, "fallback_reason": ..., "banner": ...}."""
        return {"card": self.card.model_dump(mode="json"), "fallback": self.fallback,
                "fallback_reason": self.fallback_reason, "fallback_code": self.fallback_code,
                "banner": self.banner, "provider": self.used_provider, "provider_label": self.used_label,
                "requested_provider": self.requested_provider, "requested_label": self.requested_label}


class PatchOutcome(BaseModel):
    patch: PlanPatch
    fallback: bool = False
    fallback_reason: Optional[str] = None
    fallback_code: Optional[str] = None
    banner: Optional[str] = None
    requested_provider: str = PROVIDER_BASIC
    requested_label: str = PROVIDER_LABELS[PROVIDER_BASIC]
    used_provider: str = PROVIDER_BASIC
    used_label: str = PROVIDER_LABELS[PROVIDER_BASIC]

    def to_response(self) -> dict:
        return {"patch": self.patch.model_dump(mode="json"), "fallback": self.fallback,
                "fallback_reason": self.fallback_reason, "fallback_code": self.fallback_code,
                "banner": self.banner, "provider": self.used_provider, "provider_label": self.used_label,
                "requested_provider": self.requested_provider, "requested_label": self.requested_label}


def fallback_banner(requested_label: str, code: str) -> str:
    why = {"planner_timeout": "did not answer in time",
           "planner_invalid_output": "returned an answer I could not use",
           "planner_unavailable": "is not available",
           "planner_disabled": "is turned off",
           "planner_binary_missing": "is not installed",
           "planner_key_missing": "has no key configured",
           "planner_cli_failed": "failed to run",
           "planner_http_error": "returned an error",
           "planner_network_error": "could not be reached"}.get(code, "did not work")
    return (f"{requested_label} {why}, so this plan came from the {PROVIDER_LABELS[PROVIDER_BASIC]} "
            "(keyword rules). You can try again or keep going.")


class FallbackPlanner(Planner):
    """Runs the smart provider; on any typed failure returns the Basic planner's result and says so."""

    def __init__(self, primary: Planner, fallback: Optional[Planner] = None):
        self.primary = primary
        self.fallback_planner = fallback or BasicPlanner()
        self.name = primary.name
        self.label = primary.label
        self.is_llm = primary.is_llm
        self.can_write_lyrics = primary.can_write_lyrics

    # ---- helpers ---------------------------------------------------------------------------
    def _fail_info(self, e: Exception) -> tuple[str, str, str]:
        if isinstance(e, PlannerError):
            code, msg = e.code, e.message
        else:                                       # last-resort net: a provider bug must not break planning
            code, msg = "planner_error", f"{type(e).__name__} in {self.label}"
        log.warning("planner fallback: provider=%s code=%s", self.name, code)
        return code, msg, fallback_banner(self.label, code)

    # ---- status-carrying API (use this from the HTTP layer) ----------------------------------
    def plan_with_status(self, brief: str, controls: Optional[Controls] = None,
                         context: Optional[dict] = None) -> PlanOutcome:
        if not brief or not brief.strip():
            raise ValueError("brief must not be blank")
        try:
            card = self.primary.plan(brief, controls, context)
            return PlanOutcome(card=card, requested_provider=self.name, requested_label=self.label,
                               used_provider=card.provider, used_label=card.provider_label)
        except Exception as e:                      # noqa: BLE001 - see _fail_info
            code, msg, banner = self._fail_info(e)
        card = self.fallback_planner.plan(brief, controls, context)
        card = card.model_copy(update={"notes": [banner] + list(card.notes)})
        return PlanOutcome(card=card, fallback=True, fallback_reason=msg, fallback_code=code, banner=banner,
                           requested_provider=self.name, requested_label=self.label,
                           used_provider=card.provider, used_label=card.provider_label)

    def patch_with_status(self, plan: Plan, request_text: str) -> PatchOutcome:
        try:
            patch = self.primary.patch(plan, request_text)
            return PatchOutcome(patch=patch, requested_provider=self.name, requested_label=self.label,
                                used_provider=patch.provider,
                                used_label=PROVIDER_LABELS.get(patch.provider, self.label))
        except Exception as e:                      # noqa: BLE001
            code, msg, banner = self._fail_info(e)
        patch = self.fallback_planner.patch(plan, request_text)
        patch = patch.model_copy(update={"unsupported": [{"kind": "planner_fallback", "message": banner}]
                                         + list(patch.unsupported)})
        return PatchOutcome(patch=patch, fallback=True, fallback_reason=msg, fallback_code=code, banner=banner,
                            requested_provider=self.name, requested_label=self.label,
                            used_provider=patch.provider, used_label=PROVIDER_LABELS[PROVIDER_BASIC])

    # ---- Planner interface (same return types as the providers) ------------------------------
    def plan(self, brief: str, controls: Optional[Controls] = None, context: Optional[dict] = None) -> BriefCard:
        return self.plan_with_status(brief, controls, context).card

    def patch(self, plan: Plan, request_text: str) -> PlanPatch:
        return self.patch_with_status(plan, request_text).patch

    def draft_lyrics(self, plan: Plan) -> LyricsDraft:
        """Smart provider only; no silent substitute. Typed errors reach the caller (Basic cannot write lyrics)."""
        return self.primary.draft_lyrics(plan)

    def draft_song_lyrics(self, plan: Plan, blueprint, **kw):
        """Song-pipeline lyrics come only from the smart provider (no silent fallback to anything else)."""
        return self.primary.draft_song_lyrics(plan, blueprint, **kw)


# ---------------------------------------------------------------------------------------------
# Factory and status
# ---------------------------------------------------------------------------------------------
def get_planner(settings: Optional[Mapping[str, Any]] = None, *, env: Optional[Mapping[str, str]] = None,
                http_transport: Optional[httpx.BaseTransport] = None) -> Planner:
    """BasicPlanner unless settings explicitly enable a smart provider, then FallbackPlanner(smart, Basic).

    `env` and `http_transport` exist for tests (stub environment, httpx.MockTransport).
    """
    prov = selected_provider(settings)
    if prov == PROVIDER_BASIC:
        return BasicPlanner()
    cfg = _planner_settings(settings).get(prov)
    cfg = cfg if isinstance(cfg, Mapping) else {}
    if prov == PROVIDER_CLAUDE_CLI:
        smart: Planner = ClaudeCliPlanner(enabled=True, command=str(cfg.get("command") or "claude"),
                                          model=cfg.get("model") or None, timeout_s=_timeout(cfg),
                                          bare=bool(cfg.get("bare", False)), env=env)
    else:
        smart = AnthropicApiPlanner(enabled=True, model=str(cfg.get("model") or DEFAULT_MODEL),
                                    timeout_s=_timeout(cfg), env=env, transport=http_transport)
    return FallbackPlanner(smart, BasicPlanner())


def provider_status(settings: Optional[Mapping[str, Any]] = None, *,
                    env: Optional[Mapping[str, str]] = None) -> list[dict]:
    """For the Settings screen. No subprocess, no network. Reports presence of the key, never its value."""
    import os
    environ = env if env is not None else os.environ
    p = _planner_settings(settings)
    active = selected_provider(settings)
    cli_cfg = p.get(PROVIDER_CLAUDE_CLI) if isinstance(p.get(PROVIDER_CLAUDE_CLI), Mapping) else {}
    cli_cmd = str((cli_cfg or {}).get("command") or "claude")
    cli_found = (shutil.which(cli_cmd, path=environ.get("PATH")) is not None)
    key_set = bool(str(environ.get(KEY_ENV, "")).strip())
    rows = []
    for pid in PROVIDER_IDS:
        row = {"id": pid, "label": PROVIDER_LABELS[pid], "description": PROVIDER_DESCRIPTIONS[pid],
               "is_llm": pid != PROVIDER_BASIC, "sends_data_to_anthropic": pid != PROVIDER_BASIC,
               "active": pid == active, "can_write_lyrics": pid != PROVIDER_BASIC}
        if pid == PROVIDER_BASIC:
            row["available"], row["requires"] = True, None
        elif pid == PROVIDER_CLAUDE_CLI:
            row["available"], row["requires"] = cli_found, "the 'claude' command on PATH"
        else:
            row["available"], row["requires"] = key_set, f"{KEY_ENV} in the environment"
        rows.append(row)
    return rows


def lyrics_status(planner: Planner) -> dict:
    """AT-M4-06: 'Write for me' is disabled, with an explanation, unless a smart provider is active."""
    if getattr(planner, "can_write_lyrics", False):
        return {"enabled": True, "reason": None}
    return {"enabled": False, "reason": LYRICS_OFF_MESSAGE}


__all__ = ["get_planner", "selected_provider", "provider_status", "lyrics_status", "badge_for", "FallbackPlanner",
           "PlanOutcome", "PatchOutcome", "PROVIDER_LABELS", "PROVIDER_IDS", "UnsupportedByPlanner"]
