"""Song blueprint: the section-by-section plan between a brief and the renderer.

A blueprint is an ordered list of sections. Each section knows its musical job (intro, verse, chorus, ...), how many
lyric lines it carries or how many bars it lasts, an estimated duration at the plan's tempo, an energy level (1-5),
which instruments play and which ones enter, and a short hint for the lyric tag ("[Chorus - soaring strings]").

Forms come from songwriting practice and ACE-Step's own tag set: verse/pre-chorus/chorus pop form, the Hindi film
mukhda/antara form, ghazal couplets, qawwali call-and-response, rap verses and hooks, EDM build/drop, and the raag
alaap/jor/gat/jhala arc for instrumentals. The blueprint is deterministic: the same plan gives the same sections.

Fitting to a length: optional sections are dropped in a fixed order when the song is too long for the requested
duration, instrumental sections stretch when it is too short, and verse lines shrink (never below two) as a last
resort. Every change is reported, nothing is silently cut.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import instruments as inst_db

METER_BEATS = {"4/4": 4, "3/4": 3, "6/8": 3, "2/4": 2}       # quarter-note beats per bar (6/8 = 3 quarters)
ACE_TIMESIG = {"4/4": "4", "3/4": "3", "6/8": "6", "2/4": "2"}
MIN_TOTAL_S, MAX_TOTAL_S = 30, 240
SECTION_BREATH_BARS = 1                                       # a breath/fill between sung sections


@dataclass
class Step:
    """One section of a form template."""
    kind: str                     # intro verse pre_chorus chorus bridge interlude break solo build drop outro
    name: str                     # display name ("Verse 1", "Mukhda", "Alaap")
    tag: str                      # ACE-Step tag ("Verse", "Chorus", "Intro", ...)
    lines: int = 0                # lyric lines (0 = instrumental section)
    bars: int = 0                 # bars for instrumental sections
    energy: int = 2
    drop_rank: int = 0            # 0 = always kept; lower numbers are dropped first
    uid: Optional[str] = None     # identity of a lyric section the songwriter writes ("verse_1", "chorus")
    repeat_of: Optional[str] = None   # uid of the section whose words this one repeats
    bars_per_line: Optional[float] = None


def S(kind, name, tag, **kw) -> Step:
    return Step(kind=kind, name=name, tag=tag, **kw)


V = -1    # placeholder: "lines_per_verse from the preset"

FORMS: dict[str, list[Step]] = {
    "pop_song": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("pre_chorus", "Pre-Chorus", "Pre-Chorus", lines=2, energy=3, uid="pre_chorus", drop_rank=3),
        S("chorus", "Chorus", "Chorus", lines=4, energy=4, uid="chorus"),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=4),
        S("pre_chorus", "Pre-Chorus", "Pre-Chorus", repeat_of="pre_chorus", energy=3, drop_rank=1),
        S("chorus", "Chorus", "Chorus", repeat_of="chorus", energy=4, drop_rank=4),
        S("bridge", "Bridge", "Bridge", lines=4, energy=2, uid="bridge", drop_rank=2),
        S("chorus", "Final Chorus", "Chorus", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
    "mukhda_antara": [
        S("intro", "Prelude", "Intro", bars=8, energy=2),
        S("chorus", "Mukhda", "Chorus", lines=4, energy=3, uid="chorus"),
        S("interlude", "Interlude", "Interlude", bars=8, energy=3, drop_rank=2),
        S("verse", "Antara 1", "Verse 1", lines=V, energy=3, uid="verse_1"),
        S("chorus", "Mukhda", "Chorus", repeat_of="chorus", energy=4),
        S("interlude", "Interlude 2", "Interlude", bars=8, energy=3, drop_rank=1),
        S("verse", "Antara 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=4),
        S("chorus", "Mukhda", "Chorus", repeat_of="chorus", energy=5, drop_rank=4),
        S("outro", "Outro", "Outro", bars=4, energy=2),
    ],
    "ghazal": [
        S("intro", "Aalap", "Intro", bars=8, energy=1),
        S("chorus", "Matla", "Chorus", lines=2, energy=2, uid="chorus"),
        S("verse", "Sher 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("chorus", "Matla", "Chorus", repeat_of="chorus", energy=3),
        S("interlude", "Interlude", "Interlude", bars=4, energy=2, drop_rank=2),
        S("verse", "Sher 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=3),
        S("chorus", "Matla", "Chorus", repeat_of="chorus", energy=3, drop_rank=3),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
    "qawwali": [
        S("intro", "Aalap", "Intro", bars=8, energy=1),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("chorus", "Chorus", "Chorus", lines=4, energy=3, uid="chorus"),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=3),
        S("chorus", "Chorus", "Chorus", repeat_of="chorus", energy=4, drop_rank=3),
        S("build", "Build", "Build", bars=8, energy=4, drop_rank=2),
        S("chorus", "Final Chorus", "Chorus", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=4, energy=3),
    ],
    "rap_song": [
        S("intro", "Intro", "Intro", bars=4, energy=2),
        S("chorus", "Hook", "Chorus", lines=4, energy=4, uid="chorus"),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=3, uid="verse_1", bars_per_line=1),
        S("chorus", "Hook", "Chorus", repeat_of="chorus", energy=4),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", bars_per_line=1, drop_rank=3),
        S("chorus", "Hook", "Chorus", repeat_of="chorus", energy=5, drop_rank=3),
        S("outro", "Outro", "Outro", bars=4, energy=2),
    ],
    "dance_song": [
        S("intro", "Intro", "Intro", bars=8, energy=2),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=3, uid="verse_1"),
        S("pre_chorus", "Pre-Chorus", "Pre-Chorus", lines=2, energy=4, uid="pre_chorus", drop_rank=2),
        S("chorus", "Chorus", "Chorus", lines=4, energy=5, uid="chorus"),
        S("drop", "Drop", "Drop", bars=8, energy=5, drop_rank=3),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=4),
        S("pre_chorus", "Pre-Chorus", "Pre-Chorus", repeat_of="pre_chorus", energy=4, drop_rank=1),
        S("chorus", "Chorus", "Chorus", repeat_of="chorus", energy=5, drop_rank=4),
        S("bridge", "Breakdown", "Breakdown", bars=8, energy=2, drop_rank=2),
        S("chorus", "Final Chorus", "Chorus", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=8, energy=3),
    ],
    "edm": [
        S("intro", "Intro", "Intro", bars=8, energy=2),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("build", "Build", "Build", lines=2, energy=4, uid="pre_chorus"),
        S("chorus", "Drop", "Drop", lines=4, energy=5, uid="chorus"),
        S("bridge", "Breakdown", "Breakdown", lines=4, energy=2, uid="bridge", drop_rank=2),
        S("build", "Build", "Build", repeat_of="pre_chorus", energy=4, drop_rank=1),
        S("chorus", "Final Drop", "Drop", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=8, energy=2),
    ],
    "folk_song": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("chorus", "Chorus", "Chorus", lines=4, energy=3, uid="chorus"),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=3),
        S("chorus", "Chorus", "Chorus", repeat_of="chorus", energy=4, drop_rank=3),
        S("break", "Instrumental Break", "Instrumental", bars=8, energy=3, drop_rank=2),
        S("chorus", "Final Chorus", "Chorus", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=4, energy=2),
    ],
    "jazz": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Verse 1", "Verse 1", lines=V, energy=2, uid="verse_1"),
        S("chorus", "Chorus", "Chorus", lines=4, energy=3, uid="chorus"),
        S("solo", "Solo", "Solo", bars=8, energy=4, drop_rank=2),
        S("verse", "Verse 2", "Verse 2", lines=V, energy=3, uid="verse_2", drop_rank=3),
        S("chorus", "Final Chorus", "Chorus", repeat_of="chorus", energy=4),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
    # --- instrumental and wordless forms --------------------------------------------------------------
    "raag": [
        S("intro", "Alaap", "Intro", bars=8, energy=1),
        S("verse", "Jor", "Verse", bars=8, energy=2, drop_rank=3),
        S("chorus", "Gat", "Chorus", bars=16, energy=3),
        S("solo", "Taans", "Solo", bars=8, energy=4, drop_rank=2),
        S("build", "Jhala", "Build", bars=8, energy=5, drop_rank=1),
        S("outro", "Cadence", "Outro", bars=4, energy=2),
    ],
    "instrumental_song": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Theme A", "Verse", bars=8, energy=2),
        S("chorus", "Theme B", "Chorus", bars=8, energy=4),
        S("verse", "Theme A again", "Verse", bars=8, energy=3, drop_rank=3),
        S("solo", "Solo", "Solo", bars=8, energy=4, drop_rank=2),
        S("chorus", "Final Theme B", "Chorus", bars=8, energy=5),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
    "cinematic": [
        S("intro", "Opening", "Intro", bars=8, energy=1),
        S("verse", "Theme", "Verse", bars=8, energy=2),
        S("build", "Build", "Build", bars=8, energy=3, drop_rank=2),
        S("chorus", "Climax", "Chorus", bars=8, energy=5),
        S("outro", "Resolution", "Outro", bars=8, energy=2),
    ],
    "ambient": [
        S("intro", "Opening", "Intro", bars=8, energy=1),
        S("verse", "Drift", "Verse", bars=16, energy=2),
        S("chorus", "Swell", "Chorus", bars=8, energy=3),
        S("verse", "Drift II", "Verse", bars=16, energy=2, drop_rank=2),
        S("outro", "Fade", "Outro", bars=8, energy=1),
    ],
    "loop_beat": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Loop A", "Verse", bars=16, energy=2),
        S("chorus", "Loop B", "Chorus", bars=16, energy=3),
        S("verse", "Loop A again", "Verse", bars=16, energy=2, drop_rank=2),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
    "wordless_song": [
        S("intro", "Intro", "Intro", bars=4, energy=1),
        S("verse", "Verse", "Verse", bars=8, energy=2),
        S("chorus", "Chorus", "Chorus", lines=4, energy=4, uid="chorus"),
        S("verse", "Verse 2", "Verse", bars=8, energy=3, drop_rank=3),
        S("bridge", "Bridge", "Bridge", bars=8, energy=2, drop_rank=2),
        S("chorus", "Chorus", "Chorus", repeat_of="chorus", energy=4, drop_rank=1),
        S("chorus", "Final Chorus", "Final Chorus", repeat_of="chorus", energy=5, drop_rank=5),
        S("outro", "Outro", "Outro", bars=4, energy=1),
    ],
}
SUNG_FORMS = {"pop_song", "mukhda_antara", "ghazal", "qawwali", "rap_song", "dance_song", "edm", "folk_song", "jazz"}
# When a sung form has to become instrumental or wordless, this is the form that takes its place.
NON_SUNG_FALLBACK = {"instrumental": "instrumental_song", "wordless": "wordless_song"}
SUNG_FALLBACK = "pop_song"


@dataclass
class Section:
    kind: str
    name: str
    tag: str
    lyric: bool
    lines: int
    bars: float
    seconds: float
    energy: int
    hint: str
    playing: list[str] = field(default_factory=list)
    entering: list[str] = field(default_factory=list)
    uid: Optional[str] = None
    repeat_of: Optional[str] = None
    final: bool = False
    style_hint: str = ""              # the style's own words for this section (without "X enters")


@dataclass
class Blueprint:
    form: str
    bpm: int
    meter: str
    bar_s: float
    target_s: int
    estimated_s: float
    sections: list[Section]
    lyric_slots: list[dict]           # the unique lyric sections the songwriter writes: {uid, name, lines}
    dropped: list[str] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    fit: str = "ok"                   # ok | tight | roomy

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        """One line such as 'Intro 8s · Verse 1 25s · Chorus 20s ...'."""
        return " · ".join(f"{s.name} {round(s.seconds)}s" for s in self.sections)


def bar_seconds(bpm: int, meter: str) -> float:
    return METER_BEATS.get(meter, 4) * 60.0 / max(30, bpm)


def form_for(form: Optional[str], voice_mode: str) -> str:
    """The form actually used for a voice mode (a sung form cannot carry an instrumental piece)."""
    if form not in FORMS:
        form = SUNG_FALLBACK if voice_mode == "sung" else NON_SUNG_FALLBACK.get(voice_mode, "instrumental_song")
    if voice_mode != "sung" and form in SUNG_FORMS:
        return NON_SUNG_FALLBACK.get(voice_mode, "instrumental_song")
    if voice_mode == "sung" and form not in SUNG_FORMS:
        return SUNG_FALLBACK
    return form


def _section_seconds(st: Step, lines: int, bar_s: float, default_bpl: float) -> tuple[float, float]:
    if lines > 0:
        bpl = st.bars_per_line or default_bpl
        bars = lines * bpl + SECTION_BREATH_BARS
    else:
        bars = float(st.bars)
    return bars, bars * bar_s


def _lines_of(st: Step, lines_per_verse: int, uid_lines: dict[str, int]) -> int:
    if st.repeat_of:
        return uid_lines.get(st.repeat_of, 0)
    if st.lines == V:
        return lines_per_verse
    return st.lines


def fit_form(form: str, *, bpm: int, meter: str = "4/4", target_s: Optional[int] = None, lines_per_verse: int = 4,
             bars_per_line: float = 2.0) -> tuple[list[tuple[Step, int, float]], dict]:
    """Choose the form's sections and line counts for a tempo and target length.

    Returns ([(step, lines, bars)], info) where info has target_s, dropped, changes, fit.
    """
    steps = [Step(**asdict(s)) for s in FORMS[form]]
    bar_s = bar_seconds(bpm, meter)
    dropped: list[str] = []
    changes: list[str] = []
    lpv = max(2, lines_per_verse)

    chorus_cap = [99]                       # lowered to 2 only when a very short length leaves no other choice

    def layout(active: list[Step], lpv_now: int) -> list[tuple[Step, int, float]]:
        uid_lines: dict[str, int] = {}
        out = []
        for st in active:
            n = _lines_of(st, lpv_now, uid_lines)
            if st.uid == "chorus":
                n = min(n, chorus_cap[0])
            if st.uid:
                uid_lines[st.uid] = n
            bars, _ = _section_seconds(st, n, bar_s, bars_per_line)
            out.append((st, n, bars))
        return out

    def total(lay) -> float:
        return sum(b for _, _, b in lay) * bar_s

    auto = target_s is None
    goal = float(target_s) if target_s else None

    def drop_through(rank: int) -> list[Step]:
        """The form without every optional section of rank <= `rank` (a dropped source takes its repeats along)."""
        gone_uids = {s.uid for s in steps if 0 < s.drop_rank <= rank and s.uid}
        return [s for s in steps if not (0 < s.drop_rank <= rank) and s.repeat_of not in gone_uids]

    def squeeze(lay):                       # intro/outro/interludes at half length, never below 2 bars
        return [(st, n, max(2.0, b / 2) if n == 0 else b) for st, n, b in lay]

    # 1. pick how much of the form to keep: the candidate closest to the goal, preferring more of the song.
    ranks = [0] + sorted({s.drop_rank for s in steps if s.drop_rank > 0})
    if auto:
        rank = next((r for r in ranks if total(layout(drop_through(r), lpv)) <= MAX_TOTAL_S), ranks[-1])
        active, squeezed = drop_through(rank), False
    else:
        best = None
        for r in ranks:
            for sq in (False, True):
                lay_c = layout(drop_through(r), lpv)
                lay_c = squeeze(lay_c) if sq else lay_c
                over = total(lay_c) / goal
                # within +-10% is ideal; otherwise distance from the goal, too long counts double (rushed words)
                miss = 0.0 if 0.9 <= over <= 1.1 else (over - 1.1) * 2 if over > 1.1 else 0.9 - over
                cand = (round(miss, 3), r, sq)
                if best is None or cand < best:
                    best = cand
        _, rank, squeezed = best
        active = drop_through(rank)
    dropped = [s.name for s in steps if s not in active]
    lay = layout(active, lpv)
    if squeezed:
        lay = squeeze(lay)
        changes.append("intro, outro and interludes shortened to fit the length")
    ceiling = MAX_TOTAL_S if auto else goal * 1.10
    # 2. still too long: shorter verses (never below 2 lines)
    while total(lay) > ceiling and lpv > 2 and any(s.lines == V for s in active):
        lpv -= 1
        # keep the (possibly shortened) instrumental bars; only the sung sections are re-measured
        lay = [(st, n, b if n == 0 else nb) for (st, _, b), (_, n, nb) in zip(lay, layout(active, lpv))]
        changes.append(f"verses shortened to {lpv} lines to fit the length")
    # 2b. a very short length: a two-line chorus
    if total(lay) > ceiling and any(st.uid == "chorus" and n > 2 for st, n, _ in lay):
        chorus_cap[0] = 2
        lay = [(st, n, b if n == 0 else nb) for (st, _, b), (_, n, nb) in zip(lay, layout(active, lpv))]
        changes.append("chorus shortened to 2 lines to fit the length")
    # 3. too short for a requested length: a break before the last chorus for songs, longer sections otherwise
    if goal is not None and total(lay) < goal * 0.9:
        sung = any(n > 0 for _, n, _ in lay)
        gap = goal - total(lay)
        if sung and gap > 8 * bar_s:
            last_chorus = max((i for i, (st, _, _) in enumerate(lay) if st.kind == "chorus"), default=len(lay) - 1)
            gap_bars = float(min(16, max(4, math.ceil(gap * 0.6 / bar_s))))
            brk = Step(kind="break", name="Instrumental Break", tag="Instrumental", bars=int(gap_bars), energy=3)
            lay.insert(last_chorus, (brk, 0, gap_bars))
            changes.append("an instrumental break was added before the last chorus to fill the length")
        if total(lay) < goal * 0.9:
            inst_bars = sum(b for _, n, b in lay if n == 0)
            if inst_bars:
                factor = min(2.0 if sung else 4.0, 1 + (goal - total(lay)) / (inst_bars * bar_s))
                lay = [(st, n, b * factor if n == 0 else b) for st, n, b in lay]
                changes.append("instrumental sections lengthened to fill the requested length")
    est = total(lay)
    if auto:
        target = int(round(min(MAX_TOTAL_S, max(MIN_TOTAL_S, est))))
    else:
        target = int(goal)
    ratio = est / target if target else 1.0
    fit = "tight" if ratio > 1.1 else ("roomy" if ratio < 0.85 else "ok")
    if fit == "tight":
        changes.append(f"the words need about {round(est)} s but the length is {target} s: singing may feel rushed")
    return lay, {"target_s": target, "estimated_s": round(est, 1), "dropped": dropped, "changes": changes,
                 "fit": fit, "bar_s": bar_s, "lines_per_verse": lpv, "chorus_lines": min(4, chorus_cap[0])}


# ---------------------------------------------------------------------------- arrangement over time
ROLE_ENTRY_ENERGY = {"drone": 1, "texture": 1, "harmony": 2, "answer": 2, "rhythm": 3, "lead": 2}


def _playing(energy: int, lead: str, supports: list[dict], voice_mode: str) -> list[str]:
    """Who plays at an energy level: drones/textures from the start, harmony next, rhythm from energy 3, all at 4+."""
    out = [lead] if lead else []
    for s in supports:
        need = ROLE_ENTRY_ENERGY.get(s.get("role", "texture"), 2)
        if s.get("presence") == "full":
            need -= 1
        if energy >= 4 or energy >= need:
            out.append(s["instrument"])
    return list(dict.fromkeys(out))


VOCAL_HINT = re.compile(r"\b(?:vocals?|voices?|choir|chorus|sung|singing|singer|harmonies|chant\w*|aalap|ad-libs?)\b",
                        re.I)


# Instrument words that stand for "any drums" or "any guitar": a hint naming them fits whichever kit or guitar plays.
_FAMILY_STANDINS = {"drum_kit": {"brushed_drums", "drum_machine", "light_percussion", "cajon", "taiko", "dhol"},
                    "acoustic_guitar": {"nylon_guitar", "electric_guitar"}, "bansuri": {"concert_flute"}}


def _fits(part: str, present: Optional[set]) -> bool:
    """A hint phrase that names an instrument fits only if that instrument (or a stand-in) is playing."""
    if present is None:
        return True
    for inst in inst_db.mentioned(part):
        if inst not in present and not (_FAMILY_STANDINS.get(inst, set()) & present):
            return False
    return True


def style_hint(kind: str, tag: str, final: bool, hints: dict, voice_mode: str = "sung",
               present: Optional[set] = None) -> str:
    """The style preset's words for a section, at most two short phrases, never naming an absent instrument."""
    base = ""
    if final and hints.get("final_chorus"):
        base = hints["final_chorus"]
    elif tag.lower() in hints:
        base = hints[tag.lower()]
    elif kind in hints:
        base = hints[kind]
    elif kind == "break":
        base = hints.get("solo") or hints.get("interlude") or ""
    elif kind == "interlude":
        base = hints.get("interlude") or hints.get("solo") or ""
    parts = [p.strip() for p in base.split(",") if p.strip()]
    if voice_mode == "instrumental":                  # a sung style's hints must not ask an instrumental for voices
        parts = [p for p in parts if not VOCAL_HINT.search(p)]
    parts = [p for p in parts if _fits(p, present)]
    return ", ".join(parts[:2])


def _hint(kind: str, tag: str, final: bool, hints: dict, entering: list[str], voice_mode: str = "sung",
          present: Optional[set] = None) -> str:
    """The tag modifier: the style's words, plus who enters when there is room ("soaring, strings enter")."""
    base = style_hint(kind, tag, final, hints, voice_mode, present)
    parts = [p for p in base.split(", ") if p]
    if entering and len(parts) < 2:
        names = [inst_db.display_name(i).lower() for i in entering if i in inst_db.INSTRUMENTS][:1]
        if names:
            parts.append(f"{names[0]} {'enter' if names[0].endswith('s') else 'enters'}")
    return ", ".join(parts)


def build(*, form: Optional[str], voice_mode: str, bpm: int, meter: str = "4/4", target_s: Optional[int] = None,
          lead: str, supports: list[dict], hints: Optional[dict] = None, lines_per_verse: int = 4,
          bars_per_line: float = 2.0) -> Blueprint:
    """Blueprint for a plan. `supports` are plan support dicts ({instrument, role, presence})."""
    hints = hints or {}
    form_used = form_for(form, voice_mode)
    lay, info = fit_form(form_used, bpm=bpm, meter=meter, target_s=target_s, lines_per_verse=lines_per_verse,
                         bars_per_line=bars_per_line)
    changes = list(info["changes"])
    if form and form_used != form:
        changes.insert(0, f"the {form.replace('_', ' ')} form needs sung words; using {form_used.replace('_', ' ')}")
    scale = info["target_s"] / info["estimated_s"] if info["estimated_s"] else 1.0
    chorus_idx = [i for i, (st, _, _) in enumerate(lay) if st.kind == "chorus"]
    last_chorus = chorus_idx[-1] if len(chorus_idx) > 1 else None
    sections: list[Section] = []
    prev: set[str] = set()
    present = {lead} | {s["instrument"] for s in supports}
    for i, (st, n, bars) in enumerate(lay):
        final = i == last_chorus
        energy = 5 if final else st.energy
        playing = _playing(energy, lead, supports, voice_mode)
        entering = [p for p in playing if p not in prev and i > 0]
        sections.append(Section(
            kind=st.kind, name=st.name, tag=st.tag, lyric=n > 0 and voice_mode != "instrumental", lines=n,
            bars=round(bars, 2), seconds=round(bars * info["bar_s"] * scale, 1), energy=energy,
            hint=_hint(st.kind, st.tag, final, hints, entering, voice_mode, present), playing=playing,
            entering=entering, uid=st.uid, repeat_of=st.repeat_of, final=final,
            style_hint=style_hint(st.kind, st.tag, final, hints, voice_mode, present)))
        prev = set(playing)
    slots = [{"uid": s.uid, "name": s.name, "kind": s.kind, "lines": s.lines}
             for s in sections if s.uid and s.lines > 0]
    return Blueprint(form=form_used, bpm=bpm, meter=meter, bar_s=round(info["bar_s"], 3), target_s=info["target_s"],
                     estimated_s=info["estimated_s"], sections=sections, lyric_slots=slots, dropped=info["dropped"],
                     changes=changes, fit=info["fit"])
