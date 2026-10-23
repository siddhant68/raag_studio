// Library: song list (favourites filter), taste-ledger counts, disk meter and the confirmed manual clean-up.
import { api } from "./api.js";
import { $, h, render, announce } from "./dom.js";
import { formatBytes } from "./logic.js";

let songs = [];

export function init() {
  $("#fav-only").addEventListener("change", paintList);
  $("#btn-prune").addEventListener("click", prune);
}

export async function enter() {
  await Promise.all([loadSongs(), loadLedger(), loadDisk()]);
}

async function loadSongs() {
  try { songs = (await api("/api/songs")).songs; } catch (err) { songs = []; $("#library-empty").textContent = err.message; }
  paintList();
}

function paintList() {
  const favOnly = $("#fav-only").checked;
  const shown = songs.filter((s) => !favOnly || s.favourite_count > 0);
  $("#library-empty").hidden = shown.length > 0;
  if (!shown.length) $("#library-empty").textContent = favOnly ? "No songs with a heart yet." : "Nothing here yet. Make your first song from Create.";
  render($("#song-list"), ...shown.map((s) => {
    const job = s.latest_job || {};
    const state = job.state && job.state !== "succeeded" ? ` · ${job.state === "queued" || job.state === "running" ? "still being made" : job.state}` : "";
    return h("li", {}, h("a", { class: "song-item", href: `#/song/${s.id}`, "data-chrome": "open-song" },
      h("div", { class: "t" }, s.title, job.engine === "fake" ? h("span", { class: "tag tag-fake" }, " TEST AUDIO") : null),
      h("div", { class: "m" }, `${s.take_count} take${s.take_count === 1 ? "" : "s"} · ${s.favourite_count} with a heart · ${new Date(s.created_at).toLocaleString()}${state}`)));
  }));
}

function ledgerTable(title, group, nameMap = {}) {
  const rows = Object.entries(group);
  if (!rows.length) return null;
  return h("div", {}, h("h3", {}, title), h("table", { class: "ledger-table" },
    h("thead", {}, h("tr", {}, ["", "Takes", "Loved", "Fine", "No", "Hearts"].map((c) => h("th", { scope: "col" }, c)))),
    h("tbody", {}, rows.map(([k, v]) => h("tr", {}, h("th", { scope: "row" }, nameMap[k] || k.replace(/^r\d+_/, "").replace(/_/g, " ")), h("td", {}, v.takes), h("td", {}, v.loved), h("td", {}, v.fine), h("td", {}, v.no), h("td", {}, v.favourites))))));
}

async function loadLedger() {
  const box = $("#ledger-body");
  try {
    const l = await api("/api/ledger");
    if (!l.totals.takes) { render(box, h("p", { class: "help" }, "No takes yet, so nothing to count.")); return; }
    render(box,
      h("p", {}, `${l.totals.takes} takes so far: ${l.totals.loved} loved, ${l.totals.fine} fine, ${l.totals.no} not for you, ${l.totals.unrated} not rated yet; ${l.totals.favourites} with a heart.`),
      ledgerTable("By starting sound", l.by_recipe), ledgerTable("By lead instrument", l.by_lead), ledgerTable("By pace", l.by_pace));
  } catch (err) { render(box, h("p", { class: "help warn" }, err.message)); }
}

async function loadDisk() {
  const box = $("#disk-body");
  try {
    const d = await api("/api/storage");
    const used = d.disk_total_gib - d.disk_free_gib;
    render(box,
      h("div", { class: "meter-row" },
        h("meter", { min: 0, max: d.disk_total_gib, value: used, high: d.disk_total_gib - d.min_disk_gib, optimum: 0, "aria-label": "Disk used" }),
        h("span", {}, `${d.disk_free_gib} GiB free of ${d.disk_total_gib} GiB`)),
      h("p", { class: "help" }, `Making music needs at least ${d.min_disk_gib} GiB free. Your songs use ${d.runs_gib} GiB (${d.native_files} full-quality files).`));
  } catch (err) { render(box, h("p", { class: "help warn" }, err.message)); }
}

function confirmDialog(title, text, okLabel) {
  const dlg = $("#confirm-dialog");
  $("#confirm-title").textContent = title;
  $("#confirm-text").textContent = text;
  $("#confirm-ok").textContent = okLabel;
  return new Promise((resolve) => {
    dlg.addEventListener("close", () => resolve(dlg.returnValue === "ok"), { once: true });
    dlg.returnValue = "cancel";
    if (typeof dlg.showModal === "function") dlg.showModal(); else resolve(false);
    $("#confirm-cancel").focus();
  });
}

async function prune() {
  const days = Number($("#prune-days").value);
  const out = $("#prune-result");
  if (!Number.isInteger(days) || days < 0) { out.textContent = "Type a whole number of days (0 or more)."; return; }
  const ok = await confirmDialog("Clean up old audio?",
    `This permanently removes the full-quality audio files of takes older than ${days} day${days === 1 ? "" : "s"} that you have not marked with a heart. ` +
    "The MP3 previews, plans and notes stay, so you can still listen. Hearted takes are never touched. This cannot be undone.", "Yes, remove them");
  if (!ok) { out.textContent = "Nothing was removed."; return; }
  try {
    const r = await api("/api/admin/prune", { method: "POST", body: { older_than_days: days, confirm: true } });
    out.textContent = `Removed ${r.pruned} full-quality file${r.pruned === 1 ? "" : "s"} (${formatBytes(r.freed_bytes)}). ${r.skipped_favourites.length} hearted take${r.skipped_favourites.length === 1 ? " was" : "s were"} kept.`;
    announce(out.textContent);
    loadDisk();
  } catch (err) { out.textContent = err.message; }
}
