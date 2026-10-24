"""The personal ElevenLabs script: plan conversion and spending guards, with a mock HTTP transport (no network)."""
import json
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts" / "personal"))

import elevenlabs_render as el  # noqa: E402
from experiments.listening_batch import load_briefs, plan_for  # noqa: E402
from backend import lyric_craft  # noqa: E402


def brief(bid):
    return next(b for b in load_briefs() if b["id"] == bid)


def test_sung_plan_keeps_every_word_and_section_length():
    b = brief("chai_bollywood")
    cp = el.composition_plan(plan_for(b, "new"))
    assert 1 <= len(cp["chunks"]) <= el.MAX_CHUNKS
    total = sum(c["duration_ms"] for c in cp["chunks"]) / 1000
    assert abs(total - b["duration_s"]) < 3
    sent = [ln for c in cp["chunks"] for ln in c["text"].split("\n")[1:]]
    own = [ln for _, lines in lyric_craft.parse_tagged(b["lyrics_text"]) for ln in lines]
    assert sent == own                                              # exact words, in order, nothing added
    assert all(el.MIN_CHUNK_MS <= c["duration_ms"] <= el.MAX_CHUNK_MS for c in cp["chunks"])
    assert len(cp["chunks"][0]["positive_styles"]) >= 6             # the first chunk carries the global style
    for c in cp["chunks"]:
        assert all(s.isascii() for s in c["positive_styles"])     # styles must be English
    assert cp["chunks"][0]["negative_styles"] == ["vocals"]       # the intro is instrumental


def test_instrumental_plan_forbids_vocals_everywhere():
    cp = el.composition_plan(plan_for(brief("yamuna"), "new"))
    assert all(c["negative_styles"] == ["vocals"] for c in cp["chunks"])
    assert all(c["text"].count("\n") == 0 for c in cp["chunks"])


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_render_refuses_above_the_cap_and_below_the_balance(tmp_path, monkeypatch):
    monkeypatch.setattr(el, "LEDGER", tmp_path / "ledger.json")
    cp = el.composition_plan(plan_for(brief("yamuna"), "new"))
    calls = []

    def handler(req):
        calls.append(req.url.path)
        return httpx.Response(200, json={"character_count": 99000, "character_limit": 100000})

    with pytest.raises(SystemExit):
        el.render(cp, key="k", max_credits=100, out_root=tmp_path, client=_client(handler))
    assert calls == []                                              # refused before any call
    with pytest.raises(SystemExit):
        el.render(cp, key="k", max_credits=10000, out_root=tmp_path, client=_client(handler))
    assert calls == ["/v1/user/subscription"]                      # balance read, nothing composed


def test_render_saves_the_song_and_a_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(el, "LEDGER", tmp_path / "ledger.json")
    cp = el.composition_plan(plan_for(brief("yamuna"), "new"))
    state = {"count": 1000}

    def handler(req):
        if req.url.path == "/v1/user/subscription":
            return httpx.Response(200, json={"character_count": state["count"], "character_limit": 100000})
        assert req.url.path == "/v1/music" and req.url.params["output_format"] == el.OUTPUT_FORMAT
        body = json.loads(req.content)
        assert body["model_id"] == "music_v2_5" and body["composition_plan"] == cp
        assert req.headers["xi-api-key"] == "k"
        state["count"] += 2000
        return httpx.Response(200, content=b"ID3fake", headers={"song-id": "abc"})

    entry = el.render(cp, key="k", max_credits=5000, out_root=tmp_path, client=_client(handler))
    assert entry["credits_used"] == 2000 and entry["song_id"] == "abc"
    folder = Path(entry["folder"])
    assert (folder / "song.mp3").read_bytes() == b"ID3fake" and (folder / "composition_plan.json").is_file()
    assert json.loads((tmp_path / "ledger.json").read_text())[0]["credits_used"] == 2000


def test_a_timeout_is_never_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(el, "LEDGER", tmp_path / "ledger.json")
    cp = el.composition_plan(plan_for(brief("yamuna"), "new"))
    posts = []

    def handler(req):
        if req.url.path == "/v1/user/subscription":
            return httpx.Response(200, json={"character_count": 0, "character_limit": 100000})
        posts.append(1)
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(SystemExit):
        el.render(cp, key="k", max_credits=5000, out_root=tmp_path, client=_client(handler))
    assert posts == [1]
    assert any(p.name == "TIMEOUT.txt" for p in tmp_path.rglob("*"))


def test_preview_never_calls_the_network(tmp_path, capsys):
    plan = plan_for(brief("yamuna"), "new")
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(plan.model_dump(mode="json")))
    assert el.main(["--plan", str(f)]) == 0
    assert "Preview only" in capsys.readouterr().out
