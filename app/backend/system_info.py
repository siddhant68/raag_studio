"""What the machine can do right now: MPS, disk, the ComfyUI video queue, memory, engine revision.

Reuses scripts/preflight.py (loaded by path; it is a stdlib script, not a package) for the ACE python
location, the MPS probe and the checkpoint list. Tests replace methods on `SystemProbe` to mock
a busy video queue or a nearly full disk. The fake engine never probes MPS.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from . import capabilities
from .settings import ENGINE_DIR, ROOT, VERSION, Config

MPS_CACHE_S = 120


def _load_preflight():
    spec = importlib.util.spec_from_file_location("raag_preflight", ROOT / "scripts" / "preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)               # defines functions only; main() is guarded
    return module


class SystemProbe:
    def __init__(self, config: Config):
        self.config = config
        self.preflight = _load_preflight()
        self._mps: Optional[tuple[float, dict]] = None
        self._lock = threading.Lock()

    # -- individual probes ---------------------------------------------------
    @property
    def ace_python(self) -> Path:
        return Path(self.preflight.ACE_PYTHON)

    def disk_free_gib(self) -> float:
        return round(shutil.disk_usage(self.config.runs_dir).free / 2**30, 2)

    def video_queue(self, url: str) -> dict:
        """Same semantics as preflight.check_video_queue: refused = idle, running/pending = busy."""
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.load(response)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, ConnectionRefusedError):
                return {"state": "idle", "running": 0, "pending": 0, "detail": "connection refused (no server)"}
            return {"state": "unknown", "detail": f"unreachable: {exc.reason}"}
        except Exception as exc:
            return {"state": "unknown", "detail": f"{type(exc).__name__}: {exc}"}
        running = len(data.get("queue_running", data.get("running", [])) or [])
        pending = len(data.get("queue_pending", data.get("pending", [])) or [])
        return {"state": "busy" if running or pending else "idle", "running": running, "pending": pending,
                "detail": url}

    def mps(self, fresh: bool = False) -> dict:
        """{'available': bool|None, 'detail': str}. Fake engine: not probed. Never falls back to CPU."""
        if self.config.is_fake:
            return {"available": None, "detail": "not probed: fake test engine in use"}
        with self._lock:
            if not fresh and self._mps and time.time() - self._mps[0] < MPS_CACHE_S:
                return self._mps[1]
            info = self.preflight.probe_mps()
            self._mps = (time.time(), info)
            return info

    def checkpoints(self) -> dict:
        return self.preflight.check_checkpoints()

    def memory(self) -> dict:
        """Rough free-memory snapshot recorded with each job (a sanity record, not a gate)."""
        try:
            out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
            page = int(re.search(r"page size of (\d+) bytes", out).group(1))
            pages = {k: int(v) for k, v in re.findall(r"Pages (free|inactive|speculative):\s+(\d+)", out)}
            free = sum(pages.values()) * page / 2**30
            return {"approx_available_gib": round(free, 2)}
        except Exception as exc:                  # non-macOS or vm_stat missing
            return {"approx_available_gib": None, "detail": f"{type(exc).__name__}"}

    def engine_rev(self) -> str:
        if self.config.is_fake:
            return "fake-engine-1"
        version = "unknown"
        try:
            toml = (self.preflight.ACE_SOURCE / "pyproject.toml").read_text()
            version = re.search(r'^version\s*=\s*"([^"]+)"', toml, re.M).group(1)
        except Exception:
            pass
        digest = hashlib.sha256((ENGINE_DIR / "run_takes.py").read_bytes()).hexdigest()[:8]
        return f"ace-step-{version}/acestep-v15-turbo/run_takes-{digest}"

    def capabilities_summary(self) -> dict:
        reg = capabilities.registry()
        by_class: dict[str, int] = {}
        for ctl in reg["controls"].values():
            for cls in ctl["classes"]:
                by_class[cls] = by_class.get(cls, 0) + 1
        return {"controls": len(reg["controls"]), "capability_rows": len(reg["capabilities"]),
                "controls_by_class": by_class, "source": "app/backend/capabilities.json"}

    def snapshot(self, settings: dict[str, Any], queue: dict, effective_planner: str = "basic") -> dict:
        mps = self.mps()
        return {
            "version": VERSION,
            "engine": self.config.engine,
            "engine_rev": self.engine_rev(),
            "mps": mps.get("available"),
            "mps_detail": mps.get("detail"),
            "disk_free_gib": self.disk_free_gib(),
            "min_disk_gib": settings["min_disk_gib"],
            "video_queue": self.video_queue(settings["video_queue_url"]),
            "planner_provider": effective_planner,
            "planner_setting": settings["planner_provider"],
            "planner_smart_enabled": settings["planner_smart_enabled"],
            "queue": queue,
            "capabilities": self.capabilities_summary(),
            "ace_python": {"path": str(self.ace_python), "exists": self.ace_python.is_file()},
        }
