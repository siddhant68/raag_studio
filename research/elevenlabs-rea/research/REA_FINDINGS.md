# REA findings and evidence boundary

24 October 2026 IST. The live REA MCP connection was verified independently from account access. `binary_session {}` returned rea-agents 6.7.0, skill 42,207 tools and server identity recorded in evidence/rea-server-identity.json. Supported native cua accessed authenticated Edge and verified the account, generation, editor and billing. This fixes the preparation session's two missing prerequisites.

**No REA webpage/network trace was acquired.** The supported browser inventory exposed no authenticated CDP browser; bounded process/listening-socket inspection found no existing Edge/Chrome debug endpoint. The user browser was not restarted, a debugging port was not enabled, and private credentials were not extracted. Exported rea-bundle.json has0 records; do not describe these UI findings as REA-backed reverse engineering. No native binary needed opening or closing.

## Observable behavioral path

1. Custom words and a musical brief entered separate UI fields, or Prompt/Lyrics anchors in the unified composer. v2.5, duration and variant count have visible controls. Text plus model/duration/variants/reference forms the observable input boundary.
2. Generate disables editing and shows Loading. The mechanism that expands the brief is not exposed. A saved project exposes section names, lyrics, durations and include/exclude style pills that were more detailed than the input.
3. A playable song appears in history with a project URL and selectedSongId. These are actual observed UI URL keys, not inferred API fields. Original files download from that result.
4. Project section edits remain staged. Added Chorus style pills made only Chorus report pending changes. Generate produced a new History entry labelled Composition plan edited and a new songID in the same project.
5. A client error appeared after the successful edit submission. Refreshing through Try again recovered the completed version without another submit. Signals outside the chorus strongly matched the parent at zero estimated lag; chorus signals changed. See E05 alignment data for exact windows/limits.
6. Refreshed billing confirms spending; the profile popup initially retained a stale balance. Do not equate unchanged immediate UI with failed submission or free generation.

Evidence: ACCESS_VERIFICATION.md; UI-E01.md; UI-EDITOR-E01.md; UI-E07.md; UI-E18.md; BILLING_CHECKPOINT_10800.md; experiment_log.csv; original audio hashes, ASR and alignment records.

## What remains unknown

Request endpoint/payload, asynchronous job identifiers, polling/SSE/WebSocket behavior, initiating client code, storage implementation, exact backend composition-plan format, reference embeddings, training/model algorithms and per-call server billing internals were not observed. Exposed per-section styles do not prove client-side execution. Public API `composition_plan`, `conditioning_ref`, `song_id` and audio-reference chunks are documented mechanisms, not proof the web client used those exact fields.

No private API was replayed, no model internals were inferred from interface polish, and no source was claimed from a screenshot. A later REA capture needs an existing authorized loopback endpoint/target, then list_browser_targets and a tightly scoped passive capture. That prerequisite is separate from the fully working native UI route.
