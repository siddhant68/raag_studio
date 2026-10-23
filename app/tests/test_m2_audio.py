"""AT-M2-08 (audio endpoint, native untouched), AT-M2-09 (feedback, prune), AT-M2-10 (exports) and the technical checks."""
import hashlib
import subprocess
from pathlib import Path

import pytest

from test_m2_support import (client_for, create_and_wait, decodes_clean, ffprobe, loudness, make_wav)

from backend import media


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(c, detail):
    """Everything about the takes that must never change: DB rows and file hashes."""
    rows = {r["id"]: tuple(r) for r in c.svc.db.all("SELECT * FROM takes")}
    files = {}
    for t in detail["takes"]:
        row = c.svc.get_take(t["id"])
        for key in ("native_path", "preview_path"):
            files[(t["id"], key)] = sha(c.svc.storage.abs(row[key]))
    return rows, files


# --------------------------------------------------------------------------- AT-M2-08
def test_at_m2_08_range_requests(tmp_path):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=10, takes=1)
        take = detail["takes"][0]
        row = c.svc.get_take(take["id"])
        for kind, rel, mime in (("preview", row["preview_path"], "audio/mpeg"), ("native", row["native_path"], "audio/flac")):
            path = c.svc.storage.abs(rel)
            data = path.read_bytes()
            size = len(data)
            url = f"/api/takes/{take['id']}/audio?kind={kind}"

            full = c.get(url)
            assert full.status_code == 200 and full.content == data
            assert full.headers["accept-ranges"] == "bytes" and full.headers["content-type"] == mime

            part = c.get(url, headers={"Range": "bytes=0-99"})
            assert part.status_code == 206
            assert part.headers["content-range"] == f"bytes 0-99/{size}"
            assert part.headers["content-length"] == "100" and part.content == data[:100]

            mid = c.get(url, headers={"Range": "bytes=1000-1999"})
            assert mid.status_code == 206 and mid.headers["content-range"] == f"bytes 1000-1999/{size}"
            assert mid.content == data[1000:2000]

            tail = c.get(url, headers={"Range": f"bytes={size - 50}-"})
            assert tail.status_code == 206 and tail.headers["content-range"] == f"bytes {size - 50}-{size - 1}/{size}"
            assert tail.content == data[-50:]

            suffix = c.get(url, headers={"Range": "bytes=-64"})
            assert suffix.status_code == 206 and suffix.content == data[-64:]

            beyond = c.get(url, headers={"Range": f"bytes={size + 10}-"})
            assert beyond.status_code == 416 and beyond.headers["content-range"] == f"bytes */{size}"
        assert c.get(f"/api/takes/{take['id']}/audio?kind=bogus").status_code == 422


def test_at_m2_08_native_sha256_unchanged_by_feedback_and_export(tmp_path):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=10, takes=1)
        take = detail["takes"][0]
        native = c.svc.storage.abs(c.svc.get_take(take["id"])["native_path"])
        before = sha(native)
        assert before == take["native_sha256"]
        mtime = native.stat().st_mtime_ns
        c.post(f"/api/takes/{take['id']}/feedback", json={"favourite": True, "rating": "love"})
        for fmt in ("mp3", "wav"):
            assert c.post(f"/api/takes/{take['id']}/exports",
                          json={"format": fmt, "end_fade_s": 2, "trim_end_s": 1}).status_code == 201
        c.get(f"/api/takes/{take['id']}/audio?kind=native", headers={"Range": "bytes=0-10"})
        assert sha(native) == before and native.stat().st_mtime_ns == mtime
        assert native.suffix == ".flac"                          # still the engine's FLAC, never rewritten as WAV


# --------------------------------------------------------------------------- AT-M2-09
def test_at_m2_09_feedback_appends_and_touches_nothing(tmp_path):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=10, takes=2)
        a, b = detail["takes"]
        rows0, files0 = snapshot(c, detail)

        r = c.post(f"/api/takes/{a['id']}/feedback", json={"favourite": True})
        assert r.status_code == 200 and r.json()["favourite"] is True
        c.post(f"/api/takes/{a['id']}/feedback", json={"rating": "love", "tags": ["melody", "voice"], "note": "so warm"})
        c.post(f"/api/takes/{a['id']}/feedback", json={"rating": "fine"})                 # a later opinion appends
        r = c.post(f"/api/takes/{a['id']}/feedback", json={"favourite": False})            # un-heart appends too
        view = r.json()
        assert view["favourite"] is False and view["rating"] == "fine" and view["tags"] == ["melody", "voice"]
        assert view["note"] == "so warm"
        events = view["feedback_events"]
        assert [e["kind"] for e in events] == ["favourite", "rating", "tags", "note", "rating", "favourite"]
        assert c.svc.db.one("SELECT COUNT(*) FROM feedback WHERE take_id=?", (a["id"],))[0] == 6
        assert c.svc.db.one("SELECT COUNT(*) FROM feedback WHERE take_id=?", (b["id"],))[0] == 0   # no cross-take transfer

        assert c.post(f"/api/takes/{a['id']}/feedback", json={}).status_code == 422
        assert c.post(f"/api/takes/{a['id']}/feedback", json={"tags": ["nonsense"]}).status_code == 422
        assert c.post(f"/api/takes/{a['id']}/feedback", json={"rating": "great"}).status_code == 422
        assert c.post("/api/takes/NOPE/feedback", json={"favourite": True}).status_code == 404

        rows1, files1 = snapshot(c, detail)
        assert rows1 == rows0 and files1 == files0                # takes rows and files untouched


def test_at_m2_09_prune_requires_confirm_and_never_touches_favourites(tmp_path):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=10, takes=3)
        fav, plain1, plain2 = detail["takes"]
        c.post(f"/api/takes/{fav['id']}/feedback", json={"favourite": True})
        paths = {t["id"]: (c.svc.storage.abs(c.svc.get_take(t["id"])["native_path"]),
                           c.svc.storage.abs(c.svc.get_take(t["id"])["preview_path"])) for t in detail["takes"]}

        assert c.post("/api/admin/prune", json={"older_than_days": 0}).status_code == 400
        assert c.post("/api/admin/prune", json={"older_than_days": 0, "confirm": False}).status_code == 400
        assert c.post("/api/admin/prune", json={"confirm": True}).status_code == 422          # N is required
        assert all(n.is_file() for n, _ in paths.values())                                     # nothing happened yet

        assert c.post("/api/admin/prune", json={"older_than_days": 365, "confirm": True}).json()["pruned"] == 0
        r = c.post("/api/admin/prune", json={"older_than_days": 0, "confirm": True})
        out = r.json()
        assert r.status_code == 200 and out["pruned"] == 2 and out["skipped_favourites"] == [fav["id"]]
        assert set(out["pruned_take_ids"]) == {plain1["id"], plain2["id"]} and out["freed_bytes"] > 0
        assert paths[fav["id"]][0].is_file()                                                   # favourite native kept
        for t in (plain1, plain2):
            native, preview = paths[t["id"]]
            assert not native.exists() and preview.is_file()                                   # preview + metadata stay
            view = c.get(f"/api/takes/{t['id']}").json()
            assert view["native_available"] is False and view["native_pruned_at"] and view["seed"] == t["seed"]
            assert c.get(f"/api/takes/{t['id']}/audio").status_code == 200                      # preview still plays
            gone = c.get(f"/api/takes/{t['id']}/audio?kind=native")
            assert gone.status_code == 410 and gone.json()["error"]["code"] == "audio_missing"
            ex = c.post(f"/api/takes/{t['id']}/exports", json={"format": "mp3"})
            assert ex.status_code == 409 and ex.json()["error"]["code"] == "native_pruned"
        assert c.post("/api/admin/prune", json={"older_than_days": 0, "confirm": True}).json()["pruned"] == 0
        assert c.svc.db.one("SELECT COUNT(*) FROM takes")[0] == 3                              # rows all kept


# --------------------------------------------------------------------------- AT-M2-10
@pytest.mark.parametrize("fmt", ["mp3", "wav"])
def test_at_m2_10_export_decodes_and_is_loudness_normalised(tmp_path, fmt):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=12, takes=1)
        take = detail["takes"][0]
        source = c.svc.storage.abs(c.svc.get_take(take["id"])["native_path"])
        src_lufs, _ = loudness(source)
        assert abs(src_lufs - (-16)) > 1.5                      # the source is NOT already at target: the export did the work

        r = c.post(f"/api/takes/{take['id']}/exports", json={"format": fmt, "end_fade_s": 2.0, "trim_end_s": 1.5})
        assert r.status_code == 201, r.text
        ex = r.json()
        path = c.svc.storage.abs(c.svc.db.one("SELECT path FROM exports WHERE id=?", (ex["id"],))[0])
        assert path.suffix == f".{fmt}" and path.parent.name == "exports"

        assert decodes_clean(path)
        info = ffprobe(path)
        assert abs(info["duration"] - (12 - 1.5)) <= 0.05, info
        assert info["sample_rate"] == 48000 and info["channels"] == 2
        if fmt == "wav":
            assert info["codec"] == "pcm_s24le" and info["bits"] == "24"
        else:
            assert info["codec"] == "mp3"
        lufs, tp = loudness(path)
        assert abs(lufs - (-16)) <= 1.0, lufs
        assert tp <= -1.0, tp
        assert ex["sha256"] == sha(path) == c.svc.db.one("SELECT sha256 FROM exports WHERE id=?", (ex["id"],))[0]
        rec = ex["loudness"]
        assert rec["two_pass"] is True and abs(rec["output"]["integrated_lufs"] - lufs) <= 0.2
        assert rec["target"] == {"integrated_lufs": -16.0, "true_peak_dbtp": -1.5, "lra": 11.0}
        assert ex["fade_out_s"] == 2.0 and ex["trim_end_s"] == 1.5 and ex["format"] == fmt
        dl = c.get(ex["url"])
        assert dl.status_code == 200 and dl.content == path.read_bytes()


def test_export_validation_and_fade_shape(tmp_path):
    with client_for(tmp_path) as c:
        _, _, detail = create_and_wait(c, duration=10, takes=1)
        tid = detail["takes"][0]["id"]
        assert c.post(f"/api/takes/{tid}/exports", json={"format": "ogg"}).status_code == 422
        assert c.post(f"/api/takes/{tid}/exports", json={"format": "mp3", "end_fade_s": 9}).status_code == 422
        assert c.post(f"/api/takes/{tid}/exports", json={"format": "mp3", "trim_end_s": -1}).status_code == 422
        too_much = c.post(f"/api/takes/{tid}/exports", json={"format": "mp3", "trim_end_s": 9.5})
        assert too_much.status_code == 422 and too_much.json()["error"]["code"] == "invalid_trim"
        assert c.post("/api/takes/NOPE/exports", json={"format": "mp3"}).status_code == 404
        assert c.get("/api/exports/NOPE/file").status_code == 404
        assert c.svc.db.one("SELECT COUNT(*) FROM exports")[0] == 0
        # a 3 s fade really fades: the last second is much quieter than the first
        ex = c.post(f"/api/takes/{tid}/exports", json={"format": "wav", "end_fade_s": 3}).json()
        path = c.svc.storage.abs(c.svc.db.one("SELECT path FROM exports WHERE id=?", (ex["id"],))[0])
        tail_i, _ = loudness_of_window(path, 9.0, 1.0)
        head_i, _ = loudness_of_window(path, 1.0, 1.0)
        assert tail_i < head_i - 6


def loudness_of_window(path, start, length):
    done = subprocess.run(["/opt/homebrew/bin/ffmpeg", "-hide_banner", "-nostats", "-ss", str(start), "-t", str(length),
                           "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    import re
    return float(re.search(r"mean_volume: (-?[0-9.]+) dB", done.stderr).group(1)), None


# --------------------------------------------------------------------------- technical checks (breakage only)
def test_technical_checks_pass_for_a_healthy_file(tmp_path):
    f = tmp_path / "ok.wav"
    make_wav(f, seconds=6, volume=0.25)
    res = media.technical_checks(f, 6.0)
    assert res["status"] == "passed" and res["failures"] == [] and res["warnings"] == []
    assert res["label"].startswith("Technical checks") and "not a quality score" in res["label"]
    assert res["facts"]["sample_rate"] == 48000 and res["facts"]["channels"] == 2
    assert set(res["checks"]) == {"decodes", "duration", "sample_rate", "channels", "clipping", "true_peak", "silence"}


def test_technical_checks_catch_breakage(tmp_path):
    clipped = tmp_path / "clip.wav"
    make_wav(clipped, seconds=4, volume=12.0)                      # hard-clipped sine
    res = media.technical_checks(clipped, 4.0)
    assert res["status"] == "failed" and {"clipping", "true_peak"} <= set(res["failures"])

    short = tmp_path / "short.wav"
    make_wav(short, seconds=3, volume=0.25)
    assert media.technical_checks(short, 5.0)["failures"] == ["duration"]
    assert media.technical_checks(short, 3.2)["status"] == "passed"      # within 0.25 s

    mono = tmp_path / "mono.wav"
    subprocess.run(["/opt/homebrew/bin/ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=3",
                    "-ar", "44100", "-ac", "1", str(mono)], check=True)
    assert set(media.technical_checks(mono, 3.0)["failures"]) == {"sample_rate", "channels"}

    junk = tmp_path / "junk.flac"
    junk.write_bytes(b"not audio at all")
    res = media.technical_checks(junk, 3.0)
    assert res["status"] == "failed" and res["failures"] == ["decodes"]


def test_silence_is_a_warning_not_a_failure_until_40_percent(tmp_path):
    # 10 s file: tone for 8.9 s then silence = 11 % silent -> warning
    warn = tmp_path / "warn.wav"
    make_wav(warn, seconds=10, volume=0.25, extra_filter="apad=whole_dur=10,volume=enable='gte(t,8.9)':volume=0")
    res = media.technical_checks(warn, 10.0)
    assert res["status"] == "warning" and res["warnings"] == ["silence"] and res["failures"] == []
    assert 0.05 < res["facts"]["silence_fraction"] < 0.4
    assert res["checks"]["silence"]["severity"] == "warning"

    # a normal quiet tail (M0: 7.6 s of a 168 s take = 4.5 %) stays a clean pass
    tail = tmp_path / "tail.wav"
    make_wav(tail, seconds=100, volume=0.25, extra_filter="volume=enable='gte(t,95.5)':volume=0")
    res = media.technical_checks(tail, 100.0)
    assert res["status"] == "passed", res["checks"]["silence"]

    # mostly silent -> failure
    dead = tmp_path / "dead.wav"
    make_wav(dead, seconds=10, volume=0.25, extra_filter="volume=enable='gte(t,3)':volume=0")
    res = media.technical_checks(dead, 10.0)
    assert res["status"] == "failed" and res["failures"] == ["silence"]
