# Raag Studio API notes (M2, for the frontend milestone)

Base: `http://127.0.0.1:8477` (JSON, localhost only). Interactive schema at `/api/docs`.
The web UI is served from `app/web/` at `/` (a placeholder page appears only if that folder does not exist).

## Conventions

- Ids are 26-character ULIDs. Times are UTC ISO-8601 with `Z`.
- **Every JSON body carries `"engine"`**: `"real"` or `"fake"`. Objects about a job/take/export carry their own value
  (a take made by the fake test engine always says `"fake"`, plus a `notice`). Show a loud banner when `engine == "fake"`.
- Errors: `{"error": {"code": "...", "message": "human text", ...extra}, "engine": "..."}`.
  Statuses used: 400 `confirm_required`, 403 `forbidden_origin`, 404 `*_not_found` / `not_found`, 409 `not_cancellable`
  / `native_pruned`, 410 `audio_missing`, 422 `invalid_request` / `invalid_controls` / `invalid_plan` /
  `needs_user_input` / `nothing_to_change` / `over_budget` / `invalid_tags` / `invalid_trim`, 429 `queue_full`,
  501 `experimental_not_enabled`, 507 `insufficient_disk`. Show `message` to the person as is.
- Writes that start a render (`POST /api/songs`, `POST /api/songs/{id}/rounds`) are idempotent: send header
  `Idempotency-Key: <uuid>` (or `idempotency_key` in the body). A repeat returns the same job with `"replayed": true`
  (still 202). Generate one UUID per button press so a double click cannot start two renders.
- Only requests with no `Origin` header, or `Origin: http://127.0.0.1:8477` / `http://localhost:8477`, may POST/PUT/PATCH.
  Host must be `127.0.0.1` or `localhost`.
- Nothing is auto-ranked. `technical_checks` are breakage checks, labelled as such; never show them as quality.

## Create and plan

`POST /api/songs` -> **202**

```json
{ "brief": "A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes",
  "voice": "instrumental|wordless|sung|auto", "duration": 120, "takes": 3,
  "recipe": "r1_flute_focus", "lyrics": "exact user words (voice sung)",
  "shape": { "lead": "bansuri", "instruments": ["tabla","tanpura"], "feeling": ["peaceful"], "pace": "slow",
             "bpm": 80, "key": "D major", "fullness": "spare", "arc": "slow_build", "style": "singing",
             "avoid": ["crowded accompaniment"], "singer": "female", "background": "light", "language": "hi" },
  "plan": null, "title": null }
```

Only `brief` is required (blank -> 422). All other fields are optional (Auto). `controls` is an alias of `shape`.
Passing a full `plan` skips the planner. Unknown keys and unknown instrument ids are 422.
Choir (instrument id `choir`, lead or support) is voices: with Voice Auto it makes the piece `wordless` (provenance
`suggested`, reason names the choir pick). With Voice explicitly `instrumental` the choir is dropped and the user is told
(`card.notes` and a `compile_report.conflicts` entry of kind `instrumental_with_choir`; a choir lead is replaced by the
recipe's lead for the caption). A choir never yields "Strictly no voices." next to a choir lead.

```json
{ "song_id": "01M5...", "round_id": "01M5...", "job_id": "01M5...", "plan_id": "01M5...", "plan_rev": 1,
  "plan": { "schema_version": "2.0", "voice_mode": "instrumental", "duration_s": 120, "takes": 3,
            "lead": {"instrument":"bansuri","style":"singing"}, "supports": [{"instrument":"tabla","role":"rhythm","presence":"gentle"}],
            "provenance": {"voice_mode": {"source":"suggested","reason":"you wrote 'no singing'"}}, "...": "..." },
  "card": { "provider": "basic", "provider_label": "Basic planner", "is_llm": false, "fallback": false,
            "matched": ["no singing","bansuri"], "notes": ["..."], "unsupported": [], "needs_user_input": [] },
  "compile_report": { "char_count": 482, "dropped": [], "warnings": [], "conflicts": [], "slots": [["opening","..."]] },
  "seeds": [41189026, 229770212, 150836115],
  "job": { "...see Jobs...": "state queued" }, "engine": "real" }
```

`POST /api/songs/{id}/plan` (body: optional `brief` and the same controls) -> 200
`{song_id, plan_id, plan_rev, plan, card, compile_report, compile_error}`; stores a new plan revision, renders nothing.
`compile_error` is set (with `code`, `message`) instead of failing, e.g. sung words with no lyrics (`needs_user_input`).

`PATCH /api/songs/{id}/controls` body = any subset of the control keys above (`null` = back to Auto) -> 200
`{song_id, plan_id, plan_rev, plan, changes, compile_report, compile_error}`; new revision, source `user_edit`, touched
fields get provenance `you`. Does not render; the next round uses the latest revision. Keys are the `Controls` names
(`voice, duration_s, takes, recipe_id, lead, instruments, feeling, pace, bpm, key, fullness, arc, style, avoid, singer,
background, language, lyrics_text`); an unknown key (also with `null`) is 422 `invalid_controls`.

- **`null` resets a control to Auto.** The stored control is removed and that field of the plan is recomputed the way the
  planner would choose it for the brief and the controls that are still set (pace bucket and BPM, lead and style, and
  singer/background/language each feed shared plan fields, so the one still set keeps its value). Provenance becomes the
  recomputation's (`suggested`, `recipe` or `rule`, never `you`), and the next round uses the reset value. Other fields,
  including chip changes, are untouched.
- **Choir is voices.** Picking choir as `lead` or in `instruments` while Voice is Auto (no `voice` control) makes the voice
  mode `wordless` (provenance `suggested`, reason names the choir pick) with background voices `choir`; removing the pick
  puts the voice mode back to Auto. With Voice explicitly Instrumental the choir is dropped and reported (see below).

### "What changed": one entry schema

Every producer of changes returns the same entries, in `card.changes` (stored with the plan, so `GET /api/songs/{id}`
`plans[].card.changes` has them), in the refine response `card.changes`, and in the PATCH response `changes`:

```json
{ "field": "fullness", "from": "balanced", "to": "spare", "source": "chip" }
```

- `field`: a plan field, dotted for a sub-field: `voice_mode lyrics duration_s takes recipe_id lead lead.style supports
  feeling pace key fullness arc avoid voices.singer voices.background voices.language` (`flavour` from a smart planner).
- `from` / `to`: plain JSON values, `null` = no value (show "Auto"). `lead` is an instrument id, `supports` a list of
  instrument ids, `pace` a BPM number, `feeling`/`avoid` lists of words; never display names.
- `source`: `chip` (a quick-change chip), `you` (the person's own edit or typed request; a smart-planner free-text change
  is `you`), `rule` (recomputed automatically, e.g. a reset to Auto). For PATCH it is `you` while the field's resulting
  provenance is `you`, otherwise `rule`.
- Producers: the Basic planner's chips, the smart planners' free-text patch, and `PATCH /controls` (a field-by-field
  difference of the old and new plan). The plan-only endpoint reports no changes. Older stored plans may still hold
  `{field, from, to, chip}` or a plain list of field names; `app/web/js/logic.js formatChange` reads those too.

## Rounds (more takes)

`POST /api/songs/{id}/rounds` -> **202**, same response shape as create.

| body | meaning |
| --- | --- |
| `{"kind":"another","takes":3}` | same latest plan, new random seeds. With `from_take`, the plan that take was made from instead |
| `{"kind":"refine","chips":["less_busy"],"from_take":"<take id>"}` | `chips`: `less_busy more_melodic slower livelier warmer brighter different_lead more_voices fewer_voices`; also accepts `request_text`/`patch` (text containing chip words). New plan revision + new takes; the round stores `parent_take_id`. Show `card.notice`: "These are new performances from an updated plan..." |

**Base plan of a round.** Without `from_take` the base is the song's newest plan revision. With `from_take` it is the plan
of the round that made that take (take -> round -> plan; a take of another song is 404 `take_not_found`), so refining an
older take does not inherit later edits. The chip patch is applied to that plan, which keeps its own controls and
provenance; the result is stored as a NEW revision numbered after the song's newest one (revisions stay monotonic).
| `variation`, `cover`, `repaint` | **501** `experimental_not_enabled` ("... experimental and not enabled ...") |

If nothing could be applied (free text the Basic planner cannot parse): 422 `nothing_to_change` with `unsupported[]`.

## Songs

`GET /api/songs` -> `{"songs":[{id,title,brief,created_at,archived,take_count,favourite_count,latest_job:{id,state,engine}}]}`

`GET /api/songs/{id}` -> `{song, plans[], rounds[], takes[], exports[]}`

- `plans[]`: `{id, rev, source (rules|user_edit|...), plan, card, controls, provenance, brief_sha256, created_at}`
- `rounds[]`: `{id, kind, plan_id, parent_take_id, request_text, created_at, job, take_ids[], request:{id, sha256, lyrics_sha256, seeds[], caption, engine_request, compile_report}}`
- `takes[]` (flat, group by `round_id`, sort by `ordinal`): see Take.
- `exports[]`: see Export.

## Jobs

`GET /api/jobs/{id}`

```json
{ "id": "...", "round_id": "...", "song_id": "...", "kind": "create",
  "state": "queued|running|succeeded|failed|cancelled", "phase": "queued|waiting|starting|loading_model|rendering|checking|retrying|done|failed|cancelled",
  "progress": { "take_index": 2, "takes_total": 3, "takes_completed": 1, "model_load_s": 8.6, "last_take": {"index":1,"seed":41189026,"duration_s":120.0,"wall_s":17.9} },
  "reason": null, "error": null, "attempts": 1, "worker_pid": 12345, "engine": "real",
  "elapsed_s": 31.2, "cancel_requested": false, "queued_at": "...", "started_at": "...", "finished_at": null, "take_ids": [] }
```

- Progress strip: `queued -> loading_model -> rendering (take_index/takes_total) -> checking -> done`.
- `state: "queued"` with `phase: "waiting"` and `reason: "mac_busy"` means the video generator is busy; the job starts by
  itself when it is idle (`progress.message` has a sentence for the UI). `reason: "video_queue_unknown"` is similar.
- `failed`: `error` is a human sentence. The UI offers a manual "Try again" (a new round); there is no auto loop.
  A server restart mid-render re-queues once (`attempts` 2) and then fails with "Interrupted by a restart ...".
- On success, `progress.technical_failures` lists ordinals that failed the breakage checks even after the one automatic
  retry (`progress.retry` describes the retry).

`POST /api/jobs/{id}/cancel` -> job JSON with `state: "cancelled"` (queued: immediately; running: the engine process is
killed, response returns within about 5 s). 409 if already finished.

## Events (SSE)

`GET /api/events` (`text/event-stream`, supports `Last-Event-ID` replay of the last 200 events; keep-alive comments).

| event | data |
| --- | --- |
| `hello` | `{engine, version, queue:{queued,running,depth,cap,running_job_id}}` (first frame) |
| `job` | the full job JSON on every phase/state change |
| `take_done` | `{job_id, index, seed, duration_s, wall_s, engine}`: the engine finished a take (rows appear after checking) |
| `takes_ready` | `{job_id, round_id, engine, takes:[Take...]}` after checks and previews; the take list to show |
| `feedback` | `{take_id, song_id, favourite, rating}` |

## Takes and audio

Take (also `GET /api/takes/{id}`):

```json
{ "id": "...", "round_id": "...", "song_id": "...", "ordinal": 1, "label": "T1", "seed": 41189026,
  "duration_s": 120.0, "sample_rate": 48000, "channels": 2, "engine": "real", "engine_rev": "ace-step-1.5.0/acestep-v15-turbo/run_takes-e5637396",
  "retry_of": null, "audio_url": "/api/takes/<id>/audio", "native_url": "/api/takes/<id>/audio?kind=native",
  "native_available": true, "native_pruned_at": null, "native_sha256": "...",
  "requested_params": {"guidance_scale": 7.0, "seed": 41189026, "caption": "...", "...": "..."},
  "effective_params": {"guidance_scale": 1.0, "seed": 41189026, "...": "..."},
  "timings": {"wall_s": 17.9, "pipeline_s": 11.5, "model_load_s": 8.6, "preview_s": 0.9, "peak_rss_mb": 14136.9},
  "technical_checks": { "label": "Technical checks (breakage only, not a quality score)", "status": "passed|warning|failed",
      "failures": [], "warnings": ["silence"], "checks": {"duration": {"ok": true, "value": 120.0, "limit": "120.0 +/- 0.25 s", "severity": "failure"}},
      "facts": {"silence_fraction": 0.022, "true_peak_dbtp": -1.3, "integrated_lufs": -20.9, "clipped_fraction": 0.0} },
  "favourite": false, "rating": null, "tags": [], "note": null,
  "feedback_events": [{"kind":"favourite","value":true,"created_at":"..."}] }
```

- Silence is a **warning** (>= 5 % of the take) and a failure only above 40 %. A `failed` take is kept and shown flagged;
  its automatic replacement has `retry_of = <failed take id>` and the same `ordinal`.
- `GET /api/takes/{id}/audio?kind=preview|native`: HTTP Range supported (206, `Content-Range`, `Accept-Ranges: bytes`);
  preview is MP3 192 kbps (default), native is the engine FLAC. 410 `audio_missing` if the native file was pruned.
- `POST /api/takes/{id}/feedback`: `{"favourite": true, "rating": "love|fine|no", "tags": ["melody","voice"], "note": "..."}`
  (any subset, at least one). Tags: `melody instrument voice rhythm diction` + `too busy`, `too plain`, `wrong mood`.
  Append-only: the response is the take with its current `favourite/rating/tags/note` (latest event wins) and the
  full `feedback_events` history. Un-hearting is `{"favourite": false}`.

## Export

`POST /api/takes/{id}/exports` body `{"format":"mp3|wav","end_fade_s":0..8,"trim_end_s":0..}` -> **201**

```json
{ "id": "...", "take_id": "...", "format": "wav", "fade_out_s": 2.0, "trim_end_s": 0.0, "sha256": "...",
  "url": "/api/exports/<id>/file", "filename": "My-song_T1_s41189026.wav", "engine": "real", "notice": null,
  "loudness": { "target": {"integrated_lufs": -16.0, "true_peak_dbtp": -1.5, "lra": 11.0},
                "input": {"integrated_lufs": -20.91, "true_peak_dbtp": -1.3, "lra": 5.4},
                "output": {"integrated_lufs": -15.9, "true_peak_dbtp": -1.5, "lra": 5.8, "measured_by": "ffmpeg ebur128 on the written file"},
                "two_pass": true, "normalization_type": "dynamic", "duration_s": 120.0, "sample_rate": 48000, "codec": "pcm_s24le" } }
```

WAV is 24-bit 48 kHz; MP3 is 320 kbps 48 kHz. `GET /api/exports/{id}/file` downloads it (Content-Disposition set).
The native file is never modified. Exports of fake-engine takes keep `engine:"fake"`, a `notice`, a `_FAKE` file name and a
FAKE tag inside the file. 409 `native_pruned` if the native audio was pruned.

## System, settings, admin

- `GET /api/system` -> `{version, engine, engine_rev, mps (true|false|null for fake), mps_detail, disk_free_gib, min_disk_gib, video_queue:{state:idle|busy|unknown,running,pending,detail}, planner_provider (effective), planner_setting, planner_smart_enabled, queue:{queued,running,depth,cap,running_job_id}, capabilities:{controls,capability_rows,controls_by_class,source}, ace_python}`.
  The first call in real mode probes MPS (a few seconds); cached for 2 minutes.
- `GET /api/settings` / `PUT /api/settings` (partial update) -> `{"settings": {...}}`. Keys: `planner_provider` (basic|claude_cli|anthropic_api),
  `planner_smart_enabled` (false; a smart provider runs only if the user turns this on), `min_disk_gib` (5), `queue_depth_cap` (5),
  `video_queue_url` (local http URL), `silence_warn_fraction` (0.05), `silence_fail_fraction` (0.40),
  `retry_on_technical_failure` (true), `job_timeout_s` (1800).
- `POST /api/admin/prune` `{"older_than_days": 14, "confirm": true}` -> `{pruned, pruned_take_ids, skipped_favourites, freed_bytes}`.
  `confirm` must be `true` (400 otherwise). Removes native audio of non-favourite takes older than N days; previews and all rows stay.
- Submitting with less than `min_disk_gib` free is rejected with 507 `insufficient_disk`; more than `queue_depth_cap` active jobs gives 429.

## Hooks for later milestones

- Planner: `Service.planner()` (jobs.py) calls `providers.registry.get_planner(settings)`; it is Basic unless the user sets
  `planner_provider` AND `planner_smart_enabled: true`.
- Experimental round kinds (`variation|cover|repaint`) return 501 in one place: `Service.create_round`.
- DB columns beyond PRD section 7: `jobs.engine`, `jobs.cancel_requested`, `takes.engine`, `takes.native_sha256`,
  `takes.retry_of`, `takes.native_pruned_at`, `exports.engine`.
