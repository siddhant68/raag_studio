"""Read-only data the web UI needs (M3): visible recipes, capability labels, instrument list, taste ledger.

Nothing here writes anything. Handlers in main.py are one-liners over these functions.
"""
from __future__ import annotations

import json
from typing import Any

from . import capabilities, compiler
from .db import loads
from .plan_schema import INSTRUMENT_IDS

# Plain-language names for the C6 chip picker (display only; the ids are the validated allow-list).
INSTRUMENT_NAMES = {
    "bansuri": "Flute (bansuri)", "tabla": "Tabla", "tanpura": "Tanpura", "santoor": "Santoor",
    "sitar": "Sitar", "ghatam": "Ghatam (clay pot drum)", "violin": "Violin", "cello": "Cello",
    "strings": "Strings", "piano": "Piano", "acoustic_guitar": "Acoustic guitar", "bass": "Bass",
    "light_percussion": "Light drums", "choir": "Choir", "harmonium": "Harmonium",
}
# Evidence level, from PRD section 5.4: only the first nine have evidence in the recipes and the user's liking.
VALIDATED = ("bansuri", "tabla", "tanpura", "santoor", "sitar", "ghatam", "violin", "cello", "strings")


def recipes_view() -> dict:
    """GET /api/recipes: the recipes the UI may offer. Hidden ones (R4 until rated) are never listed."""
    out = []
    for rec in compiler.list_recipes(include_hidden=False):
        d = rec["plan_defaults"]
        out.append({
            "id": rec["id"], "name": rec["display_name"], "status": rec["status"],
            "experimental": bool(rec.get("experimental")), "caveat": rec.get("caveat"),
            "lead": d.get("lead", {}).get("instrument"), "voice_mode": d.get("voice_mode"),
            "duration_s": d.get("duration_s"), "bpm": d.get("pace", {}).get("bpm"),
            "supports": [s["instrument"] for s in d.get("supports", [])],
        })
    return {"recipes": out, "hidden_count": len(compiler.list_recipes(include_hidden=True)) - len(out),
            "note": "Starting points you liked, not rules."}


def capabilities_view() -> dict:
    """GET /api/capabilities: the honesty registry for the UI, per control with its labels already resolved."""
    reg = capabilities.registry()
    controls = {}
    for cid in capabilities.control_ids():
        c = reg["controls"][cid]
        controls[cid] = {
            "id": cid, "name": c["name"], "classes": c["classes"], "class_code": capabilities.control_class(cid),
            "visible": c["visible"], "ui_wording": c["ui_wording"], "maps_to": c["maps_to"],
            "needs_label": capabilities.needs_class_label(cid),
            "labels": capabilities.class_labels(cid),
        }
    return {"source": "app/backend/capabilities.json", "classes": reg["classes"], "controls": controls,
            "options": reg["options"], "capabilities": reg["capabilities"]}


def instruments_view() -> dict:
    return {"instruments": [{"id": i, "name": INSTRUMENT_NAMES[i], "validated": i in VALIDATED}
                            for i in INSTRUMENT_IDS],
            "note": "Evidence exists only for the validated ones; the rest are plausible but untested."}


def ledger_view(svc) -> dict:
    """GET /api/ledger: taste-ledger counts (PRD 5.5). Counts only; nothing is ranked or scored."""
    db = svc.db
    takes = db.all("SELECT t.id, r.plan_id FROM takes t JOIN rounds r ON r.id=t.round_id")
    plan_cache: dict[str, dict] = {}

    def plan_of(plan_id: str) -> dict:
        if plan_id not in plan_cache:
            row = db.one("SELECT card_json FROM plans WHERE id=?", (plan_id,))
            plan_cache[plan_id] = loads(row["card_json"])["plan"] if row else {}
        return plan_cache[plan_id]

    def empty() -> dict:
        return {"takes": 0, "loved": 0, "fine": 0, "no": 0, "favourites": 0, "unrated": 0}

    totals = empty()
    groups: dict[str, dict[str, dict]] = {"recipe": {}, "lead": {}, "pace": {}}
    for t in takes:
        fb = svc.feedback_state(db.all("SELECT * FROM feedback WHERE take_id=? ORDER BY rowid", (t["id"],)))
        plan = plan_of(t["plan_id"])
        keys = {"recipe": plan.get("recipe_id") or "none", "lead": (plan.get("lead") or {}).get("instrument", "unknown"),
                "pace": (plan.get("pace") or {}).get("bucket", "unknown")}
        for bucket in [totals] + [groups[g].setdefault(k, empty()) for g, k in keys.items()]:
            bucket["takes"] += 1
            if fb["favourite"]:
                bucket["favourites"] += 1
            if fb["rating"] == "love":
                bucket["loved"] += 1
            elif fb["rating"] == "fine":
                bucket["fine"] += 1
            elif fb["rating"] == "no":
                bucket["no"] += 1
            else:
                bucket["unrated"] += 1
    return {"totals": totals, "by_recipe": groups["recipe"], "by_lead": groups["lead"], "by_pace": groups["pace"],
            "note": "Counts of your own ratings. Nothing is ranked or scored by the app."}


def planner_view(svc) -> dict[str, Any]:
    """Planner block for GET/PUT /api/settings: who runs, what each provider is, and the 'Write for me' status."""
    from .providers.registry import lyrics_status, provider_status, selected_provider, PROVIDER_LABELS
    settings = svc.settings()
    effective = selected_provider(settings)
    return {"provider": effective, "label": PROVIDER_LABELS[effective], "setting": settings["planner_provider"],
            "smart_enabled": settings["planner_smart_enabled"],
            "providers": provider_status(settings),
            "write_for_me": lyrics_status(svc.planner()),
            "how_to_enable": ("A smart planner is on. Your brief text and control choices go to Anthropic. This page never "
                              "changes it; to switch it off use PUT /api/settings with planner_provider=basic and "
                              "planner_smart_enabled=false."
                              if effective != "basic" else
                              "Smart planners are off. They stay off until you change the setting yourself "
                              "(PUT /api/settings with planner_provider and planner_smart_enabled=true). "
                              "This page never turns them on. Enabling one sends only your brief text and "
                              "control choices to Anthropic.")}


def storage_view(svc) -> dict:
    """GET /api/storage: numbers for the disk meter (free space comes from the same probe the render gate uses)."""
    import shutil
    runs = svc.config.runs_dir
    usage = shutil.disk_usage(runs)
    total_runs = 0
    native_files = 0
    if runs.is_dir():
        for path in runs.rglob("*"):
            if path.is_file():
                total_runs += path.stat().st_size
                if path.suffix == ".flac":
                    native_files += 1
    settings = svc.settings()
    return {"disk_total_gib": round(usage.total / 2**30, 2), "disk_free_gib": svc.probe.disk_free_gib(),
            "min_disk_gib": settings["min_disk_gib"], "runs_gib": round(total_runs / 2**30, 3),
            "native_files": native_files, "runs_dir": str(runs)}
