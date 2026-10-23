# ACE-Step Skills for Any Agents

[![en](https://img.shields.io/badge/lang-English-blue.svg)](../../README.md) [![zh](https://img.shields.io/badge/lang-中文-red.svg)](README_ZH.md) [![ja](https://img.shields.io/badge/lang-日本語-green.svg)](README_JA.md) [![ko](https://img.shields.io/badge/lang-한국어-yellow.svg)](README_KO.md) [![de](https://img.shields.io/badge/lang-Deutsch-black.svg)](README_DE.md) [![fr](https://img.shields.io/badge/lang-Français-purple.svg)](README_FR.md) [![ru](https://img.shields.io/badge/lang-Русский-orange.svg)](README_RU.md)

Claude Code、OpenAI Codex などの AI Agent 向けカスタム Skill。[ACE-Step](https://github.com/ace-step/ACE-Step-1.5) API で音楽を生成します。

## 利用可能な Skills

| Skill | 説明 |
|-------|------|
| **acestep** | ACE-Step API による音楽生成 |
| **acestep-docs** | ドキュメントとトラブルシューティング |

## 機能

### acestep（音楽生成）

- **テキストから音楽生成** - 説明文から音楽を生成
- **歌詞生成** - 自動生成または手動指定
- **オーディオ継続** - 既存の音声から続きを生成
- **オーディオリペイント** - 音声の特定部分を修正
- **ランダム生成** - ランダムな音楽サンプルを生成

### acestep-docs（ドキュメント）

- **インストールガイド** - セットアップと設定のヘルプ
- **GPU 互換性** - VRAM 要件とハードウェア推奨
- **Gradio UI ガイド** - Web インターフェースの使用方法
- **推論チューニング** - パラメータ最適化
- **API リファレンス** - REST API と OpenRouter 統合

## 前提条件

- **ACE-Step API サーバー** - [ACE-Step V1.5](https://github.com/ace-step/ACE-Step-1.5) API サービスが必要

## インストール

### Claude Code

`skills/` から必要な skill フォルダを以下にコピー：

**プロジェクトレベル**：
```
your-project/.claude/skills/
```

**グローバルレベル**：
```
~/.claude/skills/
```

### OpenAI Codex

`skills/` から必要な skill フォルダを以下にコピー：

**プロジェクトレベル**：
```
your-project/.agents/skills/
```

**グローバルレベル**：
```
~/.agents/skills/
```

### ディレクトリ構造

```
skills/
├── acestep/                    # 音楽生成 skill
│   ├── SKILL.md
│   └── scripts/
│       ├── acestep.sh
│       └── config.json
└── acestep-docs/               # ドキュメント skill
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

## 設定（acestep）

`acestep/scripts/config.json` を編集：

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

### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `api_url` | `http://127.0.0.1:8001` | API サーバーアドレス |
| `api_key` | `""` | API キー（オプション） |
| `generation.thinking` | `true` | 5Hz LM を有効化（高品質） |
| `generation.audio_format` | `mp3` | 出力形式 |
| `generation.vocal_language` | `en` | ボーカル言語 |

## 使用方法（acestep）

### Agent での使用

会話で音楽生成について言及：

```
ユーザー: 明るいポップソングを作って
ユーザー: 春についての曲を作成して
ユーザー: ジャズ風のBGMを生成して
```

### コマンドライン

```bash
# API ステータス確認
./scripts/acestep.sh health

# 音楽生成 - Caption モード
./scripts/acestep.sh generate "Pop music with guitar"

# 音楽生成 - Simple モード
./scripts/acestep.sh generate -d "春についての明るい曲"

# ランダム生成
./scripts/acestep.sh random

# タスク状態確認
./scripts/acestep.sh status <job_id>
```

### オプション

| オプション | 説明 |
|-----------|------|
| `-c, --caption` | 音楽スタイルの説明 |
| `-d, --description` | 簡単な説明、LM が自動生成 |
| `-l, --lyrics` | 歌詞 |
| `--no-thinking` | thinking モード無効化 |
| `--duration` | 音声の長さ（秒） |
| `--bpm` | テンポ |

## 出力

結果は `acestep_output` フォルダに保存：

```
project_root/
├── acestep_output/
│   ├── <job_id>.json
│   ├── <job_id>_1.mp3
│   └── ...
```

## GPU メモリ

| VRAM | LM モデル | 備考 |
|------|----------|------|
| ≤6GB | なし | LM 無効 |
| 6-12GB | `acestep-5Hz-lm-0.6B` | 軽量 |
| 12-16GB | `acestep-5Hz-lm-1.7B` | 高品質 |
| ≥16GB | `acestep-5Hz-lm-4B` | 最高品質 |

## 参考

- [acestep/SKILL.md](../../skills/acestep/SKILL.md) - 音楽生成 API ドキュメント
- [acestep-docs/SKILL.md](../../skills/acestep-docs/SKILL.md) - ドキュメント skill インデックス
- [ACE-Step](https://github.com/ace-step/ACE-Step-1.5) - ACE-Step プロジェクト
