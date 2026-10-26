#!/bin/sh
# Double-click in Finder to open DJ Lab. A newly started server lives with this window.
set -eu
RAAG_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$RAAG_ROOT"
RAAG_DJ_URL="http://127.0.0.1:8477/dj.html"
if curl -sf --max-time 2 http://127.0.0.1:8477/api/dj/catalog >/dev/null 2>&1; then
  open "$RAAG_DJ_URL"
  exit 0
fi
"$RAAG_ROOT/app/.venv/bin/python" -m uvicorn app.backend.main:create_app --factory --host 127.0.0.1 --port 8477 &
RAAG_DJ_PID=$!
trap 'kill "$RAAG_DJ_PID" 2>/dev/null || true' EXIT HUP INT TERM
RAAG_DJ_TRIES=0
while [ "$RAAG_DJ_TRIES" -lt 40 ]; do
  if curl -sf --max-time 1 http://127.0.0.1:8477/api/dj/catalog >/dev/null 2>&1; then
    open "$RAAG_DJ_URL"
    printf '%s\n' 'DJ Lab is ready. Keep this Terminal window open while using it.'
    wait "$RAAG_DJ_PID"
    exit 0
  fi
  if ! kill -0 "$RAAG_DJ_PID" 2>/dev/null; then
    printf '%s\n' 'The app could not start. Check the error above; port 8477 may already be in use.'
    exit 1
  fi
  RAAG_DJ_TRIES=$((RAAG_DJ_TRIES+1))
  sleep .25
done
printf '%s\n' 'The app did not become ready. Check the error above.'
exit 1
