#!/usr/bin/env bash
set -euo pipefail

echo "[bootstrap] start"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

need_cmd() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[bootstrap] missing: $cmd"
    echo "[bootstrap] fix: $hint"
    exit 1
  fi
}

need_cmd "python3" "install Python 3.12+"
need_cmd "uv" "install uv: https://docs.astral.sh/uv/"
need_cmd "git" "install git"

if [[ ! -d ".venv" ]]; then
  echo "[bootstrap] creating venv"
  uv venv
fi

echo "[bootstrap] syncing deps"
uv sync

if [[ ! -f ".env" && -f ".env.example" ]]; then
  echo "[bootstrap] creating .env from example"
  cp .env.example .env
fi

echo "[bootstrap] applying db migrations"
uv run alembic upgrade head

echo "[bootstrap] running doctor"
uv run devlens doctor

echo "[bootstrap] verifying environment"
if ! uv run devlens verify-env; then
  echo "[bootstrap] verify-env reported issues"
  echo "[bootstrap] run: uv run devlens doctor --setup"
fi

echo "[bootstrap] done"
echo "[bootstrap] next: uv run devlens tui"
