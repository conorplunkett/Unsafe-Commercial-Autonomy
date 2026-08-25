#!/usr/bin/env bash
# Start the Experiment Lab (FastAPI) and open it in the browser.
# Usage: ./scripts/lab.sh   [extra uvicorn args...]
set -euo pipefail

HOST="127.0.0.1"
PORT="${PORT:-8000}"
URL="http://${HOST}:${PORT}/lab"

# Prefer the repo venv's uvicorn; fall back to whatever is on PATH.
if [ -x "venv/bin/uvicorn" ]; then
  UVICORN="venv/bin/uvicorn"
else
  UVICORN="uvicorn"
fi

# Open the browser once the port is accepting connections, in the background.
(
  for _ in $(seq 1 60); do
    if nc -z "$HOST" "$PORT" 2>/dev/null; then
      # macOS `open`, else Linux `xdg-open`; ignore if neither exists.
      (command -v open >/dev/null && open "$URL") \
        || (command -v xdg-open >/dev/null && xdg-open "$URL") \
        || true
      break
    fi
    sleep 0.5
  done
) &

exec "$UVICORN" app.main:app --host "$HOST" --port "$PORT" --reload "$@"
