"""Showcase batch: a fixed set of briefs rendered once each through the song pipeline, published for listening.

    cd app
    .venv/bin/python -m experiments.showcase prepare            # plans, real Claude lyrics, requests, seeds (no GPU)
    .venv/bin/python -m experiments.showcase render             # on the Mac: checks resources, renders 12 takes
    .venv/bin/python -m experiments.showcase publish            # commit + push showcase/<id>/ (never to master)

Spec: experiments/showcase_diverse12.json. Working files and native renders: runs/_showcase/<id>/ (not committed).
Deliverables: showcase/<id>/ (committed): audio/NN_slug.mp3, takes/NN_slug/ (brief, plan, lyrics, songwriter
drafts and checks, caption, engine request, seed, profile, timing, technical checks), README.md, ratings.csv,
technical_summary.md and .json.

Rules this tool keeps:
  * one take per brief, rendered one after another; a failed take is recorded as failed, never retried and never
    replaced (no artistic retries, no extra takes);
  * the engine profile is fixed by the spec (shift3: turbo DiT, shift 3.0, no LM), nothing is downloaded;
  * before every take: Apple GPU present, disk free, the ComfyUI video queue idle, no other render running
    (the Raag Studio queue and any other run_takes.py process);
  * lyrics are written by the smart planner (the local `claude` CLI) with each supplied hook kept unchanged in
    every chorus; every raw draft, its line check and any revision note are saved;
  * the lyric sheet carries section names only (and, for the duet, who sings); musical direction stays in the
    caption;
  * listening copies are loudness-matched (EBU R128 -16 LUFS integrated, true peak at or below -1.5 dBTP) and
    checked for clipping; native FLACs stay in runs/;
  * tempo, meter, arrangement and vocal assignments are recorded as requested targets; nothing here claims the
    engine followed them. Musical judgments stay "pending" until someone listens.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

_APP = Path(__file__).resolve().parents[1]
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from backend import compiler, genres, media, song_compiler, song_plan  # noqa: E402
from backend import instruments as inst_db  # noqa: E402
from backend.plan_schema import Plan  # noqa: E402
from backend.planner_base import Controls  # noqa: E402
from backend.planner_rules import BasicPlanner  # noqa: E402

ROOT = _APP.parent
SPEC = Path(__file__).with_name("showcase_diverse12.json")
TOOLS = Path(os.environ.get("RAAG_TOOLS_DIR", ROOT.parent / "tools"))
ACE_PYTHON = TOOLS / "acestep-venv/bin/python"
ACE_SOURCE = TOOLS / "ace-step-1.5"
RUN_TAKES = _APP / "engine" / "run_takes.py"
FAKE_ENGINE = _APP / "engine" / "fake_engine.py"
TARGET_LUFS, TARGET_TP, MAX_COPY_TP = -16.0, -1.5, -1.0
RATING_FIELDS = ["take", "title", "file", "melody_1_to_5", "rhythm_1_to_5", "arrangement_1_to_5",
                 "vocal_delivery_1_to_5", "pronunciation_1_to_5", "lyric_fidelity_1_to_5", "overall_enjoyment_1_to_5",
                 "notes"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_spec(path: Path = SPEC) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def take_dir_name(t: dict) -> str:
    return f"{t['n']:02d}_{t['slug']}"


def paths(spec: dict, root: Path = ROOT) -> tuple[Path, Path]:
    """(runs folder, committed showcase folder) for a spec."""
    return root / "runs" / "_showcase" / spec["id"], root / "showcase" / spec["id"]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------------------------- plans
def plan_for_take(t: dict) -> Plan:
    """The song-pipeline plan for one spec entry: every value the brief states is set as the person's choice."""
    ctl = {"voice": t["voice"], "duration_s": t["duration_s"], "bpm": t["bpm"], "meter": t["meter"],
           "genre": t["genre"], "lead": t["lead"], "instruments": [s["instrument"] for s in t["supports"]],
           "takes": 1, "style": t.get("style")}
    for k in ("singer", "language", "background", "feeling", "fullness"):
        if t.get(k):
            ctl[k] = t[k]
    controls = Controls(**{k: v for k, v in ctl.items() if v is not None})
    plan = BasicPlanner().plan(t["brief"], controls).plan
    plan = song_plan.to_song_plan(plan, t["brief"], t["genre"])
    d = plan.model_dump(mode="json")
    why = "from the showcase brief"
    d["supports"] = [dict(s) for s in t["supports"]]
    d["flavour"] = t["flavour"]
    d["require_sections"] = list(t.get("require_sections", []))
    for f in ("supports", "flavour") + (("require_sections",) if t.get("require_sections") else ()):
        d["provenance"][f] = {"source": "you", "reason": why}
    if t["voice"] == "sung":
        d["lyrics"] = {"policy": "write", "text": None, "topic": t["theme"]}
        d["provenance"]["lyrics"] = {"source": "you", "reason": "theme from the showcase brief; hook supplied"}
    return Plan.model_validate(d)


def targets_markdown(t: dict, plan: Plan) -> str:
    sups = ", ".join(f"{inst_db.display_name(s['instrument'])} ({s['role']}, {s['presence']})" for s in t["supports"])
    lines = [f"# {t['n']:02d}. {t['title']}", "", "## Brief (as written)", "", t["brief"], "",
             "## Requested creative targets (not guaranteed by the engine)", ""]
    lines += [f"- {x}" for x in t.get("targets", [])]
    lines += ["", "## How the brief was set in the plan", "",
              f"- Voice: {t['voice']}" + (f", singer {t.get('singer')}, language {t.get('language')}"
                                          if t["voice"] == "sung" else ""),
              f"- Length: {t['duration_s']} s; tempo target {t['bpm']} BPM; meter {t['meter']}",
              f"- Style preset: {genres.get(t['genre'])['name']} (`{t['genre']}`), song form `{plan.form}`",
              f"- Lead: {inst_db.display_name(t['lead'])}; supports: {sups}",
              f"- Caption note (flavour): {t['flavour']}"]
    if t.get("hook"):
        lines += [f"- Hook (must appear unchanged in every chorus): {' / '.join(t['hook'])}",
                  f"- Theme given to the songwriter: {t['theme']}"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------------------------- lyrics
def write_lyrics(plan: Plan, t: dict, planner) -> tuple[Plan, dict]:
    """Real songwriting through the smart planner. Returns the plan with the lyric sheet and a full record."""
    bp = song_plan.blueprint_for(plan)
    calls_before = len(getattr(planner, "envelopes", []))
    started = time.time()
    song = planner.draft_song_lyrics(plan, bp, required_hook=t["hook"], tag_hints=False)
    record = {
        "provider": planner.name, "label": planner.label, "written_at": now(),
        "wall_s": round(time.time() - started, 1),
        # timing and cost of each songwriter call; model names stay in runs/ (see prepare), not in the published record
        "calls": [{k: v for k, v in c.items() if k != "models"}
                  for c in getattr(planner, "envelopes", [])[calls_before:]],
        "required_hook": t["hook"], "title": song.title, "hook": song.hook, "revised": song.revised,
        "notes": song.notes, "drafts": song.drafts, "final_check": song.review, "final_sections": song.written,
        "sheet": song.text,
    }
    lyr = plan.lyrics.model_copy(update={"text": song.text})
    plan = plan.model_copy(update={"lyrics": lyr}).with_provenance(
        "lyrics", "suggested", f"written by {planner.label} for this song's sections; hook supplied by you")
    return plan, record


def default_planner():
    from backend.providers.claude_cli import ClaudeCliPlanner
    return ClaudeCliPlanner(enabled=True, timeout_s=240)


# ---------------------------------------------------------------------------------------------- prepare
def engine_validator():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_takes_showcase", RUN_TAKES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    known = mod.generation_param_fields(ACE_SOURCE) if (ACE_SOURCE / "acestep/inference.py").is_file() \
        else set(compiler.ENGINE_DEFAULTS)
    return mod, known


def prepare(spec: dict, *, show_dir: Path, runs_dir: Path, planner=None, only: Optional[list[int]] = None,
            rewrite_lyrics: bool = False) -> dict:
    """Plans, lyrics (once; kept on later runs unless rewrite_lyrics), compiled requests and seeds per take."""
    mod, known = engine_validator()
    rng = random.Random(spec["rng_seed"])
    seeds = {t["n"]: rng.randrange(2**31) for t in spec["takes"]}           # fixed by the spec, not by the run order
    status = []
    for t in spec["takes"]:
        if only and t["n"] not in only:
            continue
        tdir = show_dir / "takes" / take_dir_name(t)
        take_file = tdir / "take.json"
        prev = json.loads(take_file.read_text()) if take_file.exists() else {}
        if prev.get("render", {}).get("status") in ("rendered", "failed"):
            status.append((t["n"], "kept (already rendered)"))
            continue
        plan = plan_for_take(t)
        songwriter_file = tdir / "songwriter.json"
        if t["voice"] == "sung":
            if songwriter_file.exists() and not rewrite_lyrics:
                record = json.loads(songwriter_file.read_text())
                plan = plan.model_copy(update={"lyrics": plan.lyrics.model_copy(update={"text": record["sheet"]})})
                plan = plan.with_provenance("lyrics", "suggested", f"written by {record['label']}; hook supplied by you")
            else:
                planner = planner or default_planner()
                calls_before = len(getattr(planner, "envelopes", []))
                plan, record = write_lyrics(plan, t, planner)
                write_json(songwriter_file, record)
                write_json(runs_dir / "songwriter_calls" / f"{take_dir_name(t)}.json",  # local only (runs/ is ignored)
                           getattr(planner, "envelopes", [])[calls_before:])
            (tdir / "lyrics.txt").write_text(record["sheet"] + "\n", encoding="utf-8")
        compiled = song_compiler.compile_song(plan, engine_profile=spec["profile"])
        seed = seeds[t["n"]]
        request = compiler.to_engine_request(compiled, [seed], audio_format="flac",
                                             meta={"showcase": spec["id"], "take": t["n"], "slug": t["slug"]})
        block = song_compiler.model_block(compiled)
        if block:
            request["model"] = block
        problems = mod.validate_request(request, known)
        if problems:
            raise SystemExit(f"take {t['n']}: request fails the engine validator: {problems}")
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / "brief.md").write_text(targets_markdown(t, plan), encoding="utf-8")
        write_json(tdir / "plan.json", plan.model_dump(mode="json"))
        (tdir / "caption.txt").write_text(compiled["caption"] + "\n", encoding="utf-8")
        write_json(tdir / "request.json", request)
        write_json(tdir / "compile_report.json", compiled["compile_report"])
        write_json(take_file, {
            "take": t["n"], "slug": t["slug"], "title": t["title"], "seed": seed,
            "engine_profile": spec["profile"], "profile_detail": song_compiler.ENGINE_PROFILES[spec["profile"]],
            "dit": compiled["dit_model"], "lm": compiled["lm_model"], "genre": plan.genre, "form": plan.form,
            "requested": {k: t.get(k) for k in ("duration_s", "bpm", "meter", "voice", "singer", "language")},
            "prepared_at": now(), "app_commit": git_commit(),
            "render": {"status": "not_rendered"},
            "listening": {"verdict": "pending"},
        })
        status.append((t["n"], "prepared"))
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_ratings(spec, show_dir)
    write_readme(spec, show_dir)
    return {"prepared": status}


# ---------------------------------------------------------------------------------------------- render
def preflight() -> dict:
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "preflight.py"), "--json"], capture_output=True,
                         text=True, timeout=240)
    try:
        return json.loads(out.stdout)
    except ValueError:
        return {"error": (out.stderr or "preflight gave no JSON").strip()[:300]}


def app_queue_busy(url: str = "http://127.0.0.1:8477/api/system") -> Optional[str]:
    """The Raag Studio app's own render queue, when the app is running (None = idle or not running)."""
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            q = json.loads(r.read()).get("queue") or {}
        if q.get("running") or q.get("queued"):
            return f"the Raag Studio app is rendering ({q.get('running', 0)} running, {q.get('queued', 0)} queued)"
    except Exception:
        return None
    return None


def other_renders() -> list[str]:
    try:
        out = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return []
    me = str(os.getpid())
    return [ln.strip() for ln in out.splitlines()
            if "run_takes.py" in ln and "ps -eo" not in ln and not ln.strip().startswith(me)]


def blockers(pf: dict, need_gib: float) -> list[str]:
    out = []
    if "error" in pf:
        return [f"preflight failed: {pf['error']}"]
    mps = pf.get("mps")
    if mps is False or (isinstance(mps, dict) and mps.get("available") is False):
        out.append("Apple GPU (MPS) is not available")
    free = pf.get("disk_free_gib")
    if isinstance(free, (int, float)) and free < 5.0 + need_gib:
        out.append(f"only {free} GiB free; need {5.0 + need_gib:.1f} GiB")
    if (pf.get("ace_python") or {}).get("exists") is False:
        out.append(f"the ACE python is missing ({(pf.get('ace_python') or {}).get('path')})")
    ck = pf.get("checkpoints") or {}
    if ck and not ck.get("all_present", True):
        out.append("ACE-Step turbo weights are missing")
    if (pf.get("video_queue") or {}).get("state") == "busy":
        out.append("the ComfyUI video queue is busy")
    busy = app_queue_busy()
    if busy:
        out.append(busy)
    others = other_renders()
    if others:
        out.append("another run_takes.py is running: " + others[0][:120])
    return out


def loudness_copy(native: Path, out: Path) -> dict:
    """Two-pass EBU R128 normalisation to -16 LUFS with a -1.5 dBTP ceiling, MP3 192 kbps 48 kHz; then measured."""
    ff = media.tool("ffmpeg")
    first = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(native), "-af",
                            f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=600)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", first.stderr, re.S)
    if not m:
        raise media.MediaError("loudnorm measurement failed")
    meas = json.loads(m.group(0))
    filt = (f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:measured_I={meas['input_i']}:"
            f"measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:"
            f"offset={meas['target_offset']}:linear=true")
    gain_db = 0.0
    for _ in range(3):
        af = filt + (f",volume={gain_db}dB" if gain_db else "")
        tmp = out.with_name(out.name + ".part")
        done = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(native), "-af", af,
                               "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", str(tmp)],
                              capture_output=True, text=True, timeout=600)
        if done.returncode != 0:
            tmp.unlink(missing_ok=True)
            raise media.MediaError(f"listening copy encode failed: {done.stderr.strip()[:300]}")
        tmp.replace(out)
        info = media.probe(out)
        levels = media.analyse_levels(out, info["duration_s"])
        tp = levels["true_peak_dbtp"]
        if tp is None or tp <= MAX_COPY_TP:
            break
        gain_db -= (tp - TARGET_TP)                 # pull the copy down until its true peak is below the ceiling
    pcm, complaints = media.decode_s16(out)
    frac, hot = media.clipped_fraction(pcm)
    return {"file": out.name, "bytes": out.stat().st_size, "duration_s": info["duration_s"],
            "integrated_lufs": levels["integrated_lufs"], "true_peak_dbtp": levels["true_peak_dbtp"],
            "extra_gain_db": round(gain_db, 2), "clipped_fraction": round(frac, 6), "decode_ok": not complaints,
            "native_input_lufs": float(meas["input_i"]), "native_input_tp": float(meas["input_tp"])}


def render(spec: dict, *, show_dir: Path, runs_dir: Path, engine_cmd: Optional[list[str]] = None, yes: bool = False,
           check: Callable[[], dict] = preflight, wait_s: float = 30, max_wait_s: float = 1800,
           fake: bool = False) -> dict:
    if fake and show_dir.resolve().is_relative_to((ROOT / "showcase").resolve()):
        raise SystemExit("test-engine audio is never written into showcase/: use a scratch --show-dir")
    engine_cmd = engine_cmd or [str(ACE_PYTHON), str(RUN_TAKES)]
    todo = []
    for t in spec["takes"]:
        tdir = show_dir / "takes" / take_dir_name(t)
        info = json.loads((tdir / "take.json").read_text()) if (tdir / "take.json").exists() else None
        if not info:
            raise SystemExit(f"take {t['n']} is not prepared; run prepare first")
        if info["render"]["status"] == "not_rendered":
            todo.append((t, tdir, info))
    if not todo:
        print("All takes are already rendered (or failed and recorded). Nothing to do.")
        return {"rendered": 0}
    pf = check()
    bl = [] if fake else blockers(pf, need_gib=0.1 * len(todo))
    print(f"{len(todo)} take(s) to render, one at a time, profile {spec['profile']} (turbo DiT, shift 3.0, no LM).")
    if bl:
        print("Not rendering:\n  - " + "\n  - ".join(bl))
        return {"rendered": 0, "blockers": bl}
    if not yes and input("Render now? These count against your render ledger. [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled; nothing rendered.")
        return {"rendered": 0}
    runs_dir.mkdir(parents=True, exist_ok=True)
    (show_dir / "audio").mkdir(parents=True, exist_ok=True)
    done_n = 0
    for t, tdir, info in todo:
        waited = 0.0
        while not fake:
            again = blockers(check(), need_gib=0.1)
            if not again:
                break
            if waited >= max_wait_s:
                info["render"] = {"status": "not_rendered", "skipped_at": now(), "reason": "; ".join(again)}
                write_json(tdir / "take.json", info)
                print(f"take {t['n']}: still blocked after {waited:.0f} s ({'; '.join(again)}); stopping here")
                write_summary(spec, show_dir)
                write_readme(spec, show_dir)
                return {"rendered": done_n, "stopped": "; ".join(again)}
            print(f"take {t['n']}: waiting ({'; '.join(again)})")
            time.sleep(wait_s)
            waited += wait_s
        req = tdir / "request.json"
        part = runs_dir / f"{take_dir_name(t)}.partial"
        final = runs_dir / take_dir_name(t)
        if part.exists() or final.exists():
            raise SystemExit(f"{part} or {final} already exists; renders are never overwritten")
        started = time.time()
        proc = subprocess.run(engine_cmd + [str(req), str(part)], capture_output=True, text=True)
        wall = round(time.time() - started, 1)
        events = []
        for ln in proc.stdout.splitlines():
            try:
                events.append(json.loads(ln))
            except ValueError:
                pass
        err = next((e for e in events if e.get("event") == "error"), None)
        if proc.returncode != 0 or err or not part.is_dir():
            info["render"] = {"status": "failed", "finished_at": now(), "wall_s": wall, "exit_code": proc.returncode,
                              "error": (err or {}).get("message") or proc.stderr.strip()[-300:],
                              "native_dir": str(part)}
            write_json(tdir / "take.json", info)
            print(f"take {t['n']}: FAILED ({info['render']['error']}); not retried")
            continue
        part.rename(final)
        result = json.loads((final / "result.json").read_text())
        native = next(final.glob("take_*.*"))
        checks = media.technical_checks(native, float(t["duration_s"]))
        copy = loudness_copy(native, show_dir / "audio" / f"{take_dir_name(t)}.mp3")
        tk = (result.get("takes") or [{}])[0]
        info["render"] = {
            "status": "rendered", "finished_at": now(), "wall_s": wall, "engine": result.get("engine"),
            "model_load_s": result.get("model_load_s"), "take_wall_s": tk.get("wall_s"),
            "pipeline_s": tk.get("pipeline_s"), "peak_rss_mb": result.get("peak_rss_mb"),
            "effective_params": {k: (result.get("effective_params") or {}).get(k)
                                 for k in ("shift", "inference_steps", "guidance_scale", "thinking", "bpm",
                                           "keyscale", "timesignature", "duration")},
            "native_file": str(native.relative_to(ROOT)) if native.is_relative_to(ROOT) else str(native),
            "native_sha256": media.sha256_file(native), "technical_checks": checks, "listening_copy": copy,
            "network_attempts": result.get("network_attempts"), "fake_engine": fake,
        }
        write_json(tdir / "take.json", info)
        write_json(tdir / "result.json", result)
        done_n += 1
        print(f"take {t['n']}: {checks['status']} in {wall:.0f} s -> audio/{copy['file']}")
    write_summary(spec, show_dir)
    write_readme(spec, show_dir)
    print(f"Rendered {done_n} of {len(todo)}. Add a row for these takes to the render ledger in STATUS.md.")
    return {"rendered": done_n}


# ---------------------------------------------------------------------------------------------- documents
def takes_info(spec: dict, show_dir: Path) -> list[tuple[dict, dict]]:
    out = []
    for t in spec["takes"]:
        f = show_dir / "takes" / take_dir_name(t) / "take.json"
        out.append((t, json.loads(f.read_text()) if f.exists() else {}))
    return out


def write_ratings(spec: dict, show_dir: Path) -> None:
    f = show_dir / "ratings.csv"
    if f.exists():
        return                                      # never overwrite ratings someone may have filled in
    show_dir.mkdir(parents=True, exist_ok=True)
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RATING_FIELDS)
        w.writeheader()
        for t in spec["takes"]:
            w.writerow({"take": t["n"], "title": t["title"], "file": f"audio/{take_dir_name(t)}.mp3"})


def write_summary(spec: dict, show_dir: Path) -> dict:
    rows = []
    for t, info in takes_info(spec, show_dir):
        r = info.get("render", {})
        c = r.get("technical_checks") or {}
        facts, checks = c.get("facts", {}), c.get("checks", {})
        copy = r.get("listening_copy") or {}
        rows.append({
            "take": t["n"], "title": t["title"], "status": r.get("status", "not_prepared"),
            "check_status": c.get("status"), "failures": c.get("failures"), "warnings": c.get("warnings"),
            "decodes": (checks.get("decodes") or {}).get("ok"), "requested_s": t["duration_s"],
            "duration_s": facts.get("duration_s"), "sample_rate": facts.get("sample_rate"),
            "channels": facts.get("channels"), "clipped_fraction": facts.get("clipped_fraction"),
            "silence_fraction": facts.get("silence_fraction"), "native_lufs": facts.get("integrated_lufs"),
            "native_true_peak": facts.get("true_peak_dbtp"), "copy_lufs": copy.get("integrated_lufs"),
            "copy_true_peak": copy.get("true_peak_dbtp"), "copy_clipped_fraction": copy.get("clipped_fraction"),
            "render_wall_s": r.get("wall_s"), "error": r.get("error"),
        })
    data = {"schema": "raag-showcase-technical/1", "id": spec["id"], "written_at": now(), "takes": rows,
            "note": "Breakage checks only (decoding, length, format, clipping, silence, loudness). They say nothing "
                    "about whether the music is good."}
    write_json(show_dir / "technical_summary.json", data)

    def f(v, fmt="{}"):
        return "-" if v is None else fmt.format(v)
    lines = ["# Technical results", "", data["note"], "",
             f"Silence: a warning above {5}% of the take, a failure above {40}%. Listening copies target "
             f"{TARGET_LUFS} LUFS with a true-peak ceiling of {TARGET_TP} dBTP (checked at or below {MAX_COPY_TP}).", "",
             "| # | Title | Render | Checks | Decodes | Length (req/actual s) | Rate / ch | Clipped | Silence | "
             "Native LUFS / TP | Copy LUFS / TP | Wall s |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(
            f"| {r['take']} | {r['title']} | {r['status']} | {f(r['check_status'])}"
            f"{(' (' + ', '.join(r['failures'] + r['warnings']) + ')') if r['failures'] or r['warnings'] else ''} | "
            f"{f(r['decodes'])} | {r['requested_s']} / {f(r['duration_s'])} | {f(r['sample_rate'])} / {f(r['channels'])} | "
            f"{f(r['clipped_fraction'], '{:.4%}')} | {f(r['silence_fraction'], '{:.1%}')} | "
            f"{f(r['native_lufs'])} / {f(r['native_true_peak'])} | {f(r['copy_lufs'])} / {f(r['copy_true_peak'])} | "
            f"{f(r['render_wall_s'])} |")
    failed = [r for r in rows if r["status"] == "failed"]
    if failed:
        lines += ["", "## Failed takes (not retried)", ""] + [f"- {r['take']} {r['title']}: {r['error']}" for r in failed]
    (show_dir / "technical_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def write_readme(spec: dict, show_dir: Path) -> None:
    infos = takes_info(spec, show_dir)
    rendered = [i for _, i in infos if i.get("render", {}).get("status") == "rendered"]
    failed = [i for _, i in infos if i.get("render", {}).get("status") == "failed"]
    state = (f"**{len(rendered)} of {len(infos)} takes rendered**" + (f", {len(failed)} failed (not retried)" if failed else "")
             if rendered or failed else
             "**Not rendered yet.** Plans, lyrics, captions, engine requests and seeds are fixed; the audio has to be "
             "made on the Mac with the local ACE-Step model (commands below). Nothing in this folder is fake audio.")
    lines = [f"# Showcase: diverse 12 ({spec['id']})", "", state, "",
             f"Engine profile `{spec['profile']}`: ACE-Step 1.5 turbo DiT (`acestep-v15-turbo`), shift 3.0, 8 steps, "
             "no 5Hz LM. One take per brief, rendered one after another, no retries. Lyrics written by Claude through "
             "the app's songwriter step, each supplied hook kept unchanged in every chorus. The lyric sheets carry "
             "section names only (the duet also names who sings); musical direction is in the caption.", "",
             "Tempo, meter, arrangement and vocal assignments are what was **requested**; whether the engine followed "
             "them is for your ears. Every musical judgment below is **pending** until someone listens.", "",
             "| # | Listen | Kind | Requested | Seed | Render | Checks | Verdict |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for t, info in infos:
        r = info.get("render", {})
        name = take_dir_name(t)
        audio = f"[{t['title']}](audio/{name}.mp3)" if r.get("status") == "rendered" else f"{t['title']} (no audio yet)"
        kind = "instrumental" if t["voice"] == "instrumental" else f"{t.get('language', '')} {t.get('singer', '')} vocal"
        req = f"{t['duration_s']} s, ~{t['bpm']} BPM, {t['meter']}"
        checks = (r.get("technical_checks") or {}).get("status", "-")
        lines.append(f"| {t['n']} | {audio} | {kind} | {req} | {info.get('seed', '-')} | {r.get('status', '-')} | "
                     f"{checks} | pending |")
    lines += ["", "Per take, in `takes/NN_slug/`: `brief.md` (brief as written and the requested targets), "
              "`plan.json`, `lyrics.txt` and `songwriter.json` (every Claude draft, its line check, any revision and "
              "notes), `caption.txt`, `request.json` (the exact engine request with its seed), `compile_report.json` "
              "(song map, anything left out of the caption), `take.json` (model, profile, timing, technical checks), "
              "`result.json` (the engine's own record, after rendering).", "",
              "Rate in `ratings.csv` (1 to 5 per column, blank = not rated). Technical results: "
              "`technical_summary.md`.", "",
              "## Reproduce", "",
              "```sh",
              "git fetch origin claude/intelligent-knuth-6jv48e && git checkout claude/intelligent-knuth-6jv48e",
              "cd app",
              ".venv/bin/python -m experiments.showcase prepare     # keeps the saved lyrics; --rewrite-lyrics calls Claude again",
              ".venv/bin/python -m experiments.showcase render      # Mac only: checks GPU, disk, ComfyUI and other renders first",
              ".venv/bin/python -m experiments.showcase publish     # commits showcase/ and pushes this branch (never master)",
              "```", "",
              "Native 48 kHz FLAC renders stay on the Mac in `runs/_showcase/" + spec["id"] + "/` (not committed). "
              "The MP3s here are listening copies normalised to -16 LUFS with a -1.5 dBTP true-peak ceiling."]
    show_dir.mkdir(parents=True, exist_ok=True)
    (show_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------- publish
def publish(spec: dict, show_dir: Path, *, push: bool = True) -> int:
    branch = subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"], capture_output=True,
                            text=True).stdout.strip()
    if branch in ("master", "main", ""):
        raise SystemExit(f"refusing to publish on '{branch or 'detached HEAD'}'; check out the showcase branch")
    rel = show_dir.relative_to(ROOT)
    for cmd in (["git", "-C", str(ROOT), "add", str(rel)],
                ["git", "-C", str(ROOT), "commit", "-m", f"Showcase {spec['id']}: renders, listening copies and "
                                                         "technical results"]):
        if subprocess.run(cmd).returncode != 0:
            return 1
    if push:
        return subprocess.run(["git", "-C", str(ROOT), "push", "-u", "origin", branch]).returncode
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path, default=SPEC)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--only", default="", help="comma-separated take numbers")
    p.add_argument("--rewrite-lyrics", action="store_true", help="ask Claude again even when lyrics are saved")
    r = sub.add_parser("render")
    r.add_argument("--yes", action="store_true")
    sub.add_parser("publish").add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    spec = load_spec(a.spec)
    runs_dir, show_dir = paths(spec)
    if a.cmd == "prepare":
        only = [int(x) for x in a.only.split(",") if x.strip()] or None
        out = prepare(spec, show_dir=show_dir, runs_dir=runs_dir, only=only, rewrite_lyrics=a.rewrite_lyrics)
        for n, st in out["prepared"]:
            print(f"take {n}: {st}")
        return 0
    if a.cmd == "render":
        out = render(spec, show_dir=show_dir, runs_dir=runs_dir, yes=a.yes)
        return 0 if not out.get("blockers") else 2
    return publish(spec, show_dir, push=not a.no_push)


if __name__ == "__main__":
    sys.exit(main())
