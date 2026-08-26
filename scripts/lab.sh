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

# Refuse to start a second Lab on the same port. Two uvicorn --reload
# processes watching the same app/ directory step on each other's file
# writes and each other's restarts, which reads as a mystery reload loop.
if nc -z "$HOST" "$PORT" 2>/dev/null; then
  echo "Something is already listening on ${HOST}:${PORT} — is the Lab already running?" >&2
  echo "Check with: ps aux | grep uvicorn" >&2
  exit 1
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

# --reload-dir app scopes hot-reload to the Python source. A bare --reload
# watches the whole tree, so every run written to or deleted from runtime/runs/
# (each "Run experiment" and each delete in the Lab) restarts the server
# mid-request — which blanked the Runs tab on delete and thrashed the terminal.
exec "$UVICORN" app.main:app --host "$HOST" --port "$PORT" --reload --reload-dir app "$@"
