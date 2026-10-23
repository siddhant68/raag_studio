# AI music and song pipelines: research sub-agent report

Research checked 23 October 2026. Primary repositories, model cards, product documentation and actual skill files were preferred. No model was installed, no account was created and no audio was generated for this report. Published capabilities below are not listening-test results. The practical recommendation considers the user's accepted original 2:32 Hindi song and rejected recitation-like replacement, as supplied in this session.

## Findings that change our approach

The best immediate experiment is a **small repair to the accepted full-song performance**, followed by listening and splicing only a successful replacement phrase. Whole-song generation and speech synthesis solve different tasks. A more intelligible spoken lyric is not a replacement for a sung phrase with the same melody, timing and emotion.

There are two meaningful new official agent workflows beyond the existing downloaded collection: **YuE2's score-based music skill** and **ElevenLabs' Music API skill**. Neither automatically fixes Hindi pronunciation in the accepted recording. YuE2 regenerates a recording from an editable score; ElevenLabs can preserve referenced audio chunks during inpainting, but uploading our existing recording requires enterprise inpainting access.

Hindi remains the critical gap. A multilingual headline, Hindi TTS support, or an English phonetic-respelling guide does not establish reliable Hindi singing. None of the alternatives reviewed provides a verified, ready-to-use Hindi phoneme editor that can simply repair our accepted vocal while guaranteeing its performance remains identical.

## How the pipelines differ

| Pipeline | What actually creates the singing/music | Control and usual production loop | Fit here |
|---|---|---|---|
| Joint full-song generation | Music model generates voice, melody and accompaniment together | Lyrics and style brief, several takes, select a coherent performance, replace weak sections, stems and final mix | Closest to what the user liked |
| Score-conditioned generation | Editable melody/chord representation followed by semantic/acoustic music synthesis | Compose or transcribe score, verify melody, render a new complete performance | Better inspectable composition; not identical recording preservation |
| Singing voice synthesis | Notes/F0, syllables or phonemes and a voice model | Specify exact notes, lyric alignment and expression; render vocal, arrange accompaniment | Precise in supported languages; Hindi model coverage is a blocker |
| Singing voice conversion | Existing sung performance plus a new timbre model | Keep rhythm/pitch and change voice character | Cannot recover a consonant that was sung incorrectly merely by changing timbre |
| Speech TTS plus backing | Speech engine renders text independently from instrumental composition | Narration/guide voice followed by mixing | Explains clearer words but weak or absent musical phrasing |
| Stem/DAW production | Editing, arrangement, automation and effects process existing recordings | Separate stems, select phrases, time/pitch align, crossfade, mix and master | Finishing and repair infrastructure; not a lyric-to-singing engine |

The descriptions of production loops are a synthesis of the documented editing interfaces below, not a claim that all creators use one universal workflow.

## Local and open model options

### ACE-Step 1.5: improve the existing route before changing engines

The official project supplies MPS support, Python/REST interfaces, text-to-song, cover and local repainting. The optional 5Hz LM plans metadata, lyrics/captions and musical representations before DiT audio synthesis; DiT-only operation is a supported configuration. Current upstream also offers XL 4B DiT variants, distinct from the optional LM. The README's GPU memory recommendations are not measured Apple unified-memory requirements.

Our existing successful take is direct evidence that this installed route can make a pleasing Hindi song. It is not evidence that its pronunciation is reliable. Adding an LM or choosing XL deserves a controlled audition, not a promise of corrected diction. Keep lyrics, style, duration and evaluation criteria fixed when comparing configurations. Capability differs by checkpoint: the model table assigns extract/layer/complete to base variants, not every turbo checkpoint.

Sources: [official repository and model table](https://github.com/ace-step/ACE-Step-1.5), [official documentation](https://github.com/ace-step/ACE-Step-1.5/tree/main/docs), [official skills](https://github.com/ace-step/ACE-Step-1.5/tree/main/.claude/skills). Project license: MIT; check the precise downloaded weight notices as part of deployment. Existing installation details are in the earlier local research, not reinstalled here.

### YuE2: genuine new score-first agent workflow

YuE2 has released code and [3B weights](https://huggingface.co/m-a-p/YuE2-3B), rather than only a paper. Its stages are editable ABC melody/chord planning, semantic generation, acoustic synthesis and waveform decoding. The [official skill](https://github.com/multimodal-art-projection/YuE/blob/main/skills/yue2-music/SKILL.md) supports score editing and musical checks; it explicitly lacks local inpainting and phoneme-alignment APIs. A score edit renders a new full performance, so preserving melody notes does not preserve the accepted waveform or vocal delivery. The official [repository](https://github.com/multimodal-art-projection/YuE) uses Linux/NVIDIA for its quickstart. Code is Apache-2.0; the model card marks weights CC-BY-NC-4.0. Its card tags Chinese/English; a broad multilingual claim does not verify Hindi diction.

A new independent [daig/yue2-mlx](https://github.com/daig/yue2-mlx) port offers a native Mac app/CLI with MLX generation and MPSGraph decoding. It explicitly calls its current native migration experimental, with smoke checks rather than comprehensive fidelity/performance acceptance. Documented validation is an M5 Air 32GB, macOS 26.2+; initial weights are about 7.8GB and setup requires at least 20GB disk. Historical Python timings are not current native benchmarks. This is an experimental candidate for our 48GB Mac, not a validated replacement installation.

### HeartMuLa: alternate complete-song engine, community MLX route

The [official project](https://github.com/HeartMuLa/heartlib) combines a music LM with HeartCodec; it also releases singing transcription components. The independent [heartlib-mlx port](https://github.com/Acelogic/heartlib-mlx) provides CLI/Python/UI operation on Apple Silicon, recommends 32GB+ and converts upstream weights. Its explicit generation-language list is English, Chinese, Japanese, Korean and Spanish. Hindi support and diction remain unverified. Treat it as a new-song audition candidate, not a documented repair tool for our existing performance. Published Mac memory/speed figures are author measurements, not reproduced here. Application code license and model/output rights must be checked separately.

### LeVo2 / SongGeneration v2: useful separation architecture, more setup complexity

The [official LeVo repository](https://github.com/levo-demo/LeVo) describes hierarchical planning and parallel vocal/accompaniment generation, structured lyrics, audio prompts and separate output modes. Its official runtime is CUDA-based; its documented language examples do not establish Hindi. [Community MLX weights](https://huggingface.co/mlx-community/SongGeneration-v2-large) cover the autoregressive token generator, **not the entire audio pipeline**. The model card's decoder instructions use official PyTorch runtime assets with an MPS bridge. BF16 large generator weights alone are about 9.5GB, not total installed size or peak memory. [Community runtime](https://github.com/ailuntx/SongGeneration-MLX). Worth a bounded technical audition later; not the lowest-friction next move. Its model card says license “other”; do not assume unrestricted commercial rights.

### Singing synths and conversions: precise controls, limited Hindi evidence

[SoulX-Singer](https://github.com/Soul-AILab/SoulX-Singer) documents MIDI/F0-conditioned synthesis, lyric/prosody editing and a singing-conversion model. Its named SVS training languages are Mandarin, English and Cantonese. The conversion model's broader language tolerance concerns changing an existing performance's voice; it does not prove Hindi lyric resynthesis. Community MLX ports exist, but this review did not validate end-to-end Mac Hindi generation.

[Synthesizer V's official language list](https://dreamtonics.zendesk.com/hc/en-us/articles/44278346439833-What-languages-are-supported-by-Synthesizer-V-voices) includes English, Japanese, Mandarin, Cantonese, Spanish and Korean across versions, not Hindi. Cross-language phonetic approximation should not be described as native Hindi support. ACE Studio, the separate commercial singing editor, should likewise not be confused with ACE-Step. Hindi-specific [LAPS-Diff research](https://www.ee.iitb.ac.in/course/~daplab/publications/2025/LAPS_Diff.pdf) is relevant, but this search did not establish a released, maintained consumer-ready checkpoint/runtime.

## Managed services and real agent access

| Service | Verified generation/edit workflow | Automation, cost and constraints |
|---|---|---|
| Eleven Music | Complete songs with vocals, structured composition plans and section generation; inpainting can insert stored audio-reference slices unchanged | Official Python/TypeScript/CLI and skill. Paid service; account entitlements apply. Existing-file upload for inpainting is documented as enterprise-only. Hindi singing quality requires an audition |
| Suno | Lyrics/style generation, extend and paid Replace Section; editor/stem workflow | Pro/Premier Replace Section generates two alternatives and a revised full song. No public official self-serve Suno API was verified in the primary docs searched; wrappers on other domains are not official API evidence |
| Udio | Documented lyric/music editing, timeline sessions and upload-based extensions/inpainting | Its official current transition notice says audio, video and stem downloads are disabled. That materially limits an export-to-DAW pipeline. No official public self-serve API was verified |

Eleven's **style reference** and **inpainting reference** are different. Product docs describe the former as production/style guidance rather than copying/remixing a track. Inpainting uses saved song resources and explicit chunks. For a song newly generated there, request storage for inpainting from the start. For our ACE file, check upload entitlement before making any purchase or migration decision. None of these docs establishes that regenerating a region guarantees the same singer, notes and corrected Hindi syllables inside it.

Primary sources:

- [Eleven official music skill](https://github.com/elevenlabs/skills/blob/main/music/SKILL.md), including the enterprise `music.upload` qualification.
- [Eleven API inpainting guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/music/inpainting), [music product/reference explanation](https://elevenlabs.io/docs/eleven-creative/products/music).
- [Suno Replace Section](https://help.suno.com/en/articles/3271873), [Song Editor](https://help.suno.com/en/articles/6141505), [editor/stem production announcement](https://blog.suno.com/blog/songeditor).
- [Udio editing](https://help.udio.com/en/articles/10732667-edit-your-song-music-and-lyrics), [sessions](https://help.udio.com/en/articles/11649525-sessions-udio-s-timeline-editing-view), [official export restriction notice](https://help.udio.com/en/articles/12683565-changes-associated-with-the-universal-music-group-umg-partnership), updated February 2026 and still served at research time.

No exact subscription or per-song price is quoted: feature entitlements, output duration, retries and current plan terms affect cost. Free code does not imply free compute, commercially unrestricted weights or a zero-cost song workflow.

## VoiceStudio's actual role

The inspected [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) current catalog emphasizes speech, cloning/design, dubbing, transcription and agent-facing API/MCP. The existing local review inspected its pronunciation implementation and archived singing proposal. It found word respelling support but no verified current Hindi MIDI/F0-controlled singing repair path; IPA/CMU dictionary rows were not functioning as general phoneme controls in that inspected implementation. Hindi speech coverage is useful for a pronunciation reference, not proof of sung syllable alignment. An archived proposal is not a shipped capability.

Detailed evidence and pinned source links: `../sonic_pi_hindi_20261023/VOICE_STUDIO_REVIEW.md`. [Current engine catalog](https://github.com/debpalash/VoiceStudio/blob/main/docs/engines/README.md), [MCP docs](https://github.com/debpalash/VoiceStudio/blob/main/docs/mcp.md). No VoiceStudio installation is recommended solely to repair this song.

## Skills: what is genuinely new versus already downloaded

See `LOCAL_SKILLS.md` and `SKILLS_INVENTORY.json` for the independently audited existing files. Downloaded instruction files are not installed audio engines, trained voices or listening evaluations.

New primary files found during this search:

1. [YuE2 official music skill](https://github.com/multimodal-art-projection/YuE/blob/main/skills/yue2-music/SKILL.md): actual score generation/editing workflow; requires the runtime and model. Most interesting addition for deliberate composition.
2. [ElevenLabs official music skill](https://github.com/elevenlabs/skills/blob/main/music/SKILL.md): actual paid API methods, section plans and inpainting; requires credentials and feature entitlement. MIT instructions do not make service usage free.
3. [Scenario ACE-Step skill](https://github.com/scenario-labs/skills/blob/main/skills/scenario-ace-step/SKILL.md): cloud MCP routing among separate generate/cover/repaint/layer/extract models; requires Scenario access. It explicitly warns that repaint can change the voice and that high-strength cover does not guarantee words, delivery or timing. Its useful repair recipe is audition alternatives, locate matching boundaries, then splice a verified phrase locally. This is a cloud workflow for ACE-Step, not a new local singing engine.
4. [VoiceStudio official skills](https://github.com/debpalash/VoiceStudio): available for speech/audio workflows and maintenance; useful scope is governed by actual active engines, not the breadth of the skill title.

Existing English pronunciation advice should not be promoted to a Hindi phoneme pipeline. Skill statements such as perfect AI intonation are prompts/opinions, not technical guarantees. No new skill was registered or executed during research.

## Recommended next experiments, in order

**1. Repair the approved take locally.** Freeze the original WAV and its settings. Mark one short unclear phrase with a Hindi listener. Preserve its syllable count, stress, vowel lengths and surrounding lyric context. Audition a small number of ACE cover/repaint candidates using the installed checkpoint's actual API. The parent agent's local documentation inspection confirmed the existing Repaint route takes `src_audio`, `repainting_start`, `repainting_end`, a caption, and `chunk_mask_mode='explicit'` to pass a bounded interval. It exposes conservative/balanced/aggressive choices and boundary crossfades. These are candidate controls, not proof of repaired Hindi or exact retained melody. Compare melody, word clarity, timbre, timing and seam quality against the original. If one passes, transplant only that span with carefully placed crossfades; keep the rest of the original audio. If none passes, report that outcome rather than replacing the whole song with a weaker take. This procedure is an inference from available editing controls; success is not established until listening.

**2. Test future Hindi songs as songs.** Write singable original Hindi lyrics, plan a recurring hook and verse/chorus contrast, and generate voice and arrangement together. Audition optional LM on/off, or a larger DiT, on a short common brief before installing a broad new stack. Use speech only for pronunciation reference. Record model/checkpoint/seed/configuration, lyrics and a listening decision so the winning performance can be revisited.

**3. Explore one deliberate alternative.** For editable music theory and agent composition, audition YuE2 score-first on a supported GPU or the explicitly experimental Mac port; first prove a short Hindi phrase and inspect licensing. For a managed agent workflow, Eleven's official API/skill is concrete, but first confirm Hindi quality and inpainting entitlement. Suno offers a documented browser song-editing workflow if the user chooses a subscription. Udio's export restriction is a practical blocker for our local finishing process.

Sonic Pi remains useful for explicit melodies, chord progressions, rhythmic patterns, transitions and supplemental instrumental stems. Earshot/listening tools help evaluate the resulting audio. Neither supplies a trained Hindi singing model. The missing piece in the rejected hybrid was a coherent sung performance following a shared melody and syllable timeline, not simply another mixing preset.

## Evidence limits

No independent musical-quality ranking is claimed. Publisher speed figures are not measurements of this Mac; an MLX conversion is not automatically a validated full production runtime. Hindi support is called verified only where an explicit relevant capability was established; otherwise it remains an audition question. The accepted local take is the strongest task-specific listening evidence currently available.
