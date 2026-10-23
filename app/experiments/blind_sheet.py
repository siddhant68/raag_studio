"""M6 experiment harness, part 1: arms -> engine request files + a randomised blind listening sheet.

    cd app && python -m experiments.blind_sheet create E1 --plans plans.json --seeds 11,12 \
        --out ../runs/_experiments/e1 --rng-seed 7

NO GPU is used and nothing is rendered here. The harness only (a) writes one engine request file per
(arm, plan), identical in every parameter except the tested one, with identical seeds across arms, and
(b) writes a blind sheet whose arm labels (A/B/...) are shuffled per trial, deterministically for a given
`--rng-seed`. The label -> arm key lives in a separate folder (`key/key.json`) and never appears in `sheet/`.

Also here (pure Python, `wave` module on 16-bit PCM, no numpy): the E4 splice helper and the mechanical
checks for E3 (duration) and E5 (not silent).

Honest limits (see README.md):
  * E1 and E2 requests are text2music and pass the M0 engine validator today. E3, E4 and E5 need
    `task_type` cover/repaint and `src_audio`, which `app/engine/run_takes.py` rejects until M0's contract is
    extended; the request files are written anyway and flagged `engine_ready: false` in experiment.json.
  * Listening is done by the user. Nothing here judges audio quality.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import random
import shutil
import sys
import wave
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

_APP = Path(__file__).resolve().parents[1]
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from backend import compiler                    # noqa: E402
from backend.plan_schema import Plan            # noqa: E402

LABELS = "ABCDEFGH"
MAX_SEEDS = 8                                    # engine contract: 1..8 seeds per request
AUDIO_EXTS = (".flac", ".wav")
SHEET_VERSION = "raag-blind-sheet/1"
KEY_VERSION = "raag-blind-key/1"


# ---------------------------------------------------------------------------------------------
# Experiment definitions (PRD v2 section 12 / M6)
# ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Arm:
    id: str
    params: dict                                  # the ONLY params that differ between arms
    control: bool = False                         # the incumbent; never "promoted"
    description: str = ""


@dataclass(frozen=True)
class Experiment:
    id: str
    title: str
    arms: tuple[Arm, ...]
    primary: dict                                 # {"kind": "preference"} | {"kind": "question", "name": ...}
    questions: tuple[str, ...] = ()               # yes/no questions answered per arm label
    needs_source: bool = False                    # E2..E5 compare against / work from a source take
    needs_source_texts: bool = False              # E5: caption/lyrics the source was made from
    needs_span: bool = False                      # E4
    engine_ready: bool = True                     # accepted by run_takes.validate_request as it is today
    audio_format: Optional[str] = None
    human_part: str = ""
    mechanical_part: str = ""


EXPERIMENTS: dict[str, Experiment] = {e.id: e for e in (
    Experiment(
        "E1", "shift 3.0 vs 1.0",
        (Arm("shift_1.0", {"shift": 1.0}, control=True, description="accepted recipes (shift 1.0)"),
         Arm("shift_3.0", {"shift": 3.0}, description="upstream recommendation")),
        primary={"kind": "preference"},
        human_part="blind preference, A or B",
        mechanical_part="arms differ only in `shift`; identical seeds"),
    Experiment(
        "E2", "retake_variance 0.1 / 0.3 / 0.5 from a favourite seed",
        (Arm("retake_variance_0.1", {"retake_variance": 0.1}),
         Arm("retake_variance_0.3", {"retake_variance": 0.3}),
         Arm("retake_variance_0.5", {"retake_variance": 0.5})),
        primary={"kind": "question", "name": "similar_but_different"},
        questions=("similar_but_different",), needs_source=True,
        human_part="'similar but different?' yes/no per arm, heard against the favourite take",
        mechanical_part="records params; no crash. Seeds = the favourite seed(s); one shared retake_seed"),
    Experiment(
        "E3", "cover re-arrangement, strength 0.5 vs 0.8, new caption",
        (Arm("cover_strength_0.5", {"audio_cover_strength": 0.5}),
         Arm("cover_strength_0.8", {"audio_cover_strength": 0.8})),
        primary={"kind": "preference"}, questions=("keeps_structure",), needs_source=True, engine_ready=False,
        human_part="keeps structure? (yes/no per arm) and which sounds better (preference)",
        mechanical_part="output duration equals the source +/- 0.05 s (duration_matches)"),
    Experiment(
        "E4", "repaint a span with local splice",
        (Arm("repaint_splice", {}),),
        primary={"kind": "question", "name": "melody_voice_retained"},
        questions=("melody_voice_retained",), needs_source=True, needs_span=True, engine_ready=False,
        audio_format="wav",
        human_part="melody and voice retained? yes/no, heard against the original take",
        mechanical_part="max abs sample difference outside [start - xfade, end + xfade] == 0; seam click metric"),
    Experiment(
        "E5", "flow_edit_morph over cover",
        (Arm("cover", {"flow_edit_morph": False}, control=True, description="cover only"),
         Arm("flow_edit_morph", {"flow_edit_morph": True})),
        primary={"kind": "question", "name": "follows_the_words"},
        questions=("follows_the_words",), needs_source=True, needs_source_texts=True, engine_ready=False,
        human_part="follows the new words? yes/no per arm",
        mechanical_part="runs without silence collapse: peak above -40 dBFS (peak_dbfs)"),
)}


# ---------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------
@dataclass
class PlanSpec:
    plan: Plan
    source_audio: Optional[str] = None            # path of the favourite/source take (E2-E5)
    source_duration_s: Optional[float] = None     # E3-E5: duration is locked to the source
    span: Optional[tuple[float, float]] = None    # E4: (start_s, end_s)
    xfade_s: float = 0.05                         # E4 splice crossfade, recorded in the key
    source_caption: Optional[str] = None          # E5
    source_lyrics: Optional[str] = None           # E5


def load_specs(items: Sequence[Any]) -> list[PlanSpec]:
    """Accepts brief strings (planned by the Basic planner), plan dicts, or {"plan"|"brief": ..., source...} dicts."""
    from backend.planner_rules import BasicPlanner
    out: list[PlanSpec] = []
    for it in items:
        if isinstance(it, PlanSpec):
            out.append(it)
            continue
        extra: dict[str, Any] = {}
        if isinstance(it, str):
            plan = BasicPlanner().plan(it).plan
        elif isinstance(it, dict) and "plan" in it:
            plan, extra = Plan.model_validate(it["plan"]), it
        elif isinstance(it, dict) and "brief" in it and "voice_mode" not in it:
            plan, extra = BasicPlanner().plan(it["brief"]).plan, it
        elif isinstance(it, dict):
            plan = Plan.model_validate(it)
        else:
            raise ValueError(f"cannot read a plan spec from {type(it).__name__}")
        span = extra.get("span")
        out.append(PlanSpec(plan=plan, source_audio=extra.get("source_audio"),
                            source_duration_s=extra.get("source_duration_s"),
                            span=tuple(span) if span else None, xfade_s=float(extra.get("xfade_s", 0.05)),
                            source_caption=extra.get("source_caption"), source_lyrics=extra.get("source_lyrics")))
    return out


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------------------------
# Engine requests
# ---------------------------------------------------------------------------------------------
def _common_params(exp: Experiment, spec: PlanSpec, retake_seed: int) -> dict:
    """Parameters shared by EVERY arm of one plan (the tested parameter is never in here)."""
    if exp.id == "E2":
        return {"retake_seed": retake_seed}
    if exp.id == "E3":
        return {"task_type": "cover", "src_audio": spec.source_audio,
                "duration": spec.source_duration_s or spec.plan.duration_s}
    if exp.id == "E4":
        start, end = spec.span
        return {"task_type": "repaint", "src_audio": spec.source_audio,
                "duration": spec.source_duration_s or spec.plan.duration_s,
                "repainting_start": float(start), "repainting_end": float(end), "chunk_mask_mode": "explicit",
                "repaint_wav_crossfade_sec": 0.0}            # the crossfade is done by splice_repaint()
    if exp.id == "E5":
        return {"task_type": "cover", "src_audio": spec.source_audio,
                "duration": spec.source_duration_s or spec.plan.duration_s,
                "flow_edit_source_caption": spec.source_caption, "flow_edit_source_lyrics": spec.source_lyrics or ""}
    return {}


def build_requests(exp: Experiment, specs: Sequence[PlanSpec], seeds: Sequence[int], *,
                   retake_seed: int = 0, compiled: Optional[Sequence[dict]] = None) -> dict[str, list[dict]]:
    """{arm_id: [engine request per plan]}. Same compiled plan, same seeds; only `arm.params` differ."""
    seeds = list(seeds)
    comp = list(compiled) if compiled is not None else [compiler.compile(s.plan) for s in specs]
    out: dict[str, list[dict]] = {a.id: [] for a in exp.arms}
    for i, (spec, c) in enumerate(zip(specs, comp)):
        base = _common_params(exp, spec, retake_seed)
        for arm in exp.arms:
            c2 = copy.deepcopy(c)
            c2["params"].update(base)
            c2["params"].update(arm.params)
            meta = {"experiment": exp.id, "arm": arm.id, "plan_index": i, "tested_params": sorted(arm.params)}
            out[arm.id].append(compiler.to_engine_request(c2, seeds, audio_format=exp.audio_format, meta=meta))
    return out


def _check_inputs(exp: Experiment, specs: Sequence[PlanSpec], seeds: Sequence[int]) -> None:
    if not specs:
        raise ValueError("at least one plan is required")
    seeds = list(seeds)
    if not 1 <= len(seeds) <= MAX_SEEDS or len(set(seeds)) != len(seeds):
        raise ValueError(f"seeds must be 1 to {MAX_SEEDS} distinct integers per experiment "
                         "(use more plans for more trials)")
    if not all(isinstance(s, int) and not isinstance(s, bool) and 0 <= s < 2**31 for s in seeds):
        raise ValueError("seeds must be integers in [0, 2^31)")
    for i, s in enumerate(specs):
        if exp.needs_source and not s.source_audio:
            raise ValueError(f"{exp.id} needs source_audio (the favourite/source take) for plan {i + 1}")
        if exp.needs_span:
            if not s.span or not (0 <= s.span[0] < s.span[1]):
                raise ValueError(f"{exp.id} needs span=(start_s, end_s) with 0 <= start < end for plan {i + 1}")
            if s.xfade_s < 0:
                raise ValueError("xfade_s must be >= 0")
        if exp.needs_source_texts and not (s.source_caption and s.source_caption.strip()):
            raise ValueError(f"{exp.id} needs source_caption (what the source take was made from) for plan {i + 1}")


# ---------------------------------------------------------------------------------------------
# Blind assignment
# ---------------------------------------------------------------------------------------------
def assign_labels(arm_ids: Sequence[str], n_trials: int, rng_seed: int, exp_id: str) -> list[dict[str, str]]:
    """Per trial {label: arm_id}. Deterministic in (rng_seed, exp_id). For two arms the A/B orientation is
    balanced (counts differ by at most one) so a rater who always picks 'A' cannot favour an arm."""
    rng = random.Random(f"{SHEET_VERSION}:{exp_id}:{rng_seed}:assign")
    arms = list(arm_ids)
    if len(arms) == 1:
        return [{"A": arms[0]} for _ in range(n_trials)]
    if len(arms) == 2:
        flips = [i % 2 == 1 for i in range(n_trials)]
        rng.shuffle(flips)
        return [({"A": arms[1], "B": arms[0]} if f else {"A": arms[0], "B": arms[1]}) for f in flips]
    out = []
    for _ in range(n_trials):
        perm = arms[:]
        rng.shuffle(perm)
        out.append({LABELS[i]: a for i, a in enumerate(perm)})
    return out


# ---------------------------------------------------------------------------------------------
# Create an experiment folder
# ---------------------------------------------------------------------------------------------
def create_experiment(exp_id: str, plans: Sequence[Any], seeds: Sequence[int], out_dir: str | Path, *,
                      rng_seed: int = 0, retake_seed: Optional[int] = None) -> dict:
    """Write requests/, sheet/ and key/ into the FRESH folder `out_dir`. Returns a summary dict."""
    if exp_id not in EXPERIMENTS:
        raise ValueError(f"unknown experiment {exp_id!r}; choose from {sorted(EXPERIMENTS)}")
    exp = EXPERIMENTS[exp_id]
    out = Path(out_dir)
    if out.exists():
        raise FileExistsError(f"{out} already exists; experiments are written to a fresh folder")
    if not out.parent.is_dir():
        raise FileNotFoundError(f"parent folder {out.parent} does not exist")
    specs = load_specs(plans)
    seeds = [int(s) for s in seeds]
    _check_inputs(exp, specs, seeds)
    if retake_seed is None:
        retake_seed = (int(rng_seed) * 2654435761 + 12345) % (2**31)
        if retake_seed in seeds:
            retake_seed = (retake_seed + 1) % (2**31)
    compiled = [compiler.compile(s.plan) for s in specs]
    requests = build_requests(exp, specs, seeds, retake_seed=retake_seed, compiled=compiled)

    out.mkdir()
    for sub in ("requests", "sheet", "key"):
        (out / sub).mkdir()
    req_index: dict[str, list[str]] = {}
    for arm in exp.arms:
        (out / "requests" / arm.id).mkdir()
        req_index[arm.id] = []
        for i, req in enumerate(requests[arm.id]):
            rel = f"requests/{arm.id}/plan{i + 1:02d}.json"
            (out / rel).write_text(_dump(req), encoding="utf-8")
            req_index[arm.id].append(rel)

    # trials: every (plan, seed) pair; order shuffled, ids T01.. are position in the shuffled order
    pairs = [(pi, si) for pi in range(len(specs)) for si in range(len(seeds))]
    random.Random(f"{SHEET_VERSION}:{exp.id}:{rng_seed}:order").shuffle(pairs)
    labels = assign_labels([a.id for a in exp.arms], len(pairs), rng_seed, exp.id)
    trials: dict[str, dict] = {}
    for n, ((pi, si), lab) in enumerate(zip(pairs, labels), start=1):
        tid = f"T{n:02d}"
        trials[tid] = {
            "plan_index": pi, "seed": seeds[si], "take_index": si + 1, "labels": lab,
            "requests": {arm_id: req_index[arm_id][pi] for arm_id in lab.values()},
            "source_audio": specs[pi].source_audio,
        }
    sheet_id = _sha(_dump({"exp": exp.id, "rng": rng_seed, "pairs": pairs, "labels": labels}).encode())[:12]

    key = {"version": KEY_VERSION, "sheet_id": sheet_id, "experiment": exp.id, "title": exp.title,
           "rng_seed": rng_seed, "primary": exp.primary, "questions": list(exp.questions),
           "arms": {a.id: {"params": a.params, "control": a.control, "description": a.description}
                    for a in exp.arms},
           "trials": trials}
    (out / "key" / "key.json").write_text(_dump(key), encoding="utf-8")

    sheet_rows = []
    for tid, t in trials.items():
        spec = specs[t["plan_index"]]
        row = {"trial": tid, "brief": spec.plan.brief,
               "files": {lab: f"listening/{tid}_{lab}" for lab in t["labels"]}}   # file stem; extension is whatever was staged
        if exp.needs_source:
            row["reference"] = f"listening/{tid}_ref"
        sheet_rows.append(row)
    sheet = {"version": SHEET_VERSION, "sheet_id": sheet_id, "experiment": exp.id, "title": f"Blind listening sheet {exp.id}",
             "labels": list(labels[0].keys()), "primary": exp.primary, "questions": list(exp.questions),
             "instructions": _instructions(exp), "trials": sheet_rows}
    (out / "sheet" / "sheet.json").write_text(_dump(sheet), encoding="utf-8")
    _write_sheet_csv(out / "sheet" / "sheet.csv", exp, sheet)

    manifest = {
        "experiment": exp.id, "title": exp.title, "engine_ready": exp.engine_ready,
        "engine_notes": ("" if exp.engine_ready else
                         "These requests use task_type cover/repaint and src_audio. app/engine/run_takes.py "
                         "(contract raag-engine-request/1) rejects them until M0 is extended. Nothing here has run."),
        "seeds": seeds, "retake_seed": retake_seed if exp.id == "E2" else None,
        "plans": [{"index": i, "brief": s.plan.brief, "plan_sha256": compiled[i]["plan_sha256"],
                   "caption": compiled[i]["caption"]} for i, s in enumerate(specs)],
        "tested_params": sorted({k for a in exp.arms for k in a.params}),
        "requests": req_index,
        "suggested_out_dirs": {rel: rel.replace("requests/", "outputs/").replace(".json", ".partial")
                               for rels in req_index.values() for rel in rels},
        "human_part": exp.human_part, "mechanical_part": exp.mechanical_part,
        "e4_splice": ([{"plan_index": i, "start_s": s.span[0], "end_s": s.span[1], "xfade_s": s.xfade_s}
                       for i, s in enumerate(specs)] if exp.needs_span else None),
        "note": "arm names live in key/ and in this file; the rater only sees sheet/ and listening/",
    }
    (out / "experiment.json").write_text(_dump(manifest), encoding="utf-8")
    return {"dir": str(out), "experiment": exp.id, "trials": len(trials), "sheet_id": sheet_id,
            "requests": sum(len(v) for v in req_index.values()), "engine_ready": exp.engine_ready}


def _instructions(exp: Experiment) -> str:
    lines = ["Listen to each trial's files. Do not look in key/ until you are finished."]
    if exp.primary["kind"] == "preference":
        lines.append("Fill `choice` with the label you prefer (A, B, ...), or `tie` if you cannot tell. "
                     "Leave it blank to skip a trial.")
    for q in exp.questions:
        lines.append(f"Answer `{q}` with yes or no for each label (columns {q}_A, {q}_B, ...).")
    if exp.needs_source:
        lines.append("A `reference` file is the source/favourite take for comparison.")
    return " ".join(lines)


def _write_sheet_csv(path: Path, exp: Experiment, sheet: dict) -> None:
    labels = sheet["labels"]
    cols = ["trial", "brief"] + (["reference"] if exp.needs_source else []) + labels
    if exp.primary["kind"] == "preference":
        cols.append("choice")
    for q in exp.questions:
        cols += [f"{q}_{lab}" for lab in labels]
    cols.append("notes")
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in sheet["trials"]:
            row = {"trial": r["trial"], "brief": r["brief"], **r["files"]}
            if exp.needs_source:
                row["reference"] = r["reference"]
            w.writerow(row)


def stage_audio(exp_dir: str | Path, outputs_root: str | Path) -> dict:
    """Copy rendered takes into neutral names under listening/ (T01_A.flac ...). Returns {copied, missing}.

    Expects each request rendered to `<outputs_root>/<arm>/planNN.partial` (or without .partial) by
    run_takes.py. The key decides which file becomes A or B; the rater never sees arm names.
    """
    exp_dir, outputs_root = Path(exp_dir), Path(outputs_root)
    key = json.loads((exp_dir / "key" / "key.json").read_text("utf-8"))
    listening = exp_dir / "listening"
    listening.mkdir(exist_ok=True)
    copied, missing = [], []
    for tid, t in key["trials"].items():
        for lab, arm_id in t["labels"].items():
            req_rel = t["requests"][arm_id]                    # requests/<arm>/planNN.json
            stem = Path(req_rel).stem
            found = None
            for d in (outputs_root / arm_id / f"{stem}.partial", outputs_root / arm_id / stem):
                if d.is_dir():
                    hits = sorted(p for p in d.glob(f"take_*_s{t['seed']}.*") if p.suffix in AUDIO_EXTS)
                    if hits:
                        found = hits[0]
                        break
            if found is None:
                missing.append(f"{tid}_{lab}")
                continue
            shutil.copyfile(found, listening / f"{tid}_{lab}{found.suffix}")
            copied.append(f"{tid}_{lab}{found.suffix}")
        src = t.get("source_audio")
        if src and Path(src).is_file():
            shutil.copyfile(src, listening / f"{tid}_ref{Path(src).suffix}")
            copied.append(f"{tid}_ref{Path(src).suffix}")
    return {"copied": copied, "missing": missing}


# ---------------------------------------------------------------------------------------------
# Audio helpers: 16-bit PCM wav via the `wave` module (no numpy in the app venv)
# ---------------------------------------------------------------------------------------------
@dataclass
class Pcm:
    sample_rate: int
    channels: int
    samples: array = field(default_factory=lambda: array("h"))     # interleaved int16

    @property
    def frames(self) -> int:
        return len(self.samples) // self.channels

    @property
    def duration_s(self) -> float:
        return self.frames / self.sample_rate


def read_wav(path: str | Path) -> Pcm:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError("only 16-bit PCM wav is supported")
        data = array("h")
        data.frombytes(w.readframes(w.getnframes()))
        if sys.byteorder == "big":
            data.byteswap()
        return Pcm(w.getframerate(), w.getnchannels(), data)


def write_wav(path: str | Path, pcm: Pcm) -> None:
    data = array("h", pcm.samples)
    if sys.byteorder == "big":
        data.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(pcm.channels)
        w.setsampwidth(2)
        w.setframerate(pcm.sample_rate)
        w.writeframes(data.tobytes())


def _clamp16(v: float) -> int:
    return max(-32768, min(32767, int(round(v))))


def splice_repaint(original: Pcm, repainted: Pcm, start_s: float, end_s: float, xfade_s: float) -> Pcm:
    """Put `repainted[start:end]` into `original` with linear crossfades of `xfade_s` on both seams.

    Frames before (start - xfade) and from (end + xfade) on are copied from `original` untouched, so they are
    bit-identical. Inside [start, end) the repainted audio is used; in the two crossfade zones
    [start - xfade, start) and [end, end + xfade) the two are blended. `repainted` must have the same sample
    rate and channel count and at least as many frames as `original` (extra frames are ignored).
    """
    if (original.sample_rate, original.channels) != (repainted.sample_rate, repainted.channels):
        raise ValueError("sample rate and channel count must match")
    if repainted.frames < original.frames:
        raise ValueError("repainted audio is shorter than the original")
    if not 0 <= start_s < end_s:
        raise ValueError("need 0 <= start < end")
    if xfade_s < 0:
        raise ValueError("xfade must be >= 0")
    sr, ch, n = original.sample_rate, original.channels, original.frames
    s, e, x = round(start_s * sr), round(end_s * sr), round(xfade_s * sr)
    if s >= n:
        raise ValueError("span starts after the end of the audio")
    e = min(e, n)
    out = array("h", original.samples)                          # copy: everything outside the edit stays original
    o, r = original.samples, repainted.samples
    lo_fade, hi_fade = max(0, s - x), min(n, e + x)
    for i in range(lo_fade, hi_fade):
        if i < s:
            w = (i - (s - x) + 1) / (x + 1)                    # 0 -> 1 into the repaint
        elif i < e:
            w = 1.0
        else:
            w = 1.0 - (i - e + 1) / (x + 1)                    # 1 -> 0 back to the original
        base = i * ch
        for c in range(ch):
            out[base + c] = _clamp16(o[base + c] * (1.0 - w) + r[base + c] * w)
    return Pcm(sr, ch, out)


def max_abs_diff_outside(original: Pcm, spliced: Pcm, start_s: float, end_s: float, xfade_s: float) -> int:
    """Largest |original - spliced| over all frames outside [start - xfade, end + xfade]. Must be 0 (E4)."""
    if (original.sample_rate, original.channels, original.frames) != (spliced.sample_rate, spliced.channels,
                                                                       spliced.frames):
        raise ValueError("original and spliced must have the same format and length")
    sr, ch, n = original.sample_rate, original.channels, original.frames
    lo = max(0, round(start_s * sr) - round(xfade_s * sr))
    hi = min(n, min(round(end_s * sr), n) + round(xfade_s * sr))
    worst = 0
    for i in range(0, lo * ch):
        worst = max(worst, abs(original.samples[i] - spliced.samples[i]))
    for i in range(hi * ch, n * ch):
        worst = max(worst, abs(original.samples[i] - spliced.samples[i]))
    return worst


def seam_click_metric(pcm: Pcm, start_s: float, end_s: float, window_s: float = 0.02) -> int:
    """Largest sample-to-sample jump (any channel) within `window_s` of either seam. Compare against a threshold."""
    sr, ch, n = pcm.sample_rate, pcm.channels, pcm.frames
    w = max(2, round(window_s * sr))
    worst = 0
    for seam in (round(start_s * sr), min(round(end_s * sr), n)):
        for i in range(max(1, seam - w), min(n, seam + w)):
            for c in range(ch):
                worst = max(worst, abs(pcm.samples[i * ch + c] - pcm.samples[(i - 1) * ch + c]))
    return worst


def duration_matches(source_s: float, output_s: float, tol_s: float = 0.05) -> bool:
    """E3 mechanical check: cover output duration equals the source within 0.05 s."""
    return abs(source_s - output_s) <= tol_s + 1e-9      # epsilon: 150.0 vs 149.95 is a pass


def peak_dbfs(pcm: Pcm) -> float:
    """Peak level in dBFS of 16-bit audio (-inf for digital silence)."""
    peak = max((abs(v) for v in pcm.samples), default=0)
    return -math.inf if peak == 0 else 20.0 * math.log10(peak / 32768.0)


def not_silent(pcm: Pcm, floor_dbfs: float = -40.0) -> bool:
    """E5 mechanical check: peak above -40 dBFS."""
    return peak_dbfs(pcm) > floor_dbfs


# ---------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m experiments.blind_sheet", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create", help="write request files and a blind sheet into a fresh folder")
    c.add_argument("experiment", choices=sorted(EXPERIMENTS))
    c.add_argument("--plans", required=True, help="JSON file: list of briefs, plan dicts, or {plan|brief, source_audio, ...}")
    c.add_argument("--seeds", required=True, help="comma-separated seeds, e.g. 101,102")
    c.add_argument("--out", required=True, help="fresh folder to create")
    c.add_argument("--rng-seed", type=int, default=0, help="makes the blind assignment reproducible")
    c.add_argument("--retake-seed", type=int, default=None, help="E2 only")
    s = sub.add_parser("stage", help="copy rendered takes into neutral listening/ names")
    s.add_argument("exp_dir")
    s.add_argument("outputs_root")
    sub.add_parser("list", help="list experiments")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for e in EXPERIMENTS.values():
            print(f"{e.id}  {e.title}  arms={[x.id for x in e.arms]}  engine_ready={e.engine_ready}")
        return 0
    if a.cmd == "stage":
        print(json.dumps(stage_audio(a.exp_dir, a.outputs_root), indent=2))
        return 0
    items = json.loads(Path(a.plans).read_text("utf-8"))
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()]
    print(json.dumps(create_experiment(a.experiment, items, seeds, a.out, rng_seed=a.rng_seed,
                                       retake_seed=a.retake_seed), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
