#!/bin/sh
# Start Raag Studio (uvicorn, FastAPI) in the background on 127.0.0.1:${RAAG_PORT:-8477}.
# pid -> data/server.pid, log -> data/server.log. Safe to run twice.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PORT=${RAAG_PORT:-8477}
PIDFILE="$ROOT/data/server.pid"
PY="$ROOT/app/.venv/bin/python"

mkdir -p "$ROOT/data" "$ROOT/runs"
[ -x "$PY" ] || { echo "app/.venv is missing: python3.12 -m venv app/.venv && app/.venv/bin/pip install -r app/requirements.txt" >&2; exit 1; }

if [ -f "$PIDFILE" ]; then
  OLD=$(cat "$PIDFILE")
  if kill -0 "$OLD" 2>/dev/null && ps -p "$OLD" -o command= | grep -q uvicorn; then
    echo "Raag Studio is already running (pid $OLD) at http://127.0.0.1:$PORT"
    exit 0
  fi
  rm -f "$PIDFILE"                                   # stale
fi

cd "$ROOT/app"
nohup "$PY" -m uvicorn backend.main:create_app --factory --host 127.0.0.1 --port "$PORT" \
  --timeout-graceful-shutdown 5 >> "$ROOT/data/server.log" 2>&1 &
echo $! > "$PIDFILE"

i=0
while [ $i -lt 40 ]; do
  if curl -sf "http://127.0.0.1:$PORT/api/settings" >/dev/null 2>&1; then
    echo "Raag Studio started (pid $(cat "$PIDFILE")) at http://127.0.0.1:$PORT  (log: data/server.log)"
    exit 0
  fi
  kill -0 "$(cat "$PIDFILE")" 2>/dev/null || { echo "server exited; see data/server.log" >&2; rm -f "$PIDFILE"; exit 1; }
  i=$((i + 1)); sleep 0.5
done
echo "server did not answer within 20 s; see data/server.log" >&2
exit 1
