#!/bin/sh
# Stop Raag Studio. Kills ONLY the pid in data/server.pid, and only if that process is uvicorn.
set -eu
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PIDFILE="$ROOT/data/server.pid"

[ -f "$PIDFILE" ] || { echo "No data/server.pid: nothing to stop."; exit 0; }
PID=$(cat "$PIDFILE")
if ! kill -0 "$PID" 2>/dev/null; then
  echo "pid $PID is not running; removing the stale pid file."
  rm -f "$PIDFILE"; exit 0
fi
if ! ps -p "$PID" -o command= | grep -q uvicorn; then
  echo "pid $PID is not a uvicorn process; refusing to kill it. Remove data/server.pid by hand if it is stale." >&2
  exit 1
fi
kill -TERM "$PID"
i=0
while kill -0 "$PID" 2>/dev/null && [ $i -lt 100 ]; do i=$((i + 1)); sleep 0.1; done
if kill -0 "$PID" 2>/dev/null; then
  echo "pid $PID ignored SIGTERM for 10 s; sending SIGKILL."
  kill -KILL "$PID" 2>/dev/null || true
fi
rm -f "$PIDFILE"
echo "Raag Studio stopped (pid $PID)."
