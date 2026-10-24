# Observed ElevenLabs lyrical-song workflows

Observed24 October 2026 IST in Siddhant's Workspace, Creator, native Edge through supported cua_repl. Native UI notes are not REA network captures. Evidence index: evidence/ACCESS_VERIFICATION.md and per-experiment records.

## Creation

Music initially opened Marketplace at https://elevenlabs.io/app/music. Composer defaults: v2.5,2 variants, Auto duration, Auto lyrics,900 credits/min×2; automatic prompt-improvement button present, toggle state not exposed by AX. Research explicitly used1 variant and fixed 90 seconds (1,350 credits), except150 seconds E20 (2,250 credits).

Duration menu offers Auto,30s,1m,2m,4m,6m and a custom mm:ss field. Return commits custom text; Escape closes the menu. Lyrics offers Auto, Custom and Instrumental. Custom reveals a separate text field, with AI lyric editing/generation entry controls. These AI helper actions were not tested separately.

Generations at https://elevenlabs.io/app/music/history uses a unified contenteditable composer with **Prompt** and **Lyrics** anchors. Clicking an anchor before pasting correctly targets that region. Clicking the broad contenteditable can focus the wrong region. Verify both visible sections and Auto/Custom state before rendering. Marketplace and history initially maintained distinct drafts; navigating between them preserved their own values. After reload Music commonly returned the history composer.

Research v2.5 rendered supplied Devanagari L1 and L2, brief-only Hindi writing, no-reference fresh composition, same-prompt repeat, reference-guided composition and a6/8 reinterpretation request. All produced saved assets; acoustic success has separate limits in AUDIO_EVALUATION.md.

## From input to editable song

Generate → Loading/disabled controls → saved project/song → Play/Edit Song/Download/favorite. Input prompt and words remain visible. E01 yielded Verse/Chorus/Chorus2 at30s each, expanded style pills and exact input lyrics. E07 generated four blocks32/18/24/16seconds and a recurring textual hook; generated_lyrics.txt records its text and weak lines. Project and song IDs are retained in experiment_log.csv.

Project controls: global and local include/exclude style pills, editable section text, section duration, Mark for regeneration, Add Section, timeline reorder/removal, conversational prompt, variant count, Finetune, History/Favorites, Generate1 more variant, Undo/Redo and Download. Only tested E05 chorus-style regeneration has signal-locality evidence; other controls are observed unless the matrix says otherwise. A passive “composition updated” message can appear on initial project load without an intentional edit; do not treat that message alone as an audio mutation.

E05 changed only the first Chorus styles. New version persisted despite a client-side error. Try again refreshed the page; History had the new Composition plan edited entry. No second submit was needed. Parent audio strongly resembles surrounding revised audio at0ms lag, with no sample-identity claim.

## References and voice

Reference dropdown supports Upload file and retained Uploaded files. First Music upload requires rights/terms acknowledgment; user explicitly approved it. E01's fresh0–30sWAV accepted; Influence slider showed1. Accepted source could be reused without another upload. Existing accepted historical master was not uploaded. No source screening rejection occurred. UI did not expose a copyright-screening trace or internal reference ID.

Finetune selector exposes curated musical/vocal styles; Create opens a form with Music v2 default,1 free Finetune left,≤50tracks,10s–10min/file,≤30MB/file,total1–240min, requiredgenre and workspace sharingoff. No training started. Direct own speech-clone selection was not exposed in inspected Music creation/project routes.

Voice Changer is separate at /app/speech-synthesis/speech-to-speech. Default English v2 must be changed for Hindi; ElevenMultilingual v2 was selectable.15s mixed song converted to built-inRoger, exact 250-credit debit. My voices filters separately yielded no Instant or Professional clone results after loading. Thus no eligible own clone established here. Details and limits: UI-VOICE-FINETUNE.md, UI-E18.md.

## Export, cost and recovery

MP3 exports downloaded and probed; first Music MP3 was44.1kHzstereo192kbps. Menus also offerWAV,MP4,Advanced. Project download popover has Full song, Vocals&Instrumental Generate, and Stems Generate (Vocals,Bass,Drums,Guitar,Piano,Others). Separation was not submitted because no price was exposed in this inspected popover; separation quality/charges unknown. Publishing controls were not used.

Profile balance can be cached. Refresh the Subscription page for reconciliation; avoid resubmission on an unchanged immediate tree. The browser may switch under user activity, in which case refresh state and check history. All output IDs/downloads and billing observations were verified before concluding.

## Limits

No request payload, generation job protocol, browser script execution trace or backend internals observed. UI vocal labels do not establish an identified singer. ASR supports approximate words/recurrence; it cannot establish melody, natural diction or enjoyment. No full stems/extension/local-word-repair/own-voice multilingual claim is promoted from an unrun control.
