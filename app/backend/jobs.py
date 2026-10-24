"""Application service: songs, plans, rounds, jobs, feedback, views and restart recovery.

The API handlers in main.py are thin wrappers over `Service`. The render worker
(queue_worker.py) talks to the same object. Planning and compiling are done by
the M1 modules (planner_rules, compiler); this file only sequences them and
stores the results.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import signal
import sqlite3
import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import ValidationError

from . import compiler
from .db import Database, dumps, loads, now_iso, ulid
from .events import EventBus
from .plan_schema import BUCKET_DEFAULT_BPM, Plan, bucket_for_bpm
from .planner_base import Controls, Planner, PlannerError, plan_changes
from .planner_rules import BasicPlanner, choir_pick_of
from .schemas import ApiError, CreateSongBody, PlanOnlyBody, RoundBody
from .settings import DEFAULT_SETTINGS, Config, validate_settings
from .storage import Storage
from .system_info import SystemProbe

MAX_ATTEMPTS = 2
ACTIVE_STATES = ("queued", "running")
TERMINAL_STATES = ("succeeded", "failed", "cancelled")
FEEDBACK_TAGS = ("melody", "instrument", "voice", "rhythm", "diction", "too busy", "too plain", "wrong mood")
PLAN_SOURCE = {"basic": "rules", "claude_cli": "claude_cli", "anthropic_api": "anthropic_api"}
EXPERIMENTAL_MESSAGE = ("Variation, cover and repaint are experimental and not enabled. "
                        "Use 'another' (new takes from the same plan) or 'refine' (updated plan).")


def planner_status(planner: Planner, outcome: Any = None) -> dict:
    """Facts about who produced a plan, stored on the card so the UI can show a badge and a fallback banner.

    `outcome` is a registry PlanOutcome / PatchOutcome (smart providers wrap Basic in a FallbackPlanner). A plain
    BasicPlanner has no outcome object: it never falls back.
    """
    if outcome is None:
        return {"fallback": False, "reason": None, "code": None, "banner": None,
                "requested_provider": planner.name, "requested_label": planner.label,
                "used_provider": planner.name, "used_label": planner.label}
    return {"fallback": bool(outcome.fallback), "reason": outcome.fallback_reason, "code": outcome.fallback_code,
            "banner": outcome.banner, "requested_provider": outcome.requested_provider,
            "requested_label": outcome.requested_label, "used_provider": outcome.used_provider,
            "used_label": outcome.used_label}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_title(brief: str) -> str:
    one = " ".join(brief.split())
    if len(one) <= 60:
        return one
    return one[:60].rsplit(" ", 1)[0] + "..."


def _control_dict(body: CreateSongBody | PlanOnlyBody) -> dict[str, Any]:
    """Flatten the accepted spellings of the user's controls into Controls field names."""
    c: dict[str, Any] = {}
    c.update(body.controls or {})
    c.update(body.shape or {})
    flat = {"voice": body.voice, "duration_s": body.duration_s if body.duration_s is not None else body.duration,
            "takes": body.takes, "recipe_id": body.recipe_id or body.recipe,
            "lyrics_text": body.lyrics_text if body.lyrics_text is not None else body.lyrics}
    for key, value in flat.items():
        if value is not None:
            c[key] = value
    if c.get("voice") == "auto":
        c.pop("voice")
    return c


def make_controls(raw: dict[str, Any]) -> Controls:
    try:
        return Controls.model_validate(raw)
    except ValidationError as exc:
        raise ApiError(422, "invalid_controls", _first_error(exc), fields=_errors(exc))


def _errors(exc: ValidationError) -> list[dict]:
    return [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()]


def _first_error(exc: ValidationError) -> str:
    e = exc.errors()[0]
    return f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" if e["loc"] else e["msg"]


def apply_controls(plan: Plan, ctl: dict[str, Any]) -> Plan:
    """Apply user-edited controls to an existing plan; touched fields get provenance 'you'."""
    d = plan.model_dump(mode="json")
    prov = d["provenance"]

    def mark(field: str, reason: str = "you set this") -> None:
        prov[field] = {"source": "you", "reason": reason}

    if "voice" in ctl:
        d["voice_mode"] = ctl["voice"]
        mark("voice_mode")
        if ctl["voice"] == "instrumental":
            d["lyrics"] = {"policy": "none", "text": None, "topic": None}
            d["voices"].update(background="none", singer="auto")
        elif ctl["voice"] == "wordless":
            d["lyrics"] = {"policy": "none", "text": None, "topic": None}
            d["voices"]["singer"] = "auto"
            if d["voices"]["background"] == "none":
                d["voices"]["background"] = "light"
        elif d["lyrics"]["policy"] == "none":
            d["lyrics"]["policy"] = "write"
    if ctl.get("lyrics_text"):
        d["lyrics"] = {"policy": "exact", "text": ctl["lyrics_text"], "topic": None}
        mark("lyrics", "your words, sent unchanged")
    if "duration_s" in ctl:
        d["duration_s"] = ctl["duration_s"]; mark("duration_s")
    if "takes" in ctl:
        d["takes"] = ctl["takes"]; mark("takes")
    if "recipe_id" in ctl:
        d["recipe_id"] = ctl["recipe_id"]; mark("recipe_id", "you picked this sound")
    if "lead" in ctl:
        d["lead"]["instrument"] = ctl["lead"]
        d["supports"] = [s for s in d["supports"] if s["instrument"] != ctl["lead"]]
        mark("lead"); mark("supports", "lead changed")
    if "instruments" in ctl:
        existing = {s["instrument"]: s for s in d["supports"]}
        d["supports"] = [existing.get(i, {"instrument": i, "role": "texture", "presence": "gentle"})
                         for i in ctl["instruments"] if i != d["lead"]["instrument"]]
        mark("supports")
    if "style" in ctl:
        d["lead"]["style"] = ctl["style"]; mark("lead")
    for key in ("feeling", "avoid", "fullness", "arc", "key"):
        if key in ctl:
            d[key] = ctl[key]; mark(key)
    if "pace" in ctl or "bpm" in ctl:
        bpm = ctl.get("bpm") or (BUCKET_DEFAULT_BPM[ctl["pace"]] if "pace" in ctl else d["pace"]["bpm"])
        d["pace"] = {"bucket": ctl.get("pace") or bucket_for_bpm(bpm), "bpm": bpm}
        mark("pace")
    voices_touched = False
    for key, field in (("singer", "singer"), ("background", "background"), ("language", "language")):
        if key in ctl:
            d["voices"][field] = ctl[key]; voices_touched = True
    if voices_touched:
        mark("voices")
    try:
        return Plan.model_validate(d)
    except ValidationError as exc:
        raise ApiError(422, "invalid_plan", _first_error(exc), fields=_errors(exc))


# Plan fields a recipe's defaults can supply (see app/recipes/*.json plan_defaults). Voice fields are not among them.
RECIPE_FIELDS = ("lead", "supports", "feeling", "pace", "fullness", "arc", "key", "avoid", "flavour", "duration_s", "takes")


def adopt_auto(d: dict, auto: dict, key: str, merged: dict) -> None:
    """Put the Auto value of control `key` into plan dict `d`, with Auto's provenance (no longer 'you').

    `auto` is the plan the planner makes for the brief and the controls that are STILL set (`merged`), so a
    field that another remaining control also feeds (pace bucket + BPM, lead + style) keeps that control's value.
    Fields not belonging to `key` (other controls, chip changes) are left alone.
    """
    prov, auto_prov = d["provenance"], auto["provenance"]

    def take(field: str) -> None:
        if field in auto_prov:
            prov[field] = auto_prov[field]
        else:
            prov.pop(field, None)

    if key == "voice":
        for f in ("voice_mode", "lyrics", "voices"):
            d[f] = auto[f]
            take(f)
    elif key == "lead":
        d["lead"]["instrument"] = auto["lead"]["instrument"]
        take("lead")
        if "instruments" in merged:                       # supports are still yours: only drop the new lead from them
            d["supports"] = [s for s in d["supports"] if s["instrument"] != d["lead"]["instrument"]]
        else:
            d["supports"] = auto["supports"]
            take("supports")
    elif key == "instruments":
        d["supports"] = [s for s in auto["supports"] if s["instrument"] != d["lead"]["instrument"]]
        take("supports")
    elif key == "style":
        d["lead"]["style"] = auto["lead"]["style"]
        take("lead")
    elif key in ("pace", "bpm"):
        d["pace"] = auto["pace"]
        take("pace")
    elif key in ("singer", "background", "language"):
        d["voices"][key] = auto["voices"][key]
        take("voices")
    elif key == "recipe_id":
        # The recipe is a bundle of defaults. Back to Auto recomputes every field the recipe supplies, except those that
        # are still a choice of yours (control or chip, provenance 'you'): those are kept exactly.
        d["recipe_id"] = auto["recipe_id"]
        take("recipe_id")
        for field in RECIPE_FIELDS:
            if (prov.get(field) or {}).get("source") == "you":
                continue
            d[field] = auto[field]
            take(field)
        d["supports"] = [s for s in d["supports"] if s["instrument"] != d["lead"]["instrument"]]
    elif key in ("duration_s", "takes", "feeling", "avoid", "fullness", "arc", "key"):
        d[key] = auto[key]
        take(key)
    elif key == "lyrics_text":
        d["lyrics"] = auto["lyrics"]
        take("lyrics")


class Service:
    def __init__(self, config: Config, db: Database, storage: Storage, probe: SystemProbe, bus: EventBus):
        self.config, self.db, self.storage, self.probe, self.bus = config, db, storage, probe, bus
        self.worker = None                    # set by main.create_app (QueueWorker)

    # ------------------------------------------------------------------ settings / planner
    def settings(self) -> dict[str, Any]:
        defaults = dict(DEFAULT_SETTINGS, **self.config.setting_overrides)
        return self.db.get_settings(defaults)

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        try:
            clean = validate_settings(patch)
        except ValueError as exc:
            raise ApiError(422, "invalid_setting", str(exc))
        self.db.put_settings(clean)
        return self.settings()

    def planner(self) -> Planner:
        """Basic rules unless the user has chosen AND switched on a smart provider (providers/registry.py)."""
        settings = self.settings()
        try:
            from .providers.registry import get_planner
        except ImportError:
            return BasicPlanner()
        return get_planner(settings)

    def effective_planner(self) -> str:
        """The provider that will really run (a smart one needs planner_smart_enabled=true)."""
        try:
            from .providers.registry import selected_provider
        except ImportError:
            return "basic"
        return selected_provider(self.settings())

    # ------------------------------------------------------------------ admission
    def _admit(self) -> None:
        s = self.settings()
        free = self.probe.disk_free_gib()
        if free < s["min_disk_gib"]:
            raise ApiError(507, "insufficient_disk",
                           f"Only {free} GiB of disk is free; at least {s['min_disk_gib']} GiB is needed "
                           "to render safely. Free some space and try again.", disk_free_gib=free)
        row = self.db.one("SELECT COUNT(*) AS n FROM jobs WHERE state IN ('queued','running')")
        if row["n"] >= s["queue_depth_cap"]:
            raise ApiError(429, "queue_full", f"{row['n']} renders are already waiting (limit "
                           f"{s['queue_depth_cap']}). Wait for one to finish or cancel one.", queue_depth=row["n"])

    def queue_info(self) -> dict:
        rows = self.db.all("SELECT state, COUNT(*) AS n FROM jobs WHERE state IN ('queued','running') GROUP BY state")
        counts = {r["state"]: r["n"] for r in rows}
        running = self.db.one("SELECT id FROM jobs WHERE state='running' ORDER BY started_at LIMIT 1")
        return {"queued": counts.get("queued", 0), "running": counts.get("running", 0),
                "depth": sum(counts.values()), "cap": self.settings()["queue_depth_cap"],
                "running_job_id": running["id"] if running else None}

    # ------------------------------------------------------------------ plan + compile
    def _compile(self, plan: Plan, takes: int) -> tuple[dict, dict, list[int]]:
        """Plan -> (compiled, engine_request, seeds). Raises ApiError with the compiler's own message."""
        try:
            compiled = compiler.compile(plan)
        except compiler.OverBudget as exc:
            raise ApiError(422, "over_budget", exc.message, caption=exc.caption)
        except compiler.LyricsMissing as exc:
            raise ApiError(422, "needs_user_input", exc.message + " Paste your own lyrics, or choose Instrumental "
                           "or Wordless voices.")
        except compiler.CompileError as exc:
            raise ApiError(422, exc.code, exc.message)
        seeds = random.SystemRandom().sample(range(2**31), takes)
        request = compiler.to_engine_request(compiled, seeds, audio_format="flac", meta={"app": "raag-studio"})
        return compiled, request, seeds

    def _insert_plan(self, c: sqlite3.Connection, song_id: str, rev: int, source: str, card: dict,
                     controls: dict, plan: Plan, brief: str) -> str:
        plan_id = ulid()
        c.execute("INSERT INTO plans(id, song_id, rev, source, card_json, controls_json, provenance_json, "
                  "brief_sha256, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                  (plan_id, song_id, rev, source, dumps(card), dumps(controls),
                   dumps(plan.model_dump(mode="json")["provenance"]), sha256_text(brief), now_iso()))
        return plan_id

    def _insert_round(self, c: sqlite3.Connection, song_id: str, plan_id: str, kind: str,
                      parent_take_id: Optional[str], request_text: Optional[str], compiled: dict,
                      request: dict, idem_key: str) -> tuple[str, str]:
        round_id, job_id = ulid(), ulid()
        c.execute("INSERT INTO rounds(id, song_id, plan_id, kind, parent_take_id, request_text, created_at) "
                  "VALUES(?,?,?,?,?,?,?)", (round_id, song_id, plan_id, kind, parent_take_id, request_text, now_iso()))
        stored = {"engine_request": request, "caption": compiled["caption"], "lyrics": compiled["lyrics"],
                  "effective_params": compiled["effective_params"], "effective_notes": compiled["effective_notes"],
                  "plan_sha256": compiled["plan_sha256"]}
        c.execute("INSERT INTO requests(id, round_id, compiled_json, compile_report_json, lyrics_sha256, sha256) "
                  "VALUES(?,?,?,?,?,?)",
                  (ulid(), round_id, dumps(stored), dumps(compiled["compile_report"]),
                   sha256_text(compiled["lyrics"]), sha256_text(dumps(request))))
        c.execute("INSERT INTO jobs(id, round_id, idempotency_key, state, engine, queued_at) "
                  "VALUES(?,?,?,'queued',?,?)", (job_id, round_id, idem_key, self.config.engine, now_iso()))
        return round_id, job_id

    def _replay(self, idem_key: str) -> Optional[dict]:
        row = self.db.one("SELECT j.id AS job_id, j.round_id, r.song_id, r.plan_id FROM jobs j "
                          "JOIN rounds r ON r.id=j.round_id WHERE j.idempotency_key=?", (idem_key,))
        if not row:
            return None
        plan = self.db.one("SELECT * FROM plans WHERE id=?", (row["plan_id"],))
        out = self._create_response(row["song_id"], row["round_id"], row["job_id"], plan)
        out["replayed"] = True
        return out

    def _create_response(self, song_id: str, round_id: str, job_id: str, plan_row: sqlite3.Row) -> dict:
        req = self.db.one("SELECT compile_report_json, compiled_json FROM requests WHERE round_id=?", (round_id,))
        stored = loads(req["compiled_json"])
        card = loads(plan_row["card_json"])
        return {"song_id": song_id, "round_id": round_id, "job_id": job_id, "plan_id": plan_row["id"],
                "plan_rev": plan_row["rev"], "plan": card["plan"], "card": self._card_summary(card),
                "compile_report": loads(req["compile_report_json"]), "seeds": stored["engine_request"]["seeds"],
                "job": self.job_view(job_id)}

    @staticmethod
    def _card_summary(card: dict) -> dict:
        keys = ("provider", "provider_label", "is_llm", "fallback", "matched", "notes", "unsupported",
                "needs_user_input", "applied", "changes", "notice", "planner_status")
        return {k: card[k] for k in keys if k in card}

    def _plan_from_body(self, brief: str, controls: Controls, supplied: Optional[dict]) -> tuple[Plan, dict, str]:
        """(plan, card dict, plan source). Runs the planner unless a plan was supplied."""
        if supplied is not None:
            try:
                plan = Plan.model_validate(supplied)
            except ValidationError as exc:
                raise ApiError(422, "invalid_plan", _first_error(exc), fields=_errors(exc))
            return plan, {"plan": plan.model_dump(mode="json"), "provider": "user", "provider_label": "Your plan",
                          "is_llm": False, "notes": ["Plan supplied by you; no planner was run."]}, "user_edit"
        planner = self.planner()
        try:
            if hasattr(planner, "plan_with_status"):          # smart provider wrapped in the Basic fallback
                outcome = planner.plan_with_status(brief, controls)
                card, status = outcome.card, planner_status(planner, outcome)
            else:                                              # plain Basic planner: cannot fall back
                card, status = planner.plan(brief, controls), planner_status(planner)
        except PlannerError as exc:
            raise ApiError(409, exc.code, exc.message)
        except ValueError as exc:
            raise ApiError(422, "invalid_brief", str(exc))
        card_dict = card.model_dump(mode="json")
        card_dict["planner_status"] = status
        return card.plan, card_dict, PLAN_SOURCE.get(card.provider, "rules")

    # ------------------------------------------------------------------ songs
    def create_song(self, body: CreateSongBody, header_key: Optional[str]) -> dict:
        idem = header_key or body.idempotency_key or f"auto-{ulid()}"
        replay = self._replay(idem)
        if replay:
            return replay
        controls = make_controls(_control_dict(body))
        plan, card, source = self._plan_from_body(body.brief, controls, body.plan)
        compiled, request, _ = self._compile(plan, plan.takes)
        self._admit()
        song_id = ulid()
        try:
            with self.db.tx() as c:
                c.execute("INSERT INTO songs(id, title, brief, created_at) VALUES(?,?,?,?)",
                          (song_id, body.title or make_title(body.brief), body.brief, now_iso()))
                plan_id = self._insert_plan(c, song_id, 1, source, card, controls.model_dump(exclude_none=True),
                                            plan, body.brief)
                round_id, job_id = self._insert_round(c, song_id, plan_id, "create", None, None, compiled,
                                                      request, idem)
        except sqlite3.IntegrityError:                     # lost a race with an identical request
            replay = self._replay(idem)
            if replay:
                return replay
            raise
        return self._after_enqueue(song_id, round_id, job_id, plan_id)

    def _after_enqueue(self, song_id: str, round_id: str, job_id: str, plan_id: str) -> dict:
        self.publish_job(job_id)
        if self.worker:
            self.worker.wake()
        plan_row = self.db.one("SELECT * FROM plans WHERE id=?", (plan_id,))
        return self._create_response(song_id, round_id, job_id, plan_row)

    def _song(self, song_id: str) -> sqlite3.Row:
        row = self.db.one("SELECT * FROM songs WHERE id=?", (song_id,))
        if not row:
            raise ApiError(404, "song_not_found", f"No song with id {song_id}.")
        return row

    def latest_plan(self, song_id: str) -> sqlite3.Row:
        return self.db.one("SELECT * FROM plans WHERE song_id=? ORDER BY rev DESC LIMIT 1", (song_id,))

    def plan_only(self, song_id: str, body: PlanOnlyBody) -> dict:
        """Plan (and compile) without rendering; stores the result as a new plan revision."""
        song = self._song(song_id)
        brief = body.brief or song["brief"]
        if not brief.strip():
            raise ApiError(422, "invalid_brief", "brief must not be blank")
        nulls = sorted({k for d in (body.controls, body.shape) for k, v in (d or {}).items() if v is None}
                       | {k for k in body.model_fields_set - {"brief", "controls", "shape"} if getattr(body, k) is None})
        if nulls:                                               # this endpoint only sets controls; it cannot reset one
            raise ApiError(422, "reset_not_supported",
                           f"{', '.join(nulls)}: null cannot reset a control here. "
                           "Use PATCH /api/songs/{id}/controls to put a control back to Auto.")
        prev = self.latest_plan(song_id)
        merged = dict(loads(prev["controls_json"], {}))
        merged.update(_control_dict(body))
        controls = make_controls(merged)
        plan, card, source = self._plan_from_body(brief, controls, None)
        report: Optional[dict] = None
        compile_error: Optional[dict] = None
        try:
            report = compiler.compile(plan)["compile_report"]
        except compiler.CompileError as exc:
            compile_error = {"code": "needs_user_input" if isinstance(exc, compiler.LyricsMissing) else exc.code,
                             "message": exc.message}
        with self.db.tx() as c:
            rev = c.execute("SELECT COALESCE(MAX(rev),0)+1 FROM plans WHERE song_id=?", (song_id,)).fetchone()[0]
            plan_id = self._insert_plan(c, song_id, rev, source, card, controls.model_dump(exclude_none=True),
                                        plan, brief)
        return {"song_id": song_id, "plan_id": plan_id, "plan_rev": rev, "plan": card["plan"],
                "card": self._card_summary(card), "compile_report": report, "compile_error": compile_error}

    def patch_controls(self, song_id: str, patch: dict[str, Any]) -> dict:
        """PATCH /controls: apply user edits to the latest plan as a NEW revision (no render).

        A value sets the control (provenance 'you'). null puts the control back to Auto: the field is recomputed the
        way the planner would have chosen it for the brief and the controls that are still set, with that
        recomputation's provenance, so the plan, the stored controls and the next round all agree.
        """
        self._song(song_id)
        unknown = sorted(k for k in patch if k not in Controls.model_fields)
        if unknown:
            raise ApiError(422, "invalid_controls", f"{unknown[0]}: not a control", fields=[
                {"loc": [k], "msg": "Extra inputs are not permitted"} for k in unknown])
        prev = self.latest_plan(song_id)
        prev_controls = loads(prev["controls_json"], {})
        merged = dict(prev_controls)
        resets = [k for k, v in patch.items() if v is None]
        for key, value in patch.items():
            if value is None:
                merged.pop(key, None)                        # null = back to Auto
            else:
                merged[key] = value
        controls = make_controls(merged)                     # validates every field
        changed = {k: v for k, v in patch.items() if v is not None}
        old_plan = Plan.model_validate(loads(prev["card_json"])["plan"])
        plan = apply_controls(old_plan, make_controls(changed).model_dump(exclude_none=True))
        # Choir is voices: adding or removing it as lead/support moves an Auto voice mode (never an explicit one).
        choir_moved = "voice" not in merged and choir_pick_of(Controls.model_validate(prev_controls)) != choir_pick_of(controls)
        if resets or choir_moved:
            auto = self._plan_from_body(old_plan.brief, controls, None)[0].model_dump(mode="json")
            d = plan.model_dump(mode="json")
            for key in resets:
                adopt_auto(d, auto, key, merged)
            if choir_moved:
                adopt_auto(d, auto, "voice", merged)
            try:
                plan = Plan.model_validate(d)
            except ValidationError as exc:
                raise ApiError(422, "invalid_plan", _first_error(exc), fields=_errors(exc))
        def source_of(field: str) -> str:                    # 'you' only while the field is still a choice of yours
            p = plan.provenance.get(field.split(".")[0])
            return "you" if p and p.source == "you" else "rule"

        changes = plan_changes(old_plan, plan, source_of)
        try:
            report = compiler.compile(plan)["compile_report"]
        except compiler.CompileError as exc:
            report = None
            note = {"code": exc.code, "message": exc.message}
        else:
            note = None
        notes = ["Controls edited by you."]
        if resets:
            notes.append("Back to Auto: " + ", ".join(resets) + ".")
        card = {"plan": plan.model_dump(mode="json"), "provider": "user", "provider_label": "Your edits",
                "is_llm": False, "changes": changes, "notes": notes}
        with self.db.tx() as c:
            rev = c.execute("SELECT COALESCE(MAX(rev),0)+1 FROM plans WHERE song_id=?", (song_id,)).fetchone()[0]
            plan_id = self._insert_plan(c, song_id, rev, "user_edit", card, controls.model_dump(exclude_none=True),
                                        plan, plan.brief)
        return {"song_id": song_id, "plan_id": plan_id, "plan_rev": rev, "plan": card["plan"], "changes": changes,
                "compile_report": report, "compile_error": note}

    # ------------------------------------------------------------------ rounds
    def create_round(self, song_id: str, body: RoundBody, header_key: Optional[str]) -> dict:
        if body.kind in ("variation", "cover", "repaint"):
            raise ApiError(501, "experimental_not_enabled", EXPERIMENTAL_MESSAGE)
        idem = header_key or body.idempotency_key or f"auto-{ulid()}"
        replay = self._replay(idem)
        if replay:
            return replay
        song = self._song(song_id)
        prev = self.latest_plan(song_id)                    # base plan: the newest revision ...
        parent_take = body.from_take
        if body.from_round:                                 # retry of a round: that round's plan, not the newest
            if body.from_take:
                raise ApiError(422, "ambiguous_base", "Send from_take or from_round, not both.")
            if body.kind != "another":
                raise ApiError(422, "from_round_needs_another", "from_round can only be used with kind 'another'.")
            rr = self.db.one("SELECT song_id, plan_id, parent_take_id FROM rounds WHERE id=?", (body.from_round,))
            if not rr or rr["song_id"] != song_id:
                raise ApiError(404, "round_not_found", "from_round is not a round of this song.")
            prev = self.db.one("SELECT * FROM plans WHERE id=?", (rr["plan_id"],))
            parent_take = rr["parent_take_id"]              # a retry keeps the failed round's lineage
        if body.from_take:                                  # ... unless a take is named: then THAT take's plan
            owner = self.db.one("SELECT r.song_id, r.plan_id FROM takes t JOIN rounds r ON r.id=t.round_id "
                                "WHERE t.id=?", (body.from_take,))
            if not owner or owner["song_id"] != song_id:
                raise ApiError(404, "take_not_found", "from_take is not a take of this song.")
            prev = self.db.one("SELECT * FROM plans WHERE id=?", (owner["plan_id"],))
        prev_card = loads(prev["card_json"])
        plan = Plan.model_validate(prev_card["plan"])
        new_plan_row: Optional[tuple] = None
        request_text = body.request_text
        if body.kind == "refine":
            parts = list(body.chips or [])
            if isinstance(body.patch, list):
                parts += [str(p) for p in body.patch]
            elif isinstance(body.patch, str):
                parts.append(body.patch)
            if body.request_text:
                parts.append(body.request_text)
            text = ", ".join(p.replace("_", " ") for p in parts if p and p.strip())
            if not text:
                raise ApiError(422, "nothing_to_change", "Say what to change or tap a chip.")
            request_text = text
            planner = self.planner()
            try:
                if hasattr(planner, "patch_with_status"):
                    outcome = planner.patch_with_status(plan, text)
                    patch, pstatus = outcome.patch, planner_status(planner, outcome)
                else:
                    patch, pstatus = planner.patch(plan, text), planner_status(planner)
            except PlannerError as exc:
                raise ApiError(409, exc.code, exc.message)
            if not patch.applied:
                raise ApiError(422, "nothing_to_change", "That change could not be applied.",
                               unsupported=patch.unsupported)
            plan = patch.plan
            patch_card = patch.model_dump(mode="json")
            patch_card["planner_status"] = pstatus
            patch_card.setdefault("provider_label", pstatus["used_label"])
            new_plan_row = (patch_card, PLAN_SOURCE.get(patch.provider, "rules"))
        takes = body.takes or plan.takes
        compiled, request, _ = self._compile(plan, takes)
        self._admit()
        try:
            with self.db.tx() as c:
                if new_plan_row:
                    rev = c.execute("SELECT COALESCE(MAX(rev),0)+1 FROM plans WHERE song_id=?", (song_id,)).fetchone()[0]
                    plan_id = self._insert_plan(c, song_id, rev, new_plan_row[1], new_plan_row[0],
                                                loads(prev["controls_json"], {}), plan, song["brief"])
                else:
                    plan_id = prev["id"]
                round_id, job_id = self._insert_round(c, song_id, plan_id, body.kind, parent_take, request_text,
                                                      compiled, request, idem)
        except sqlite3.IntegrityError:
            replay = self._replay(idem)
            if replay:
                return replay
            raise
        return self._after_enqueue(song_id, round_id, job_id, plan_id)

    # ------------------------------------------------------------------ jobs
    def _job_row(self, job_id: str) -> sqlite3.Row:
        row = self.db.one("SELECT j.*, r.song_id, r.kind AS round_kind FROM jobs j JOIN rounds r ON r.id=j.round_id "
                          "WHERE j.id=?", (job_id,))
        if not row:
            raise ApiError(404, "job_not_found", f"No job with id {job_id}.")
        return row

    def job_view(self, job_id: str) -> dict:
        row = self._job_row(job_id)
        progress = loads(row["progress_json"], {})
        started = row["started_at"]
        elapsed = None
        if started:
            t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
            t1 = datetime.fromisoformat((row["finished_at"] or now_iso()).replace("Z", "+00:00"))
            elapsed = round((t1 - t0).total_seconds(), 1)
        take_ids = [r["id"] for r in self.db.all("SELECT id FROM takes WHERE round_id=? ORDER BY ordinal, created_at",
                                                 (row["round_id"],))]
        return {"id": row["id"], "round_id": row["round_id"], "song_id": row["song_id"], "kind": row["round_kind"],
                "state": row["state"], "phase": row["phase"], "progress": progress,
                "reason": progress.get("reason"), "error": row["error"], "attempts": row["attempts"],
                "worker_pid": row["pid"], "engine": row["engine"], "elapsed_s": elapsed,
                "cancel_requested": bool(row["cancel_requested"]), "queued_at": row["queued_at"],
                "started_at": started, "finished_at": row["finished_at"], "take_ids": take_ids}

    def publish_job(self, job_id: str) -> None:
        try:
            self.bus.publish("job", self.job_view(job_id))
        except ApiError:
            pass

    def cancel_job(self, job_id: str) -> dict:
        row = self._job_row(job_id)
        if row["state"] == "queued":
            n = self.db.execute(
                "UPDATE jobs SET state='cancelled', phase='cancelled', cancel_requested=1, finished_at=?, "
                "error='Cancelled before it started.' WHERE id=? AND state='queued'", (now_iso(), job_id))
            if n:
                self.publish_job(job_id)
                return self.job_view(job_id)
            row = self._job_row(job_id)                       # the worker claimed it first
        if row["state"] != "running":
            raise ApiError(409, "not_cancellable", f"The job is already {row['state']}.", job=self.job_view(job_id))
        self.db.execute("UPDATE jobs SET cancel_requested=1 WHERE id=? AND state='running'", (job_id,))
        if self.worker:
            self.worker.kill_current(job_id)
        deadline = time.time() + self.config.kill_grace_s + 4
        while time.time() < deadline:
            if self._job_row(job_id)["state"] in TERMINAL_STATES:
                break
            time.sleep(0.05)
        return self.job_view(job_id)

    def is_cancel_requested(self, job_id: str) -> bool:
        row = self.db.one("SELECT cancel_requested FROM jobs WHERE id=?", (job_id,))
        return bool(row and row["cancel_requested"])

    # ------------------------------------------------------------------ views
    @staticmethod
    def feedback_state(rows: list[sqlite3.Row]) -> dict:
        state = {"favourite": False, "rating": None, "tags": [], "note": None}
        for r in rows:                                          # chronological: the latest event wins
            value = json.loads(r["value_json"])["value"]
            key = {"favourite": "favourite", "rating": "rating", "tags": "tags", "note": "note"}[r["kind"]]
            state[key] = value
        return state

    def take_view(self, row: sqlite3.Row, feedback: Optional[list[sqlite3.Row]] = None) -> dict:
        if feedback is None:
            feedback = self.db.all("SELECT * FROM feedback WHERE take_id=? ORDER BY rowid", (row["id"],))
        native = self.storage.abs(row["native_path"])
        song_id = self.db.one("SELECT song_id FROM rounds WHERE id=?", (row["round_id"],))["song_id"]
        view = {
            "id": row["id"], "round_id": row["round_id"], "song_id": song_id, "ordinal": row["ordinal"],
            "label": f"T{row['ordinal']}", "seed": row["seed"], "duration_s": row["duration_s"],
            "sample_rate": row["sample_rate"], "channels": row["channels"], "engine": row["engine"],
            "engine_rev": row["engine_rev"], "retry_of": row["retry_of"], "created_at": row["created_at"],
            "audio_url": f"/api/takes/{row['id']}/audio",
            "native_url": f"/api/takes/{row['id']}/audio?kind=native",
            "native_available": bool(native and native.is_file()),
            "native_pruned_at": row["native_pruned_at"], "native_sha256": row["native_sha256"],
            "requested_params": loads(row["requested_params_json"]),
            "effective_params": loads(row["effective_params_json"]),
            "timings": loads(row["timings_json"]), "technical_checks": loads(row["checks_json"]),
            "feedback_events": [{"kind": f["kind"], "value": json.loads(f["value_json"])["value"],
                                 "created_at": f["created_at"]} for f in feedback],
        }
        view.update(self.feedback_state(feedback))
        if row["engine"] == "fake":
            view["notice"] = "FAKE ENGINE test audio, not a real render."
        return view

    def get_take(self, take_id: str) -> sqlite3.Row:
        row = self.db.one("SELECT * FROM takes WHERE id=?", (take_id,))
        if not row:
            raise ApiError(404, "take_not_found", f"No take with id {take_id}.")
        return row

    def list_songs(self) -> list[dict]:
        out = []
        for s in self.db.all("SELECT * FROM songs WHERE archived=0 ORDER BY id DESC"):
            takes = self.db.all("SELECT t.id FROM takes t JOIN rounds r ON r.id=t.round_id WHERE r.song_id=?", (s["id"],))
            fav = 0
            for t in takes:
                fb = self.db.all("SELECT * FROM feedback WHERE take_id=? AND kind='favourite' ORDER BY rowid",
                                 (t["id"],))
                fav += 1 if fb and json.loads(fb[-1]["value_json"])["value"] else 0
            job = self.db.one("SELECT j.id, j.state, j.engine FROM jobs j JOIN rounds r ON r.id=j.round_id "
                              "WHERE r.song_id=? ORDER BY j.queued_at DESC, j.id DESC LIMIT 1", (s["id"],))
            out.append({"id": s["id"], "title": s["title"], "brief": s["brief"], "created_at": s["created_at"],
                        "archived": bool(s["archived"]), "take_count": len(takes), "favourite_count": fav,
                        "latest_job": dict(job) if job else None})
        return out

    def song_detail(self, song_id: str) -> dict:
        song = self._song(song_id)
        plans = []
        for p in self.db.all("SELECT * FROM plans WHERE song_id=? ORDER BY rev", (song_id,)):
            card = loads(p["card_json"])
            plans.append({"id": p["id"], "rev": p["rev"], "source": p["source"], "plan": card["plan"],
                          "card": self._card_summary(card), "controls": loads(p["controls_json"]),
                          "provenance": loads(p["provenance_json"]), "brief_sha256": p["brief_sha256"],
                          "created_at": p["created_at"]})
        rounds = []
        for r in self.db.all("SELECT * FROM rounds WHERE song_id=? ORDER BY id", (song_id,)):
            req = self.db.one("SELECT * FROM requests WHERE round_id=?", (r["id"],))
            job = self.db.one("SELECT id FROM jobs WHERE round_id=?", (r["id"],))
            stored = loads(req["compiled_json"])
            rounds.append({
                "id": r["id"], "kind": r["kind"], "plan_id": r["plan_id"], "parent_take_id": r["parent_take_id"],
                "request_text": r["request_text"], "created_at": r["created_at"],
                "job": self.job_view(job["id"]),
                "request": {"id": req["id"], "sha256": req["sha256"], "lyrics_sha256": req["lyrics_sha256"],
                            "seeds": stored["engine_request"]["seeds"], "caption": stored["caption"],
                            "engine_request": stored["engine_request"],
                            "compile_report": loads(req["compile_report_json"])},
                "take_ids": [t["id"] for t in self.db.all(
                    "SELECT id FROM takes WHERE round_id=? ORDER BY ordinal, created_at", (r["id"],))]})
        take_rows = self.db.all("SELECT t.* FROM takes t JOIN rounds r ON r.id=t.round_id WHERE r.song_id=? "
                                "ORDER BY t.round_id, t.ordinal, t.created_at", (song_id,))
        takes = [self.take_view(t) for t in take_rows]
        exports = [self.export_view(e) for e in self.db.all(
            "SELECT e.* FROM exports e JOIN takes t ON t.id=e.take_id JOIN rounds r ON r.id=t.round_id "
            "WHERE r.song_id=? ORDER BY e.id", (song_id,))]
        return {"song": {"id": song["id"], "title": song["title"], "brief": song["brief"],
                         "created_at": song["created_at"], "archived": bool(song["archived"])},
                "plans": plans, "rounds": rounds, "takes": takes, "exports": exports}

    def export_view(self, row: sqlite3.Row) -> dict:
        return {"id": row["id"], "take_id": row["take_id"], "format": row["format"], "fade_out_s": row["fade_out_s"],
                "trim_end_s": row["trim_end_s"], "loudness": loads(row["loudness_json"]), "sha256": row["sha256"],
                "engine": row["engine"], "created_at": row["created_at"], "url": f"/api/exports/{row['id']}/file",
                "notice": "FAKE ENGINE test audio, not a real render." if row["engine"] == "fake" else None}

    # ------------------------------------------------------------------ feedback
    def add_feedback(self, take_id: str, favourite: Optional[bool], rating: Optional[str],
                     tags: Optional[list[str]], note: Optional[str]) -> dict:
        take = self.get_take(take_id)
        events: list[tuple[str, Any]] = []
        if favourite is not None:
            events.append(("favourite", favourite))
        if rating is not None:
            events.append(("rating", rating))
        if tags is not None:
            bad = [t for t in tags if t not in FEEDBACK_TAGS]
            if bad:
                raise ApiError(422, "invalid_tags", f"Unknown reason tag(s) {bad}. Allowed: {list(FEEDBACK_TAGS)}.")
            events.append(("tags", list(dict.fromkeys(tags))))
        if note is not None:
            events.append(("note", note))
        if not events:
            raise ApiError(422, "empty_feedback", "Send at least one of favourite, rating, tags, note.")
        with self.db.tx() as c:
            for kind, value in events:
                c.execute("INSERT INTO feedback(id, take_id, kind, value_json, created_at) VALUES(?,?,?,?,?)",
                          (ulid(), take_id, kind, dumps({"value": value}), now_iso()))
        view = self.take_view(take)
        self.bus.publish("feedback", {"take_id": take_id, "song_id": view["song_id"], "favourite": view["favourite"],
                                      "rating": view["rating"]})
        return view

    # ------------------------------------------------------------------ prune
    def prune(self, older_than_days: int) -> dict:
        """Remove native audio of non-favourite takes older than N days. Previews and metadata stay."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat(
            timespec="milliseconds").replace("+00:00", "Z")
        pruned, skipped_fav, freed = [], [], 0
        for t in self.db.all("SELECT * FROM takes WHERE native_path IS NOT NULL AND created_at <= ?", (cutoff,)):
            fb = self.db.all("SELECT * FROM feedback WHERE take_id=? AND kind='favourite' ORDER BY rowid",
                             (t["id"],))
            if fb and json.loads(fb[-1]["value_json"])["value"]:
                skipped_fav.append(t["id"])
                continue
            path = self.storage.abs(t["native_path"])
            if path and path.is_file():
                freed += path.stat().st_size
                path.unlink()
            self.db.execute("UPDATE takes SET native_path=NULL, native_pruned_at=? WHERE id=?", (now_iso(), t["id"]))
            pruned.append(t["id"])
        return {"pruned_take_ids": pruned, "pruned": len(pruned), "skipped_favourites": skipped_fav,
                "freed_bytes": freed, "older_than_days": older_than_days,
                "note": "Native audio removed; MP3 previews and all metadata are kept. Favourites are never touched."}

    # ------------------------------------------------------------------ restart recovery
    def recover(self) -> dict:
        """Boot-time recovery (PRD section 9). Runs before the worker starts."""
        report = {"requeued": [], "failed": [], "killed_orphans": []}
        for row in self.db.all("SELECT * FROM jobs WHERE state IN ('running', 'interrupted')"):
            if row["pid"] and self._kill_orphan(row["pid"], row["id"]):
                report["killed_orphans"].append(row["pid"])
            with self.db.tx() as c:
                c.execute("UPDATE jobs SET state='interrupted', pid=NULL WHERE id=?", (row["id"],))
                if row["cancel_requested"]:
                    c.execute("UPDATE jobs SET state='cancelled', phase='cancelled', finished_at=?, "
                              "error='Cancelled; the server restarted before the render stopped.' WHERE id=?",
                              (now_iso(), row["id"]))
                elif row["attempts"] < MAX_ATTEMPTS:
                    c.execute("UPDATE jobs SET state='queued', phase='queued', progress_json=?, error=?, "
                              "started_at=NULL WHERE id=?",
                              (dumps({"reason": "restarted", "message": "Interrupted by a restart; re-queued."}),
                               f"Interrupted by a restart (attempt {row['attempts']} of {MAX_ATTEMPTS}); re-queued.",
                               row["id"]))
                    report["requeued"].append(row["id"])
                else:
                    c.execute("UPDATE jobs SET state='failed', phase='failed', finished_at=?, error=? WHERE id=?",
                              (now_iso(), f"Interrupted by a restart on attempt {row['attempts']} of {MAX_ATTEMPTS}; "
                               "giving up. Use 'Try again' to start a new render.", row["id"]))
                    report["failed"].append(row["id"])
        report.update(self.storage.sweep(self.db))
        for tmp in self.storage.tmp.glob("*.request.json"):
            tmp.unlink(missing_ok=True)
        return report

    def _kill_orphan(self, pid: int, job_id: str) -> bool:
        """Stop an engine process left behind by a killed server (only if it is verifiably ours)."""
        try:
            cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                                 timeout=5).stdout
        except Exception:
            return False
        if job_id not in cmd or not ("run_takes.py" in cmd or "fake_engine.py" in cmd):
            return False
        try:
            os.kill(pid, signal.SIGTERM)
            deadline = time.time() + self.config.kill_grace_s
            while time.time() < deadline:
                os.kill(pid, 0)
                time.sleep(0.1)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return True
