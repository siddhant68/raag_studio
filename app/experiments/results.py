"""M6 experiment harness, part 3: per-arm tallies, the promotion rule, and a markdown results table.

    cd app && python -m experiments.results --key ../runs/_experiments/e1/key/key.json \
        --ratings filled_sheet.csv [--adopt shift_3.0] [--out results.md]

PROMOTION RULE (PRD v2 section 12/M6): an arm is promoted when it is preferred in >= 70% of >= 10 blind
trials, or when Siddhant explicitly adopts it.

How the rule is applied here:
  * "trial" = a blind trial that was actually rated. A tie counts as a trial and as no win for anyone.
    Skipped (blank) trials are not trials.
  * Preference experiments (E1, E3): successes = trials where the arm was chosen, trials = all rated trials.
  * Question experiments (E2, E4, E5): successes = "yes" answers to the primary question for that arm,
    trials = answers given for that arm. Other questions are listed as information only.
  * The test is exact integer arithmetic: successes * 10 >= trials * 7 and trials >= 10. 9 trials never
    promote by the rule (even 9 of 9); 7 of 10 promotes; 6 of 10 does not.
  * A control arm is the incumbent and is never "promoted".
  * Explicit adoption (`--adopt ARM` or "adopted" in the ratings JSON) promotes regardless of the counts and
    is labelled as adoption, not as a pass.
  * Passing the rule never changes the app by itself: the orchestrator ships an experiment only if it passes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

_APP = Path(__file__).resolve().parents[1]
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

from experiments.ratings_import import DeblindedRatings, RatingsError, import_ratings   # noqa: E402

MIN_TRIALS = 10
RATE_NUM, RATE_DEN = 7, 10          # 70%


def passes_rule(successes: int, trials: int) -> bool:
    """>= 70% of >= 10 blind trials, in exact integer arithmetic."""
    if successes < 0 or trials < 0 or successes > trials:
        raise ValueError("need 0 <= successes <= trials")
    return trials >= MIN_TRIALS and successes * RATE_DEN >= trials * RATE_NUM


def promotion(successes: int, trials: int, *, adopted: bool = False, control: bool = False) -> dict:
    """{"promoted": bool, "via": "rule"|"adoption"|None, "verdict": str}"""
    rate = (successes / trials) if trials else 0.0
    if control:
        return {"promoted": False, "via": None, "rate": rate, "verdict": "control (incumbent)"}
    ok = passes_rule(successes, trials)
    if ok:
        return {"promoted": True, "via": "rule", "rate": rate,
                "verdict": f"PROMOTED by the rule ({successes}/{trials})"}
    if adopted:
        return {"promoted": True, "via": "adoption", "rate": rate, "verdict": "PROMOTED: adopted by the user"}
    if trials < MIN_TRIALS:
        why = f"only {trials} blind trial{'s' if trials != 1 else ''}, need {MIN_TRIALS}"
    else:
        why = f"{successes}/{trials} = {rate:.0%}, need 70%"
    return {"promoted": False, "via": None, "rate": rate, "verdict": f"not promoted ({why})"}


def compute(d: DeblindedRatings) -> dict:
    """Structured results from de-blinded ratings."""
    rows = []
    primary = d.primary
    for arm in d.arms:
        is_control = arm in d.controls
        if primary["kind"] == "preference":
            succ, tri = d.wins.get(arm, 0), d.preference_trials
        else:
            q = primary["name"]
            succ, tri = d.yes.get(q, {}).get(arm, 0), d.answered.get(q, {}).get(arm, 0)
        row = {"arm": arm, "role": "control" if is_control else "candidate", "successes": succ, "trials": tri}
        row.update(promotion(succ, tri, adopted=arm in d.adopted, control=is_control))
        rows.append(row)
    extra = {}
    for q in d.questions:
        if primary["kind"] == "question" and q == primary["name"]:
            continue
        extra[q] = {a: {"yes": d.yes[q][a], "answered": d.answered[q][a]} for a in d.arms}
    return {
        "experiment": d.experiment, "sheet_id": d.sheet_id, "primary": primary, "arms": rows,
        "ties": d.ties, "rated_trials": d.preference_trials if primary["kind"] == "preference" else None,
        "skipped_trials": list(d.skipped), "adopted": list(d.adopted), "other_questions": extra,
        "promoted_arms": [r["arm"] for r in rows if r["promoted"]],
    }


def render_markdown(res: dict, title: str = "") -> str:
    p = res["primary"]
    what = "Preferred" if p["kind"] == "preference" else f"Yes: {p['name']}"
    lines = [f"# {res['experiment']}{': ' + title if title else ''} (sheet {res['sheet_id']})", "",
             "Promotion rule: arm preferred in >= 70% of >= 10 blind trials, or explicit user adoption.", ""]
    lines += [f"| Arm | Role | {what} | Trials | Rate | Verdict |", "|---|---|---|---|---|---|"]
    for r in res["arms"]:
        rate = f"{r['rate']:.0%}" if r["trials"] else "-"
        lines.append(f"| {r['arm']} | {r['role']} | {r['successes']} | {r['trials']} | {rate} | {r['verdict']} |")
    lines.append("")
    if p["kind"] == "preference":
        lines.append(f"Ties: {res['ties']}. Rated trials: {res['rated_trials']}. "
                     f"Skipped: {len(res['skipped_trials'])}.")
    else:
        lines.append(f"Skipped trials (nothing answered): {len(res['skipped_trials'])}.")
    if res["adopted"]:
        lines.append(f"Explicitly adopted by the user: {', '.join(res['adopted'])}.")
    for q, per in res["other_questions"].items():
        lines += ["", f"Other question `{q}` (information only):", "", "| Arm | Yes | Answered |", "|---|---|---|"]
        for arm, c in per.items():
            lines.append(f"| {arm} | {c['yes']} | {c['answered']} |")
    lines += ["", "Promoted: " + (", ".join(res["promoted_arms"]) if res["promoted_arms"] else "none") + "."]
    return "\n".join(lines) + "\n"


def results_from_files(key_path: str | Path, ratings_path: str | Path, adopted: Sequence[str] = ()) -> tuple[dict, str]:
    d = import_ratings(ratings_path, key_path, adopted)
    key = json.loads(Path(key_path).read_text("utf-8"))
    res = compute(d)
    return res, render_markdown(res, key.get("title", ""))


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m experiments.results", description=__doc__.split("\n\n")[0])
    ap.add_argument("--key", required=True)
    ap.add_argument("--ratings", required=True)
    ap.add_argument("--adopt", action="append", default=[])
    ap.add_argument("--out", default=None, help="write the markdown here (printed anyway)")
    a = ap.parse_args(argv)
    try:
        _, md = results_from_files(a.key, a.ratings, a.adopt)
    except RatingsError as e:
        print("ratings problems:\n  - " + "\n  - ".join(e.problems), file=sys.stderr)
        return 2
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
