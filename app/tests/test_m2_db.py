"""AT-M2-01: fresh DB bootstrap (tables, WAL, user_version) plus the immutability rules of PRD section 7."""
import sqlite3

import pytest

from test_m2_support import make_config  # noqa: F401  (also puts app/ on sys.path)

from backend import db as dbmod
from backend.main import create_app

TABLES = {"songs", "plans", "rounds", "requests", "jobs", "takes", "feedback", "exports", "settings"}


def test_at_m2_01_fresh_bootstrap(tmp_path):
    config = make_config(tmp_path)
    assert not config.db_path.exists()
    create_app(config)
    assert config.db_path == tmp_path / "data" / "raag.db" and config.db_path.is_file()
    conn = sqlite3.connect(config.db_path)
    try:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert TABLES <= names
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA user_version").fetchone()[0] == dbmod.USER_VERSION > 0
        cols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
        assert {"idempotency_key", "state", "attempts", "pid", "phase", "progress_json", "error", "queued_at",
                "started_at", "finished_at"} <= cols
        # UNIQUE on the idempotency key
        idx = [r for r in conn.execute("PRAGMA index_list(jobs)") if r[2] == 1]
        assert any(conn.execute(f"PRAGMA index_info({r[1]})").fetchone()[2] == "idempotency_key" for r in idx)
    finally:
        conn.close()


def test_bootstrap_is_idempotent_and_keeps_data(tmp_path):
    config = make_config(tmp_path)
    app = create_app(config)
    app.state.svc.db.put_settings({"planner_provider": "basic"})
    create_app(config)                                             # second boot over the same file
    assert app.state.svc.db.one("SELECT COUNT(*) FROM settings")[0] == 1


def test_database_refuses_newer_schema(tmp_path):
    config = make_config(tmp_path)
    create_app(config)
    conn = sqlite3.connect(config.db_path)
    conn.execute(f"PRAGMA user_version={dbmod.USER_VERSION + 5}")
    conn.commit()
    conn.close()
    with pytest.raises(RuntimeError, match="newer"):
        create_app(config)


def test_ulids_are_26_chars_sortable_and_unique():
    ids = [dbmod.ulid(ms) for ms in range(1_700_000_000_000, 1_700_000_000_050)]
    assert all(len(i) == 26 and set(i) <= set(dbmod._CROCKFORD) for i in ids)
    assert ids == sorted(ids)
    assert len({dbmod.ulid() for _ in range(2000)}) == 2000


def _seed(db):
    now = dbmod.now_iso()
    with db.tx() as c:
        c.execute("INSERT INTO songs(id,title,brief,created_at) VALUES('S','t','b',?)", (now,))
        c.execute("INSERT INTO plans(id,song_id,rev,source,card_json,controls_json,provenance_json,brief_sha256,"
                  "created_at) VALUES('P','S',1,'rules','{}','{}','{}','x',?)", (now,))
        c.execute("INSERT INTO rounds(id,song_id,plan_id,kind,created_at) VALUES('R','S','P','create',?)", (now,))
        c.execute("INSERT INTO requests(id,round_id,compiled_json,compile_report_json,lyrics_sha256,sha256) "
                  "VALUES('Q','R','{}','{}','l','s')")
        c.execute("INSERT INTO takes(id,round_id,ordinal,seed,native_path,preview_path,requested_params_json,"
                  "effective_params_json,timings_json,checks_json,engine_rev,created_at) "
                  "VALUES('T','R',1,5,'a/b.flac','a/p.mp3','{}','{}','{}','{}','rev',?)", (now,))
        c.execute("INSERT INTO feedback(id,take_id,kind,value_json,created_at) VALUES('F','T','favourite','{}',?)", (now,))


def test_immutability_triggers(tmp_path):
    db = dbmod.Database(tmp_path / "x.db")
    _seed(db)
    for sql in ("UPDATE plans SET rev=2 WHERE id='P'", "DELETE FROM plans WHERE id='P'",
                "UPDATE requests SET sha256='z' WHERE id='Q'", "DELETE FROM requests WHERE id='Q'",
                "UPDATE takes SET seed=6 WHERE id='T'", "UPDATE takes SET checks_json='{\"x\":1}' WHERE id='T'",
                "UPDATE takes SET native_path='other' WHERE id='T'", "DELETE FROM takes WHERE id='T'",
                "UPDATE feedback SET kind='note' WHERE id='F'", "DELETE FROM feedback WHERE id='F'"):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)
    # the single allowed change on a take: its native audio may be pruned
    assert db.execute("UPDATE takes SET native_path=NULL, native_pruned_at='now' WHERE id='T'") == 1
    assert db.one("SELECT preview_path FROM takes WHERE id='T'")["preview_path"] == "a/p.mp3"
    # feedback is appended, never edited
    db.execute("INSERT INTO feedback(id,take_id,kind,value_json,created_at) VALUES('F2','T','note','{}','now')")
    assert db.one("SELECT COUNT(*) FROM feedback")[0] == 2


def test_idempotency_key_is_unique(tmp_path):
    db = dbmod.Database(tmp_path / "x.db")
    _seed(db)
    db.execute("INSERT INTO jobs(id,round_id,idempotency_key,state,queued_at) VALUES('J1','R','k','queued','now')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO jobs(id,round_id,idempotency_key,state,queued_at) VALUES('J2','R','k','queued','now')")
