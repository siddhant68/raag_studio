// Settings: read-only on purpose. Smart planners are off and nothing on this page can switch them on.
import { api } from "./api.js";
import { capabilities } from "./caps.js";
import { $, h, render } from "./dom.js";
import { store } from "./store.js";
import { loadSettings, refreshSystem } from "./system.js";

export function init() {}

export async function enter() {
  const [, sys] = await Promise.all([loadSettings().catch(() => null), refreshSystem()]);
  paintPlanner();
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
