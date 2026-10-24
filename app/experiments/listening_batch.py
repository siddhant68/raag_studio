"""Old-versus-new listening batch: the same briefs through the classic app and the song pipeline, rated blind.

    cd app
    .venv/bin/python -m experiments.listening_batch prepare --out ../runs/_listening/b1              # no GPU
    .venv/bin/python -m experiments.listening_batch prepare --out ../runs/_listening/b2 --conditions old,new,new_lm
    .venv/bin/python -m experiments.listening_batch render ../runs/_listening/b1                    # Mac, asks first
    .venv/bin/python -m experiments.listening_batch reveal ../runs/_listening/b1                    # after rating

What differs between conditions is the pipeline and the engine profile; the brief, the controls (voice, length,
singer, language, the exact lyrics of sung briefs) and the seed are the same for every condition of a trial. Plans
come from the Basic planner so the batch is deterministic and sends nothing anywhere; "Write for me" lyrics are not
part of it (test those in the app).

Conditions:
  old         the app before the song pipeline: classic template compiler, shift 1.0 (instruments it did not know
              are left out, as it would have done)
  new         song pipeline (style preset, song map, tagged lyrics), turbo, shift 3.0
  new_shift1  song pipeline with shift 1.0 (separates the effect of the prompts from the effect of shift)
  new_lm      song pipeline, shift 3.0, 5Hz LM (needs `python3 scripts/fetch_models.py lm`)
  new_xl      song pipeline, XL turbo (needs `python3 scripts/fetch_models.py xl`)
  new_xl_lm   both

Folder (must not exist before `prepare`):
  manifest.json           briefs, conditions, seeds, app commit; no labels
  requests/T01_A.json     one engine request per trial and label
  key/key.json            label -> condition. Do not open it before you have rated everything.
  sheet/sheet.csv         what you fill in: rating 1-5, favourite, notes
  outputs/T01_A/          run_takes output (native FLAC, request, result, engine log)
  listening/T01_A.mp3     loudness-matched copies (-16 LUFS) with neutral names: listen to these

Nothing here judges the music. Technical checks only show whether a file is broken.
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_APP = Path(__file__).resolve().parents[1]
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from backend import compiler, song_compiler, song_plan  # noqa: E402
from backend.media import tool  # noqa: E402
from backend.plan_schema import CLASSIC_INSTRUMENT_IDS, Plan  # noqa: E402
from backend.planner_base import Controls  # noqa: E402
from backend.planner_rules import BasicPlanner  # noqa: E402

ROOT = _APP.parent
BRIEFS = Path(__file__).with_name("listening_briefs.json")
TOOLS = Path(os.environ.get("RAAG_TOOLS_DIR", ROOT.parent / "tools"))
ACE_PYTHON = TOOLS / "acestep-venv/bin/python"
ACE_SOURCE = TOOLS / "ace-step-1.5"
RUN_TAKES = _APP / "engine" / "run_takes.py"
LABELS = "ABCDEFGH"
CONDITIONS = {
    "old": ("classic", "classic"),
    "new": ("song", "shift3"),
    "new_shift1": ("song", "classic"),
    "new_lm": ("song", "lm"),
    "new_xl": ("song", "xl"),
    "new_xl_lm": ("song", "xl_lm"),
}
DEFAULT_CONDITIONS = ("old", "new")
SHEET_FIELDS = ["trial", "brief_id", "brief", "label", "file", "rating_1_to_5", "favourite_x", "melody_1_to_5",
                "singing_1_to_5", "arrangement_1_to_5", "notes"]


# ------------------------------------------------------------------------------------------------ plans
def load_briefs(path: Path = BRIEFS, only: Optional[list[str]] = None) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    briefs = data["briefs"]
    if only:
        unknown = set(only) - {b["id"] for b in briefs}
        if unknown:
            raise SystemExit(f"unknown brief ids: {sorted(unknown)}")
        briefs = [b for b in briefs if b["id"] in only]
    for b in briefs:
        b["lyrics_text"] = lyrics_of(b, path.parent)
    return briefs


def lyrics_of(b: dict, base: Path) -> Optional[str]:
    if b.get("lyrics"):
        return b["lyrics"]
    if b.get("lyrics_from_recipe"):
        return compiler.load_recipe(b["lyrics_from_recipe"])["example_lyrics"]
    if b.get("lyrics_file"):
        return (base / b["lyrics_file"]).resolve().read_text(encoding="utf-8").strip()
    return None


def controls_for(b: dict) -> Controls:
    c = {"voice": b["voice"], "duration_s": b["duration_s"], "takes": 1}
    for k in ("singer", "language"):
        if b.get(k):
            c[k] = b[k]
    if b.get("lyrics_text"):
        c["lyrics_text"] = b["lyrics_text"]
    return Controls(**c)


def to_classic(plan: Plan) -> Plan:
    """What the app made before the song pipeline: no style, only the 15 instruments it knew."""
    if plan.pipeline == "classic":
        return plan
    d = plan.model_dump(mode="json")
    rec = compiler.load_recipe(d.get("recipe_id") or "r1_flute_focus")
    lead = d["lead"]["instrument"]
    if lead not in CLASSIC_INSTRUMENT_IDS:
        lead = rec["plan_defaults"]["lead"]["instrument"]
    d["lead"] = {"instrument": lead, "style": d["lead"]["style"]}
    d["supports"] = [s for s in d["supports"] if s["instrument"] in CLASSIC_INSTRUMENT_IDS and s["instrument"] != lead]
    d.update(pipeline="classic", genre=None, form=None, meter="4/4")
    for k in ("genre", "form", "meter"):
        d["provenance"].pop(k, None)
    return Plan.model_validate(d)


def plan_for(b: dict, condition: str) -> Plan:
    pipeline, _ = CONDITIONS[condition]
    plan = BasicPlanner().plan(b["brief"], controls_for(b)).plan
    if pipeline == "classic":
        return to_classic(plan)
    return song_plan.to_song_plan(plan, b["brief"])


def request_for(plan: Plan, condition: str, seed: int, trial: str) -> dict:
    _, profile = CONDITIONS[condition]
    compiled = song_compiler.compile_any(plan, engine_profile=profile)
    req = compiler.to_engine_request(compiled, [seed], audio_format="flac", meta={"batch_trial": trial})
    block = song_compiler.model_block(compiled)
    if block:
        req["model"] = block
    return req


def engine_validator():
    """run_takes.validate_request plus the known ACE param names (from the ACE source when present)."""
    spec = importlib.util.spec_from_file_location("run_takes_batch", RUN_TAKES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if (ACE_SOURCE / "acestep/inference.py").is_file():
        known = mod.generation_param_fields(ACE_SOURCE)
    else:
        known = set(compiler.ENGINE_DEFAULTS)
    return mod, known


def git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ------------------------------------------------------------------------------------------------ prepare
def prepare(out: Path, conditions: list[str], seeds: int, only: Optional[list[str]], rng_seed: int) -> dict:
    if out.exists():
        raise SystemExit(f"{out} already exists; batches are never overwritten")
    for c in conditions:
        if c not in CONDITIONS:
            raise SystemExit(f"unknown condition {c}; choose from {list(CONDITIONS)}")
    if len(set(conditions)) != len(conditions) or not 2 <= len(conditions) <= len(LABELS):
        raise SystemExit("give 2 to 8 different conditions")
    briefs = load_briefs(only=only)
    rng = random.Random(rng_seed)
    mod, known = engine_validator()
    for d in ("requests", "key", "sheet", "outputs", "listening"):
        (out / d).mkdir(parents=True)
    key: dict[str, dict] = {}
    rows, problems = [], []
    n = 0
    for b in briefs:
        plans = {c: plan_for(b, c) for c in conditions}
        for _ in range(seeds):
            n += 1
            trial = f"T{n:02d}"
            seed = rng.randrange(2**31)
            order = list(conditions)
            rng.shuffle(order)
            key[trial] = {"brief_id": b["id"], "seed": seed, "labels": {}}
            for label, cond in zip(LABELS, order):
                req = request_for(plans[cond], cond, seed, trial)
                bad = mod.validate_request(req, known)
                if bad:
                    problems.append(f"{trial}_{label} ({cond}): {bad}")
                name = f"{trial}_{label}"
                (out / "requests" / f"{name}.json").write_text(json.dumps(req, indent=2, ensure_ascii=False))
                key[trial]["labels"][label] = {"condition": cond, "pipeline": CONDITIONS[cond][0],
                                               "engine_profile": CONDITIONS[cond][1],
                                               "genre": plans[cond].genre}
                rows.append({"trial": trial, "brief_id": b["id"], "brief": b["brief"], "label": label,
                             "file": f"listening/{name}.mp3"})
    if problems:
        shutil.rmtree(out)
        raise SystemExit("requests failed the engine validator (nothing written):\n" + "\n".join(problems))
    (out / "key" / "key.json").write_text(json.dumps(key, indent=2))
    with open(out / "sheet" / "sheet.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in SHEET_FIELDS})
    (out / "sheet" / "HOW_TO_RATE.md").write_text(HOW_TO_RATE)
    manifest = {"schema": "raag-listening-batch/1", "created_at": datetime.now(timezone.utc).isoformat(),
                "app_commit": git_commit(), "conditions": conditions, "seeds_per_brief": seeds,
                "rng_seed": rng_seed, "renders": len(rows),
                "briefs": [{k: v for k, v in b.items() if k != "lyrics_text"} for b in briefs]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


HOW_TO_RATE = """# How to rate

1. Listen to `listening/T01_A.mp3`, `T01_B.mp3`, ... trial by trial. Every take in a trial had the same brief,
   length and seed; only the app's way of asking the model differs. The files are loudness-matched.
2. In `sheet.csv` give each take a `rating_1_to_5` (5 = I would keep this), put `x` in `favourite_x` for the
   best take of each trial, and, if you like, rate melody, singing (sung trials) and arrangement.
3. Do not open `key/key.json` until every row is rated. Then run
   `.venv/bin/python -m experiments.listening_batch reveal <batch folder>`.

Ratings are your taste; nothing in the app pretends to measure it.
"""


# ------------------------------------------------------------------------------------------------ render
def preflight() -> dict:
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "preflight.py"), "--json"], capture_output=True,
                         text=True, timeout=180)
    try:
        return json.loads(out.stdout)
    except ValueError:
        return {"error": out.stderr.strip() or "preflight gave no JSON"}


def preview(src: Path, dst: Path) -> None:
    subprocess.run([tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-b:a", "192k", str(dst)], check=True)


def render(batch: Path, yes: bool) -> int:
    reqs = sorted((batch / "requests").glob("T*_*.json"))
    todo = [r for r in reqs if not (batch / "outputs" / r.stem).is_dir()]
    if not todo:
        print("Everything in this batch is already rendered.")
        return 0
    needs = set()
    for r in todo:
        model = json.loads(r.read_text()).get("model") or {}
        needs.add(model.get("dit", song_compiler.DIT_TURBO))
        if model.get("lm"):
            needs.add(model["lm"]["name"])
    pf = preflight()
    print(f"{len(todo)} takes to render (about {len(todo) * 40 // 60 + 1} min on the M5 Pro). Models: {sorted(needs)}")
    if "error" in pf:
        print("Preflight failed:", pf["error"])
        return 2
    vq = (pf.get("video_queue") or {}).get("state")
    blockers = []
    if pf.get("mps") is False or (isinstance(pf.get("mps"), dict) and not pf["mps"].get("available", True)):
        blockers.append("Apple GPU (MPS) not available")
    if vq == "busy":
        blockers.append("the ComfyUI video queue is busy; wait for it to finish")
    for m in needs:
        d = ACE_SOURCE / "checkpoints" / m
        if not ((d / "config.json").is_file() and any(d.glob("*.safetensors"))):
            blockers.append(f"{m} is not installed (python3 scripts/fetch_models.py)")
    if blockers:
        print("Not rendering:\n  - " + "\n  - ".join(blockers))
        return 2
    if not yes and input("Render now? These count against your render ledger. [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled; nothing rendered.")
        return 1
    log = []
    for r in todo:
        part = batch / "outputs" / f"{r.stem}.partial"
        started = time.time()
        proc = subprocess.run([str(ACE_PYTHON), str(RUN_TAKES), str(r), str(part)], capture_output=True, text=True)
        events = [json.loads(ln) for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        err = next((e for e in events if e.get("event") == "error"), None)
        if proc.returncode != 0 or err:
            print(f"{r.stem}: FAILED ({(err or {}).get('message', proc.returncode)}); see {part}/engine.log")
            log.append({"take": r.stem, "ok": False, "error": (err or {}).get("message")})
            continue
        final = batch / "outputs" / r.stem
        part.rename(final)
        take = next(final.glob("take_*.*"))
        preview(take, batch / "listening" / f"{r.stem}.mp3")
        log.append({"take": r.stem, "ok": True, "wall_s": round(time.time() - started, 1), "file": take.name})
        print(f"{r.stem}: done in {time.time() - started:.0f} s")
    rows = json.loads((batch / "renders.json").read_text()) if (batch / "renders.json").exists() else []
    (batch / "renders.json").write_text(json.dumps(rows + log, indent=2))
    ok = sum(1 for x in log if x["ok"])
    print(f"Rendered {ok} of {len(todo)}. Add a row for these {ok} takes to the render ledger in STATUS.md.")
    print(f"Listen in {batch / 'listening'} and fill {batch / 'sheet' / 'sheet.csv'}.")
    return 0 if ok == len(todo) else 3


# ------------------------------------------------------------------------------------------------ reveal
def _num(v: str) -> Optional[float]:
    try:
        x = float(v)
        return x if 1 <= x <= 5 else None
    except (TypeError, ValueError):
        return None


def reveal(batch: Path) -> str:
    key = json.loads((batch / "key" / "key.json").read_text())
    with open(batch / "sheet" / "sheet.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    stats: dict[str, dict] = {}
    per_brief: dict[str, dict[str, list[float]]] = {}
    rated_trials = set()
    for r in rows:
        info = key.get(r["trial"], {}).get("labels", {}).get(r["label"])
        if not info:
            continue
        cond = info["condition"]
        s = stats.setdefault(cond, {"ratings": [], "favourites": 0, "melody": [], "singing": [], "arrangement": []})
        rating = _num(r.get("rating_1_to_5"))
        if rating is not None:
            s["ratings"].append(rating)
            rated_trials.add(r["trial"])
            per_brief.setdefault(r["brief_id"], {}).setdefault(cond, []).append(rating)
        if (r.get("favourite_x") or "").strip().lower() in ("x", "yes", "1", "y"):
            s["favourites"] += 1
        for f in ("melody", "singing", "arrangement"):
            v = _num(r.get(f"{f}_1_to_5"))
            if v is not None:
                s[f].append(v)

    def mean(xs):
        return f"{sum(xs) / len(xs):.2f} ({len(xs)})" if xs else "-"

    conds = sorted(stats)
    lines = ["# Listening batch results", "",
             f"Batch: `{batch.name}`. Rated trials: {len(rated_trials)} of {len(key)}. "
             "Numbers are your ratings (mean, with how many ratings in brackets). They are taste, not measurements.", "",
             "| Condition | Rating | Favourite | Melody | Singing | Arrangement |", "| --- | --- | --- | --- | --- | --- |"]
    for c in conds:
        s = stats[c]
        lines.append(f"| {c} | {mean(s['ratings'])} | {s['favourites']} | {mean(s['melody'])} | {mean(s['singing'])} | "
                     f"{mean(s['arrangement'])} |")
    lines += ["", "| Brief | " + " | ".join(conds) + " |", "| --- | " + " | ".join("---" for _ in conds) + " |"]
    for bid, by in per_brief.items():
        lines.append(f"| {bid} | " + " | ".join(mean(by.get(c, [])) for c in conds) + " |")
    if len(rated_trials) < 8:
        lines += ["", "Fewer than 8 rated trials: treat any difference as a hint, not a result."]
    text = "\n".join(lines) + "\n"
    (batch / "results.md").write_text(text)
    return text


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="write requests, the blind key and the rating sheet (no GPU)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--conditions", default=",".join(DEFAULT_CONDITIONS))
    p.add_argument("--seeds", type=int, default=1, help="seeds (trials) per brief, 1-4")
    p.add_argument("--only", default="", help="comma-separated brief ids")
    p.add_argument("--rng-seed", type=int, default=2410)
    r = sub.add_parser("render", help="render missing takes on this Mac (asks first)")
    r.add_argument("batch", type=Path)
    r.add_argument("--yes", action="store_true")
    v = sub.add_parser("reveal", help="unblind the filled sheet")
    v.add_argument("batch", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        if not 1 <= a.seeds <= 4:
            raise SystemExit("--seeds must be 1 to 4")
        m = prepare(a.out, [c.strip() for c in a.conditions.split(",") if c.strip()], a.seeds,
                    [x.strip() for x in a.only.split(",") if x.strip()] or None, a.rng_seed)
        print(f"Prepared {m['renders']} requests in {a.out} ({len(m['briefs'])} briefs x {a.seeds} seed(s) x "
              f"{len(m['conditions'])} conditions). Next: render on the Mac.")
        return 0
    if a.cmd == "render":
        return render(a.batch, a.yes)
    print(reveal(a.batch))
    return 0


if __name__ == "__main__":
    sys.exit(main())
