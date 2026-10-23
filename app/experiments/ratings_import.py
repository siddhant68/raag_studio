"""M6 experiment harness, part 2: import the user's blind ratings (CSV or JSON) and de-blind them with the key.

Accepted inputs (the filled-in `sheet/sheet.csv` works as it is):

CSV columns:  trial, choice, <question>_<label> ...   (other columns are ignored)
    T01,B,,            -> trial T01: preferred label B
    T02,tie,,          -> a blind trial where neither was preferred (counts as a trial, not as a win)
    T03,,yes,no        -> per-label yes/no answers (columns such as similar_but_different_A / _B)
    blank cells are "not rated" and are skipped.

JSON:
    {"adopted": ["shift_3.0"],                                   # optional: explicit user adoption (arm ids)
     "ratings": [{"trial": "T01", "choice": "B"},
                 {"trial": "T02", "choice": "tie"},
                 {"trial": "T03", "answers": {"similar_but_different": {"A": "yes", "B": "no"}}}]}
    or just the list of ratings.

De-blinding: `deblind(ratings, key)` replaces labels by arm ids using key/key.json. Problems (unknown trial,
unknown label, duplicate trial, unknown question, bad yes/no) are all collected and raised together as
RatingsError so nothing is silently dropped.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

_APP = Path(__file__).resolve().parents[1]
if str(_APP) not in sys.path:
    sys.path.insert(0, str(_APP))

TIE_WORDS = {"tie", "none", "same", "neither", "="}
YES, NO = {"yes", "y", "true", "1"}, {"no", "n", "false", "0"}


class RatingsError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class RawRatings:
    choices: dict[str, str] = field(default_factory=dict)                 # trial -> label | "tie"
    answers: dict[str, dict[str, dict[str, bool]]] = field(default_factory=dict)   # trial -> question -> label -> bool
    adopted: list[str] = field(default_factory=list)


@dataclass
class DeblindedRatings:
    experiment: str
    sheet_id: str
    arms: list[str]
    controls: list[str]
    primary: dict
    questions: list[str]
    wins: dict[str, int] = field(default_factory=dict)                    # preference: arm -> times preferred
    ties: int = 0
    preference_trials: int = 0                                            # rated trials (ties included)
    skipped: list[str] = field(default_factory=list)                      # trials with nothing rated
    yes: dict[str, dict[str, int]] = field(default_factory=dict)          # question -> arm -> yes count
    answered: dict[str, dict[str, int]] = field(default_factory=dict)     # question -> arm -> answered count
    adopted: list[str] = field(default_factory=list)
    per_trial: dict[str, dict] = field(default_factory=dict)              # de-blinded detail, for audit


# ---------------------------------------------------------------------------------------------
def load_key(path: str | Path) -> dict:
    key = json.loads(Path(path).read_text("utf-8"))
    if key.get("version") != "raag-blind-key/1":
        raise RatingsError(["not a blind-sheet key file"])
    return key


def _yn(v: Any) -> Optional[bool]:
    s = str(v).strip().lower()
    if s in YES:
        return True
    if s in NO:
        return False
    return None


def read_ratings(path: str | Path, questions: Sequence[str] = (), labels: Sequence[str] = ()) -> RawRatings:
    """Parse a CSV or JSON ratings file (by extension). `questions`/`labels` come from the key and are needed
    to split CSV column names like `similar_but_different_B`."""
    p = Path(path)
    text = p.read_text("utf-8-sig")
    if p.suffix.lower() == ".json":
        return _read_json(json.loads(text))
    return _read_csv(text, questions, labels)


def _read_json(data: Any) -> RawRatings:
    raw = RawRatings()
    problems: list[str] = []
    if isinstance(data, dict):
        raw.adopted = [str(a) for a in data.get("adopted", [])]
        items = data.get("ratings", [])
    else:
        items = data
    if not isinstance(items, list):
        raise RatingsError(["ratings JSON must be a list or {\"ratings\": [...]}"])
    for it in items:
        if not isinstance(it, dict) or "trial" not in it:
            problems.append(f"rating without a trial id: {str(it)[:60]}")
            continue
        tid = str(it["trial"]).strip()
        got = False
        ch = it.get("choice")
        if ch is not None and str(ch).strip() != "":
            if tid in raw.choices:
                problems.append(f"duplicate choice for {tid}")
            raw.choices[tid] = str(ch).strip()
            got = True
        for q, per in (it.get("answers") or {}).items():
            for lab, val in (per or {}).items():
                b = _yn(val)
                if b is None:
                    problems.append(f"{tid}: answer for {q}/{lab} must be yes or no, got {val!r}")
                    continue
                d = raw.answers.setdefault(tid, {}).setdefault(q, {})
                if str(lab) in d:
                    problems.append(f"duplicate answer for {tid} {q} {lab}")
                d[str(lab)] = b
                got = True
        if not got:
            raw.choices.setdefault("__empty__" + tid, "")      # remembered so the trial counts as skipped
    if problems:
        raise RatingsError(problems)
    return raw


def _read_csv(text: str, questions: Sequence[str], labels: Sequence[str]) -> RawRatings:
    raw = RawRatings()
    problems: list[str] = []
    reader = csv.DictReader(text.splitlines())
    fields = [f.strip() for f in (reader.fieldnames or [])]
    if "trial" not in fields:
        raise RatingsError(["CSV needs a 'trial' column"])
    qcols: dict[str, tuple[str, str]] = {}
    for q in questions:
        for lab in labels:
            qcols[f"{q}_{lab}"] = (q, lab)
    seen: set[str] = set()
    for row in reader:
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        tid = row.get("trial", "")
        if not tid:
            continue
        if tid in seen:
            problems.append(f"duplicate row for {tid}")
            continue
        seen.add(tid)
        got = False
        if row.get("choice"):
            raw.choices[tid] = row["choice"]
            got = True
        for col, (q, lab) in qcols.items():
            v = row.get(col, "")
            if v == "":
                continue
            b = _yn(v)
            if b is None:
                problems.append(f"{tid}: {col} must be yes or no, got {v!r}")
                continue
            raw.answers.setdefault(tid, {}).setdefault(q, {})[lab] = b
            got = True
        if not got:
            raw.choices.setdefault("__empty__" + tid, "")
    if problems:
        raise RatingsError(problems)
    return raw


# ---------------------------------------------------------------------------------------------
def deblind(raw: RawRatings, key: dict, adopted: Sequence[str] = ()) -> DeblindedRatings:
    """Map labels back to arms with the key. All problems are reported together."""
    trials = key["trials"]
    arms = list(key["arms"])
    controls = [a for a, v in key["arms"].items() if v.get("control")]
    questions = list(key.get("questions", []))
    problems: list[str] = []
    out = DeblindedRatings(experiment=key["experiment"], sheet_id=key["sheet_id"], arms=arms, controls=controls,
                           primary=key["primary"], questions=questions)
    out.wins = {a: 0 for a in arms}
    out.yes = {q: {a: 0 for a in arms} for q in questions}
    out.answered = {q: {a: 0 for a in arms} for q in questions}

    adopt = list(dict.fromkeys(list(raw.adopted) + list(adopted)))
    for a in adopt:
        if a not in arms:
            problems.append(f"adopted arm {a!r} is not an arm of {key['experiment']} ({', '.join(arms)})")
    out.adopted = [a for a in adopt if a in arms]

    seen_rated: set[str] = set()
    for tid, choice in raw.choices.items():
        if tid.startswith("__empty__"):
            continue
        if tid not in trials:
            problems.append(f"unknown trial {tid}")
            continue
        labels = trials[tid]["labels"]
        c = choice.strip()
        if c.lower() in TIE_WORDS:
            out.ties += 1
            out.preference_trials += 1
            out.per_trial.setdefault(tid, {})["choice"] = "tie"
            seen_rated.add(tid)
        elif c.upper() in labels:
            arm = labels[c.upper()]
            out.wins[arm] += 1
            out.preference_trials += 1
            out.per_trial.setdefault(tid, {})["choice"] = arm
            seen_rated.add(tid)
        else:
            problems.append(f"{tid}: choice {choice!r} is not one of {', '.join(labels)} or tie")
    for tid, per_q in raw.answers.items():
        if tid not in trials:
            problems.append(f"unknown trial {tid}")
            continue
        labels = trials[tid]["labels"]
        for q, per_lab in per_q.items():
            if q not in questions:
                problems.append(f"{tid}: unknown question {q!r}")
                continue
            for lab, val in per_lab.items():
                if lab not in labels:
                    problems.append(f"{tid}: label {lab!r} does not exist for this trial")
                    continue
                arm = labels[lab]
                out.answered[q][arm] += 1
                out.yes[q][arm] += 1 if val else 0
                out.per_trial.setdefault(tid, {}).setdefault("answers", {}).setdefault(q, {})[arm] = val
                seen_rated.add(tid)
    for tid in trials:
        if tid not in seen_rated:
            out.skipped.append(tid)
    if problems:
        raise RatingsError(problems)
    return out


def import_ratings(ratings_path: str | Path, key_path: str | Path, adopted: Sequence[str] = ()) -> DeblindedRatings:
    key = load_key(key_path)
    labels = sorted({lab for t in key["trials"].values() for lab in t["labels"]})
    raw = read_ratings(ratings_path, key.get("questions", []), labels)
    return deblind(raw, key, adopted)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m experiments.ratings_import",
                                 description="De-blind a ratings file and print the tallies as JSON.")
    ap.add_argument("--key", required=True)
    ap.add_argument("--ratings", required=True)
    ap.add_argument("--adopt", action="append", default=[], help="arm id the user explicitly adopts")
    a = ap.parse_args(argv)
    d = import_ratings(a.ratings, a.key, a.adopt)
    print(json.dumps(d.__dict__, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
