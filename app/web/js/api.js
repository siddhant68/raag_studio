// Thin wrapper over fetch for the local API, plus the SSE connection with a polling fallback. Same origin only.
import { describeApiError } from "./logic.js";

export class ApiProblem extends Error {
  constructor(status, body) {
    super(describeApiError(status, body));
    this.status = status;
    this.code = body && body.error ? body.error.code : "network";
    this.body = body;
  }
}

export async function api(path, { method = "GET", body, headers = {} } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiProblem(0, null);
  }
  let data = null;
  try { data = await res.json(); } catch (err) { /* empty body */ }
  if (!res.ok) throw new ApiProblem(res.status, data);
  return data;
}

/**
 * Live events. Calls handlers[event](data) for hello, job, take_done, takes_ready, feedback.
 * `status()` is "live" while the stream is open, otherwise "polling" so callers know to poll.
 */
export function connectEvents(handlers) {
  let es = null;
  let state = "connecting";
  let lastEventAt = 0;
  const names = ["hello", "job", "take_done", "takes_ready", "feedback"];
  function open() {
    if (typeof EventSource === "undefined") { state = "polling"; return; }
    es = new EventSource("/api/events");
    es.onopen = () => { state = "live"; lastEventAt = Date.now(); };
    es.onerror = () => { state = "polling"; }; // the browser reconnects by itself; callers poll meanwhile
    for (const name of names) {
      es.addEventListener(name, (ev) => {
        state = "live";
        lastEventAt = Date.now();
        let data = null;
        try { data = JSON.parse(ev.data); } catch (err) { return; }
        if (handlers[name]) handlers[name](data);
      });
    }
  }
  open();
  return { status: () => state, lastEventAt: () => lastEventAt, close: () => es && es.close() };
}
