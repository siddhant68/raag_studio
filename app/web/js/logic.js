// Pure logic for the Raag Studio UI. No DOM, no fetch, no globals: everything here is unit-tested with `node --test`.
// Wording that describes how much we control (class labels, language badges) is NOT here: it comes from /api/capabilities.

export const VOICE_MODES = ["auto", "instrumental", "wordless", "sung"];
export const LENGTHS = { auto: null, "60": 60, "120": 120, "180": 180 };
export const MAX_INSTRUMENTS = 4; // one lead plus up to three supports (C6)
export const FEELINGS = ["peaceful", "tender", "yearning", "joyful", "epic", "dark"];
export const REASON_TAGS = ["melody", "instrument", "voice", "rhythm", "diction", "too busy", "too plain", "wrong mood"];
export const CHIPS = [
  { id: "less_busy", label: "Less busy", gloss: "fewer things playing" },
  { id: "more_melodic", label: "More melodic", gloss: "a tune you can hum" },
  { id: "slower", label: "Slower", gloss: "a gentler pulse" },
  { id: "livelier", label: "Livelier", gloss: "a quicker pulse" },
  { id: "warmer", label: "Warmer", gloss: "softer, rounder tone" },
  { id: "brighter", label: "Brighter", gloss: "clearer, lighter tone" },
  { id: "different_lead", label: "Different lead", gloss: "another instrument takes the tune" },
  { id: "more_voices", label: "More voices", gloss: "a bit more singing or humming behind" },
  { id: "fewer_voices", label: "Fewer voices", gloss: "a bit less singing or humming" },
];

// Fields that exist only for some voice modes (C13-C17). Anything not visible for the current mode must be empty.
const VOICE_FIELDS = ["singer", "background", "language", "languageOther", "lyricsSource", "lyricsText"];

export function initialFormState() {
  return {
    brief: "", voice: "auto", length: "auto", takes: 3, takesTouched: false, recipe: null,
    lead: null, picked: [], feeling: [], pace: null, fullness: null, arc: null, style: null, avoid: "",
    singer: null, background: null, language: null, languageOther: "", lyricsSource: null, lyricsText: "",
  };
}

/** Which of the voice controls C13-C17 are shown. `lyricsSource` decides whether C17 (the text box) shows. */
export function voiceVisibility(mode, lyricsSource) {
  const voices = mode === "wordless" || mode === "sung";
  const sung = mode === "sung";
  return {
    C13: voices, C14: voices, C15: voices,
    C16: sung, C17: sung && lyricsSource === "exact",
  };
}

/** Switch the voice mode and clear every value that the new mode hides (no hidden conflicting values). */
export function setVoiceMode(state, mode) {
  if (!VOICE_MODES.includes(mode)) throw new Error("unknown voice mode " + mode);
  const next = { ...state, voice: mode };
  const vis = voiceVisibility(mode, mode === "sung" ? "exact" : null);
  if (!vis.C13) next.singer = null;
  if (!vis.C14) next.background = null;
  if (!vis.C15) { next.language = null; next.languageOther = ""; }
  if (!vis.C16) { next.lyricsSource = null; next.lyricsText = ""; }
  if (mode === "sung" && !next.lyricsSource) next.lyricsSource = "exact";
  return next;
}

export function setLyricsSource(state, source) {
  if (state.voice !== "sung") return state;
  const next = { ...state, lyricsSource: source };
  if (source !== "exact") next.lyricsText = ""; // C17 hides, so its value goes too
  return next;
}

/** True when no hidden voice control still holds a value. Used by the tests and as a runtime assertion. */
export function hiddenVoiceValues(state) {
  const vis = voiceVisibility(state.voice, state.lyricsSource);
  const hidden = [];
  if (!vis.C13 && state.singer) hidden.push("singer");
  if (!vis.C14 && state.background) hidden.push("background");
  if (!vis.C15 && (state.language || state.languageOther)) hidden.push("language");
  if (!vis.C16 && state.lyricsSource) hidden.push("lyricsSource");
  if (!vis.C17 && state.lyricsText) hidden.push("lyricsText");
  return hidden;
}

// ---- C6: instruments. Tap = include, star = lead. -------------------------------------------------------------
export function toggleInstrument(state, id) {
  const has = state.picked.includes(id);
  if (has) {
    return { ...state, picked: state.picked.filter((x) => x !== id), lead: state.lead === id ? null : state.lead };
  }
  if (state.picked.length >= MAX_INSTRUMENTS) return { ...state, error: `Pick at most ${MAX_INSTRUMENTS}: one to lead and up to three to support.` };
  return { ...state, picked: [...state.picked, id], error: undefined };
}

export function starLead(state, id) {
  if (state.lead === id) return { ...state, lead: null };
  let picked = state.picked;
  if (!picked.includes(id)) {
    if (picked.length >= MAX_INSTRUMENTS) return { ...state, error: `Pick at most ${MAX_INSTRUMENTS}: one to lead and up to three to support.` };
    picked = [...picked, id];
  }
  return { ...state, picked, lead: id, error: undefined };
}

export function toggleFeeling(state, word) {
  const has = state.feeling.includes(word);
  return { ...state, feeling: has ? state.feeling.filter((w) => w !== word) : [...state.feeling, word] };
}

export function parseAvoid(text) {
  return String(text || "")
    .split(/[,;\n]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.slice(0, 60))
    .slice(0, 10);
}

const LANG_RE = /^[a-z]{2,3}$/;
export function languageCode(state) {
  if (!state.language) return null;
  if (state.language === "other") return LANG_RE.test((state.languageOther || "").trim().toLowerCase()) ? state.languageOther.trim().toLowerCase() : null;
  return state.language;
}

/** {ok, reason}: Create is disabled for a blank brief (and for incomplete sung-words input). */
export function canCreate(state, opts = {}) {
  if (!state.brief || !state.brief.trim()) return { ok: false, reason: "Write a few words about what you feel or imagine." };
  if (state.voice === "sung") {
    if (state.lyricsSource === "write" && !opts.writeEnabled) return { ok: false, reason: "Writing lyrics for you needs the smart planner, which is off. Paste your own words instead." };
    if (state.lyricsSource === "exact" && !state.lyricsText.trim()) return { ok: false, reason: "Paste the words you want sung, or pick another Voice option." };
  }
  if (state.language === "other" && !languageCode(state)) return { ok: false, reason: "Type the two or three letter language code, or pick another language." };
  return { ok: true, reason: "" };
}

/** Request body for POST /api/songs. Only things the person chose are sent; everything else stays Auto. */
export function buildCreateBody(state) {
  const body = { brief: state.brief.trim() };
  if (state.voice !== "auto") body.voice = state.voice;
  const seconds = LENGTHS[state.length];
  if (seconds) body.duration = seconds;
  if (state.takesTouched) body.takes = state.takes; // untouched stays Auto, so the plan does not claim "you set this"
  if (state.recipe) body.recipe = state.recipe;
  if (state.voice === "sung" && state.lyricsSource === "exact" && state.lyricsText.trim()) body.lyrics = state.lyricsText; // sent unchanged
  const shape = {};
  if (state.lead) shape.lead = state.lead;
  const supports = state.picked.filter((x) => x !== state.lead);
  if (supports.length) shape.instruments = supports;
  if (state.feeling.length) shape.feeling = [...state.feeling];
  if (state.pace) shape.pace = state.pace;
  if (state.fullness) shape.fullness = state.fullness;
  if (state.arc) shape.arc = state.arc;
  if (state.style) shape.style = state.style;
  const avoid = parseAvoid(state.avoid);
  if (avoid.length) shape.avoid = avoid;
  if (state.voice === "wordless" || state.voice === "sung") {
    if (state.singer) shape.singer = state.singer;
    if (state.background) shape.background = state.background;
    const lang = languageCode(state);
    if (lang) shape.language = lang;
  }
  if (Object.keys(shape).length) body.shape = shape;
  return body;
}

/** One new UUID per button press (Idempotency-Key). `cryptoLike` is injectable for tests. */
export function newIdempotencyKey(cryptoLike = globalThis.crypto, rand = Math.random) {
  if (cryptoLike && typeof cryptoLike.randomUUID === "function") return cryptoLike.randomUUID();
  const hex = (n) => Array.from({ length: n }, () => Math.floor(rand() * 16).toString(16)).join("");
  return `${hex(8)}-${hex(4)}-4${hex(3)}-${"89ab"[Math.floor(rand() * 4)]}${hex(3)}-${hex(12)}`;
}

// ---- time and text helpers -----------------------------------------------------------------------------------
export function formatDuration(seconds) {
  const s = Math.round(Number(seconds) || 0);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function formatBytes(bytes) {
  const b = Number(bytes) || 0;
  if (b >= 2 ** 30) return (b / 2 ** 30).toFixed(2) + " GiB";
  if (b >= 2 ** 20) return (b / 2 ** 20).toFixed(1) + " MiB";
  if (b >= 2 ** 10) return Math.round(b / 2 ** 10) + " KiB";
  return b + " B";
}

// ---- progress strip -------------------------------------------------------------------------------------------
const STEP_LABELS = ["Queued", "Loading the music model", null, "Checking the files", "Done"];

/**
 * Turn a job (GET /api/jobs/{id} or an SSE `job` event) into the progress strip:
 * queued -> loading model -> take n/N -> checking -> done. `waiting` is true for the mac-busy reason.
 */
export function progressView(job) {
  const p = (job && job.progress) || {};
  const total = p.takes_total || 0;
  const idx = p.take_index || 0;
  const rendering = total ? `Making take ${Math.max(idx, 1)} of ${total}` : "Making the takes";
  let step = 0;
  let headline = "Waiting in line";
  let detail = "";
  let waiting = false;
  switch (job && job.phase) {
    case "waiting":
      step = 0; waiting = true;
      headline = job.reason === "mac_busy" ? "Waiting: this Mac is busy with a video job" : "Waiting for the Mac to be free";
      detail = p.message || "It starts by itself when the other job finishes. Nothing is wrong.";
      break;
    case "starting": step = 0; headline = "Starting"; break;
    case "loading_model": step = 1; headline = "Loading the music model"; detail = "This takes a few seconds the first time."; break;
    case "rendering": step = 2; headline = rendering; break;
    case "retrying": step = 2; headline = "One take failed its breakage check; making a replacement"; break;
    case "checking": step = 3; headline = "Checking the files for breakage"; break;
    case "done": step = 4; headline = "Done"; break;
    case "failed": headline = "That did not work"; break;
    case "cancelled": headline = "Cancelled"; break;
    default: step = 0;
  }
  const labels = [...STEP_LABELS];
  labels[2] = total ? `Take ${Math.max(idx, 1)}/${total}` : "Making takes";
  const failed = job && job.state === "failed";
  const cancelled = job && job.state === "cancelled";
  const active = !!job && (job.state === "queued" || job.state === "running");
  return {
    steps: labels.map((label, i) => ({ label, state: failed || cancelled ? (i < step ? "done" : "todo") : i < step ? "done" : i === step ? (job && job.state === "succeeded" ? "done" : "active") : "todo" })),
    headline: failed ? "That did not work, so no takes were made this time" : cancelled ? "Cancelled" : headline,
    detail: failed ? (job.error || "The render stopped.") : cancelled ? (job.error || "You cancelled this render.") : detail,
    waiting, failed: !!failed, cancelled: !!cancelled, active,
    canCancel: active, canRetry: !!(failed || cancelled),
  };
}

// ---- technical checks vs your verdict --------------------------------------------------------------------------
export const CHECKS_DISCLAIMER = "These checks only catch breakage: silence, clipping, wrong length, a file that will not play. They say nothing about whether the music is good. That is your verdict.";

export function techCheckSummary(tc) {
  if (!tc || !tc.status) return { tone: "unknown", headline: "Technical checks have not run yet", details: [] };
  const details = [...(tc.failures || []).map((f) => describeCheck(tc, f)), ...(tc.warnings || []).map((w) => describeCheck(tc, w))];
  if (tc.status === "passed") return { tone: "ok", headline: "Technical checks passed", details };
  if (tc.status === "warning") return { tone: "warn", headline: "Technical checks passed with a note", details };
  return { tone: "bad", headline: "Technical checks found a problem: this take may be broken", details };
}

function describeCheck(tc, key) {
  const c = (tc.checks || {})[key];
  const names = { silence: "Quiet stretch", duration: "Length", sample_rate: "Sample rate", channels: "Channels", clipping: "Clipping", true_peak: "Peak level", decode: "File decode" };
  const name = names[key] || key;
  if (!c) return name;
  const val = typeof c.value === "number" ? Math.round(c.value * 1000) / 1000 : c.value;
  return `${name}: ${val}${c.limit ? ` (limit ${c.limit})` : ""}`;
}

// ---- the plan view ---------------------------------------------------------------------------------------------
const VOICE_TEXT = { instrumental: "Instrumental: no voices", wordless: "Wordless voices: ooh and aah, no words", sung: "Sung words" };
const STYLE_TEXT = { simple: "simple and clean", singing: "singing, like a voice", ornate: "ornate, lots of decoration" };
const ARC_TEXT = { steady: "Steady", slow_build: "Slow build", quiet_middle_bloom: "Quiet middle, then bloom" };
const FULL_TEXT = { spare: "Spare", balanced: "Balanced", full: "Full" };
const PACE_TEXT = { slow: "Slow", medium: "Medium", lively: "Lively" };
const SINGER_TEXT = { auto: "Auto", male: "Male", female: "Female", duet: "Duet" };
const BG_TEXT = { none: "None", light: "Light harmonies", choir: "Choir", big: "Big choir" };
const LYRICS_TEXT = { none: "No lyrics", write: "Written for you (smart planner)", exact: "Your words, sent unchanged" };
const PROVENANCE = {
  you: { label: "You set this", short: "you" },
  suggested: { label: "Suggested from your words", short: "suggested" },
  recipe: { label: "From the starting sound", short: "recipe" },
  rule: { label: "Rule", short: "rule" },
};
export function provenanceInfo(source) { return PROVENANCE[source] || { label: String(source || "unknown"), short: String(source || "?") }; }

/**
 * Rows for the plan table. `nameOf(id)` turns an instrument id into a display name.
 * Each row: {key, label, control, value, prov: {source, reason} | null}. `control` is the C-id whose honesty label applies.
 */
/**
 * The arrangement the compiler really sent (report.arrangement.effective) laid over the stored plan. The stored plan keeps
 * what was asked for; this copy is what the music model is told. Without a report (or an arrangement) it is the plan.
 */
export function effectivePlan(plan, report) {
  const eff = report && report.arrangement && report.arrangement.effective;
  if (!plan || !eff) return plan;
  const out = JSON.parse(JSON.stringify(plan));
  if (out.lead && eff.lead) out.lead.instrument = eff.lead;
  out.supports = (plan.supports || []).filter((s) => (eff.supports || []).includes(s.instrument)).map((s) => ({ ...s }));
  if (eff.voice_mode) out.voice_mode = eff.voice_mode;
  if (out.voices && eff.background) out.voices = { ...out.voices, background: eff.background };
  return out;
}

/** Plain lines for every place the compiler departed from the plan: "You asked for X. Y." */
export function arrangementNotes(report, nameOf = (x) => x) {
  const adj = (report && report.arrangement && report.arrangement.adjustments) || [];
  return adj.map((a) => {
    const asked = a.field === "lead" ? `${nameOf(a.requested)} as the lead`
      : a.field === "supports" ? `${nameOf(a.requested)} as a supporting instrument`
      : `${BG_TEXT[a.requested] || a.requested} background voices`;
    return { field: a.field, text: `You asked for ${asked}. ${capitalise(String(a.reason))}.` };
  });
}

export function planRows(plan, nameOf = (x) => x, report = null) {
  if (!plan) return [];
  const asked = plan;
  plan = effectivePlan(plan, report);
  const notes = arrangementNotes(report, nameOf);
  const noteFor = (...fields) => {
    const t = notes.filter((n) => fields.includes(n.field)).map((n) => n.text).join(" ");
    return t || null;
  };
  const prov = asked.provenance || {};
  const rows = [];
  const add = (key, label, control, value, provKey = key, adjusted = null) =>
    rows.push({ key, label, control, value, prov: prov[provKey] || null, adjusted });
  add("voice_mode", "Voice", "C2", VOICE_TEXT[plan.voice_mode] || plan.voice_mode);
  add("duration_s", "Length", "C3", `about ${formatDuration(plan.duration_s)} (${plan.duration_s} s)`);
  add("takes", "Versions", "C4", String(plan.takes));
  if (plan.recipe_id) add("recipe_id", "Starting sound", "C5", plan.recipe_id.replace(/^r\d+_/, "").replace(/_/g, " "));
  if (plan.lead) add("lead", "Leads", "C6", `${nameOf(plan.lead.instrument)}, playing style: ${STYLE_TEXT[plan.lead.style] || plan.lead.style}`, "lead", noteFor("lead"));
  add("supports", "Supports", "C6", (plan.supports || []).length ? plan.supports.map((s) => `${nameOf(s.instrument)} (${s.presence}, ${s.role})`).join(", ") : "nothing else", "supports", noteFor("supports"));
  add("feeling", "Feeling", "C7", (plan.feeling || []).join(", ") || "not specified");
  if (plan.pace) add("pace", "Pace", "C8", `${PACE_TEXT[plan.pace.bucket] || plan.pace.bucket}, target ${plan.pace.bpm} beats per minute`);
  add("fullness", "How full", "C9", FULL_TEXT[plan.fullness] || plan.fullness);
  add("arc", "Story of the piece", "C10", ARC_TEXT[plan.arc] || plan.arc);
  if ((plan.avoid || []).length) add("avoid", "Avoid", "C12", plan.avoid.join(", "));
  if (plan.voice_mode !== "instrumental" && plan.voices) {
    add("voices", "Singer", "C13", SINGER_TEXT[plan.voices.singer] || plan.voices.singer, "voices");
    add("voices", "Background voices", "C14", BG_TEXT[plan.voices.background] || plan.voices.background, "voices", noteFor("voices.background"));
    add("voices", "Language", "C15", plan.voices.language, "voices");
  }
  if (plan.lyrics && plan.lyrics.policy !== "none") add("lyrics", "Lyrics", plan.lyrics.policy === "exact" ? "C17" : "C16", LYRICS_TEXT[plan.lyrics.policy] || plan.lyrics.policy);
  add("key", "Key", "C23", `${plan.key} (a target, not a promise)`);
  if (plan.flavour) add("flavour", "Extra flavour", null, plan.flavour);
  return rows;
}

// ---- "What changed" ---------------------------------------------------------------------------------------------
// One entry schema from every backend producer: {field, from, to, source: "chip" | "you" | "rule"}.
const CHANGE_LABEL = {
  voice_mode: "Voice", lyrics: "Lyrics", duration_s: "Length", takes: "Versions", recipe_id: "Starting sound",
  lead: "Lead", "lead.style": "Playing style", supports: "Supporting instruments", feeling: "Feeling", pace: "Pace",
  key: "Key", fullness: "How full", arc: "Story of the piece", avoid: "Avoid", flavour: "Extra flavour",
  "voices.singer": "Singer", "voices.background": "Background voices", "voices.language": "Language",
};
const CHANGE_SOURCE = { chip: "quick change", you: "you", rule: "automatic" };
const CHANGE_VOICE = { instrumental: "Instrumental", wordless: "Wordless voices", sung: "Sung words" };
const CHANGE_WORDS = {
  voice_mode: CHANGE_VOICE, "lead.style": STYLE_TEXT, fullness: FULL_TEXT, arc: ARC_TEXT, "voices.singer": SINGER_TEXT,
  "voices.background": BG_TEXT, lyrics: LYRICS_TEXT,
};
const humanId = (x) => String(x).replace(/_/g, " ");

function changeValue(field, v, nameOf) {
  if (v === null || v === undefined) return "Auto";                    // null = no explicit value = Auto
  if (Array.isArray(v)) {
    if (!v.length) return "none";
    return v.map((x) => (field === "supports" ? nameOf(x) : String(x))).join(", ");
  }
  if (field === "lead") return nameOf(v);
  if (field === "pace" && typeof v === "number") return `${v} BPM`;
  if (field === "duration_s" && typeof v === "number") return formatDuration(v);
  const words = CHANGE_WORDS[field];
  if (words && words[v] !== undefined) return words[v];
  if (field === "recipe_id") return String(v).replace(/^r\d+_/, "").replace(/_/g, " ");
  return String(v);
}

/**
 * One "what changed" entry -> {field, label, from, to, source, sourceLabel, text}. Arrays become comma lists, null is "Auto".
 * Also reads the two older stored shapes (a plain field-name string; {old, new, chip}) so earlier plans do not show "undefined".
 */
export function formatChange(entry, nameOf = humanId) {
  const e = typeof entry === "string" ? { field: entry, legacyOnlyName: true } : (entry || {});
  const field = String(e.field || "");
  const label = CHANGE_LABEL[field] || humanId(field);
  const source = CHANGE_SOURCE[e.source] ? e.source : (e.chip ? "chip" : "you");
  const sourceLabel = CHANGE_SOURCE[source];
  if (e.legacyOnlyName) return { field, label, from: null, to: null, source, sourceLabel, text: `${label} changed` };
  const hasFrom = "from" in e, hasTo = "to" in e;
  const from = changeValue(field, hasFrom ? e.from : e.old, nameOf);
  const to = changeValue(field, hasTo ? e.to : e.new, nameOf);
  return { field, label, from, to, source, sourceLabel, text: `${label}: ${from} → ${to}` };
}

export function formatChanges(changes, nameOf = humanId) {
  return (changes || []).map((c) => formatChange(c, nameOf));
}

export function summarySentence(plan, nameOf = (x) => x, report = null) {
  if (!plan) return "";
  plan = effectivePlan(plan, report);
  const lead = plan.lead ? nameOf(plan.lead.instrument) : "an instrument";
  const sup = (plan.supports || []).map((s) => nameOf(s.instrument));
  const voice = { instrumental: "no voices", wordless: "wordless voices", sung: "sung words" }[plan.voice_mode] || plan.voice_mode;
  const support = sup.length ? `, supported by ${sup.join(", ")}` : "";
  return `${lead} leads${support}. ${capitalise(voice)}. About ${formatDuration(plan.duration_s)}.`;
}

function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : s; }

/** Compile report -> plain lines. Nothing hidden: dropped items, conflicts, warnings, unsupported words. */
export function compileReportLines(report) {
  if (!report) return [];
  const lines = [];
  if (report.char_count != null) lines.push({ kind: "info", text: `Prompt length: ${report.char_count} of ${report.cap || 512} characters.` });
  for (const d of report.dropped || []) lines.push({ kind: "dropped", text: `Left out to fit: ${d.item || d.kind}${d.reason ? " (" + d.reason + ")" : ""}` });
  for (const c of report.conflicts || []) lines.push({ kind: "conflict", text: `Conflict: ${c.detail || c.kind}. ${c.resolution ? "What I did: " + c.resolution : ""}`.trim() });
  for (const w of report.warnings || []) lines.push({ kind: "warning", text: typeof w === "string" ? w : (w.message || JSON.stringify(w)) });
  for (const u of report.unsupported || []) lines.push({ kind: "unsupported", text: typeof u === "string" ? u : (u.message || u.item || JSON.stringify(u)) });
  for (const n of report.notes || []) lines.push({ kind: "note", text: typeof n === "string" ? n : (n.message || n.detail || JSON.stringify(n)) });
  return lines;
}

/**
 * Notes from the planner worth showing. Under a non-LLM planner, drop any line that uses the word "AI":
 * the Basic planner is keyword rules, the badge says so, and nothing in the UI should dress it up.
 */
export function plannerNotes(card) {
  const notes = (card && card.notes) || [];
  if (card && card.is_llm) return notes;
  return notes.filter((n) => !/\bAI\b/.test(n));
}

// ---- lineage ----------------------------------------------------------------------------------------------------
/** Plain sentence describing where a round came from. `parentLabel` like "round 1, T2" or null. */
export function lineageText(round, parentLabel, planRev = null) {
  switch (round.kind) {
    case "create": return "First round: made from your brief.";
    case "another": {
      const rev = planRev ? ` (plan version ${planRev})` : "";
      return parentLabel
        ? `Another take of ${parentLabel}: that take's own plan${rev} with new random seeds. New performances, not edits of ${parentLabel}.`
        : `Another take: the same plan${rev} with new random seeds.`;
    }
    case "refine": {
      const asked = round.request_text ? ` You asked: "${round.request_text}".` : "";
      const from = parentLabel ? ` These are new performances from an updated plan, not an edit of ${parentLabel}.` : " These are new performances from an updated plan, not edits.";
      return `Changed plan.${asked}${from}`;
    }
    default: return `Round (${round.kind}).`;
  }
}

/** Label every take "round R, Tn" so T-numbers stay unambiguous across rounds. */
export function takeLabels(rounds, takes) {
  const roundNo = new Map(rounds.map((r, i) => [r.id, i + 1]));
  const out = new Map();
  for (const t of takes) out.set(t.id, `round ${roundNo.get(t.round_id) || "?"}, ${t.label}`);
  return out;
}

export function describeApiError(status, body) {
  const e = body && body.error;
  if (e && e.message) return e.message;
  if (status === 0) return "I cannot reach the Raag Studio server. Is it running? (scripts/start.sh)";
  return `The server answered with an error (${status}).`;
}

// ---- which plan a new round starts from -------------------------------------------------------------------------
/** "Another take" starts from the take you have selected (its own plan); with none selected the server uses the newest plan. */
export function anotherBody(selectedTakeId) {
  return selectedTakeId ? { kind: "another", from_take: selectedTakeId } : { kind: "another" };
}

/** "Try again" repeats the failed round's own plan, never whatever plan happens to be newest. */
export function retryBody(failedRoundId) {
  return { kind: "another", from_round: failedRoundId };
}

/** One sentence under "What next?": which take the next changes start from and which plan that is. */
export function selectionNote(label, takePlanRev, latestRev) {
  if (!label) return "";
  const rev = takePlanRev ? `, which was made from plan version ${takePlanRev}` : "";
  const older = takePlanRev && latestRev && takePlanRev !== latestRev
    ? ` The plan shown above is version ${latestRev}, so “Another take” will use version ${takePlanRev} (this take's plan), not the newest.`
    : "";
  return `Changes below start from: ${label}${rev} (the one you last played or marked).${older}`;
}
