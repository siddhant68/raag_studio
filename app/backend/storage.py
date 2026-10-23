"""File store under runs/ (PRD section 7):

    runs/<song_id>/<round_id>/            final round folder (renamed from <round_id>.partial on success only)
    runs/<song_id>/<round_id>.partial/    engine output while rendering; swept on boot
    runs/<song_id>/exports/               MP3/WAV exports
    runs/_quarantine/                     final folders that lack a succeeded job row (never reused)

DB paths are stored relative to the runs directory so the store can move.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .db import Database, now_iso


class Storage:
    def __init__(self, runs_dir: Path, tmp_dir: Path):
        self.runs = Path(runs_dir)
        self.tmp = Path(tmp_dir)
        self.runs.mkdir(parents=True, exist_ok=True)
        self.tmp.mkdir(parents=True, exist_ok=True)

    # -- paths ---------------------------------------------------------------
    def round_dir(self, song_id: str, round_id: str) -> Path:
        return self.runs / song_id / round_id

    def partial_dir(self, song_id: str, round_id: str, suffix: str = "") -> Path:
        return self.runs / song_id / f"{round_id}{suffix}.partial"

    def exports_dir(self, song_id: str) -> Path:
        d = self.runs / song_id / "exports"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.runs.resolve()))

    def abs(self, rel_path: Optional[str]) -> Optional[Path]:
        if not rel_path:
            return None
        p = (self.runs / rel_path).resolve()
        if self.runs.resolve() not in p.parents:      # never serve anything outside runs/
            return None
        return p

    # -- lifecycle -----------------------------------------------------------
    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)

    def finalize(self, partial: Path, final: Path) -> None:
        """Rename X.partial to X. An existing X is quarantined first, never overwritten."""
        if final.exists():
            self.quarantine(final)
        partial.rename(final)

    def quarantine(self, path: Path) -> Path:
        qdir = self.runs / "_quarantine"
        qdir.mkdir(parents=True, exist_ok=True)
        target = qdir / f"{path.parent.name}__{path.name}__{now_iso().replace(':', '')}"
        path.rename(target)
        return target

    def sweep(self, db: Database) -> dict:
        """Boot sweep: delete every .partial folder of a known song and quarantine
        final round folders whose round has no succeeded job."""
        swept, quarantined = [], []
        for song in db.all("SELECT id FROM songs"):
            sdir = self.runs / song["id"]
            if not sdir.is_dir():
                continue
            for child in sorted(sdir.iterdir()):
                if child.is_dir() and child.name.endswith(".partial"):
                    self.remove_tree(child)
                    swept.append(str(child.relative_to(self.runs)))
                elif child.is_dir() and child.name != "exports":
                    ok = db.one("SELECT 1 FROM jobs WHERE round_id=? AND state='succeeded'", (child.name,))
                    if not ok:
                        before = str(child.relative_to(self.runs))
                        self.quarantine(child)
                        quarantined.append(before)
        return {"swept": swept, "quarantined": quarantined}

    def disk_free_gib(self) -> float:
        return round(shutil.disk_usage(self.runs).free / 2**30, 2)
