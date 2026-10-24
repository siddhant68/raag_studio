"""Instrument vocabulary for the song pipeline.

The classic compiler (`compiler.INSTR`) knows the original 15 instruments and stays unchanged so the accepted
recipes compile byte-for-byte as before. This table is the wider vocabulary used by the song pipeline
(`song_compiler`) and the planners. Every entry says how to name the instrument in an ACE-Step caption, which
role it usually plays, whether it can carry a melody, the tag used for its solo section, and the words people use
for it in a brief (English, Roman Hindi, Devanagari).

Caption words were chosen to match ACE-Step's own genre/instrument vocabulary where possible.
"""
from __future__ import annotations

from typing import Optional

CLASSIC_IDS = (
    "bansuri", "tabla", "tanpura", "santoor", "sitar", "ghatam", "violin", "cello",
    "strings", "piano", "acoustic_guitar", "bass", "light_percussion", "choir", "harmonium",
)


def _i(name: str, caption: str, family: str, *, lead: bool = True, solo: Optional[str] = None,
       role: str = "texture", lead_caption: Optional[str] = None, aliases: tuple[str, ...] = (),
       indian: bool = False) -> dict:
    return {"name": name, "caption": caption, "lead_caption": lead_caption or caption, "family": family,
            "can_lead": lead, "solo_tag": solo, "role": role, "aliases": list(aliases), "indian": indian}


# family: melodic | harmony | rhythm | bass | drone | voices | texture
INSTRUMENTS: dict[str, dict] = {
    # --- the classic 15 (aliases mirror planner_rules.INSTRUMENT_ALIASES) ------------------------------
    "bansuri": _i("Bansuri", "bansuri bamboo flute", "melodic", solo="Flute Solo", role="answer", indian=True,
                  lead_caption="expressive bansuri bamboo flute melody"),
    "tabla": _i("Tabla", "tabla", "rhythm", lead=False, solo="Tabla Solo", role="rhythm", indian=True),
    "tanpura": _i("Tanpura", "tanpura drone", "drone", lead=False, role="drone", indian=True),
    "santoor": _i("Santoor", "shimmering santoor", "melodic", solo="Santoor Solo", indian=True),
    "sitar": _i("Sitar", "sitar", "melodic", solo="Sitar Solo", indian=True, lead_caption="resonant sitar melody"),
    "ghatam": _i("Ghatam", "ghatam clay pot percussion", "rhythm", lead=False, role="rhythm", indian=True),
    "violin": _i("Violin", "violin", "melodic", solo="Violin Solo", role="answer",
                 lead_caption="singing violin melody"),
    "cello": _i("Cello", "cello", "melodic", solo="Cello Solo", role="harmony"),
    "strings": _i("Strings", "lush string section", "harmony", solo="String Interlude", role="harmony"),
    "piano": _i("Piano", "piano", "harmony", solo="Piano Interlude", role="harmony",
                lead_caption="expressive piano melody"),
    "acoustic_guitar": _i("Acoustic guitar", "fingerpicked acoustic guitar", "harmony", solo="Guitar Solo",
                          role="harmony"),
    "bass": _i("Bass", "warm bass", "bass", lead=False, role="harmony"),
    "light_percussion": _i("Light percussion", "light percussion", "rhythm", lead=False, role="rhythm"),
    "choir": _i("Choir", "choir", "voices", solo=None, role="harmony"),
    "harmonium": _i("Harmonium", "harmonium", "harmony", solo="Harmonium Solo", role="drone", indian=True),
    # --- Indian ------------------------------------------------------------------------------------------
    "sarangi": _i("Sarangi", "sarangi", "melodic", solo="Sarangi Solo", role="answer", indian=True,
                  aliases=("sarangi", "सारंगी")),
    "shehnai": _i("Shehnai", "shehnai", "melodic", solo="Shehnai Solo", role="answer", indian=True,
                  aliases=("shehnai", "shehnaai", "shenai", "शहनाई")),
    "sarod": _i("Sarod", "sarod", "melodic", solo="Sarod Solo", indian=True, aliases=("sarod", "सरोद")),
    "veena": _i("Veena", "veena", "melodic", solo="Veena Solo", indian=True, aliases=("veena", "vina", "वीणा")),
    "dholak": _i("Dholak", "dholak", "rhythm", lead=False, solo="Percussion Break", role="rhythm", indian=True,
                 aliases=("dholak", "dholki", "ढोलक", "ढोलकी")),
    "dhol": _i("Dhol", "punchy dhol drums", "rhythm", lead=False, solo="Dhol Break", role="rhythm", indian=True,
               aliases=("dhol", "ढोल")),
    "mridangam": _i("Mridangam", "mridangam", "rhythm", lead=False, solo="Percussion Break", role="rhythm",
                    indian=True, aliases=("mridangam", "mridanga", "मृदंगम", "पखावज", "pakhawaj")),
    "tumbi": _i("Tumbi", "tumbi", "melodic", solo="Tumbi Riff", role="answer", indian=True,
                aliases=("tumbi", "toombi", "तुम्बी")),
    "manjira": _i("Manjira", "manjira hand cymbals", "rhythm", lead=False, role="rhythm", indian=True,
                  aliases=("manjira", "manjeera", "jhanj", "मंजीरा")),
    "ektara": _i("Ektara", "ektara", "melodic", solo="Ektara Riff", role="drone", indian=True,
                 aliases=("ektara", "iktara", "इकतारा")),
    "handclaps": _i("Handclaps", "rhythmic handclaps", "rhythm", lead=False, role="rhythm",
                    aliases=("handclaps", "hand claps", "claps", "clapping", "taali", "तालियाँ", "ताली")),
    # --- Western acoustic --------------------------------------------------------------------------------
    "nylon_guitar": _i("Nylon guitar", "nylon-string classical guitar", "harmony", solo="Guitar Solo",
                       role="harmony", aliases=("nylon guitar", "classical guitar", "spanish guitar")),
    "electric_guitar": _i("Electric guitar", "electric guitar", "melodic", solo="Guitar Solo", role="harmony",
                          aliases=("electric guitar", "lead guitar", "guitar solo", "distorted guitar",
                                   "rock guitar", "इलेक्ट्रिक गिटार")),
    "upright_bass": _i("Upright bass", "upright bass", "bass", lead=False, role="harmony",
                       aliases=("upright bass", "double bass", "acoustic bass", "contrabass")),
    "drum_kit": _i("Drum kit", "live drum kit", "rhythm", lead=False, solo="Drum Break", role="rhythm",
                   aliases=("drum kit", "drumkit", "full drums", "live drums", "rock drums", "drum set")),
    "brushed_drums": _i("Brushed drums", "brushed drums", "rhythm", lead=False, role="rhythm",
                        aliases=("brushed drums", "brushes", "brush drums")),
    "cajon": _i("Cajon", "cajon", "rhythm", lead=False, role="rhythm", aliases=("cajon", "cajón")),
    "harp": _i("Harp", "harp", "harmony", solo="Harp Interlude", role="texture", aliases=("harp", "हार्प")),
    "concert_flute": _i("Concert flute", "concert flute", "melodic", solo="Flute Solo", role="answer",
                aliases=("concert flute", "western flute", "silver flute")),
    "clarinet": _i("Clarinet", "clarinet", "melodic", solo="Clarinet Solo", role="answer", aliases=("clarinet",)),
    "saxophone": _i("Saxophone", "saxophone", "melodic", solo="Sax Solo", role="answer",
                    aliases=("saxophone", "sax", "सैक्सोफोन")),
    "trumpet": _i("Trumpet", "trumpet", "melodic", solo="Trumpet Solo", role="answer",
                  aliases=("trumpet", "flugelhorn")),
    "brass": _i("Brass section", "brass section", "harmony", solo="Brass Hits", role="harmony",
                aliases=("brass", "horns", "horn section")),
    "organ": _i("Organ", "warm organ", "harmony", solo="Organ Solo", role="harmony",
                aliases=("organ", "hammond", "church organ")),
    "rhodes": _i("Electric piano", "Rhodes electric piano", "harmony", solo="Keys Solo", role="harmony",
                 aliases=("rhodes", "electric piano", "e-piano", "wurlitzer", "keys")),
    "ukulele": _i("Ukulele", "ukulele", "harmony", solo="Ukulele Solo", role="harmony", aliases=("ukulele", "uke")),
    "mandolin": _i("Mandolin", "mandolin", "melodic", solo="Mandolin Solo", role="answer", aliases=("mandolin",)),
    "accordion": _i("Accordion", "accordion", "melodic", solo="Accordion Solo", role="answer",
                    aliases=("accordion",)),
    "harmonica": _i("Harmonica", "harmonica", "melodic", solo="Harmonica Solo", role="answer",
                    aliases=("harmonica", "mouth organ")),
    "bells": _i("Bells", "celesta and glockenspiel bells", "texture", solo=None, role="texture",
                aliases=("glockenspiel", "celesta", "music box", "chimes", "bells")),
    # --- electronic --------------------------------------------------------------------------------------
    "synth_pad": _i("Synth pad", "warm synth pads", "texture", lead=False, role="texture",
                    aliases=("synth pad", "synth pads", "pads", "atmospheric pads")),
    "synth_lead": _i("Synth lead", "bright synth lead", "melodic", solo="Synth Solo", role="answer",
                     aliases=("synth lead", "lead synth", "synthesizer", "synth", "synths", "सिंथ")),
    "synth_bass": _i("Synth bass", "deep synth bass", "bass", lead=False, role="harmony",
                     aliases=("synth bass", "bassline", "sub bass")),
    "bass_808": _i("808 bass", "booming 808 bass", "bass", lead=False, role="harmony",
                   aliases=("808", "808s", "808 bass")),
    "drum_machine": _i("Drum machine", "punchy electronic drums", "rhythm", lead=False, solo="Drum Break",
                       role="rhythm", aliases=("drum machine", "electronic drums", "beat", "beats", "trap drums",
                                               "hi-hats", "hi hats")),
    "arpeggiator": _i("Synth arpeggio", "pulsing synth arpeggios", "texture", lead=False, role="texture",
                      aliases=("arpeggio", "arpeggios", "arp", "arpeggiator")),
    # --- other world / cinematic -------------------------------------------------------------------------
    "oud": _i("Oud", "oud", "melodic", solo="Oud Solo", role="answer", aliases=("oud",)),
    "duduk": _i("Duduk", "duduk", "melodic", solo="Duduk Solo", role="answer", aliases=("duduk",)),
    "kalimba": _i("Kalimba", "kalimba", "texture", solo=None, role="texture", aliases=("kalimba", "thumb piano")),
    "marimba": _i("Marimba", "marimba", "texture", solo="Marimba Solo", role="texture",
                  aliases=("marimba", "vibraphone", "vibes")),
    "taiko": _i("Taiko", "thundering taiko drums", "rhythm", lead=False, solo="Drum Break", role="rhythm",
                aliases=("taiko", "war drums", "epic drums", "big drums")),
}

INSTRUMENT_IDS: tuple[str, ...] = tuple(INSTRUMENTS)
assert set(CLASSIC_IDS) <= set(INSTRUMENT_IDS)
NEW_IDS: tuple[str, ...] = tuple(i for i in INSTRUMENT_IDS if i not in CLASSIC_IDS)


def get(inst: str) -> dict:
    return INSTRUMENTS[inst]


def caption_name(inst: str) -> str:
    return INSTRUMENTS[inst]["caption"]


def display_name(inst: str) -> str:
    return INSTRUMENTS[inst]["name"]


def can_lead(inst: str) -> bool:
    return INSTRUMENTS[inst]["can_lead"]


def default_role(inst: str) -> str:
    return INSTRUMENTS[inst]["role"]


_MENTION_WORDS: Optional[dict[str, str]] = None


def _mention_words() -> dict[str, str]:
    """word or phrase -> instrument id, for spotting instrument names inside style hints."""
    global _MENTION_WORDS
    if _MENTION_WORDS is None:
        words: dict[str, str] = {}
        for inst, d in INSTRUMENTS.items():
            for w in [d["name"], d["caption"], inst.replace("_", " ")] + d["aliases"]:
                w = w.lower()
                if w.isascii() and len(w) >= 3 and w not in ("beat", "beats", "keys", "drone"):
                    words.setdefault(w, inst)
        words.update({"flute": "bansuri", "guitar": "acoustic_guitar", "drums": "drum_kit", "brushes": "brushed_drums",
                      "claps": "handclaps", "strings": "strings", "orchestra": "strings", "tabla": "tabla"})
        _MENTION_WORDS = words
    return _MENTION_WORDS


def mentioned(text: str) -> set[str]:
    """Instrument ids named in a short phrase ("dhol and tumbi intro" -> {dhol, tumbi})."""
    import re
    low = text.lower()
    hits = set()
    for w, inst in _mention_words().items():
        if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low):
            hits.add(inst)
    return hits
