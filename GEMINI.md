# DevLens: Project Context & Instructions

DevLens is a local-first, CLI-driven developer skill analysis tool. It uses static analysis and local LLMs (via Ollama) to extract skill signals from code and generate targeted feedback.

## Project Overview

- **Core Purpose:** Analyze coding activity, extract skill signals, and generate feedback locally and privately.
- **Main Technologies:**
    - **Language:** Python 3.12+
    - **Package Manager:** `uv`
    - **CLI:** `typer`
    - **Database:** SQLite with SQLAlchemy 2.0 ORM and Alembic migrations.
    - **Static Analysis:** `ast`, `libcst`, `radon`.
    - **LLM Runtime:** Ollama (local-only).
    - **Vector Store:** Qdrant (optional, with SQLite fallback).
    - **TUI:** Custom TUI implemented in Go (located in `tui/`).
- **Architecture:** Modular monolith following a pipeline:
  `Ingestion -> Static Analysis -> LLM Analysis -> Skill Extraction -> Feedback Generation -> SQLite/Qdrant Storage`.

## Building and Running

### Setup and Bootstrap
The project uses `uv` for dependency management. A bootstrap script is provided:
```bash
# Recommended one-command bootstrap
bash scripts/bootstrap.sh

# Manual setup
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env
uv run alembic upgrade head
```

### Key CLI Commands
- **Main Entry:** `uv run devlens [COMMAND]`
- **Analyze Code:**
    - Entire path: `uv run devlens analyze <path>`
    - Changed files only: `uv run devlens analyze --changed <path>` (uses `git diff --name-only HEAD`)
- **Interactive Chat:** `uv run devlens chat --files <path>`
- **View Skills/History:** `uv run devlens skills` or `uv run devlens history`
- **TUI:** `uv run devlens tui`
- **Health Checks:** `uv run devlens doctor` and `uv run devlens verify-env`

### Database Migrations
Always ensure migrations are up to date:
```bash
uv run alembic upgrade head
```

## Development Conventions

### Code Style and Quality
- **Linting & Formatting:** Use `ruff`. Run `uv run ruff check .`.
- **Type Checking:** Use `mypy`. Run `uv run mypy src`.
- **Pre-flight Check:** `uv run ruff check . && uv run mypy src && uv run pytest -q`.

### Testing
- **Framework:** `pytest`.
- **Location:** `tests/unit/` and `tests/integration/`.
- **Running Tests:** `uv run pytest`.

### Configuration
- Config is managed via `pydantic-settings` (effectively) in `src/devlens/config.py`.
- Defaults are in code, overrides in `.env` (managed by `python-dotenv`, `override=False`).
- Key variables: `DEVLENS_DB_URL`, `DEVLENS_OLLAMA_MODEL`, `DEVLENS_PROJECT_ROOT`.

### Important Gotchas
- **File Access:** Analysis is restricted to files within `DEVLENS_PROJECT_ROOT`.
- **Supported Files:** Defaults to `.py` files. Configurable via `DEVLENS_ALLOWED_EXTENSIONS`.
- **Deduplication:** Analysis is skipped for a file if the `(path, content_hash)` pair already exists in the database.
- **Chat Command:** Requires `--files` flag for positional paths (e.g., `uv run devlens chat --files main.py`).

## Directory Structure

- `src/devlens/`: Main Python source code.
    - `cli/`: Typer command definitions.
    - `analysis/`: Static analysis (`static/`) and LLM (`llm/`) logic.
    - `ingestion/`: File scanning and git diff logic.
    - `skills/`: Taxonomy and scoring engine.
    - `storage/`: SQLAlchemy models (`tables.py`) and repositories.
- `alembic/`: Database migrations.
- `tui/`: Go-based TUI source code.
- `docs/`: Design documents, blueprints, and setup guides.
- `scripts/`: Utility scripts for bootstrap and execution.
- `tests/`: Unit and integration tests.
