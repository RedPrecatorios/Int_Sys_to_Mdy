#!/usr/bin/env bash
# Servidor HTTP para Ubuntu / cloud (escuta em todas as interfaces).
#
# Uso:
#   chmod +x scripts/run_server.sh
#   ./scripts/run_server.sh
#
# Ou com venv:
#   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
#   ./scripts/run_server.sh
#
# Variáveis opcionais: HOST (default 0.0.0.0), PORT (default 8000), WORKERS (default 1)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"

exec uvicorn main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
