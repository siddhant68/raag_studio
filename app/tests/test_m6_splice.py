"""E4 splice helper and the E3/E5 mechanical checks. 16-bit PCM wav fixtures are generated here (no numpy)."""
import math
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from experiments import blind_sheet as bs
from test_m6_support import sine

SR = 8000


def orig_and_repaint(seconds=2.0, channels=2):
    return (sine(SR, seconds, 220.0, 12000, channels),
            sine(SR, seconds, 330.0, 9000, channels, phase=1.3))


@pytest.mark.parametrize("start,end,xfade", [
    (0.5, 1.0, 0.05),
    (0.5, 1.0, 0.0),            # hard splice
    (0.2, 1.8, 0.1),
    (0.01, 0.4, 0.05),          # span at the very start: fade-in zone clipped at 0
    (1.5, 2.0, 0.1),            # span reaching the end of the audio
    (1.0, 1.0004, 0.02),        # a few samples long
])
def test_bit_identical_outside_the_crossfade_window(start, end, xfade):
    o, r = orig_and_repaint()
    out = bs.splice_repaint(o, r, start, end, xfade)
    assert (out.sample_rate, out.channels, out.frames) == (o.sample_rate, o.channels, o.frames)
    assert bs.max_abs_diff_outside(o, out, start, end, xfade) == 0
    # independent check, written differently from the helper: compare raw samples outside the window
    lo = max(0, round(start * SR) - round(xfade * SR))
    hi = min(o.frames, round(end * SR) + round(xfade * SR))
    ch = o.channels
    assert out.samples[: lo * ch] == o.samples[: lo * ch]
    assert out.samples[hi * ch:] == o.samples[hi * ch:]
    # and the edit is real: the repainted core replaced the original
    s, e = round(start * SR), min(round(end * SR), o.frames)
    if e > s:
        assert out.samples[s * ch: e * ch] == r.samples[s * ch: e * ch]
        assert out.samples[s * ch: e * ch] != o.samples[s * ch: e * ch]


def test_diff_check_detects_a_leak_outside_the_window():
    o, r = orig_and_repaint()
    out = bs.splice_repaint(o, r, 0.5, 1.0, 0.05)
    out.samples[10 * out.channels] += 1                          # corrupt one sample far from the span
    assert bs.max_abs_diff_outside(o, out, 0.5, 1.0, 0.05) == 1
    out2 = bs.splice_repaint(o, r, 0.5, 1.0, 0.05)
    out2.samples[round(1.0 * SR) * 2 + 2 * 5] += 7                # inside the tail crossfade: allowed to differ
    assert bs.max_abs_diff_outside(o, out2, 0.5, 1.0, 0.05) == 0


def test_window_boundary_is_exact():
    o, r = orig_and_repaint()
    start, end, xf = 0.5, 1.0, 0.05
    out = bs.splice_repaint(o, r, start, end, xf)
    s, e, x = round(start * SR), round(end * SR), round(xf * SR)
    ch = 2
    # first and last frame INSIDE the fade zones may differ; the frame just outside never does
    assert out.samples[(s - x - 1) * ch] == o.samples[(s - x - 1) * ch]
    assert out.samples[(e + x) * ch] == o.samples[(e + x) * ch]
    assert out.samples[(s - x) * ch] != o.samples[(s - x) * ch]
    assert out.samples[(e + x - 1) * ch] != o.samples[(e + x - 1) * ch]


def test_crossfade_removes_clicks_a_hard_splice_has():
    o, r = orig_and_repaint()
    start, end = 0.5, 1.0
    hard = bs.splice_repaint(o, r, start, end, 0.0)
    soft = bs.splice_repaint(o, r, start, end, 0.05)
    clean = bs.seam_click_metric(o, start, end)                  # the original's own largest step
    h, s = bs.seam_click_metric(hard, start, end), bs.seam_click_metric(soft, start, end)
    assert h > 2 * clean                                         # hard splice jumps
    assert s <= 1.5 * max(clean, bs.seam_click_metric(r, start, end))   # crossfaded seam is no louder than the material
    assert s < h


def test_crossfade_weights_are_monotonic_and_stay_between_the_two_signals():
    o = bs.Pcm(SR, 1, array("h", [0] * 4000))
    r = bs.Pcm(SR, 1, array("h", [10000] * 4000))
    out = bs.splice_repaint(o, r, 0.25, 0.5, 0.05)
    s, x = 2000, 400
    fade_in = list(out.samples[s - x: s])
    assert fade_in == sorted(fade_in) and 0 < fade_in[0] < fade_in[-1] < 10000
    assert out.samples[s] == 10000
    out2 = bs.splice_repaint(o, r, 0.1, 0.3, 0.05)
    e2 = round(0.3 * SR)
    fade_out = list(out2.samples[e2: e2 + x])
    assert fade_out == sorted(fade_out, reverse=True) and 0 < fade_out[-1] < fade_out[0] < 10000


def test_splice_input_validation():
    o, r = orig_and_repaint()
    with pytest.raises(ValueError):
        bs.splice_repaint(o, bs.Pcm(44100, 2, r.samples), 0.5, 1.0, 0.05)       # sample rate mismatch
    with pytest.raises(ValueError):
        bs.splice_repaint(o, sine(SR, 2.0, 330.0, channels=1), 0.5, 1.0, 0.05)  # channel mismatch
    with pytest.raises(ValueError):
        bs.splice_repaint(o, sine(SR, 1.0, 330.0), 0.5, 1.0, 0.05)              # repaint shorter
    with pytest.raises(ValueError):
        bs.splice_repaint(o, r, 1.0, 0.5, 0.05)
    with pytest.raises(ValueError):
        bs.splice_repaint(o, r, 0.5, 1.0, -0.1)
    with pytest.raises(ValueError):
        bs.splice_repaint(o, r, 5.0, 6.0, 0.05)                                  # starts after the end
    longer = sine(SR, 3.0, 330.0)
    assert bs.splice_repaint(o, longer, 0.5, 1.0, 0.05).frames == o.frames        # extra repainted frames ignored


def test_clamping_never_wraps():
    o = bs.Pcm(SR, 1, array("h", [32767] * 4000))
    r = bs.Pcm(SR, 1, array("h", [-32768] * 4000))
    out = bs.splice_repaint(o, r, 0.1, 0.3, 0.02)
    assert min(out.samples) == -32768 and max(out.samples) == 32767


def test_wav_roundtrip_and_end_to_end_via_files(tmp_path):
    o, r = orig_and_repaint(seconds=1.0)
    po, pr, ps = tmp_path / "o.wav", tmp_path / "r.wav", tmp_path / "s.wav"
    bs.write_wav(po, o)
    bs.write_wav(pr, r)
    o2, r2 = bs.read_wav(po), bs.read_wav(pr)
    assert o2.samples == o.samples and (o2.sample_rate, o2.channels) == (SR, 2)
    bs.write_wav(ps, bs.splice_repaint(o2, r2, 0.3, 0.6, 0.03))
    s2 = bs.read_wav(ps)
    assert bs.max_abs_diff_outside(o2, s2, 0.3, 0.6, 0.03) == 0
    assert abs(s2.duration_s - o.duration_s) <= 0.05
    import wave
    with wave.open(str(tmp_path / "e.wav"), "wb") as w:                    # 8-bit is refused, not misread
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(8000); w.writeframes(b"\x80" * 100)
    with pytest.raises(ValueError):
        bs.read_wav(tmp_path / "e.wav")


def test_e3_duration_check():
    assert bs.duration_matches(150.0, 150.04) and bs.duration_matches(150.0, 149.95)
    assert not bs.duration_matches(150.0, 150.06) and not bs.duration_matches(150.0, 148.0)
    o = sine(SR, 2.0)
    assert bs.duration_matches(2.0, o.duration_s)


def test_e5_silence_collapse_check():
    assert bs.peak_dbfs(bs.Pcm(SR, 1, array("h", [0] * 100))) == -math.inf
    quiet = bs.Pcm(SR, 1, array("h", [10] * 100))                    # about -70 dBFS
    assert bs.peak_dbfs(quiet) < -40 and not bs.not_silent(quiet)
    loud = sine(SR, 0.5, 440.0, 3277)                                  # about -20 dBFS
    assert -21 < bs.peak_dbfs(loud) < -19 and bs.not_silent(loud)
    assert bs.peak_dbfs(bs.Pcm(SR, 1, array("h", [-32768]))) == pytest.approx(0.0)
