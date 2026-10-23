# M1 caption comparison (AT-M1-10, human check)

Purpose: Siddhant, please read each compiled caption next to the original you accepted and say whether it carries the **same intent**. The compiled captions are what the app would send for the recipe's default plan. Nothing here is a listening test; the compiler is rule-built text only, and nobody has rendered these captions yet.

The verdict lines are left blank on purpose. Only you fill them.

Notes on how the compiler differs from the hand-written originals:

- Slot grammar is fixed (format and lead, lead-priority sentence, tone and techniques, melody, arc, BPM and key, voice tail), so wording order can differ from the originals.
- BPM and key sit near the end as their own sentence (R2 and R3 originals put them first); they are also sent as engine metadata.
- R2 and R3 lose some hand-written colour (R2: the 'resolved piano ending' and 'warm balanced production' phrases; R3: 'intimate low verses' and 'polished spacious mix' in part). R1 is character-for-character identical.
- For R3 the lead instrument is the fingerpicked guitar and the voice is the lead singer; the lead-priority sentence says the voice leads.

## R1 Flute focus (Yamuna at Dawn)

Original (509 characters, `context_pack/recipes/yamuna/request.json`):

> Instrumental Indian bamboo flute solo with gentle tabla, tanpura drone and sparse santoor. Bansuri is the loud clear melodic lead in every section. Rich breathy flute tone, expressive meend pitch slides, delicate grace notes, fluid fast runs, octave turns, lyrical sustained notes with natural breaths. Beautiful recurring melody, tender and luminous. Spacious solo opening, flowing tabla pulse, exposed flute interlude, intricate flute improvisation and peaceful cadence. 82 BPM, D major. Strictly no voices.

Compiled (509 characters, recipe `r1_flute_focus`, nothing dropped):

> Instrumental Indian bamboo flute solo with gentle tabla, tanpura drone and sparse santoor. Bansuri is the loud clear melodic lead in every section. Rich breathy flute tone, expressive meend pitch slides, delicate grace notes, fluid fast runs, octave turns, lyrical sustained notes with natural breaths. Beautiful recurring melody, tender and luminous. Spacious solo opening, flowing tabla pulse, exposed flute interlude, intricate flute improvisation and peaceful cadence. 82 BPM, D major. Strictly no voices.

Metadata equal to the original: BPM 82, key D major, duration 168 s, instrumental=True, language en.

Same intent? (yes / no): ______

Comment: ______

## R2 Warm ensemble with wordless choir (Daylight)

Original (504 characters, `context_pack/recipes/daylight/request.json`):

> Melodious cinematic acoustic pop, 88 BPM, D major. Memorable lyrical piano hook answered by warm flute, fingerpicked acoustic guitar, legato strings, round bass, gentle kick, brushed snare and shaker groove. Tender intimate opening, flowing verse, soaring wordless mixed-choir ooh/aah chorus in close harmony. Quiet piano-and-cello bridge, then a richer final chorus with countermelody. Smooth chord changes, expressive sustained notes, breathing phrases, warm balanced production, resolved piano ending.

Compiled (498 characters, recipe `r2_warm_ensemble`, nothing dropped):

> Melodious cinematic acoustic pop led by a lyrical piano hook with warm flute, fingerpicked guitar, legato strings, round bass and soft groove, with wordless mixed-choir ooh/aah harmonies. Piano is the clear melodic lead in every section. Warm piano tone, smooth chord changes, expressive sustained notes, breathing phrases. Memorable recurring melody, tender and warm. Tender opening, flowing verse, soaring choir chorus, quiet bridge and richer final chorus. 88 BPM, D major. Wordless voices only.

Metadata equal to the original: BPM 88, key D major, duration 132 s, instrumental=False, language en.

Same intent? (yes / no): ______

Comment: ______

## R3 Hindi ballad (Thodi Der Aur)

Original (493 characters, `context_pack/recipes/thodi/request.json`):

> Hindi romantic acoustic pop ballad, 76 BPM, D major, 4/4. Warm expressive male lead singing clear Hindi, intimate low verses and a soaring memorable chorus. Fingerpicked steel-string guitar, felt piano, round bass, brushed drums and swelling strings. Tender longing, sunset warmth, an unspoken confession. Brief guitar intro, verse, rising prechorus, wide chorus, second verse, quiet bridge, fuller final chorus and gentle outro. Vocal forward, natural phrasing, polished spacious mix, no rap.

Compiled (475 characters, recipe `r3_hindi_ballad`, nothing dropped):

> Hindi romantic acoustic pop ballad: warm expressive male lead singing clear Hindi over fingerpicked steel-string guitar, felt piano, round bass, brushed drums and swelling strings. Voice is the clear lead in every section. Soaring memorable chorus melody, tender and yearning, with sunset warmth. Brief intro, rising verse into a wide chorus, quiet bridge, fuller final chorus and gentle outro. 76 BPM, D major. Vocal forward, natural phrasing, polished spacious mix, no rap.

Metadata equal to the original: BPM 76, key D major, duration 152 s, instrumental=False, language hi.

Same intent? (yes / no): ______

Comment: ______
