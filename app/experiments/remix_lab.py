"""Offline remix research prototype. Not an app endpoint or a generative engine.

Requires numpy/scipy/soundfile in the explicitly selected analysis Python, plus
ffmpeg/ffprobe and Rubber Band CLI. Never downloads weights or edits a source.
Beat positions, phrase labels and hooks remain editable, fallible annotations.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
SCHEMA = "raag-remix-study/v1"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True)


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def decode(path, sr=SR):
    raw = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ar", sr,
               "-ac", 2, "-f", "f32le", "-"]).stdout
    x = np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()
    if not len(x) or not np.isfinite(x).all():
        raise ValueError("empty/nonfinite decoded audio")
    return x


def write(path, x, sr=SR):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    if not np.isfinite(x).all():
        raise ValueError("nonfinite audio")
    sf.write(path, x, sr, subtype="FLOAT")


def envelope(points, n, beat_s, sr=SR):
    p = np.asarray(points, dtype=float)
    # Values are amplitudes, not dB; automation is linear between explicit points.
    return np.interp(np.arange(n) / sr / beat_s, p[:, 0], p[:, 1])


def split_bands(x, sr=SR, hz=180):
    # Complementary source bands, never claimed to be isolated bass/instrument stems.
    # Offline zero-phase crossover: with a causal lowpass, x-low retains bass
    # through phase rotation. The real overlap diagnostic exposed that defect.
    low = signal.sosfiltfilt(signal.butter(4, hz, fs=sr, output="sos"), x, axis=0)
    return low, x - low


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_plan(p, root):
    """Fail closed on unknown operations and invalid annotations; no output created."""
    if p.get("schema") != SCHEMA:
        raise ValueError("schema")
    if p.get("operation") not in ("transition", "single_source_remix"):
        raise ValueError("operation")
    for name, lo, hi in (("bpm", 40, 200), ("output_beats", 4, 256)):
        if not finite_number(p.get(name)) or not lo <= p[name] <= hi:
            raise ValueError(name)
    if p.get("meter") != 4:
        raise ValueError("prototype currently supports explicit 4-beat meters only")
    if not p.get("sources") or not p.get("clips"):
        raise ValueError("sources/clips required")
    for sid, src in p["sources"].items():
        path = Path(root) / src["path"]
        if src["kind"] not in ("stereo_mix", "supplied_stem", "estimated_stem", "synthesized"):
            raise ValueError("source kind")
        if sha(path) != src["sha256"]:
            raise ValueError(f"source hash mismatch: {sid}")
        beats = np.asarray(src["beats_s"], dtype=float)
        if len(beats) < 2 or not np.isfinite(beats).all() or beats[0] < 0 or np.any(np.diff(beats) <= 0):
            raise ValueError("source beat map must be finite and increasing")
        duration = float(json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                                        "format=duration", "-of", "json", path]).stdout)["format"]["duration"])
        if beats[-1] > duration:
            raise ValueError("beat annotation outside source")
    ids = set()
    for c in p["clips"]:
        if not isinstance(c["id"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", c["id"]):
            raise ValueError("unsafe clip id")
        if c["id"] in ids:
            raise ValueError("duplicate clip id")
        ids.add(c["id"])
        if c["source"] not in p["sources"]:
            raise ValueError("unknown source")
        a, b = c["source_beats"]
        if not all(type(v) is int for v in (a, b)) or not 0 <= a < b < len(p["sources"][c["source"]]["beats_s"]):
            raise ValueError("source beat range")
        if not finite_number(c["at_beat"]) or c["at_beat"] < 0 or c["at_beat"] + b - a > p["output_beats"]:
            raise ValueError("clip outside timeline")
        if not finite_number(c.get("pitch_semitones", 0)) or abs(c.get("pitch_semitones", 0)) > 3:
            raise ValueError("pitch shift outside bounded prototype range")
        for key in ("gain", "low_gain", "high_gain"):
            pts = np.asarray(c[key], dtype=float)
            if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2 or not np.isfinite(pts).all():
                raise ValueError("invalid automation")
            if np.any(np.diff(pts[:, 0]) <= 0) or pts[0, 0] != 0 or pts[-1, 0] != b - a:
                raise ValueError("automation must span clip in increasing local beats")
            if np.any((pts[:, 1] < 0) | (pts[:, 1] > 1.5)):
                raise ValueError("automation amplitude")
    for h in p.get("hooks", []):
        if h["clip"] not in ids:
            raise ValueError("hook clip")
        clip = next(c for c in p["clips"] if c["id"] == h["clip"])
        if not 0 <= h["local_beats"][0] < h["local_beats"][1] <= clip["source_beats"][1] - clip["source_beats"][0]:
            raise ValueError("hook range")
    if p.get("drums") and (p["drums"].get("recipe") != "laidback_to_four/v1" or p["output_beats"] != 96):
        raise ValueError("unsupported drum recipe/timeline")


def warp(x, source_times, beat_s, folder, pitch=0, sr=SR):
    """Map candidate pulses with R2; use a separate R3 pitch pass if requested."""
    folder = Path(folder)
    folder.mkdir()
    start, end = round(source_times[0] * sr), round(source_times[-1] * sr)
    if not 0 <= start < end <= len(x):
        raise ValueError("warp range outside decoded source")
    write(folder / "input.wav", x[start:end], sr)
    target_n = round((len(source_times) - 1) * beat_s * sr)
    source_frames = np.rint((np.asarray(source_times) - source_times[0]) * sr).astype(int)
    target_frames = np.rint(np.arange(len(source_times)) * beat_s * sr).astype(int)
    (folder / "timemap.txt").write_text("".join(f"{a} {b}\n" for a, b in zip(source_frames, target_frames)))
    # R3 4.0.0 + timemap measured ~44 ms attack displacement on the impulse fixture,
    # failing our 30 ms tolerance. R2 measured <9 ms. Do not loosen that threshold.
    # R3 + timemap also lost the requested pitch shift in our known-tone test.
    # For a genuinely linear map, R3 global stretching avoids R2's periodic
    # anchor-induced tone sidebands. Do not send an unnecessary keyframe map.
    linear = bool(np.max(np.abs(source_frames - np.linspace(0, end - start, len(source_frames)))) <= 1)
    timed_path = folder / "native_time.wav"
    if linear:
        args = ["rubberband", "-3", "--centre-focus", "-F", "-q", "-D", target_n / sr,
                "-p", pitch, folder / "input.wav", timed_path]
    else:
        args = ["rubberband", "-2", "--centre-focus", "-q", "-D", target_n / sr,
                "-M", folder / "timemap.txt", folder / "input.wav", timed_path]
    result = run(args)
    (folder / "stderr.log").write_bytes(result.stderr)
    commands = [list(map(str, args))]
    if pitch and not linear:
        pitch_args = ["rubberband", "-3", "--centre-focus", "-F", "-q", "-p", pitch,
                      timed_path, folder / "native_pitch.wav"]
        pitch_result = run(pitch_args)
        (folder / "pitch_stderr.log").write_bytes(pitch_result.stderr)
        commands.append(list(map(str, pitch_args)))
    y, actual_sr = sf.read(folder / ("native_pitch.wav" if pitch and not linear else "native_time.wav"), always_2d=True, dtype="float32")
    if actual_sr != sr or len(y) < target_n - round(.02 * sr) or len(y) > target_n + round(.02 * sr):
        raise ValueError("unexpected Rubber Band sample rate or duration")
    # CLI sample-rounding allowance is measured before padding, never a hidden fix.
    adjustment = target_n - len(y)
    y = np.pad(y[:target_n], ((0, max(0, adjustment)), (0, 0)))
    dump(folder / "transform.json", {"commands": commands, "source_frames": source_frames.tolist(),
         "target_frames": target_frames.tolist(), "raw_samples": target_n - adjustment,
         "output_samples": target_n, "padding_or_trim_samples": adjustment,
         "pitch_semitones": pitch, "sample_rate": sr, "linear_map": linear,
         "processor": "R3 global" if linear else "R2 time map, optional separate R3 pitch",
         "pitch_with_nonlinear_map": "not musically validated" if pitch and not linear else "not used"})
    return y


def drum_components(beats, beat_s, seed=251025, sr=SR):
    """Actual deterministic oscillator/noise audio, not an AI or realistic kit claim."""
    n = round(beats * beat_s * sr)
    rng = np.random.default_rng(seed)
    buses = {k: np.zeros((n, 2)) for k in ("kick", "snare", "hat")}
    events = []

    def add(name, beat, sound, amp, pan=0):
        at = round(beat * beat_s * sr)
        length = min(len(sound), n - at)
        if length <= 0:
            return
        # Linear pan with centre at unity per channel; documented component gain.
        buses[name][at:at + length] += amp * sound[:length, None] * np.array([1 - max(0, pan), 1 + min(0, pan)])
        events.append({"bus": name, "beat": beat, "sample": at, "amplitude": amp})

    for beat in np.arange(32, beats, .5):
        if 60 <= beat < 64:  # purposeful four-beat withdrawal before return
            continue
        returning = beat >= 64
        local = beat % 4
        if beat == int(beat) and (returning or local in (0, 2.0)):
            t = np.arange(round(.35 * sr)) / sr
            freq = 46 + 85 * np.exp(-t * 32)
            kick = np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-t * 15)
            kick *= np.minimum(t / .002, 1)
            add("kick", float(beat), kick, .18 if returning else .12)
        if local in (1.0, 3.0):
            t = np.arange(round(.16 * sr)) / sr
            noise = rng.standard_normal(len(t))
            snap = signal.sosfilt(signal.butter(2, 1400, btype="highpass", fs=sr, output="sos"), noise)
            snap = np.tanh(snap) * np.exp(-t * 35) * np.minimum(t / .001, 1)
            add("snare", float(beat), snap, .045, -.12)
        t = np.arange(round(.075 * sr)) / sr
        noise = rng.standard_normal(len(t))
        hat = signal.sosfilt(signal.butter(2, 7000, btype="highpass", fs=sr, output="sos"), noise)
        hat = np.tanh(hat) * np.exp(-t * 65) * np.minimum(t / .001, 1)
        add("hat", float(beat), hat, .022 if local % 1 else .013, .2)
    return buses, events


def render(p, root, out):
    validate_plan(p, root)
    out = Path(out)
    out.mkdir()  # exclusive: never replace a prior run
    dump(out / "plan.json", p)
    n = round(p["output_beats"] * 60 / p["bpm"] * SR)
    beat_s = 60 / p["bpm"]
    buses, templates, clips = {}, {}, {}
    for c in p["clips"]:
        src = p["sources"][c["source"]]
        a, b = c["source_beats"]
        y = warp(decode(Path(root) / src["path"]), src["beats_s"][a:b + 1], beat_s,
                 out / ("warp_" + c["id"]), c.get("pitch_semitones", 0))
        templates[c["id"]] = y
        write(out / ("template_" + c["id"] + ".wav"), y)
        low, high = split_bands(y)
        z = (low * envelope(c["low_gain"], len(y), beat_s)[:, None]
             + high * envelope(c["high_gain"], len(y), beat_s)[:, None])
        z *= envelope(c["gain"], len(y), beat_s)[:, None]
        # 8 ms source edge ramps. Preserve source/template originals alongside.
        edge = min(round(.008 * SR), len(z) // 2)
        z[:edge] *= np.linspace(0, 1, edge)[:, None]
        z[-edge:] *= np.linspace(1, 0, edge)[:, None]
        bus = np.zeros((n, 2))
        start = round(c["at_beat"] * beat_s * SR)
        length = min(len(z), n - start)
        bus[start:start + length] = z[:length]
        buses[c["id"]] = bus
        clips[c["id"]] = {"start_sample": start, "samples": length}
    if p.get("drums"):
        drum_buses, events = drum_components(p["output_beats"], beat_s, p["drums"]["seed"])
        buses.update(drum_buses)
        dump(out / "drum_events.json", events)
    master = sum(buses.values())
    # Conservative fixed bus headroom followed by one fixed gain for master and all buses.
    peak = float(np.max(np.abs(master)))
    master_gain = min(.7, .8 / max(peak, 1e-12))
    for key in buses:
        buses[key] *= master_gain
        write(out / ("bus_" + key + ".wav"), buses[key])
    master *= master_gain
    write(out / "native_mix.wav", master)
    dump(out / "render.json", {"schema": SCHEMA, "engine": "deterministic editing + Rubber Band R2 time map / optional R3 pitch",
         "generative_model": None, "checkpoint": None, "lyrics": None, "prompt": None,
         "master_gain": master_gain, "clip_offsets": clips, "sample_rate": SR,
         "samples": n, "native_sha256": sha(out / "native_mix.wav"),
         "musical_acceptance": "pending", "beat_and_hook_annotations": "machine_candidates_unreviewed"})
    return out


def loudness(path):
    result = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af",
                  "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"])
    log = result.stderr.decode(errors="replace")
    raw = json.loads(log[log.rfind("{"):log.rfind("}") + 1])
    return {k: float(raw[k]) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}


def listening_copy(source, out, target=-16):
    """Constant gain only; matched LUFS is verified, peak ceiling can lower target."""
    stats = loudness(source)
    gain_db = min(target - stats["input_i"], -1.7 - stats["input_tp"])
    if not math.isfinite(gain_db):
        raise ValueError("cannot normalize silence/nonfinite loudness")
    run(["ffmpeg", "-v", "error", "-n", "-i", source, "-af", f"volume={gain_db:.9f}dB",
         "-ar", SR, "-c:a", "pcm_s24le", out])
    return {"gain_db": gain_db, "before": stats, "after": loudness(out)}


def waveform_checks(x, expected_n=None, sr=SR):
    if x.ndim != 2 or x.shape[1] != 2 or not len(x) or not np.isfinite(x).all():
        return {"failures": ["invalid_audio"]}
    rms = float(np.sqrt(np.mean(x.astype(float) ** 2)))
    mono = np.mean(x, axis=1)
    mono_rms = float(np.sqrt(np.mean(mono ** 2)))
    mono_loss = 20 * math.log10(max(mono_rms, 1e-12) / max(rms, 1e-12))
    failures = []
    if rms < 10 ** (-60 / 20):
        failures.append("silence")
    if float(np.max(np.abs(x))) >= .999:
        failures.append("sample_clipping")
    if expected_n is not None and abs(len(x) - expected_n) > round(.01 * sr):
        failures.append("duration")
    if mono_loss < -12:
        failures.append("mono_cancellation")
    return {"failures": failures, "samples": len(x), "duration_s": len(x) / sr,
            "rms_dbfs": 20 * math.log10(max(rms, 1e-12)), "peak": float(np.max(np.abs(x))),
            "mono_loss_db": mono_loss,
            "tail": {"last_sample_peak": float(np.max(np.abs(x[-1]))),
                     "last_100ms_rms_dbfs": 20 * math.log10(max(float(np.sqrt(np.mean(x[-min(len(x), round(.1 * sr)):] ** 2))), 1e-12)),
                     "scope": "edge level only; a musically resolved cadence/effect tail requires listening"}}


def retention(reference, candidate):
    """Gain-invariant sample correlation at the declared location, NOT melody recognition."""
    n = min(len(reference), len(candidate))
    if n < 32 or len(reference) != len(candidate):
        return {"correlation": 0., "residual_db": 0., "pass": False}
    a, b = reference.reshape(-1).astype(float), candidate.reshape(-1).astype(float)
    aa, bb = float(a @ a), float(b @ b)
    corr = float(a @ b / max(math.sqrt(aa * bb), 1e-20))
    scale = float(a @ b / max(aa, 1e-20))
    residual = float(np.sqrt(np.mean((b - scale * a) ** 2)))
    db = 20 * math.log10(max(residual, 1e-12) / max(math.sqrt(bb / len(b)), 1e-12))
    return {"correlation": corr, "fitted_gain": scale, "residual_db": db,
            "pass": corr >= .75 and scale > 0}


def pulse_alignment(observed_s, expected_s, tolerance_s=.03):
    """Requires independently supplied corresponding pulse onsets; won't infer downbeats."""
    if len(observed_s) != len(expected_s) or not len(observed_s):
        return {"pass": False, "reason": "missing_corresponding_onsets"}
    delta = np.asarray(observed_s) - np.asarray(expected_s)
    if not np.isfinite(delta).all():
        return {"pass": False, "reason": "nonfinite_onsets"}
    return {"pass": bool(np.max(np.abs(delta)) <= tolerance_s),
            "max_error_ms": float(np.max(np.abs(delta)) * 1000),
            "drift_ms": float((delta[-1] - delta[0]) * 1000), "tolerance_ms": tolerance_s * 1000}


def seam_check(x, sample, sr=SR):
    # A large one-sample jump is suspicious. Percussive attacks can be legitimate;
    # use only at declared edit points and retain as a review flag on music.
    if sample <= 1 or sample >= len(x) - 1:
        return {"flag": False, "reason": "outside_interior"}
    diff = np.max(np.abs(np.diff(x, axis=0)), axis=1)
    lo, hi = max(0, sample - round(.03 * sr)), min(len(diff), sample + round(.03 * sr))
    local = float(np.median(diff[lo:hi]))
    jump = float(diff[sample - 1])
    return {"jump": jump, "local_median": local, "flag": jump > .08 and jump > max(local, 1e-6) * 12}


def bass_conflict(a, b, start, end, sr=SR):
    lo_a, _ = split_bands(a[start:end], sr)
    lo_b, _ = split_bands(b[start:end], sr)
    window = round(.25 * sr)
    both = []
    for i in range(0, len(lo_a) - window + 1, window):
        ra = np.sqrt(np.mean(lo_a[i:i + window] ** 2))
        rb = np.sqrt(np.mean(lo_b[i:i + window] ** 2))
        # Diagnostic only: sustained similar and appreciable low-band energy.
        both.append(min(ra, rb) > .004 and min(ra, rb) / max(ra, rb, 1e-12) > .5)
    frac = float(np.mean(both)) if both else 0.
    return {"competing_low_band_fraction": frac, "flag": frac > .25,
            "scope": "source bands, not isolated kick/bass; not a harmonic or taste verdict"}


def audit(folder):
    folder = Path(folder)
    p = json.loads((folder / "plan.json").read_text())
    meta = json.loads((folder / "render.json").read_text())
    x = decode(folder / "native_mix.wav")
    result = waveform_checks(x, meta["samples"])
    result["loudness"] = loudness(folder / "native_mix.wav")
    result["hash_matches_render"] = sha(folder / "native_mix.wav") == meta["native_sha256"]
    if not result["hash_matches_render"]:
        result["failures"].append("native_hash_mismatch")
    hooks = []
    for h in p.get("hooks", []):
        template = decode(folder / ("template_" + h["clip"] + ".wav"))
        a, b = [round(v * 60 / p["bpm"] * SR) for v in h["local_beats"]]
        at = meta["clip_offsets"][h["clip"]]["start_sample"]
        check = retention(template[a:b], x[at + a:at + b])
        hooks.append({"id": h["id"], "status": "sample_retention_only", **check})
    result["hook_checks"] = hooks
    if any(not h["pass"] for h in hooks):
        result["failures"].append("missing_or_masked_source_template")
    seams = [round(c["at_beat"] * 60 / p["bpm"] * SR) for c in p["clips"]]
    result["seam_flags"] = [{"sample": s, **seam_check(x, s)} for s in seams]
    # Never turn unverified grids and musical decisions into green quality badges.
    result["source_annotation_review"] = "pending"
    result["musical_acceptance"] = "pending_human_listening"
    result["professional_release_ready"] = False
    result["audio_pulse_alignment"] = "unverified_on_music; impulse fixtures tested separately"
    dump(folder / "audit.json", result)
    return result
