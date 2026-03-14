#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="${RFPR_DEPLOY_DIR:-/opt/rf-passive-recorder}"
REMOVE_IMAGES="${REMOVE_IMAGES:-false}"

if [ ! -d "$DEPLOY_DIR" ]; then
  echo "Nothing to uninstall: $DEPLOY_DIR does not exist"
  exit 0
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  COMPOSE_CMD=()
fi

if [ ${#COMPOSE_CMD[@]} -gt 0 ] && [ -f "$DEPLOY_DIR/compose.yml" ]; then
  echo "Stopping and removing compose stack..."
  "${COMPOSE_CMD[@]}" -f "$DEPLOY_DIR/compose.yml" --env-file "$DEPLOY_DIR/.env" down --remove-orphans
else
  echo "Compose not found or compose.yml missing; skipping stack shutdown"
fi

if [ "$REMOVE_IMAGES" = "true" ]; then
  echo "Removing rf-passive-recorder image if present..."
  docker image rm rf-passive-recorder:local >/dev/null 2>&1 || true
fi

echo "Removing deployment directory: $DEPLOY_DIR"
rm -rf "$DEPLOY_DIR"

echo "Uninstall complete. Docker engine and unrelated resources were left intact."
