export const USE_CASES = {
  club: {preset: "tease_blend", aBeats: 32, bBeats: 32},
  genre: {preset: "echo_reset", aBeats: 32, bBeats: 32},
  reel: {preset: "reel_switch", aBeats: 16, bBeats: 16},
  chill: {preset: "bass_swap", aBeats: 48, bBeats: 48},
};

export function timing(p) {
  const changing = ["echo_reset", "reel_switch"].includes(p.preset);
  const aTempo = changing ? p.a_bpm : p.target_bpm;
  const bTempo = changing ? p.b_bpm : p.target_bpm;
  const overlap = (p.preset === "tease_blend" ? 16 : p.preset === "bass_swap" ? 8 : 0) * 60 / aTempo;
  const reveal = p.a_beats * 60 / aTempo - overlap;
  return {reveal: p.preset === "tease_blend" ? p.a_beats * 60 / aTempo : reveal, overlapStart: reveal, duration: reveal + p.b_beats * 60 / bTempo, changing};
}

export function validateSelection(p, a, b) {
  if (!a || !b) return "Choose a track for each deck.";
  if (a.status !== "ready" || b.status !== "ready") return "Wait for both tracks to finish analysis.";
  for (const [role, source] of [["a", a], ["b", b]]) {
    const bpm = p[`${role}_bpm`], cue = p[`${role}_cue_s`], beats = p[`${role}_beats`];
    if (!Number.isFinite(bpm) || bpm < 60 || bpm > 180) return "Source tempo must be between 60 and 180 BPM.";
    if (!Number.isFinite(cue) || cue < 0) return "Choose a valid start time.";
    if (cue + beats * 60 / bpm > source.duration_s - .005) return `Deck ${role.toUpperCase()}: passage runs past the end. Choose an earlier cue or fewer beats.`;
  }
  if (!Number.isFinite(p.target_bpm) || p.target_bpm < 60 || p.target_bpm > 180) return "Mix tempo must be between 60 and 180 BPM.";
  if (!["echo_reset", "reel_switch"].includes(p.preset) && [p.a_bpm, p.b_bpm].some(b => Math.abs(p.target_bpm / b - 1) > .15)) return "This tempo gap needs more than 15% stretching. Try Tempo portal.";
  if (p.preset === "tease_blend" && Math.min(p.a_beats, p.b_beats) < 24) return "Tease & handover needs at least 24 beats on each deck.";
  return null;
}

export function timeLabel(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
}
