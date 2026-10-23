// node --test app/tests/js   (no npm, no DOM): the pure UI rules from app/web/js/logic.js
import test from "node:test";
import assert from "node:assert/strict";
import * as L from "../../web/js/logic.js";

const form = (over = {}) => ({ ...L.initialFormState(), brief: "the quiet right after rain", ...over });

test("AT-M3-02: Create is disabled for a blank or whitespace brief", () => {
  assert.equal(L.canCreate(form({ brief: "" })).ok, false);
  assert.equal(L.canCreate(form({ brief: "   \n\t " })).ok, false);
  assert.equal(L.canCreate(form()).ok, true);
});

test("AT-M3-03: Instrumental and Auto hide C13-C17", () => {
  for (const mode of ["auto", "instrumental"]) {
    const v = L.voiceVisibility(mode, null);
    assert.deepEqual(Object.values(v), [false, false, false, false, false], mode);
  }
});

test("AT-M3-03: Wordless shows C13-C15 only; Sung shows C15-C17 (C17 with 'exact')", () => {
  assert.deepEqual(L.voiceVisibility("wordless", null), { C13: true, C14: true, C15: true, C16: false, C17: false });
  const s = L.setVoiceMode(form(), "sung");
  assert.equal(s.lyricsSource, "exact");
  assert.deepEqual(L.voiceVisibility(s.voice, s.lyricsSource), { C13: true, C14: true, C15: true, C16: true, C17: true });
});

test("AT-M3-03: switching voice mode leaves no hidden conflicting value", () => {
  let s = L.setVoiceMode(form(), "sung");
  s = { ...s, singer: "female", background: "choir", language: "hi", lyricsText: "तेरी याद में" };
  assert.deepEqual(L.hiddenVoiceValues(s), []);
  for (const mode of ["instrumental", "auto", "wordless"]) {
    const t = L.setVoiceMode(s, mode);
    assert.deepEqual(L.hiddenVoiceValues(t), [], mode);
    assert.equal(t.lyricsText, "", mode);
    assert.equal(t.lyricsSource, null, mode);
    if (mode !== "wordless") assert.deepEqual([t.singer, t.background, t.language], [null, null, null], mode);
  }
  // wordless keeps the voice choices that still apply, drops the lyrics
  const w = L.setVoiceMode(s, "wordless");
  assert.deepEqual([w.singer, w.background, w.language], ["female", "choir", "hi"]);
  // the request body of an instrumental piece carries none of the voice fields, whatever was typed before
  const body = L.buildCreateBody(L.setVoiceMode(s, "instrumental"));
  assert.equal(body.voice, "instrumental");
  assert.equal(body.lyrics, undefined);
  assert.equal(body.shape, undefined);
});

test("switching lyrics source to 'write' clears the typed words", () => {
  let s = L.setVoiceMode(form(), "sung");
  s = { ...s, lyricsText: "my words" };
  s = L.setLyricsSource(s, "write");
  assert.equal(s.lyricsText, "");
  assert.equal(L.voiceVisibility(s.voice, s.lyricsSource).C17, false);
});

test("sung words need the words (or a smart planner) before Create", () => {
  const s = L.setVoiceMode(form(), "sung");
  assert.equal(L.canCreate(s).ok, false);
  assert.equal(L.canCreate({ ...s, lyricsText: "a b" }).ok, true);
  assert.equal(L.canCreate({ ...s, lyricsSource: "write" }, { writeEnabled: false }).ok, false);
});

test("exact lyrics are sent byte for byte (no trimming, no newline changes)", () => {
  const text = "  पहली पंक्ति \r\n\nदूसरी\t \n";
  const s = { ...L.setVoiceMode(form(), "sung"), lyricsText: text, language: "hi" };
  const body = L.buildCreateBody(s);
  assert.equal(body.lyrics, text);
  assert.equal(body.shape.language, "hi");
});

test("untouched controls stay Auto: only the brief is sent", () => {
  assert.deepEqual(L.buildCreateBody(form({ brief: "  hello  " })), { brief: "hello" });
});

test("chosen controls are mapped to the API", () => {
  let s = form({ length: "120", recipe: "r1_flute_focus", pace: "slow", avoid: " crowded, drums ,, " });
  s = L.starLead(L.toggleInstrument(L.toggleInstrument(s, "tabla"), "tanpura"), "bansuri");
  s = L.toggleFeeling(s, "tender");
  const body = L.buildCreateBody({ ...s, takes: 2, takesTouched: true });
  assert.equal(body.duration, 120);
  assert.equal(body.takes, 2);
  assert.equal(body.recipe, "r1_flute_focus");
  assert.deepEqual(body.shape, { lead: "bansuri", instruments: ["tabla", "tanpura"], feeling: ["tender"], pace: "slow", avoid: ["crowded", "drums"] });
});

test("instrument picker: up to four, star = lead, un-pick drops the lead", () => {
  let s = form();
  for (const id of ["bansuri", "tabla", "tanpura", "santoor"]) s = L.toggleInstrument(s, id);
  s = L.toggleInstrument(s, "sitar");
  assert.equal(s.picked.length, 4);
  assert.ok(s.error);
  s = L.starLead(s, "tabla");
  assert.equal(s.lead, "tabla");
  s = L.toggleInstrument(s, "tabla");
  assert.equal(s.lead, null);
});

test("one fresh idempotency key per call, UUID shaped, with or without crypto.randomUUID", () => {
  const a = L.newIdempotencyKey(), b = L.newIdempotencyKey();
  assert.notEqual(a, b);
  const re = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  assert.match(L.newIdempotencyKey(null), re);
  assert.match(a, re);
});

test("AT-M3-07: progress strip phases queued -> loading model -> take n/N -> checking -> done", () => {
  const job = (phase, extra = {}) => ({ state: "running", phase, progress: { take_index: 2, takes_total: 3 }, ...extra });
  const active = (pv) => pv.steps.find((s) => s.state === "active").label;
  assert.equal(active(L.progressView({ state: "queued", phase: "queued", progress: {} })), "Queued");
  assert.equal(active(L.progressView(job("loading_model"))), "Loading the music model");
  assert.equal(active(L.progressView(job("rendering"))), "Take 2/3");
  assert.equal(L.progressView(job("rendering")).headline, "Making take 2 of 3");
  assert.equal(active(L.progressView(job("checking"))), "Checking the files");
  const done = L.progressView(job("done", { state: "succeeded" }));
  assert.ok(done.steps.every((s) => s.state === "done") && !done.active);
});

test("AT-M3-07: 'mac busy' reason is shown plainly and the job can still be cancelled", () => {
  const pv = L.progressView({ state: "queued", phase: "waiting", reason: "mac_busy", progress: { message: "The video generator is busy." } });
  assert.ok(pv.waiting && pv.canCancel);
  assert.match(pv.headline, /busy/);
  assert.equal(pv.detail, "The video generator is busy.");
});

test("AT-M3-07: a failure shows a human message and a manual Try again, never an automatic one", () => {
  const pv = L.progressView({ state: "failed", phase: "failed", error: "The music engine stopped on take 1.", progress: {} });
  assert.equal(pv.failed, true);
  assert.equal(pv.canRetry, true);
  assert.equal(pv.canCancel, false);
  assert.equal(pv.detail, "The music engine stopped on take 1.");
  assert.equal(L.progressView({ state: "cancelled", phase: "cancelled", progress: {} }).canRetry, true);
});

test("honesty: technical checks are about breakage; 'passed' never says 'sounds good'", () => {
  const ok = L.techCheckSummary({ status: "passed", failures: [], warnings: [], checks: {} });
  assert.equal(ok.headline, "Technical checks passed");
  assert.doesNotMatch(JSON.stringify(ok) + L.CHECKS_DISCLAIMER.replace(/not|nothing/g, ""), /sounds good|sound good|quality score/i);
  assert.match(L.CHECKS_DISCLAIMER, /breakage/);
  assert.match(L.techCheckSummary({ status: "failed", failures: ["duration"], warnings: [], checks: { duration: { value: 4, limit: "10 +/- 0.25 s" } } }).headline, /may be broken/);
  const warn = L.techCheckSummary({ status: "warning", failures: [], warnings: ["silence"], checks: { silence: { value: 0.05, limit: "< 5%" } } });
  assert.equal(warn.details.length, 1);
});

const PLAN = {
  voice_mode: "instrumental", duration_s: 90, takes: 3, recipe_id: "r1_flute_focus",
  lead: { instrument: "bansuri", style: "singing" },
  supports: [{ instrument: "tabla", role: "rhythm", presence: "sparse" }],
  feeling: ["peaceful"], pace: { bucket: "slow", bpm: 74 }, key: "D major", arc: "steady", fullness: "spare",
  voices: { singer: "auto", background: "none", language: "en" }, lyrics: { policy: "none" }, avoid: [],
  provenance: { voice_mode: { source: "suggested", reason: "r" }, lead: { source: "you", reason: "r" }, pace: { source: "recipe", reason: "r" }, fullness: { source: "rule", reason: "r" } },
};

test("AT-M3-04: every plan row that has provenance carries a valid tag and reason; voices rows hidden for instrumental", () => {
  const rows = L.planRows(PLAN);
  assert.ok(!rows.some((r) => r.control === "C13"));
  const withProv = rows.filter((r) => r.prov);
  assert.ok(withProv.length >= 4);
  for (const r of withProv) assert.ok(["you", "suggested", "recipe", "rule"].includes(r.prov.source) && r.prov.reason);
  assert.equal(L.provenanceInfo("you").short, "you");
  const sung = L.planRows({ ...PLAN, voice_mode: "sung", lyrics: { policy: "exact" } });
  assert.ok(sung.some((r) => r.control === "C15") && sung.some((r) => r.control === "C17"));
});

test("AT-M3-04: under the Basic planner no note says 'AI'", () => {
  const card = { is_llm: false, notes: ["Words I understood: flute.", "This is the Basic planner (keyword rules, not an AI). It cannot read stories."] };
  const shown = L.plannerNotes(card);
  assert.deepEqual(shown, ["Words I understood: flute."]);
  assert.equal(L.plannerNotes({ is_llm: true, notes: ["x AI y"] }).length, 1);
});

test("plan rows never contain per-instrument level controls or counts of singers", () => {
  const text = JSON.stringify(L.planRows(PLAN)) + JSON.stringify(L.CHIPS);
  assert.doesNotMatch(text, /volume|fader|louder|quieter|headcount|lock/i);
});

test("lineage: a refine round says new performance from an updated plan, not an edit", () => {
  const s = L.lineageText({ kind: "refine", request_text: "slower" }, "round 1, T2");
  assert.match(s, /new performances from an updated plan, not an edit of round 1, T2/);
  assert.match(L.lineageText({ kind: "another" }, null), /new random seeds/);
});

test("compile report lines name dropped items, conflicts and warnings plainly", () => {
  const lines = L.compileReportLines({ char_count: 500, cap: 512, dropped: [{ kind: "flavour", item: "flavour clause", reason: "over budget" }], conflicts: [{ kind: "x", detail: "instrumental with choir", resolution: "voices dropped" }], warnings: ["w"], unsupported: [], notes: [] });
  assert.deepEqual(lines.map((l) => l.kind), ["info", "dropped", "conflict", "warning"]);
  assert.match(lines[2].text, /voices dropped/);
});

test("formatting helpers", () => {
  assert.equal(L.formatDuration(150), "2:30");
  assert.equal(L.formatBytes(3 * 2 ** 20), "3.0 MiB");
  assert.match(L.describeApiError(0, null), /cannot reach/);
  assert.equal(L.describeApiError(422, { error: { message: "brief must not be blank" } }), "brief must not be blank");
});
