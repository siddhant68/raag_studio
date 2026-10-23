"""Shared helpers for the M2 tests (not a test module: it holds no tests).

Every M2 test runs with RAAG_ENGINE=fake, a temp data dir and a temp runs dir, and points the
video-queue gate at a closed port so the real ComfyUI on :8388 can never influence a test.
"""
import contextlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import create_app  # noqa: E402
from backend.settings import Config  # noqa: E402

BRIEF = "A peaceful bansuri at dawn, gentle tabla, no singing, about two minutes"
TERMINAL = ("succeeded", "failed", "cancelled")
FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def env_for(tmp_path, engine="fake", **extra):
    env = {"RAAG_DATA_DIR": str(tmp_path / "data"), "RAAG_RUNS_DIR": str(tmp_path / "runs"),
           "RAAG_POLL_INTERVAL_S": "0.1", "RAAG_VIDEO_QUEUE_URL": "http://127.0.0.1:1/queue"}
    if engine:
        env["RAAG_ENGINE"] = engine
    env.update(extra)
    return env


def make_config(tmp_path, engine="fake", **extra):
    config = Config.from_env(env_for(tmp_path, engine, **extra))
    config.kill_grace_s = 1.0
    return config


@contextlib.contextmanager
def client_for(tmp_path, engine="fake", **extra):
    """TestClient with the lifespan running (so the worker thread and recovery are active)."""
    config = make_config(tmp_path, engine, **extra)
    app = create_app(config)
    with TestClient(app, base_url="http://127.0.0.1:8477") as client:
        client.app_ref = app
        client.svc = app.state.svc
        client.config = config
        yield client


def create_body(**extra):
    body = {"brief": BRIEF, "duration": 10, "takes": 2}
    body.update(extra)
    return body


def wait_job(client, job_id, timeout=60, until=TERMINAL):
    deadline = time.time() + timeout
    job = None
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in until:
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not reach {until} in {timeout}s; last: {job}")


def create_and_wait(client, **extra):
    r = client.post("/api/songs", json=create_body(**extra))
    assert r.status_code == 202, r.text
    data = r.json()
    job = wait_job(client, data["job_id"])
    assert job["state"] == "succeeded", job
    detail = client.get(f"/api/songs/{data['song_id']}").json()
    return data, job, detail


def ffprobe(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    stream = info["streams"][0]
    return {"codec": stream["codec_name"], "sample_rate": int(stream["sample_rate"]),
            "channels": int(stream["channels"]), "duration": float(info["format"]["duration"]),
            "bits": stream.get("bits_per_raw_sample")}


def decodes_clean(path):
    done = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    return done.returncode == 0 and not done.stderr.strip()


def loudness(path):
    """(integrated LUFS, true peak dBTP) measured independently with ffmpeg ebur128."""
    done = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                           "-f", "null", "-"], capture_output=True, text=True)
    summary = done.stderr[done.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[0-9.]+) LUFS", summary).group(1))
    tp = float(re.search(r"True peak:\s+Peak:\s+(-?[0-9.]+) dBFS", summary).group(1))
    return i, tp


def make_wav(path, seconds=5.0, volume=1.0, freq=440, extra_filter=""):
    af = f"volume={volume}" + (f",{extra_filter}" if extra_filter else "")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
                    f"sine=frequency={freq}:sample_rate=48000:duration={seconds}", "-af", af + ",pan=stereo|c0=c0|c1=c0",
                    "-ar", "48000", str(path)], check=True)


# --------------------------------------------------------------------------- live server (real uvicorn)
class LiveServer:
    def __init__(self, tmp_path, port=None, **env_extra):
        self.tmp_path = Path(tmp_path)
        self.port = port or free_port()
        self.env_extra = env_extra
        self.proc = None
        self.base = f"http://127.0.0.1:{self.port}"

    def start(self):
        env = {**os.environ, **env_for(self.tmp_path, RAAG_PORT=str(self.port)), **self.env_extra}
        log = open(self.tmp_path / f"server_{self.port}_{int(time.time()*1000)}.log", "w")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:create_app", "--factory", "--host", "127.0.0.1",
             "--port", str(self.port), "--timeout-graceful-shutdown", "3"],
            cwd=str(APP), env=env, stdout=log, stderr=subprocess.STDOUT)
        import httpx
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if httpx.get(f"{self.base}/api/settings", timeout=2).status_code == 200:
                    return self
            except httpx.HTTPError:
                time.sleep(0.2)
        raise AssertionError("live server did not start")

    def kill9(self):
        os.kill(self.proc.pid, 9)
        self.proc.wait(timeout=10)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
