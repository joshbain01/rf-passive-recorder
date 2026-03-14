#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RFPR_REPO_URL:-https://github.com/joshbain01/rf-passive-recorder.git}"
DEPLOY_DIR="${RFPR_DEPLOY_DIR:-/opt/rf-passive-recorder}"
BRANCH="${RFPR_BRANCH:-main}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

require_cmd git
require_cmd docker

mkdir -p "$DEPLOY_DIR"

if [ -d "$DEPLOY_DIR/.git" ]; then
  echo "Updating existing repository at $DEPLOY_DIR"
  git -C "$DEPLOY_DIR" fetch --all --tags
  git -C "$DEPLOY_DIR" checkout "$BRANCH"
  git -C "$DEPLOY_DIR" pull --ff-only origin "$BRANCH"
else
  if [ -n "$(find "$DEPLOY_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null || true)" ]; then
    echo "ERROR: $DEPLOY_DIR exists and is not an rf-passive-recorder git checkout." >&2
    echo "Refusing to overwrite existing files." >&2
    exit 1
  fi
  echo "Cloning repository into $DEPLOY_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
fi

mkdir -p "$DEPLOY_DIR/config" "$DEPLOY_DIR/data"

if [ ! -f "$DEPLOY_DIR/config/settings.yaml" ]; then
  cp "$DEPLOY_DIR/config/settings.example.yaml" "$DEPLOY_DIR/config/settings.yaml"
  sed -i 's|data_dir: ./data|data_dir: /data|' "$DEPLOY_DIR/config/settings.yaml"
  sed -i 's|host: 127.0.0.1|host: 0.0.0.0|' "$DEPLOY_DIR/config/settings.yaml"
  echo "Seeded $DEPLOY_DIR/config/settings.yaml"
else
  echo "Config already exists: $DEPLOY_DIR/config/settings.yaml"
fi

if [ ! -f "$DEPLOY_DIR/.env" ]; then
  cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
  sed -i "s/^RFPR_UID=.*/RFPR_UID=$(id -u)/" "$DEPLOY_DIR/.env"
  sed -i "s/^RFPR_GID=.*/RFPR_GID=$(id -g)/" "$DEPLOY_DIR/.env"
  echo "Created $DEPLOY_DIR/.env"
else
  echo ".env already exists: $DEPLOY_DIR/.env"
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "ERROR: Docker Compose plugin not found (docker compose / docker-compose)." >&2
  exit 1
fi

echo "Building image..."
"${COMPOSE_CMD[@]}" -f "$DEPLOY_DIR/compose.yml" --env-file "$DEPLOY_DIR/.env" build

echo "Initializing database..."
"${COMPOSE_CMD[@]}" -f "$DEPLOY_DIR/compose.yml" --env-file "$DEPLOY_DIR/.env" run --rm rf-passive-recorder init-db --config /config/settings.yaml

echo "\nSetup complete. Next steps:"
echo "  1) Review config:   $DEPLOY_DIR/config/settings.yaml"
echo "  2) Start service:   cd $DEPLOY_DIR && docker compose up -d"
echo "  3) Follow logs:     cd $DEPLOY_DIR && docker compose logs -f"
echo "  4) Health check:    curl http://127.0.0.1:\$(grep '^RFPR_API_PORT=' "$DEPLOY_DIR/.env" | cut -d= -f2)/healthz"
echo "  5) Uninstall later: $DEPLOY_DIR/uninstall_rfpr_docker.sh"
