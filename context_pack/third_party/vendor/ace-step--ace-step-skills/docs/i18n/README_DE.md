# ACE-Step Skills for Any Agents

[![en](https://img.shields.io/badge/lang-English-blue.svg)](../../README.md) [![zh](https://img.shields.io/badge/lang-中文-red.svg)](README_ZH.md) [![ja](https://img.shields.io/badge/lang-日本語-green.svg)](README_JA.md) [![ko](https://img.shields.io/badge/lang-한국어-yellow.svg)](README_KO.md) [![de](https://img.shields.io/badge/lang-Deutsch-black.svg)](README_DE.md) [![fr](https://img.shields.io/badge/lang-Français-purple.svg)](README_FR.md) [![ru](https://img.shields.io/badge/lang-Русский-orange.svg)](README_RU.md)

Benutzerdefinierte Skills für AI Agents (Claude Code, OpenAI Codex, etc.) zur Musikgenerierung über [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) API.

## Verfügbare Skills

| Skill | Beschreibung |
|-------|--------------|
| **acestep** | Musikgenerierung über ACE-Step API |
| **acestep-docs** | Dokumentation und Fehlerbehebung |

## Funktionen

### acestep (Musikgenerierung)

- **Text-zu-Musik** - Musik aus Beschreibungen generieren
- **Liedtext-Generierung** - Automatisch oder manuell
- **Audio-Fortsetzung** - Von bestehendem Audio fortsetzen
- **Audio-Repainting** - Bestimmte Teile ändern
- **Zufallsgenerierung** - Zufällige Musikproben

### acestep-docs (Dokumentation)

- **Installationsanleitung** - Einrichtung und Konfigurationshilfe
- **GPU-Kompatibilität** - VRAM-Anforderungen und Hardware-Empfehlungen
- **Gradio UI-Anleitung** - Web-Interface-Nutzung
- **Inferenz-Tuning** - Parameteroptimierung
- **API-Referenz** - REST API und OpenRouter-Integration

## Voraussetzungen

- **ACE-Step API Server** - [ACE-Step V1.5](https://github.com/ace-step/ACE-Step-1.5) API-Dienst erforderlich

## Installation

### Claude Code

Gewünschte Skill-Ordner aus `skills/` kopieren nach:

**Projektebene**:
```
your-project/.claude/skills/
```

**Global**:
```
~/.claude/skills/
```

### OpenAI Codex

Gewünschte Skill-Ordner aus `skills/` kopieren nach:

**Projektebene**:
```
your-project/.agents/skills/
```

**Global**:
```
~/.agents/skills/
```

### Verzeichnisstruktur

```
skills/
├── acestep/                    # Musikgenerierung Skill
│   ├── SKILL.md
│   └── scripts/
│       ├── acestep.sh
│       └── config.json
└── acestep-docs/               # Dokumentation Skill
    ├── SKILL.md
    ├── getting-started/
    │   ├── README.md
    │   ├── Tutorial.md
    │   └── ABOUT.md
    ├── guides/
    │   ├── GRADIO_GUIDE.md
    │   ├── INFERENCE.md
    │   └── GPU_COMPATIBILITY.md
    └── api/
        ├── API.md
        └── Openrouter_API.md
```

## Konfiguration (acestep)

`acestep/scripts/config.json` bearbeiten:

```json
{
  "api_url": "http://127.0.0.1:8001",
  "api_key": "",
  "generation": {
    "thinking": true,
    "use_format": true,
    "audio_format": "mp3",
    "vocal_language": "en"
  }
}
```

### Optionen

| Option | Standard | Beschreibung |
|--------|----------|--------------|
| `api_url` | `http://127.0.0.1:8001` | API-Serveradresse |
| `api_key` | `""` | API-Schlüssel (optional) |
| `generation.thinking` | `true` | 5Hz LM aktivieren (hohe Qualität) |
| `generation.audio_format` | `mp3` | Ausgabeformat |

## Verwendung (acestep)

### Im Agent

```
Benutzer: Erstelle einen fröhlichen Popsong
Benutzer: Generiere Jazz-Hintergrundmusik
Benutzer: Erstelle ein Lied über den Frühling
```

### Kommandozeile

```bash
# API-Status prüfen
./scripts/acestep.sh health

# Musik generieren - Caption-Modus
./scripts/acestep.sh generate "Pop music with guitar"

# Musik generieren - Simple-Modus
./scripts/acestep.sh generate -d "Ein fröhliches Lied über den Frühling"

# Zufallsgenerierung
./scripts/acestep.sh random

# Aufgabenstatus prüfen
./scripts/acestep.sh status <job_id>
```

### Optionen

| Option | Beschreibung |
|--------|--------------|
| `-c, --caption` | Musikstil-Beschreibung |
| `-d, --description` | Einfache Beschreibung, LM generiert automatisch |
| `-l, --lyrics` | Liedtext |
| `--no-thinking` | Thinking-Modus deaktivieren |
| `--duration` | Audiodauer (Sekunden) |
| `--bpm` | Tempo |

## Ausgabe

Ergebnisse werden im `acestep_output`-Ordner gespeichert:

```
project_root/
├── acestep_output/
│   ├── <job_id>.json
│   ├── <job_id>_1.mp3
│   └── ...
```

## GPU-Speicher

| VRAM | LM-Modell | Hinweis |
|------|-----------|---------|
| ≤6GB | Keins | LM deaktiviert |
| 6-12GB | `acestep-5Hz-lm-0.6B` | Leichtgewicht |
| 12-16GB | `acestep-5Hz-lm-1.7B` | Bessere Qualität |
| ≥16GB | `acestep-5Hz-lm-4B` | Beste Qualität |

## Referenzen

- [acestep/SKILL.md](../../skills/acestep/SKILL.md) - Musikgenerierung API-Dokumentation
- [acestep-docs/SKILL.md](../../skills/acestep-docs/SKILL.md) - Dokumentation Skill-Index
- [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) - ACE-Step Projekt
