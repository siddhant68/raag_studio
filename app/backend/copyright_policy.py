"""Copyright policy (PRD critique F14, AT-M1-06).

Rules, in plain words:
- Named songs, artists and "in the voice of X" phrases are stripped from the
  caption and lyric prompts. A note records what was removed ("I used the mood,
  not the song").
- "remix <song>" is unsupported: the text path has no source audio. The request
  is flagged, the name is stripped, and an original piece is offered instead.
- This is name stripping only. It is not copyright clearance (see capabilities.json).
- User-supplied exact lyrics are never touched here (byte preservation wins);
  the compiler only strips names from prompts it builds itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NOTE_MESSAGE = "Removed the name '{name}' from the prompt. I used the mood, not the song."
REMIX_OFFER = ("I can't remix an existing song. I can make an original piece in the "
               "same mood instead.")

_TITLE = (r"[A-Z][\w'\u2019\-]*(?:\s+(?:(?:on|the|of|in|and|a|an|to|for|at|my|your|me|you|with|&)\s+)*"
          r"[A-Z][\w'\u2019\-]*)*")
_TITLE_RE = re.compile(_TITLE)
_QUOTED_RE = re.compile(r"[\"\u201c\u2018'](?P<q>[^\"\u201d\u2019']{2,60})[\"\u201d\u2019']")
_FREE_RE = re.compile(r"[^,.;:!?\n]+?(?=\s+(?:and|but|with|while|for|except|only|though|yet|so|then)\s|[,.;:!?\n]|$)")

# Cues after which a single capitalised name is enough.
_STRONG_CUES = re.compile(
    r"(?i:\b(?:in\s+the\s+(?:voice|style|manner|vein)\s+of|in\s+the\s+voice\s+and\s+style\s+of|"
    r"(?:sung|performed|written|composed|played)\s+by|inspired\s+by|similar\s+to|reminiscent\s+of|"
    r"(?:song|track|tune|music)\s+by|cover\s+of|version\s+of|"
    r"(?:sounds?|sounding|sing(?:ing|s)?|play(?:ing|s)?)\s+(?:exactly\s+)?like|"
    r"make\s+(?:it|this|me\s+something)\s+(?:sound\s+)?like)\s+)")
# Bare "like X" needs a two-word capitalised title or a quoted title.
_BARE_LIKE = re.compile(r"(?i:\blike\s+)")
_VOICE_CUES = re.compile(r"(?i:\b(?:in\s+the\s+voice\s+of|sung\s+by|voice\s+of)\s+)")
_REMIX = re.compile(r"(?i:\b(?:re-?mix(?:ed|ing)?|mash-?up)\b)(?:\s+(?:of|the|this|that|my|a))*\s*")

_GENERIC_STARTS = {"a", "an", "the", "my", "your", "her", "his", "their", "our", "some", "someone",
                   "somebody", "woman", "man", "girl", "boy", "child", "it", "this", "that"}
_GENERIC_REMIX_TARGETS = {"", "song", "songs", "track", "tracks", "music", "tune", "it", "this", "that",
                          "this song", "that song", "the song", "a song", "my song"}
# Capitalised words that are musical or geographic vocabulary, not titles/artists.
_ALLOW = {"raag", "raga", "yaman", "bhairavi", "bhupali", "hindustani", "carnatic", "indian", "hindi",
          "english", "urdu", "punjabi", "bollywood", "classical", "folk", "sufi", "ghazal", "qawwali",
          "jazz", "blues", "yamuna", "ganga", "ganges", "himalayas", "banaras", "varanasi", "kashmir",
          "kerala", "rajasthan", "diwali", "holi", "monday", "tuesday", "wednesday", "thursday", "friday",
          "saturday", "sunday", "d", "g", "a", "b", "c", "e", "f", "major", "minor", "bpm"}


@dataclass
class PolicyResult:
    text: str
    notes: list[dict] = field(default_factory=list)
    unsupported: list[dict] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.notes or self.unsupported)


def _is_allowed(name: str) -> bool:
    words = [w.lower() for w in re.split(r"[\s&]+", name) if w]
    return not words or all(w in _ALLOW or w in {"on", "the", "of", "in", "and", "a", "an"} for w in words)


def _match_name(text: str, pos: int, *, two_words: bool = False, free_ok: bool = False):
    """Return (name, end) for a title at `pos`, or None."""
    q = _QUOTED_RE.match(text, pos)
    if q:
        return q.group("q").strip(), q.end()
    t = _TITLE_RE.match(text, pos)
    if t:
        name = t.group(0).strip()
        n_caps = sum(1 for w in name.split() if w[:1].isupper())
        if (not two_words or n_caps >= 2) and not _is_allowed(name):
            return name, t.end()
        return None
    if free_ok:
        f = _FREE_RE.match(text, pos)
        if f:
            name = f.group(0).strip()
            first = name.split()[0].lower() if name.split() else ""
            if name and first not in _GENERIC_STARTS and len(name.split()) <= 4:
                return name, f.end()
    return None


def _tidy(text: str) -> str:
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])\s*([,.;:!?])", r"\2", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:")
    return re.sub(r"^(?:but|and|with|then)\s+", "", text, flags=re.I)


def sanitize(text: str) -> PolicyResult:
    """Strip named songs/artists from `text`; flag remix requests."""
    if not text:
        return PolicyResult(text=text or "")
    spans: list[tuple[int, int]] = []
    notes: list[dict] = []
    unsupported: list[dict] = []

    def free(start: int) -> bool:
        return all(not (s <= start < e) for s, e in spans)

    for m in _REMIX.finditer(text):
        found = _match_name(text, m.end(), free_ok=True)
        target, end = (found if found else ("", m.end()))
        spans.append((m.start(), end))
        unsupported.append({"kind": "remix", "target": target if target.lower() not in _GENERIC_REMIX_TARGETS else "",
                            "message": REMIX_OFFER, "offer": "original_piece_same_mood"})
        if target and target.lower() not in _GENERIC_REMIX_TARGETS:
            notes.append({"kind": "named_reference", "cue": "remix", "removed": target,
                          "message": NOTE_MESSAGE.format(name=target)})

    for pattern, kwargs, cue in (
        (_VOICE_CUES, {"free_ok": True}, "voice"),
        (_STRONG_CUES, {}, "style"),
        (_BARE_LIKE, {"two_words": True}, "like"),
    ):
        for m in pattern.finditer(text):
            if not free(m.start()):
                continue
            found = _match_name(text, m.end(), **kwargs)
            if not found:
                continue
            name, end = found
            spans.append((m.start(), end))
            notes.append({"kind": "named_reference", "cue": cue, "removed": name,
                          "message": NOTE_MESSAGE.format(name=name)})

    if not spans:
        return PolicyResult(text=text)
    out, last = [], 0
    for s, e in sorted(spans):
        if s < last:
            continue
        out.append(text[last:s])
        last = e
    out.append(text[last:])
    return PolicyResult(text=_tidy("".join(out)), notes=notes, unsupported=unsupported)


def contains_named_reference(text: str) -> bool:
    return sanitize(text).changed
