"""Plan JSON schema (PRD v2 section 7, schema_version 2.0).

Unknown fields are rejected, instrument ids must be in the 15-item allow-list,
a blank brief is rejected. Every field may carry provenance
(you | suggested | recipe | rule) plus a human reason.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "2.0"

# The validated instrument list (PRD 5.4). harmonium is aliased and unvalidated.
INSTRUMENT_IDS = (
    "bansuri", "tabla", "tanpura", "santoor", "sitar", "ghatam", "violin", "cello",
    "strings", "piano", "acoustic_guitar", "bass", "light_percussion", "choir", "harmonium",
)
InstrumentId = Literal[
    "bansuri", "tabla", "tanpura", "santoor", "sitar", "ghatam", "violin", "cello",
    "strings", "piano", "acoustic_guitar", "bass", "light_percussion", "choir", "harmonium",
]
RECIPE_IDS = ("r1_flute_focus", "r2_warm_ensemble", "r3_hindi_ballad", "r4_fusion")
RecipeId = Literal["r1_flute_focus", "r2_warm_ensemble", "r3_hindi_ballad", "r4_fusion"]

VoiceMode = Literal["instrumental", "wordless", "sung"]
Style = Literal["simple", "singing", "ornate"]
Role = Literal["rhythm", "drone", "harmony", "answer", "texture", "lead"]  # "lead" = a second claim to lead; compiler demotes it
Presence = Literal["sparse", "gentle", "full"]
Bucket = Literal["slow", "medium", "lively"]
Arc = Literal["steady", "slow_build", "quiet_middle_bloom"]
Fullness = Literal["spare", "balanced", "full"]
Singer = Literal["auto", "male", "female", "duet"]
Background = Literal["none", "light", "choir", "big"]
LyricsPolicy = Literal["none", "write", "exact"]
ProvenanceSource = Literal["you", "suggested", "recipe", "rule"]

# C8 pace buckets (BPM ranges from PRD section 4)
BUCKET_RANGES = {"slow": (68, 78), "medium": (80, 96), "lively": (100, 116)}
BUCKET_DEFAULT_BPM = {"slow": 74, "medium": 88, "lively": 108}


def bucket_for_bpm(bpm: int) -> str:
    if bpm <= 79:
        return "slow"
    return "medium" if bpm <= 98 else "lively"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Lead(_Strict):
    instrument: InstrumentId
    style: Style = "singing"


class Support(_Strict):
    instrument: InstrumentId
    role: Role = "texture"
    presence: Presence = "gentle"


class Pace(_Strict):
    bucket: Bucket = "medium"
    bpm: int = Field(default=88, ge=60, le=140)


class Voices(_Strict):
    singer: Singer = "auto"
    background: Background = "none"
    language: str = Field(default="en", pattern=r"^[a-z]{2,3}$")


class LyricsSpec(_Strict):
    policy: LyricsPolicy = "none"
    text: Optional[str] = None
    topic: Optional[str] = None


class FieldProvenance(_Strict):
    source: ProvenanceSource
    reason: str = ""


_KEY_RE = re.compile(r"^[A-G][#b]? (major|minor)$")


class Plan(_Strict):
    schema_version: Literal["2.0"] = SCHEMA_VERSION
    brief: str
    recipe_id: Optional[RecipeId] = None
    voice_mode: VoiceMode
    duration_s: int = Field(default=150, ge=10, le=240)
    lead: Lead
    supports: list[Support] = Field(default_factory=list, max_length=14)
    feeling: list[str] = Field(default_factory=list, max_length=8)
    pace: Pace = Field(default_factory=Pace)
    key: str = "D major"
    arc: Arc = "slow_build"
    fullness: Fullness = "balanced"
    voices: Voices = Field(default_factory=Voices)
    lyrics: LyricsSpec = Field(default_factory=LyricsSpec)
    avoid: list[str] = Field(default_factory=list, max_length=10)
    flavour: Optional[str] = Field(default=None, max_length=120)
    notes_for_user: list[str] = Field(default_factory=list, max_length=12)
    takes: int = Field(default=3, ge=1, le=4)
    provenance: dict[str, FieldProvenance] = Field(default_factory=dict)

    @field_validator("brief")
    @classmethod
    def _brief_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("brief must not be blank")
        if len(v) > 4000:
            raise ValueError("brief is longer than 4000 characters")
        return v

    @field_validator("key")
    @classmethod
    def _key_ok(cls, v: str) -> str:
        if not _KEY_RE.match(v):
            raise ValueError("key must look like 'D major' or 'F# minor'")
        return v

    @field_validator("feeling")
    @classmethod
    def _feeling_ok(cls, v: list[str]) -> list[str]:
        out = []
        for w in v:
            w = w.strip()
            if not w or len(w) > 40:
                raise ValueError("feeling words must be 1-40 characters")
            out.append(w)
        return out

    @field_validator("avoid")
    @classmethod
    def _avoid_ok(cls, v: list[str]) -> list[str]:
        out = []
        for w in v:
            w = w.strip()
            if not w or len(w) > 60:
                raise ValueError("avoid terms must be 1-60 characters")
            out.append(w)
        return out

    @model_validator(mode="after")
    def _cross_checks(self) -> "Plan":
        names = [s.instrument for s in self.supports]
        if len(set(names)) != len(names):
            raise ValueError("an instrument may appear only once in supports")
        if self.lyrics.policy == "exact" and not (self.lyrics.text and self.lyrics.text.strip()):
            raise ValueError("lyrics.policy 'exact' needs lyrics.text")
        if self.voice_mode == "sung" and self.lyrics.policy == "none":
            raise ValueError("sung voice_mode needs lyrics.policy 'write' or 'exact'")
        fields = set(type(self).model_fields) - {"provenance"}
        for key in self.provenance:
            if key.split(".")[0] not in fields:
                raise ValueError(f"provenance key '{key}' is not a plan field")
        return self

    # --- helpers -------------------------------------------------------
    def with_provenance(self, field: str, source: str, reason: str = "") -> "Plan":
        prov = dict(self.provenance)
        prov[field] = FieldProvenance(source=source, reason=reason)
        return self.model_copy(update={"provenance": prov})

    def fingerprint(self) -> str:
        blob = json.dumps(self.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
