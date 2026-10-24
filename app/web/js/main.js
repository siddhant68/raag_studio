// Entry point: loads what the server knows, wires the four views, runs the router, keeps the system strip fresh.
import { api, connectEvents } from "./api.js";
import { loadCapabilities, applyCapabilityLabels } from "./caps.js";
import { $, $$, h, render, announce } from "./dom.js";
import { store } from "./store.js";
import { loadSettings, refreshSystem } from "./system.js";
import * as create from "./create.js";
import * as song from "./song.js";
import * as library from "./library.js";
import * as settings from "./settings.js";

const VIEWS = { create, song, library, settings };

async function loadBasics() {
  const results = await Promise.allSettled([
    loadCapabilities(),
    api("/api/instruments").then((r) => { store.instruments = r.instruments; }),
    api("/api/genres").then((r) => { store.genres = r.genres; }),
    loadSettings(),
  ]);
  const failed = results.find((r) => r.status === "rejected");
  if (failed) {
    const main = $("#main");
    main.prepend(h("div", { class: "banner banner-error", role: "alert" }, failed.reason && failed.reason.message ? failed.reason.message : "Something went wrong while starting."));
  }
}

// ---------------------------------------------------------------------------------------------- router
function parseRoute() {
  const hash = location.hash.replace(/^#\/?/, "");
  const [name, arg] = hash.split("/");
  if (name === "song" && arg) return { view: "song", arg };
  if (name === "library" || name === "settings") return { view: name };
  return { view: "create" };
}

let current = null;
async function route() {
  const r = parseRoute();
  for (const name of Object.keys(VIEWS)) $(`#view-${name}`).hidden = name !== r.view;
  for (const a of $$(".nav a")) a.removeAttribute("aria-current");
  const navKey = r.view === "song" ? "create" : r.view;
  const navLink = $(`#nav-${navKey}`);
  if (navLink) navLink.setAttribute("aria-current", "page");
  current = r.view;
  document.title = { create: "Raag Studio", song: "Your song · Raag Studio", library: "Library · Raag Studio", settings: "Settings · Raag Studio" }[r.view];
  await VIEWS[r.view].enter(r.arg);
  const heading = $(`#view-${r.view} h1`);
  if (heading && !route.first) heading.focus({ preventScroll: false });
  route.first = false;
}
route.first = true;

async function boot() {
  await loadBasics();
  applyCapabilityLabels(document);
  await create.init();
  song.init();
  library.init();
  settings.init();
  store.events = connectEvents({
    hello: () => refreshSystem(),
    job: (job) => { song.onJob(job); },
    takes_ready: (ev) => { song.onTakesReady(ev); refreshSystem(); },
    feedback: (ev) => song.onFeedback(ev),
  });
  window.addEventListener("hashchange", route);
  await route();
  refreshSystem();
  setInterval(() => { if (!document.hidden) refreshSystem(); }, 15000);
  // The planner is switched outside the page (PUT /api/settings): pick that up without a manual reload.
  const syncPlanner = async () => {
    const before = JSON.stringify(store.planner && [store.planner.provider, store.planner.write_for_me]);
    try { await loadSettings(); } catch (err) { return; }
    if (before !== JSON.stringify(store.planner && [store.planner.provider, store.planner.write_for_me])) create.onPlannerChanged();
  };
  window.addEventListener("focus", syncPlanner);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) syncPlanner(); });
  announce("Raag Studio is ready.");
}

boot();
