"""Genre presets (app/genres/presets.json): load, validate, look up, match keywords.

A preset is a starting point for the song pipeline: genre words for the caption, typical tempo and meter, a lead and
supporting instruments, vocal and production descriptions, a song form and lyric conventions. The planner copies what
it needs into the plan; the user can override every value.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

from . import instruments as inst_db
from . import song_blueprint

PRESETS_PATH = Path(__file__).resolve().parents[1] / "genres" / "presets.json"
METERS = tuple(song_blueprint.METER_BEATS)
VOICES = ("instrumental", "wordless", "sung")
SINGERS = ("auto", "male", "female", "duet")
CLASSIC_RECIPES = ("r1_flute_focus", "r2_warm_ensemble", "r3_hindi_ballad", "r4_fusion")
_ARTIST_GUARD = re.compile(r"\b(?:in the style of|sounds like|like [A-Z][a-z]+ [A-Z][a-z]+)\b")


class PresetError(ValueError):
    pass


def _check(p: dict) -> list[str]:
    errs = []
    pid = p.get("id", "?")
    for key in ("id", "name", "family", "blurb", "languages", "voice", "singer", "genre_tags", "moods", "bpm",
                "bpm_default", "meter", "key", "lead", "supports", "production", "form", "hints", "keywords"):
        if key not in p:
            errs.append(f"{pid}: missing '{key}'")
    if errs:
        return errs
    if not re.fullmatch(r"[a-z0-9_]{3,40}", pid):
        errs.append(f"{pid}: id must be lowercase letters, digits, underscore")
    if p["voice"] not in VOICES:
        errs.append(f"{pid}: voice '{p['voice']}'")
    if p["singer"] not in SINGERS:
        errs.append(f"{pid}: singer '{p['singer']}'")
    lo, hi = p["bpm"]
    if not (60 <= lo <= p["bpm_default"] <= hi <= 140):
        errs.append(f"{pid}: bpm_default {p['bpm_default']} outside {lo}-{hi} or outside 60-140")
    if p["meter"] not in METERS:
        errs.append(f"{pid}: meter '{p['meter']}'")
    if not re.fullmatch(r"[A-G][#b]? (major|minor)", p["key"]):
        errs.append(f"{pid}: key '{p['key']}'")
    for field in ("supports", "color"):
        for i in p.get(field, []):
            if i not in inst_db.INSTRUMENTS:
                errs.append(f"{pid}: unknown instrument '{i}' in {field}")
    if p["lead"] not in inst_db.INSTRUMENTS:
        errs.append(f"{pid}: unknown lead '{p['lead']}'")
    elif p["lead"] in p["supports"]:
        errs.append(f"{pid}: lead '{p['lead']}' is also a support")
    if p["form"] not in song_blueprint.FORMS:
        errs.append(f"{pid}: unknown form '{p['form']}'")
    elif p["voice"] == "sung" and p["form"] not in song_blueprint.SUNG_FORMS:
        errs.append(f"{pid}: sung preset with a non-sung form")
    if p.get("recipe") and p["recipe"] not in CLASSIC_RECIPES:
        errs.append(f"{pid}: unknown recipe '{p['recipe']}'")
    if len(p["genre_tags"]) > 90:
        errs.append(f"{pid}: genre_tags longer than 90 characters")
    if _ARTIST_GUARD.search(json.dumps(p)):
        errs.append(f"{pid}: presets describe a sound; they never name an artist")
    return errs


@lru_cache(maxsize=1)
def _load() -> tuple[dict, ...]:
    data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    presets = data["presets"]
    errs = [e for p in presets for e in _check(p)]
    ids = [p["id"] for p in presets]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errs.append(f"duplicate ids: {sorted(dupes)}")
    if errs:
        raise PresetError("; ".join(errs))
    return tuple(presets)


def presets() -> list[dict]:
    return [dict(p) for p in _load()]


def ids() -> tuple[str, ...]:
    return tuple(p["id"] for p in _load())


def exists(preset_id: Optional[str]) -> bool:
    return bool(preset_id) and preset_id in ids()


def get(preset_id: str) -> dict:
    for p in _load():
        if p["id"] == preset_id:
            return dict(p)
    raise KeyError(preset_id)


def for_recipe(recipe_id: Optional[str]) -> Optional[str]:
    """The preset that carries a classic recipe forward (r3_hindi_ballad -> hindi_acoustic_ballad)."""
    for p in _load():
        if recipe_id and p.get("recipe") == recipe_id:
            return p["id"]
    return None


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).lower()


# Umbrella words name a whole family of styles; a more specific word in the same brief wins over them
# ("a bollywood sufi qawwali" is a qawwali).
GENERIC_KEYWORDS = {"bollywood", "pop", "folk", "rock", "indie", "acoustic", "dance", "ballad", "fusion", "cinematic",
                    "chill", "edm", "rap", "hip hop", "hip-hop", "devotional", "epic", "classical", "film song",
                    "movie song", "party song", "soundtrack", "score", "trailer", "orchestral", "atmospheric",
                    "hindi song", "hindi gaana", "हिंदी गाना", "romantic hindi song", "hindi love song"}


def match(text: str, language: Optional[str] = None) -> list[tuple[str, str]]:
    """Presets whose keywords appear in the text: [(preset_id, matched keyword)], best first.

    Ranking: a specific keyword beats an umbrella word; then, for sung music, a style in the song's language beats
    one in another language ("a Hindi romantic acoustic ballad" is not an English acoustic-pop song); then the
    longer keyword wins, then the one written later (the head noun of "hindi rock ballad" comes last)."""
    t = _norm(text)
    if language is None and re.search(r"\bhindi\b|हिंदी|हिन्दी|[\u0900-\u097F]", t):
        language = "hi"
    hits: list[tuple[int, int, int, int, int, str, str]] = []
    for order, p in enumerate(_load()):
        best = None                       # (generic, -len, -pos, keyword)
        for kw in p["keywords"]:
            k = _norm(kw)
            if re.search(r"[ऀ-ॿ]", k):
                pos = t.find(k)
            else:
                m = re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", t)
                pos = m.start() if m else -1
            if pos < 0:
                continue
            cand = (int(k in GENERIC_KEYWORDS), -len(k), -pos, kw)
            if best is None or cand < best:
                best = cand
        if best:
            other_lang = int(bool(language) and p["voice"] == "sung" and language not in p["languages"])
            hits.append((best[0], other_lang, best[1], best[2], order, p["id"], best[3]))
    hits.sort()
    return [(pid, kw) for *_, pid, kw in hits]


def pick(text: str, *, language: Optional[str] = None, voice: Optional[str] = None) -> Optional[tuple[str, str]]:
    """The best preset for a brief, or None. With a voice the person chose, an umbrella word ("acoustic", "ballad")
    never puts a wordless or instrumental piece into a sung style (a specific word like "qawwali" still does: an
    instrumental qawwali is a real request)."""
    for pid, kw in match(text, language):
        if voice and get(pid)["voice"] != voice and kw.lower() in GENERIC_KEYWORDS:
            continue
        return pid, kw
    return None


def summary_for_llm() -> str:
    """One line per preset for the smart planner's system prompt."""
    return "\n".join(f"- {p['id']}: {p['name']} ({p['voice']}, {'/'.join(p['languages'])}) - {p['blurb']}"
                     for p in _load())
