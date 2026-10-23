"""AT-M1-02: exact lyrics are byte-preserved apart from code-inserted tag lines and newline normalisation."""
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend import compiler
from backend.plan_schema import Plan

ALPHABET = (list("abcdefghijklmnopqrstuvwxyzABCDEF0123456789 .,;:!?'\"()-_/\\")
            + list("तेरी चाय का आधा प्याला खिड़की धूप ज़ ँ") + list("日本語の歌詞") + list("😀🎵🪈") + ["é", "ñ", "́", "‍"])
LINE_BREAKS = ["\n", "\n", "\n", "\r\n", "\r", "\n\n", "\n \n", "\t\n", " ", "\x0b", "\x0c", "\x85"]


def random_lyric(rng: random.Random) -> str:
    parts = []
    for _ in range(rng.randint(1, 14)):
        if rng.random() < 0.08:
            parts.append(rng.choice(["[Verse]", "[Chorus 2]", " [Bridge] "]))     # user-written tags are plain text
        elif rng.random() < 0.15 and parts:
            parts.append(rng.choice(parts))                                       # repeated lines/stanzas
        else:
            parts.append("".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 40))))
        parts.append(rng.choice(LINE_BREAKS))
    text = "".join(parts)
    if not text.strip():
        text += "x"
    return text


def sung(text):
    return Plan.model_validate({"brief": "b", "voice_mode": "sung", "lead": {"instrument": "acoustic_guitar"},
                                "voices": {"language": "hi"}, "lyrics": {"policy": "exact", "text": text}})


def norm(t):
    return t.replace("\r\n", "\n").replace("\r", "\n")


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def test_at_m1_02_exact_lyrics_property_200_cases():
    rng = random.Random(20261024)
    saw_inserted = saw_user_tags = 0
    for case in range(200):
        text = random_lyric(rng)
        if len(norm(text)) > 4000:
            continue
        out = compiler.compile(sung(text))
        lines = out["lyrics"].split("\n")
        rep = out["compile_report"]["lyrics"]
        idx = rep["inserted_tag_line_indices"]
        stripped = "\n".join(ln for i, ln in enumerate(lines) if i not in set(idx))
        assert stripped == norm(text), f"case {case}: {text!r}"
        assert all(lines[i] in ("[Verse]", "[Chorus]") for i in idx)
        assert rep["sha256"] == sha(norm(text)) == sha(stripped)
        assert rep["source_sha256"] == sha(text) and rep["output_sha256"] == sha(out["lyrics"])
        assert rep["mode"] == "exact"
        saw_inserted += bool(idx)
        saw_user_tags += (not idx and any(ln.strip().startswith("[") for ln in lines))
    assert saw_inserted > 20 and saw_user_tags > 3                    # both code paths were exercised


def test_user_written_tags_are_kept_and_nothing_is_inserted():
    thodi = compiler.load_recipe("r3_hindi_ballad")["example_lyrics"]
    out = compiler.compile(sung(thodi))
    assert out["lyrics"] == thodi and out["compile_report"]["lyrics"]["inserted_tag_lines"] == []


def test_untagged_lyrics_get_verse_chorus_tag_lines_in_separate_lines():
    text = "line one\nline two\n\nrefrain a\nrefrain b\n\nline three\n\nrefrain a\nrefrain b"
    out = compiler.compile(sung(text))
    assert out["lyrics"].split("\n")[0] == "[Verse]"
    tags = [ln for ln in out["lyrics"].split("\n") if ln.startswith("[")]
    assert tags == ["[Verse]", "[Chorus]", "[Verse]", "[Chorus]"]     # repeated stanza = chorus
    assert compiler.insert_tag_lines("only\none stanza")[0].startswith("[Verse]\nonly")


def test_newlines_normalised_and_reported():
    out = compiler.compile(sung("a\r\nb\rc"))
    assert "\r" not in out["lyrics"] and out["compile_report"]["lyrics"]["newlines_normalised"] is True


def test_lyrics_cap_4000_never_truncated():
    ok = compiler.compile(sung("x" * 4000))                   # exactly at the cap: kept whole, tags skipped
    assert ok["lyrics"] == "x" * 4000
    assert any("tags were not added" in w for w in ok["compile_report"]["warnings"])
    with pytest.raises(compiler.LyricsTooLong):
        compiler.compile(sung("y" * 4001))
    with pytest.raises(compiler.LyricsTooLong):
        compiler.compile(sung("a\r\n" * 2001))                       # 4002 chars once normalised? 2001*2 = 4002
