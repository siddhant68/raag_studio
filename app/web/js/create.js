// The Create screen (C1-C17). All rules about what shows and what gets cleared live in logic.js.
import { api } from "./api.js";
import { backgroundOptions, languageBadge, languageOptions } from "./caps.js";
import { $, $$, h, render, show, announce } from "./dom.js";
import {
  FEELINGS, buildCreateBody, canCreate, formatDuration, initialFormState, newIdempotencyKey, setLyricsSource,
  setVoiceMode, starLead, toggleFeeling, toggleInstrument, voiceVisibility, hiddenVoiceValues,
} from "./logic.js";
import { store, nameOf } from "./store.js";

let state = initialFormState();
let recipes = [];
let busy = false;

export async function init() {
  try {
    const r = await api("/api/recipes");
    recipes = r.recipes;
  } catch (err) {
    recipes = [];
  }
  buildRecipeCards();
  buildInstrumentChips();
  buildFeelingChips();
  buildVoiceSelects();
  wire();
  paint();
}

export function enter() {
  paint();
}

export function currentState() { return state; }

// ------------------------------------------------------------------------------------------ builders
function buildRecipeCards() {
  const box = $("#recipe-cards");
  const cards = [
    h("label", { class: "choice" }, h("input", { type: "radio", name: "recipe", value: "", checked: true }),
      h("span", {}, h("b", {}, "None"), h("small", {}, "Start from my words only"))),
  ];
  for (const r of recipes) {
    const bits = [store.instruments.length ? nameOf(r.lead) : r.lead, r.voice_mode === "instrumental" ? "no voices" : r.voice_mode === "wordless" ? "wordless voices" : "sung words", `about ${formatDuration(r.duration_s)}`];
    cards.push(h("label", { class: "choice" },
      h("input", { type: "radio", name: "recipe", value: r.id }),
      h("span", {}, h("b", {}, r.name), h("small", {}, bits.join(" · ")),
        r.experimental ? h("span", { class: "recipe-flag" }, "experimental") : null)));
  }
  render(box, ...cards);
}

function buildInstrumentChips() {
  const box = $("#instrument-chips");
  render(box, ...store.instruments.map((i) => h("span", { class: "chip-pair", "data-instrument": i.id },
    h("button", { type: "button", "aria-pressed": "false", class: "pick", title: i.validated ? "" : "Plausible but untested: no recipe has used it" },
      i.name, i.validated ? "" : h("small", {}, " (untested)")),
    h("button", { type: "button", "aria-pressed": "false", class: "star", "aria-label": `Make ${i.name} the lead`, title: "Make this the lead" }, "★"))));
}

function buildFeelingChips() {
  render($("#feeling-chips"), ...FEELINGS.map((w) => h("button", { type: "button", class: "chip", "aria-pressed": "false", "data-feeling": w }, w)));
}

function buildVoiceSelects() {
  const bg = $("#background");
  render(bg, h("option", { value: "" }, "Auto"), ...backgroundOptions().map((o) => h("option", { value: o.code }, o.badge ? `${o.label} (${o.badge})` : o.label)));
  const lang = $("#language");
  render(lang, h("option", { value: "" }, "Auto"), ...languageOptions().map((o) => h("option", { value: o.code }, `${o.label} (${o.badge})`)));
}

// ------------------------------------------------------------------------------------------ events
function wire() {
  const form = $("#create-form");
  $("#brief").addEventListener("input", (e) => { state.brief = e.target.value; paint(); });
  $$('input[name="voice"]').forEach((r) => r.addEventListener("change", () => { state = setVoiceMode(state, r.value); paint(); }));
  $("#length").addEventListener("change", (e) => { state.length = e.target.value; });
  $$('input[name="takes"]').forEach((r) => r.addEventListener("change", () => { state.takes = Number(r.value); state.takesTouched = true; }));
  $("#recipe-cards").addEventListener("change", (e) => { if (e.target.name === "recipe") { state.recipe = e.target.value || null; paintRecipeNote(); } });
  for (const name of ["pace", "fullness", "arc", "style"]) {
    $$(`input[name="${name}"]`).forEach((r) => r.addEventListener("change", () => { state[name] = r.value || null; }));
  }
  $("#avoid").addEventListener("input", (e) => { state.avoid = e.target.value; });
  $("#singer").addEventListener("change", (e) => { state.singer = e.target.value || null; });
  $("#background").addEventListener("change", (e) => { state.background = e.target.value || null; });
  $("#language").addEventListener("change", (e) => { state.language = e.target.value || null; paint(); });
  $("#language-other").addEventListener("input", (e) => { state.languageOther = e.target.value; paint(); });
  $$('input[name="lyrics-source"]').forEach((r) => r.addEventListener("change", () => { state = setLyricsSource(state, r.value); paint(); }));
  $("#lyrics-text").addEventListener("input", (e) => { state.lyricsText = e.target.value; paint(); });

  $("#instrument-chips").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    const id = btn.closest("[data-instrument]").dataset.instrument;
    state = btn.classList.contains("star") ? starLead(state, id) : toggleInstrument(state, id);
    paint();
  });
  $("#feeling-chips").addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (btn) { state = toggleFeeling(state, btn.dataset.feeling); paint(); }
  });

  form.addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  $("#btn-create-retry").addEventListener("click", () => submit());
}

// ------------------------------------------------------------------------------------------ painting
function writeEnabled() {
  return !!(store.planner && store.planner.write_for_me && store.planner.write_for_me.enabled);
}

function paint() {
  const vis = voiceVisibility(state.voice, state.lyricsSource);
  show($("#field-singer"), vis.C13);
  show($("#field-background"), vis.C14);
  show($("#field-language"), vis.C15);
  show($("#field-lyrics-source"), vis.C16);
  show($("#field-lyrics-text"), vis.C17);
  // Hidden controls give up their values on screen too, not just in memory.
  if (!vis.C13) $("#singer").value = "";
  if (!vis.C14) $("#background").value = "";
  if (!vis.C15) { $("#language").value = ""; $("#language-other").value = ""; }
  if (!vis.C17) $("#lyrics-text").value = "";
  if (hiddenVoiceValues(state).length) console.error("hidden voice values remained: " + hiddenVoiceValues(state).join(", "));

  const write = $('input[name="lyrics-source"][value="write"]');
  write.disabled = !writeEnabled();
  $("#write-reason").textContent = writeEnabled() ? "The smart planner drafts words for you" : ((store.planner && store.planner.write_for_me && store.planner.write_for_me.reason) || "Needs the smart planner, which is off");
  if (state.lyricsSource) $$('input[name="lyrics-source"]').forEach((r) => { r.checked = r.value === state.lyricsSource; });

  $("#language-other").hidden = state.language !== "other";
  paintLanguageBadge();

  for (const wrap of $$("[data-instrument]")) {
    const id = wrap.dataset.instrument;
    wrap.querySelector(".pick").setAttribute("aria-pressed", String(state.picked.includes(id)));
    wrap.querySelector(".star").setAttribute("aria-pressed", String(state.lead === id));
  }
  for (const b of $$("[data-feeling]")) b.setAttribute("aria-pressed", String(state.feeling.includes(b.dataset.feeling)));
  const err = $("#instrument-error");
  err.hidden = !state.error;
  err.textContent = state.error || "";

  const ok = canCreate(state, { writeEnabled: writeEnabled() });
  $("#btn-create").disabled = !ok.ok || busy;
  $("#create-hint").textContent = ok.ok ? (store.system && store.system.engine === "fake" ? "Ready. This server is the TEST engine: it makes fake sound, not music." : "Ready. This makes real music on this Mac and takes about a minute or two.") : ok.reason;
}

function paintLanguageBadge() {
  const note = $("#language-badge");
  const code = state.language;
  if (!code) { note.hidden = true; return; }
  const b = languageBadge(code);
  note.hidden = !b;
  if (b) note.textContent = `${b.label}: ${b.badge}.${b.note ? " " + b.note + "." : ""}${b.wording && b.wording !== b.badge ? " (" + b.wording + ")" : ""}`;
}

function paintRecipeNote() {
  const note = $("#recipe-note");
  const r = recipes.find((x) => x.id === state.recipe);
  note.hidden = !(r && r.caveat);
  note.textContent = r && r.caveat ? r.caveat : "";
}

// ------------------------------------------------------------------------------------------ submit
async function submit() {
  const ok = canCreate(state, { writeEnabled: writeEnabled() });
  if (!ok.ok || busy) return;
  busy = true;
  paint();
  const key = newIdempotencyKey(); // one new UUID per press
  $("#create-error").hidden = true;
  announce("Making your plan.");
  try {
    const resp = await api("/api/songs", { method: "POST", body: buildCreateBody(state), headers: { "Idempotency-Key": key } });
    location.hash = `#/song/${resp.song_id}`;
  } catch (err) {
    $("#create-error-text").textContent = err.message;
    $("#create-error").hidden = false;
    announce("That did not work. " + err.message);
  } finally {
    busy = false;
    paint();
  }
}
