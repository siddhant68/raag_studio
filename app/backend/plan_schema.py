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

from . import instruments

SCHEMA_VERSION = "2.0"

# The classic instrument list (PRD 5.4; harmonium is aliased and unvalidated). The classic compiler and the
# accepted recipes know only these. The song pipeline accepts the wider vocabulary in backend/instruments.py.
CLASSIC_INSTRUMENT_IDS = instruments.CLASSIC_IDS
INSTRUMENT_IDS = instruments.INSTRUMENT_IDS
InstrumentId = Literal[instruments.INSTRUMENT_IDS]
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
Pipeline = Literal["classic", "song"]          # classic = the original template compiler; song = blueprint compiler
Meter = Literal["4/4", "3/4", "6/8", "2/4"]
# Fields added with the song pipeline. A plan that leaves them at these defaults fingerprints exactly as before.
SONG_FIELD_DEFAULTS = {"genre": None, "pipeline": "classic", "meter": "4/4", "form": None, "require_sections": []}
SectionKind = Literal["intro", "verse", "pre_chorus", "chorus", "bridge", "solo", "interlude", "break", "build",
                      "drop", "outro"]

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
    genre: Optional[str] = Field(default=None, pattern=r"^[a-z0-9_]{3,40}$")
    pipeline: Pipeline = "classic"
    meter: Meter = "4/4"
    form: Optional[str] = Field(default=None, pattern=r"^[a-z_]{3,30}$")
    require_sections: list[SectionKind] = Field(default_factory=list, max_length=6)   # never dropped to fit the length
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
        if self.pipeline == "classic":
            extra = [i for i in [self.lead.instrument] + names if i not in CLASSIC_INSTRUMENT_IDS]
            if extra:
                raise ValueError(f"instruments {extra} need the song pipeline (pipeline 'song')")
        if self.genre is not None:
            from . import genres
            if not genres.exists(self.genre):
                raise ValueError(f"unknown genre preset '{self.genre}'")
        if self.form is not None:
            from . import song_blueprint
            if self.form not in song_blueprint.FORMS:
                raise ValueError(f"unknown song form '{self.form}'")
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
        data = self.model_dump(mode="json")
        for key, default in SONG_FIELD_DEFAULTS.items():        # classic plans keep their original fingerprint
            if data.get(key) == default:
                data.pop(key, None)
        blob = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
