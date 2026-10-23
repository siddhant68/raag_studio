"""Deterministic caption/lyrics/params compiler (PRD v2 section 5.2).

compile(plan) -> {caption, lyrics, params, effective_params, compile_report, ...}

Caption slot grammar, in order (each slot is one sentence):
  1 opening        format + lead + supports
  2 lead_priority  "<Lead> is the loud clear melodic lead in every section."
  3 techniques     tone + up to 5 technique terms for the lead (C11)
  4 melody         one melody/feeling sentence (C7), then the "how full" phrase (C9)
  5 arc            3-5 beats (C10)
  6 bpm_key        "NN BPM, <key>."
  7 tail           voice constraint, e.g. "Strictly no voices."
  8 flavour        optional clause, <= 120 chars

Budget: hard cap 512 characters (target <= 510). DROP ORDER when over budget:
  1. flavour clause
  2. optional supports, lowest rank (last in the list) first
  3. technique terms beyond the first three (last first)
  4. arc beats beyond the first three (last first)
  5. mood adjectives (feeling words last first, then the "how full" phrase)
NEVER dropped: lead instrument, lead-priority sentence, voice-constraint tail,
BPM/key. If those alone exceed the cap, OverBudget is raised. Nothing is truncated.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional

from . import capabilities, copyright_policy, lyric_fit
from .plan_schema import Plan

CAPTION_HARD_CAP = 512
CAPTION_TARGET = 510
LYRICS_HARD_CAP = 4000
KEEP_TECHNIQUES = 3     # drop phase 3 never goes below this
KEEP_BEATS = 3          # drop phase 4 never goes below this
RECIPES_DIR = Path(__file__).resolve().parents[1] / "recipes"
ENGINE_REQUEST_SCHEMA = "raag-engine-request/1"


class CompileError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class OverBudget(CompileError):
    """The never-dropped core of the caption alone exceeds the cap."""

    def __init__(self, char_count: int, cap: int, caption: str, dropped: list[dict]):
        super().__init__("over_budget", f"The essential caption is {char_count} characters; the cap is {cap}. "
                                        "Nothing was truncated.")
        self.char_count, self.cap, self.caption, self.dropped = char_count, cap, caption, dropped


class LyricsTooLong(CompileError):
    pass


class LyricsMissing(CompileError):
    pass


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
def _i(short, base, solo, avoid, tone=None, tech=None, is_are="is", support=None):
    return {"short": short, "base": base, "lead_solo": solo, "avoid_words": avoid, "tone": tone,
            "tech": tech or {}, "is_are": is_are, "support_base": support or base}


INSTR: dict[str, dict] = {
    "bansuri": _i("Bansuri", "bamboo flute", "Indian bamboo flute solo", ["bansuri", "flute", "bamboo"],
                  "Rich breathy flute tone", {
        "simple": ["clean sustained notes", "gentle phrasing", "natural breaths"],
        "singing": ["expressive meend pitch slides", "delicate grace notes", "fluid fast runs", "octave turns",
                    "lyrical sustained notes with natural breaths"],
        "ornate": ["graceful pitch glides", "sparkling fast taans and trills", "octave leaps", "intricate grace notes",
                   "virtuoso runs"]}),
    "tabla": _i("Tabla", "tabla", "tabla-led rhythmic piece", ["tabla"], "Crisp resonant tabla tone", {
        "simple": ["soft steady theka", "gentle taps"],
        "singing": ["flowing tabla patterns", "soft rolling phrases", "gentle rhythmic conversation"],
        "ornate": ["fast tihai patterns", "rolling rhythmic phrases", "intricate bols"]}),
    "tanpura": _i("Tanpura", "tanpura", "tanpura drone piece", ["tanpura", "drone"], support="tanpura drone"),
    "santoor": _i("Santoor", "santoor", "Indian santoor solo", ["santoor"], "Shimmering hammered santoor tone", {
        "simple": ["clear hammered notes", "soft sustain", "spacious phrasing"],
        "singing": ["flowing tremolo", "delicate grace notes", "lyrical melodic phrases"],
        "ornate": ["rippling fast runs", "shimmering tremolo", "intricate ornaments", "virtuoso passages"]}),
    "sitar": _i("Sitar", "sitar", "Indian sitar solo", ["sitar"], "Resonant plucked sitar tone", {
        "simple": ["clear plucked notes", "gentle phrasing", "sustained resonance"],
        "singing": ["expressive meend string bends", "delicate grace notes", "flowing melodic phrases"],
        "ornate": ["fast jhala strumming", "sparkling taans", "intricate meend bends", "virtuoso runs"]}),
    "ghatam": _i("Ghatam", "ghatam", "ghatam-led rhythmic piece", ["ghatam", "matka"]),
    "violin": _i("Violin", "violin", "solo violin piece", ["violin", "fiddle"], "Warm singing violin tone", {
        "simple": ["long bowed notes", "gentle vibrato", "simple phrasing"],
        "singing": ["expressive vibrato", "lyrical legato phrasing", "tender slides"],
        "ornate": ["fast bowed runs", "expressive slides", "double-stop flourishes", "virtuoso passages"]}),
    "cello": _i("Cello", "cello", "solo cello piece", ["cello"], "Deep warm cello tone", {
        "simple": ["long bowed notes", "gentle vibrato", "simple phrasing"],
        "singing": ["expressive vibrato", "lyrical legato phrasing", "tender slides"],
        "ornate": ["fast bowed runs", "expressive slides", "rich double stops"]}),
    "strings": _i("Strings", "strings", "string ensemble piece", ["strings", "string", "orchestra"],
                  "Warm legato string tone", {
        "simple": ["long sustained chords", "gentle swells"],
        "singing": ["lyrical legato lines", "gentle swells", "expressive sustained notes"],
        "ornate": ["sweeping runs", "rich layered swells", "dramatic crescendos"]}, is_are="are"),
    "piano": _i("Piano", "piano", "piano solo", ["piano"], "Warm expressive piano tone", {
        "simple": ["simple gentle chords", "soft sustained notes", "spacious phrasing"],
        "singing": ["smooth chord changes", "expressive sustained notes", "breathing phrases"],
        "ornate": ["flowing arpeggios", "expressive runs", "rich harmonies", "dynamic builds"]}),
    "acoustic_guitar": _i("Acoustic guitar", "acoustic guitar", "acoustic guitar solo", ["guitar"],
                          "Warm fingerpicked guitar tone", {
        "simple": ["gentle fingerpicking", "soft open chords", "spacious phrasing"],
        "singing": ["lyrical fingerpicked melody", "expressive sustained notes", "smooth chord changes"],
        "ornate": ["flowing fingerstyle runs", "rich arpeggios", "intricate ornaments"]}),
    "bass": _i("Bass", "bass", "bass-led piece", ["bass"]),
    "light_percussion": _i("Percussion", "light percussion", "light percussion piece",
                           ["drums", "drum", "percussion", "kick", "snare", "shaker", "groove"]),
    "choir": _i("Choir", "choir", "choir piece", ["choir"]),
    "harmonium": _i("Harmonium", "harmonium", "harmonium solo", ["harmonium"], "Warm breathy harmonium tone", {
        "simple": ["soft sustained chords", "gentle phrasing"],
        "singing": ["lyrical sustained lines", "gentle ornaments", "breathing phrases"],
        "ornate": ["flowing ornamented runs", "rich sustained chords"]}),
}

PRESENCE_WORD = {"sparse": "sparse", "gentle": "gentle", "full": "rich"}
SINGER = {"auto": "expressive lead voice", "male": "warm expressive male lead",
          "female": "warm expressive female lead", "duet": "male and female duet leads"}
BG_WORDLESS = {"light": "soft wordless ooh/aah harmonies", "choir": "wordless mixed-choir ooh/aah harmonies",
               "big": "big swelling wordless choir ooh/aah"}
BG_SUNG = {"light": "soft backing harmonies", "choir": "choir harmonies in the chorus",
           "big": "big choir swells in the chorus"}
LANG_NAME = {"hi": "Hindi", "en": "English", "ur": "Urdu", "pa": "Punjabi", "bn": "Bengali", "ta": "Tamil",
             "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "es": "Spanish", "fr": "French"}
FULLNESS_PHRASE = {"spare": "Sparse accompaniment with breathing space.", "balanced": "", "full": "Full rich arrangement."}
GENERIC_ARCS = {
    "steady": ["steady gentle opening", "even flowing pulse", "warm sustained middle", "calm resolved ending"],
    "slow_build": ["spacious quiet opening", "gradual entrance of the rhythm", "growing fuller middle",
                   "expressive climax", "gentle cadence"],
    "quiet_middle_bloom": ["gentle opening", "flowing first half", "quiet exposed middle", "blooming fuller return",
                           "peaceful cadence"],
}
GENERIC_OPENING = {
    "instrumental": "Instrumental {lead_solo}{with_supports}.",
    "wordless": "Acoustic piece led by {lead_ens}{with_supports}{voice_with}.",
    "sung": "{Language} acoustic song: {voice_phrase} over {ensemble}.",
}
GENERIC_LEAD_PRIORITY = {
    "instrumental": "{Lead} {is_are} the loud clear melodic lead in every section.",
    "wordless": "{Lead} {is_are} the clear melodic lead in every section.",
    "sung": "Voice is the clear lead in every section.",
}
GENERIC_TAIL = {"instrumental": "Strictly no voices.", "wordless": "Wordless voices only, no lyrics.",
                "sung": "Vocal forward, natural phrasing."}
GENERIC_MELODY = "Beautiful recurring melody{feeling_clause}."
VOICE_WORDS = {"voice", "voices", "vocal", "vocals", "vocalist", "singing", "singer", "sing", "lyrics", "words", "choir"}
# Style L1 (PRD 5.1): wording blamed for the rejected "someone reading" vocal result.
BLOCKED_VOCAL = re.compile(r"a[\s-]?cappella|one\s+note\s+per\s+syllable|no\s+melisma|no\s+reverb|dry\s+vocal", re.I)

# Engine params in the same order/keys as context_pack/recipes/*/request.json "params" (minus seed).
# None marks values filled in by compile().
_FILL = None
ENGINE_DEFAULTS: dict[str, Any] = {
    "task_type": "text2music", "instruction": "Fill the audio semantic mask based on the given conditions:",
    "reference_audio": None, "src_audio": None, "audio_codes": "", "caption": _FILL, "global_caption": "",
    "lyrics": _FILL, "instrumental": _FILL, "vocal_language": _FILL, "bpm": _FILL, "keyscale": _FILL,
    "timesignature": "4", "duration": _FILL, "enable_normalization": True, "normalization_db": -1.5,
    "fade_in_duration": _FILL, "fade_out_duration": _FILL, "latent_shift": 0.0, "latent_rescale": 1.0,
    "inference_steps": 8, "guidance_scale": 7.0, "use_adg": False, "cfg_interval_start": 0.0,
    "cfg_interval_end": 1.0, "shift": 1.0, "infer_method": "ode", "sampler_mode": "euler",
    "velocity_norm_threshold": 0.0, "velocity_ema_factor": 0.0, "dcw_enabled": None, "dcw_mode": "double",
    "dcw_scaler": 0.05, "dcw_high_scaler": 0.02, "dcw_wavelet": "haar", "timesteps": None,
    "repainting_start": 0.0, "repainting_end": -1, "chunk_mask_mode": "auto",
    "repaint_latent_crossfade_frames": 10, "repaint_wav_crossfade_sec": 0.0, "repaint_mode": "balanced",
    "repaint_strength": 0.5, "retake_seed": None, "retake_variance": 0.0, "flow_edit_morph": False,
    "flow_edit_source_caption": "", "flow_edit_source_lyrics": "", "flow_edit_n_min": 0.0, "flow_edit_n_max": 1.0,
    "flow_edit_n_avg": 1, "audio_cover_strength": 1.0, "cover_noise_strength": 0.0, "thinking": False,
    "lm_temperature": 0.85, "lm_cfg_scale": 2.0, "lm_top_k": 0, "lm_top_p": 0.9,
    "lm_negative_prompt": "NO USER INPUT", "use_cot_metas": False, "use_cot_caption": False,
    "use_cot_lyrics": False, "use_cot_language": False, "use_constrained_decoding": True, "cot_bpm": None,
    "cot_keyscale": "", "cot_timesignature": "", "cot_duration": None, "cot_vocal_language": "unknown",
    "cot_caption": "", "cot_lyrics": "",
}
# Native-audio config for the worker (not part of "params").
ENGINE_CONFIG = {"batch_size": 1, "use_random_seed": False, "audio_format": "flac"}


# ---------------------------------------------------------------------------
# Recipes (data in app/recipes/*.json)
# ---------------------------------------------------------------------------
def load_recipe(recipe_id: Optional[str]) -> Optional[dict]:
    if recipe_id is None:
        return None
    with open(RECIPES_DIR / f"{recipe_id}.json", encoding="utf-8") as fh:
        return json.load(fh)


def list_recipes(include_hidden: bool = False) -> list[dict]:
    out = [load_recipe(p.stem) for p in sorted(RECIPES_DIR.glob("*.json"))]
    return [r for r in out if include_hidden or not r["hidden_until_rated"]]


def plan_from_recipe(recipe_id: str, brief: str, *, with_example_lyrics: bool = False, **overrides: Any) -> Plan:
    """A full plan from a recipe's defaults; every defaulted field is tagged provenance 'recipe'."""
    rec = load_recipe(recipe_id)
    data = copy.deepcopy(rec["plan_defaults"])
    if with_example_lyrics and rec.get("example_lyrics"):
        data["lyrics"] = {"policy": "exact", "text": rec["example_lyrics"], "topic": None}
    data.update(overrides)
    data.update(brief=brief, recipe_id=recipe_id)
    reason = f"{rec['display_name']} default (evidence: {rec['evidence']})"
    data["provenance"] = {k: {"source": "recipe", "reason": reason} for k in rec["plan_defaults"] if k not in overrides}
    return Plan.model_validate(data)


def default_plan(recipe_id: str) -> Plan:
    """The recipe exactly as accepted (R3 includes its example Hindi lyric)."""
    return plan_from_recipe(recipe_id, f"Default plan: {load_recipe(recipe_id)['display_name']}",
                            with_example_lyrics=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]


def _sentence(s: str) -> str:
    s = s.strip()
    return s if s.endswith((".", "!", "?")) else s + "."


def _pick(value: Any, mode: str, generic: dict | str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        hit = value.get(mode) or value.get("default")
        if hit:
            return hit
    return generic[mode] if isinstance(generic, dict) else generic


def _avoid_norm(term: str) -> str:
    return re.sub(r"^(?:no|not|without|avoid|never)\s+", "", term.strip().lower()).strip()


def _avoid_matchset(term: str) -> tuple[set[str], set[str]]:
    """(strings to look for, instrument ids the term refers to)."""
    tokens = re.findall(r"\w+", term)
    insts = {i for i, d in INSTR.items() if any(t in d["avoid_words"] for t in tokens)}
    words = {term} if term else set()
    for i in insts:
        words |= set(INSTR[i]["avoid_words"])
    return words, insts


def _hits(text: str, words: set[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(w)}s?\b", low) for w in words if w)


def _newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


_TAG_LINE = re.compile(r"^\s*\[[^\[\]\n]{1,40}\]\s*$")


class _Report:
    def __init__(self) -> None:
        self.dropped: list[dict] = []
        self.warnings: list[str] = []
        self.conflicts: list[dict] = []
        self.unsupported: list[dict] = []
        self.notes: list[dict] = []

    def conflict(self, kind: str, detail: str, resolution: str, **extra: Any) -> None:
        self.conflicts.append({"kind": kind, "detail": detail, "resolution": resolution, **extra})

    def drop(self, kind: str, item: str, reason: str) -> None:
        self.dropped.append({"kind": kind, "item": item, "reason": reason})


# ---------------------------------------------------------------------------
# Step 1: resolve the plan into a working state, applying conflicts/policy/avoid
# ---------------------------------------------------------------------------
def _strip_names(text: Optional[str], where: str, rep: _Report) -> Optional[str]:
    if not text:
        return text
    res = copyright_policy.sanitize(text)
    for n in res.notes:
        rep.notes.append({**n, "field": where})
        rep.conflict("named_reference_stripped", f"'{n['removed']}' named in {where}",
                     "removed from prompts; the mood is used, not the song", field=where)
    for u in res.unsupported:
        if u not in rep.unsupported:
            rep.unsupported.append({**u, "field": where})
    return res.text


def _resolve(plan: Plan, rec: Optional[dict], rep: _Report, instrumental_flag: Optional[bool]) -> dict:
    mode = plan.voice_mode
    if instrumental_flag is not None and instrumental_flag != (mode == "instrumental"):
        rep.conflict("instrumental_flag_vs_voice_mode",
                     f"instrumental={instrumental_flag} was requested but voice_mode is '{mode}'",
                     f"voice_mode '{mode}' wins; instrumental={mode == 'instrumental'}")

    _strip_names(plan.brief, "brief", rep)
    flavour = _strip_names(plan.flavour, "flavour", rep) or None
    topic = _strip_names(plan.lyrics.topic, "lyrics.topic", rep) or None
    feelings = [w for w in (_strip_names(f, "feeling", rep) for f in plan.feeling) if w]
    avoid_terms = [t for t in (_avoid_norm(_strip_names(a, "avoid", rep) or "") for a in plan.avoid) if t]

    lead = plan.lead.instrument
    bg, singer, language = plan.voices.background, plan.voices.singer, plan.voices.language

    def choir_conflict(detail: str) -> None:
        if not any(c["kind"] == "instrumental_with_choir" for c in rep.conflicts):
            rep.conflict("instrumental_with_choir", detail, "voices dropped; the piece stays instrumental")

    supports: list[dict] = []
    for s in plan.supports:
        sd = s.model_dump()
        if sd["instrument"] == lead:
            rep.warnings.append(f"{lead} is already the lead; the duplicate support was ignored.")
            continue
        if sd["role"] == "lead":
            rep.conflict("two_leads", f"both {lead} and {sd['instrument']} claim the lead",
                         f"{lead} stays the lead; {sd['instrument']} became a support (answer)")
            sd["role"] = "answer"
        if sd["instrument"] == "choir":
            if mode == "instrumental":
                choir_conflict("choir was requested in an instrumental piece")
                rep.drop("support", "choir", "instrumental")
            else:
                bg = bg if bg != "none" else "choir"
                rep.warnings.append("choir moved from the instrument list to background voices (C14).")
            continue
        supports.append(sd)

    if mode == "instrumental" and bg != "none":
        choir_conflict(f"background voices '{bg}' were requested in an instrumental piece")
        bg = "none"
    if mode == "wordless" and bg == "none":
        rep.conflict("wordless_without_voices", "wordless voices were requested but background voices are 'none'",
                     "light harmonies used so the wordless request has voices")
        bg = "light"
    if mode != "sung" and plan.lyrics.text:
        rep.conflict("lyrics_ignored", f"lyrics were given but voice_mode is '{mode}'",
                     "lyric text kept in the plan but not sent; it is only used when Voice is Sung words")
    if mode != "sung" and singer != "auto":
        rep.warnings.append(f"singer '{singer}' is ignored unless Voice is Sung words.")
    if mode == "instrumental" and language != "en":
        rep.warnings.append("language is ignored for instrumental pieces (vocal_language is set to 'en').")

    # L1: wording blamed for the rejected vocal result is never emitted for voiced modes.
    if mode != "instrumental":
        if flavour and BLOCKED_VOCAL.search(flavour):
            rep.warnings.append("flavour dropped: dry/a-cappella/no-reverb vocal wording is blocked (style L1).")
            rep.drop("flavour", flavour, "blocked_style_L1")
            flavour = None
        kept = [w for w in feelings if not BLOCKED_VOCAL.search(w)]
        for w in set(feelings) - set(kept):
            rep.drop("mood", w, "blocked_style_L1")
        feelings = kept

    # Avoid: omit matching items; never write "no X" into the caption body.
    kept_terms: list[tuple[str, set[str]]] = []
    for term in avoid_terms:
        words, insts = _avoid_matchset(term)
        if set(re.findall(r"\w+", term)) & VOICE_WORDS:
            if mode != "instrumental":
                rep.conflict("avoid_vs_voice_mode", f"avoid '{term}' conflicts with voice_mode '{mode}'",
                             "the Voice control wins; avoid term ignored")
            continue                                        # instrumental already satisfies it
        if lead in insts or _hits(INSTR[lead]["short"], {term}):
            rep.conflict("avoid_vs_lead", f"avoid '{term}' matches the lead instrument {lead}",
                         "lead kept; avoid term ignored")
            continue
        kept_terms.append((term, words))

    def avoided(text: str) -> bool:
        return any(_hits(text, w) for _, w in kept_terms)

    new_supports = []
    for s in supports:
        if avoided(INSTR[s["instrument"]]["support_base"]) or any(s["instrument"] in _avoid_matchset(t)[1] for t, _ in kept_terms):
            rep.drop("support", s["instrument"], "avoid")
        else:
            new_supports.append(s)
    supports = new_supports
    for w in [f for f in feelings if avoided(f)]:
        feelings.remove(w)
        rep.drop("mood", w, "avoid")
    if flavour and avoided(flavour):
        rep.drop("flavour", flavour, "avoid")
        flavour = None

    # Arc beats, technique terms, fullness phrase.
    slots = (rec or {}).get("slots", {})
    arc_src = slots.get("arcs", {}).get(plan.arc)
    only = slots.get("arcs_lead_only")
    if arc_src is None or (only and only != lead):
        arc_src = [{"text": t} for t in GENERIC_ARCS[plan.arc]]
    beats = [dict(b) for b in arc_src]
    tone = tech = None
    if mode != "sung":
        d = INSTR[lead]
        tone = slots.get("tone", {}).get(lead) or d["tone"]
        tech = list(slots.get("techniques", {}).get(lead, {}).get(plan.lead.style) or d["tech"].get(plan.lead.style, []))
    state = {
        "mode": mode, "lead": lead, "style": plan.lead.style, "supports": supports, "feelings": feelings,
        "beats": beats, "tone": tone, "techniques": tech or [], "fullness": plan.fullness,
        "fullness_on": bool(FULLNESS_PHRASE[plan.fullness]), "flavour": flavour, "bg": bg, "singer": singer,
        "language": language, "bpm": plan.pace.bpm, "key": plan.key, "topic": topic, "avoid": kept_terms,
    }
    _prune_beats(state, rep, reason="avoid")
    for t, w in kept_terms:
        for key in ("techniques",):
            for item in [x for x in state[key] if _hits(x, w)]:
                state[key].remove(item)
                rep.drop("technique", item, "avoid")
    return state


def _prune_beats(st: dict, rep: _Report, reason: str) -> None:
    """Remove beats whose `needs` instrument/voices is gone, or that mention an avoided word."""
    present = {st["lead"]} | {s["instrument"] for s in st["supports"]}
    keep = []
    for b in st["beats"]:
        need = b.get("needs")
        gone = need and ((need == "voices" and st["bg"] == "none") or (need != "voices" and need not in present))
        hit = any(_hits(b["text"], w) for _, w in st["avoid"])
        if gone or hit:
            rep.drop("beat", b["text"], "needs_dropped_support" if gone else "avoid")
        else:
            keep.append(b)
    st["beats"] = keep


# ---------------------------------------------------------------------------
# Step 2: render caption slots, fit the budget
# ---------------------------------------------------------------------------
def _support_phrase(sd: dict, slots: dict) -> str:
    custom = slots.get("support_phrases", {}).get(sd["instrument"])
    if isinstance(custom, str):
        return custom
    if isinstance(custom, dict) and sd["presence"] in custom:
        return custom[sd["presence"]]
    base = INSTR[sd["instrument"]]["support_base"]
    return f"answering {base}" if sd["role"] == "answer" else f"{PRESENCE_WORD[sd['presence']]} {base}"


def _render(st: dict, rec: Optional[dict]) -> list[tuple[str, str]]:
    slots = (rec or {}).get("slots", {})
    mode, lead, d = st["mode"], st["lead"], INSTR[st["lead"]]
    sup_phrases = [_support_phrase(s, slots) for s in st["supports"]]
    lead_ens = slots.get("lead_phrases", {}).get(lead, d["base"])
    lang = LANG_NAME.get(st["language"], st["language"].upper())
    if mode == "wordless":
        voice_phrase = BG_WORDLESS[st["bg"]]
    elif mode == "sung":
        voice_phrase = f"{SINGER[st['singer']]} singing clear {lang}"
        if st["bg"] != "none":
            voice_phrase += f" with {BG_SUNG[st['bg']]}"
    else:
        voice_phrase = ""
    feelings = st["feelings"]
    memorable = "memorable" in [f.lower() for f in feelings]
    others = [f for f in feelings if f.lower() != "memorable"]
    melody_tpl = slots.get("melody") or GENERIC_MELODY
    swap_head = memorable and "Beautiful recurring melody" in melody_tpl     # "Memorable recurring melody" instead
    clause_words = others + (["memorable"] if memorable and not swap_head else [])
    vals = {
        "lead_solo": d["lead_solo"], "lead_ens": lead_ens, "Lead": d["short"], "lead_lower": d["short"].lower(),
        "is_are": d["is_are"], "with_supports": (" with " + _join(sup_phrases)) if sup_phrases else "",
        "ensemble": _join([lead_ens] + sup_phrases), "voice_phrase": voice_phrase,
        "voice_with": f", with {voice_phrase}" if voice_phrase and mode == "wordless" else "",
        "Language": lang, "feeling_clause": (", " + _join(clause_words)) if clause_words else "",
    }

    def fmt(tpl: str) -> str:
        try:
            return _sentence(tpl.format_map(vals))
        except (KeyError, IndexError) as exc:
            raise CompileError("recipe_template_error", f"recipe template uses unknown placeholder {exc}") from exc

    out: list[tuple[str, str]] = [
        ("opening", _cap_first(fmt(_pick(slots.get("opening"), mode, GENERIC_OPENING)))),
        ("lead_priority", _cap_first(fmt(_pick(slots.get("lead_priority"), mode, GENERIC_LEAD_PRIORITY)))),
    ]
    terms = ([st["tone"]] if st["tone"] else []) + st["techniques"]
    if terms:
        out.append(("techniques", _cap_first(_sentence(", ".join(terms)))))
    melody = fmt(melody_tpl)
    if swap_head:
        melody = melody.replace("Beautiful recurring melody", "Memorable recurring melody", 1)
    out.append(("melody", _cap_first(melody)))
    if st["fullness_on"]:
        out.append(("fullness", FULLNESS_PHRASE[st["fullness"]]))
    if st["beats"]:
        out.append(("arc", _cap_first(_sentence(_join([b["text"] for b in st["beats"]])))))
    out.append(("bpm_key", f"{st['bpm']} BPM, {st['key']}."))
    out.append(("tail", _sentence(_pick(slots.get("tail"), mode, GENERIC_TAIL))))
    if st["flavour"]:
        out.append(("flavour", _sentence(st["flavour"])))
    return out


def _caption(slots: list[tuple[str, str]]) -> str:
    return " ".join(text for _, text in slots)


def _drop_next(st: dict, rep: _Report) -> bool:
    """Apply the next drop in the documented order; False when nothing droppable remains."""
    if st["flavour"]:
        rep.drop("flavour", st["flavour"], "over_budget")
        st["flavour"] = None
        return True
    if st["supports"]:
        gone = st["supports"].pop()
        rep.drop("support", gone["instrument"], "over_budget")
        _prune_beats(st, rep, reason="support")
        return True
    if len(st["techniques"]) > KEEP_TECHNIQUES:
        rep.drop("technique", st["techniques"].pop(), "over_budget")
        return True
    if len(st["beats"]) > KEEP_BEATS:
        rep.drop("beat", st["beats"].pop()["text"], "over_budget")
        return True
    if st["feelings"]:
        rep.drop("mood", st["feelings"].pop(), "over_budget")
        return True
    if st["fullness_on"]:
        rep.drop("mood", FULLNESS_PHRASE[st["fullness"]], "over_budget")
        st["fullness_on"] = False
        return True
    return False


def _fit(st: dict, rec: Optional[dict], rep: _Report, max_chars: int) -> tuple[str, list[tuple[str, str]]]:
    target = min(CAPTION_TARGET, max_chars)
    slots = _render(st, rec)
    while len(_caption(slots)) > target:
        if not _drop_next(st, rep):
            break
        slots = _render(st, rec)
    caption = _caption(slots)
    if len(caption) > max_chars:
        raise OverBudget(len(caption), max_chars, caption, rep.dropped)
    if len(caption) > target:
        rep.warnings.append(f"caption is {len(caption)} characters, within {max_chars - len(caption)} of the hard cap.")
    # Safety net: avoid terms must not appear in the body (only the voice tail may carry them).
    for term, words in st["avoid"]:
        if any(_hits(text, words) for name, text in slots if name != "tail"):
            rep.conflict("avoid_unresolved", f"'{term}' appears in fixed wording", "kept; could not be removed safely")
    return caption, slots


# ---------------------------------------------------------------------------
# Step 3: lyrics
# ---------------------------------------------------------------------------
def insert_tag_lines(text: str) -> tuple[str, list[int]]:
    """Insert [Verse]/[Chorus] tag lines (code-inserted, separate lines) into untagged lyrics.

    The text itself is never altered: removing the returned line indices from the
    result gives back the newline-normalised input exactly. If the user already
    wrote any [Tag] line, nothing is inserted.
    """
    lines = _newlines(text).split("\n")
    if any(_TAG_LINE.match(ln) for ln in lines):
        return "\n".join(lines), []
    stanzas: list[tuple[int, str]] = []            # (first line index, content key)
    i = 0
    while i < len(lines):
        if lines[i].strip():
            j = i
            while j < len(lines) and lines[j].strip():
                j += 1
            stanzas.append((i, "\n".join(lines[i:j])))
            i = j
        else:
            i += 1
    counts: dict[str, int] = {}
    for _, key in stanzas:
        counts[key] = counts.get(key, 0) + 1
    repeated = any(c > 1 for c in counts.values())
    out: list[str] = []
    inserted: list[int] = []
    starts = {first: n for n, (first, _) in enumerate(stanzas)}
    for idx, line in enumerate(lines):
        if idx in starts:
            n = starts[idx]
            if repeated:
                tag = "[Chorus]" if counts[stanzas[n][1]] > 1 else "[Verse]"
            else:
                tag = "[Verse]" if n % 2 == 0 else "[Chorus]"
            inserted.append(len(out))
            out.append(tag)
        out.append(line)
    return "\n".join(out), inserted


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _skeleton(rec: Optional[dict], bg: str) -> str:
    sk = (rec or {}).get("lyric_skeleton") or load_recipe("r2_warm_ensemble")["lyric_skeleton"]
    blocks = sk["vowel_blocks"]
    parts = []
    for sec in sk["sections"]:
        if sec["body"] == "instrumental":
            body = ["[Instrumental]"]
        else:
            body = blocks[sec["block"]][: 2 if bg == "light" else None]
        parts.append("\n".join([f"[{sec['tag']}]"] + body))
    return "\n\n".join(parts)


def _build_lyrics(plan: Plan, st: dict, rec: Optional[dict], rep: _Report) -> tuple[str, dict]:
    mode = st["mode"]
    if mode == "instrumental":
        return "[Instrumental]", {"mode": "instrumental"}
    if mode == "wordless":
        text = _skeleton(rec, st["bg"])
        return text, {"mode": "wordless_skeleton", "sha256": _sha(text)}
    raw = plan.lyrics.text
    if raw is None or not raw.strip():
        raise LyricsMissing("lyrics_missing", "Voice is 'Sung words' but there are no lyrics. Paste your own words "
                                              "(use my words exactly) or ask the smart planner to draft them.")
    normalised = _newlines(raw)
    if len(normalised) > LYRICS_HARD_CAP:
        raise LyricsTooLong("lyrics_too_long", f"Lyrics are {len(normalised)} characters; the limit is "
                                               f"{LYRICS_HARD_CAP}. Nothing was truncated.")
    tagged, inserted = insert_tag_lines(normalised)
    if len(tagged) > LYRICS_HARD_CAP:
        rep.warnings.append("section tags were not added because the lyrics are close to the character limit.")
        tagged, inserted = normalised, []
    fit = lyric_fit.fit_lyrics(normalised, plan.duration_s)
    if fit.status != "ok" or any("differs" in w for w in fit.warnings):
        rep.conflict("lyrics_duration_fit", "; ".join(fit.warnings) or f"{fit.line_count} lines",
                     "lyrics sent unchanged and length kept as requested; nothing was repeated or removed",
                     fit=fit.to_dict())
    return tagged, {
        "mode": "exact" if plan.lyrics.policy == "exact" else "draft",
        "source_sha256": _sha(raw), "sha256": _sha(normalised), "output_sha256": _sha(tagged),
        "newlines_normalised": raw != normalised,
        "inserted_tag_line_indices": inserted, "inserted_tag_lines": [tagged.split("\n")[i] for i in inserted],
        "line_count": fit.line_count, "char_count": len(tagged), "fit": fit.to_dict(),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compile(plan: Plan | dict, *, max_chars: int = CAPTION_HARD_CAP, instrumental_flag: Optional[bool] = None,
            recipe: Optional[dict] = None) -> dict:  # noqa: A001 - spec name
    """Compile a validated plan. `max_chars` may only lower the 512 cap (used by tests)."""
    plan = plan if isinstance(plan, Plan) else Plan.model_validate(plan)
    if not 1 <= max_chars <= CAPTION_HARD_CAP:
        raise ValueError(f"max_chars must be 1..{CAPTION_HARD_CAP}")
    rec = recipe if recipe is not None else load_recipe(plan.recipe_id)
    rep = _Report()
    st = _resolve(plan, rec, rep, instrumental_flag)
    if len(plan.supports) > 3:
        rep.warnings.append(f"{len(plan.supports)} supports requested; more than 3 tends to blur the lead.")
    caption, slot_list = _fit(st, rec, rep, max_chars)
    lyrics, lyr_rep = _build_lyrics(plan, st, rec, rep)

    mode = st["mode"]
    if mode == "sung":
        badge = capabilities.language_badge(st["language"])
        rep.warnings.append(f"{badge['label']} sung words are {badge['badge']}: listen to check diction.")
    fin = (rec or {}).get("finish", {})
    params = copy.deepcopy(ENGINE_DEFAULTS)
    params.update(
        caption=caption, lyrics=lyrics, instrumental=(mode == "instrumental"),
        vocal_language="en" if mode == "instrumental" else st["language"],
        bpm=st["bpm"], keyscale=st["key"], duration=plan.duration_s,
        fade_in_duration=fin.get("fade_in_duration", 0.08), fade_out_duration=fin.get("fade_out_duration", 3.0),
    )
    effective = dict(params, guidance_scale=1.0)
    topic = st["topic"]
    return {
        "caption": caption, "lyrics": lyrics, "params": params,
        "effective_params": effective,
        "effective_notes": ["Turbo model does not use CFG: the engine overrides guidance_scale to 1.0. "
                            "The engine result is authoritative; this is the expected value."],
        "engine_config": dict(ENGINE_CONFIG),
        "lyrics_prompt": topic,
        "plan_sha256": plan.fingerprint(),
        "compile_report": {
            "char_count": len(caption), "dropped": rep.dropped, "warnings": rep.warnings,
            "conflicts": rep.conflicts, "unsupported": rep.unsupported, "notes": rep.notes,
            "cap": max_chars, "slots": [[n, t] for n, t in slot_list], "lyrics": lyr_rep,
        },
    }


def to_engine_request(compiled: dict, seeds: list[int], *, audio_format: Optional[str] = None,
                      meta: Optional[dict] = None) -> dict:
    """The contract with app/engine/run_takes.py (see app/engine/REQUEST_CONTRACT.md).

    Returns {"schema", "params" (WITHOUT seed), "seeds"}; `audio_format` and `meta` are
    added only when given.
    """
    ok = (isinstance(seeds, list) and 1 <= len(seeds) <= 8 and len(set(seeds)) == len(seeds)
          and all(isinstance(s, int) and not isinstance(s, bool) and 0 <= s < 2**31 for s in seeds))
    if not ok:
        raise ValueError("seeds must be 1 to 8 distinct integers in [0, 2^31)")
    params = copy.deepcopy(compiled["params"])
    params.pop("seed", None)
    if len(params["caption"]) > CAPTION_HARD_CAP:
        raise CompileError("caption_too_long", "caption exceeds 512 characters")
    if len(params["lyrics"]) > LYRICS_HARD_CAP:
        raise CompileError("lyrics_too_long", "lyrics exceed 4000 characters")
    req: dict[str, Any] = {"schema": ENGINE_REQUEST_SCHEMA, "params": params, "seeds": list(seeds)}
    if audio_format:
        req["audio_format"] = audio_format
    if meta:
        req["meta"] = meta
    return req
