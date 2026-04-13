#!/usr/bin/env bash
set -euo pipefail

# Modular commit helper for DevLens.
# Usage: bash git.sh

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside git repository."
  exit 1
fi

if ! git diff --cached --quiet; then
  echo "Staged changes already present."
  echo "Please commit/stash/unstage first, then run again."
  exit 1
fi

get_changed_files() {
  {
    git diff --name-only
    git diff --name-only --cached
    git ls-files --others --exclude-standard
  } | awk 'NF' | sort -u
}

contains_blocked_files() {
  local blocked
  blocked="$(get_changed_files | grep -E '(^|/)\.env($|\.)|credentials|secret|token' || true)"
  if [[ -n "$blocked" ]]; then
    echo "Potential secret-like files detected."
    echo "$blocked"
    echo "Handle manually. Script stopped."
    return 0
  fi
  return 1
}

commit_group() {
  local label="$1"
  local message="$2"
  local pattern="$3"

  mapfile -t files < <(get_changed_files | grep -E "$pattern" || true)
  if [[ ${#files[@]} -eq 0 ]]; then
    echo "[$label] no matching changes"
    return 0
  fi

  git add -- "${files[@]}"
  if git diff --cached --quiet; then
    echo "[$label] nothing staged"
    return 0
  fi

  git commit -m "$message"
  echo "[$label] committed"
}

if contains_blocked_files; then
  exit 1
fi

# 1) foundation
commit_group \
  "foundation" \
  "foundation: establish baseline project plumbing and contracts" \
  '^(src/devlens/(config|core|security|storage/(db|tables)\.py)|alembic/versions/0001_.*\.py|pyproject\.toml|README\.md)$'

# 2) static analysis
commit_group \
  "static-analysis" \
  "static-analysis: improve scan and analysis pipeline behavior" \
  '^(src/devlens/(analysis/static|analysis/pipeline\.py|ingestion/)|tests/unit/test_(static_analysis|file_scanner).*\.py)'

# 3) llm/skills/feedback
commit_group \
  "llm-skills-feedback" \
  "llm-skills-feedback: refine model handling, scoring, and feedback generation" \
  '^(src/devlens/(analysis/llm|skills/|feedback/|cache/)|tests/unit/test_llm_parser\.py)'

# 4) chat/knowledge/tasks
commit_group \
  "chat-knowledge-tasks" \
  "chat-knowledge-tasks: improve chat flow, retrieval persistence, and task lifecycle" \
  '^(src/devlens/(chat/|storage/repositories/(chat|knowledge)\.py|cli/commands/(ask|ingest|tasks|sessions)\.py)|tests/unit/test_(chat|knowledge|json_error_contract).*\.py|alembic/versions/000[234]_.*\.py)'

# 5) doctor/qdrant
commit_group \
  "doctor-qdrant" \
  "doctor-qdrant: strengthen diagnostics and vector backend observability" \
  '^(src/devlens/(health\.py|retrieval/|cli/commands/(doctor|reindex)\.py)|tests/unit/test_(json_contract|reindex_command).*\.py)'

# extra: watch mode
commit_group \
  "watch-mode" \
  "watch: add polling watcher with queued background analysis" \
  '^(src/devlens/(watch/|cli/commands/watch\.py)|tests/unit/test_watch_service\.py)'

# extra: tui scaffold
commit_group \
  "tui-scaffold" \
  "tui: scaffold bubble tea interface with session and ingest pickers" \
  '^(tui/|src/devlens/cli/commands/tui\.py|docs/tui\.md)$'

# final catch-all
mapfile -t remaining < <(get_changed_files)
if [[ ${#remaining[@]} -gt 0 ]]; then
  git add -- "${remaining[@]}"
  if ! git diff --cached --quiet; then
    git commit -m "chore: commit remaining project updates"
    echo "[remaining] committed"
  fi
fi

echo "Done. Modular commit pass complete."
