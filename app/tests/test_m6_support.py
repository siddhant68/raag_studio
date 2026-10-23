"""Shared helpers for the M6 tests (no tests in here)."""
import csv
import json
import math
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments import blind_sheet as bs

BRIEFS = [
    "a slow tender flute piece with tanpura, no singing, two minutes",
    "warm piano and cello, instrumental, about 90 seconds",
    "bansuri and tabla, lively, no singing, 2 minutes",
]
SOURCE = {"source_audio": "/data/takes/fav.flac", "source_duration_s": 150.0}


def e_items(exp_id):
    """Plan specs good enough for any experiment."""
    items = []
    for b in BRIEFS:
        it = {"brief": b}
        if bs.EXPERIMENTS[exp_id].needs_source:
            it.update(SOURCE)
        if bs.EXPERIMENTS[exp_id].needs_span:
            it.update(span=[40.0, 50.0], xfade_s=0.05)
        if bs.EXPERIMENTS[exp_id].needs_source_texts:
            it.update(source_caption="Gentle flute and tanpura, slow.", source_lyrics="")
        items.append(it)
    return items


def make_exp(tmp_path, exp_id="E1", seeds=(101, 202), rng_seed=7, name=None, **kw):
    out = tmp_path / (name or f"exp_{exp_id}_{rng_seed}")
    bs.create_experiment(exp_id, e_items(exp_id), list(seeds), out, rng_seed=rng_seed, **kw)
    return out


def read_json(p):
    return json.loads(Path(p).read_text("utf-8"))


def sine(sr=8000, seconds=2.0, freq=220.0, amp=12000, channels=2, phase=0.0):
    n = int(sr * seconds)
    a = array("h")
    for i in range(n):
        v = int(amp * math.sin(2 * math.pi * freq * i / sr + phase))
        a.extend([v] * channels)
    return bs.Pcm(sr, channels, a)


def fill_csv_with(exp_dir, picker):
    """Fill sheet.csv like a rater would; picker(trial_row, key_trial) -> choice label or ''."""
    key = read_json(exp_dir / "key" / "key.json")
    p = exp_dir / "sheet" / "sheet.csv"
    rows = list(csv.DictReader(p.read_text("utf-8").splitlines()))
    for r in rows:
        r["choice"] = picker(r, key["trials"][r["trial"]])
    out = exp_dir / "filled.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return out
