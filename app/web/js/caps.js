// Honesty labels. The ONLY source of wording about how much we control is GET /api/capabilities (capabilities.json).
import { api } from "./api.js";
import { h, clear } from "./dom.js";

let caps = null;

export async function loadCapabilities() {
  caps = await api("/api/capabilities");
  return caps;
}
export const capabilities = () => caps;

/** Pills for one control, with the label and tooltip text taken from the registry. Returns [] for n/a controls. */
export function labelFor(controlId) {
  const c = caps && caps.controls[controlId];
  if (!c || !c.needs_label) return [];
  return c.labels.map((l) => h("span", { class: `cap cap-${l.cls}`, title: `${l.label}: ${l.tooltip}` }, l.label));
}

export function wordingFor(controlId) {
  const c = caps && caps.controls[controlId];
  return c ? c.ui_wording : "";
}

/** Fill every <span data-cap-for="C#"> under root with the registry's labels and wording. */
export function applyCapabilityLabels(root = document) {
  for (const slot of root.querySelectorAll("[data-cap-for]")) {
    const id = slot.getAttribute("data-cap-for");
    clear(slot);
    const pills = labelFor(id);
    if (!pills.length) continue;
    pills.forEach((p) => slot.append(p));
    const wording = wordingFor(id);
    if (wording && wording !== "n/a") slot.append(h("span", { class: "cap-wording" }, wording));
    slot.setAttribute("title", caps.controls[id].labels.map((l) => `${l.label}: ${l.tooltip}`).join("\n"));
  }
}

/** Badge for a C15 language option ("experimental" / "untested"), straight from the registry. */
export function languageBadge(code) {
  const opts = caps && caps.options && caps.options.C15;
  if (!opts) return null;
  const o = opts[code] || opts.other;
  return { label: o.label, badge: o.badge, note: o.note || "", wording: (caps.capabilities[o.capability] || {}).ui_wording || "" };
}

export function languageOptions() {
  const opts = (caps && caps.options && caps.options.C15) || {};
  return Object.entries(opts).map(([code, o]) => ({ code, label: o.label, badge: o.badge }));
}

export function backgroundOptions() {
  const opts = (caps && caps.options && caps.options.C14) || {};
  return Object.entries(opts).map(([code, o]) => ({ code, label: o.label, badge: o.badge || "" }));
}
