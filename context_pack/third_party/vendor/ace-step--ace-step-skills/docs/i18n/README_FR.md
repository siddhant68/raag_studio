# ACE-Step Skills for Any Agents

[![en](https://img.shields.io/badge/lang-English-blue.svg)](../../README.md) [![zh](https://img.shields.io/badge/lang-中文-red.svg)](README_ZH.md) [![ja](https://img.shields.io/badge/lang-日本語-green.svg)](README_JA.md) [![ko](https://img.shields.io/badge/lang-한국어-yellow.svg)](README_KO.md) [![de](https://img.shields.io/badge/lang-Deutsch-black.svg)](README_DE.md) [![fr](https://img.shields.io/badge/lang-Français-purple.svg)](README_FR.md) [![ru](https://img.shields.io/badge/lang-Русский-orange.svg)](README_RU.md)

Skills personnalisés pour AI Agents (Claude Code, OpenAI Codex, etc.) pour générer de la musique via [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) API.

## Skills Disponibles

| Skill | Description |
|-------|-------------|
| **acestep** | Génération musicale via ACE-Step API |
| **acestep-docs** | Documentation et dépannage |

## Fonctionnalités

### acestep (Génération Musicale)

- **Texte vers musique** - Générer de la musique à partir de descriptions
- **Génération de paroles** - Automatique ou manuelle
- **Continuation audio** - Continuer à partir d'un audio existant
- **Repeinture audio** - Modifier des parties spécifiques
- **Génération aléatoire** - Échantillons musicaux aléatoires

### acestep-docs (Documentation)

- **Guide d'installation** - Aide à la configuration
- **Compatibilité GPU** - Exigences VRAM et recommandations matérielles
- **Guide Gradio UI** - Utilisation de l'interface web
- **Réglage d'inférence** - Optimisation des paramètres
- **Référence API** - REST API et intégration OpenRouter

## Prérequis

- **Serveur API ACE-Step** - Service [ACE-Step V1.5](https://github.com/ace-step/ACE-Step-1.5) requis

## Installation

### Claude Code

Copier les dossiers skill souhaités depuis `skills/` vers:

**Niveau projet**:
```
your-project/.claude/skills/
```

**Niveau global**:
```
~/.claude/skills/
```

### OpenAI Codex

Copier les dossiers skill souhaités depuis `skills/` vers:

**Niveau projet**:
```
your-project/.agents/skills/
```

**Niveau global**:
```
~/.agents/skills/
```

### Structure des Répertoires

```
skills/
├── acestep/                    # Skill de génération musicale
│   ├── SKILL.md
│   └── scripts/
│       ├── acestep.sh
│       └── config.json
└── acestep-docs/               # Skill de documentation
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

## Configuration (acestep)

Éditer `acestep/scripts/config.json`:

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

### Options

| Option | Par défaut | Description |
|--------|------------|-------------|
| `api_url` | `http://127.0.0.1:8001` | Adresse du serveur API |
| `api_key` | `""` | Clé API (optionnel) |
| `generation.thinking` | `true` | Activer 5Hz LM (haute qualité) |
| `generation.audio_format` | `mp3` | Format de sortie |

## Utilisation (acestep)

### Dans l'Agent

```
Utilisateur: Crée une chanson pop joyeuse
Utilisateur: Génère de la musique jazz
Utilisateur: Crée une chanson sur le printemps
```

### Ligne de commande

```bash
# Vérifier le statut de l'API
./scripts/acestep.sh health

# Générer de la musique - Mode Caption
./scripts/acestep.sh generate "Pop music with guitar"

# Générer de la musique - Mode Simple
./scripts/acestep.sh generate -d "Une chanson joyeuse sur le printemps"

# Génération aléatoire
./scripts/acestep.sh random

# Vérifier le statut de la tâche
./scripts/acestep.sh status <job_id>
```

### Options

| Option | Description |
|--------|-------------|
| `-c, --caption` | Description du style musical |
| `-d, --description` | Description simple, LM génère automatiquement |
| `-l, --lyrics` | Paroles |
| `--no-thinking` | Désactiver le mode thinking |
| `--duration` | Durée audio (secondes) |
| `--bpm` | Tempo |

## Sortie

Les résultats sont sauvegardés dans le dossier `acestep_output`:

```
project_root/
├── acestep_output/
│   ├── <job_id>.json
│   ├── <job_id>_1.mp3
│   └── ...
```

## Mémoire GPU

| VRAM | Modèle LM | Note |
|------|-----------|------|
| ≤6GB | Aucun | LM désactivé |
| 6-12GB | `acestep-5Hz-lm-0.6B` | Léger |
| 12-16GB | `acestep-5Hz-lm-1.7B` | Meilleure qualité |
| ≥16GB | `acestep-5Hz-lm-4B` | Meilleure qualité |

## Références

- [acestep/SKILL.md](../../skills/acestep/SKILL.md) - Documentation API de génération musicale
- [acestep-docs/SKILL.md](../../skills/acestep-docs/SKILL.md) - Index du skill documentation
- [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) - Projet ACE-Step
