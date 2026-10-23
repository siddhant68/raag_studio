# AI music research and our next practical pipeline

Checked 23 October 2026. One research sub-agent investigated models, production pipelines and agent skills; the main agent audited the local installation and downloaded skill collection. This is a source review and local inventory, not a listening benchmark of newly discovered models.

## What this means for our song

The original 2:32 Hindi song, **Thodi Der Aur**, remains our best result because you liked its melody and emotion. The later Sonic Pi hybrid made the words and backing clearer but lost the sung phrasing. We should preserve the accepted recording and test a short unclear phrase before changing an entire song.

The most useful next local experiment is ACE-Step Repaint on one bounded interval. This is already exposed by our installed engine, but we have not established that it can correct Hindi words while preserving this singer and melody. If a replacement passes a listening comparison, splice only that passage into the original. Keep the original if it fails.

## What is available

| Option | How it creates music | Mac and agent access | Practical judgement for us |
| --- | --- | --- | --- |
| **ACE-Step 1.5** | Lyrics/style or source audio to a joint vocal-and-instrumental performance; optional LM planning before audio synthesis | Already installed and used on this Mac; Python API; source repaint available | First choice for a controlled local repair and future full-song takes. Hindi diction remains imperfect |
| **YuE2** | Editable ABC melody/chord score, semantic generation, acoustic synthesis, waveform decoding | Official agent skill; official setup is Linux/NVIDIA. Independent experimental Mac port exists | Interesting for deliberate melody/composition control. Score edits regenerate a complete recording; no official local inpainting API. Weights are noncommercial; Hindi quality unverified |
| **HeartMuLa** | Music language model plus HeartCodec audio generation | Official project; independent `heartlib-mlx` Mac runtime | Alternate full-song audition candidate. Listed languages do not establish Hindi capability |
| **LeVo2 / SongGeneration v2** | Hierarchical planning and parallel vocal/accompaniment generation | Official CUDA setup; community MLX generator with PyTorch/MPS decoding bridge | Potential stem/control benefits, more setup. Community generator weights are not the complete runtime; Hindi unverified |
| **Eleven Music** | Prompt or structured composition plan to complete songs; section editing/inpainting | Official API, SDKs and music skill; paid service | Concrete managed agent workflow. Uploading our existing song for inpainting requires enterprise entitlement; Hindi needs an audition |
| **Suno** | Lyrics/style to complete performances; extend and replace sections | Browser/editor; no public official self-serve API verified in this research | Paid Pro/Premier section replacement is documented. Community skill files do not grant API access |
| **Udio** | Full-song generation with lyric/music editing and timeline tools | Browser service; no official public self-serve API verified | Current official notice says audio/video/stem downloads are disabled, limiting our local finishing workflow |
| **SoulX-Singer / Synthesizer V** | Notes or F0 and aligned syllables/phonemes to sung vocals | Different runtimes and language-specific voice support | Useful control in supported languages. A ready Hindi melody-preserving correction path was not established |
| **VoiceStudio, debpalash** | Speech, voice design/cloning, dubbing and transcription workflows | Agent-facing API/MCP documented; not installed here | Useful speech infrastructure. Current evidence does not establish dependable Hindi singing repair |
| **Sonic Pi + DAW/audio tools** | Explicit notes, rhythms and arrangements; editing and mixing existing performances | Sonic Pi, FFmpeg, Rubber Band and separation already available | Good for backing, transitions and finishing. Needs a singing model or actual sung performance for melodic vocals |

Sources: [ACE-Step](https://github.com/ace-step/ACE-Step-1.5), [YuE2](https://github.com/multimodal-art-projection/YuE), [experimental YuE2 Mac port](https://github.com/daig/yue2-mlx), [HeartMuLa](https://github.com/HeartMuLa/heartlib), [HeartMuLa Mac port](https://github.com/Acelogic/heartlib-mlx), [LeVo](https://github.com/levo-demo/LeVo), [SongGeneration MLX](https://github.com/ailuntx/SongGeneration-MLX), [MLX model/decoder instructions](https://huggingface.co/mlx-community/SongGeneration-v2-large), [Eleven official skill](https://github.com/elevenlabs/skills/blob/main/music/SKILL.md), [Suno section editing](https://help.suno.com/en/articles/3271873), [Udio export restriction](https://help.udio.com/en/articles/12683565-changes-associated-with-the-universal-music-group-umg-partnership), [SoulX-Singer](https://github.com/Soul-AILab/SoulX-Singer), [Synthesizer V languages](https://dreamtonics.zendesk.com/hc/en-us/articles/44278346439833-What-languages-are-supported-by-Synthesizer-V-voices), [VoiceStudio](https://github.com/debpalash/VoiceStudio).

## How a useful production pipeline works

These are practical patterns synthesized from the documented tools, not a claim that every creator uses the same process.

**Complete generated song:** write singable lyrics and a style/structure brief, generate several coherent performances, select the strongest hook and delivery, replace weak sections, then separate stems if needed and mix/master. This is closest to the approach that produced the song you liked.

**Composition first:** plan melody, harmony, rhythm and syllable placement in a score, render it through a score-conditioned song model or supported singing synthesizer, then arrange and finish. YuE2 makes part of this plan inspectable through ABC notation. Note preservation does not guarantee identical vocal delivery or audio.

**Existing-song repair:** mark a short problem region, condition a replacement on the original context or melody, audition alternatives, align a successful phrase and splice it into the original. Inpainting can change the voice or phrasing inside the region. Keeping only the verified replacement span lets us preserve the rest of the original audio.

**Voice conversion:** start with an already sung performance and change its timbre. This can preserve pitch and timing, but changing voice character alone does not fix a consonant that the original singer pronounced incorrectly.

**TTS over backing:** creates speech unless the engine has actual singing controls. Clear pronunciation and a pleasant instrumental do not establish a shared vocal melody. This distinction explains the limitation of our rejected hybrid; it does not isolate one cause of that result.

## Skills already downloaded

The audit found **159 distinct vendor SKILL.md files across eight repository snapshots**, plus the standalone Nous songwriting guide and Earshot skill. Some entries are utility, research or release workflows rather than music-generation skills.

| Collection | Files | Most relevant use |
| --- | ---: | --- |
| ACE-Step skills | 6 | Actual generation integration, songwriting and companion workflows |
| Bitwize music studio | 53 | Lyrics, review, Suno prompts, mixing/mastering and release procedures |
| Glincker Ableton skills | 12 | Arrangement, groove, chords, vocal chain and mixing procedures |
| Lyric-writing skills | 17 | Intent, imagery, form, rhyme and language-specific writing guidance |
| Music-composition skills | 29 | Melody, harmony, orchestration, development and vocal direction |
| Ableton MCP Pro | 21 | DAW production procedures; separate integration required |
| DJ Claude | 20 | Strudel/live-coded music and DJ workflows |
| Mixxx skills | 1 | Custom Mixxx AI-DJ integration instructions |

Useful existing names include `mc-melody`, `mc-vocal-direction`, `mc-arrangement-arch`, `lw-song-intent`, `lw-structure`, `lyric-writer`, `pronunciation-specialist`, `suno-engineer`, `mix-engineer` and `mastering-engineer`.

These are instruction files. Downloading them does not install their runtime, connect a DAW or add a trained singing voice. The pronunciation guide is mostly English/Suno-oriented; it is not a Hindi phoneme synthesizer. Earshot gives measurements and fallible acoustic descriptions, not a reliable judge of taste or sung-word correctness.

See [LOCAL_SKILLS.md](LOCAL_SKILLS.md) for every skill name and [SKILLS_INVENTORY.json](SKILLS_INVENTORY.json) for exact local paths, source revisions, URLs and content hashes.

## New skill files worth considering

1. **[Official YuE2 music skill](https://github.com/multimodal-art-projection/YuE/blob/main/skills/yue2-music/SKILL.md):** reproducible generation, editable scores, melody/reharmonization checks and listening comparisons. Requires the actual engine and weights; full recording regeneration rather than local phrase inpainting.
2. **[Official ElevenLabs music skill](https://github.com/elevenlabs/skills/blob/main/music/SKILL.md):** structured composition, song resources and inpainting through a documented paid API. Existing-song upload entitlement must be checked before choosing it for this recording.
3. **[Scenario ACE-Step skill](https://github.com/scenario-labs/skills/blob/main/skills/scenario-ace-step/SKILL.md):** cloud generate/cover/repaint routing with useful warnings about voice changes and a listen-then-splice repair method. Requires Scenario access; not a new local singing model.

No new skill was installed or globally registered during this research.

## What to do next, and what it would cost

**First:** keep the accepted song and try one short ACE repaint. Compare the original and candidate for Hindi word clarity, melody, timing, emotion, voice identity and audible seams. Corrected captions or favorable loudness measurements cannot substitute for this comparison.

**For new Hindi songs:** use joint song generation, with a recurring melodic hook and contrasting sections. Optional ACE LM planning or a larger model can be compared on a common brief, but neither is an established pronunciation fix. Our installed weights are turbo DiT, VAE and the Qwen embedding model; the separate 5 Hz music LM is absent. The embedding model is not that LM.

**For a new platform:** audition one alternative before broad installation. YuE2 is compelling for score control, with runtime/licensing limits. Eleven provides a concrete managed API, with paid access and existing-audio upload constraints. Neither has passed a Hindi listening test here.

Existing local inference has no per-song API charge, but uses the Mac's time, power and storage. Cloud services charge under their current plan/usage rules, and retries affect cost. Code licences, model-weight licences and service/output terms are separate. This research did not run paid jobs, download new models or create new audio.

## Files in this package

- `AI_MUSIC_RESEARCH.md`: this practical overview.
- `RESEARCH_AGENT.md`: detailed sub-agent findings with primary sources and evidence limits.
- `LOCAL_SKILLS.md`: complete skill-name inventory and relevant cautions.
- `SKILLS_INVENTORY.json`: machine-readable paths, pinned sources and hashes.
- `LOCAL_SETUP_AND_LESSONS.md`: what is installed/tested and which results you accepted or rejected.
- `earlier_guides/`: preserved earlier installation/research and VoiceStudio notes. These are historical records, not a recommendation to rerun every installation. Relative paths inside them refer to their original project locations.

The package contains reports and inventory, not audio recordings, model weights or copies of every third-party skill. The inventory links to the existing local files and their upstream sources.
