#!/usr/bin/env bash
# Starts the API and the web app for local development, and stops both on Ctrl+C.
#
#   scripts/dev.sh                 API on :8000, web on :3000, in-memory data
#   DATABASE_URL=... scripts/dev.sh   the same against a database (see docs/DEVELOPMENT.md)
#
# TEST_MODE is on, so the rate limits are off and the test-only controls answer.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_port="${API_PORT:-8000}"
web_port="${WEB_PORT:-3000}"

export TEST_MODE="${TEST_MODE:-1}"
export SESSION_SECRET="${SESSION_SECRET:-dev-secret-change-me-before-sharing}"
export APP_ORIGIN="${APP_ORIGIN:-http://localhost:${web_port}}"
export API_URL="${API_URL:-http://127.0.0.1:${api_port}}"

port_busy() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

for port in "$api_port" "$web_port"; do
  if port_busy "$port"; then
    echo "Port $port is already in use. Stop the other process or set API_PORT / WEB_PORT." >&2
    exit 1
  fi
done

echo "Installing dependencies if needed..."
(cd "$root/backend" && uv sync --frozen >/dev/null)
(cd "$root/frontend" && pnpm install --frozen-lockfile >/dev/null)

pids=()
cleanup() {
  trap - INT TERM EXIT
  for pid in "${pids[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(cd "$root/backend" && exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$api_port" --reload) &
pids+=("$!")
(cd "$root/frontend" && exec ./node_modules/.bin/next dev --port "$web_port") &
pids+=("$!")

echo
echo "API  http://127.0.0.1:${api_port}/api/health"
echo "Web  http://localhost:${web_port}   (demo users are on the login screen)"
echo "Press Ctrl+C to stop both."
wait -n
