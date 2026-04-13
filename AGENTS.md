# AGENTS.md

## What This Repo Is (Current, Verified)
- DevLens is a Python 3.12, CLI-first local tool (Typer entrypoint: `devlens`) for static code analysis + Ollama-assisted critique + skill/feedback persistence.
- Runtime flow in code is: CLI command -> ingestion/scanning -> static AST/radon metrics -> LLM analysis (or fallback) -> skill scoring/feedback -> SQLite storage.
- Source root is `src/devlens`; tests are currently only under `tests/unit` (5 tests total at time of writing).

## High-Value Commands (Use These Exact Forms)
- Bootstrap: `uv venv && source .venv/bin/activate && uv sync && cp .env.example .env`
- CLI help: `uv run devlens --help`
- Analyze all allowed files under path: `uv run devlens analyze <path>`
- Analyze changed tracked files only: `uv run devlens analyze --changed <path>`
- Health check: `uv run devlens doctor`
- Lint/type/test (fast gate): `uv run ruff check . && uv run mypy src && uv run pytest -q`
- Run one test: `uv run pytest tests/unit/test_llm_parser.py -q`
- Collect tests only: `uv run pytest --collect-only -q`
- Apply DB migrations: `uv run alembic upgrade head`

## CLI + Behavior Gotchas Agents Usually Miss
- `devlens chat` takes files via `--files`; positional paths fail. Example: `uv run devlens chat --files src/devlens/main.py`.
- `analyze --changed` uses `git diff --name-only HEAD`; this excludes untracked files and includes tracked unstaged/staged changes vs `HEAD`.
- File scanning is constrained by `DEVLENS_PROJECT_ROOT` and `ensure_within_root(...)`; paths outside root raise errors.
- Scanner defaults to Python files only (`DEVLENS_ALLOWED_EXTENSIONS=.py`) and ignores directories including `.git`, `.venv`, caches, `build`, `dist`, and `alembic`.
- Analysis deduplicates by `(file_path, content_hash)` if a prior analysis row exists, and skips re-analysis in that case.

## Config + Environment Truths
- Config is loaded from `.env` via `python-dotenv` with `override=False`; existing shell env vars win over `.env`.
- Default DB URL is `sqlite:///devlens.db` (local file in repo root unless overridden).
- Qdrant is optional at runtime: if client/import is unavailable, retrieval falls back to SQLite-stored embeddings with local scoring.
- Caching is controlled by `DEVLENS_CACHE_ENABLED` and stored in `llm_cache_entries`.

## Database and Migration Notes
- SQLAlchemy models live in `src/devlens/storage/tables.py`; Alembic env wires metadata from `devlens.storage.db.Base`.
- Current migrations: `0001_create_initial_tables`, `0002_add_chat_cache_knowledge_tasks`.
- If DB exists but schema is stale/missing, run `uv run alembic upgrade head` before using analysis/chat workflows.

## Key Code Map (When You Need To Change Behavior)
- CLI wiring: `src/devlens/cli/app.py`
- Analyze command + summary output: `src/devlens/cli/commands/analyze.py`
- End-to-end analysis pipeline: `src/devlens/analysis/pipeline.py`
- Static parsing/metrics entrypoint: `src/devlens/analysis/static/python_ast.py`
- LLM calls + fallback + caching: `src/devlens/analysis/llm/client.py`
- File ingestion/filtering rules: `src/devlens/ingestion/file_scanner.py`
- Changed-file detection: `src/devlens/ingestion/git_diff.py`
- Chat/task workflow: `src/devlens/chat/service.py`
- Knowledge retrieval + Qdrant/SQLite fallback: `src/devlens/storage/repositories/knowledge.py`

## Agent Working Rules For This Repo
- Prefer executable truth (`pyproject.toml`, CLI help, code in `src/`) over design docs if they diverge.
- Keep changes local-first and offline-safe; avoid introducing network/service assumptions beyond existing Ollama/Qdrant optional behavior.
- Before finishing substantial edits, run: `uv run ruff check . && uv run mypy src && uv run pytest -q`.
