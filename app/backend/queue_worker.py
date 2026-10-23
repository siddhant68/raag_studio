"""The render worker (PRD section 9): ONE heavy job at a time, engine run as a subprocess.

    queued job -> pre-start gates (disk, MPS, :8388 video queue) -> subprocess
    ACE_PYTHON app/engine/run_takes.py <request.json> <round>.partial
    -> JSONL events on stdout (phases, SSE) -> rename .partial -> ffprobe/ffmpeg checks + previews
    -> takes rows + job succeeded (one transaction).

Cancel is a real kill (SIGTERM, then SIGKILL after the grace period). A take that fails the
TECHNICAL checks gets one automatic retry with a new seed; taste never triggers a retry.
Under RAAG_ENGINE=fake the same code runs app/engine/fake_engine.py and every row says "fake".
"""
from __future__ import annotations

import json
import os
import random
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Optional

from . import media
from .db import dumps, loads, now_iso, ulid
from .jobs import Service
from .settings import ENGINE_DIR

ENGINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false",
              "OMP_NUM_THREADS": "4"}


class Outcome:
    """Result of one engine subprocess."""

    def __init__(self) -> None:
        self.returncode: Optional[int] = None
        self.takes_done: list[dict] = []
        self.saw_done = False
        self.error: Optional[dict] = None
        self.tail: deque = deque(maxlen=12)
        self.timed_out = False
        self.cancelled = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.saw_done and not self.timed_out and not self.cancelled

    def failure_message(self) -> str:
        if self.timed_out:
            return "The render took too long and was stopped."
        if self.error:
            return f"{self.error.get('code', 'error')}: {self.error.get('message', '')}".strip()
        tail = " | ".join(list(self.tail)[-4:])
        return f"The engine exited with code {self.returncode} before finishing. {tail}".strip()


class _Running:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.proc: Optional[subprocess.Popen] = None
        self.killer: Optional[threading.Thread] = None


class QueueWorker:
    def __init__(self, svc: Service):
        self.svc = svc
        self.config, self.db, self.storage, self.probe = svc.config, svc.db, svc.storage, svc.probe
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current: Optional[_Running] = None
        self._lock = threading.Lock()
        self._last_wait: Optional[str] = None

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="raag-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        with self._lock:
            cur = self._current
        if cur and cur.proc and cur.proc.poll() is None:
            self._terminate(cur.proc)
        if self._thread:
            self._thread.join(timeout=10)

    def wake(self) -> None:
        self._wake.set()

    # ------------------------------------------------------------------ kill helpers
    def _terminate(self, proc: subprocess.Popen) -> None:
        """SIGTERM now, SIGKILL after the grace period (blocking)."""
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=self.config.kill_grace_s)
        except subprocess.TimeoutExpired:
            proc.kill()
        except ProcessLookupError:
            pass

    def kill_current(self, job_id: str) -> bool:
        """Called from the API thread: stop the engine of a running job without blocking the caller."""
        with self._lock:
            cur = self._current
        if not cur or cur.job_id != job_id or not cur.proc or cur.proc.poll() is not None:
            return False                       # not spawned yet (the worker checks the flag) or already over
        cur.killer = threading.Thread(target=self._terminate, args=(cur.proc,), daemon=True)
        cur.killer.start()
        return True

    # ------------------------------------------------------------------ main loop
    def _loop(self) -> None:
        while not self._stop.is_set():
            job = self.db.one("SELECT j.*, r.song_id FROM jobs j JOIN rounds r ON r.id=j.round_id "
                              "WHERE j.state='queued' ORDER BY j.queued_at, j.id LIMIT 1")
            if not job:
                self._wake.wait(self.config.poll_interval_s)
                self._wake.clear()
                continue
            try:
                verdict = self._gates(job)
                if verdict is None:
                    self._last_wait = None
                    self._run_job(job)
                elif verdict[0] == "wait":
                    self._note_wait(job, verdict[1], verdict[2])
                    self._stop.wait(self.config.poll_interval_s)
                else:
                    self._fail_queued(job, verdict[1])
            except Exception as exc:           # a worker bug must never wedge the queue
                self._fail(job["id"], f"internal error: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ gates
    def _gates(self, job) -> Optional[tuple]:
        """None = go. ('wait', reason, message) keeps the job queued. ('fail', message) fails it."""
        s = self.svc.settings()
        free = self.probe.disk_free_gib()
        if free < s["min_disk_gib"]:
            return ("fail", f"Only {free} GiB of disk is free; at least {s['min_disk_gib']} GiB is needed to render.")
        vq = self.probe.video_queue(s["video_queue_url"])
        if vq["state"] == "busy":
            return ("wait", "mac_busy", f"The video generator is busy ({vq.get('running', 0)} running, "
                    f"{vq.get('pending', 0)} pending). Waiting for it to finish; ACE and ComfyUI must not overlap.")
        if vq["state"] != "idle":
            return ("wait", "video_queue_unknown", f"Cannot tell whether the video generator is idle ({vq.get('detail')}). "
                    "Waiting rather than risk running out of memory.")
        if not self.config.is_fake:
            if not self.probe.ace_python.is_file():
                return ("fail", f"ACE python not found at {self.probe.ace_python}.")
            mps = self.probe.mps(fresh=True)
            if not mps.get("available"):
                return ("fail", "Apple MPS (GPU) is not available to this process, and Raag Studio never falls back "
                        f"to CPU. {mps.get('detail', '')}")
            cp = self.probe.checkpoints()
            if not cp["all_present"]:
                missing = [k for k, v in cp["files"].items() if not v]
                return ("fail", f"ACE-Step weights are missing: {missing}")
        return None

    def _note_wait(self, job, reason: str, message: str) -> None:
        if self._last_wait == f"{job['id']}:{reason}":
            return
        self._last_wait = f"{job['id']}:{reason}"
        self.db.execute("UPDATE jobs SET phase='waiting', progress_json=? WHERE id=? AND state='queued'",
                        (dumps({"reason": reason, "message": message}), job["id"]))
        self.svc.publish_job(job["id"])

    def _fail_queued(self, job, message: str) -> None:
        self.db.execute("UPDATE jobs SET state='failed', phase='failed', error=?, finished_at=?, "
                        "progress_json=? WHERE id=? AND state='queued'",
                        (message, now_iso(), dumps({"reason": "gate_failed"}), job["id"]))
        self.svc.publish_job(job["id"])

    def _fail(self, job_id: str, message: str) -> None:
        self.db.execute("UPDATE jobs SET state='failed', phase='failed', error=?, finished_at=?, pid=NULL "
                        "WHERE id=? AND state IN ('queued','running')", (message, now_iso(), job_id))
        self.svc.publish_job(job_id)

    # ------------------------------------------------------------------ one job
    def _set_progress(self, job_id: str, phase: str, **fields: Any) -> None:
        row = self.db.one("SELECT progress_json FROM jobs WHERE id=?", (job_id,))
        progress = loads(row["progress_json"], {}) if row else {}
        progress.pop("reason", None)
        progress.pop("message", None)
        progress.update(fields)
        self.db.execute("UPDATE jobs SET phase=?, progress_json=? WHERE id=?", (phase, dumps(progress), job_id))
        self.svc.publish_job(job_id)

    def _run_job(self, job) -> None:
        job_id, round_id, song_id = job["id"], job["round_id"], job["song_id"]
        n = self.db.execute("UPDATE jobs SET state='running', attempts=attempts+1, started_at=?, phase='starting', "
                            "progress_json=?, error=NULL, pid=NULL WHERE id=? AND state='queued'",
                            (now_iso(), dumps({"memory": self.probe.memory()}), job_id))
        if not n:                                    # cancelled between the read and the claim
            return
        self.svc.publish_job(job_id)
        req = self.db.one("SELECT compiled_json FROM requests WHERE round_id=?", (round_id,))
        engine_request = loads(req["compiled_json"])["engine_request"]
        settings = self.svc.settings()
        partial = self.storage.partial_dir(song_id, round_id)
        final = self.storage.round_dir(song_id, round_id)
        (self.storage.runs / song_id).mkdir(parents=True, exist_ok=True)
        self.storage.remove_tree(partial)

        outcome = self._run_engine(job_id, engine_request, partial, settings["job_timeout_s"])
        if self._stop.is_set() and not self.svc.is_cancel_requested(job_id):
            return                          # server shutting down: leave 'running'; boot recovery re-queues it
        if self.svc.is_cancel_requested(job_id) or outcome.cancelled:
            return self._finish_cancelled(job_id, partial)
        if not outcome.ok or len(outcome.takes_done) != len(engine_request["seeds"]):
            return self._fail_running(job_id, outcome.failure_message() +
                                      " (the partial render is kept until the next start for inspection)")

        self.storage.finalize(partial, final)
        self._set_progress(job_id, "checking")
        result = json.loads((final / "result.json").read_text())
        rows = [self._process_take(final, rec, engine_request, result, settings, None) for rec in result["takes"]]
        retry_info = None
        failing = [r for r in rows if r["checks"]["status"] == "failed"]
        if failing and settings["retry_on_technical_failure"] and not self.svc.is_cancel_requested(job_id):
            retry_info = self._retry_failed(job_id, song_id, round_id, final, engine_request, rows, failing, settings)
        if self.svc.is_cancel_requested(job_id):
            self.storage.remove_tree(final)
            return self._finish_cancelled(job_id, partial)
        self._commit_success(job_id, round_id, rows, result, retry_info)

    # ------------------------------------------------------------------ engine subprocess
    def _engine_cmd(self, request_file: Path, out_dir: Path) -> list[str]:
        if self.config.is_fake:
            return [sys.executable, str(ENGINE_DIR / "fake_engine.py"), str(request_file), str(out_dir)]
        return [str(self.probe.ace_python), str(ENGINE_DIR / "run_takes.py"), str(request_file), str(out_dir)]

    def _run_engine(self, job_id: str, engine_request: dict, out_dir: Path, timeout_s: float,
                    attempt_label: str = "") -> Outcome:
        outcome = Outcome()
        request_file = self.storage.tmp / f"{job_id}{attempt_label}.request.json"
        request_file.write_text(json.dumps(engine_request, ensure_ascii=False, sort_keys=True))
        env = {**os.environ, **ENGINE_ENV}
        cur = _Running(job_id)
        with self._lock:
            self._current = cur
        timer: Optional[threading.Timer] = None
        try:
            proc = subprocess.Popen(self._engine_cmd(request_file, out_dir), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1, env=env, start_new_session=True,
                                    cwd=str(self.config.data_dir))
            cur.proc = proc
            self.db.execute("UPDATE jobs SET pid=? WHERE id=?", (proc.pid, job_id))
            self.svc.publish_job(job_id)
            if self.svc.is_cancel_requested(job_id):         # cancel arrived before the process existed
                outcome.cancelled = True
                self.kill_current(job_id)

            def on_timeout() -> None:
                outcome.timed_out = True
                self._terminate(proc)
            timer = threading.Timer(timeout_s, on_timeout)
            timer.daemon = True
            timer.start()
            total = len(engine_request["seeds"])
            for line in proc.stdout:
                self._on_line(job_id, line.rstrip("\n"), outcome, total)
            outcome.returncode = proc.wait()
            if cur.killer:
                cur.killer.join(timeout=self.config.kill_grace_s + 2)
        finally:
            if timer:
                timer.cancel()
            with self._lock:
                self._current = None
            request_file.unlink(missing_ok=True)
        if self.svc.is_cancel_requested(job_id):
            outcome.cancelled = True
        return outcome

    def _on_line(self, job_id: str, line: str, outcome: Outcome, total: int) -> None:
        try:
            ev = json.loads(line)
            kind = ev["event"]
        except (ValueError, KeyError, TypeError):
            if line.strip():
                outcome.tail.append(line.strip()[:200])         # library noise before the harness redirects it
            return
        if kind == "model_loading":
            self._set_progress(job_id, "loading_model", takes_total=total)
        elif kind == "model_ready":
            self._set_progress(job_id, "loading_model", model_load_s=ev.get("load_s"), device=ev.get("device"))
        elif kind == "take_start":
            self._set_progress(job_id, "rendering", take_index=ev["index"], takes_total=ev.get("of", total))
        elif kind == "take_done":
            outcome.takes_done.append(ev)
            self._set_progress(job_id, "rendering", takes_completed=len(outcome.takes_done), takes_total=total,
                               last_take={"index": ev["index"], "seed": ev["seed"], "duration_s": ev.get("duration_s"),
                                          "wall_s": ev.get("wall_s")})
            self.svc.bus.publish("take_done", {"job_id": job_id, "index": ev["index"], "seed": ev["seed"],
                                               "duration_s": ev.get("duration_s"), "wall_s": ev.get("wall_s"),
                                               "engine": self.config.engine})
        elif kind == "done":
            outcome.saw_done = True
        elif kind == "error":
            outcome.error = ev

    # ------------------------------------------------------------------ takes: checks, previews, retry
    def _process_take(self, final: Path, rec: dict, engine_request: dict, result: dict, settings: dict,
                      retry_of: Optional[str]) -> dict:
        native = final / rec["file"]
        expected = float(engine_request["params"]["duration"])
        checks = media.technical_checks(native, expected, silence_warn=settings["silence_warn_fraction"],
                                        silence_fail=settings["silence_fail_fraction"])
        t0 = time.time()
        preview = final / f"preview_{rec['index']:02d}_s{rec['seed']}.mp3"
        preview_error = None
        try:
            media.make_preview(native, preview)
        except media.MediaError as exc:
            preview, preview_error = None, str(exc)
        facts = checks["facts"]
        return {
            "id": ulid(), "ordinal": rec["index"], "seed": rec["seed"], "rec": rec, "native": native,
            "preview": preview, "preview_error": preview_error, "checks": checks, "retry_of": retry_of,
            "sha256": media.sha256_file(native), "preview_s": round(time.time() - t0, 3),
            "duration_s": facts.get("duration_s"), "sample_rate": facts.get("sample_rate"),
            "channels": facts.get("channels"),
        }

    def _retry_failed(self, job_id: str, song_id: str, round_id: str, final: Path, engine_request: dict,
                      rows: list[dict], failing: list[dict], settings: dict) -> dict:
        """ONE automatic retry, new seeds, only for takes that failed the technical checks."""
        used = {r["seed"] for r in rows}
        rng = random.SystemRandom()
        new_seeds: list[int] = []
        while len(new_seeds) < len(failing):
            s = rng.randrange(2**31)
            if s not in used and s not in new_seeds:
                new_seeds.append(s)
        self._set_progress(job_id, "retrying", retry_for=[r["ordinal"] for r in failing],
                           retry_reason="technical checks failed: " + "; ".join(
                               f"T{r['ordinal']} {','.join(r['checks']['failures'])}" for r in failing))
        request = {**engine_request, "seeds": new_seeds,
                   "meta": {**(engine_request.get("meta") or {}), "retry": 1, "round_id": round_id}}
        retry_dir = self.storage.partial_dir(song_id, round_id, ".retry1")
        self.storage.remove_tree(retry_dir)
        outcome = self._run_engine(job_id, request, retry_dir, settings["job_timeout_s"], attempt_label=".retry1")
        info: dict = {"attempted": True, "for_ordinals": [r["ordinal"] for r in failing], "new_seeds": new_seeds,
                      "ok": outcome.ok}
        if not outcome.ok or len(outcome.takes_done) != len(new_seeds):
            info["error"] = outcome.failure_message()
            return info
        result = json.loads((retry_dir / "result.json").read_text())
        for bad, rec in zip(failing, result["takes"]):
            ext = rec["file"].rsplit(".", 1)[-1]
            name = f"take_{bad['ordinal']:02d}_s{rec['seed']}.{ext}"
            os.replace(retry_dir / rec["file"], final / name)
            rec = {**rec, "file": name, "index": bad["ordinal"]}
            rows.append(self._process_take(final, rec, request, result, settings, bad["id"]))
        for keep in ("result.json", "engine.log"):
            os.replace(retry_dir / keep, final / f"retry1_{keep}")
        self.storage.remove_tree(retry_dir)
        return info

    # ------------------------------------------------------------------ terminal transitions
    def _commit_success(self, job_id: str, round_id: str, rows: list[dict], result: dict,
                        retry_info: Optional[dict]) -> None:
        engine_rev = self.probe.engine_rev()
        params = loads(self.db.one("SELECT compiled_json FROM requests WHERE round_id=?", (round_id,))
                       ["compiled_json"])["engine_request"]["params"]
        effective = result.get("effective_params") or params
        stamp = now_iso()
        failed_checks = [r["ordinal"] for r in rows if r["checks"]["status"] == "failed"]
        with self.db.tx() as c:
            for r in rows:
                rec = r["rec"]
                timings = {"wall_s": rec.get("wall_s"), "pipeline_s": rec.get("pipeline_s"),
                           "model_load_s": result.get("model_load_s"), "total_wall_s": result.get("total_wall_s"),
                           "peak_rss_mb": rec.get("peak_rss_mb", result.get("peak_rss_mb")),
                           "preview_s": r["preview_s"], "time_costs": rec.get("time_costs")}
                checks = dict(r["checks"])
                if r["preview_error"]:
                    checks["preview_error"] = r["preview_error"]
                c.execute(
                    "INSERT INTO takes(id, round_id, ordinal, seed, native_path, preview_path, duration_s, sample_rate, "
                    "channels, requested_params_json, effective_params_json, timings_json, checks_json, engine_rev, "
                    "engine, native_sha256, retry_of, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r["id"], round_id, r["ordinal"], r["seed"], self.storage.rel(r["native"]),
                     self.storage.rel(r["preview"]) if r["preview"] else None, r["duration_s"], r["sample_rate"],
                     r["channels"], dumps({**params, "seed": r["seed"]}), dumps({**effective, "seed": r["seed"]}),
                     dumps(timings), dumps(checks), engine_rev, self.config.engine, r["sha256"], r["retry_of"], stamp))
            progress = {"takes_completed": len(rows), "technical_failures": failed_checks, "retry": retry_info,
                        "total_wall_s": result.get("total_wall_s"), "model_load_s": result.get("model_load_s")}
            n = c.execute("UPDATE jobs SET state='succeeded', phase='done', finished_at=?, pid=NULL, progress_json=? "
                          "WHERE id=? AND state='running'", (stamp, dumps(progress), job_id)).rowcount
            if not n:
                raise RuntimeError("job is no longer running; takes not recorded")
        self.svc.publish_job(job_id)
        views = [self.svc.take_view(self.svc.get_take(r["id"])) for r in rows]
        self.svc.bus.publish("takes_ready", {"job_id": job_id, "round_id": round_id, "engine": self.config.engine,
                                             "takes": views})

    def _fail_running(self, job_id: str, message: str) -> None:
        self.db.execute("UPDATE jobs SET state='failed', phase='failed', error=?, finished_at=?, pid=NULL "
                        "WHERE id=? AND state='running'", (message, now_iso(), job_id))
        self.svc.publish_job(job_id)

    def _finish_cancelled(self, job_id: str, partial: Path) -> None:
        self.storage.remove_tree(partial)
        self.db.execute("UPDATE jobs SET state='cancelled', phase='cancelled', finished_at=?, pid=NULL, "
                        "error='Cancelled by you.' WHERE id=? AND state='running'", (now_iso(), job_id))
        self.svc.publish_job(job_id)
