"""Download optional ACE-Step weights into the shared checkpoints folder, after asking.

    python3 scripts/fetch_models.py lm          # acestep-5Hz-lm-1.7B   (about 3.5 GB)
    python3 scripts/fetch_models.py xl          # acestep-v15-xl-turbo  (about 9-10 GB)
    python3 scripts/fetch_models.py lm --yes    # no prompt
    python3 scripts/fetch_models.py --list      # what is installed

Renders never download anything (app/engine/run_takes.py blocks the network and refuses missing weights); this
script is the only place a download happens, and only when you run it. It needs `huggingface_hub`, which the shared
ACE python has: when this python lacks it, the script re-runs itself with the ACE python.

Free disk is checked first (the download plus the app's 5 GiB minimum). Each finished download is recorded in
data/model_downloads.json. Nothing outside the checkpoints folder is changed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(os.environ.get("RAAG_TOOLS_DIR", ROOT.parent / "tools"))
ACE_PYTHON = TOOLS / "acestep-venv/bin/python"
CHECKPOINTS = TOOLS / "ace-step-1.5/checkpoints"
MIN_DISK_GIB = 5.0
LEDGER = ROOT / "data" / "model_downloads.json"

# name -> (Hugging Face repo, files inside the repo, target folder under checkpoints, approximate GiB)
MODELS = {
    "lm": ("ACE-Step/Ace-Step1.5", ["acestep-5Hz-lm-1.7B/*"], "acestep-5Hz-lm-1.7B", 3.6),
    "xl": ("ACE-Step/acestep-v15-xl-turbo", None, "acestep-v15-xl-turbo", 10.0),
}


def installed(folder: str) -> bool:
    d = CHECKPOINTS / folder
    return (d / "config.json").is_file() and any(d.glob("*.safetensors"))


def free_gib() -> float:
    probe = CHECKPOINTS if CHECKPOINTS.exists() else ROOT
    return shutil.disk_usage(probe).free / 2**30


def record(entry: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    rows = json.loads(LEDGER.read_text()) if LEDGER.exists() else []
    rows.append(entry)
    LEDGER.write_text(json.dumps(rows, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", nargs="?", choices=sorted(MODELS))
    ap.add_argument("--yes", action="store_true", help="do not ask before downloading")
    ap.add_argument("--list", action="store_true", help="show which optional models are installed")
    args = ap.parse_args()

    if args.list or not args.model:
        for key, (_, _, folder, gib) in MODELS.items():
            print(f"{key:5s} {folder:24s} ~{gib:4.1f} GiB  {'installed' if installed(folder) else 'not installed'}")
        print(f"checkpoints: {CHECKPOINTS}   free disk: {free_gib():.1f} GiB")
        return 0

    repo, patterns, folder, gib = MODELS[args.model]
    if installed(folder):
        print(f"{folder} is already installed in {CHECKPOINTS}. Nothing to do.")
        return 0
    if not CHECKPOINTS.is_dir():
        print(f"Checkpoints folder not found: {CHECKPOINTS} (set RAAG_TOOLS_DIR?)", file=sys.stderr)
        return 2
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        if ACE_PYTHON.is_file() and Path(sys.executable).resolve() != ACE_PYTHON.resolve():
            return subprocess.call([str(ACE_PYTHON), __file__] + sys.argv[1:])
        print("huggingface_hub is not available; run with the ACE python.", file=sys.stderr)
        return 2
    free = free_gib()
    need = gib + MIN_DISK_GIB
    print(f"About to download {folder} (~{gib} GiB) from huggingface.co/{repo} into {CHECKPOINTS}.")
    print(f"Free disk: {free:.1f} GiB (needs about {need:.1f} GiB including the 5 GiB minimum).")
    if free < need:
        print("Not enough free disk. Free some space first; nothing was downloaded.", file=sys.stderr)
        return 3
    if not args.yes:
        if input("Download now? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Cancelled; nothing was downloaded.")
            return 1
    for var in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        os.environ.pop(var, None)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if patterns:                       # a subfolder of the main repo lands at checkpoints/<subfolder>
        snapshot_download(repo_id=repo, allow_patterns=patterns, local_dir=str(CHECKPOINTS))
    else:
        snapshot_download(repo_id=repo, local_dir=str(CHECKPOINTS / folder))
    ok = installed(folder)
    size = sum(f.stat().st_size for f in (CHECKPOINTS / folder).rglob("*") if f.is_file()) / 2**30
    record({"model": folder, "repo": repo, "started_at": started, "ok": ok, "gib": round(size, 2),
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    print(f"{folder}: {'installed' if ok else 'INCOMPLETE'} ({size:.1f} GiB). Free disk now {free_gib():.1f} GiB.")
    if ok:
        profile = {"lm": "lm", "xl": "xl"}[args.model]
        print(f"Turn it on with: curl -X PUT localhost:8477/api/settings -H 'content-type: application/json' "
              f"-d '{{\"engine_profile\": \"{profile}\"}}'   (or the Settings page)")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
