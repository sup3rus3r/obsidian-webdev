#!/usr/bin/env bash
# Start Qdrant for local dev. MongoDB is on Atlas — no local container needed.
# Idempotent — safe to run if Qdrant is already up.
set -e

start_container() {
  local name="$1"
  shift
  local run_args=("$@")

  if docker ps -q -f "name=^/${name}$" | grep -q .; then
    echo "[services] $name already running"
  elif docker ps -aq -f "name=^/${name}$" | grep -q .; then
    echo "[services] Restarting stopped $name container"
    docker start "$name"
  else
    echo "[services] Creating $name container"
    docker run -d --name "$name" --restart unless-stopped "${run_args[@]}"
  fi
}

start_container obsidian-qdrant \
  -p 6333:6333 \
  -v obsidian_qdrant_data:/qdrant/storage \
  qdrant/qdrant:latest

echo "[services] All services up"
