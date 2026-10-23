// Server facts shown in the strip at the top: planner badge, GPU, disk, video queue, test-engine banner.
import { api } from "./api.js";
import { $ } from "./dom.js";
import { store } from "./store.js";

export async function loadSettings() {
  const r = await api("/api/settings");
  store.settings = r.settings;
  store.planner = r.planner;
  paintPlannerBadge();
  return r;
}

function paintPlannerBadge() {
  const el = $("#planner-badge");
  if (!el || !store.planner) return;
  el.textContent = `Planner: ${store.planner.label}`; // text comes from the API
  el.title = (store.planner.providers.find((p) => p.active) || {}).description || "";
}

export async function refreshSystem() {
  try {
    const s = await api("/api/system");
    store.system = s;
    paintSystem(s);
    return s;
  } catch (err) {
    paintSystemDown();
    return null;
  }
}

function setSys(el, text, level) {
  el.textContent = text;
  el.className = "sys" + (level ? " " + level : "");
}

function paintSystem(s) {
  $("#fake-banner").hidden = s.engine !== "fake";
  if (s.engine === "fake") setSys($("#sys-mps"), "Apple GPU: not used (test engine)", "bad");
  else if (s.mps === true) setSys($("#sys-mps"), "Apple GPU: ready", "ok");
  else if (s.mps === false) setSys($("#sys-mps"), "Apple GPU: not available, so I will not render", "bad");
  else setSys($("#sys-mps"), "Apple GPU: unknown", "warn");
  const free = s.disk_free_gib;
  setSys($("#sys-disk"), `Disk: ${free} GiB free`, free < s.min_disk_gib ? "bad" : free < s.min_disk_gib * 2 ? "warn" : "ok");
  const vq = s.video_queue || {};
  let text;
  let level = "warn";
  if (vq.state === "idle") { text = "Video queue: idle"; level = "ok"; }
  else if (vq.state === "busy") text = `Video queue: busy (${(vq.running || 0) + (vq.pending || 0)} job); music waits its turn`;
  else text = "Video queue: unknown";
  const q = s.queue || {};
  if (q.depth) text += ` · ${q.depth} music job${q.depth === 1 ? "" : "s"} in line`;
  setSys($("#sys-queue"), text, level);
}

function paintSystemDown() {
  setSys($("#sys-mps"), "Server: not reachable", "bad");
  setSys($("#sys-disk"), "Disk: unknown", "warn");
  setSys($("#sys-queue"), "Video queue: unknown", "warn");
}
