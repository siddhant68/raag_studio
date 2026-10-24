"""PERSONAL USE ONLY: render a Raag Studio song plan with ElevenLabs Music (music_v2_5), from your own account.

    cd app
    .venv/bin/python ../scripts/personal/elevenlabs_render.py --song <song_id>                 # preview, no call
    .venv/bin/python ../scripts/personal/elevenlabs_render.py --plan plan.json                 # preview, no call
    ELEVENLABS_API_KEY=... .venv/bin/python ../scripts/personal/elevenlabs_render.py --song <id> --render --max-credits 3000

Why this is a separate script and not part of the app:
  * ElevenLabs' terms allow personal use of Music outputs on paid plans, but forbid using their service or outputs
    to research, develop, train or improve competing products, reverse engineering, and making their models
    available through another app without written permission (elevenlabs.io/use-policy section 12,
    elevenlabs.io/music-terms sections 4.3 and 4.8). So: render songs you want to keep, for yourself. Do not use
    these outputs to tune or benchmark Raag Studio's own engine, and keep this script out of any public release.
  * The app itself never calls ElevenLabs.

How a plan is sent: the song blueprint becomes a v2 composition plan, one chunk per section: the section name and
its lyric lines as the chunk text (exact words unchanged), the section's length in milliseconds, the style words
(genre, mood, voice, instruments and production in the first chunk, the section's own hints in every chunk), and
"vocals" as a negative style for instrumental sections. Nothing is sent without --render.

Spending: --max-credits is required with --render. The script reads your balance first (GET /v1/user/subscription)
and refuses if the balance is too low; the estimate uses the web app's observed 900 credits per minute of music
(the API may bill differently: the balance before and after is recorded so you can see the real cost). A timeout
is NOT retried: the song may still have been made, so check your ElevenLabs history before trying again.
Outputs go to runs/_elevenlabs/<time>/ with the plan sent, the MP3 and the response headers, and a row is added to
data/elevenlabs_ledger.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from backend import lyric_craft, song_compiler, song_plan  # noqa: E402
from backend.plan_schema import Plan  # noqa: E402

API = "https://api.elevenlabs.io"
MODEL_ID = "music_v2_5"
OUTPUT_FORMAT = "mp3_48000_192"
CREDITS_PER_MINUTE_ESTIMATE = 900          # observed in the web app on 24 October 2026 (Creator plan)
MIN_CHUNK_MS, MAX_CHUNK_MS, MAX_CHUNKS = 3000, 120000, 30
LEDGER = ROOT / "data" / "elevenlabs_ledger.json"


# ------------------------------------------------------------------------------------------- plan conversion
def _styles(text: str) -> list[str]:
    return [p.strip().rstrip(".") for p in text.replace(". ", ", ").split(",") if p.strip().rstrip(".")]


def composition_plan(plan: Plan) -> dict:
    """The ElevenLabs v2 composition plan for a song-pipeline plan (pure function, no network)."""
    if plan.pipeline != "song":
        plan = song_plan.to_song_plan(plan, plan.brief)
    compiled = song_compiler.compile_song(plan)
    report = compiled["compile_report"]
    sections = report["blueprint"]["sections"]
    slots = dict(report["slots"])
    global_styles: list[str] = []
    for name in ("genre", "mood", "vocal", "instruments", "production"):
        if name in slots:
            global_styles += _styles(slots[name])
    global_styles.append(f"{plan.pace.bpm} BPM")
    global_styles.append(plan.key)
    if plan.meter != "4/4":
        global_styles.append(f"{plan.meter} time")
    mode = plan.voice_mode
    sung_blocks = lyric_craft.parse_tagged(compiled["lyrics"]) if mode == "sung" else []
    if mode == "sung" and len(sung_blocks) != len(sections):
        raise ValueError(f"lyric sheet has {len(sung_blocks)} sections but the blueprint has {len(sections)}")
    chunks = []
    for i, s in enumerate(sections[:MAX_CHUNKS]):
        lines = sung_blocks[i][1] if mode == "sung" else []
        if mode == "wordless" and s["lines"]:
            lines = ["(ooh, aah)"]                         # wordless vocal sounds go in parentheses
        styles = (global_styles if i == 0 else []) + _styles(s.get("hint") or "")
        if not styles:
            styles = _styles(slots.get("genre", ""))[:2]
        negative = []
        if mode == "instrumental" or (mode == "sung" and not lines):
            negative.append("vocals")
            if mode == "sung":
                styles = styles + ["instrumental section"]
        ms = int(round(float(s["seconds"]) * 1000))
        chunks.append({
            "text": "\n".join([f"[{s['name']}]"] + lines),
            "duration_ms": max(MIN_CHUNK_MS, min(MAX_CHUNK_MS, ms)),
            "positive_styles": styles[:50],
            "negative_styles": negative,
            "context_adherence": "high",
        })
    return {"chunks": chunks}


def estimate_credits(cplan: dict) -> int:
    seconds = sum(c["duration_ms"] for c in cplan["chunks"]) / 1000
    return int(round(seconds / 60 * CREDITS_PER_MINUTE_ESTIMATE))


# ------------------------------------------------------------------------------------------- inputs
def plan_from_song(song_id: str, db_path: Path) -> Plan:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)       # read-only: never touches the app's data
    row = con.execute("SELECT card_json FROM plans WHERE song_id=? ORDER BY rev DESC LIMIT 1", (song_id,)).fetchone()
    con.close()
    if not row:
        raise SystemExit(f"no plan for song {song_id} in {db_path}")
    return Plan.model_validate(json.loads(row[0])["plan"])


# ------------------------------------------------------------------------------------------- render
def balance(client, key: str) -> Optional[int]:
    r = client.get(f"{API}/v1/user/subscription", headers={"xi-api-key": key}, timeout=30)
    r.raise_for_status()
    d = r.json()
    if "character_limit" in d and "character_count" in d:
        return int(d["character_limit"]) - int(d["character_count"])
    return None


def render(cplan: dict, *, key: str, max_credits: int, out_root: Path, client=None) -> dict:
    import httpx
    client = client or httpx.Client()
    est = estimate_credits(cplan)
    if est > max_credits:
        raise SystemExit(f"estimated {est} credits is above --max-credits {max_credits}; nothing was sent")
    before = balance(client, key)
    if before is not None and before < est:
        raise SystemExit(f"balance {before} credits is below the estimate {est}; nothing was sent")
    out = out_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)
    body = {"composition_plan": cplan, "model_id": MODEL_ID}
    (out / "composition_plan.json").write_text(json.dumps(body, indent=2, ensure_ascii=False))
    started = time.time()
    try:
        r = client.post(f"{API}/v1/music", params={"output_format": OUTPUT_FORMAT},
                        headers={"xi-api-key": key, "content-type": "application/json"}, json=body, timeout=600)
    except httpx.TimeoutException:
        (out / "TIMEOUT.txt").write_text("The request timed out. The song may still have been made and billed: check "
                                         "your ElevenLabs Music history before sending it again. Not retried.")
        raise SystemExit("timed out; NOT retried. Check your ElevenLabs history before trying again.")
    if r.status_code != 200:
        (out / "error.json").write_text(json.dumps({"status": r.status_code, "body": r.text[:4000]}, indent=2))
        raise SystemExit(f"ElevenLabs answered {r.status_code}: {r.text[:300]}")
    (out / "song.mp3").write_bytes(r.content)
    headers = {k: v for k, v in r.headers.items() if k.lower() not in ("set-cookie",)}
    (out / "response_headers.json").write_text(json.dumps(headers, indent=2))
    after = balance(client, key)
    entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "folder": str(out), "model": MODEL_ID,
             "seconds": sum(c["duration_ms"] for c in cplan["chunks"]) / 1000, "estimate_credits": est,
             "balance_before": before, "balance_after": after,
             "credits_used": (before - after) if before is not None and after is not None else None,
             "song_id": r.headers.get("song-id"), "wall_s": round(time.time() - started, 1)}
    (out / "receipt.json").write_text(json.dumps(entry, indent=2))
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    LEDGER.write_text(json.dumps(rows + [entry], indent=2))
    return entry


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--song", help="song id from the Raag Studio library (latest plan revision)")
    src.add_argument("--plan", type=Path, help="a plan JSON file")
    ap.add_argument("--db", type=Path, default=ROOT / "data" / "raag.db")
    ap.add_argument("--render", action="store_true", help="actually call ElevenLabs (spends credits)")
    ap.add_argument("--max-credits", type=int, help="refuse when the estimate is above this (required with --render)")
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / "_elevenlabs")
    a = ap.parse_args(argv)
    plan = plan_from_song(a.song, a.db) if a.song else Plan.model_validate(json.loads(a.plan.read_text()))
    if plan.voice_mode == "sung" and not (plan.lyrics.text or "").strip():
        raise SystemExit("this sung plan has no lyrics yet: make the song in the app first (or paste your words)")
    cplan = composition_plan(plan)
    print(json.dumps(cplan, indent=2, ensure_ascii=False))
    print(f"\n{len(cplan['chunks'])} sections, {sum(c['duration_ms'] for c in cplan['chunks']) / 1000:.0f} s, "
          f"estimated {estimate_credits(cplan)} credits (web-app rate; the API may differ).")
    if not a.render:
        print("Preview only. Add --render --max-credits N to send it (personal use only; see the top of this file).")
        return 0
    if a.max_credits is None:
        raise SystemExit("--render needs --max-credits")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("set ELEVENLABS_API_KEY in the environment (never in a file inside the repository)")
    entry = render(cplan, key=key, max_credits=a.max_credits, out_root=a.out)
    print(json.dumps(entry, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
