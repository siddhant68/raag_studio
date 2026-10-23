# ACE-Step Skills for Any Agents

[![en](https://img.shields.io/badge/lang-English-blue.svg)](../../README.md) [![zh](https://img.shields.io/badge/lang-中文-red.svg)](README_ZH.md) [![ja](https://img.shields.io/badge/lang-日本語-green.svg)](README_JA.md) [![ko](https://img.shields.io/badge/lang-한국어-yellow.svg)](README_KO.md) [![de](https://img.shields.io/badge/lang-Deutsch-black.svg)](README_DE.md) [![fr](https://img.shields.io/badge/lang-Français-purple.svg)](README_FR.md) [![ru](https://img.shields.io/badge/lang-Русский-orange.svg)](README_RU.md)

Пользовательские Skills для AI Agents (Claude Code, OpenAI Codex и др.) для генерации музыки через [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) API.

## Доступные Skills

| Skill | Описание |
|-------|----------|
| **acestep** | Генерация музыки через ACE-Step API |
| **acestep-docs** | Документация и устранение неполадок |

## Возможности

### acestep (Генерация музыки)

- **Текст в музыку** - Генерация музыки из описания
- **Генерация текста** - Автоматическая или ручная
- **Продолжение аудио** - Продолжение существующего аудио
- **Перерисовка аудио** - Изменение отдельных частей
- **Случайная генерация** - Случайные музыкальные сэмплы

### acestep-docs (Документация)

- **Руководство по установке** - Помощь в настройке
- **Совместимость GPU** - Требования к VRAM и рекомендации по оборудованию
- **Руководство Gradio UI** - Использование веб-интерфейса
- **Настройка инференса** - Оптимизация параметров
- **Справочник API** - REST API и интеграция с OpenRouter

## Требования

- **ACE-Step API сервер** - Требуется [ACE-Step V1.5](https://github.com/ace-step/ACE-Step-1.5)

## Установка

### Claude Code

Скопируйте нужные папки skill из `skills/` в:

**Уровень проекта**:
```
your-project/.claude/skills/
```

**Глобальный**:
```
~/.claude/skills/
```

### OpenAI Codex

Скопируйте нужные папки skill из `skills/` в:

**Уровень проекта**:
```
your-project/.agents/skills/
```

**Глобальный**:
```
~/.agents/skills/
```

### Структура каталогов

```
skills/
├── acestep/                    # Skill генерации музыки
│   ├── SKILL.md
│   └── scripts/
│       ├── acestep.sh
│       └── config.json
└── acestep-docs/               # Skill документации
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

## Конфигурация (acestep)

Редактируйте `acestep/scripts/config.json`:

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

### Опции

| Опция | По умолчанию | Описание |
|-------|--------------|----------|
| `api_url` | `http://127.0.0.1:8001` | Адрес API-сервера |
| `api_key` | `""` | API-ключ (опционально) |
| `generation.thinking` | `true` | Включить 5Hz LM (высокое качество) |
| `generation.audio_format` | `mp3` | Формат вывода |

## Использование (acestep)

### В Agent

```
Пользователь: Создай весёлую поп-песню
Пользователь: Сгенерируй джазовую музыку
Пользователь: Создай песню о весне
```

### Командная строка

```bash
# Проверить статус API
./scripts/acestep.sh health

# Генерация музыки - режим Caption
./scripts/acestep.sh generate "Pop music with guitar"

# Генерация музыки - режим Simple
./scripts/acestep.sh generate -d "Весёлая песня о весне"

# Случайная генерация
./scripts/acestep.sh random

# Проверить статус задачи
./scripts/acestep.sh status <job_id>
```

### Опции

| Опция | Описание |
|-------|----------|
| `-c, --caption` | Описание музыкального стиля |
| `-d, --description` | Простое описание, LM генерирует автоматически |
| `-l, --lyrics` | Текст песни |
| `--no-thinking` | Отключить режим thinking |
| `--duration` | Длительность аудио (секунды) |
| `--bpm` | Темп |

## Вывод

Результаты сохраняются в папку `acestep_output`:

```
project_root/
├── acestep_output/
│   ├── <job_id>.json
│   ├── <job_id>_1.mp3
│   └── ...
```

## Память GPU

| VRAM | Модель LM | Примечание |
|------|-----------|------------|
| ≤6GB | Нет | LM отключён |
| 6-12GB | `acestep-5Hz-lm-0.6B` | Лёгкая |
| 12-16GB | `acestep-5Hz-lm-1.7B` | Лучшее качество |
| ≥16GB | `acestep-5Hz-lm-4B` | Лучшее качество |

## Ссылки

- [acestep/SKILL.md](../../skills/acestep/SKILL.md) - Документация API генерации музыки
- [acestep-docs/SKILL.md](../../skills/acestep-docs/SKILL.md) - Индекс skill документации
- [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) - Проект ACE-Step
