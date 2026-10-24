// The song view: plan, progress strip, player, take cards (T1..Tn) with lineage, verdict, export, change requests.
import { api, ApiProblem } from "./api.js";
import { labelFor } from "./caps.js";
import { $, $$, h, render, clear, show, announce } from "./dom.js";
import {
  CHECKS_DISCLAIMER, CHIPS, REASON_TAGS, compileReportLines, formatChanges, formatDuration, lineageText, newIdempotencyKey, plannerNotes,
  planRows, progressView, provenanceInfo, summarySentence, takeLabels, techCheckSummary,
} from "./logic.js";
import { store, nameOf, plannerIsSmart } from "./store.js";

const KEYS = ["D major", "D minor", "G major", "G minor", "A major", "A minor", "C major", "C minor", "E minor", "F major", "B minor", "E major"];

const S = {
  id: null, detail: null, jobs: {}, selectedTakeId: null, playingTakeId: null, chips: new Set(),
  patchReports: {}, tick: 0, lastStepLabel: "", requestedStart: false,
};

// ------------------------------------------------------------------------------------------------- setup
export function init() {
  render($("#change-chips"), ...CHIPS.map((c) => h("button", { type: "button", class: "chip", "aria-pressed": "false", "data-chip": c.id, title: c.gloss }, c.label, h("small", {}, c.gloss))));
  $("#change-chips").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const id = b.dataset.chip;
    if (S.chips.has(id)) S.chips.delete(id); else S.chips.add(id);
    b.setAttribute("aria-pressed", String(S.chips.has(id)));
    paintAfter();
  });
  $("#change-text").addEventListener("input", paintAfter);
  $("#btn-refine").addEventListener("click", refine);
  $("#btn-another").addEventListener("click", () => startRound({ kind: "another" }, $("#btn-another")));
  $("#btn-cancel").addEventListener("click", cancelJob);
  $("#btn-retry").addEventListener("click", () => startRound({ kind: "another" }, $("#btn-retry")));
  $("#btn-apply-details").addEventListener("click", applyDetails);
  render($("#keyscale"), h("option", { value: "" }, "Keep the plan’s key"), ...KEYS.map((k) => h("option", { value: k }, k)));

  const player = $("#player");
  player.addEventListener("play", paintPlayState);
  player.addEventListener("pause", paintPlayState);
  player.addEventListener("ended", paintPlayState);
  player.addEventListener("error", () => {
    $("#now-playing").textContent = "I could not play this take. If you cleaned up old audio, the full-quality file may be gone; the preview should still be there.";
  });
  setInterval(pollTick, 2000);
}

export async function enter(songId) {
  if (S.id !== songId) {
    S.id = songId; S.detail = null; S.jobs = {}; S.selectedTakeId = null; S.playingTakeId = null; S.chips = new Set();
    $("#player").removeAttribute("src");
    render($("#rounds"));
    for (const id of ["progress-panel", "plan-panel", "player-panel", "after-panel", "details-drawer"]) $("#" + id).hidden = true;
    $("#h-song").textContent = "Your song";
    $("#song-brief").textContent = "";
  }
  $("#change-help").textContent = plannerIsSmart()
    ? "Describe the change in plain words."
    : "The Basic planner only understands the quick-change buttons above and simple words like slower, less busy or warmer. It does not read sentences or stories. If it cannot use your words it will tell you instead of guessing.";
  await load();
}

async function load() {
  if (!S.id) return;
  try {
    S.detail = await api(`/api/songs/${S.id}`);
  } catch (err) {
    $("#h-song").textContent = "Song not found";
    $("#song-brief").textContent = err.message;
    return;
  }
  for (const r of S.detail.rounds) S.jobs[r.job.id] = r.job;
  renderAll();
}

// ------------------------------------------------------------------------------------------------- events
export function onJob(job) {
  if (job.song_id !== S.id) return;
  applyJob(job);
}

export function onTakesReady(ev) {
  if (!S.detail) return;
  if ((ev.takes || []).some((t) => t.song_id === S.id)) { load(); announce("Your takes are ready."); }
}

export function onFeedback(ev) {
  if (ev.song_id === S.id && S.detail) {
    const t = S.detail.takes.find((x) => x.id === ev.take_id);
    if (t && (t.favourite !== ev.favourite || t.rating !== ev.rating)) load();
  }
}

function applyJob(job) {
  const before = S.jobs[job.id];
  S.jobs[job.id] = job;
  if (S.detail) {
    const r = S.detail.rounds.find((x) => x.job.id === job.id);
    if (r) r.job = job;
  }
  paintProgress();
  const terminal = ["succeeded", "failed", "cancelled"].includes(job.state);
  if (terminal && (!before || before.state !== job.state)) load();
  paintAfter();
}

function latestJob() {
  if (!S.detail || !S.detail.rounds.length) return null;
  return S.jobs[S.detail.rounds[S.detail.rounds.length - 1].job.id];
}

function jobIsActive(job) { return !!job && (job.state === "queued" || job.state === "running"); }

async function pollTick() {
  const job = latestJob();
  if (!jobIsActive(job) || $("#view-song").hidden) return;
  S.tick += 1;
  const live = store.events && store.events.status() === "live";
  if (!live || S.tick % 5 === 0) { // polling fallback when the live stream is down; a slow safety poll otherwise
    try { applyJob(await api(`/api/jobs/${job.id}`)); } catch (err) { /* keep trying */ }
  }
}

// ------------------------------------------------------------------------------------------------- render
function renderAll() {
  const d = S.detail;
  $("#h-song").textContent = d.song.title;
  $("#song-brief").textContent = `“${d.song.brief}”`;
  document.title = `${d.song.title} · Raag Studio`;

  const plan = d.plans[d.plans.length - 1];
  show($("#plan-panel"), !!plan);
  if (plan) renderPlan($("#plan-body"), plan, reportForPlan(plan), true);

  const takes = d.takes;
  show($("#player-panel"), takes.length > 0);
  show($("#after-panel"), takes.length > 0);
  show($("#details-drawer"), true);
  if (takes.length && !takes.some((t) => t.id === S.selectedTakeId)) {
    const lastRound = [...d.rounds].reverse().find((r) => r.take_ids.length);
    S.selectedTakeId = lastRound ? lastRound.take_ids[0] : takes[0].id;
  }
  renderRounds();
  paintProgress();
  paintAfter();
  paintSelection();
}

function reportForPlan(planRec) {
  const round = [...S.detail.rounds].reverse().find((r) => r.plan_id === planRec.id);
  if (round) return round.request.compile_report;
  return S.patchReports[planRec.id] || null;
}

// ---- plan view
function renderPlan(container, planRec, report, isTop) {
  const card = planRec.card || {};
  const plan = planRec.plan;
  const status = card.planner_status;
  const kids = [];
  kids.push(h("div", { class: "plan-meta" },
    h("span", { class: "badge badge-planner", title: "Who made this plan" }, card.provider_label || "Planner"),
    h("span", { class: "help" }, isTop ? `Plan version ${planRec.rev}, used for the next takes` : `Plan version ${planRec.rev}`),
    card.is_llm === false && card.provider === "basic" ? h("span", { class: "help" }, "Keyword rules on this computer. It reads simple words, not stories.") : null));
  if (status && status.fallback) {
    kids.push(h("div", { class: "banner banner-warn", role: "note" }, h("b", {}, "Fallback: "), status.banner || "The smart planner did not work, so the Basic planner made this plan.",
      status.reason ? h("span", { class: "help" }, ` Reason: ${status.reason}`) : null));
  }
  kids.push(h("p", { class: "summary-line" }, summarySentence(plan, nameOf)));
  const rows = planRows(plan, nameOf);
  kids.push(h("table", { class: "plan-table" }, h("tbody", {}, rows.map((row) => {
    const pi = row.prov ? provenanceInfo(row.prov.source) : null;
    return h("tr", {},
      h("th", { scope: "row" }, row.label, " ", row.control ? h("span", { class: "cap-slot" }, labelFor(row.control)) : null),
      h("td", {}, row.value,
        pi ? h("span", { class: "why" }, h("span", { class: `tag tag-${row.prov.source}` }, pi.label), row.prov.reason || "") : null));
  }))));
  const notes = plannerNotes(card);
  if (notes.length) kids.push(h("ul", { class: "report" }, notes.map((n) => h("li", { class: "note" }, n))));
  const extra = [...(card.unsupported || []).map((u) => u.message || JSON.stringify(u)), ...(card.needs_user_input || [])];
  if (extra.length) kids.push(h("ul", { class: "report" }, extra.map((m) => h("li", { class: "unsupported" }, m))));
  if (card.changes && card.changes.length) {
    kids.push(h("p", { class: "help" }, "What changed in this plan:"));
    kids.push(h("ul", { class: "report" }, formatChanges(card.changes, nameOf).map((c) => h("li", { class: "note" }, c.text, h("span", { class: "help" }, ` (${c.sourceLabel})`)))));
  }
  const lines = compileReportLines(report);
  kids.push(h("h3", {}, "What was sent to the music model"));
  if (lines.length) kids.push(h("ul", { class: "report" }, lines.map((l) => h("li", { class: l.kind }, l.text))));
  else kids.push(h("p", { class: "help" }, "The prompt check runs when the next takes are made."));
  render(container, ...kids);
}

// ---- progress strip
function paintProgress() {
  const job = latestJob();
  const pv = job ? progressView(job) : null;
  const panel = $("#progress-panel");
  const showIt = !!pv && (pv.active || pv.failed || pv.cancelled);
  show(panel, showIt);
  if (!showIt) return;
  render($("#progress-steps"), ...pv.steps.map((s) => h("li", { "data-state": s.state, "aria-current": s.state === "active" ? "step" : null }, s.label)));
  $("#progress-headline").textContent = pv.headline;
  $("#progress-detail").textContent = pv.detail;
  show($("#btn-cancel"), pv.canCancel);
  show($("#btn-retry"), pv.canRetry);
  if (pv.headline !== S.lastStepLabel) { S.lastStepLabel = pv.headline; announce(pv.headline); }
}

async function cancelJob() {
  const job = latestJob();
  if (!job) return;
  const btn = $("#btn-cancel");
  btn.disabled = true;
  try { applyJob(await api(`/api/jobs/${job.id}/cancel`, { method: "POST" })); }
  catch (err) { $("#progress-detail").textContent = err.message; await load(); }
  finally { btn.disabled = false; }
}

// ---- rounds and take cards
function renderRounds() {
  const d = S.detail;
  const labels = takeLabels(d.rounds, d.takes);
  const box = $("#rounds");
  clear(box);
  const tplRound = $("#tpl-round");
  const tplTake = $("#tpl-take");
  const ordered = [...d.rounds].map((r, i) => ({ r, n: i + 1 })).reverse();
  for (const { r, n } of ordered) {
    const frag = tplRound.content.cloneNode(true);
    const root = frag.querySelector(".round");
    const takes = d.takes.filter((t) => t.round_id === r.id);
    frag.querySelector(".round-title").textContent = `Round ${n}`;
    const parent = r.parent_take_id ? labels.get(r.parent_take_id) : null;
    frag.querySelector(".round-lineage").textContent = lineageText(r, parent);
    const holder = frag.querySelector(".takes");
    const job = S.jobs[r.job.id] || r.job;
    if (!takes.length) {
      if (job.state === "failed" || job.state === "cancelled") holder.append(h("div", { class: "banner banner-error" }, job.error || (job.state === "cancelled" ? "Cancelled." : "This round failed.")));
      else holder.append(h("p", { class: "help" }, "Still being made. The takes will appear here."));
    }
    for (const t of takes) holder.append(buildTake(tplTake, t, r));
    const planRec = d.plans.find((p) => p.id === r.plan_id);
    const details = frag.querySelector(".round-plan");
    details.addEventListener("toggle", () => {
      if (!details.open || details.dataset.built) return;
      details.dataset.built = "1";
      const body = details.querySelector(".round-plan-body");
      const planBox = h("div", {});
      if (planRec) renderPlan(planBox, planRec, r.request.compile_report, false);
      body.append(planBox, requestBox(r));
    });
    box.append(frag);
  }
}

function requestBox(round) {
  const req = round.request;
  return h("div", {},
    h("h3", {}, "Exact request"),
    h("p", { class: "help" }, `Seeds: ${req.seeds.join(", ")}. Request fingerprint (sha256): ${req.sha256.slice(0, 16)}…`),
    h("p", { class: "help" }, "The sentence sent to the music model:"),
    h("pre", { class: "request-box" }, req.caption),
    h("details", {}, h("summary", { "data-chrome": "request-json" }, "Everything sent (JSON)"), h("pre", { class: "request-box" }, JSON.stringify(req.engine_request, null, 2))));
}

const FACT_LABELS = {
  silence_fraction: ["Quiet stretch", (v) => `${(v * 100).toFixed(1)}% of the take`],
  true_peak_dbtp: ["Loudest peak", (v) => `${v} dBTP`],
  integrated_lufs: ["Overall loudness", (v) => `${v} LUFS`],
  clipped_fraction: ["Clipped samples", (v) => `${(v * 100).toFixed(3)}%`],
};

function buildTake(tpl, take, round) {
  const frag = tpl.content.cloneNode(true);
  const el = frag.querySelector(".take");
  el.dataset.takeId = take.id;
  el.querySelector(".take-title").textContent = take.label;
  el.querySelector(".take-meta").textContent = `${formatDuration(take.duration_s)} · seed ${take.seed}`;
  if (take.engine === "fake") { el.classList.add("is-fake"); el.querySelector(".tag-fake").hidden = false; }
  if (take.retry_of) el.querySelector(".tag-retry").hidden = false;

  const play = el.querySelector(".btn-play");
  play.addEventListener("click", () => togglePlay(take));

  // Technical checks: about breakage only, kept apart from "Your verdict".
  const cs = techCheckSummary(take.technical_checks);
  const head = el.querySelector(".checks-headline");
  head.textContent = cs.headline;
  head.classList.add(cs.tone === "ok" ? "ok" : cs.tone === "warn" ? "warn" : cs.tone === "bad" ? "bad" : "unknown");
  render(el.querySelector(".checks-list"), ...cs.details.map((d) => h("li", {}, d)));
  el.querySelector(".checks-disclaimer").textContent = CHECKS_DISCLAIMER;
  const facts = (take.technical_checks && take.technical_checks.facts) || {};
  render(el.querySelector(".facts"), ...Object.entries(facts).flatMap(([k, v]) => {
    const f = FACT_LABELS[k];
    return v == null ? [] : [h("dt", {}, f ? f[0] : k), h("dd", {}, f ? f[1](v) : String(v))];
  }));

  // Verdict: yours alone.
  const verdict = el.querySelector(".verdict");
  const radios = $$('input[name="rating"]', verdict);
  radios.forEach((r) => { r.name = `rating-${take.id}`; r.addEventListener("change", () => sendFeedback(take, el, { rating: r.value })); });
  el.querySelector(".heart").addEventListener("click", () => sendFeedback(take, el, { favourite: !currentTake(take.id).favourite }));
  render(el.querySelector(".reasons"), ...REASON_TAGS.map((tag) => h("button", { type: "button", class: "chip", "aria-pressed": "false", "data-tag": tag }, tag)));
  el.querySelector(".reasons").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const cur = new Set(currentTake(take.id).tags || []);
    if (cur.has(b.dataset.tag)) cur.delete(b.dataset.tag); else cur.add(b.dataset.tag);
    sendFeedback(take, el, { tags: [...cur] });
  });
  paintVerdict(el, take);

  // Export (C21)
  const result = el.querySelector(".export-result");
  for (const btn of $$("[data-act]", el)) btn.addEventListener("click", () => exportTake(take, btn.dataset.act, el, result));
  for (const ex of S.detail.exports.filter((x) => x.take_id === take.id)) result.append(exportLink(ex));
  // fill the honesty label from the registry (cloned nodes are not in the document yet)
  for (const slot of $$("[data-cap-for]", el)) { clear(slot); labelFor(slot.getAttribute("data-cap-for")).forEach((p) => slot.append(p)); }
  if (take.id === S.playingTakeId) el.classList.add("is-playing");
  return frag;
}

function currentTake(id) { return S.detail.takes.find((t) => t.id === id); }

function paintVerdict(el, take) {
  const heart = el.querySelector(".heart");
  heart.setAttribute("aria-pressed", String(!!take.favourite));
  heart.querySelector(".heart-icon").textContent = take.favourite ? "♥" : "♡";
  heart.querySelector(".heart-text").textContent = take.favourite ? "Favourite (tap to undo)" : "Favourite";
  $$('input[name^="rating-"]', el).forEach((r) => { r.checked = r.value === take.rating; });
  $$("[data-tag]", el).forEach((b) => b.setAttribute("aria-pressed", String((take.tags || []).includes(b.dataset.tag))));
}

async function sendFeedback(take, el, body) {
  let err = el.querySelector(".verdict-error");
  if (!err) { err = h("p", { class: "help warn verdict-error", role: "alert", hidden: true }); el.querySelector(".verdict").append(err); }
  err.hidden = true;
  try {
    const view = await api(`/api/takes/${take.id}/feedback`, { method: "POST", body });
    const i = S.detail.takes.findIndex((t) => t.id === take.id);
    S.detail.takes[i] = view;
    paintVerdict(el, view);
    S.selectedTakeId = take.id;
    paintSelection();
    if ("favourite" in body) announce(view.favourite ? "Marked as a favourite." : "Favourite removed.");
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
    paintVerdict(el, currentTake(take.id)); // snap back to what the server has
  }
}

// ---- player
function togglePlay(take) {
  const player = $("#player");
  if (S.playingTakeId === take.id && !player.paused) { player.pause(); return; }
  if (player.getAttribute("src") !== take.audio_url) player.setAttribute("src", take.audio_url);
  S.playingTakeId = take.id;
  S.selectedTakeId = take.id;
  const label = takeLabels(S.detail.rounds, S.detail.takes).get(take.id);
  $("#now-playing").textContent = `Now playing: ${label}${take.engine === "fake" ? " (TEST AUDIO, not a real render)" : ""}`;
  player.play().catch(() => { /* the error event explains */ });
  paintSelection();
  paintPlayState();
}

function paintPlayState() {
  const player = $("#player");
  for (const card of $$(".take")) {
    const mine = card.dataset.takeId === S.playingTakeId;
    card.classList.toggle("is-playing", mine);
    const b = card.querySelector(".btn-play");
    b.textContent = mine && !player.paused && !player.ended ? "Pause" : "Play";
  }
}

function paintSelection() {
  if (!S.detail) return;
  const labels = takeLabels(S.detail.rounds, S.detail.takes);
  const t = S.detail.takes.find((x) => x.id === S.selectedTakeId);
  $("#selected-take").textContent = t ? `Changes below start from: ${labels.get(t.id)} (the one you last played or marked).` : "";
  $("#seed-readout").textContent = t ? `${labels.get(t.id)}: seed ${t.seed}` : "Pick a take to see its seed.";
  paintPlayState();
}

// ---- export
async function exportTake(take, fmtName, el, result) {
  const buttons = $$("[data-act]", el);
  buttons.forEach((b) => { b.disabled = true; });
  const fade = Math.min(8, Math.max(0, Number($("#end-fade").value) || 0));
  result.textContent = `Making the ${fmtName.toUpperCase()}. Loudness is evened out first, so this takes a few seconds.`;
  try {
    const ex = await api(`/api/takes/${take.id}/exports`, { method: "POST", body: { format: fmtName, end_fade_s: fade } });
    S.detail.exports.push(ex);
    clear(result);
    result.append(exportLink(ex));
    announce("Your file is ready.");
  } catch (err) {
    result.textContent = err.message;
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
  }
}

function exportLink(ex) {
  const out = ex.loudness && ex.loudness.output;
  return h("div", {},
    h("a", { href: ex.url, download: ex.filename || "" }, `Download ${ex.filename || ex.format.toUpperCase()}`),
    out ? h("span", { class: "help" }, ` (${ex.format.toUpperCase()}, loudness ${out.integrated_lufs} LUFS, peak ${out.true_peak_dbtp} dBTP${ex.fade_out_s ? `, ${ex.fade_out_s} s end fade` : ""})`) : null,
    ex.notice ? h("span", { class: "tag tag-fake" }, ex.notice) : null);
}

// ---- after listening
function paintAfter() {
  const active = jobIsActive(latestJob());
  const text = $("#change-text").value.trim();
  $("#btn-refine").disabled = active || !(S.chips.size || text);
  $("#btn-another").disabled = active;
  $("#btn-apply-details").disabled = false;
}

async function startRound(body, btn) {
  if (!S.detail) return;
  const plan = S.detail.plans[S.detail.plans.length - 1].plan;
  btn.disabled = true;
  try {
    await api(`/api/songs/${S.id}/rounds`, { method: "POST", body: { takes: plan.takes, ...body }, headers: { "Idempotency-Key": newIdempotencyKey() } });
    await load();
    announce("Making new takes.");
  } catch (err) {
    $("#progress-panel").hidden = false;
    $("#progress-headline").textContent = "That did not start";
    $("#progress-detail").textContent = err.message;
  } finally {
    btn.disabled = false;
    paintAfter();
  }
}

async function refine() {
  const err = $("#change-error");
  err.hidden = true;
  const body = { kind: "refine" };
  if (S.chips.size) body.chips = [...S.chips];
  const text = $("#change-text").value.trim();
  if (text) body.request_text = text;
  if (S.selectedTakeId) body.from_take = S.selectedTakeId;
  const btn = $("#btn-refine");
  const plan = S.detail.plans[S.detail.plans.length - 1].plan;
  btn.disabled = true;
  try {
    await api(`/api/songs/${S.id}/rounds`, { method: "POST", body: { takes: plan.takes, ...body }, headers: { "Idempotency-Key": newIdempotencyKey() } });
    S.chips.clear();
    $$("#change-chips [aria-pressed]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    $("#change-text").value = "";
    await load();
    announce("Making new versions from the updated plan.");
  } catch (e) {
    const extra = e instanceof ApiProblem && e.body && e.body.error && e.body.error.unsupported ? e.body.error.unsupported.map((u) => u.message).filter(Boolean).join(" ") : "";
    err.textContent = [e.message, extra].filter(Boolean).join(" ");
    err.hidden = false;
  } finally {
    paintAfter();
  }
}

async function applyDetails() {
  const err = $("#details-error");
  err.hidden = true;
  const body = {};
  const bpm = $("#bpm").value.trim();
  if (bpm) {
    const n = Number(bpm);
    if (!Number.isInteger(n) || n < 60 || n > 140) { err.textContent = "Pace must be a whole number from 60 to 140."; err.hidden = false; return; }
    body.bpm = n;
  }
  if ($("#keyscale").value) body.key = $("#keyscale").value;
  if (!Object.keys(body).length) { err.textContent = "Choose a pace or a key first."; err.hidden = false; return; }
  try {
    const r = await api(`/api/songs/${S.id}/controls`, { method: "PATCH", body });
    if (r.compile_report) S.patchReports[r.plan_id] = r.compile_report;
    await load();
    announce("Saved. The next takes will use these.");
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
}
