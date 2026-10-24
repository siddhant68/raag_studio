"""Basic planner: deterministic keyword rules. It is NOT an LLM and never pretends to be one.

What it does: alias dictionary (English / Devanagari / Roman Hindi) for the 15 instruments, voice
keywords, duration regex, mood lexicon -> recipe + feeling chips, pace/arc/fullness/style words,
and the section 6 chip patches. What it cannot do: read analogies or stories, write lyrics, or
rewrite free-text change requests. When nothing matches it starts from R1 (or R2 for a joyful or
epic mood) and says which words it did match.
"""
from __future__ import annotations

import copy
import re
import unicodedata
from typing import Any, Optional

from . import compiler, copyright_policy, genres
from . import instruments as inst_db
from .plan_schema import BUCKET_DEFAULT_BPM, CLASSIC_INSTRUMENT_IDS, INSTRUMENT_IDS, Plan, bucket_for_bpm
from .planner_base import (BriefCard, Controls, LyricsDraft, Planner, PlanPatch, UnsupportedByPlanner, change_entry)

# --------------------------------------------------------------------------- vocabulary
INSTRUMENT_ALIASES: dict[str, list[str]] = {
    "bansuri": ["bansuri", "bansri", "basuri", "baansuri", "bansi", "bamboo flute", "flute", "venu", "murli", "murali",
                "बांसुरी", "बाँसुरी", "बासुरी", "बंसी", "मुरली", "फ्लूट", "फ्लूट"],
    "tabla": ["tabla", "tabala", "तबला", "तबले"],
    "tanpura": ["tanpura", "tambura", "tanpuri", "drone", "तानपुरा", "तानपूरा", "तम्बूरा"],
    "santoor": ["santoor", "santur", "संतूर"],
    "sitar": ["sitar", "sitaar", "सितार"],
    "ghatam": ["ghatam", "matka", "घटम"],
    "violin": ["violin", "fiddle", "vayalin", "वायलिन", "वाइलिन"],
    "cello": ["cello", "चेलो", "सेलो"],
    "strings": ["strings", "string section", "orchestra", "orchestral", "स्ट्रिंग्स"],
    "piano": ["piano", "पियानो", "पिआनो"],
    "acoustic_guitar": ["acoustic guitar", "guitar", "gitar", "गिटार"],
    "bass": ["bass", "बेस"],
    "light_percussion": ["drums", "drum", "percussion", "shaker", "ड्रम", "ड्रम्स"],
    "choir": ["choir", "choral", "क्वायर", "कोरस"],
    "harmonium": ["harmonium", "हारमोनियम", "हार्मोनियम"],
}
# The song-pipeline instruments bring their own aliases (backend/instruments.py).
for _inst in inst_db.NEW_IDS:
    INSTRUMENT_ALIASES[_inst] = list(inst_db.get(_inst)["aliases"])
assert set(INSTRUMENT_ALIASES) == set(INSTRUMENT_IDS)

DISPLAY = {"bansuri": "flute", "acoustic_guitar": "guitar", "light_percussion": "drums"}
MELODIC = ["bansuri", "sitar", "santoor", "violin", "cello", "piano", "acoustic_guitar", "harmonium", "strings"] + [
    i for i in inst_db.NEW_IDS if inst_db.can_lead(i) and inst_db.get(i)["family"] in ("melodic", "harmony")]
INDIAN_LEADS = {"bansuri", "sitar", "santoor", "tabla", "ghatam", "tanpura", "harmonium"} | {
    i for i in inst_db.NEW_IDS if inst_db.get(i)["indian"]}
ROLE = {"bansuri": "answer", "tabla": "rhythm", "tanpura": "drone", "santoor": "texture", "sitar": "texture",
        "ghatam": "rhythm", "violin": "answer", "cello": "harmony", "strings": "harmony", "piano": "harmony",
        "acoustic_guitar": "harmony", "bass": "harmony", "light_percussion": "rhythm", "harmonium": "drone",
        "choir": "harmony"}
ROLE.update({i: inst_db.default_role(i) for i in inst_db.NEW_IDS})
assert set(ROLE) == set(INSTRUMENT_IDS)

STRONG_INSTRUMENTAL = [
    r"\binstrumental\b", r"\bno\s+(?:vocals?|voices?|words|lyrics)\b",
    r"\bwithout\s+(?:any\s+)?(?:vocals?|voices?|lyrics|words|singers?)\b", r"\b(?:only|just)\s+instruments?\b",
    "इंस्ट्रुमेंटल", r"बिना\s+(?:वोकल|बोल|आवाज़|आवाज|शब्द)", r"\bbina\s+(?:vocals?|bol|awaaz|awaz|shabd)\b",
]
WEAK_INSTRUMENTAL = [
    r"\bno\s+sing(?:ing|er)\b", r"\bwithout\s+(?:any\s+)?sing(?:ing|er)\b", r"\bnot\s+(?:a\s+)?song\b",
    r"बिना\s+गाने", r"बिना\s+गाना", r"\bbina\s+(?:gaane|gaana|gane|gana)\b", r"\b(?:gaane|gaana)\s+ke\s+bina\b",
]
WORDLESS = [r"\bwordless\b", r"\bhumming\b", r"\booh\b", r"\baah+\b", r"\bvowel", r"\bchoir\b",
            "ऊह", "आह", "हम्मिंग", r"\bbina\s+shabd\s+ke\s+voices\b"]
SUNG = [r"\bsongs?\b", r"\bsing(?:s|ing|er)?\b", r"\bsung\b", r"\bvocals?\b", r"\blyrics?\b", r"\bballad\b",
        r"\bghazal\b", r"\bbhajan\b", r"\b(?:male|female)\s+(?:voice|singer|vocal)", r"\b(?:gaana|gana|gaane|geet)\b",
        "गाना", "गाने", "गीत", "ग़ज़ल", "भजन", "गायक", "गायिका"]

MOODS: dict[str, list[str]] = {
    "peaceful": ["peace*", "calm*", "quiet", "serene", "tranquil", "meditat*", "dawn", "morning", "rain",
                 "gentle", "relax*", "soothing", "lullaby", "शांत", "सुकून", "शांति", "सुबह", "बारिश", "shaant",
                 "shanti", "sukoon", "subah", "baarish", "barish"],
    "tender": ["tender*", "love", "loving", "romantic", "warm", "affection", "lullaby", "pyaar", "pyar", "प्यार",
               "मोहब्बत", "ishq", "इश्क"],
    "yearning": ["miss", "missing", "longing", "yearn*", "nostalgi*", "remember*", "memories", "lonely", "sad",
                 "sadness", "heartbreak", "याद", "इंतज़ार", "इंतजार", "yaad", "yaadein", "intezaar", "judai", "जुदाई",
                 "udaas", "उदास"],
    "joyful": ["joy*", "happy", "happiness", "celebrat*", "dance", "dancing", "playful", "cheerful", "festival", "upbeat",
               "खुश", "खुशी", "khushi", "mast", "नाच", "naach"],
    "epic": ["epic", "cinematic", "grand", "heroic", "triumph*", "majestic", "powerful", "anthem", "battle"],
    "dark": ["dark", "ominous", "haunting", "eerie", "tense", "mysterious", "brooding", "menacing", "अंधेरा", "andhera"],
}
PACE_WORDS = {
    "slow": ["slow", "slowly", "unhurried", "lullaby", "dheema", "dhima", "dheemi", "धीमा", "धीमे", "धीमी", "leisurely",
             "languid"],
    "lively": ["fast", "lively", "upbeat", "energetic", "dance", "dancing", "quick", "brisk", "peppy", "तेज़", "तेज़",
               "tez", "fast-paced"],
    "medium": ["medium", "mid-tempo", "moderate"],
}
ARC_PATTERNS = {
    "slow_build": r"slow(?:ly)?[\s-]+build\w*|build(?:s|ing)?\s+(?:up\s+)?slowly|gradual(?:ly)?|crescendo|builds?\s+up",
    "quiet_middle_bloom": r"quiet\s+middle|bloom\w*|blossom\w*",
    "steady": r"\bsteady\b|\bconstant\b|\bunchanging\b|\bambient\b",
}
FULLNESS_WORDS = {"spare": ["minimal", "minimalist", "sparse", "spare", "stripped", "uncluttered", "bare"],
                  "full": ["lush", "rich", "big", "layered", "dense", "full"]}
STYLE_WORDS = {"ornate": ["ornate", "virtuoso", "virtuosic", "taan", "taans", "intricate", "elaborate"],
               "simple": ["simple", "plain", "unadorned"]}
SPARSE_ADJ = ["barely", "faint", "sparse", "sparsely", "subtle", "soft", "softly", "light", "lightly", "hint of",
              "thoda", "halka", "हल्का"]
FULL_ADJ = ["loud", "strong", "prominent", "driving", "bold", "heavy"]
LEAD_CUES = r"led\s+by|lead(?:ing)?|main|solo|focus(?:ed)?\s+on|featuring|mostly|mainly"
NEGATION = re.compile(r"(?:\bno|\bwithout|\bavoid|\bnot|\bskip|\bbina|बिना|\bnahi|\bnahin)\W*(?:any\s+|the\s+|a\s+)?$")
HINDI_ROMAN = {"gaana", "gana", "gaane", "pyaar", "pyar", "dil", "tera", "teri", "mera", "meri", "hai", "tum", "yaadein",
               "yaad", "chai", "sukoon", "shaant", "dheema", "likho", "chahiye", "mujhe", "subah", "raat", "bina", "ek",
               "ke", "ki", "ka", "mein", "se", "aur"}
HINDI_ROMAN_STRONG = HINDI_ROMAN - {"ek", "ke", "ki", "ka", "se", "aur", "hai", "mein", "bina"}
NUM_WORDS = {"one": 1, "a": 1, "an": 1, "two": 2, "three": 3, "four": 4, "ek": 1, "do": 2, "teen": 3, "char": 4,
             "chaar": 4, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "dedh": 1.5, "डेढ़": 1.5, "डेढ": 1.5, "dhai": 2.5,
             "ढाई": 2.5, "half": 0.5, "five": 5, "paanch": 5, "पाँच": 5, "पांच": 5}
MIN_S, MAX_S = 10, 240


def choir_pick_of(ctl: Controls) -> Optional[str]:
    """'lead' or 'support' when the user picked choir in the instrument controls, else None."""
    if ctl.lead == "choir":
        return "lead"
    if ctl.instruments and "choir" in ctl.instruments:
        return "support"
    return None


def choir_pick_text(pick: str) -> str:
    return "the lead" if pick == "lead" else "a supporting sound"


# --------------------------------------------------------------------------- text helpers
def _n(s: str) -> str:
    """NFC-normalise so precomposed/decomposed Devanagari (e.g. ज़) compare equal."""
    return unicodedata.normalize("NFC", s)


def _rx(term: str) -> re.Pattern:
    term = _n(term)
    if re.search(r"[ऀ-ॿ]", term):
        return re.compile(re.escape(term.rstrip("*")))
    if term.endswith("*"):
        return re.compile(rf"(?<![a-z0-9]){re.escape(term[:-1])}\w*")
    return re.compile(rf"(?<![a-z0-9]){re.escape(term)}(?:s|es)?(?![a-z0-9])")


def _find_any(text: str, terms: list[str]) -> list[tuple[int, int, str]]:
    hits = []
    for t in terms:
        # regex entries (contain a backslash or bracket) are used as-is, plain terms get boundaries
        pat = re.compile(_n(t)) if re.search(r"[\\\[\](){}|]", t) else _rx(t)
        for m in pat.finditer(text):
            hits.append((m.start(), m.end(), m.group(0)))
    return sorted(hits)


def parse_duration(text: str) -> tuple[Optional[int], Optional[str], Optional[str]]:
    """(seconds, matched text, note). Understands English, Roman Hindi and Devanagari; clamps to 10-240 s."""
    t = _n(text).lower()
    num = r"(\d+(?:\.\d+)?|" + "|".join(re.escape(_n(w)) for w in sorted(NUM_WORDS, key=len, reverse=True)) + ")"
    minute, second = _n(r"(?:minutes?|mins?|mnt|मिनट)"), _n(r"(?:seconds?|secs?|सेकंड|सेकेंड)")

    def val(tok: str) -> float:
        for k, v in NUM_WORDS.items():
            if _n(k) == tok:
                return v
        return float(tok)

    rules = [
        (r"\b(\d{1,2}):([0-5]\d)\b(?!\s*(?:am|pm))", lambda m: int(m[1]) * 60 + int(m[2])),
        (num + r"\s+and\s+(?:a\s+)?half\s+" + minute, lambda m: val(m[1]) * 60 + 30),
        (_n(r"half\s+(?:a\s+)?") + minute + _n(r"|आधा\s+मिनट|aadha\s+minute"), lambda m: 30),
        (r"(?<![\w.:])" + num + r"[\s-]*" + minute + r"(?![a-z])", lambda m: val(m[1]) * 60),
        (r"(?<![\w.:])" + num + r"[\s-]*" + second, lambda m: val(m[1])),
    ]
    for pattern, to_secs in rules:
        m = re.search(pattern, t)
        if not m:
            continue
        secs, matched, note = int(round(to_secs(m))), m.group(0), None
        if secs > MAX_S:
            note = (f"You asked for about {matched}; the maximum is {MAX_S // 60} minutes "
                    "until longer pieces are measured.")
            secs = MAX_S
        elif secs < MIN_S:
            note, secs = f"'{matched}' is shorter than the {MIN_S} second minimum.", MIN_S
        return secs, matched, note
    return None, None, None


# --------------------------------------------------------------------------- the planner
class BasicPlanner(Planner):
    name = "basic"
    label = "Basic planner"
    is_llm = False
    can_write_lyrics = False

    # ---- plan -------------------------------------------------------------------------------
    def plan(self, brief: str, controls: Optional[Controls] = None, context: Optional[dict] = None) -> BriefCard:
        if not brief or not brief.strip():
            raise ValueError("brief must not be blank")
        ctl = controls or Controls()
        pol = copyright_policy.sanitize(brief)
        text = _n(pol.text).lower()
        matched: list[str] = []
        notes: list[str] = []
        unsupported: list[dict] = [dict(u) for u in pol.unsupported]
        for n in pol.notes:
            notes.append(n["message"])
        for u in pol.unsupported:
            notes.append(u["message"])

        # --- style (genre preset)
        genre_id, genre_why = None, None
        if ctl.genre:
            genre_id, genre_why = ctl.genre, "you picked the style"
        else:
            g_hits = genres.match(text)
            if g_hits:
                genre_id, kw = g_hits[0]
                genre_why = f"you wrote '{kw}'"
                matched.append(kw)
        # --- voice
        choir_pick = choir_pick_of(ctl)
        mode, voice_why = self._voice(text, ctl, matched)
        if genre_id and not ctl.voice and voice_why.startswith("no voice words"):
            mode = genres.get(genre_id)["voice"]
            voice_why = f"{genres.get(genre_id)['name']} is usually {'sung' if mode == 'sung' else mode}"
        # --- instruments
        mentions, avoid = self._instruments(text, matched)
        choir_in_brief = "choir" in mentions
        mentions.pop("choir", None)
        for a in (ctl.avoid or []):
            avoid.append(a)
        # --- mood / pace / arc / ...
        feelings = self._moods(text, matched)
        recipe_id, recipe_why = self._recipe(ctl, mode, mentions, feelings, matched)
        rec = compiler.load_recipe(recipe_id)
        data = copy.deepcopy(rec["plan_defaults"])
        prov: dict[str, dict] = {k: {"source": "recipe", "reason": f"{rec['display_name']} default"} for k in data}

        def put(field: str, value: Any, source: str, reason: str) -> None:
            data[field] = value
            prov[field] = {"source": source, "reason": reason}

        put("voice_mode", mode, "you" if ctl.voice else "suggested", voice_why)
        if ctl.recipe_id:
            prov["recipe_id"] = {"source": "you", "reason": "you picked this sound"}
        else:
            prov["recipe_id"] = {"source": "suggested", "reason": recipe_why}

        # lead + supports (with a style named, the style preset fills the supporting bed later, not the recipe)
        self._lead_and_supports(data, put, rec, ctl, mentions, avoid, mode, text, notes, top_up=not genre_id)
        # duration
        secs, said, dnote = parse_duration(pol.text)
        if ctl.duration_s:
            put("duration_s", ctl.duration_s, "you", "you set the length")
        elif secs:
            put("duration_s", secs, "suggested", f"you wrote '{said}'")
            matched.append(said)
            if dnote:
                notes.append(dnote)
        # pace / bpm
        self._pace(data, put, ctl, text, matched)
        # key
        km = re.search(r"(?:\bin\s+|\bkey\s+(?:of\s+)?|,\s*)([a-g])(#|b)?\s+(major|minor)\b", text)
        if ctl.key:
            put("key", ctl.key, "you", "you set the key")
        elif km:
            key = f"{km.group(1).upper()}{km.group(2) or ''} {km.group(3)}"
            put("key", key, "suggested", f"you wrote '{km.group(0).strip(' ,')}'")
            matched.append(km.group(0).strip(" ,"))
        # feeling
        if ctl.feeling is not None:
            put("feeling", ctl.feeling, "you", "you picked the feeling")
        elif feelings:
            put("feeling", feelings, "suggested", "mood words in your brief: " + ", ".join(feelings))
        # arc / fullness / style
        self._arc_fullness_style(data, put, ctl, text, matched)
        # voices
        self._voices(data, put, ctl, mode, text, choir_in_brief, choir_pick, notes)
        if choir_pick and mode == "instrumental":
            notes.append(f"You picked choir as {choir_pick_text(choir_pick)} but chose Instrumental, so the voices are "
                         "left out and the piece stays instrumental. Change Voice to Wordless voices to hear the choir.")
        # lyrics policy
        needs: list[str] = []
        if mode == "sung":
            if ctl.lyrics_text and ctl.lyrics_text.strip():
                put("lyrics", {"policy": "exact", "text": ctl.lyrics_text, "topic": None}, "you", "your words, sent unchanged")
            else:
                topic = pol.text.strip()[:200] or None
                put("lyrics", {"policy": "write", "text": None, "topic": topic}, "rule",
                    "Sung words need lyrics; the Basic planner cannot write them")
                unsupported.append({"kind": "write_lyrics", "message":
                    "Writing lyrics for you needs the smart planner, which is off. Paste your own words "
                    "(\"Use my words exactly\"), or choose Instrumental or Wordless voices."})
                needs.append("lyrics")
        else:
            put("lyrics", {"policy": "none", "text": None, "topic": None}, "rule", f"voice is {mode}: no lyric text")
        # avoid
        if avoid:
            uniq = []
            for a in avoid:
                a = a.strip()[:60]
                if a and a.lower() not in [u.lower() for u in uniq]:
                    uniq.append(a)
            put("avoid", uniq[:10], "you" if ctl.avoid else "suggested",
                "left out of the request (the engine may still add them)")
        if ctl.takes:
            put("takes", ctl.takes, "you", "you set versions")

        fallback = not matched
        if fallback:
            notes.append("I could not match any musical words in your brief, so I started from the "
                         f"{rec['display_name']} recipe. Words I look for: instruments, singing or no singing, "
                         "a length, a feeling, a pace.")
        else:
            notes.insert(0, "Words I understood: " + ", ".join(dict.fromkeys(matched)) + ".")
        if recipe_id == "r3_hindi_ballad":
            notes.append("Hindi singing is experimental: one heard take, diction imperfect.")
        notes.append("This is the Basic planner (keyword rules, not an AI). It cannot read stories or analogies.")

        used = [data["lead"]["instrument"]] + [s["instrument"] for s in data.get("supports", [])]
        if genre_id:
            data["genre"] = genre_id
            prov["genre"] = {"source": "you" if ctl.genre else "suggested", "reason": genre_why}
        if ctl.meter:
            data["meter"] = ctl.meter
            prov["meter"] = {"source": "you", "reason": "you set the meter"}
        if genre_id or ctl.meter or any(i not in CLASSIC_INSTRUMENT_IDS for i in used):
            data["pipeline"] = "song"
        plan_dict = dict(data, brief=brief, recipe_id=recipe_id, notes_for_user=notes[:12],
                         provenance={k: v for k, v in prov.items()})
        plan = Plan.model_validate(plan_dict)
        return BriefCard(plan=plan, provider=self.name, provider_label=self.label, is_llm=False, fallback=fallback,
                         matched=list(dict.fromkeys(matched)), notes=notes, unsupported=unsupported,
                         needs_user_input=needs)

    # ---- parsing pieces -----------------------------------------------------------------
    def _voice(self, text: str, ctl: Controls, matched: list[str]) -> tuple[str, str]:
        if ctl.voice:
            return ctl.voice, "you chose the voice"
        def first(pats):
            h = _find_any(text, pats)
            return h[0][2] if h else None
        strong, weak, wl, sg = first(STRONG_INSTRUMENTAL), first(WEAK_INSTRUMENTAL), first(WORDLESS), first(SUNG)
        pick = choir_pick_of(ctl)
        if pick and not (sg and not (strong or weak)):
            # Choir is voices, not an instrument: picking it with Voice on Auto means wordless voices (PRD 5.2).
            why = f"you picked choir as {choir_pick_text(pick)}, and a choir is voices, so I added wordless voices"
            if strong or weak:
                why += f" (your brief said '{strong or weak}'; set Voice to Instrumental to drop the choir)"
            return "wordless", why
        if strong:
            matched.append(strong)
            return "instrumental", f"you wrote '{strong}'"
        if wl:
            matched.append(wl)
            return "wordless", f"you wrote '{wl}'"
        if weak:
            matched.append(weak)
            return "instrumental", f"you wrote '{weak}'"
        if sg:
            matched.append(sg)
            return "sung", f"you wrote '{sg}'"
        return "instrumental", "no voice words in your brief: instrumental is the safest start"

    def _instruments(self, text: str, matched: list[str]) -> tuple[dict[str, dict], list[str]]:
        found: dict[str, dict] = {}
        avoid: list[str] = []
        # every alias hit; a hit inside a longer hit of another instrument ("guitar" in "electric guitar",
        # "bass" in "808 bass") belongs to the longer one
        all_hits = [(s, e, w, inst) for inst, aliases in INSTRUMENT_ALIASES.items() for s, e, w in _find_any(text, aliases)]
        shadowed = {(s, e, inst) for s, e, _, inst in all_hits
                    for s2, e2, _, inst2 in all_hits if inst2 != inst and s2 <= s and e <= e2 and (e2 - s2) > (e - s)}
        for inst, aliases in INSTRUMENT_ALIASES.items():
            for s, e, word in _find_any(text, aliases):
                if (s, e, inst) in shadowed:
                    continue
                if NEGATION.search(text[max(0, s - 14):s]):
                    avoid.append(word if word.isascii() else DISPLAY.get(inst, inst.replace("_", " ")))
                    matched.append(f"no {word}")
                    continue
                if inst in found:
                    continue
                before, after = text[max(0, s - 12):s], text[e:e + 18]
                if _find_any(before, SPARSE_ADJ) or re.match(r"\W*(?:is\s+|are\s+)?(?:barely|faintly|hardly|subtle|quiet)", after):
                    presence = "sparse"
                elif _find_any(before, FULL_ADJ):
                    presence = "full"
                else:
                    presence = "gentle"
                lead_cue = bool(re.search(rf"(?:{LEAD_CUES})\W+(?:\w+\W+){{0,2}}{re.escape(word)}|{re.escape(word)}\W+(?:{LEAD_CUES})",
                                          text[max(0, s - 30):e + 20]))
                found[inst] = {"pos": s, "word": word, "presence": presence, "lead_cue": lead_cue}
                matched.append(word)
        m = re.search(r"\bavoid\s+([a-z ]{3,40}?)(?:[,.;]|$|\sand\s)", text)
        if m:
            avoid.append(m.group(1).strip())
            matched.append(m.group(0).strip(" ,."))
        return dict(sorted(found.items(), key=lambda kv: kv[1]["pos"])), avoid

    def _moods(self, text: str, matched: list[str]) -> list[str]:
        hits: list[tuple[int, str, str]] = []
        for chip, terms in MOODS.items():
            pos = [(s, w) for s, _, w in _find_any(text, terms)]
            if pos:
                s, w = min(pos)
                hits.append((s, chip, w))
        hits.sort()
        for _, chip, w in hits[:3]:
            matched.append(w)
        return [chip for _, chip, _ in hits[:3]]

    def _recipe(self, ctl: Controls, mode: str, mentions: dict, feelings: list[str], matched: list[str]) -> tuple[str, str]:
        if ctl.recipe_id:
            return ctl.recipe_id, "you picked this sound"
        if mode == "sung":
            return "r3_hindi_ballad", "sung words start from the Hindi ballad recipe"
        if mode == "wordless":
            return "r2_warm_ensemble", "wordless voices start from the warm ensemble recipe"
        leads = [i for i in mentions]
        if leads:
            first = next((i for i in mentions if i in MELODIC), leads[0])
            if first in INDIAN_LEADS:
                return "r1_flute_focus", f"{DISPLAY.get(first, first)} is an Indian lead: Flute focus recipe"
            return "r2_warm_ensemble", f"{DISPLAY.get(first, first)} fits the Warm ensemble recipe"
        if any(f in ("joyful", "epic") for f in feelings):
            return "r2_warm_ensemble", "joyful or epic mood: Warm ensemble recipe"
        return "r1_flute_focus", "default start: Flute focus recipe"

    def _lead_and_supports(self, data, put, rec, ctl, mentions, avoid, mode, text, notes, top_up: bool = True) -> None:
        avoid_words = " ".join(avoid).lower()
        def avoided(inst: str) -> bool:
            return any(re.search(rf"\b{re.escape(w)}", avoid_words) for w in _avoid_words(inst)) if avoid_words else False
        named = [i for i in mentions if not avoided(i)]
        if ctl.lead:
            lead = ctl.lead
            lead_src, lead_why = "you", "you starred this instrument"
        elif named:
            cued = [i for i in named if mentions[i]["lead_cue"]]
            melodic = [i for i in named if i in MELODIC]
            lead = (cued or melodic or named)[0]
            lead_src, lead_why = "suggested", f"you wrote '{mentions[lead]['word']}'" + (" with a lead cue" if cued else "")
        else:
            lead, lead_src, lead_why = data["lead"]["instrument"], "recipe", f"{rec['display_name']} default"
        if lead_src != "recipe":
            put("lead", {"instrument": lead, "style": data["lead"]["style"]}, lead_src, lead_why)
        if ctl.instruments is not None:
            order = [i for i in ctl.instruments if i != lead]
            src, why = "you", "you picked the instruments"
        elif named:
            order = [i for i in named if i != lead]
            src, why = "suggested", "instruments you named, in the order you wrote them"
        else:
            order, src, why = [], "recipe", f"{rec['display_name']} default"
        if src == "recipe":
            # the lead never doubles as a support (a picked lead may be one of the recipe's supports)
            data["supports"] = [s for s in data["supports"] if s["instrument"] != lead]
            return
        solo = re.search(r"\b(?:just|only|solo|alone|unaccompanied)\b", text) and not order
        sups = []
        for i in order[:3]:
            m = mentions.get(i)
            sups.append({"instrument": i, "role": ROLE.get(i, "texture"), "presence": m["presence"] if m else "gentle"})
        if len(order) > 3:
            notes.append("I kept the first three supports you named; the rest are left out so the lead stays clear.")
        have = {s["instrument"] for s in sups} | {lead}
        filled = []
        if not solo and top_up:
            for s in data["supports"]:                                  # top up from the recipe to at least two supports
                if len(sups) >= 2:
                    break
                i = s["instrument"]
                if i in have or avoided(i) or (mode == "instrumental" and i == "choir"):
                    continue
                sups.append(dict(s))
                have.add(i)
                filled.append(i)
        put("supports", sups, src, why + (f"; added {', '.join(filled)} from the recipe" if filled else ""))

    def _pace(self, data, put, ctl, text, matched) -> None:
        masked = re.sub(ARC_PATTERNS["slow_build"], " ", text)       # "build slowly" is an arc, not a pace
        bm = re.search(r"(\d{2,3})\s*bpm|bpm\s*(\d{2,3})", text)
        bpm = ctl.bpm or (int(bm.group(1) or bm.group(2)) if bm else None)
        if bpm:
            bpm = max(60, min(140, bpm))
            put("pace", {"bucket": bucket_for_bpm(bpm), "bpm": bpm}, "you" if ctl.bpm else "suggested",
                f"you set {bpm} BPM" if ctl.bpm else f"you wrote '{bm.group(0)}'")
            if bm and not ctl.bpm:
                matched.append(bm.group(0))
            return
        bucket, src, why = ctl.pace, "you", "you picked the pace"
        if not bucket:
            src = "suggested"
            for b in ("slow", "lively", "medium"):
                hit = _find_any(masked, PACE_WORDS[b])
                if hit:
                    bucket, why = b, f"you wrote '{hit[0][2]}'"
                    matched.append(hit[0][2])
                    break
        if not bucket:
            return
        if bucket == data["pace"]["bucket"]:
            put("pace", data["pace"], src, why + " (the recipe tempo already fits)")
        else:
            put("pace", {"bucket": bucket, "bpm": BUCKET_DEFAULT_BPM[bucket]}, src, why)

    def _arc_fullness_style(self, data, put, ctl, text, matched) -> None:
        if ctl.arc:
            put("arc", ctl.arc, "you", "you picked the story")
        else:
            for arc in ("slow_build", "quiet_middle_bloom", "steady"):
                m = re.search(ARC_PATTERNS[arc], text)
                if m:
                    put("arc", arc, "suggested", f"you wrote '{m.group(0)}'")
                    matched.append(m.group(0))
                    break
        if ctl.fullness:
            put("fullness", ctl.fullness, "you", "you picked how full")
        else:
            for level, terms in FULLNESS_WORDS.items():
                for s, e, w in _find_any(text, terms):
                    if _near_instrument(text, e):
                        continue
                    put("fullness", level, "suggested", f"you wrote '{w}'")
                    matched.append(w)
                    break
        style_done = False
        if ctl.style:
            put("lead", dict(data["lead"], style=ctl.style), "you", "you picked the playing style")
            return
        for style, terms in STYLE_WORDS.items():
            h = _find_any(text, terms)
            if h and not style_done:
                put("lead", dict(data["lead"], style=style), "suggested", f"you wrote '{h[0][2]}'")
                matched.append(h[0][2])
                style_done = True

    def _voices(self, data, put, ctl, mode, text, choir_in_brief, choir_pick, notes) -> None:
        v = dict(data["voices"])
        src = "recipe"
        why = "recipe default"
        if mode == "instrumental":
            v = {"singer": "auto", "background": "none", "language": "en"}
            put("voices", v, "rule", "instrumental: no voices")
            return
        if ctl.singer:
            v["singer"], src, why = ctl.singer, "you", "you picked the singer"
        elif mode == "sung":
            if re.search(r"\bduet\b", text):
                v["singer"], src, why = "duet", "suggested", "you wrote 'duet'"
            elif re.search(r"\bfemale\b|\bwoman\b|\bgirl\b|\blady\b|लड़की|औरत|\bladki\b", text):
                v["singer"], src, why = "female", "suggested", "you asked for a female voice"
            elif re.search(r"(?<!fe)\bmale\b|\bman'?s\b|\bboy\b|लड़का|आदमी|\bladka\b", text):
                v["singer"], src, why = "male", "suggested", "you asked for a male voice"
        if ctl.background:
            v["background"], src, why = ctl.background, "you", "you picked background voices"
        elif re.search(r"big\s+choir|huge\s+choir|grand\s+choir|epic\s+choir|choir\s+swell", text):
            v["background"], src, why = "big", "suggested", "you asked for a big choir"
        elif choir_pick:
            v["background"], src, why = "choir", "suggested", f"you picked choir as {choir_pick_text(choir_pick)}"
        elif choir_in_brief:
            v["background"], src, why = "choir", "suggested", "you wrote 'choir'"
        elif re.search(r"harmon(?:y|ies)|backing\s+vocals", text):
            v["background"], src, why = "light", "suggested", "you wrote 'harmonies'"
        elif mode == "wordless" and v["background"] == "none":
            v["background"], src, why = "light", "rule", "wordless voices need at least light harmonies"
        if mode != "sung":
            v["singer"] = "auto"
        # language
        if mode == "sung":
            if ctl.language:
                v["language"], lsrc, lwhy = ctl.language, "you", "you picked the language"
            elif re.search(r"[ऀ-ॿ]", text) or re.search(r"\bhindi\b|हिंदी|हिन्दी", text):
                v["language"], lsrc, lwhy = "hi", "suggested", "Hindi in your brief"
            elif re.search(r"\benglish\b", text):
                v["language"], lsrc, lwhy = "en", "suggested", "you asked for English"
            elif len(set(re.findall(r"[a-z]+", text)) & HINDI_ROMAN_STRONG) >= 2:
                v["language"], lsrc, lwhy = "hi", "suggested", "Roman Hindi words in your brief"
            else:
                v["language"], lsrc, lwhy = "hi", "rule", "no language given: Hindi is the only sung language we have heard"
                notes.append("No language given, so I chose Hindi (the only sung language heard so far, still experimental).")
            if v["language"] == "en":
                notes.append("English sung words are untested.")
            put("voices", v, src if src != "recipe" else lsrc, f"{why}; language: {lwhy}")
            return
        v["language"] = ctl.language or "en"
        put("voices", v, src, why)

    # ---- patch (chips) --------------------------------------------------------------------
    def patch(self, plan: Plan, request_text: str) -> PlanPatch:
        t = request_text.strip().lower().replace("_", " ")
        chips = [c for c, pat in CHIP_PATTERNS.items() if re.search(pat, t)]
        data = plan.model_dump(mode="json")
        changes: list[dict] = []
        applied: list[str] = []
        unsupported: list[dict] = []
        for chip in chips:
            before = len(changes)
            msg = CHIP_FUNCS[chip](data, changes)
            if len(changes) > before:
                applied.append(chip)
            elif msg:
                unsupported.append({"kind": "chip_noop", "chip": chip, "message": msg})
        if not chips:
            unsupported.append({"kind": "free_text", "message":
                "The Basic planner can only apply the quick-change chips (less busy, more melodic, slower, "
                "livelier, warmer, brighter, different lead, more/fewer voices). Free-text change requests "
                "need the smart planner."})
        new = Plan.model_validate(data) if applied else plan
        return PlanPatch(plan=new, provider=self.name, applied=applied, changes=changes, unsupported=unsupported)

    def draft_lyrics(self, plan: Plan) -> LyricsDraft:
        raise UnsupportedByPlanner("Writing lyrics needs the smart planner, which is off. The Basic planner "
                                   "cannot write lyrics. Paste your own words instead.", code="write_lyrics_unsupported")


def _avoid_words(inst: str) -> list[str]:
    if inst in compiler.INSTR:
        return compiler.INSTR[inst]["avoid_words"]
    return [a for a in inst_db.get(inst)["aliases"] if a.isascii()] or [inst.replace("_", " ")]


def _near_instrument(text: str, end: int) -> bool:
    """True if an instrument alias starts right after `end` (so the adjective belongs to it)."""
    tail = text[end:end + 16]
    for aliases in INSTRUMENT_ALIASES.values():
        hit = _find_any(tail, aliases)
        if hit and hit[0][0] <= 2:
            return True
    return False


# --------------------------------------------------------------------------- chips (PRD section 6)
CHIP_PATTERNS = {
    "less_busy": r"less busy|simpler|fewer instruments|too busy|less crowded|कम भीड़",
    "more_melodic": r"more melod|catchier|more memorable",
    "slower": r"slower|slow down|धीमा|dheema",
    "livelier": r"livelier|faster|speed up|more lively|more energy|तेज़",
    "warmer": r"warmer|more warmth",
    "brighter": r"brighter",
    "different_lead": r"different lead|another lead|change the lead|swap the lead",
    "more_voices": r"more voices|more choir|bigger choir",
    "fewer_voices": r"fewer voices|less choir|smaller choir",
}
_FULLNESS_DOWN = {"full": "balanced", "balanced": "spare", "spare": "spare"}
_BG_UP = ["none", "light", "choir", "big"]


def _change(changes: list, field: str, old: Any, new: Any, chip: str) -> None:
    """One 'what changed' entry in the standard schema (see planner_base.change_entry); `chip` only names the stamp."""
    changes.append(change_entry(field, old, new, "chip"))


def _stamp(data: dict, field: str, chip: str) -> None:
    data["provenance"][field.split(".")[0]] = {"source": "you", "reason": f"chip: {chip.replace('_', ' ')}"}


def _less_busy(data, changes):
    old = data["fullness"]
    if _FULLNESS_DOWN[old] != old:
        data["fullness"] = _FULLNESS_DOWN[old]
        _change(changes, "fullness", old, data["fullness"], "less_busy")
        _stamp(data, "fullness", "less_busy")
    if data["supports"]:
        before = [x["instrument"] for x in data["supports"]]
        data["supports"].pop()
        _change(changes, "supports", before, before[:-1], "less_busy")
        _stamp(data, "supports", "less_busy")
    return "Already as spare as it gets: nothing left to remove."


def _more_melodic(data, changes):
    if data["lead"]["style"] != "singing":
        _change(changes, "lead.style", data["lead"]["style"], "singing", "more_melodic")
        data["lead"]["style"] = "singing"
        _stamp(data, "lead", "more_melodic")
    if "memorable" not in [f.lower() for f in data["feeling"]] and len(data["feeling"]) < 8:
        _change(changes, "feeling", list(data["feeling"]), ["memorable"] + data["feeling"], "more_melodic")
        data["feeling"] = ["memorable"] + data["feeling"]
        _stamp(data, "feeling", "more_melodic")
    return "Already singing and memorable."


def _tempo(delta: int, chip: str):
    def f(data, changes):
        old = data["pace"]["bpm"]
        new = max(68, min(116, old + delta))
        if new == old:
            return "Already at the slowest allowed pace." if delta < 0 else "Already at the liveliest allowed pace."
        data["pace"] = {"bucket": bucket_for_bpm(new), "bpm": new}
        _change(changes, "pace", old, new, chip)
        _stamp(data, "pace", chip)
        return None
    return f


def _tone(add: str, remove: set[str], chip: str):
    def f(data, changes):
        old = list(data["feeling"])
        new = [w for w in old if w.lower() not in remove]
        if add not in [w.lower() for w in new]:
            new.append(add)
        new = new[:8]
        if new == old:
            return f"Already {add}."
        data["feeling"] = new
        _change(changes, "feeling", old, new, chip)
        _stamp(data, "feeling", chip)
        return None
    return f


def _different_lead(data, changes):
    if not data["supports"]:
        return "There is no other instrument to promote to lead."
    before = [x["instrument"] for x in data["supports"]]
    old_lead, new = data["lead"], data["supports"].pop(0)
    data["lead"] = {"instrument": new["instrument"], "style": old_lead["style"]}
    data["supports"].insert(0, {"instrument": old_lead["instrument"], "role": "answer", "presence": "gentle"})
    _change(changes, "lead", old_lead["instrument"], new["instrument"], "different_lead")
    _change(changes, "supports", before, [x["instrument"] for x in data["supports"]], "different_lead")
    _stamp(data, "lead", "different_lead")
    _stamp(data, "supports", "different_lead")
    return None


def _voices(step: int, chip: str):
    def f(data, changes):
        if data["voice_mode"] == "instrumental":
            return "This piece is instrumental. Change Voice first to add voices."
        v = data["voices"]
        old = v["background"]
        new = _BG_UP[max(0, min(3, _BG_UP.index(old) + step))]
        if data["voice_mode"] == "wordless" and new == "none":
            new = "light"
        if new == old:
            return "Already at the limit for background voices."
        v["background"] = new
        _change(changes, "voices.background", old, new, chip)
        _stamp(data, "voices", chip)
        return None
    return f


CHIP_FUNCS = {
    "less_busy": _less_busy, "more_melodic": _more_melodic, "slower": _tempo(-8, "slower"),
    "livelier": _tempo(8, "livelier"),
    "warmer": _tone("warm", {"bright", "luminous", "sparkling", "crisp", "cold"}, "warmer"),
    "brighter": _tone("bright", {"warm", "dark", "mellow", "dull"}, "brighter"),
    "different_lead": _different_lead, "more_voices": _voices(1, "more_voices"), "fewer_voices": _voices(-1, "fewer_voices"),
}
