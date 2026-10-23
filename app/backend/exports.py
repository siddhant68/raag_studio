"""Export a take as MP3 or WAV (PRD C21/C25, section 9).

ffmpeg only; the native file is read, never modified. Order of operations:
trim the end, fade out, then a two-pass loudnorm to -16 LUFS / -1.5 dBTP, then
encode (WAV 24-bit 48 kHz, or MP3 320 kbps 48 kHz). The loudness actually
measured on the written file is stored with the export, plus its sha256.
Exports of takes made by the fake engine are labelled engine:"fake" and tagged.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from . import media
from .db import dumps, now_iso, ulid
from .schemas import ApiError, ExportBody

TARGET_I = -16.0
TARGET_TP = -1.5
TARGET_LRA = 11.0
MAX_TP_AFTER_ENCODE = -1.0
MP3_BITRATE = "320k"


def _prefilter(duration_s: float, end_fade_s: float, trim_end_s: float) -> tuple[str, float]:
    parts: list[str] = []
    new_len = duration_s - trim_end_s
    if trim_end_s > 0:
        parts += [f"atrim=end={new_len:.6f}", "asetpts=PTS-STARTPTS"]
    if end_fade_s > 0:
        parts.append(f"afade=t=out:st={max(0.0, new_len - end_fade_s):.6f}:d={min(end_fade_s, new_len):.6f}")
    return ",".join(parts), new_len


def _measure_pass(native: Path, pre: str, tp: float) -> dict:
    chain = (pre + "," if pre else "") + f"loudnorm=I={TARGET_I}:TP={tp}:LRA={TARGET_LRA}:print_format=json"
    done = media.run([media.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(native), "-af", chain,
                      "-f", "null", "-"], timeout=600)
    log = done.stderr.decode(errors="replace")
    block = re.findall(r"\{[^{}]*\}", log)
    if done.returncode != 0 or not block:
        raise media.MediaError(f"loudness measurement failed: {log.strip()[-300:]}")
    return json.loads(block[-1])


def _encode_pass(native: Path, pre: str, m: dict, tp: float, fmt: str, out: Path, fake: bool) -> dict:
    norm = (f"loudnorm=I={TARGET_I}:TP={tp}:LRA={TARGET_LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
            f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}"
            ":linear=true:print_format=json")
    chain = (pre + "," if pre else "") + norm
    codec = (["-c:a", "pcm_s24le", "-f", "wav"] if fmt == "wav"
             else ["-c:a", "libmp3lame", "-b:a", MP3_BITRATE, "-f", "mp3"])
    cmd = [media.tool("ffmpeg"), "-y", "-hide_banner", "-nostats", "-i", str(native), "-vn", "-af", chain,
           "-ar", "48000", "-ac", "2", *codec]
    if fake:
        cmd += ["-metadata", "comment=FAKE ENGINE TEST AUDIO (not a real render)"]
    cmd.append(str(out))
    done = media.run(cmd, timeout=600)
    if done.returncode != 0:
        raise media.MediaError(f"export encode failed: {done.stderr.decode(errors='replace').strip()[-300:]}")
    blocks = re.findall(r"\{[^{}]*\}", done.stderr.decode(errors="replace"))
    return json.loads(blocks[-1]) if blocks else {}


def render_export(native: Path, out: Path, fmt: str, duration_s: float, end_fade_s: float, trim_end_s: float,
                  fake: bool = False) -> dict:
    """Write `out` (exact path, any suffix) and return the loudness record."""
    pre, new_len = _prefilter(duration_s, end_fade_s, trim_end_s)
    first = _measure_pass(native, pre, TARGET_TP)
    tp = TARGET_TP
    for attempt in (1, 2):
        applied = _encode_pass(native, pre, first, tp, fmt, out, fake)
        after = media.analyse_levels(out, new_len)
        if after["true_peak_dbtp"] is not None and after["true_peak_dbtp"] <= MAX_TP_AFTER_ENCODE:
            break
        tp -= 1.0                      # the lossy encode overshot: leave one more dB of headroom and redo once
    info = media.probe(out)
    return {
        "target": {"integrated_lufs": TARGET_I, "true_peak_dbtp": TARGET_TP, "lra": TARGET_LRA},
        "input": {"integrated_lufs": float(first["input_i"]), "true_peak_dbtp": float(first["input_tp"]),
                  "lra": float(first["input_lra"])},
        "output": {"integrated_lufs": after["integrated_lufs"], "true_peak_dbtp": after["true_peak_dbtp"],
                   "lra": after["loudness_range_lu"], "measured_by": "ffmpeg ebur128 on the written file"},
        "two_pass": True, "normalization_type": applied.get("normalization_type"), "tp_target_used": tp,
        "duration_s": info["duration_s"], "sample_rate": info["sample_rate"], "channels": info["channels"],
        "codec": info["codec"], "bits_per_raw_sample": info.get("bits_per_raw_sample"),
    }


def create_export(svc, take_id: str, body: ExportBody) -> dict:
    take = svc.get_take(take_id)
    native = svc.storage.abs(take["native_path"])
    if not native or not native.is_file():
        raise ApiError(409, "native_pruned", "The native audio of this take was removed by a prune, so it cannot "
                       "be exported. Previews remain playable.")
    duration = float(take["duration_s"])
    if body.trim_end_s > max(0.0, duration - 1.0):
        raise ApiError(422, "invalid_trim", f"trim_end_s must leave at least 1 second of a {duration:.1f} s take.")
    fake = take["engine"] == "fake"
    song = svc.db.one("SELECT s.id, s.title FROM songs s JOIN rounds r ON r.song_id=s.id WHERE r.id=?",
                      (take["round_id"],))
    export_id = ulid()
    ext = body.format
    out_dir = svc.storage.exports_dir(song["id"])
    tmp, final = out_dir / f"{export_id}.part", out_dir / f"{export_id}.{ext}"
    try:
        loudness = render_export(native, tmp, ext, duration, body.end_fade_s, body.trim_end_s, fake)
    except (media.MediaError, subprocess.TimeoutExpired) as exc:
        tmp.unlink(missing_ok=True)
        raise ApiError(500, "export_failed", f"Export failed: {exc}")
    tmp.replace(final)
    digest = media.sha256_file(final)
    svc.db.execute(
        "INSERT INTO exports(id, take_id, format, fade_out_s, trim_end_s, loudness_json, path, sha256, engine, "
        "created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (export_id, take_id, ext, body.end_fade_s, body.trim_end_s, dumps(loudness), svc.storage.rel(final), digest,
         take["engine"], now_iso()))
    row = svc.db.one("SELECT * FROM exports WHERE id=?", (export_id,))
    view = svc.export_view(row)
    view["filename"] = download_name(song["title"], take, ext, fake)
    return view


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:40] or "song"


def download_name(title: str, take, ext: str, fake: bool) -> str:
    return f"{slug(title)}_T{take['ordinal']}_s{take['seed']}{'_FAKE' if fake else ''}.{ext}"


def export_file(svc, export_id: str) -> tuple[Path, str, str]:
    """(path, media type, download filename) for GET /api/exports/{id}/file."""
    row = svc.db.one("SELECT * FROM exports WHERE id=?", (export_id,))
    if not row:
        raise ApiError(404, "export_not_found", f"No export with id {export_id}.")
    path = svc.storage.abs(row["path"])
    if not path or not path.is_file():
        raise ApiError(404, "export_file_missing", "The exported file is no longer on disk.")
    take = svc.get_take(row["take_id"])
    song = svc.db.one("SELECT s.title FROM songs s JOIN rounds r ON r.song_id=s.id WHERE r.id=?", (take["round_id"],))
    media_type = "audio/wav" if row["format"] == "wav" else "audio/mpeg"
    return path, media_type, download_name(song["title"], take, row["format"], row["engine"] == "fake")
