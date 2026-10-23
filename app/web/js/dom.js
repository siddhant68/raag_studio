// Tiny DOM helpers. Text is always set with textContent / createTextNode, never innerHTML, because briefs are user text.

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, String(v));
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
export function show(el, on = true) { el.hidden = !on; }

/** Replace the children of `el`. */
export function render(el, ...children) { clear(el); return append(el, children); }

let announceEl = null;
/** Polite screen-reader announcement (also visible in the status line when `visible`). */
export function announce(message) {
  announceEl = announceEl || document.getElementById("live-status");
  if (announceEl) announceEl.textContent = message;
}
