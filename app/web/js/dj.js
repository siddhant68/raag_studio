import {USE_CASES, timing, validateSelection, timeLabel} from "./dj_logic.mjs";

const $ = s => document.querySelector(s);
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};
let catalog = {assets: [], takes: [], jobs: [], presets: {}};
let preset = "tease_blend", takesSignature = "", assetsSignature = "", loading = false;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw Error(data.error?.message || data.detail || "The request could not be completed.");
  return data;
}
const post = (path, body) => api(`/api/dj${path}`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
function status(message, error = false) {$("#status").textContent = message; $("#status").classList.toggle("error", error);}
function source(role) {return catalog.assets.find(a => a.id === $(`#source-${role}`).value);}
function selection() {
  return {a_id: $("#source-a").value, b_id: $("#source-b").value, preset,
    a_bpm: Number($("#bpm-a").value), b_bpm: Number($("#bpm-b").value),
    a_cue_s: Number($("#cue-a").value), b_cue_s: Number($("#cue-b").value),
    target_bpm: Number($("#target-bpm").value), a_beats: Number($("#beats-a").value), b_beats: Number($("#beats-b").value),
    title: `${source("a")?.name || "A"} → ${source("b")?.name || "B"}`.slice(0, 120)};
}

function waveform(canvas, values = [], color = "#72cebb", marker = null, region = null) {
  const ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#111510"; ctx.fillRect(0, 0, w, h);
  if (region) {ctx.fillStyle = `${color}18`; ctx.fillRect(w * region[0], 0, w * (region[1] - region[0]), h);}
  const max = Math.max(.01, ...values);
  const step = w / Math.max(values.length, 1);
  ctx.fillStyle = color;
  values.forEach((v, i) => {
    const height = Math.max(2, v / max * h * .84);
    ctx.globalAlpha = marker != null && i / values.length < marker ? .4 : .9;
    ctx.fillRect(i * step, (h - height) / 2, Math.max(1, step * .65), height);
  });
  ctx.globalAlpha = 1;
  if (marker != null) {ctx.fillStyle = "#eff8cc"; ctx.fillRect(marker * w, 0, 2, h);}
}

function updateTiming() {
  const p = selection(), error = validateSelection(p, source("a"), source("b"));
  const t = timing(p);
  $("#estimate").textContent = error || `About ${Math.round(t.duration)} seconds · ${p.preset === "tease_blend" ? `overlap at ${t.overlapStart.toFixed(1)}s · tease releases` : "incoming track"} at ${t.reveal.toFixed(1)}s · ${t.changing ? "each source keeps its original tempo" : `both decks at ${p.target_bpm} BPM`}`;
  $("#render").disabled = Boolean(error) || loading;
  $("#move-label").textContent = catalog.presets[preset]?.name || "→";
  $("#target-bpm").disabled = t.changing;
  for (const role of ["a", "b"]) {
    const asset = source(role), cue = p[`${role}_cue_s`], bpm = p[`${role}_bpm`], beats = p[`${role}_beats`];
    waveform($(`#wave-${role}`), asset?.analysis?.waveform, role === "a" ? "#72cebb" : "#ec9a6b",
      asset ? cue / asset.duration_s : null, asset ? [cue / asset.duration_s, Math.min(1, (cue + beats * 60 / bpm) / asset.duration_s)] : null);
  }
}

function choosePreset(key) {
  preset = key;
  document.querySelectorAll(".preset").forEach(b => {b.classList.toggle("selected", b.dataset.preset === key); b.setAttribute("aria-pressed", String(b.dataset.preset === key));});
  updateTiming();
}

function deckChanged(role) {
  const asset = source(role), audio = $(`#audio-${role}`);
  if (!asset) {audio.removeAttribute("src"); updateTiming(); return;}
  audio.src = `/api/dj/assets/${asset.id}/audio`;
  $(`#bpm-${role}`).value = Number((asset.analysis?.bpm || 120).toFixed(3));
  $(`#cue-${role}`).value = Number((asset.suggested_cue_s ?? asset.analysis?.grid_offset_s ?? 0).toFixed(3));
  const analysis = asset.analysis;
  $(`#info-${role}`).textContent = `${timeLabel(asset.duration_s)} · ${asset.sharing === "original_generated_sources" ? "Original music" : "Local source"} · ${analysis ? "Tempo estimated; choose and audition your cue." : asset.status === "analysis_failed" ? "Analysis failed. Retry, or choose another recording." : "Analysis in progress…"}`;
  let retry = document.querySelector(`#retry-${role}`);
  if (!retry) {
    retry = action("Retry analysis", async () => {
      const s = source(role); if (!s) return;
      try {await post(`/assets/${s.id}/analyze`, {}); status("Analysis queued. You can keep listening to existing previews."); await refresh();}
      catch (e) {status(e.message, true);}
    });
    retry.id = `retry-${role}`; retry.className = "small-button"; $(`#info-${role}`).after(retry);
  }
  retry.hidden = !["analysis_failed", "imported"].includes(asset.status);
  if (source("a") && source("b")) $("#target-bpm").value = Math.round((Number($("#bpm-a").value) + Number($("#bpm-b").value)) / 2);
  updateTiming();
}

function drawAssets() {
  const signature = catalog.assets.map(a => `${a.id}:${a.status}`).join();
  if (signature === assetsSignature) return;
  assetsSignature = signature;
  for (const role of ["a", "b"]) {
    const select = $(`#source-${role}`), old = select.value;
    select.replaceChildren(new Option("Choose a track", ""));
    for (const asset of catalog.assets) select.add(new Option(`${asset.name}${asset.status === "ready" ? "" : " · analyzing"}`, asset.id));
    select.value = old;
    if (!old && catalog.assets.length) select.value = catalog.assets[Math.min(role === "a" ? 0 : 1, catalog.assets.length - 1)].id;
    // Refresh after analysis, keeping manual edits when only another asset changed.
    if (!old || select.dataset.status !== source(role)?.status) deckChanged(role);
    select.dataset.status = source(role)?.status || "";
  }
}

function drawPresets() {
  if ($("#presets").children.length) return;
  for (const [key, value] of Object.entries(catalog.presets)) {
    const button = el("button", null, "preset"); button.type = "button"; button.dataset.preset = key;
    button.append(el("strong", value.name), el("span", value.description));
    button.addEventListener("click", () => choosePreset(key));
    $("#presets").append(button);
  }
  choosePreset(preset);
}

function drawJobs() {
  const jobs = catalog.jobs.filter(j => ["queued", "running", "failed", "interrupted"].includes(j.state)).slice(0, 5);
  $("#queue-section").hidden = !jobs.length;
  $("#queue").replaceChildren();
  for (const job of jobs) {
    const row = el("div", null, `job ${job.state}`);
    row.append(el("strong", `${{analyze: "Analyzing track", render: "Rendering transition", visualizer: "Making reel video"}[job.operation]} · ${job.state}`), el("span", job.message));
    $("#queue").append(row);
  }
}

function action(label, fn) {const b = el("button", label); b.type = "button"; b.addEventListener("click", fn); return b;}
async function feedback(take, verdict, notes) {
  try {await post(`/takes/${take.id}/feedback`, {verdict, notes}); takesSignature = ""; await refresh();}
  catch (e) {status(e.message, true);}
}

function takeCard(take) {
  const card = el("article", null, "take"), head = el("div", null, "take-title"), title = el("div");
  title.append(el("p", catalog.presets[take.preset]?.use_case || "DJ EXPERIMENT", "eyebrow"), el("h3", take.title));
  const favorite = action(take.feedback?.verdict === "favorite" ? "★" : "☆", () => feedback(take, take.feedback?.verdict === "favorite" ? "unrated" : "favorite", take.feedback?.notes || ""));
  favorite.className = `favorite ${take.feedback?.verdict === "favorite" ? "kept" : ""}`;
  favorite.setAttribute("aria-label", "Toggle favorite"); favorite.setAttribute("aria-pressed", String(take.feedback?.verdict === "favorite"));
  head.append(title, favorite); card.append(head);
  const sharing = take.sharing === "original_generated_sources" ? "Original-music demo" : "Private song experiment";
  card.append(el("span", `${timeLabel(take.duration_s)} · ${catalog.presets[take.preset]?.name || take.preset} · ${sharing}`, "take-badge"));
  const canvas = el("canvas"); canvas.width = 1000; canvas.height = 110; canvas.setAttribute("aria-label", "Preview waveform; click to seek");
  waveform(canvas, take.waveform, "#d5ef78", take.reveal_s / take.duration_s);
  const audio = el("audio"); audio.controls = true; audio.preload = "none"; audio.src = `/api/dj/takes/${take.id}/master.mp3`;
  canvas.addEventListener("click", e => {audio.currentTime = (e.clientX - canvas.getBoundingClientRect().left) / canvas.getBoundingClientRect().width * take.duration_s; audio.play().catch(e => status(e.message, true));});
  card.append(canvas, audio);
  const buttons = el("div", null, "take-actions");
  const edited = action("Edited", () => switchArm("master")), control = action("Untreated comparison", () => switchArm("control")); edited.className = "selected";
  function switchArm(arm) {
    const currentTime = audio.currentTime, playing = !audio.paused;
    audio.pause(); audio.src = `/api/dj/takes/${take.id}/${arm}.mp3`;
    audio.addEventListener("loadedmetadata", () => {audio.currentTime = Math.min(currentTime, audio.duration); if (playing) audio.play().catch(e => status(e.message, true));}, {once: true});
    // The gallery uses preload=none. Explicitly load the new arm so metadata
    // arrives before seeking; otherwise the loadedmetadata callback never runs.
    audio.preload = "metadata";
    audio.load();
    edited.classList.toggle("selected", arm === "master"); control.classList.toggle("selected", arm === "control");
  }
  buttons.append(edited, control, action("Hear the handover ↗", () => {audio.currentTime = Math.max(0, take.reveal_s - 6); audio.play().catch(e => status(e.message, true));}));
  if (take.recipe) buttons.append(action("Use this recipe", () => useRecipe(take.recipe)));
  if (!take.has_visualizer) buttons.append(action("Make reel video", async () => {
    try {await post(`/takes/${take.id}/visualizer`, {}); status("Vertical waveform video queued. Its download will appear here when ready."); await refresh();}
    catch (e) {status(e.message, true);}
  }));
  card.append(buttons);
  const downloads = el("div", null, "downloads");
  for (const [filename, text] of [["master.mp3", "MP3 ↓"], ["master.wav", "WAV master ↓"], ["plan.json", "Recipe ↓"]]) {
    const a = el("a", text); a.href = `/api/dj/takes/${take.id}/${filename}`; a.download = ""; downloads.append(a);
  }
  card.append(downloads);
  if (take.has_visualizer) {
    const videoLink = el("a", "Vertical reel video ↓"); videoLink.href = `/api/dj/takes/${take.id}/visualizer.mp4`; videoLink.download = ""; downloads.append(videoLink);
  }
  const detail = el("details"), list = el("ul", null, "event-list"); detail.append(el("summary", "Cue sheet & listening notes"));
  for (const ev of take.events) {
    const item = el("li"); item.append(action(`${ev.time_s.toFixed(1)}s`, () => {audio.currentTime = ev.time_s; audio.play().catch(e => status(e.message, true));}), el("span", ev.label)); list.append(item);
  }
  detail.append(list, el("p", `Measured export: ${take.levels.master.mp3.input_i.toFixed(1)} LUFS · ${take.levels.master.mp3.input_tp.toFixed(1)} dBTP. Listening decides whether the timing, harmony and payoff work.`));
  const notes = el("textarea"); notes.placeholder = "What worked? Where did it lose you?"; notes.setAttribute("aria-label", "Listening notes"); notes.value = take.feedback?.notes || "";
  const review = el("div", null, "review-actions");
  for (const [verdict, label] of [["keep", "Keep"], ["revise", "Refine"], ["reject", "Reject"]]) review.append(action(label, () => feedback(take, verdict, notes.value)));
  detail.append(notes, review); card.append(detail);
  return card;
}

function useRecipe(p) {
  for (const role of ["a", "b"]) {
    $(`#source-${role}`).value = p[`${role}_id`]; deckChanged(role);
    for (const [control, key] of [["bpm", "bpm"], ["cue", "cue_s"]]) $(`#${control}-${role}`).value = Number(p[`${role}_${key}`].toFixed(3));
    $(`#beats-${role}`).value = p[`${role}_beats`];
  }
  $("#target-bpm").value = p.target_bpm; choosePreset(p.preset);
  $("#studio").scrollIntoView({behavior: "smooth"}); status("Recipe loaded. Move a cue or choose a different technique, then render a new version.");
}

function drawTakes() {
  const filter = $("#take-filter").value;
  const signature = filter + JSON.stringify(catalog.takes.map(t => [t.id, t.feedback, t.has_visualizer]));
  if (signature === takesSignature) return;
  if (document.activeElement?.tagName === "TEXTAREA") return;
  // Do not interrupt playback when a background job finishes.
  if ($("#takes audio:not([data-unused])") && [...$("#takes").querySelectorAll("audio")].some(a => !a.paused)) return;
  takesSignature = signature;
  const takes = catalog.takes.filter(t => filter === "all" || (filter === "favorites" ? t.feedback?.verdict === "favorite" : t.sharing === "original_generated_sources"));
  $("#takes").replaceChildren(...takes.map(takeCard));
  if (!takes.length) $("#takes").append(el("p", "Your previews will appear here. Pick two tracks and make the first handover.", "empty"));
}

async function refresh() {
  try {
    catalog = await api("/api/dj/catalog"); drawPresets(); drawAssets(); drawJobs(); drawTakes(); updateTiming();
    if (!catalog.runtime_available) status("Audio runtime unavailable. The existing previews can still be played.", true);
    else if (!loading && !$("#status").classList.contains("error") && $("#status").textContent.startsWith("Loading")) status("Ready. Choose a source passage on each deck, or load an existing recipe below.");
  } catch (e) {status(`Could not reach DJ Lab: ${e.message}`, true);}
}

$("#upload").addEventListener("change", async event => {
  loading = true; updateTiming();
  try {
    for (const file of event.target.files) {
      status(`Importing ${file.name}…`);
      const extension = file.name.split(".").at(-1).toLowerCase();
      await api(`/api/dj/import?name=${encodeURIComponent(file.name.replace(/\.[^.]+$/, ""))}&extension=${extension}`, {method: "POST", headers: {"Content-Type": "application/octet-stream"}, body: file});
    }
    status("Music imported. Measuring tempo and preparing waveforms…"); await refresh();
  } catch (e) {status(e.message, true);}
  finally {loading = false; event.target.value = ""; updateTiming();}
});
$("#render").addEventListener("click", async () => {
  const p = selection(), error = validateSelection(p, source("a"), source("b"));
  if (error) {status(error, true); return;}
  loading = true; updateTiming();
  try {await post("/renders", p); status("Preview queued. Keep exploring while the CPU audio worker renders it."); await refresh();}
  catch (e) {status(e.message, true);}
  finally {loading = false; updateTiming();}
});
for (const role of ["a", "b"]) {
  $(`#source-${role}`).addEventListener("change", () => deckChanged(role));
  $(`#mark-${role}`).addEventListener("click", () => {$(`#cue-${role}`).value = $(`#audio-${role}`).currentTime.toFixed(3); updateTiming();});
  $(`#wave-${role}`).addEventListener("click", e => {
    const s = source(role); if (!s) return;
    const canvas = e.currentTarget;
    const cue = Math.max(0, Math.min(s.duration_s, (e.clientX - canvas.getBoundingClientRect().left) / canvas.getBoundingClientRect().width * s.duration_s));
    $(`#cue-${role}`).value = cue.toFixed(3); $(`#audio-${role}`).currentTime = cue; updateTiming();
  });
}
for (const id of ["bpm-a", "bpm-b", "cue-a", "cue-b", "target-bpm", "beats-a", "beats-b"]) $(`#${id}`).addEventListener("input", updateTiming);
for (const button of document.querySelectorAll("[data-use]")) button.addEventListener("click", () => {
  const use = USE_CASES[button.dataset.use];
  document.querySelectorAll("[data-use]").forEach(b => b.classList.toggle("selected", b === button));
  $("#beats-a").value = use.aBeats; $("#beats-b").value = use.bBeats; choosePreset(use.preset);
});
$("#take-filter").addEventListener("change", () => {document.querySelectorAll("audio").forEach(a => a.pause()); takesSignature = ""; drawTakes();});
document.addEventListener("play", event => {if (event.target.tagName === "AUDIO") document.querySelectorAll("audio").forEach(a => {if (a !== event.target) a.pause();});}, true);
await refresh();
setInterval(() => {if (!document.hidden) refresh();}, 3000);
