#!/usr/bin/env sh
set -eu

APP_NAME="matsedel-app"
NGINX_NAME="matsedel-nginx"
IMAGE_NAME="matsedel_app"
NETWORK_NAME="matsedel-net"
VOLUME_NAME="db-data"

if [ -n "${CONTAINER_CLI:-}" ]; then
  ENGINE="$CONTAINER_CLI"
elif command -v docker >/dev/null 2>&1; then
  ENGINE="docker"
elif command -v podman >/dev/null 2>&1; then
  ENGINE="podman"
else
  echo "Error: neither docker nor podman is available in PATH" >&2
  exit 1
fi

# Resolve absolute project path from this script's location.
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
NGINX_CONF="$PROJECT_DIR/nginx/default.conf"
STATIC_DIR="$PROJECT_DIR/static"

if [ ! -f "$NGINX_CONF" ]; then
  echo "Error: missing nginx config: $NGINX_CONF" >&2
  exit 1
fi

if [ ! -d "$STATIC_DIR" ]; then
  echo "Error: missing static directory: $STATIC_DIR" >&2
  exit 1
fi

echo "Stopping old containers (if any)..."
"$ENGINE" rm -f "$NGINX_NAME" "$APP_NAME" >/dev/null 2>&1 || true

echo "Creating network + volume..."
"$ENGINE" network create "$NETWORK_NAME" >/dev/null 2>&1 || true
"$ENGINE" volume create "$VOLUME_NAME" >/dev/null 2>&1 || true

echo "Building app image..."
"$ENGINE" build -t "$IMAGE_NAME" "$PROJECT_DIR"

echo "Starting app container..."
"$ENGINE" run -d --name "$APP_NAME" --network "$NETWORK_NAME" --network-alias app -v "$VOLUME_NAME:/app/data" "$IMAGE_NAME"

echo "Starting nginx container..."
"$ENGINE" run -d --name "$NGINX_NAME" --network "$NETWORK_NAME" -p 8081:80 -v "$NGINX_CONF:/etc/nginx/conf.d/default.conf:ro" -v "$STATIC_DIR:/app/static:ro" nginx:alpine

echo "Done. Open: http://localhost:8081"
