"""Planner evaluation on independently written briefs (tests/fixtures/eval_briefs_v2.jsonl).

Reports, per dimension, how often a planner's plan matches the expectation a producer would have. It does NOT assert
a pass mark and never calls a provider: the default is the Basic planner; a smart planner is evaluated only from
recorded plans (`--plans plans.json`: {"<brief id>": <BriefCard dict>}) that someone obtained after authorising a
provider. A score here says the plan matches what was asked; it says nothing about how the music sounds.

Run from app/:  .venv/bin/python -m experiments.eval_planner [--plans plans.json] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / "tests"))

from backend import compiler  # noqa: E402
from backend.planner_base import BriefCard  # noqa: E402
from backend.planner_rules import BasicPlanner  # noqa: E402
from test_m1_planner import checks  # noqa: E402  (the same field checks as the original fixture)

FIXTURE = APP / "tests" / "fixtures" / "eval_briefs_v2.jsonl"


def load(path: Path = FIXTURE) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text("utf-8").splitlines() if ln.strip()]


def evaluate(cards: dict[str, BriefCard], briefs: list[dict]) -> dict:
    per_dim: dict[str, list[bool]] = defaultdict(list)
    rows = []
    for b in briefs:
        card = cards[b["id"]]
        res = checks(b["expected"], card)
        compile_ok, compile_note = True, None
        try:
            compiler.compile(card.plan)
        except compiler.LyricsMissing:
            compile_note = "asks for lyrics (expected for sung)"
        except compiler.CompileError as exc:
            compile_ok, compile_note = False, f"{exc.code}: {exc.message}"
        for dim in b["dimensions"]:
            if res:
                per_dim[dim].append(all(res.values()))
        rows.append({"id": b["id"], "brief": b["brief"], "dimensions": b["dimensions"], "checks": res,
                     "failed": [k for k, ok in res.items() if not ok], "compiles": compile_ok,
                     "compile_note": compile_note, "note": b.get("note")})
    fields = [ok for r in rows for ok in r["checks"].values()]
    return {"briefs": len(briefs), "field_checks": len(fields), "field_accuracy": round(sum(fields) / len(fields), 3),
            "briefs_fully_right": sum(1 for r in rows if r["checks"] and not r["failed"]),
            "briefs_scored": sum(1 for r in rows if r["checks"]),
            "by_dimension": {d: {"right": sum(v), "of": len(v)} for d, v in sorted(per_dim.items())},
            "all_compile": all(r["compiles"] for r in rows), "rows": rows}


def live(provider: str, briefs: list[dict], record: Path, json_out: str | None) -> int:
    """Call the provider once per brief. A fallback to Basic is recorded as such and NOT scored as the smart planner."""
    from backend.providers.registry import get_planner
    planner = get_planner({"planner": {"provider": provider, "smart_enabled": True}})
    cards, meta = {}, {}
    for b in briefs:
        out = planner.plan_with_status(b["brief"])
        cards[b["id"]] = out.card.model_dump(mode="json")
        meta[b["id"]] = {"fallback": out.fallback, "reason": out.fallback_reason}
        print(f"  {b['id']}: {'FALLBACK to Basic (' + str(out.fallback_reason) + ')' if out.fallback else 'smart plan'}", flush=True)
    record.write_text(json.dumps(cards, indent=2, ensure_ascii=False), "utf-8")
    record.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), "utf-8")
    fell = [k for k, v in meta.items() if v["fallback"]]
    print(f"recorded {len(cards)} plans to {record}; {len(fell)} fell back to Basic: {', '.join(fell) or 'none'}")
    if len(fell) == len(cards):
        # Nothing here came from the provider: scoring would only re-score Basic under another name.
        record.unlink(missing_ok=True)
        record.with_suffix(".meta.json").rename(record.with_suffix(".failed.meta.json"))
        print("No plan came from the provider, so nothing was scored and no plans file was kept. "
              f"Reason of the first failure: {meta[briefs[0]['id']]['reason']}")
        return 2
    print("WARNING: fallback plans are Basic's, not the provider's; scores below mix both." if fell else "")
    argv = ["--plans", str(record)] + (["--json", json_out] if json_out else [])
    return main(argv)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plans", help="recorded BriefCards from a smart planner; default: run the Basic planner")
    ap.add_argument("--json", help="write the full result here")
    ap.add_argument("--live", choices=["claude_cli", "anthropic_api"],
                    help="SENDS each brief to Anthropic through that provider (you authorised this) and records the plans")
    ap.add_argument("--record", help="with --live: where to write the recorded plans (a --plans file)")
    args = ap.parse_args(argv)
    briefs = load()
    if args.live:
        if not args.record:
            sys.exit("--live needs --record <file> so the plans are kept and re-scorable without another call")
        return live(args.live, briefs, Path(args.record), args.json)
    if args.plans:
        recorded = json.loads(Path(args.plans).read_text("utf-8"))
        missing = [b["id"] for b in briefs if b["id"] not in recorded]
        if missing:
            sys.exit(f"recorded plans are missing: {', '.join(missing)}")
        cards = {k: BriefCard.model_validate(v) for k, v in recorded.items()}
        who = f"recorded plans from {args.plans}"
    else:
        planner = BasicPlanner()
        cards = {b["id"]: planner.plan(b["brief"]) for b in briefs}
        who = "Basic planner (keyword rules)"
    out = evaluate(cards, briefs)
    out["planner"] = who
    print(f"{who}: {out['briefs_fully_right']}/{out['briefs_scored']} scored briefs fully right, "
          f"field accuracy {out['field_accuracy']:.0%} over {out['field_checks']} checks; every plan compiles: {out['all_compile']}")
    for dim, v in out["by_dimension"].items():
        print(f"  {dim:<12} {v['right']}/{v['of']}")
    for r in out["rows"]:
        if r["failed"]:
            print(f"  miss {r['id']} {r['failed']}: {r['brief']}")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2, ensure_ascii=False), "utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
