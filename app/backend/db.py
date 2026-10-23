"""SQLite (WAL) store for Raag Studio (PRD v2 section 7).

One short-lived connection per use (WAL lets the API threads and the worker
share the file). `plans`, `requests` and `takes` are immutable (triggers abort
updates; the only mutable take columns are the pruned-native markers), `feedback`
is append-only. ids are ULIDs.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

USER_VERSION = 1
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


# ---------------------------------------------------------------------------
# ids and time
# ---------------------------------------------------------------------------
_ulid_lock = threading.Lock()
_ulid_last = [0, 0]                      # [timestamp ms, 80-bit random part] of the previous id


def ulid(ms: Optional[int] = None) -> str:
    """26-char ULID: 48-bit millisecond timestamp + 80 random bits, Crockford base32.

    Monotonic within the process: two ids made in the same millisecond still sort in creation order.
    """
    with _ulid_lock:
        now = int(time.time() * 1000) if ms is None else ms
        if ms is None and now <= _ulid_last[0]:
            now, rand = _ulid_last[0], (_ulid_last[1] + 1) & ((1 << 80) - 1)
        else:
            rand = secrets.randbits(80)
        if ms is None:
            _ulid_last[0], _ulid_last[1] = now, rand
    value = (now << 80) | rand
    return "".join(_CROCKFORD[(value >> shift) & 31] for shift in range(125, -1, -5))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def loads(text: Optional[str], default: Any = None) -> Any:
    return default if text is None else json.loads(text)


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS songs(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, brief TEXT NOT NULL,
  created_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0);

CREATE TABLE IF NOT EXISTS plans(
  id TEXT PRIMARY KEY, song_id TEXT NOT NULL REFERENCES songs(id), rev INTEGER NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('rules','claude_cli','anthropic_api','user_edit','recipe')),
  card_json TEXT NOT NULL, controls_json TEXT NOT NULL, provenance_json TEXT NOT NULL,
  brief_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(song_id, rev));

CREATE TABLE IF NOT EXISTS rounds(
  id TEXT PRIMARY KEY, song_id TEXT NOT NULL REFERENCES songs(id), plan_id TEXT NOT NULL REFERENCES plans(id),
  kind TEXT NOT NULL CHECK(kind IN ('create','another','refine','variation','cover','repaint')),
  parent_take_id TEXT, request_text TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS requests(
  id TEXT PRIMARY KEY, round_id TEXT NOT NULL UNIQUE REFERENCES rounds(id),
  compiled_json TEXT NOT NULL, compile_report_json TEXT NOT NULL,
  lyrics_sha256 TEXT NOT NULL, sha256 TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, round_id TEXT NOT NULL REFERENCES rounds(id),
  idempotency_key TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL CHECK(state IN ('queued','running','succeeded','failed','cancelled','interrupted')),
  attempts INTEGER NOT NULL DEFAULT 0, pid INTEGER, phase TEXT NOT NULL DEFAULT 'queued',
  progress_json TEXT NOT NULL DEFAULT '{}', error TEXT,
  engine TEXT NOT NULL DEFAULT 'real', cancel_requested INTEGER NOT NULL DEFAULT 0,
  queued_at TEXT NOT NULL, started_at TEXT, finished_at TEXT);
CREATE INDEX IF NOT EXISTS jobs_state ON jobs(state, queued_at);

CREATE TABLE IF NOT EXISTS takes(
  id TEXT PRIMARY KEY, round_id TEXT NOT NULL REFERENCES rounds(id), ordinal INTEGER NOT NULL,
  seed INTEGER NOT NULL, native_path TEXT, preview_path TEXT, duration_s REAL, sample_rate INTEGER, channels INTEGER,
  requested_params_json TEXT NOT NULL, effective_params_json TEXT NOT NULL,
  timings_json TEXT NOT NULL, checks_json TEXT NOT NULL, engine_rev TEXT NOT NULL,
  engine TEXT NOT NULL DEFAULT 'real', native_sha256 TEXT, retry_of TEXT,
  native_pruned_at TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS takes_round ON takes(round_id, ordinal);

CREATE TABLE IF NOT EXISTS feedback(
  id TEXT PRIMARY KEY, take_id TEXT NOT NULL REFERENCES takes(id),
  kind TEXT NOT NULL CHECK(kind IN ('favourite','rating','tags','note')),
  value_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS feedback_take ON feedback(take_id, created_at);

CREATE TABLE IF NOT EXISTS exports(
  id TEXT PRIMARY KEY, take_id TEXT NOT NULL REFERENCES takes(id), format TEXT NOT NULL,
  fade_out_s REAL NOT NULL DEFAULT 0, trim_end_s REAL NOT NULL DEFAULT 0,
  loudness_json TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL,
  engine TEXT NOT NULL DEFAULT 'real', created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value_json TEXT NOT NULL);

CREATE TRIGGER IF NOT EXISTS plans_immutable BEFORE UPDATE ON plans
  BEGIN SELECT RAISE(ABORT, 'plans are immutable'); END;
CREATE TRIGGER IF NOT EXISTS plans_nodelete BEFORE DELETE ON plans
  BEGIN SELECT RAISE(ABORT, 'plans are immutable'); END;
CREATE TRIGGER IF NOT EXISTS requests_immutable BEFORE UPDATE ON requests
  BEGIN SELECT RAISE(ABORT, 'requests are immutable'); END;
CREATE TRIGGER IF NOT EXISTS requests_nodelete BEFORE DELETE ON requests
  BEGIN SELECT RAISE(ABORT, 'requests are immutable'); END;
CREATE TRIGGER IF NOT EXISTS takes_nodelete BEFORE DELETE ON takes
  BEGIN SELECT RAISE(ABORT, 'takes are immutable'); END;
CREATE TRIGGER IF NOT EXISTS takes_immutable BEFORE UPDATE ON takes
  WHEN NEW.id IS NOT OLD.id OR NEW.round_id IS NOT OLD.round_id OR NEW.ordinal IS NOT OLD.ordinal
    OR NEW.seed IS NOT OLD.seed OR NEW.preview_path IS NOT OLD.preview_path
    OR NEW.duration_s IS NOT OLD.duration_s OR NEW.sample_rate IS NOT OLD.sample_rate
    OR NEW.channels IS NOT OLD.channels OR NEW.requested_params_json IS NOT OLD.requested_params_json
    OR NEW.effective_params_json IS NOT OLD.effective_params_json OR NEW.timings_json IS NOT OLD.timings_json
    OR NEW.checks_json IS NOT OLD.checks_json OR NEW.engine_rev IS NOT OLD.engine_rev
    OR NEW.engine IS NOT OLD.engine OR NEW.native_sha256 IS NOT OLD.native_sha256
    OR NEW.retry_of IS NOT OLD.retry_of OR NEW.created_at IS NOT OLD.created_at
    OR (NEW.native_path IS NOT OLD.native_path AND NEW.native_path IS NOT NULL)
  BEGIN SELECT RAISE(ABORT, 'takes are immutable (only the native audio may be pruned)'); END;
CREATE TRIGGER IF NOT EXISTS feedback_append_only_u BEFORE UPDATE ON feedback
  BEGIN SELECT RAISE(ABORT, 'feedback is append-only'); END;
CREATE TRIGGER IF NOT EXISTS feedback_append_only_d BEFORE DELETE ON feedback
  BEGIN SELECT RAISE(ABORT, 'feedback is append-only'); END;
CREATE TRIGGER IF NOT EXISTS exports_immutable BEFORE UPDATE ON exports
  BEGIN SELECT RAISE(ABORT, 'exports are immutable'); END;
"""


class Database:
    """Thin wrapper: open the file, create the schema once, hand out connections."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version > USER_VERSION:
                raise RuntimeError(f"database user_version {version} is newer than this app ({USER_VERSION})")
            c.executescript(SCHEMA)
            c.execute(f"PRAGMA user_version={USER_VERSION}")

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        """Autocommit connection (use `tx()` for multi-statement atomic writes)."""
        c = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=10000")
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """BEGIN IMMEDIATE ... COMMIT; rolls back on any exception."""
        with self.conn() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                c.execute("ROLLBACK")
                raise
            c.execute("COMMIT")

    # -- small helpers -------------------------------------------------------
    def one(self, sql: str, args: tuple = ()) -> Optional[sqlite3.Row]:
        with self.conn() as c:
            return c.execute(sql, args).fetchone()

    def all(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.conn() as c:
            return c.execute(sql, args).fetchall()

    def execute(self, sql: str, args: tuple = ()) -> int:
        """Run one write statement; returns rowcount."""
        with self.conn() as c:
            return c.execute(sql, args).rowcount

    # -- settings ------------------------------------------------------------
    def get_settings(self, defaults: dict[str, Any]) -> dict[str, Any]:
        out = dict(defaults)
        for row in self.all("SELECT key, value_json FROM settings"):
            if row["key"] in out:
                out[row["key"]] = json.loads(row["value_json"])
        return out

    def put_settings(self, values: dict[str, Any]) -> None:
        with self.tx() as c:
            for key, value in values.items():
                c.execute("INSERT INTO settings(key, value_json) VALUES(?, ?) "
                          "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", (key, dumps(value)))


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        os.makedirs(p, exist_ok=True)
