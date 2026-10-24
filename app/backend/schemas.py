"""Request bodies and the API error type."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ApiError(Exception):
    """Raised anywhere; main.py turns it into {"error": {code, message, ...}} with `status`."""

    def __init__(self, status: int, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSongBody(_Body):
    brief: str
    title: Optional[str] = Field(default=None, max_length=120)
    voice: Optional[str] = None                   # instrumental | wordless | sung | auto
    duration: Optional[int] = None                # seconds (C3); alias duration_s
    duration_s: Optional[int] = None
    takes: Optional[int] = Field(default=None, ge=1, le=4)
    recipe: Optional[str] = None                  # alias recipe_id
    recipe_id: Optional[str] = None
    lyrics: Optional[str] = None                  # "Use my words exactly" (alias lyrics_text)
    lyrics_text: Optional[str] = None
    shape: Optional[dict[str, Any]] = None        # C6-C15 controls: lead, instruments, feeling, pace, ...
    controls: Optional[dict[str, Any]] = None     # same keys as Controls, alternative spelling
    plan: Optional[dict[str, Any]] = None         # supply a full plan instead of running the planner
    idempotency_key: Optional[str] = Field(default=None, max_length=200)

    @field_validator("brief")
    @classmethod
    def _brief(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("brief must not be blank")
        if len(v) > 4000:
            raise ValueError("brief is longer than 4000 characters")
        return v


class PlanOnlyBody(_Body):
    """POST /api/songs/{id}/plan: same optional controls; nothing is rendered."""
    brief: Optional[str] = None
    voice: Optional[str] = None
    duration: Optional[int] = None
    duration_s: Optional[int] = None
    takes: Optional[int] = Field(default=None, ge=1, le=4)
    recipe: Optional[str] = None
    recipe_id: Optional[str] = None
    lyrics: Optional[str] = None
    lyrics_text: Optional[str] = None
    shape: Optional[dict[str, Any]] = None
    controls: Optional[dict[str, Any]] = None


class RoundBody(_Body):
    kind: Literal["another", "refine", "variation", "cover", "repaint"]
    from_take: Optional[str] = None
    from_round: Optional[str] = None              # retry: reuse THAT round's plan (kind "another" only)
    request_text: Optional[str] = None
    chips: Optional[list[str]] = None
    patch: Optional[Any] = None                   # chip text or list of chip ids (alias of request_text/chips)
    takes: Optional[int] = Field(default=None, ge=1, le=4)
    idempotency_key: Optional[str] = Field(default=None, max_length=200)


class FeedbackBody(_Body):
    favourite: Optional[bool] = None
    rating: Optional[Literal["love", "fine", "no"]] = None
    tags: Optional[list[str]] = None
    note: Optional[str] = Field(default=None, max_length=2000)


class ExportBody(_Body):
    format: Literal["mp3", "wav"]
    end_fade_s: float = Field(default=0.0, ge=0.0, le=8.0)
    trim_end_s: float = Field(default=0.0, ge=0.0)


class PruneBody(_Body):
    older_than_days: int = Field(ge=0, le=3650)
    confirm: bool = False
