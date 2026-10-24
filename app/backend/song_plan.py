"""Turn a planner's card into a song-pipeline plan and work out its blueprint.

Order of precedence for every field: what the person set (provenance 'you') > what the planner read in the brief
('suggested') > the genre preset > the old recipe default ('recipe'). The preset therefore only fills fields that
nobody chose: a rule-planner card built from recipe defaults takes the genre's instruments, tempo and key, while a
smart-planner card (which chooses everything itself) keeps its own choices and only gains the genre's form and hints.
"""
from __future__ import annotations

import re
from typing import Optional

from . import compiler, genres, lyric_craft, song_blueprint
from . import instruments as inst_db
from .plan_schema import Plan, bucket_for_bpm

CHOSEN = ("you", "suggested")
LANG_DEFAULT_SUNG = {"hi": "hindi_acoustic_ballad", "ur": "ghazal", "pa": "punjabi_bhangra"}


def _source(plan: Plan, field: str) -> Optional[str]:
    p = plan.provenance.get(field)
    return p.source if p else None


def chosen(plan: Plan, field: str) -> bool:
    return _source(plan, field) in CHOSEN


def _voice_part_chosen(plan: Plan, part: str) -> bool:
    """Voices carry one provenance for singer, background and language; the rule planner's reason tells which part
    came from the brief ("recipe default; language: you asked for English" chose the language, not the singer)."""
    pr = plan.provenance.get("voices")
    if not pr or pr.source not in CHOSEN:
        return False
    if part == "singer":
        return not pr.reason.startswith("recipe default")
    return "no language given" not in pr.reason


def default_genre(plan: Plan) -> tuple[str, str]:
    """A genre for a plan nobody gave a genre: (preset id, reason)."""
    if plan.voice_mode == "sung":
        lang = plan.voices.language
        pid = LANG_DEFAULT_SUNG.get(lang, "acoustic_pop")
        return pid, f"sung words in {lang}: starting from {genres.get(pid)['name']}"
    if plan.voice_mode == "wordless":
        return "warm_cinematic_acoustic", "wordless voices: starting from the warm ensemble sound"
    lead = plan.lead.instrument
    if lead == "sitar":
        return "raag_sitar", "sitar lead: raag form"
    if inst_db.get(lead)["indian"]:
        return "raag_bansuri", f"{inst_db.display_name(lead)} lead: raag form"
    if lead in ("strings", "cello", "brass"):
        return "cinematic_orchestral", f"{inst_db.display_name(lead)} lead: cinematic form"
    if lead in ("synth_lead", "synth_pad", "arpeggiator"):
        return "synthwave", "synth lead: synthwave"
    if lead == "rhodes":
        return "lofi_hiphop", "electric piano lead: lo-fi"
    return "piano_neoclassical", "instrumental: starting from the solo-piano sound"


def choose_genre(plan: Plan, brief: str, control_genre: Optional[str]) -> tuple[str, str, str]:
    """(preset id, provenance source, reason)."""
    if control_genre:
        if not genres.exists(control_genre):
            raise ValueError(f"unknown genre '{control_genre}'")
        return control_genre, "you", "you picked the style"
    if plan.genre and genres.exists(plan.genre) and _source(plan, "genre") in ("you", "suggested", None):
        src = _source(plan, "genre") or "suggested"
        reason = plan.provenance["genre"].reason if "genre" in plan.provenance else "the planner picked this style"
        return plan.genre, src, reason
    lang = plan.voices.language if plan.voice_mode == "sung" and _voice_part_chosen(plan, "language") else None
    hit = genres.pick(brief, language=lang, voice=plan.voice_mode if chosen(plan, "voice_mode") else None)
    if hit:                        # a voice the person chose still wins; the blueprint adapts the form to it
        return hit[0], "suggested", f"you wrote '{hit[1]}'"
    rec = genres.for_recipe(plan.recipe_id)
    if rec and _source(plan, "recipe_id") == "you":
        return rec, "you", "the sound you picked"
    pid, why = default_genre(plan)
    return pid, "rule", why


def _supports_from(preset: dict, lead: str, voice_mode: str) -> list[dict]:
    out = []
    for i in preset["supports"]:
        if i == lead or (i == "choir" and voice_mode == "instrumental"):
            continue
        out.append({"instrument": i, "role": inst_db.default_role(i), "presence": "gentle"})
    return out[:5]


def apply_genre(plan: Plan, preset_id: str, source: str, reason: str) -> Plan:
    """A song-pipeline plan with the preset filling every field nobody chose."""
    p = genres.get(preset_id)
    d = plan.model_dump(mode="json")
    prov = {k: v.model_dump() for k, v in plan.provenance.items()}
    why = f"{p['name']} style"

    def fill(field: str, value) -> None:
        d[field] = value
        prov[field] = {"source": "recipe", "reason": why}

    d["pipeline"] = "song"
    d["genre"] = preset_id
    prov["genre"] = {"source": source, "reason": reason}
    if _source(plan, "recipe_id") != "you":       # an old recipe nobody picked has no say in a styled song
        d["recipe_id"] = None
        prov.pop("recipe_id", None)
    voice = d["voice_mode"]
    if not chosen(plan, "voice_mode"):
        voice = p["voice"]
        fill("voice_mode", voice)
    if not chosen(plan, "lead"):
        lead = p["lead"]
        if voice == "instrumental" and lead == "choir":
            lead = next(i for i in p["supports"] if i != "choir")
        fill("lead", {"instrument": lead, "style": d["lead"]["style"]})
    elif not inst_db.can_lead(d["lead"]["instrument"]) and _source(plan, "lead") != "you":
        # the brief named only a rhythm or bass sound ("a lofi beat"): the style's melodic lead takes over and the
        # named sound joins the supports
        old = d["lead"]["instrument"]
        d["supports"] = [{"instrument": old, "role": inst_db.default_role(old), "presence": "gentle"}] + [
            s for s in d["supports"] if s["instrument"] not in (old, p["lead"])]
        d["lead"] = {"instrument": p["lead"], "style": d["lead"]["style"]}
        prov["lead"] = {"source": "recipe", "reason": f"{inst_db.display_name(old)} cannot carry a melody; "
                                                      f"{p['name']} lead"}
    if not chosen(plan, "supports"):
        fill("supports", _supports_from(p, d["lead"]["instrument"], voice))
    else:
        d["supports"] = [s for s in d["supports"] if s["instrument"] != d["lead"]["instrument"]]
        # the rule planner tops up a short list from the old recipe; the style's own bed replaces those
        m = re.search(r"added ([\w, ]+?) from the recipe", prov.get("supports", {}).get("reason", ""))
        if m:
            filled = {x.strip() for x in m.group(1).split(",")}
            d["supports"] = [s for s in d["supports"] if s["instrument"] not in filled]
            prov["supports"]["reason"] = prov["supports"]["reason"][:m.start()].rstrip("; ")
        if len(d["supports"]) < 2:              # the person named one or two instruments: the style adds its bed
            have = {d["lead"]["instrument"]} | {s["instrument"] for s in d["supports"]}
            extra = [s for s in _supports_from(p, d["lead"]["instrument"], voice) if s["instrument"] not in have]
            if extra:
                added = extra[: 3 - len(d["supports"])]
                d["supports"] = d["supports"] + added
                old = prov.get("supports", {}).get("reason", "")
                prov["supports"] = {"source": prov.get("supports", {}).get("source", "suggested"),
                                    "reason": (old + "; " if old else "") + f"{p['name']} adds "
                                              + ", ".join(inst_db.display_name(x["instrument"]) for x in added)}
    pace_why = (plan.provenance.get("pace").reason if plan.provenance.get("pace") else "")
    if not chosen(plan, "pace"):
        fill("pace", {"bucket": bucket_for_bpm(p["bpm_default"]), "bpm": p["bpm_default"]})
    elif "BPM" not in pace_why and bucket_for_bpm(p["bpm_default"]) == d["pace"]["bucket"]:
        d["pace"] = {"bucket": d["pace"]["bucket"], "bpm": p["bpm_default"]}   # a pace word, the style's own tempo
    if not chosen(plan, "key"):
        fill("key", p["key"])
    if not chosen(plan, "meter"):
        fill("meter", p["meter"])
    if not chosen(plan, "feeling") or not d["feeling"]:
        fill("feeling", list(p["moods"])[:3])
    if not chosen(plan, "form"):
        fill("form", p["form"])
    v = dict(d["voices"])
    if voice == "sung":
        if p["singer"] != "auto" and (not _voice_part_chosen(plan, "singer") or v.get("singer") == "auto"):
            v["singer"] = p["singer"]
        if not _voice_part_chosen(plan, "language") and p["languages"]:
            v["language"] = p["languages"][0]
    elif voice == "wordless":
        if v.get("background", "none") == "none":
            v["background"] = "choir"
    else:
        v = {"singer": "auto", "background": "none", "language": "en"}
    d["voices"] = v
    if voice != "sung":
        d["lyrics"] = {"policy": "none", "text": None, "topic": None}
    elif d["lyrics"]["policy"] == "none":
        d["lyrics"] = {"policy": "write", "text": None, "topic": d["lyrics"].get("topic")}
    d["provenance"] = prov
    new = Plan.model_validate(d)
    # duration: the person's or the brief's length wins, otherwise the blueprint's natural length
    if not chosen(new, "duration_s"):
        bp = blueprint_for(new, auto_length=True)
        new = new.model_copy(update={"duration_s": max(10, min(240, bp.target_s))})
        new = new.with_provenance("duration_s", "rule", f"the natural length of this {p['name'].lower()} form")
    return new


def to_song_plan(plan: Plan, brief: str, control_genre: Optional[str] = None) -> Plan:
    pid, src, why = choose_genre(plan, brief, control_genre)
    return apply_genre(plan, pid, src, why)


# --------------------------------------------------------------------------------------- blueprints
_KIND_OF_TAG = [
    (r"pre[\s-]?chorus|build|lift", "pre_chorus"), (r"final\s+chorus|chorus|hook|mukhda|refrain|matla|drop", "chorus"),
    (r"verse|antara|sher", "verse"), (r"bridge|breakdown", "bridge"), (r"intro|prelude|alaap|aalap", "intro"),
    (r"outro|ending|coda|fade", "outro"), (r"solo", "solo"), (r"interlude|instrumental|break", "interlude"),
]


def kind_of_tag(tag: str) -> str:
    low = tag.lower()
    for pat, kind in _KIND_OF_TAG:
        if re.search(pat, low):
            return kind
    return "verse"


def frame_exact_lyrics(text: str) -> tuple[str, list[int]]:
    """The person's words with section tags: [Verse]/[Chorus] where they wrote none, plus an [Intro] before and an
    [Outro] after when their sheet has none. Only tag lines are added; every word line stays exactly as written.
    Returns (sheet, indices of inserted tag lines)."""
    tagged, inserted = compiler.insert_tag_lines(text)
    lines = tagged.split("\n")
    tags = [i for i, ln in enumerate(lines) if compiler._TAG_LINE.match(ln)]
    first_tag = lines[tags[0]].strip("[] ").lower() if tags else ""
    last_tag = lines[tags[-1]].strip("[] ").lower() if tags else ""
    if not re.match(r"(intro|prelude|alaap|aalap)", first_tag):
        lines = ["[Intro]", ""] + lines
        inserted = [0] + [i + 2 for i in inserted]
    if not re.match(r"(outro|ending|coda|fade)", last_tag):
        lines = lines + ["", "[Outro]"]
        inserted = inserted + [len(lines) - 1]
    return "\n".join(lines), inserted


def blueprint_from_lyrics(text: str, *, bpm: int, meter: str, target_s: Optional[int], lead: str,
                          supports: list[dict], hints: dict) -> song_blueprint.Blueprint:
    """A blueprint that follows the person's own tagged lyrics (their words decide the structure). With no target
    length, the length is what the words need at this tempo."""
    tagged, _ = frame_exact_lyrics(text)
    parsed = lyric_craft.parse_tagged(tagged)
    bar_s = song_blueprint.bar_seconds(bpm, meter)
    energy_of = {"intro": 1, "verse": 2, "pre_chorus": 3, "chorus": 4, "bridge": 2, "solo": 4, "interlude": 3,
                 "outro": 1}
    raw = []
    for tag, lines in parsed:
        kind = kind_of_tag(tag or "Verse")
        bars = len(lines) * 2 + song_blueprint.SECTION_BREATH_BARS if lines else 4
        raw.append((tag or "Verse", kind, len(lines), bars))
    est = sum(b for *_, b in raw) * bar_s
    if target_s is None:
        target_s = int(round(min(song_blueprint.MAX_TOTAL_S, max(song_blueprint.MIN_TOTAL_S, est))))
    scale = target_s / est if est else 1.0
    chorus_idx = [i for i, r in enumerate(raw) if r[1] == "chorus"]
    last = chorus_idx[-1] if len(chorus_idx) > 1 else None
    sections, prev = [], set()
    present = {lead} | {s["instrument"] for s in supports}
    for i, (tag, kind, n, bars) in enumerate(raw):
        final = i == last
        energy = 5 if final else energy_of.get(kind, 2)
        playing = song_blueprint._playing(energy, lead, supports, "sung")
        sh = song_blueprint.style_hint(kind, tag, final, hints, "sung", present)
        playing += [m for m in sorted(inst_db.mentioned(sh) & present) if m not in playing]
        entering = [x for x in playing if x not in prev and i > 0]
        sections.append(song_blueprint.Section(
            kind=kind, name=tag, tag=tag, lyric=n > 0, lines=n, bars=bars, seconds=round(bars * bar_s * scale, 1),
            energy=energy, hint=song_blueprint._hint(kind, tag, final, hints,
                                                    [e for e in entering if e not in inst_db.mentioned(sh)], "sung",
                                                    present),
            playing=playing, entering=entering, final=final, style_hint=sh))
        prev = set(playing)
    ratio = est / target_s if target_s else 1
    fit = "tight" if ratio > 1.1 else ("roomy" if ratio < 0.85 else "ok")
    changes = []
    if fit == "tight":
        changes.append(f"your words need about {round(est)} s at {bpm} BPM but the length is {target_s} s: "
                       "singing may feel rushed")
    elif fit == "roomy":
        changes.append(f"your words fill about {round(est)} s of {target_s} s: expect longer instrumental passages")
    return song_blueprint.Blueprint(form="your_lyrics", bpm=bpm, meter=meter, bar_s=round(bar_s, 3),
                                    target_s=target_s, estimated_s=round(est, 1), sections=sections, lyric_slots=[],
                                    changes=changes, fit=fit)


def blueprint_for(plan: Plan, *, auto_length: bool = False, lead: Optional[str] = None,
                  supports: Optional[list[dict]] = None) -> song_blueprint.Blueprint:
    """The plan's blueprint. `lead`/`supports` override the plan's own (the compiler passes what really plays after
    choir and avoid rules)."""
    preset = genres.get(plan.genre) if plan.genre else None
    hints = (preset or {}).get("hints", {})
    supports = supports if supports is not None else [s.model_dump() for s in plan.supports]
    lead = lead or plan.lead.instrument
    target = None if auto_length else plan.duration_s
    if plan.voice_mode == "sung" and plan.lyrics.policy == "exact" and (plan.lyrics.text or "").strip():
        return blueprint_from_lyrics(plan.lyrics.text, bpm=plan.pace.bpm, meter=plan.meter,
                                     target_s=target, lead=lead, supports=supports, hints=hints)
    lyr = (preset or {}).get("lyrics", {})
    return song_blueprint.build(form=plan.form or (preset or {}).get("form"), voice_mode=plan.voice_mode,
                                bpm=plan.pace.bpm, meter=plan.meter, target_s=target, lead=lead,
                                supports=supports, hints=hints, lines_per_verse=lyr.get("lines_per_verse", 4))
