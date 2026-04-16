#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-tui}"

if [[ ! -d ".venv" || ! -f ".env" ]]; then
  echo "[devlens.sh] setup missing, bootstrapping"
  bash scripts/bootstrap.sh
fi

if ! uv run devlens verify-env; then
  echo "[devlens.sh] verify-env failed"
  echo "[devlens.sh] run: uv run devlens doctor --setup"
  exit 1
fi

# Ensure global command uses editable install in development workflow.
if command -v devlens >/dev/null 2>&1; then
  uv tool install . --editable --force >/dev/null 2>&1 || true
fi

if [[ "$MODE" == "chat" ]]; then
  uv run devlens start --mode chat
else
  uv run devlens start --mode tui
fi
