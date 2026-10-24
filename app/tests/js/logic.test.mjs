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

// ---- "What changed": one entry schema {field, from, to, source: chip|you|rule} (review bug 4: it showed "none -> none")
test("formatChange: before and after are read from from/to, never old/new", () => {
  const c = L.formatChange({ field: "fullness", from: "balanced", to: "spare", source: "chip" });
  assert.equal(c.label, "How full");
  assert.equal(c.from, "Balanced");
  assert.equal(c.to, "Spare");
  assert.equal(c.text, "How full: Balanced → Spare");
  assert.equal(c.sourceLabel, "quick change");
  assert.doesNotMatch(c.text, /none|undefined|null/i);
});

test("formatChange: arrays become comma lists, instrument ids use nameOf, null is Auto", () => {
  const nameOf = (id) => ({ tabla: "Tabla", tanpura: "Tanpura", acoustic_guitar: "Acoustic guitar" })[id] || id;
  const a = L.formatChange({ field: "supports", from: ["tabla", "tanpura"], to: ["acoustic_guitar"], source: "you" }, nameOf);
  assert.equal(a.text, "Supporting instruments: Tabla, Tanpura → Acoustic guitar");
  assert.equal(L.formatChange({ field: "supports", from: ["tabla"], to: [], source: "chip" }, nameOf).to, "none");
  const reset = L.formatChange({ field: "key", from: null, to: "D major", source: "rule" });
  assert.equal(reset.text, "Key: Auto → D major");
  assert.equal(reset.sourceLabel, "automatic");
  assert.equal(L.formatChange({ field: "feeling", from: ["peaceful", "tender"], to: ["peaceful"], source: "you" }).from, "peaceful, tender");
  assert.equal(L.formatChange({ field: "lead", from: "piano", to: "bansuri", source: "you" }, nameOf).text, "Lead: piano → bansuri");
});

test("formatChange: field labels and value words for the other fields", () => {
  const f = (field, from, to) => L.formatChange({ field, from, to, source: "you" }).text;
  assert.equal(f("pace", 82, 90), "Pace: 82 BPM → 90 BPM");
  assert.equal(f("lead.style", "simple", "ornate"), "Playing style: simple and clean → ornate, lots of decoration");
  assert.equal(f("voice_mode", "instrumental", "wordless"), "Voice: Instrumental → Wordless voices");
  assert.equal(f("voices.background", "none", "choir"), "Background voices: None → Choir");
  assert.equal(f("voices.singer", "auto", "female"), "Singer: Auto → Female");
  assert.equal(f("duration_s", 150, 90), "Length: 2:30 → 1:30");
  assert.equal(f("arc", "steady", "slow_build"), "Story of the piece: Steady → Slow build");
  assert.equal(f("something_new", "a", "b"), "something new: a → b");
});

test("formatChange: old stored shapes still render sensibly (plain field names, old/chip keys)", () => {
  const plain = L.formatChange("fullness");
  assert.equal(plain.text, "How full changed");
  assert.equal(plain.source, "you");
  const old = L.formatChange({ field: "pace", old: 82, new: 74, chip: "slower" });
  assert.equal(old.text, "Pace: 82 BPM → 74 BPM");
  assert.equal(old.source, "chip");
  assert.deepEqual(L.formatChanges(null), []);
  assert.deepEqual(L.formatChanges([{ field: "key", from: "D major", to: "E minor", source: "you" }]).map((c) => c.text), ["Key: D major → E minor"]);
});

// ---- follow-up 1: effective arrangement, selected take, retry ---------------------------------------------------
const REQUESTED_PLAN = {
  voice_mode: "instrumental", duration_s: 120, takes: 3, recipe_id: "r1_flute_focus",
  lead: { instrument: "choir", style: "singing" }, supports: [{ instrument: "tabla", presence: "soft", role: "rhythm" }, { instrument: "choir", presence: "soft", role: "harmony" }],
  feeling: [], pace: { bucket: "slow", bpm: 80 }, fullness: "sparse", arc: "gentle_rise", avoid: [], key: "D major",
  voices: { singer: "auto", background: "none", language: "en" }, lyrics: { policy: "none" },
  provenance: { lead: { source: "you" } },
};
const ARR_REPORT = { arrangement: {
  requested: { lead: "choir", supports: ["tabla", "choir"], voice_mode: "instrumental", background: "none" },
  effective: { lead: "bansuri", supports: ["tabla"], voice_mode: "instrumental", background: "none" },
  adjustments: [{ field: "lead", requested: "choir", effective: "bansuri", reason: "Choir is voices and Voice is Instrumental, so choir was left out; Bansuri leads instead" },
                { field: "supports", requested: "choir", effective: null, reason: "Voice is Instrumental" }] } };
const NAMES = { choir: "Choir", bansuri: "Bansuri", tabla: "Tabla" };
const nm = (x) => NAMES[x] || x;

test("effective arrangement: the plan table and summary describe the real lead, with the original ask explained", () => {
  const rows = L.planRows(REQUESTED_PLAN, nm, ARR_REPORT);
  const lead = rows.find((r) => r.key === "lead");
  assert.match(lead.value, /^Bansuri/);
  assert.match(lead.adjusted, /You asked for Choir as the lead\. Choir is voices and Voice is Instrumental/);
  assert.match(lead.adjusted, /Bansuri leads instead/);
  assert.equal(lead.prov.source, "you");                                   // provenance of the user's pick is kept
  const sup = rows.find((r) => r.key === "supports");
  assert.doesNotMatch(sup.value, /Choir/);
  assert.match(sup.adjusted, /You asked for Choir as a supporting instrument\. Voice is Instrumental\./);
  const summary = L.summarySentence(REQUESTED_PLAN, nm, ARR_REPORT);
  assert.match(summary, /^Bansuri leads, supported by Tabla\. No voices\./);
});

test("effective arrangement: without a report the stored plan is shown unchanged and the input is never mutated", () => {
  const before = JSON.stringify(REQUESTED_PLAN);
  const rows = L.planRows(REQUESTED_PLAN, nm, null);
  assert.match(rows.find((r) => r.key === "lead").value, /^Choir/);
  assert.equal(rows.find((r) => r.key === "lead").adjusted, null);
  L.planRows(REQUESTED_PLAN, nm, ARR_REPORT);
  assert.equal(JSON.stringify(REQUESTED_PLAN), before);
  assert.deepEqual(L.arrangementNotes({ arrangement: { adjustments: [] } }), []);
});

test("another take sends the selected take; with none selected it sends no base", () => {
  assert.deepEqual(L.anotherBody("TAKE1"), { kind: "another", from_take: "TAKE1" });
  assert.deepEqual(L.anotherBody(null), { kind: "another" });
  assert.deepEqual(L.retryBody("ROUND9"), { kind: "another", from_round: "ROUND9" });
});

test("selection note explains an older take's plan; lineage names the base take and plan version", () => {
  assert.match(L.selectionNote("round 1, T2", 1, 3), /made from plan version 1.*version 3.*will use version 1/);
  assert.doesNotMatch(L.selectionNote("round 3, T1", 3, 3), /will use/);
  assert.equal(L.selectionNote(null, 1, 3), "");
  const s = L.lineageText({ kind: "another" }, "round 1, T2", 1);
  assert.match(s, /Another take of round 1, T2: that take's own plan \(plan version 1\)/);
  assert.match(L.lineageText({ kind: "another" }, null, 4), /same plan \(plan version 4\)/);
});
