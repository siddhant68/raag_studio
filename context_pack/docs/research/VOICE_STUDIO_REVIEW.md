# VoiceStudio and Hindi singing pronunciation

Inspected 23 October 2026, repository `debpalash/VoiceStudio`, commit
`f3d685ac293d9423a85c82c629c931e7da5c7a7b`. This is research, not an installed
or tested VoiceStudio integration.

Findings:

1. The current feature catalog and engine guide focus on speech generation,
   voice cloning/design, dubbing, transcription and vocal isolation. Apple
   Silicon MPS and an agent-facing local MCP/API are documented. These are
   relevant capabilities for narration, dialogue and spoken lyric guides.
2. Its default OmniVoice engine is documented as TTS. Broad language coverage
   does not establish equally accurate Hindi singing or melody control.
3. The inspected pronunciation implementation applies per-language/global
   word respellings before synthesis. Its own `inert_entries_for_language`
   function and regression tests state that IPA/CMU dictionary rows currently
   are not applied as phoneme controls. Inline engine-specific controls are
   a separate capability; OmniVoice's guide documents Chinese pinyin and
   English CMU markup, not an established Hindi phoneme editor.
4. An archived singing-design document exists. It explicitly says the early
   OmniVoice-singing option lacked F0/MIDI conditioning and could not preserve
   a source song's melody; it points to a superseding historical SoulX plan.
   The current engine catalog and inspected active dubbing files did not
   establish a usable Hindi melody-preserving singing-repair path. Do not
   mistake that archived proposal or the phrase “feature shipped” for current
   verified Hindi singing support.
5. Voice conversion or separating vocals does not, by itself, replace incorrect
   sung consonants. This is an inference from the roles of those operations.
   The existing song would need a correctly pronounced replacement performance
   or a suitable singing editor that can regenerate syllables while preserving
   melody and timing.

Recommendation: VoiceStudio is worth considering for local Hindi speech and
pronunciation-reference work, with actual listening tests. Do not install its
multi-GB model stack solely on the assumption that it will automatically repair
this song. Its value for this specific singing task remains untested. No model
installation or voice cloning was performed as part of this research.

Primary sources:
- https://github.com/debpalash/VoiceStudio
- https://github.com/debpalash/VoiceStudio/blob/main/docs/feature-catalog.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/README.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/omnivoice.md
- https://github.com/debpalash/VoiceStudio/blob/main/docs/mcp.md
- https://github.com/debpalash/VoiceStudio/blob/f3d685ac293d9423a85c82c629c931e7da5c7a7b/backend/services/pronunciation.py
- https://github.com/debpalash/VoiceStudio/blob/f3d685ac293d9423a85c82c629c931e7da5c7a7b/tests/test_pronunciation_inert_1949.py
- https://github.com/debpalash/VoiceStudio/blob/f3d685ac293d9423a85c82c629c931e7da5c7a7b/docs/adr/SPIKE-02-singing.md

Selected source files are preserved unchanged in `voicestudio-research/` with
the repository revision and upstream licence notices. They were read, not run.
