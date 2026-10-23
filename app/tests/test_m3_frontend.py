"""AT-M3-01 .. AT-M3-07 (mechanical): the static web UI served at /, its control inventory, honesty rules,
and the player / library / progress flows against the fake engine through the API.

The browser itself is not driven here (no extra dependencies); the pure rules are tested by node in
test_m3_logic.py and the pages were checked by hand in a browser (see reports/M3.md).
"""
import json
import re
import shutil
import subprocess
import sys
import threading
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pytest

from test_m2_support import (BRIEF, FFMPEG, LiveServer, client_for, create_and_wait, create_body, decodes_clean,
                             wait_job)

APP = Path(__file__).resolve().parents[1]
WEB = APP / "web"
JS_DIR = Path(__file__).resolve().parent / "js"
NODE = shutil.which("node")
CAPS = json.loads((APP / "backend" / "capabilities.json").read_text(encoding="utf-8"))
VOID = {"input", "br", "meta", "link", "img", "hr", "source", "area", "base", "col", "embed", "param", "track", "wbr"}
INTERACTIVE = {"input", "select", "textarea", "button", "a", "summary", "audio"}


# --------------------------------------------------------------------------- tiny static DOM
class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.text = tag, dict(attrs), parent, [], []

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent

    def hidden_on_load(self) -> bool:
        """Not visible when the page first loads: hidden attribute, inert <template>, or inside a closed <details>."""
        chain = [self] + list(self.ancestors())
        for i, n in enumerate(chain):
            if "hidden" in n.attrs or n.tag == "template":
                return True
            if n.tag == "details" and "open" not in n.attrs and i > 0:
                child = chain[i - 1]
                if child.tag != "summary":
                    return True
        return False


class Dom(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root
        self.all = []

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        self.all.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.text.append(data)


def parse_index() -> Dom:
    dom = Dom()
    dom.feed((WEB / "index.html").read_text(encoding="utf-8"))
    return dom


def web_files():
    return [p for p in WEB.rglob("*") if p.is_file()]


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def control_of(node: Node):
    for n in [node] + list(node.ancestors()):
        if "data-control" in n.attrs:
            return n.attrs["data-control"]
    return None


# --------------------------------------------------------------------------- AT-M3-01
def test_at_m3_01_index_and_every_asset_load_and_nothing_points_off_localhost(tmp_path):
    with client_for(tmp_path) as c:
        r = c.get("/")
        assert r.status_code == 200 and "text/html" in r.headers["content-type"]
        html = r.text
        assert "Raag Studio" in html
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
        assert "default-src 'self'" in csp and "connect-src 'self'" in csp and "script-src 'self'" in csp

        # every URL-ish attribute in the page
        dom = parse_index()
        urls = []
        for n in dom.all:
            for attr in ("href", "src", "action", "poster", "data"):
                if attr in n.attrs and n.attrs[attr]:
                    urls.append(n.attrs[attr])
        assets = set()
        for u in urls:
            if u.startswith(("#", "data:")):
                continue
            assert not re.match(r"^(https?:)?//", u) or re.match(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?/", u), f"off-host URL {u}"
            if u.startswith("/"):
                assets.add(u)
        assert "/app.css" in assets and "/js/main.js" in assets

        # follow module imports and CSS url()s
        queue, seen = list(assets), set()
        while queue:
            path = queue.pop()
            if path in seen or path.startswith("/api/"):
                continue
            seen.add(path)
            resp = c.get(path)
            assert resp.status_code == 200, path
            body = resp.text
            if path.endswith(".js"):
                for pair in re.findall(r'''^\s*(?:import|export)\b[^;"']*?from\s*["']([^"']+)["']|\bimport\(\s*["']([^"']+)["']''', body, re.M):
                    spec = pair[0] or pair[1]
                    assert spec.startswith("./") or spec.startswith("/"), f"bare or off-host import {spec} in {path}"
                    queue.append("/js/" + spec[2:] if spec.startswith("./") else spec)
            if path.endswith(".css"):
                for spec in re.findall(r"url\(\s*['\"]?([^)'\"]+)", body):
                    assert spec.startswith(("data:", "/")), f"css url {spec}"
                    if spec.startswith("/"):
                        queue.append(spec)
                assert "@import" not in body
        assert {"/app.css", "/js/main.js", "/js/logic.js", "/js/song.js", "/js/create.js"} <= seen


def test_at_m3_01_no_off_host_urls_cdns_or_network_apis_anywhere_in_the_web_files():
    cdn = re.compile(r"cdn\.|cdnjs|unpkg|jsdelivr|googleapis|gstatic|fonts\.|bootstrapcdn|cloudflare|jquery\.com|tailwindcss\.com", re.I)
    for p in web_files():
        text = read(p)
        assert not cdn.search(text), f"CDN reference in {p}"
        for m in re.finditer(r"https?://[^\s\"'`)<>]+", text):
            url = m.group(0)
            ok = url.startswith(("http://127.0.0.1", "http://localhost")) or url == "http://www.w3.org/2000/svg"  # SVG namespace in the data: icon
            assert ok, f"{p.name}: {url}"
        assert not re.search(r"\bnew\s+WebSocket\b|navigator\.sendBeacon|importScripts", text), p
        # every fetch goes to our own /api/ paths
        for m in re.finditer(r"\bfetch\(\s*([^,)]+)", text):
            assert m.group(1).strip().strip("`\"'").startswith(("/api/", "path")), (p.name, m.group(1))
        for m in re.finditer(r"""api\(\s*[`"']([^`"']+)""", text):
            assert m.group(1).startswith("/api/"), (p.name, m.group(1))


# --------------------------------------------------------------------------- AT-M3-02
def controls_by_visibility(dom):
    ids_all, ids_visible = set(), set()
    for n in dom.all:
        cid = n.attrs.get("data-control")
        if cid is None:
            continue
        ids_all.add(cid)
        if not n.hidden_on_load():
            ids_visible.add(cid)
    return ids_all, ids_visible


def test_at_m3_02_control_inventory():
    dom = parse_index()
    all_ids, visible = controls_by_visibility(dom)
    legal = {f"C{i}" for i in range(1, 26)}
    assert all_ids <= legal, f"ids outside C1-C25: {all_ids - legal}"
    assert all_ids == legal, f"missing control ids: {legal - all_ids}"        # all 25 exist somewhere (template or drawer)
    assert len(all_ids) <= 25
    assert visible == {"C1", "C2", "C3", "C4", "C5"}, visible
    assert len(visible) <= 9
    # C13-C17 are hidden until the matching voice mode; the Details drawer and Shape it are collapsed
    for cid in ("C13", "C14", "C15", "C16", "C17"):
        assert cid not in visible
    for cid in ("C6", "C7", "C8", "C9", "C10", "C11", "C12", "C22", "C23", "C24", "C25"):
        assert cid not in visible
    shape = next(n for n in dom.all if n.attrs.get("id") == "shape-it")
    details = next(n for n in dom.all if n.attrs.get("id") == "details-drawer")
    assert "open" not in shape.attrs and "open" not in details.attrs
    # Create starts disabled (no brief yet)
    assert "disabled" in next(n for n in dom.all if n.attrs.get("id") == "btn-create").attrs
    # every interactive element belongs to a C-control or is named chrome (nothing smuggled in)
    for n in dom.all:
        if n.tag in INTERACTIVE and not (n.tag == "input" and n.attrs.get("type") == "hidden"):
            assert control_of(n) or "data-chrome" in n.attrs or any("data-chrome" in a.attrs for a in n.ancestors()), \
                f"interactive element outside C1-C25 and not chrome: <{n.tag} {n.attrs}>"
    # ids used in the JS are inside the legal range too
    for p in WEB.glob("js/*.js"):
        for cid in re.findall(r"""data-control["']?\s*[:=]\s*["']?(C\d+)""", read(p)) + re.findall(r"""controlId?\s*=\s*["'](C\d+)""", read(p)):
            assert cid in legal


def test_at_m3_02_capabilities_and_html_control_ids_agree():
    assert set(CAPS["controls"]) == {f"C{i}" for i in range(1, 26)}


# --------------------------------------------------------------------------- AT-M3-03 (DOM wiring; rules are in node)
def test_at_m3_03_voice_dependent_fields_start_hidden_and_logic_module_drives_them():
    dom = parse_index()
    by_ctl = {n.attrs["data-control"]: n for n in dom.all if "data-control" in n.attrs}
    for cid in ("C13", "C14", "C15", "C16", "C17"):
        assert "hidden" in by_ctl[cid].attrs, cid
    create_js = read(WEB / "js" / "create.js")
    assert "voiceVisibility" in create_js and "setVoiceMode" in create_js and "hiddenVoiceValues" in create_js


# --------------------------------------------------------------------------- AT-M3-04 / 05
def test_at_m3_04_planner_badge_comes_from_the_api_and_plan_view_shows_provenance(tmp_path):
    html = read(WEB / "index.html")
    badge = re.search(r'<span id="planner-badge"[^>]*>([^<]*)<', html).group(1)
    assert "Basic" not in badge and "Claude" not in badge                       # nothing hard-coded: it says "loading"
    assert "store.planner.label" in read(WEB / "js" / "system.js")
    song_js = read(WEB / "js" / "song.js")
    assert "provider_label" in song_js and "planner_status" in song_js and "provenanceInfo" in song_js
    # the real API data the UI renders: badge label, provenance on every field, no word "AI" after the UI's own filter
    with client_for(tmp_path) as c:
        planner = c.get("/api/settings").json()["planner"]
        assert planner["label"] == "Basic planner"
        data, job, detail = create_and_wait(c, brief="the quiet right after rain, someone playing flute on the ghat, tabla barely there", duration=10, takes=1)
        plan_rec = detail["plans"][0]
        assert plan_rec["card"]["provider_label"] == "Basic planner"
        plan = plan_rec["plan"]
        rows = json.loads(run_node("planRows", [plan]))
        shown = [r for r in rows if r["control"] in ("C2", "C6", "C7", "C8")]
        assert shown and all(r["prov"] and r["prov"]["source"] in ("you", "suggested", "recipe", "rule") and r["prov"]["reason"] for r in shown)
        notes = json.loads(run_node("plannerNotes", [plan_rec["card"]]))
        assert not re.search(r"\bAI\b", " ".join(notes))


def run_node(fn, args):
    assert NODE, "node is required"
    done = subprocess.run([NODE, str(JS_DIR / "apply.mjs"), fn], input=json.dumps(args), capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_at_m3_05_no_faders_locks_headcounts_or_per_instrument_levels():
    banned = re.compile(r"\bfaders?\b|\bvolume\b|\bgain\b|\bpan\b|\bheadcount\b|\block(?:ed|s)?\b|\bfreeze\b", re.I)
    for p in web_files():
        if p.suffix in (".html", ".js"):
            for m in banned.finditer(read(p)):
                line = read(p)[max(0, m.start() - 60): m.end() + 40].replace("\n", " ")
                pytest.fail(f"{p.name}: banned word {m.group(0)!r} near: {line}")
    html = read(WEB / "index.html")
    assert 'type="range"' not in html and "<meter" not in html and "orient=" not in html
    assert not re.search(r"type\s*[:=]\s*[\"']range", "".join(read(p) for p in WEB.glob("js/*.js")))
    assert len(re.findall(r"<audio\b", html)) == 1                                  # one player
    # C14 offers word sizes (None / Light / Choir / Big), not a number
    assert "headcount" not in html.lower()


def test_at_m3_05_every_b_or_d_control_has_a_label_slot_filled_from_the_registry():
    dom = parse_index()
    slots = {n.attrs["data-cap-for"] for n in dom.all if "data-cap-for" in n.attrs}
    need = {cid for cid, c in CAPS["controls"].items() if set(c["classes"]) & {"b", "d"}}
    assert need <= slots, f"b/d controls without a label slot: {sorted(need - slots)}"
    caps_js = read(WEB / "js" / "caps.js")
    assert 'api("/api/capabilities")' in caps_js and "data-cap-for" in caps_js
    assert "applyCapabilityLabels" in read(WEB / "js" / "main.js")
    # the wording lives only in capabilities.json: none of the registry's label or wording strings is copied into the UI files
    sources = "\n".join(read(p) for p in WEB.rglob("*") if p.suffix in (".js", ".html"))
    for cls in CAPS["classes"].values():
        if cls["label"]:
            assert cls["label"] not in sources, f"hard-coded label {cls['label']!r}"
    for cid in need:
        w = CAPS["controls"][cid]["ui_wording"]
        if len(w) > 12:
            assert w not in sources, f"hard-coded wording for {cid}: {w}"


def test_at_m3_05_api_serves_labels_for_every_control(tmp_path):
    with client_for(tmp_path) as c:
        caps = c.get("/api/capabilities").json()
        for cid, ctl in CAPS["controls"].items():
            served = caps["controls"][cid]
            assert served["classes"] == ctl["classes"]
            if set(ctl["classes"]) & {"b", "d"}:
                assert served["needs_label"] and served["labels"], cid
                assert {l["label"] for l in served["labels"]} <= {v["label"] for v in CAPS["classes"].values()}
        assert caps["options"]["C15"]["hi"]["badge"] == "experimental"
        assert caps["options"]["C15"]["en"]["badge"] == "untested"


def test_honesty_copy_is_present_in_the_page():
    text = read(WEB / "index.html") + "".join(read(p) for p in WEB.glob("js/*.js"))
    assert "Exact lyrics sent unchanged, listen to check singing" in text
    assert "Technical checks passed" in text or "Technical checks" in text
    assert "Your verdict" in text
    assert "new performances from an updated plan" in text.lower()
    assert not re.search(r"sounds good(?! about)", text) or "say nothing about whether the music is good" in text
    assert "Smart planners are off" in text
    # no UI path flips smart planners on: settings are only ever read (GET), never written, by the web files
    js = "".join(read(p) for p in WEB.glob("js/*.js"))
    assert not re.search(r"/api/settings[\"'`]\s*,", js), "a call to /api/settings passes options (a write?)"
    assert not re.search(r"[\"']PUT[\"']|planner_smart_enabled|planner_provider", js)


# --------------------------------------------------------------------------- AT-M3-06
def test_at_m3_06_player_library_heart_persistence_and_export(tmp_path):
    with client_for(tmp_path) as c:
        data, job, detail = create_and_wait(c, takes=3, duration=10)
        song = data["song_id"]
        takes = detail["takes"]
        assert [t["label"] for t in takes] == ["T1", "T2", "T3"]
        t1 = takes[0]
        # play / seek: one URL per take, Range works
        full = c.get(t1["audio_url"])
        assert full.status_code == 200 and full.headers["accept-ranges"] == "bytes"
        part = c.get(t1["audio_url"], headers={"Range": "bytes=100-199"})
        assert part.status_code == 206 and len(part.content) == 100
        assert part.headers["content-range"].startswith("bytes 100-199/")
        assert part.headers["x-raag-engine"] == "fake"
        # heart + rating + reason persist across a "reload" (a fresh GET of the song)
        c.post(f"/api/takes/{t1['id']}/feedback", json={"favourite": True, "rating": "love", "tags": ["melody"]})
        again = c.get(f"/api/songs/{song}").json()["takes"][0]
        assert (again["favourite"], again["rating"], again["tags"]) == (True, "love", ["melody"])
        listing = c.get("/api/songs").json()["songs"][0]
        assert listing["favourite_count"] == 1 and listing["take_count"] == 3
        c.post(f"/api/takes/{t1['id']}/feedback", json={"favourite": False})
        assert c.get(f"/api/songs/{song}").json()["takes"][0]["favourite"] is False
        # lineage: a chip refine is a new round that points at the take it started from
        r = c.post(f"/api/songs/{song}/rounds", json={"kind": "refine", "chips": ["slower"], "from_take": takes[1]["id"], "takes": 2})
        assert r.status_code == 202
        assert "updated plan" in r.json()["card"]["notice"]
        wait_job(c, r.json()["job_id"])
        d2 = c.get(f"/api/songs/{song}").json()
        assert [x["kind"] for x in d2["rounds"]] == ["create", "refine"]
        assert d2["rounds"][1]["parent_take_id"] == takes[1]["id"]
        lineage = run_node("lineageText", [d2["rounds"][1], "round 1, T2"])
        assert "not an edit of round 1, T2" in lineage
        # export downloads and decodes
        ex = c.post(f"/api/takes/{takes[2]['id']}/exports", json={"format": "mp3", "end_fade_s": 1})
        assert ex.status_code == 201
        body = ex.json()
        assert body["engine"] == "fake" and body["notice"] and body["filename"].endswith(".mp3")
        dl = c.get(body["url"])
        assert dl.status_code == 200 and "attachment" in dl.headers["content-disposition"]
        out = tmp_path / "dl.mp3"
        out.write_bytes(dl.content)
        assert decodes_clean(out)
        # the song detail lists the export, which the page shows as a link under the take
        assert any(e["take_id"] == takes[2]["id"] for e in c.get(f"/api/songs/{song}").json()["exports"])


def test_at_m3_06_fake_takes_are_loudly_labelled_for_the_banner(tmp_path):
    with client_for(tmp_path) as c:
        data, job, detail = create_and_wait(c, takes=1, duration=10)
        assert c.get("/api/system").json()["engine"] == "fake"
        assert detail["takes"][0]["engine"] == "fake" and "FAKE" in detail["takes"][0]["notice"]
        assert c.get("/").status_code == 200
        song_js = read(WEB / "js" / "song.js") + read(WEB / "js" / "system.js") + read(WEB / "index.html")
        assert 'engine === "fake"' in song_js and "fake-banner" in song_js and "TEST AUDIO" in song_js


def test_library_prune_requires_confirm_and_keeps_hearts(tmp_path):
    with client_for(tmp_path) as c:
        data, job, detail = create_and_wait(c, takes=2, duration=10)
        t1, t2 = detail["takes"]
        c.post(f"/api/takes/{t1['id']}/feedback", json={"favourite": True})
        assert c.post("/api/admin/prune", json={"older_than_days": 0}).status_code == 400
        r = c.post("/api/admin/prune", json={"older_than_days": 0, "confirm": True}).json()
        assert r["pruned"] == 1 and r["skipped_favourites"] == [t1["id"]]
        st = c.get("/api/storage").json()
        assert st["disk_total_gib"] > st["disk_free_gib"] > 0 and st["native_files"] == 1
        # the library page asks first: there is a dialog and the call only happens after "ok"
        lib = read(WEB / "js" / "library.js")
        assert "confirmDialog(" in lib and "confirm: true" in lib and lib.index("confirmDialog(") < lib.index("confirm: true")
        assert "setInterval" not in lib and "setTimeout" not in lib               # never automatic


# --------------------------------------------------------------------------- AT-M3-07
def test_at_m3_07_sse_phases_and_polling_fallback_exist(tmp_path):
    server = LiveServer(tmp_path, RAAG_FAKE_TAKE_S="0.4").start()
    events, ready = [], threading.Event()

    def reader():
        try:
            with httpx.Client(timeout=None) as client:
                with client.stream("GET", f"{server.base}/api/events") as resp:
                    name = data = None
                    for line in resp.iter_lines():
                        if line.startswith(": connected"):
                            ready.set()
                        elif line.startswith("event:"):
                            name = line[6:].strip()
                        elif line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                        elif line == "" and name:
                            events.append((name, data))
                            name = data = None
        except httpx.HTTPError:
            pass
    threading.Thread(target=reader, daemon=True).start()
    try:
        assert ready.wait(10)
        r = httpx.post(f"{server.base}/api/songs", json=create_body(), timeout=10)
        job_id = r.json()["job_id"]
        import time
        t0 = time.time()
        while time.time() - t0 < 30 and not any(n == "takes_ready" for n, _ in events):
            time.sleep(0.1)
        jobs = [d for n, d in events if n == "job" and d["id"] == job_id]
        # what the progress strip would show for each streamed job event, computed by the real UI logic
        shown = []
        for j in jobs:
            pv = json.loads(run_node("progressView", [j]))
            active = [s["label"] for s in pv["steps"] if s["state"] == "active"]
            shown.append(active[0] if active else "Done")
        order = [s for i, s in enumerate(shown) if i == 0 or s != shown[i - 1]]
        assert order[0] == "Queued" and "Loading the music model" in order and "Checking the files" in order
        assert any(re.fullmatch(r"Take \d/2", s) for s in order) and order[-1] == "Done", order
    finally:
        server.stop()
    api_js = read(WEB / "js" / "api.js")
    song_js = read(WEB / "js" / "song.js")
    assert "EventSource" in api_js and "/api/events" in api_js
    assert "/api/jobs/" in song_js and "status() === \"live\"" in song_js                # polling fallback


def test_at_m3_07_failure_gives_a_human_message_and_only_a_manual_retry(tmp_path, monkeypatch):
    monkeypatch.setenv("RAAG_FAKE_FAIL", "1")
    with client_for(tmp_path) as c:
        r = c.post("/api/songs", json=create_body(takes=1))
        job = wait_job(c, r.json()["job_id"])
        assert job["state"] == "failed" and job["error"]
        pv = json.loads(run_node("progressView", [job]))
        assert pv["failed"] and pv["canRetry"] and not pv["canCancel"] and pv["detail"] == job["error"]
        before = c.svc.db.one("SELECT COUNT(*) FROM jobs")[0]
        import time
        time.sleep(1.5)
        assert c.svc.db.one("SELECT COUNT(*) FROM jobs")[0] == before                # nothing retried by itself
        monkeypatch.delenv("RAAG_FAKE_FAIL")                                         # the person fixes the cause and presses Try again
        again = c.post(f"/api/songs/{r.json()['song_id']}/rounds", json={"kind": "another", "takes": 1},
                       headers={"Idempotency-Key": "press-2"})
        assert again.status_code == 202 and again.json()["job_id"] != job["id"]
        assert wait_job(c, again.json()["job_id"])["state"] == "succeeded"
    song_js = read(WEB / "js" / "song.js")
    # startRound is only ever called from click handlers (no timer or event path retries)
    for m in re.finditer(r"startRound\(", song_js):
        line_start = song_js.rfind("\n", 0, m.start()) + 1
        line = song_js[line_start: song_js.find("\n", m.start())]
        assert "addEventListener(\"click\"" in line or line.lstrip().startswith("async function startRound"), line
    html = read(WEB / "index.html")
    assert 'id="btn-retry"' in html and "Try again" in html and 'id="btn-cancel"' in html


def test_at_m3_07_mac_busy_reason_reaches_the_progress_strip(tmp_path):
    job = {"state": "queued", "phase": "waiting", "reason": "mac_busy", "progress": {"message": "The video generator is busy. Your job starts when it is idle."}}
    pv = json.loads(run_node("progressView", [job]))
    assert pv["waiting"] and "busy" in pv["headline"] and pv["canCancel"]
