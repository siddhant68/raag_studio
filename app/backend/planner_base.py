"""Planner interface (PRD v2 section 8): one interface, several providers, one deterministic compiler.

The planner fills a schema-validated card; code builds the caption. Exact lyrics never pass
through a planner. A provider must report what it is (`name`, `label`, `is_llm`) so the UI
never pretends a rule table is an AI.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .plan_schema import Arc, Background, Fullness, InstrumentId, Plan, RecipeId, Singer, Style, VoiceMode

REFINE_NOTICE = ("These are new performances from an updated plan. "
                 "They will not be exact edits of the take you started from.")


class PlannerError(Exception):
    """Base class for typed planner failures (the caller shows `message`, falls back if allowed)."""
    code = "planner_error"

    def __init__(self, message: str, *, code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class PlannerUnavailable(PlannerError):
    code = "planner_unavailable"          # provider off, not configured, binary or key missing


class PlannerTimeout(PlannerError):
    code = "planner_timeout"


class PlannerInvalidOutput(PlannerError):
    code = "planner_invalid_output"       # provider returned something that is not a valid card


class UnsupportedByPlanner(PlannerError):
    code = "unsupported_by_planner"       # e.g. "write lyrics" under the Basic planner


CHANGE_SOURCES = ("chip", "you", "rule")


def change_entry(field: str, old: Any, new: Any, source: str) -> dict[str, Any]:
    """THE 'what changed' entry, produced by every backend path (chips, free-text patch, PATCH /controls):

    {"field": "lead.style", "from": <old value or None>, "to": <new value or None>, "source": "chip|you|rule"}

    `field` is a plan field, dotted for a sub-field (lead, lead.style, supports, pace, voices.background, ...).
    `from`/`to` are plain JSON values (instrument ids and lists of ids, never display names); null means "no value".
    `source`: chip = a quick-change chip, you = an edit or request of the person, rule = recomputed automatically
    (for example a control reset to Auto).
    """
    if source not in CHANGE_SOURCES:
        raise ValueError(f"change source must be one of {CHANGE_SOURCES}")
    return {"field": field, "from": old, "to": new, "source": source}


# plan fields compared by plan_changes(), in display order: (change field, getter)
_DIFF_FIELDS: tuple[tuple[str, Any], ...] = (
    ("voice_mode", lambda d: d["voice_mode"]),
    ("lyrics", lambda d: d["lyrics"]["policy"]),
    ("duration_s", lambda d: d["duration_s"]),
    ("takes", lambda d: d["takes"]),
    ("recipe_id", lambda d: d["recipe_id"]),
    ("lead", lambda d: d["lead"]["instrument"]),
    ("lead.style", lambda d: d["lead"]["style"]),
    ("supports", lambda d: [s["instrument"] for s in d["supports"]]),
    ("feeling", lambda d: d["feeling"]),
    ("pace", lambda d: d["pace"]["bpm"]),
    ("key", lambda d: d["key"]),
    ("fullness", lambda d: d["fullness"]),
    ("arc", lambda d: d["arc"]),
    ("avoid", lambda d: d["avoid"]),
    ("voices.singer", lambda d: d["voices"]["singer"]),
    ("voices.background", lambda d: d["voices"]["background"]),
    ("voices.language", lambda d: d["voices"]["language"]),
)


def plan_changes(old: "Plan", new: "Plan", source_of: Any) -> list[dict[str, Any]]:
    """Field-by-field difference between two plans as standard change entries.

    `source_of(field)` returns the entry's source ('you' or 'rule') for a changed field.
    """
    a, b = old.model_dump(mode="json"), new.model_dump(mode="json")
    out = []
    for field, get in _DIFF_FIELDS:
        before, after = get(a), get(b)
        if before != after:
            out.append(change_entry(field, before, after, source_of(field)))
    return out


class Controls(BaseModel):
    """User-set controls (C2-C17, C22-C23). A field left None means Auto; set fields get provenance 'you'."""
    model_config = ConfigDict(extra="forbid")

    voice: Optional[VoiceMode] = None
    duration_s: Optional[int] = Field(default=None, ge=10, le=240)
    takes: Optional[int] = Field(default=None, ge=1, le=4)
    recipe_id: Optional[RecipeId] = None
    lead: Optional[InstrumentId] = None
    instruments: Optional[list[InstrumentId]] = None      # supports, in rank order
    feeling: Optional[list[str]] = None
    pace: Optional[Literal["slow", "medium", "lively"]] = None
    bpm: Optional[int] = Field(default=None, ge=60, le=140)
    key: Optional[str] = None
    fullness: Optional[Fullness] = None
    arc: Optional[Arc] = None
    style: Optional[Style] = None
    avoid: Optional[list[str]] = None
    singer: Optional[Singer] = None
    background: Optional[Background] = None
    language: Optional[str] = None
    lyrics_text: Optional[str] = None                       # "Use my words exactly"


class BriefCard(BaseModel):
    plan: Plan
    provider: str
    provider_label: str
    is_llm: bool
    fallback: bool = False                                   # True: nothing matched, started from a default recipe
    matched: list[str] = Field(default_factory=list)         # words/phrases of the brief that were understood
    notes: list[str] = Field(default_factory=list)
    unsupported: list[dict[str, Any]] = Field(default_factory=list)
    needs_user_input: list[str] = Field(default_factory=list)


class PlanPatch(BaseModel):
    plan: Plan                                               # the new revision (unchanged plan if nothing applied)
    provider: str
    applied: list[str] = Field(default_factory=list)         # chip ids that changed something
    changes: list[dict[str, Any]] = Field(default_factory=list)
    unsupported: list[dict[str, Any]] = Field(default_factory=list)
    notice: str = REFINE_NOTICE


class LyricsDraft(BaseModel):
    text: str
    provider: str


class Planner(ABC):
    name: str = "abstract"
    label: str = "Planner"
    is_llm: bool = False
    can_write_lyrics: bool = False

    @abstractmethod
    def plan(self, brief: str, controls: Optional[Controls] = None, context: Optional[dict] = None) -> BriefCard:
        """Brief (+ user controls) -> validated card."""

    @abstractmethod
    def patch(self, plan: Plan, request_text: str) -> PlanPatch:
        """Change request or chip id -> new plan revision."""

    @abstractmethod
    def draft_lyrics(self, plan: Plan) -> LyricsDraft:
        """Draft lyrics (smart providers only); never called for policy 'exact'."""
