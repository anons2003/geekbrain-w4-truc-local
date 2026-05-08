#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

uv run uvicorn app.main:app --host 127.0.0.1 --port 8080
