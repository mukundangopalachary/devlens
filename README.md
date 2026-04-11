# DevLens

DevLens is local-first CLI tool for analyzing coding activity, extracting skill signals, and generating targeted feedback.

## Stack

- Python 3.12
- Typer
- SQLite + SQLAlchemy
- Alembic
- `ast`, `libcst`, `radon`
- Ollama

## Bootstrap

```bash
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

Run CLI:

```bash
uv run devlens --help
```

Architecture blueprint: [docs/apt/blueprint.md](docs/apt/blueprint.md)

