"""Song-pipeline compiler: plan + blueprint -> ACE-Step caption, tagged lyrics and engine parameters.

Same output shape as `compiler.compile` (caption, lyrics, params, effective_params, compile_report, ...), so the
queue, storage and UI need no special case. Differences from the classic template compiler:

* the caption follows ACE-Step's songwriting guide: genre words, mood, vocal character, instrumentation,
  the journey through the sections, and production texture. Tempo, key and time signature go in their own
  parameters, never in the caption;
* the lyric sheet is the temporal script: one tag per blueprint section with a short hint
  ("[Chorus - soaring strings]"), sung lines under vocal sections, every chorus repeat copied word for word;
* the engine profile sets `shift` (3.0 is ACE-Step's recommendation for the turbo model) and, when the optional
  5Hz LM is installed and enabled, `thinking`.

Budget: 512 characters (ACE-Step's caption limit). Drop order when over budget: flavour, production beyond the first
phrase, section-journey beats beyond three, supports beyond three, mood words beyond two, all production, the whole
journey, supports beyond one, all mood words. Never dropped: genre words, the vocal description or voice tail, the
lead instrument. Nothing is truncated mid-word; if the core alone is too long, OverBudget is raised.
"""
from __future__ import annotations

import copy
import hashlib
import re
from typing import Any, Optional

from . import capabilities, compiler, copyright_policy, genres, lyric_craft, song_plan
from . import instruments as inst_db
from .plan_schema import Plan

CAPTION_HARD_CAP = compiler.CAPTION_HARD_CAP
LM_MODEL = "acestep-5Hz-lm-1.7B"
DIT_TURBO, DIT_XL = "acestep-v15-turbo", "acestep-v15-xl-turbo"
ENGINE_PROFILES: dict[str, dict[str, Any]] = {
    "classic": {"dit": DIT_TURBO, "lm": None, "shift": 1.0, "inference_steps": 8, "thinking": False,
                "label": "Classic (turbo, shift 1.0, as the accepted recipes)"},
    "shift3": {"dit": DIT_TURBO, "lm": None, "shift": 3.0, "inference_steps": 8, "thinking": False,
               "label": "Turbo, shift 3.0 (ACE-Step's recommendation for turbo)"},
    "lm": {"dit": DIT_TURBO, "lm": LM_MODEL, "shift": 3.0, "inference_steps": 8, "thinking": True,
           "label": f"Turbo, shift 3.0, with the 5Hz LM ({LM_MODEL}) planning the audio"},
    "xl": {"dit": DIT_XL, "lm": None, "shift": 3.0, "inference_steps": 8, "thinking": False,
           "label": "XL turbo (4B DiT), shift 3.0"},
    "xl_lm": {"dit": DIT_XL, "lm": LM_MODEL, "shift": 3.0, "inference_steps": 8, "thinking": True,
              "label": f"XL turbo (4B DiT), shift 3.0, with the 5Hz LM ({LM_MODEL})"},
}
DEFAULT_PROFILE = "shift3"
LANG_NAME = compiler.LANG_NAME
SINGER_WORD = {"male": "male", "female": "female", "duet": "male and female duet", "auto": ""}
BG_SUNG = {"light": "soft backing harmonies", "choir": "choir harmonies in the chorus",
           "big": "big choir swells in the chorus"}
BG_WORDLESS = compiler.BG_WORDLESS
KIND_WORD = {"intro": "intro", "verse": "verses", "pre_chorus": "pre-chorus", "chorus": "chorus", "bridge": "bridge",
             "outro": "outro", "solo": "solo", "interlude": "interlude", "build": "build", "drop": "drop",
             "break": "instrumental break"}
# Section names that mean something musically and are worth saying in the caption; any other name ("Theme A",
# "Loop B", "Verse 2") is described by its job instead.
NAMED_SECTIONS = {"alaap", "aalap", "jor", "gat", "taans", "jhala", "cadence", "mukhda", "antara 1", "matla",
                  "prelude", "hook", "drop", "breakdown", "climax", "resolution", "swell"}
PRESENCE = {"sparse": "sparse ", "gentle": "", "full": "rich "}


def _sentence(s: str) -> str:
    s = s.strip().rstrip(",")
    return s if s.endswith((".", "!", "?")) else s + "."


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _join(items: list[str]) -> str:
    return compiler._join(items)


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class _Report(compiler._Report):
    pass


# ------------------------------------------------------------------------------------------- resolve
def _resolve(plan: Plan, preset: dict, rep: _Report) -> dict:
    mode = plan.voice_mode
    _strip = compiler._strip_names
    _strip(plan.brief, "brief", rep)
    flavour = _strip(plan.flavour, "flavour", rep) or None
    feelings = [w for w in (_strip(f, "feeling", rep) for f in plan.feeling) if w]
    avoid_terms = [t for t in (compiler._avoid_norm(_strip(a, "avoid", rep) or "") for a in plan.avoid) if t]
    lead = plan.lead.instrument
    bg = plan.voices.background
    supports = [s.model_dump() for s in plan.supports]

    if mode == "instrumental" and lead == "choir":
        heir = next((s["instrument"] for s in supports if s["instrument"] != "choir"), None)
        lead = preset["lead"] if preset["lead"] != "choir" else (heir or "piano")
        supports = [s for s in supports if s["instrument"] != lead]
        rep.conflict("instrumental_with_choir", "choir was chosen as the lead of an instrumental piece",
                     f"voices dropped; {inst_db.display_name(lead)} leads instead and the piece stays instrumental")
    kept = []
    for s in supports:
        if s["instrument"] == lead:
            rep.warnings.append(f"{lead} is already the lead; the duplicate support was ignored.")
            continue
        if s["instrument"] == "choir":
            if mode == "instrumental":
                if not any(c["kind"] == "instrumental_with_choir" for c in rep.conflicts):
                    rep.conflict("instrumental_with_choir", "choir was requested in an instrumental piece",
                                 "voices dropped; the piece stays instrumental")
                rep.drop("support", "choir", "instrumental")
            else:
                bg = bg if bg != "none" else "choir"
                rep.warnings.append("choir moved from the instrument list to background voices.")
            continue
        kept.append(s)
    supports = kept
    if mode == "instrumental":
        bg = "none"
    if mode == "wordless" and bg == "none":
        bg = "light"

    # avoid: omit matching instruments and words; "no X" is never written into the caption body
    def words_for(inst: str) -> set[str]:
        d = inst_db.get(inst)
        return {d["name"].lower(), d["caption"].lower(), inst.replace("_", " ")} | {a.lower() for a in d["aliases"]}

    kept_terms = []
    for term in avoid_terms:
        if set(re.findall(r"\w+", term)) & compiler.VOICE_WORDS:
            if mode != "instrumental":
                rep.conflict("avoid_vs_voice_mode", f"avoid '{term}' conflicts with voice_mode '{mode}'",
                             "the Voice control wins; avoid term ignored")
            continue
        if any(term == w or term in w.split() for w in words_for(lead)):
            rep.conflict("avoid_vs_lead", f"avoid '{term}' matches the lead instrument {lead}",
                         "lead kept; avoid term ignored")
            continue
        kept_terms.append(term)
    out = []
    for s in supports:
        if any(t in words_for(s["instrument"]) or any(t in w for w in words_for(s["instrument"])) for t in kept_terms):
            rep.drop("support", s["instrument"], "avoid")
        else:
            out.append(s)
    supports = out

    def avoided(text: str) -> bool:
        return any(compiler._hits(text, {t}) for t in kept_terms)

    for w in [f for f in feelings if avoided(f)]:
        feelings.remove(w)
        rep.drop("mood", w, "avoid")
    if flavour and avoided(flavour):
        rep.drop("flavour", flavour, "avoid")
        flavour = None
    if mode != "instrumental":
        if flavour and compiler.BLOCKED_VOCAL.search(flavour):
            rep.drop("flavour", flavour, "blocked_style_L1")
            flavour = None
        for w in [f for f in feelings if compiler.BLOCKED_VOCAL.search(f)]:
            feelings.remove(w)
            rep.drop("mood", w, "blocked_style_L1")
    production = [p for p in preset.get("production", []) if not avoided(p)]
    fullness = {"spare": "sparse arrangement with breathing space", "full": "full rich arrangement"}.get(plan.fullness)
    if fullness:                                       # "How full" leads the production words (dropped last of them)
        production = [fullness] + production
    return {"mode": mode, "lead": lead, "supports": supports, "bg": bg, "feelings": feelings, "flavour": flavour,
            "production": production, "avoid": kept_terms, "singer": plan.voices.singer,
            "language": plan.voices.language, "style": plan.lead.style}


# ------------------------------------------------------------------------------------------- caption
def _vocal_phrase(st: dict, preset: dict) -> str:
    lang = LANG_NAME.get(st["language"], st["language"].upper())
    base = preset.get("vocal") or "expressive lead vocal with natural phrasing"
    for other in set(LANG_NAME.values()) - {lang}:
        base = re.sub(rf"\b{other}\b", lang, base)
    if lang not in base:
        base += f", sung in {lang}"
    gender = SINGER_WORD.get(st["singer"], "")
    if gender:
        base = re.sub(r"\bvocal\b", f"{gender} vocal", base, count=1) if re.search(r"\bvocal\b", base) \
            else f"{gender} vocals, {base}"
    if st["bg"] != "none":
        base += f", with {BG_SUNG[st['bg']]}"
    return base


def _journey(blueprint, limit: int = 7) -> list[str]:
    beats, seen = [], set()
    for s in blueprint.sections:
        key = "final" if s.final else s.kind
        if key in seen:
            continue
        seen.add(key)
        label = "final chorus" if s.final else (s.name.lower() if s.name.lower() in NAMED_SECTIONS
                                                else KIND_WORD.get(s.kind, s.kind))
        hint = s.style_hint.split(",")[0].strip() if s.style_hint else ""
        if hint and (label in hint.lower() or KIND_WORD.get(s.kind, "~") in hint.lower()):
            beats.append(hint)
        elif hint:
            beats.append(f"{hint} {label}")
        else:
            beats.append(label)
    return beats[:limit]


def _techniques(st: dict) -> list[str]:
    """Playing-technique words for instrumental leads (the terms behind the accepted Yamuna take)."""
    d = compiler.INSTR.get(st["lead"])
    if not d or st["mode"] == "sung":
        return []
    return list(d["tech"].get(st["style"], []))[:4]


def _render(st: dict, preset: dict) -> list[tuple[str, str]]:
    mode = st["mode"]
    genre = preset["genre_tags"]
    if mode == "instrumental" and "instrumental" not in genre.lower():
        genre += ", instrumental"
    out = [("genre", _sentence(_cap(genre)))]
    if st["feelings"]:
        out.append(("mood", _sentence(_cap(", ".join(st["feelings"])))))
    if mode == "sung":
        out.append(("vocal", _sentence(_cap(_vocal_phrase(st, preset)))))
    elif mode == "wordless":
        out.append(("vocal", _sentence(_cap(preset.get("wordless") or BG_WORDLESS.get(st["bg"], "wordless voices")))))
    lead = inst_db.get(st["lead"])
    sups = [PRESENCE.get(s.get("presence", "gentle"), "") + inst_db.caption_name(s["instrument"]) for s in st["supports"]]
    if mode == "sung":
        out.append(("instruments", _sentence(_cap(_join([lead["caption"]] + sups)))))
    else:
        tail = f", with {_join(sups)}" if sups else ""
        verb = "lead" if re.search(r"(?:s|drums)$", lead["lead_caption"]) and not lead["lead_caption"].endswith("ss") else "leads"
        out.append(("instruments", _sentence(_cap(f"{lead['lead_caption']} {verb} every section{tail}"))))
        if st["techniques"]:
            out.append(("techniques", _sentence(_cap(", ".join(st["techniques"])))))
    if st["journey"]:
        out.append(("journey", _sentence(_cap(", ".join(st["journey"])))))
    if st["production"]:
        out.append(("production", _sentence(_cap(", ".join(st["production"])))))
    if st["flavour"]:
        out.append(("flavour", _sentence(st["flavour"])))
    tail = {"instrumental": "Strictly no voices.", "wordless": "Wordless voices only, no lyrics.",
            "sung": "Vocal forward, natural phrasing."}[mode]
    out.append(("tail", tail))
    return out


def _caption(slots: list[tuple[str, str]]) -> str:
    return " ".join(t for _, t in slots)


def _drop_next(st: dict, rep: _Report) -> bool:
    steps = [
        ("flavour", lambda: st["flavour"], lambda: st.update(flavour=None)),
        ("production", lambda: len(st["production"]) > 1, lambda: st["production"].pop()),
        ("technique", lambda: len(st["techniques"]) > 2, lambda: st["techniques"].pop()),
        ("beat", lambda: len(st["journey"]) > 3, lambda: st["journey"].pop()),
        ("support", lambda: len(st["supports"]) > 3, lambda: st["supports"].pop()),
        ("mood", lambda: len(st["feelings"]) > 2, lambda: st["feelings"].pop()),
        ("production", lambda: st["production"], lambda: st["production"].pop()),
        ("technique", lambda: st["techniques"], lambda: st["techniques"].pop()),
        ("beat", lambda: st["journey"], lambda: st["journey"].pop()),
        ("support", lambda: len(st["supports"]) > 1, lambda: st["supports"].pop()),
        ("mood", lambda: st["feelings"], lambda: st["feelings"].pop()),
    ]
    for kind, can, do in steps:
        if can():
            item = do()
            if isinstance(item, dict):
                item = item["instrument"]
            rep.drop(kind, str(item) if item is not None else kind, "over_budget")
            return True
    return False


def _fit(st: dict, preset: dict, rep: _Report, max_chars: int) -> tuple[str, list[tuple[str, str]]]:
    slots = _render(st, preset)
    while len(_caption(slots)) > max_chars:
        if not _drop_next(st, rep):
            break
        slots = _render(st, preset)
    cap = _caption(slots)
    if len(cap) > max_chars:
        raise compiler.OverBudget(len(cap), max_chars, cap, rep.dropped)
    return cap, slots


# ------------------------------------------------------------------------------------------- lyrics
def _lyrics(plan: Plan, st: dict, blueprint, rep: _Report) -> tuple[str, dict]:
    mode = st["mode"]
    if mode in ("instrumental", "wordless"):
        text = lyric_craft.assemble(blueprint.sections, {}, voice_mode=mode)
        return text, {"mode": f"{mode}_sections", "sha256": _sha(text), "sections": len(blueprint.sections)}
    raw = plan.lyrics.text
    if raw is None or not raw.strip():
        raise compiler.LyricsMissing("lyrics_missing", "Voice is 'Sung words' but there are no lyrics. Paste your "
                                     "own words (use my words exactly) or ask the smart planner to write them.")
    normalised = compiler._newlines(raw)
    if len(normalised) > compiler.LYRICS_HARD_CAP:
        raise compiler.LyricsTooLong("lyrics_too_long", f"Lyrics are {len(normalised)} characters; the limit is "
                                     f"{compiler.LYRICS_HARD_CAP}. Nothing was truncated.")
    if plan.lyrics.policy == "exact":
        tagged, inserted = song_plan.frame_exact_lyrics(normalised)
        if len(tagged) > compiler.LYRICS_HARD_CAP:
            tagged, inserted = normalised, []
            rep.warnings.append("section tags were not added because the lyrics are close to the character limit.")
        mode_name = "exact"
    else:
        tagged, inserted = normalised, []          # drafted sheets are already tagged by the songwriter
        mode_name = "draft"
    lines = [ln for _, ls in lyric_craft.parse_tagged(tagged) for ln in ls]
    if blueprint.fit != "ok":
        rep.conflict("lyrics_duration_fit", "; ".join(blueprint.changes) or blueprint.fit,
                     "lyrics sent unchanged and length kept as requested; nothing was repeated or removed")
    return tagged, {
        "mode": mode_name, "source_sha256": _sha(raw), "sha256": _sha(normalised), "output_sha256": _sha(tagged),
        "newlines_normalised": raw != normalised, "inserted_tag_line_indices": inserted,
        "inserted_tag_lines": [tagged.split("\n")[i] for i in inserted], "line_count": len(lines),
        "char_count": len(tagged), "fit": {"status": blueprint.fit, "estimated_s": blueprint.estimated_s,
                                           "target_s": blueprint.target_s},
    }


def _arrangement(plan: Plan, st: dict, rep: _Report) -> dict:
    req = {"lead": plan.lead.instrument, "supports": [s.instrument for s in plan.supports],
           "voice_mode": plan.voice_mode, "background": plan.voices.background}
    eff = {"lead": st["lead"], "supports": [s["instrument"] for s in st["supports"]],
           "voice_mode": st["mode"], "background": st["bg"]}
    adj = []
    if req["lead"] != eff["lead"]:
        adj.append({"field": "lead", "requested": req["lead"], "effective": eff["lead"],
                    "reason": f"Choir is voices and Voice is Instrumental, so choir was left out; "
                              f"{inst_db.display_name(eff['lead'])} leads instead"})
    dropped = {d["item"]: d["reason"] for d in rep.dropped if d["kind"] == "support"}
    for inst in req["supports"]:
        if inst in eff["supports"]:
            continue
        if inst == eff["lead"]:
            why = f"{inst} already leads"
        elif inst == "choir" and eff["voice_mode"] != "instrumental":
            why = "choir is carried by the background voices"
        else:
            why = {"instrumental": "Voice is Instrumental", "avoid": "it matches something you asked to avoid",
                   "over_budget": "it did not fit the prompt length"}.get(dropped.get(inst, ""), "left out")
        adj.append({"field": "supports", "requested": inst, "effective": None, "reason": why})
    if req["background"] != eff["background"]:
        adj.append({"field": "voices.background", "requested": req["background"], "effective": eff["background"],
                    "reason": "Voice is Instrumental, so there are no voices" if eff["voice_mode"] == "instrumental"
                    else "wordless voices need some background voices"})
    return {"requested": req, "effective": eff, "adjustments": adj}


# ------------------------------------------------------------------------------------------- public
def compile_song(plan: Plan | dict, *, engine_profile: str = DEFAULT_PROFILE,
                 max_chars: int = CAPTION_HARD_CAP) -> dict:
    plan = plan if isinstance(plan, Plan) else Plan.model_validate(plan)
    if plan.pipeline != "song":
        raise compiler.CompileError("wrong_pipeline", "this plan uses the classic pipeline; use compiler.compile")
    if engine_profile not in ENGINE_PROFILES:
        raise compiler.CompileError("unknown_engine_profile", f"engine profile must be one of {list(ENGINE_PROFILES)}")
    if not 1 <= max_chars <= CAPTION_HARD_CAP:
        raise ValueError(f"max_chars must be 1..{CAPTION_HARD_CAP}")
    preset = genres.get(plan.genre) if plan.genre else genres.get(song_plan.default_genre(plan)[0])
    rep = _Report()
    st = _resolve(plan, preset, rep)
    if (plan.provenance.get("arc") and plan.provenance["arc"].source == "you"):
        rep.unsupported.append({"kind": "arc_replaced_by_song_map", "field": "arc", "message":
                                "Story of the piece is not used for styled songs: the song map sets the shape "
                                "(which sections, how loud each one gets)."})
    blueprint = song_plan.blueprint_for(plan, lead=st["lead"], supports=st["supports"])
    st["journey"] = _journey(blueprint)
    st["techniques"] = _techniques(st)
    if len(st["supports"]) > 4:
        rep.warnings.append(f"{len(st['supports'])} supporting instruments; more than 4 tends to blur the lead.")
    caption, slot_list = _fit(st, preset, rep, max_chars)
    lyrics, lyr_rep = _lyrics(plan, st, blueprint, rep)
    mode = st["mode"]
    if mode == "sung":
        badge = capabilities.language_badge(st["language"])
        rep.warnings.append(f"{badge['label']} sung words are {badge['badge']}: listen to check diction.")
    prof = ENGINE_PROFILES[engine_profile]
    params = copy.deepcopy(compiler.ENGINE_DEFAULTS)
    params.update(
        caption=caption, lyrics=lyrics, instrumental=(mode == "instrumental"),
        vocal_language="en" if mode != "sung" else st["language"],
        bpm=plan.pace.bpm, keyscale=plan.key, timesignature=_timesig(plan.meter), duration=plan.duration_s,
        fade_in_duration=0.08, fade_out_duration=3.0,
        shift=prof["shift"], inference_steps=prof["inference_steps"], thinking=prof["thinking"],
    )
    effective = dict(params, guidance_scale=1.0)
    notes = ["Turbo model does not use CFG: the engine overrides guidance_scale to 1.0. "
             "The engine result is authoritative; this is the expected value."]
    if prof["thinking"]:
        notes.append(f"The 5Hz LM ({prof['lm']}) writes audio codes before the DiT renders; caption, lyrics and "
                     "metadata stay exactly as compiled (no LM rewriting).")
    if prof["dit"] != DIT_TURBO:
        notes.append(f"DiT checkpoint {prof['dit']} instead of {DIT_TURBO}.")
    return {
        "caption": caption, "lyrics": lyrics, "params": params, "effective_params": effective,
        "effective_notes": notes, "engine_config": dict(compiler.ENGINE_CONFIG),
        "engine_profile": engine_profile, "lm_model": prof["lm"], "dit_model": prof["dit"],
        "lyrics_prompt": plan.lyrics.topic, "plan_sha256": plan.fingerprint(),
        "compile_report": {
            "pipeline": "song", "genre": preset["id"], "genre_name": preset["name"],
            "engine_profile": engine_profile, "engine_profile_label": prof["label"],
            "char_count": len(caption), "dropped": rep.dropped, "warnings": rep.warnings + blueprint.changes,
            "conflicts": rep.conflicts, "unsupported": rep.unsupported, "notes": rep.notes, "cap": max_chars,
            "slots": [[n, t] for n, t in slot_list], "lyrics": lyr_rep,
            "arrangement": _arrangement(plan, st, rep), "blueprint": blueprint.to_dict(),
        },
    }


def _timesig(meter: str) -> str:
    from .song_blueprint import ACE_TIMESIG
    return ACE_TIMESIG.get(meter, "4")


def compile_any(plan: Plan | dict, *, engine_profile: Optional[str] = None,
                max_chars: int = CAPTION_HARD_CAP) -> dict:
    """The one entry point for the app: song plans go through this compiler, classic plans through the original."""
    plan = plan if isinstance(plan, Plan) else Plan.model_validate(plan)
    if plan.pipeline == "song":
        return compile_song(plan, engine_profile=engine_profile or DEFAULT_PROFILE, max_chars=max_chars)
    out = compiler.compile(plan, max_chars=max_chars)
    out["engine_profile"], out["lm_model"], out["dit_model"] = "classic", None, DIT_TURBO
    out["compile_report"]["pipeline"] = "classic"
    out["compile_report"]["engine_profile"] = "classic"
    return out


def model_block(compiled: dict) -> Optional[dict]:
    """The engine request's "model" object, or None for the default turbo DiT without an LM (so classic requests
    stay exactly as they were)."""
    dit, lm = compiled.get("dit_model") or DIT_TURBO, compiled.get("lm_model")
    if dit == DIT_TURBO and not lm:
        return None
    block: dict[str, Any] = {"dit": dit}
    if lm:
        block["lm"] = {"name": lm, "backend": "mlx"}
    return block


def required_weights(profile: str) -> list[str]:
    prof = ENGINE_PROFILES[profile]
    return [prof["dit"]] + ([prof["lm"]] if prof["lm"] else [])
