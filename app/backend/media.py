"""ffmpeg / ffprobe helpers: probe, previews and the per-take TECHNICAL checks (PRD section 9).

The checks look for breakage only (does not decode, wrong length, wrong format,
clipping, mostly silent). They say nothing about musical quality and are shown
as "Technical checks", never as a score. Pure stdlib: no numpy in the API venv.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from array import array
from pathlib import Path
from typing import Optional

CHECKS_LABEL = "Technical checks (breakage only, not a quality score)"
DURATION_TOLERANCE_S = 0.25
CLIP_FRACTION_LIMIT = 0.001        # 0.1 %
TRUE_PEAK_LIMIT_DBTP = -1.0
SILENCE_FLOOR_DB = -50
SILENCE_MIN_S = 0.5
CLIP_LEVEL_S16 = 32735             # |x| >= 0.999 of full scale at 16 bit
PREVIEW_BITRATE = "192k"


class MediaError(Exception):
    pass


def tool(name: str) -> str:
    found = shutil.which(name) or shutil.which(name, path="/opt/homebrew/bin")
    if not found:
        raise MediaError(f"{name} not found; install ffmpeg (Homebrew) to use Raag Studio")
    return found


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], *, timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


def probe(path: Path) -> dict:
    """ffprobe facts for the first audio stream. Raises MediaError if the file is not readable audio."""
    done = run([tool("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], timeout=60)
    if done.returncode != 0:
        raise MediaError(f"ffprobe failed: {done.stderr.decode(errors='replace').strip()[:300]}")
    info = json.loads(done.stdout)
    streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise MediaError("no audio stream")
    s = streams[0]
    try:
        duration = float(info["format"]["duration"])
        size = int(info["format"]["size"])
        rate, channels = int(s["sample_rate"]), int(s["channels"])
    except (KeyError, ValueError, TypeError):
        raise MediaError("audio stream has no usable duration, sample rate or channel count") from None
    return {
        "codec": s.get("codec_name"), "sample_fmt": s.get("sample_fmt"),
        "bits_per_raw_sample": s.get("bits_per_raw_sample"),
        "sample_rate": rate, "channels": channels, "duration_s": round(duration, 3), "size_bytes": size,
    }


def decode_s16(path: Path) -> tuple[bytes, str]:
    """Decode the whole file to 16-bit PCM; returns (pcm bytes, decoder complaints)."""
    done = run([tool("ffmpeg"), "-v", "error", "-i", str(path), "-f", "s16le", "-acodec", "pcm_s16le", "-"], timeout=300)
    err = done.stderr.decode(errors="replace").strip()
    if done.returncode != 0:
        raise MediaError(f"decode failed: {err[:300]}")
    return done.stdout, err


def clipped_fraction(pcm: bytes) -> tuple[float, int]:
    """(fraction of samples at |x| >= 0.999 full scale, count). Fast path: skip counting if the peak is lower."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    if not samples:
        return 0.0, 0
    if max(max(samples), -min(samples)) < CLIP_LEVEL_S16:
        return 0.0, 0
    hot = sum(1 for x in samples if x >= CLIP_LEVEL_S16 or x <= -CLIP_LEVEL_S16)
    return hot / len(samples), hot


def _grab(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def analyse_levels(path: Path, duration_s: float) -> dict:
    """One ffmpeg pass: silence (-50 dB, >= 0.5 s) plus EBU R128 loudness and true peak."""
    filt = f"silencedetect=n={SILENCE_FLOOR_DB}dB:d={SILENCE_MIN_S},ebur128=peak=true"
    done = run([tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af", filt, "-f", "null", "-"], timeout=300)
    log = done.stderr.decode(errors="replace")
    silent_s = sum(float(m) for m in re.findall(r"silence_duration: ([0-9.]+)", log))
    starts = re.findall(r"silence_start: (-?[0-9.]+)", log)
    ends = re.findall(r"silence_end: ([0-9.]+)", log)
    if len(starts) > len(ends):                       # silence runs to the end of the file
        silent_s += max(0.0, duration_s - float(starts[-1]))
    summary = log[log.rfind("Summary:"):]
    return {
        "silence_s": round(silent_s, 3),
        "silence_fraction": round(silent_s / duration_s, 5) if duration_s else 0.0,
        "integrated_lufs": _grab(r"I:\s+(-?[0-9.]+) LUFS", summary),
        "loudness_range_lu": _grab(r"LRA:\s+(-?[0-9.]+) LU", summary),
        "true_peak_dbtp": _grab(r"True peak:\s+Peak:\s+(-?[0-9.]+) dBFS", summary),
    }


def _check(ok: bool, value, limit, severity: str = "failure") -> dict:
    return {"ok": bool(ok), "value": value, "limit": limit, "severity": severity}


def technical_checks(path: Path, expected_duration_s: float, *, silence_warn: float = 0.05,
                     silence_fail: float = 0.40) -> dict:
    """Breakage-only checks for one take. `status`: passed | warning | failed."""
    checks: dict[str, dict] = {}
    facts: dict = {"file": path.name}
    try:
        info = probe(path)
        facts.update(info)
        pcm, complaints = decode_s16(path)
        checks["decodes"] = _check(not complaints and len(pcm) > 0, complaints or "ok", "no decoder errors")
    except (MediaError, subprocess.TimeoutExpired, OSError) as exc:
        checks["decodes"] = _check(False, str(exc)[:300], "no decoder errors")
        return _summary(checks, facts)

    dur = info["duration_s"]
    checks["duration"] = _check(abs(dur - expected_duration_s) <= DURATION_TOLERANCE_S, dur,
                                f"{expected_duration_s} +/- {DURATION_TOLERANCE_S} s")
    checks["sample_rate"] = _check(info["sample_rate"] == 48000, info["sample_rate"], 48000)
    checks["channels"] = _check(info["channels"] == 2, info["channels"], 2)

    frac, hot = clipped_fraction(pcm)
    facts["clipped_fraction"], facts["clipped_samples"] = round(frac, 6), hot
    checks["clipping"] = _check(frac < CLIP_FRACTION_LIMIT, round(frac, 6), f"< {CLIP_FRACTION_LIMIT}")

    try:
        levels = analyse_levels(path, dur)
    except (subprocess.TimeoutExpired, OSError) as exc:
        checks["levels"] = _check(False, str(exc)[:200], "ffmpeg level analysis runs")
        return _summary(checks, facts)
    facts.update(levels)
    tp = levels["true_peak_dbtp"]
    checks["true_peak"] = _check(tp is not None and tp <= TRUE_PEAK_LIMIT_DBTP, tp, f"<= {TRUE_PEAK_LIMIT_DBTP} dBTP")
    sf = levels["silence_fraction"]
    if sf > silence_fail:
        checks["silence"] = _check(False, sf, f"<= {silence_fail} (mostly silent)")
    else:
        checks["silence"] = _check(sf < silence_warn, sf, f"< {silence_warn} (warning only)", severity="warning")
    return _summary(checks, facts)


def _summary(checks: dict, facts: dict) -> dict:
    failures = [n for n, c in checks.items() if not c["ok"] and c["severity"] == "failure"]
    warnings = [n for n, c in checks.items() if not c["ok"] and c["severity"] == "warning"]
    return {"label": CHECKS_LABEL, "status": "failed" if failures else "warning" if warnings else "passed",
            "failures": failures, "warnings": warnings, "checks": checks, "facts": facts}


def make_preview(native: Path, out: Path) -> None:
    """MP3 192 kbps for the in-browser player (written to a temp name, then renamed)."""
    tmp = out.with_name(out.name + ".part")
    done = run([tool("ffmpeg"), "-y", "-v", "error", "-i", str(native), "-vn", "-c:a", "libmp3lame",
                "-b:a", PREVIEW_BITRATE, "-ar", "48000", "-f", "mp3", str(tmp)], timeout=300)
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise MediaError(f"preview encode failed: {done.stderr.decode(errors='replace').strip()[:300]}")
    tmp.replace(out)
