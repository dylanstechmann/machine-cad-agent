#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command="${1:-demo}"
if [[ $# -gt 0 ]]; then shift; fi
case "$command" in
  demo)
    docker compose build dev
    docker compose run --rm dev python -m machine_cad demo
    docker compose up -d viewer
    echo 'Viewer: http://127.0.0.1:8765'
    ;;
  test) docker compose run --rm dev python -m unittest discover -s tests -v ;;
  stop) docker compose stop viewer ;;
  *) docker compose run --rm dev python -m machine_cad "$command" "$@" ;;
esac
