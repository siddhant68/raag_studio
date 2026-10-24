"""Song pipeline: genre presets, blueprints, lyric craft, the songwriter step, the song compiler and the API wiring.

No real render and no real model call: the songwriter is exercised with a scripted provider, the API with the
labelled fake engine. Musical quality is not tested here and cannot be; these tests pin structure and honesty.
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_m2_support import client_for, wait_job  # noqa: E402

from backend import compiler, genres, lyric_craft, song_blueprint, song_compiler, song_plan, songwriter  # noqa: E402
from backend import instruments as inst_db  # noqa: E402
from backend.plan_schema import CLASSIC_INSTRUMENT_IDS, INSTRUMENT_IDS, Plan  # noqa: E402
from backend.planner_base import Controls, PlannerInvalidOutput  # noqa: E402
from backend.planner_rules import BasicPlanner  # noqa: E402
from backend.providers import LlmCardDraft, LlmPlanner, assemble_card  # noqa: E402
from backend import copyright_policy  # noqa: E402

THODI = compiler.load_recipe("r3_hindi_ballad")["example_lyrics"]


def engine_request(c, round_id):
    row = c.svc.db.one("SELECT compiled_json FROM requests WHERE round_id=?", (round_id,))
    return json.loads(row["compiled_json"])["engine_request"]


def song_from_brief(brief, **ctl):
    card = BasicPlanner().plan(brief, Controls(**ctl))
    return song_plan.to_song_plan(card.plan, brief, ctl.get("genre"))


def with_lyrics(plan, text=THODI, policy="exact"):
    return plan.model_copy(update={"lyrics": plan.lyrics.model_copy(update={"policy": policy, "text": text})})


# --------------------------------------------------------------------------------------------- presets
def test_presets_load_and_are_valid():
    ps = genres.presets()
    assert len(ps) >= 35
    assert len({p["id"] for p in ps}) == len(ps)
    fams = {p["family"] for p in ps}
    assert {"hindi_song", "english_song", "indian_instrumental", "instrumental", "electronic"} <= fams
    for p in ps:
        assert p["lead"] in inst_db.INSTRUMENTS and all(i in inst_db.INSTRUMENTS for i in p["supports"])
        assert p["form"] in song_blueprint.FORMS


def test_presets_never_name_an_artist():
    text = json.dumps(genres.presets(), ensure_ascii=False).lower()
    for name in ("arijit", "lata", "rafi", "kishore", "rahman", "nusrat", "pritam", "taylor swift", "beyonce"):
        assert name not in text


def test_every_classic_recipe_has_a_preset_that_carries_it_forward():
    for rid in ("r1_flute_focus", "r2_warm_ensemble", "r3_hindi_ballad", "r4_fusion"):
        assert genres.for_recipe(rid)


@pytest.mark.parametrize("brief,expected", [
    ("a bollywood sufi qawwali at the dargah", "qawwali"),
    ("an old bollywood 70s love song", "bollywood_retro"),
    ("a lofi hindi song about rain", "hindi_lofi"),
    ("एक भजन सुबह के लिए", "bhajan"),
    ("hindi rock ballad", "hindi_rock"),
    ("festival edm with a big drop", "edm_house"),
])
def test_genre_keywords_pick_the_specific_style(brief, expected):
    assert genres.match(brief)[0][0] == expected


@pytest.mark.parametrize("pid", genres.ids())
def test_every_preset_compiles_within_budget_without_tempo_in_the_caption(pid):
    p = genres.get(pid)
    plan = song_from_brief(f"something in the style {p['name']}", genre=pid)
    if plan.voice_mode == "sung":
        plan = with_lyrics(plan)
    out = song_compiler.compile_song(plan)
    cap = out["caption"]
    assert len(cap) <= 512
    assert "BPM" not in cap and not re.search(r"\b[A-G][#b]? (?:major|minor)\b", cap)   # tempo/key are parameters
    assert p["genre_tags"].split(",")[0].strip().lower() in cap.lower()
    assert out["params"]["timesignature"] in ("2", "3", "4", "6")
    assert out["params"]["shift"] == 3.0 and out["params"]["thinking"] is False
    if plan.voice_mode == "instrumental":
        assert cap.endswith("Strictly no voices.") and out["params"]["instrumental"] is True
    report = out["compile_report"]
    assert report["pipeline"] == "song" and report["genre"] == pid and report["blueprint"]["sections"]


# --------------------------------------------------------------------------------------------- blueprints
@pytest.mark.parametrize("form", sorted(song_blueprint.FORMS))
@pytest.mark.parametrize("target", [60, 90, 120, 180, None])
def test_blueprint_fits_the_length_or_says_so(form, target):
    voice = "sung" if form in song_blueprint.SUNG_FORMS else "instrumental"
    bp = song_blueprint.build(form=form, voice_mode=voice, bpm=90, target_s=target, lead="piano",
                              supports=[{"instrument": "tabla", "role": "rhythm"}], hints={})
    assert bp.form == form
    if target:
        assert bp.target_s == target
        assert abs(sum(s.seconds for s in bp.sections) - target) < 2       # displayed times add up to the length
        if bp.fit != "ok":
            assert any("rushed" in c or "words" in c for c in bp.changes) or bp.fit == "roomy"
    else:
        assert 30 <= bp.target_s <= 240
    uids = [s["uid"] for s in bp.lyric_slots]
    assert len(uids) == len(set(uids))
    for s in bp.sections:                                                  # every repeat points at a kept source
        if s.repeat_of:
            assert s.repeat_of in uids
    choruses = [s for s in bp.sections if s.kind == "chorus"]
    if len(choruses) > 1:
        assert choruses[-1].final and choruses[-1].energy == 5


def test_short_pop_song_keeps_a_full_verse_and_chorus_at_90s():
    bp = song_blueprint.build(form="pop_song", voice_mode="sung", bpm=76, target_s=90, lead="piano", supports=[])
    names = [s.name for s in bp.sections]
    assert "Verse 1" in names and "Chorus" in names
    assert next(s for s in bp.sections if s.name == "Verse 1").lines == 4


def test_instruments_enter_over_the_song():
    sups = [{"instrument": "tanpura", "role": "drone"}, {"instrument": "tabla", "role": "rhythm"}]
    bp = song_blueprint.build(form="raag", voice_mode="instrumental", bpm=82, lead="bansuri", supports=sups, hints={})
    first, gat = bp.sections[0], next(s for s in bp.sections if s.name == "Gat")
    assert "tabla" not in first.playing and "tabla" in gat.playing
    assert any("tabla" in s.entering for s in bp.sections)


def test_instrumental_version_of_a_sung_style_never_asks_for_voices():
    p = genres.get("qawwali")
    bp = song_blueprint.build(form=p["form"], voice_mode="instrumental", bpm=96, lead="harmonium", supports=[],
                              hints=p["hints"])
    assert bp.form == "instrumental_song"
    for s in bp.sections:
        assert not song_blueprint.VOCAL_HINT.search(s.hint), s.hint


# --------------------------------------------------------------------------------------------- lyric craft
@pytest.mark.parametrize("word,n", [("समझना", 3), ("दिल", 1), ("धड़कन", 2), ("ज़िंदगी", 3), ("इंतज़ार", 3), ("प्यार", 1),
                                    ("मुस्कुराए", 4), ("Walking through the city lights", 7)])
def test_syllables(word, n):
    assert lyric_craft.syllables(word) == n


def test_assemble_repeats_the_chorus_word_for_word_and_keeps_instrumental_sections_bare():
    bp = song_blueprint.build(form="pop_song", voice_mode="sung", bpm=76, lead="acoustic_guitar", supports=[],
                              hints={"chorus": "soaring"})
    written = {s["uid"]: [f"{s['uid']} line {i}" for i in range(s["lines"])] for s in bp.lyric_slots}
    sheet = lyric_craft.assemble(bp.sections, written, voice_mode="sung")
    parsed = lyric_craft.parse_tagged(sheet)
    choruses = [lines for tag, lines in parsed if tag.startswith("Chorus")]
    assert len(choruses) >= 2 and all(c == written["chorus"] for c in choruses)
    assert parsed[0] == ("Intro", []) or parsed[0][1] == []
    assert any(tag.startswith("Chorus - ") for tag, _ in parsed)


def test_wordless_and_instrumental_sheets():
    bp = song_blueprint.build(form="wordless_song", voice_mode="wordless", bpm=88, lead="piano", supports=[])
    sheet = lyric_craft.assemble(bp.sections, {}, voice_mode="wordless")
    assert "Ooh" in sheet and "[Instrumental]" in sheet
    bp2 = song_blueprint.build(form="raag", voice_mode="instrumental", bpm=82, lead="bansuri", supports=[])
    sheet2 = lyric_craft.assemble(bp2.sections, {}, voice_mode="instrumental")
    assert sheet2.count("[Instrumental]") == len(bp2.sections) and "Ooh" not in sheet2


def test_lint_flags_gender_hook_script_and_copying():
    slots = [{"uid": "verse_1", "name": "Verse 1", "kind": "verse", "lines": 2},
             {"uid": "chorus", "name": "Chorus", "kind": "chorus", "lines": 2}]
    written = {"verse_1": ["मैं तेरे दर पे आई थी", "थोड़ी देर और यहीं ठहर"],
               "chorus": ["थोड़ी देर और यहीं ठहर", "dil ki baat sun le zara"]}
    res = lyric_craft.lint(written, slots, language="hi", singer="male", hook="एक और चाय")
    codes = {i.code for i in res.issues}
    assert {"gender_agreement", "hook_missing", "script", "verse_copies_chorus"} <= codes
    assert res.needs_revision
    ok = lyric_craft.lint({"verse_1": ["मैं तेरे दर पे आया था", "बारिश में भीगी थी शाम"],
                           "chorus": ["एक और चाय, बस", "थोड़ी देर और यहीं ठहर"]},
                          slots, language="hi", singer="male", hook="एक और चाय")
    assert not ok.needs_revision, ok.to_dict()


# --------------------------------------------------------------------------------------------- song plans
def test_rule_card_takes_the_styles_instruments_tempo_and_singer():
    plan = song_from_brief("A bollywood dance number for a wedding sangeet")
    assert plan.pipeline == "song" and plan.genre == "bollywood_dance" and plan.voice_mode == "sung"
    assert plan.lead.instrument == "synth_lead" and "dhol" in [s.instrument for s in plan.supports]
    assert plan.pace.bpm == 124 and plan.voices.singer == "female" and plan.voices.language == "hi"


def test_what_the_person_chose_wins_over_the_style():
    plan = song_from_brief("a sad english pop ballad with piano, about 2 minutes")
    assert plan.genre == "pop_ballad" and plan.lead.instrument == "piano"
    assert plan.duration_s == 120 and plan.voices.language == "en"
    plan2 = song_from_brief("a ghazal", lead="sitar", bpm=90, singer="female")
    assert plan2.lead.instrument == "sitar" and plan2.pace.bpm == 90 and plan2.voices.singer == "female"


def test_a_beat_cannot_lead():
    plan = song_from_brief("A lofi beat for studying with rain")
    assert plan.genre == "lofi_hiphop" and inst_db.can_lead(plan.lead.instrument)
    assert "drum_machine" in [s.instrument for s in plan.supports]


def test_classic_plans_keep_their_fingerprint():
    plan = compiler.default_plan("r1_flute_focus")
    data = plan.model_dump(mode="json")
    for k in ("genre", "pipeline", "meter", "form"):
        data.pop(k)
    import hashlib
    old = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert plan.fingerprint() == old


def test_new_instruments_need_the_song_pipeline():
    base = compiler.default_plan("r1_flute_focus").model_dump(mode="json")
    with pytest.raises(Exception):
        Plan.model_validate(dict(base, lead={"instrument": "dhol", "style": "simple"}))
    Plan.model_validate(dict(base, lead={"instrument": "dhol", "style": "simple"}, pipeline="song"))
    assert set(CLASSIC_INSTRUMENT_IDS) < set(INSTRUMENT_IDS)


# --------------------------------------------------------------------------------------------- compiler
def test_exact_lyrics_are_sent_unchanged():
    plan = with_lyrics(song_from_brief("A Hindi love song about tea", genre="hindi_acoustic_ballad"))
    out = song_compiler.compile_song(plan)
    sent = [ln for ln in out["lyrics"].split("\n") if ln.strip() and not ln.startswith("[")]
    own = [ln for ln in THODI.split("\n") if ln.strip() and not ln.startswith("[")]
    assert sent == own
    assert out["compile_report"]["lyrics"]["mode"] == "exact"


def test_choir_lead_in_an_instrumental_song_is_replaced_and_reported():
    plan = song_from_brief("a calm piece", genre="cinematic_orchestral", voice="instrumental", lead="choir")
    out = song_compiler.compile_song(plan)
    assert "choir" not in out["caption"].lower() and out["caption"].endswith("Strictly no voices.")
    assert any(c["kind"] == "instrumental_with_choir" for c in out["compile_report"]["conflicts"])
    assert out["compile_report"]["arrangement"]["effective"]["lead"] != "choir"


def test_avoided_instrument_is_left_out():
    plan = song_from_brief("a bhangra song", genre="punjabi_bhangra", voice="instrumental")
    plan = plan.model_copy(update={"avoid": ["dhol"]})
    out = song_compiler.compile_song(plan)
    assert "dhol" not in out["caption"].lower()
    assert {"kind": "support", "item": "dhol", "reason": "avoid"} in out["compile_report"]["dropped"]


@pytest.mark.parametrize("profile,shift,thinking", [("classic", 1.0, False), ("shift3", 3.0, False), ("lm", 3.0, True)])
def test_engine_profiles(profile, shift, thinking):
    plan = song_from_brief("A lofi beat", genre="lofi_hiphop")
    out = song_compiler.compile_song(plan, engine_profile=profile)
    assert out["params"]["shift"] == shift and out["params"]["thinking"] is thinking
    assert (out["lm_model"] is not None) is thinking
    for k in ("use_cot_metas", "use_cot_caption", "use_cot_language", "use_cot_lyrics"):
        assert out["params"][k] is False                       # the LM never rewrites caption, lyrics or metadata


def test_classic_plans_still_compile_exactly_as_before():
    plan = compiler.default_plan("r1_flute_focus")
    assert song_compiler.compile_any(plan)["caption"] == compiler.compile(plan)["caption"]


# --------------------------------------------------------------------------------------------- songwriter
class Scripted(LlmPlanner):
    name, label = "scripted", "Scripted"

    def __init__(self, answers):
        super().__init__(enabled=True)
        self.answers, self.seen = list(answers), []

    def _transport(self, system, user, schema, tool_name):
        self.seen.append({"system": system, "user": user, "tool": tool_name})
        return self.answers.pop(0)


def _sung_plan(singer="male", text=None):
    plan = song_from_brief("A Hindi love song about one more cup of tea", genre="hindi_acoustic_ballad",
                           singer=singer, duration_s=150)
    return plan.model_copy(update={"lyrics": plan.lyrics.model_copy(update={"policy": "write", "text": text})})


def _answer(bp, chorus=("एक और चाय, बस", "थोड़ी देर और ठहर जा", "बातों में शाम ढले", "तेरा साथ रहे यहाँ"),
            verse_word="आया"):
    secs = []
    for s in bp.lyric_slots:
        if s["uid"] == "chorus":
            lines = list(chorus)[: s["lines"]]
        else:
            nth = {"verse_1": "पहली", "verse_2": "दूसरी", "pre_chorus": "तीसरी", "bridge": "चौथी"}.get(s["uid"], "")
            lines = [f"मैं तेरी गली में {verse_word} था" if i == 0 and s["uid"] == "verse_1"
                     else f"खिड़की पे {nth} धूप रुकी {'एक दो तीन चार'.split()[i]}" for i in range(s["lines"])]
        secs.append({"uid": s["uid"], "lines": lines})
    return {"title": "एक और चाय", "hook": "एक और चाय", "sections": secs}


def test_songwriter_writes_once_and_the_chorus_returns_word_for_word():
    plan = _sung_plan()
    bp = song_plan.blueprint_for(plan)
    p = Scripted([_answer(bp)])
    song = p.draft_song_lyrics(plan, bp)
    assert len(p.seen) == 1 and p.seen[0]["tool"] == "submit_song_lyrics"
    assert "<theme>" in p.seen[0]["user"] and "masculine" in p.seen[0]["user"]
    parsed = lyric_craft.parse_tagged(song.text)
    choruses = [lines for tag, lines in parsed if tag.startswith("Chorus")]
    assert len(choruses) >= 2 and len({tuple(c) for c in choruses}) == 1
    assert song.title == "एक और चाय" and not song.revised


def test_songwriter_revises_once_when_the_check_finds_a_wrong_gender():
    plan = _sung_plan(singer="male")
    bp = song_plan.blueprint_for(plan)
    p = Scripted([_answer(bp, verse_word="आई"), _answer(bp, verse_word="आया")])
    song = p.draft_song_lyrics(plan, bp)
    assert len(p.seen) == 2 and "Fix these problems" in p.seen[1]["user"] and song.revised
    assert "आई" not in song.text


def test_songwriter_refuses_a_missing_section():
    plan = _sung_plan()
    bp = song_plan.blueprint_for(plan)
    bad = _answer(bp)
    bad["sections"] = [s for s in bad["sections"] if s["uid"] != "chorus"]
    p = Scripted([bad, bad])
    with pytest.raises(PlannerInvalidOutput):
        p.draft_song_lyrics(plan, bp)


def test_songwriter_never_sees_exact_lyrics():
    plan = with_lyrics(_sung_plan(), text="मेरे अपने शब्द")
    with pytest.raises(Exception):
        Scripted([]).draft_song_lyrics(plan, song_plan.blueprint_for(plan))


def test_smart_card_with_a_style_moves_to_the_song_pipeline():
    draft = LlmCardDraft.model_validate({
        "voice_mode": "instrumental", "lead": {"instrument": "sitar", "style": "ornate"},
        "supports": [{"instrument": "tabla", "role": "rhythm", "presence": "gentle"}], "genre": "raag_sitar"})
    card = assemble_card("an evening raga", copyright_policy.sanitize("an evening raga"), draft, Controls(),
                         provider="x", label="X")
    assert card.plan.pipeline == "song" and card.plan.genre == "raag_sitar"
    assert card.plan.provenance["genre"].source == "suggested"


# --------------------------------------------------------------------------------------------- API
def test_api_creates_a_song_pipeline_take(tmp_path):
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json={"brief": "A lofi beat for studying with rain", "duration": 20, "takes": 1})
        assert r.status_code == 202, r.text
        data = r.json()
        assert data["plan"]["pipeline"] == "song" and data["plan"]["genre"] == "lofi_hiphop"
        job = wait_job(c, data["job_id"])
        assert job["state"] == "succeeded"
        req = engine_request(c, data["round_id"])
        assert req["params"]["shift"] == 3.0 and "BPM" not in req["params"]["caption"]
        assert req["meta"]["pipeline"] == "song" and req["meta"]["engine_profile"] == "shift3"
        assert req["params"]["lyrics"].startswith("[Intro")


def test_api_style_control_and_reset(tmp_path):
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json={"brief": "a quiet evening piece", "controls": {"genre": "raag_sitar"},
                                       "duration": 20, "takes": 1})
        assert r.status_code == 202, r.text
        data = r.json()
        assert data["plan"]["genre"] == "raag_sitar" and data["plan"]["provenance"]["genre"]["source"] == "you"
        assert data["plan"]["lead"]["instrument"] == "sitar"
        out = c.patch(f"/api/songs/{data['song_id']}/controls", json={"genre": "meditation"}).json()
        assert out["plan"]["genre"] == "meditation" and out["compile_report"]["genre"] == "meditation"
        back = c.patch(f"/api/songs/{data['song_id']}/controls", json={"genre": None}).json()
        assert back["plan"]["provenance"]["genre"]["source"] != "you"
        bad = c.post("/api/songs", json={"brief": "x", "controls": {"genre": "no_such_style"}})
        assert bad.status_code == 422


def test_api_genres_and_instruments(tmp_path):
    with client_for(tmp_path) as c:
        g = c.get("/api/genres").json()["genres"]
        assert len(g) == len(genres.ids()) and {"id", "name", "blurb", "voice"} <= set(g[0])
        ins = c.get("/api/instruments").json()["instruments"]
        assert {i["id"] for i in ins} == set(INSTRUMENT_IDS)


def test_api_engine_profile_setting(tmp_path):
    with client_for(tmp_path) as c:
        assert c.put("/api/settings", json={"engine_profile": "classic"}).status_code == 200
        r = c.post("/api/songs", json={"brief": "A lofi beat", "duration": 20, "takes": 1}).json()
        req = engine_request(c, r["round_id"])
        assert req["params"]["shift"] == 1.0
        assert c.put("/api/settings", json={"engine_profile": "lm"}).status_code == 200
        r = c.post("/api/songs", json={"brief": "A lofi beat", "duration": 20, "takes": 1}).json()
        req = engine_request(c, r["round_id"])
        assert req["params"]["thinking"] is True and req["lm"]["model"] == song_compiler.LM_MODEL
        assert c.put("/api/settings", json={"engine_profile": "turbo"}).status_code == 422
        # a real engine without the LM weights refuses before queueing anything
        c.svc.config.engine = "real"
        c.svc.probe.lm_installed = lambda: False
        plan = song_from_brief("A lofi beat")
        from backend.schemas import ApiError
        with pytest.raises(ApiError) as e:
            c.svc._compile(plan, 1)
        assert e.value.code == "lm_not_installed"
        c.svc.config.engine = "fake"


def test_api_classic_mode_keeps_classic_plans(tmp_path):
    with client_for(tmp_path, RAAG_SONG_PIPELINE="0") as c:
        r = c.post("/api/songs", json={"brief": "A peaceful bansuri at dawn, gentle tabla, no singing",
                                       "duration": 20, "takes": 1}).json()
        assert r["plan"]["pipeline"] == "classic"
        r2 = c.post("/api/songs", json={"brief": "A lofi beat for studying", "duration": 20, "takes": 1}).json()
        assert r2["plan"]["pipeline"] == "song"                # a named style still uses the song pipeline


@pytest.mark.parametrize("role", ["instruments", "lead"])
def test_api_every_instrument_gives_a_plan_or_a_4xx(tmp_path, role):
    with client_for(tmp_path) as c:
        for inst in INSTRUMENT_IDS:
            ctl = {"instruments": [inst]} if role == "instruments" else {"lead": inst}
            r = c.post("/api/songs", json={"brief": "a gentle evening piece", "controls": ctl, "duration": 10,
                                           "takes": 1})
            assert r.status_code < 500, (role, inst, r.text)
            if r.status_code == 202:
                plan = r.json()["plan"]
                if inst != "choir" and role == "lead":
                    assert plan["lead"]["instrument"] == inst


def test_api_another_take_from_a_song_plan_reuses_it(tmp_path):
    with client_for(tmp_path) as c:
        data = c.post("/api/songs", json={"brief": "A lofi beat", "duration": 10, "takes": 1}).json()
        wait_job(c, data["job_id"])
        take = c.get(f"/api/songs/{data['song_id']}").json()["takes"][0]["id"]
        c.patch(f"/api/songs/{data['song_id']}/controls", json={"genre": "ambient"})
        r = c.post(f"/api/songs/{data['song_id']}/rounds", json={"kind": "another", "from_take": take, "takes": 1})
        assert r.status_code == 202 and r.json()["plan_id"] == data["plan_id"]
