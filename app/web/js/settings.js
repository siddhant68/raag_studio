// Settings: the planner part is read-only on purpose. Smart planners are off and nothing on this page can switch them on
// (that sends your brief to Anthropic, so it stays a deliberate API call). The music-engine part is editable through
// its own endpoint, which accepts only the local pipeline and model choice and sends nothing anywhere.
import { api } from "./api.js";
import { capabilities } from "./caps.js";
import { $, h, render } from "./dom.js";
import { store } from "./store.js";
import { loadSettings, refreshSystem } from "./system.js";

export function init() {}

export async function enter() {
  const [, sys] = await Promise.all([loadSettings().catch(() => null), refreshSystem()]);
  paintPlanner();
  paintEngine(sys);
  paintSystem(sys);
  paintCaps();
}

function paintPlanner() {
  const p = store.planner;
  const box = $("#settings-planner");
  if (!p) { render(box, h("p", { class: "help warn" }, "Could not read the planner setting.")); return; }
  render(box,
    h("p", {}, "Right now your words are turned into a plan by: ", h("span", { class: "badge badge-planner" }, p.label)),
    h("table", { class: "plan-table" }, h("tbody", {}, p.providers.map((row) =>
      h("tr", {}, h("th", { scope: "row" }, row.label),
        h("td", {}, row.active ? h("span", { class: "tag tag-you" }, "In use") : h("span", { class: "tag" }, "Off"), " ", row.description,
          h("span", { class: "why" }, row.id === "basic" ? "Always available." : row.available ? `Ready if you ever switch it on (${row.requires} found).` : `Not ready: needs ${row.requires}.`)))))),
    h("div", { class: "banner" },
      h("p", {}, p.how_to_enable)),
    h("p", { class: "help" }, `"Write lyrics for me": ${p.write_for_me.enabled ? "available" : "off. " + (p.write_for_me.reason || "")}`));
}

const PROFILES = [
  ["auto", "Auto", "Song pipeline: turbo with shift 3.0 (ACE-Step's recommendation). Classic plans keep their exact settings."],
  ["classic", "Classic", "Turbo with shift 1.0, exactly like the accepted Yamuna, Daylight and Thodi takes."],
  ["shift3", "Turbo, shift 3.0", "The same model with ACE-Step's recommended timestep shift."],
  ["lm", "Turbo + 5Hz LM", "The 1.7B language model plans the audio before rendering (needs about 3.6 GB, downloaded once)."],
  ["xl", "XL turbo", "The 4B model (needs about 10 GB, downloaded once; uses more memory)."],
  ["xl_lm", "XL turbo + 5Hz LM", "Both of the above."],
];

function paintEngine(sys) {
  const box = $("#settings-engine");
  const st = store.settings || {};
  const models = (sys && sys.optional_models) || {};
  const have = (name) => models[name] && models[name].installed;
  const needs = { lm: ["acestep-5Hz-lm-1.7B"], xl: ["acestep-v15-xl-turbo"], xl_lm: ["acestep-v15-xl-turbo", "acestep-5Hz-lm-1.7B"] };
  const sel = h("select", { id: "engine-profile" }, PROFILES.map(([id, label]) => {
    const missing = (needs[id] || []).filter((m) => !have(m));
    return h("option", { value: id, selected: st.engine_profile === id }, missing.length ? `${label} (not installed)` : label);
  }));
  const pipe = h("input", { type: "checkbox", id: "song-pipeline", checked: st.song_pipeline !== false });
  const msg = h("p", { class: "help", role: "status" });
  const save = async (patch) => {
    try { await api("/api/settings/engine", { method: "PUT", body: patch }); await loadSettings(); msg.textContent = "Saved. New takes use this."; }
    catch (err) { msg.textContent = err.message; }
  };
  sel.addEventListener("change", () => save({ engine_profile: sel.value }));
  pipe.addEventListener("change", () => save({ song_pipeline: pipe.checked }));
  render(box,
    h("p", {}, h("label", {}, pipe, " Use song styles for new songs (genre presets, song map, lyrics written per section)")),
    h("p", { class: "help" }, "Off: new songs use the original template, except when you pick a style or an instrument it does not know."),
    h("p", {}, h("label", { for: "engine-profile" }, "Engine: "), sel),
    h("ul", { class: "report" }, PROFILES.map(([id, label, text]) => h("li", { class: "note" }, h("b", {}, label), ": ", text))),
    h("p", { class: "help" }, "Optional models are never downloaded by a render. To install one, run in Terminal: python3 scripts/fetch_models.py lm (or xl). It shows the size and asks first."),
    msg);
}

function paintSystem(s) {
  const box = $("#settings-system");
  if (!s) { render(box, h("p", { class: "help warn" }, "I cannot reach the server.")); return; }
  const rows = [
    ["Music engine", s.engine === "fake" ? "TEST ENGINE (fake sound, not real music)" : "ACE-Step turbo (real), run as a separate process"],
    ["Engine version", s.engine_rev], ["App version", s.version],
    ["Apple GPU", s.engine === "fake" ? "not used by the test engine" : s.mps === true ? "ready" : s.mps === false ? "not available (I never fall back to the CPU)" : "unknown"],
    ["Disk free", `${s.disk_free_gib} GiB (renders need at least ${s.min_disk_gib} GiB)`],
    ["Video generator queue", `${s.video_queue.state}${s.video_queue.state === "busy" ? " (music waits its turn)" : ""}`],
    ["Music jobs in line", `${s.queue.depth} of ${s.queue.cap} allowed`],
  ];
  render(box, h("dl", { class: "kv" }, rows.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, String(v))])));
}

function paintCaps() {
  const caps = capabilities();
  const box = $("#settings-caps");
  if (!caps) { render(box, h("p", { class: "help warn" }, "Labels could not be loaded.")); return; }
  const classes = Object.entries(caps.classes).filter(([, c]) => c.label);
  const cannot = Object.values(caps.capabilities).filter((c) => (c.classes || []).some((x) => ["c", "unavailable", "not_offered"].includes(x)) || c.ui_wording === "n/a");
  render(box,
    h("p", { class: "help" }, "Next to many choices you will see a small label. It tells you how much that choice really controls."),
    h("dl", { class: "kv" }, classes.flatMap(([k, c]) => [h("dt", {}, h("span", { class: `cap cap-${k}` }, c.label)), h("dd", {}, c.tooltip)])),
    h("h3", {}, "Things this app does not offer"),
    h("ul", { class: "report" }, cannot.map((c) => h("li", { class: "note" }, `${c.name}: ${c.what_we_do}`))));
}
