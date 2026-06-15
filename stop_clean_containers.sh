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

FULL_CLEAN="${1:-}"  # use: --all

echo "Stopping and removing app/nginx containers (if they exist)..."
"$ENGINE" rm -f "$NGINX_NAME" "$APP_NAME" >/dev/null 2>&1 || true

echo "Removing project network (if it exists)..."
"$ENGINE" network rm "$NETWORK_NAME" >/dev/null 2>&1 || true

echo "Removing project volume (if it exists)..."
"$ENGINE" volume rm "$VOLUME_NAME" >/dev/null 2>&1 || true

if [ "$FULL_CLEAN" = "--all" ]; then
  echo "Removing app image (if it exists)..."
  "$ENGINE" rmi "$IMAGE_NAME" >/dev/null 2>&1 || true

  echo "Pruning dangling Docker resources..."
  "$ENGINE" system prune -f >/dev/null 2>&1 || true
fi

echo "Cleanup complete."
if [ "$FULL_CLEAN" = "--all" ]; then
  echo "Mode: full clean (--all)"
else
  echo "Mode: standard clean"
  echo "Tip: run with '--all' to also remove image and prune dangling resources"
fi
