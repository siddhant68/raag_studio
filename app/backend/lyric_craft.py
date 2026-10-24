"""Lyric craft: count syllables, parse and assemble tagged lyrics, and check drafted lyrics before rendering.

* `syllables(line)` counts Devanagari syllables with Hindi schwa deletion (समझना = 3, दिल = 1, धड़कन = 2) and Latin
  script with a vowel-group heuristic. It is an estimate for line-length checks, not a phonetic transcription.
* `assemble(blueprint, written)` turns the songwriter's unique sections into the full tagged lyric sheet the renderer
  sees. Repeated sections (every chorus after the first) are copied word for word from the first one, so a recurring
  hook is guaranteed by construction rather than hoped for.
* `lint(...)` finds problems a revision pass can fix: wrong line counts, lines too long or short for the tempo, a
  hook missing from the chorus, the wrong script, a Hindi verb that does not agree with the singer's gender,
  verses that copy the chorus, stock filler phrases. It never edits words itself.

Exact lyrics supplied by the user are never passed through `lint` fixes or `assemble`; they are sent as written.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------------------- syllables
_DEV_CONS = set(range(0x0915, 0x093A)) | set(range(0x0958, 0x0960)) | {0x0978, 0x0979, 0x097A, 0x097B, 0x097C,
                                                                        0x097D, 0x097E, 0x097F}
_DEV_INDEP_VOWEL = set(range(0x0904, 0x0915)) | {0x0960, 0x0961, 0x0972, 0x0973, 0x0974, 0x0975, 0x0976, 0x0977}
_DEV_MATRA = set(range(0x093E, 0x094D)) | {0x0962, 0x0963, 0x094E, 0x094F, 0x0955, 0x0956, 0x0957}
_VIRAMA, _NUKTA = 0x094D, 0x093C
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")


def _dev_word_syllables(word: str) -> int:
    """Akshara analysis with right-to-left schwa deletion (Ohala's rule, simplified)."""
    w = unicodedata.normalize("NFD", word)
    cps = [ord(c) for c in w]
    units: list[str] = []          # per akshara: "V" explicit vowel, "A" inherent schwa, "C" no vowel (conjunct)
    coda: list[bool] = []          # akshara closed by an anusvara/visarga (a nasal or h coda)
    i = 0
    while i < len(cps):
        c = cps[i]
        if c in (0x0902, 0x0903) and coda:
            coda[-1] = True
            i += 1
            continue
        if c in _DEV_INDEP_VOWEL:
            units.append("V")
            coda.append(False)
            i += 1
        elif c in _DEV_CONS:
            j = i + 1
            while j < len(cps) and cps[j] == _NUKTA:
                j += 1
            if j < len(cps) and cps[j] == _VIRAMA:
                units.append("C")
                i = j + 1
            elif j < len(cps) and cps[j] in _DEV_MATRA:
                units.append("V")
                i = j + 1
            else:
                units.append("A")
                i = j
            coda.append(False)
        else:
            i += 1                 # anusvara, chandrabindu, visarga, punctuation: no extra syllable
    if not units:
        return 0
    vowel = [u in ("V", "A") for u in units]
    # word-final schwa is silent in a word of more than one akshara
    if units[-1] == "A" and len(units) > 1:
        vowel[-1] = False
    # medial: a schwa between a voiced akshara and a following voiced akshara is dropped (right to left,
    # never two in a row, never the first akshara, never where it would stack three consonants: after a nasal
    # coda as in ज़िंदगी, or before a conjunct)
    k = len(units) - 2
    while k >= 1:
        if (units[k] == "A" and vowel[k] and vowel[k - 1] and vowel[k + 1] and not coda[k - 1]
                and units[k - 1] != "C" and units[k + 1] != "C"):
            vowel[k] = False
            k -= 2
            continue
        k -= 1
    return max(1, sum(vowel))


def _latin_word_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def syllables(line: str) -> int:
    total = 0
    for word in re.findall(r"[\wऀ-ॿ']+", line):
        if _DEVANAGARI.search(word):
            total += _dev_word_syllables(word)
        elif _LATIN.search(word):
            total += _latin_word_syllables(word)
    return total


def script_of(text: str) -> str:
    dev, lat = len(_DEVANAGARI.findall(text)), len(_LATIN.findall(text))
    if dev == 0 and lat == 0:
        return "none"
    return "devanagari" if dev >= lat else "latin"


# --------------------------------------------------------------------------------------- tagged lyrics
_TAG = re.compile(r"^\s*\[([^\[\]\n]{1,60})\]\s*$")


def parse_tagged(text: str) -> list[tuple[str, list[str]]]:
    """[(tag, [lines])] in order; text before the first tag goes under an empty tag."""
    out: list[tuple[str, list[str]]] = []
    cur_tag: str = ""
    cur: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = _TAG.match(raw)
        if m:
            if cur_tag or cur:
                out.append((cur_tag, cur))
            cur_tag, cur = m.group(1).strip(), []
        elif raw.strip():
            cur.append(raw.strip())
    if cur_tag or cur:
        out.append((cur_tag, cur))
    return out


def tag_line(tag: str, hint: str = "") -> str:
    return f"[{tag} - {hint}]" if hint else f"[{tag}]"


WORDLESS_CHORUS = ["Ooh, ooh, aah", "Ooh, aah, ooh", "Aah, aah, ooh", "Ooh, ooh, aah"]
WORDLESS_FINAL = ["Ooh, ooh, aah", "Aah, aah, ooh", "Ooh, aah, ooh", "Ooh, ooh, aah"]


def assemble(sections: list, written: dict[str, list[str]], *, voice_mode: str, with_hints: bool = True) -> str:
    """The full lyric sheet for a blueprint (`sections` are song_blueprint.Section objects or dicts).

    Sung: lyric sections carry the written lines, repeats copy their source verbatim, instrumental sections are a
    bare tag (the accepted Thodi layout). Wordless: vowel lines in vocal sections, [Instrumental] elsewhere (the
    accepted Daylight layout). Instrumental: every section is a tag plus [Instrumental].
    """
    blocks: list[str] = []
    for s in sections:
        sd = s if isinstance(s, dict) else s.__dict__
        tag = tag_line(sd["tag"], sd.get("hint", "") if with_hints else "")
        if voice_mode == "instrumental":
            blocks.append(tag + "\n[Instrumental]")
            continue
        if voice_mode == "wordless":
            if sd["lines"] > 0:
                lines = (WORDLESS_FINAL if sd.get("final") else WORDLESS_CHORUS)[: max(2, sd["lines"])]
                blocks.append("\n".join([tag] + lines))
            else:
                blocks.append(tag + "\n[Instrumental]")
            continue
        key = sd.get("repeat_of") or sd.get("uid")
        lines = written.get(key, []) if key and sd["lines"] > 0 else []
        blocks.append("\n".join([tag] + list(lines)))
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------------------- checks
@dataclass
class Issue:
    code: str
    message: str
    uid: Optional[str] = None
    line: Optional[int] = None
    severity: str = "fix"          # fix = worth a revision pass; note = shown to the user only

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "uid": self.uid, "line": self.line,
                "severity": self.severity}


@dataclass
class LintResult:
    issues: list[Issue] = field(default_factory=list)
    syllables: dict[str, list[int]] = field(default_factory=dict)

    @property
    def needs_revision(self) -> bool:
        return any(i.severity == "fix" for i in self.issues)

    def to_dict(self) -> dict:
        return {"issues": [i.to_dict() for i in self.issues], "syllables": self.syllables,
                "needs_revision": self.needs_revision}


# First-person verb forms that mark the speaker's gender. Only lines containing मैं/main are checked; a hit is a
# reason to ask the songwriter to check the line, not proof of an error (the verb may belong to another subject).
_FEM_VERBS = r"(?:गई|आई|थी|रही|सकी|चुकी|लगी|हुई|बैठी|खोई|डूबी|जागी|रोई|भूली|हारी|चली|सोई|कहती|करती|रहती|जाती|आती|सोचती|देखती)"
_MASC_VERBS = r"(?:गया|आया|था|रहा|सका|चुका|लगा|हुआ|बैठा|खोया|डूबा|जागा|रोया|भूला|हारा|चला|सोया|कहता|करता|रहता|जाता|आता|सोचता|देखता)"
_I_HI = re.compile(r"(?:^|\s)मैं(?:\s|$|ने\b)")

STOCK_FILLER_EN = ("neon", "tapestry", "symphony of", "shattered dreams", "endless night", "electric hearts",
                   "fire in my soul", "dance in the rain", "whispers of the wind", "echoes of", "heart of gold",
                   "set my soul on fire", "into the unknown")


def lint(written: dict[str, list[str]], slots: list[dict], *, language: str, singer: str = "auto",
         syllable_range: tuple[int, int] = (6, 12), hook: Optional[str] = None,
         rap_uids: tuple[str, ...] = ()) -> LintResult:
    """Problems in drafted lyrics. `slots` are blueprint lyric slots ({uid, name, lines})."""
    res = LintResult()
    lo, hi = syllable_range
    want_script = "devanagari" if language in ("hi", "mr", "ne", "sa") else "latin"
    chorus_lines = {ln.strip().lower() for ln in written.get("chorus", [])}
    for slot in slots:
        uid, name, need = slot["uid"], slot["name"], slot["lines"]
        lines = written.get(uid)
        if not lines:
            res.issues.append(Issue("missing_section", f"{name} has no lines; it needs {need}.", uid))
            continue
        if abs(len(lines) - need) > (1 if need >= 4 else 0):
            res.issues.append(Issue("line_count", f"{name} has {len(lines)} lines; write exactly {need}.", uid))
        counts = [syllables(ln) for ln in lines]
        res.syllables[uid] = counts
        s_lo, s_hi = (lo + 2, hi + 4) if uid in rap_uids else (lo, hi)
        for n, (ln, c) in enumerate(zip(lines, counts), 1):
            if c > s_hi + 2:
                res.issues.append(Issue("line_too_long", f"{name} line {n} has about {c} syllables (aim for "
                                                         f"{s_lo}-{s_hi}); it will be hard to sing in one breath.",
                                        uid, n))
            elif c < max(2, s_lo - 3):
                res.issues.append(Issue("line_too_short", f"{name} line {n} has about {c} syllables (aim for "
                                                          f"{s_lo}-{s_hi}).", uid, n, severity="note"))
            if "[" in ln or "]" in ln:
                res.issues.append(Issue("tag_in_line", f"{name} line {n} contains brackets; tags are added by the "
                                                       "app.", uid, n))
            sc = script_of(ln)
            if sc != "none" and sc != want_script:
                res.issues.append(Issue("script", f"{name} line {n} is not in "
                                                  f"{'Devanagari' if want_script == 'devanagari' else 'Latin'} "
                                                  "script.", uid, n))
            if language == "hi" and singer in ("male", "female") and _I_HI.search(f" {ln} "):
                wrong = _FEM_VERBS if singer == "male" else _MASC_VERBS
                m = re.search(wrong, ln)
                if m:
                    res.issues.append(Issue("gender_agreement", f"{name} line {n}: '{m.group(0)}' reads as a "
                                                                f"{'woman' if singer == 'male' else 'man'} speaking, "
                                                                f"but the singer is {singer}. Check the verb form.",
                                            uid, n))
            if language == "en":
                low = ln.lower()
                hit = next((p for p in STOCK_FILLER_EN if p in low), None)
                if hit:
                    res.issues.append(Issue("stock_phrase", f"{name} line {n} uses the stock phrase '{hit}'; use a "
                                                            "concrete image instead.", uid, n))
        if uid.startswith("verse") and chorus_lines:
            copied = [n for n, ln in enumerate(lines, 1) if ln.strip().lower() in chorus_lines]
            if copied:
                res.issues.append(Issue("verse_copies_chorus", f"{name} repeats chorus lines {copied}; verses "
                                                               "should move the story on.", uid))
    if hook and written.get("chorus"):
        joined = " ".join(written["chorus"]).lower()
        if hook.strip().lower() not in joined:
            res.issues.append(Issue("hook_missing", f"The hook '{hook}' does not appear in the chorus.", "chorus"))
    v1, v2 = written.get("verse_1"), written.get("verse_2")
    if v1 and v2 and [x.strip() for x in v1] == [x.strip() for x in v2]:
        res.issues.append(Issue("verses_identical", "Verse 2 repeats verse 1 word for word.", "verse_2"))
    return res
