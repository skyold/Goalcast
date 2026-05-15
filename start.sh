#!/bin/bash
set -euo pipefail

CMD="${1:-help}"
shift 2>/dev/null || true

BUILD_FLAG=""
for arg in "$@"; do
  [ "$arg" = "--build" ] && BUILD_FLAG="--build"
done

case "$CMD" in
  start)
    docker compose up -d $BUILD_FLAG
    ;;
  stop)
    docker compose down
    ;;
  logs)
    docker compose logs -f
    ;;
  build)
    docker compose build
    ;;
  *)
    echo "Usage: ./start.sh <command> [--build]"
    echo ""
    echo "  start [--build]   Start all services (rebuild images with --build)"
    echo "  stop              Stop all services"
    echo "  logs              Follow logs from all services"
    echo "  build             Build images without starting"
    ;;
esac
