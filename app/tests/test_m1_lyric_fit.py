"""AT-M1-08: lyric duration fit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import compiler, lyric_fit


def lines(n):
    return "\n".join(f"line {i}" for i in range(n))


def test_at_m1_08_26_lines_gives_152_seconds():
    fit = lyric_fit.fit_lyrics(lines(26))
    assert abs(fit.suggested_seconds - 152) <= 16 and fit.status == "ok" and fit.estimate is True


def test_thodi_counts_26_lines_and_152_seconds():
    thodi = compiler.load_recipe("r3_hindi_ballad")["example_lyrics"]
    fit = lyric_fit.fit_lyrics(thodi, requested_duration_s=152)
    assert fit.line_count == 26 and fit.suggested_seconds == 152 and fit.warnings == []


def test_at_m1_08_two_lines_too_short_with_options_and_no_auto_repeat():
    text = "tera naam\nmeri dua"
    fit = lyric_fit.fit_lyrics(text)
    assert fit.status == "too_short" and fit.line_count == 2
    ids = {o["id"] for o in fit.options}
    assert {"sketch", "repeat", "add_lines"} <= ids
    sketch = next(o for o in fit.options if o["id"] == "sketch")
    assert 45 <= sketch["duration_s"] <= 60
    repeat = next(o for o in fit.options if o["id"] == "repeat")
    assert repeat["requires_user_approval"] is True and repeat["auto"] is False
    # compiling reports it but sends the two lines unchanged (no repeats, no deletions)
    plan = {"brief": "b", "voice_mode": "sung", "lead": {"instrument": "piano"}, "voices": {"language": "hi"},
            "lyrics": {"policy": "exact", "text": text}, "duration_s": 150}
    out = compiler.compile(plan)
    conflict = next(c for c in out["compile_report"]["conflicts"] if c["kind"] == "lyrics_duration_fit")
    assert conflict["fit"]["status"] == "too_short"
    assert [ln for ln in out["lyrics"].split("\n") if not ln.startswith("[")] == text.split("\n")


def test_at_m1_08_80_lines_capped_with_warning():
    fit = lyric_fit.fit_lyrics(lines(80))
    assert fit.status == "too_long" and fit.suggested_seconds == 240
    assert fit.warnings and any(o["id"] == "use_cap" for o in fit.options)


def test_boundaries_and_clamps():
    assert lyric_fit.fit_lyrics(7).status == "too_short" and lyric_fit.fit_lyrics(8).status == "ok"
    assert lyric_fit.fit_lyrics(40).status == "ok" and lyric_fit.fit_lyrics(41).status == "too_long"
    assert lyric_fit.suggested_seconds(1) == 45 and lyric_fit.suggested_seconds(100) == 240


def test_tags_and_blank_lines_are_not_lyric_lines():
    assert lyric_fit.count_lyric_lines("[Verse]\na\n\nb\n[Chorus]\r\nc\n  \n") == 3


def test_mismatch_with_requested_length_is_reported_not_applied():
    fit = lyric_fit.fit_lyrics(lines(26), requested_duration_s=60)
    assert fit.suggested_seconds == 152 and any(o["id"] == "use_estimate" for o in fit.options)
