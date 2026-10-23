// Shared, read-mostly state: what the server told us at start-up.
export const store = {
  instruments: [],   // [{id, name, validated}] from /api/instruments
  planner: null,     // planner block of /api/settings: {provider, label, smart_enabled, providers, write_for_me, how_to_enable}
  settings: null,
  system: null,      // last /api/system
  events: null,      // connectEvents handle
};

export function nameOf(id) {
  const found = store.instruments.find((i) => i.id === id);
  return found ? found.name : String(id).replace(/_/g, " ");
}

/** The honest wording about the current planner. Never says "AI" for a rule-based planner. */
export function plannerIsSmart() {
  return !!(store.planner && store.planner.provider !== "basic");
}
