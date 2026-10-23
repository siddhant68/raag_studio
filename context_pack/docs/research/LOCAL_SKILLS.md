# Local skill inventory

Inspected 23 October 2026. 159 SKILL.md entries across 8 repository snapshots, plus two separate guides.

Downloaded files are distinct from registered plugins, working MCP servers, installed models and tested music quality.

| Repository | Local skill entries | Role |
| --- | ---: | --- |
| ace-step/ace-step-skills | 6 | Local generation wrapper and companion media/transcription workflows |
| bitwize-music-studio/claude-ai-music-skills | 53 | Suno-oriented writing/production/release workflow; generation happens on Suno |
| glincker/ableton-skills | 12 | DAW production procedures requiring a separate Ableton MCP setup |
| jtydhr88/lyric-writing-skills | 17 | Lyric intent, form, imagery and prosody; no Hindi-specific layer |
| jtydhr88/music-composition-skills | 29 | Composition, arrangement and vocal-direction guidance; text only |
| nicholasbien/ableton-mcp-pro | 21 | Ableton MCP code plus production skills; not installed here |
| p-poss/dj-claude | 20 | Strudel/live-code/MCP workflow; not an audio singing model |
| tsirysndr/mixxx-skills | 1 | Custom Mixxx AI-DJ fork instructions; not installed here |

Separate guides: Nous songwriting-and-ai-music and the installed Earshot analysis skill.

## Most relevant existing skills for this user

- `mc-melody`, `mc-vocal-direction`, `mc-arrangement-arch`, `mc-development`: plan melody, expressive delivery and development.
- `lw-song-intent`, `lw-structure`, `lw-imagery`, `lw-rhyme`: write lyrics that fit a concrete song brief.
- `pronunciation-specialist`: Suno-oriented word-risk/respelling guide; predominantly English examples. It is not a Hindi phoneme synthesizer.
- `suno-engineer`, `pre-generation-check`, `lyric-reviewer`: generation prompts and review gates; Suno settings need verification against current official docs.
- `vocal-chain`, `mix-engineer`, `mastering-engineer`: production guidance; processing does not replace wrong consonants.
- `acestep`: actual local-engine integration instructions, adapted here through its official Python API.
- Earshot: measurements and fallible acoustic descriptions, not taste or sung-word validation.

## Reading these files critically

- These are procedure guides, not trained musical judgment or new synthesis engines.
- Some composition skill prose treats AI vocals as always perfectly in tune. That is an unverified generalization, not a constraint to enforce.
- Do not transpose English homograph or Chinese lexical-tone rules into Hindi as if they were language-neutral.
- The ACE lyrics-transcription guide describes correcting ASR text against intended lyrics for captions. Those corrected captions cannot serve as evidence that the audio actually pronounced every word correctly.
- The Bitwize README explicitly says the user generates on Suno; downloading its skills does not provide a Suno API or paid service access.

## All vendor skill names

### ace-step/ace-step-skills

acestep; acestep-docs; acestep-lyrics-transcription; acestep-simplemv; acestep-songwriting; acestep-thumbnail

### bitwize-music-studio/claude-ai-music-skills

about; album-art-director; album-conceptualizer; album-dashboard; album-ideas; clipboard; cloud-uploader; configure; document-hunter; explicit-checker; genre-creator; health-check; help; import-art; import-audio; import-track; lyric-refiner; lyric-reviewer; lyric-writer; mastering-engineer; mix-engineer; new-album; next-step; plagiarism-checker; pre-generation-check; promo-director; promo-reviewer; promo-writer; promote-idea; pronunciation-specialist; release-director; rename; researcher; researchers-biographical; researchers-financial; researchers-gov; researchers-historical; researchers-journalism; researchers-legal; researchers-primary-source; researchers-security; researchers-tech; researchers-verifier; resume; session-start; setup; sheet-music-publisher; suno-engineer; test; tutorial; validate-album; verify-sources; voice-checker

### glincker/ableton-skills

arrangement-coach; chord-pro; groove-builder; mastering-prep; midi-cleanup; mixer-doctor; producer-mode; reference-match; sidechain-setup; sound-designer; tempo-coach; vocal-chain

### jtydhr88/lyric-writing-skills

lw-ai-tell-audit; lw-cantonese; lw-case-studies; lw-chinese-style; lw-english; lw-imagery; lw-japanese; lw-korean; lw-mandarin; lw-musical-theatre; lw-narrative; lw-rap; lw-rhyme; lw-song-intent; lw-structure; lw-tone-check; lw-workflow

### jtydhr88/music-composition-skills

mc-ai-tell-audit; mc-arrangement-arch; mc-case-studies; mc-counterpoint; mc-development; mc-form; mc-harmony; mc-melody; mc-mix-intent; mc-modulation; mc-orchestration; mc-progressions; mc-render-compile; mc-rhythm-groove; mc-rhythm-section; mc-sound-design; mc-style-chinese-pop; mc-style-cinematic; mc-style-citypop-rnb; mc-style-edm; mc-style-hiphop; mc-style-jazz; mc-style-jpop; mc-style-latin; mc-style-rock-band; mc-symbolic-score; mc-texture-layering; mc-vocal-direction; mc-workflow

### nicholasbien/ableton-mcp-pro

acid-bass; ambient; drum-swing; ethereal-pads; growl-bass; hardgroove-bass; hardgroove-drums; house-chords; house-drums; mix-check; mixing-guide; reese-bass; speed-garage; supersaw-chords; synthwave; techno-bass; techno-drums; track-arrangement; trance-bass; trance-melodies; ukg-drums

### p-poss/dj-claude

analyze; browser; conduct; connect; context; export; hush; jam; jam-clear; jam-status; list-saves; live-mix; load; now-playing; play; play-preset; preview; save; strudel; vibe

### tsirysndr/mixxx-skills

mixxx-ai-dj

## Full paths and pinned revisions

See `SKILLS_INVENTORY.json` for all absolute paths, repository paths, revisions, URLs and SHA256 fingerprints.
