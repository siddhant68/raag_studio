# Public and source evidence notes

Inspected 24 October 2026 (India time). No authenticated account data, cookies, credentials, voice samples or audio were collected by this parallel track.

`IDENTITY.json` records correct VoiceStudio repository and pinned commit. `voicestudio-tree.json` is the complete returned GitHub recursive tree (`truncated: false`, 4,213 entries). `source-manifest.json` records hashes for immutable selected upstream files, including original licence notices. Source was read, not executed. Filename searches for singing/SoulX are bounded inventory searches; code reads cover the recorded conversion, TTS registry, pronunciation and dubbing files.

Official documentation was retrieved successfully through the supported web tool on the URLs linked in `../VOICE_AND_LANGUAGE_FINDINGS.md`. A separate ordinary HTTP attempt to archive `.md` pages received HTTP 403 for all seven URLs. No retry or bypass was attempted; `official-source-manifest.json` is empty because no source bytes were downloaded. The report links to the observed public pages rather than claiming preserved official HTML. The successful browser-independent web observations and extracted claims are summarized below.

| Source | Observation |
| --- | --- |
| PVC product guide | Spoken training only; explicit singing exclusion |
| Music compose API | `music_v1`, `music_v2`, `music_v2_5`, `finetune_id`; no inspected speech `voice_id` field |
| Music Finetunes guide | Dataset-derived musical/vocal style; language directed by prompt; separate upload/training workflow |
| Voice Changer capability/API/product guides | Hindi and cloned/designed output voices; source-audio performance transfer; no inspected F0/MIDI guarantee for singing |
| Singing Voice Changer marketing page | Singing and multilingual marketing claim; not an experimental result |

The existing 23 October VoiceStudio review was read as historical comparison only; no Raag Studio files were edited.
