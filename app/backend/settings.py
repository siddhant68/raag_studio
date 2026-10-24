"""Runtime configuration (paths, engine mode, defaults) and the user-editable settings.

`Config` is read from the environment once per app. Tests build their own with
`Config.from_env(env)`. Nothing here imports torch.

Environment:
  RAAG_DATA_DIR   where raag.db and tmp/ live            (default <root>/data)
  RAAG_RUNS_DIR   where runs/<song>/<round>/ live        (default <root>/runs)
  RAAG_ENGINE     unset = real ACE-Step; "fake" = test engine (labelled everywhere)
  RAAG_TOOLS_DIR  ACE python / source (read by scripts/preflight.py as well)
  RAAG_VIDEO_QUEUE_URL  ComfyUI queue URL checked before every render
  RAAG_HOST / RAAG_PORT  bind address (127.0.0.1:8477)
  RAAG_SONG_PIPELINE     "1" (default) new songs use the song pipeline; "0" keeps the classic template compiler
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

VERSION = "0.2.0-m2"
ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
ENGINE_DIR = APP_DIR / "engine"
WEB_DIR = APP_DIR / "web"
DEFAULT_PORT = 8477

ENGINE_MODES = ("real", "fake")

# Defaults for the user-editable settings table (PUT /api/settings).
DEFAULT_SETTINGS: dict[str, Any] = {
    "planner_provider": "basic",          # basic | claude_cli | anthropic_api
    "planner_smart_enabled": False,       # a smart provider runs ONLY if this is true (set by the user, never by code)
    "min_disk_gib": 5.0,
    "queue_depth_cap": 5,
    "video_queue_url": "http://127.0.0.1:8388/queue",
    "silence_warn_fraction": 0.05,         # shown as a warning only
    "silence_fail_fraction": 0.40,         # beyond this the take counts as broken
    "retry_on_technical_failure": True,    # one automatic retry with a new seed, never for taste
    "job_timeout_s": 1800,
    "song_pipeline": True,                 # new songs use genre presets, blueprints and the song compiler
    "engine_profile": "auto",              # auto | classic | shift3 | lm | xl | xl_lm (song_compiler.ENGINE_PROFILES)
}
PLANNER_PROVIDERS = ("basic", "claude_cli", "anthropic_api")
ENGINE_PROFILE_SETTINGS = ("auto", "classic", "shift3", "lm", "xl", "xl_lm")


@dataclass
class Config:
    data_dir: Path
    runs_dir: Path
    engine: str = "real"                   # "real" | "fake"
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    poll_interval_s: float = 1.0           # worker idle poll / mac_busy re-check
    kill_grace_s: float = 3.0              # SIGTERM -> SIGKILL
    web_dir: Path = WEB_DIR
    setting_overrides: dict[str, Any] = field(default_factory=dict)   # env-derived defaults

    @property
    def db_path(self) -> Path:
        return self.data_dir / "raag.db"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def is_fake(self) -> bool:
        return self.engine == "fake"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env
        engine = (env.get("RAAG_ENGINE") or "real").strip().lower()
        if engine not in ENGINE_MODES:
            raise ValueError(f"RAAG_ENGINE must be unset or 'fake', got {engine!r}")
        overrides: dict[str, Any] = {}
        if env.get("RAAG_VIDEO_QUEUE_URL"):
            overrides["video_queue_url"] = env["RAAG_VIDEO_QUEUE_URL"]
        if env.get("RAAG_SONG_PIPELINE") in ("0", "1"):           # default for new songs (tests pin classic with 0)
            overrides["song_pipeline"] = env["RAAG_SONG_PIPELINE"] == "1"
        return cls(
            data_dir=Path(env.get("RAAG_DATA_DIR") or ROOT / "data").resolve(),
            runs_dir=Path(env.get("RAAG_RUNS_DIR") or ROOT / "runs").resolve(),
            engine=engine,
            host=env.get("RAAG_HOST") or "127.0.0.1",
            port=int(env.get("RAAG_PORT") or DEFAULT_PORT),
            poll_interval_s=float(env.get("RAAG_POLL_INTERVAL_S") or 1.0),
            setting_overrides=overrides,
        )


def validate_settings(patch: Mapping[str, Any]) -> dict[str, Any]:
    """Return a cleaned copy of `patch`; raise ValueError with a human message on bad input."""
    clean: dict[str, Any] = {}
    for key, value in patch.items():
        if key not in DEFAULT_SETTINGS:
            raise ValueError(f"unknown setting '{key}'")
        default = DEFAULT_SETTINGS[key]
        if key == "planner_provider":
            if value not in PLANNER_PROVIDERS:
                raise ValueError(f"planner_provider must be one of {list(PLANNER_PROVIDERS)}")
        elif key == "engine_profile":
            if value not in ENGINE_PROFILE_SETTINGS:
                raise ValueError(f"engine_profile must be one of {list(ENGINE_PROFILE_SETTINGS)}")
        elif isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{key} must be true or false")
        elif isinstance(default, str):
            if not isinstance(value, str) or not value.startswith(("http://127.0.0.1", "http://localhost")):
                raise ValueError(f"{key} must be a local http URL")
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise ValueError(f"{key} must be a non-negative number")
            if key == "queue_depth_cap" and not 1 <= value <= 50:
                raise ValueError("queue_depth_cap must be between 1 and 50")
            if key.endswith("_fraction") and not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
            value = type(default)(value) if not isinstance(default, float) else float(value)
        clean[key] = value
    return clean
