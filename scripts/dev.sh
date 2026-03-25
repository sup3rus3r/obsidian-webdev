#!/usr/bin/env bash
# Dev entrypoint — starts services, runs frontend + backend, shuts everything down on exit.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Ensure uv is on PATH (installed to ~/.local/bin on Windows/Linux)
export PATH="$HOME/.local/bin:$PATH"

cleanup() {
  # Remove trap first to prevent double-run on EXIT + INT
  trap - INT TERM EXIT
  echo ""
  echo "[obsidian-webdev] Shutting down services..."
  docker stop obsidian-qdrant 2>/dev/null && echo "[obsidian-webdev] obsidian-qdrant stopped." || true
  echo "[obsidian-webdev] Done."
}

trap cleanup INT TERM EXIT

# Ensure backend venv is up to date (idempotent, fast if nothing changed)
echo "[obsidian-webdev] Syncing backend dependencies..."
(cd "$PROJECT_ROOT/backend" && uv sync --quiet)

# Start background services (Qdrant, etc.)
bash "$SCRIPT_DIR/start-services.sh"

# Run frontend + backend concurrently (inherits terminal — Ctrl+C propagates)
npx concurrently \
  --names "frontend,backend" \
  --prefix-colors "cyan,green" \
  "npm run dev --prefix \"$PROJECT_ROOT/frontend\"" \
  "PYTHONUNBUFFERED=1 uv run --directory \"$PROJECT_ROOT/backend\" uvicorn main:app --port 7412 --reload --reload-dir \"$PROJECT_ROOT/backend\" --reload-exclude \"$PROJECT_ROOT/backend/.venv\" --reload-exclude \"$PROJECT_ROOT/backend/data\" --ws-ping-interval 120 --ws-ping-timeout 30"
