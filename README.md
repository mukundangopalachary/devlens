# DevLens

DevLens is local-first CLI tool for analyzing coding activity, extracting skill signals, and generating targeted feedback.

Default model tuned for low-RAM setups: `gemma2:2b`.

## Stack

- Python 3.12
- Typer
- SQLite + SQLAlchemy
- Alembic
- `ast`, `libcst`, `radon`
- Ollama

## Installation

DevLens is designed to be installed as a system-wide command line tool.

1. Clone the repository and enter the directory.
2. Run the `make install` command to globally install DevLens via `uv`:

```bash
make install
```

This isolates dependencies and exposes the `devlens` command globally. You can now run `devlens` from any directory!

If the command isn't in your PATH, you can run:
```bash
uvx --from . devlens --help
```

To just bootstrap the environment locally without a global install:
```bash
make bootstrap
```

Environment verification:

```bash
uv run devlens verify-env
```

Smoke test:

```bash
uv run devlens smoke-test --json
```

One-command start:

```bash
uv run devlens start
```

Wrapper start (auto-bootstrap + verify):

```bash
bash scripts/devlens.sh
```

Local release bundle:

```bash
bash scripts/release_bundle.sh
```

Make targets:

```bash
make bootstrap
make check
make start
```

`make test` runs non-packaging tests only.
`make check` includes wheel packaging sanity test.
CI runs non-packaging tests first, then packaging tests after wheel build.

Run TUI:

```bash
uv run devlens tui
```

TUI controls and troubleshooting: [docs/tui.md](docs/tui.md)
Setup details: [docs/setup.md](docs/setup.md)

Architecture blueprint: [docs/blueprint/blueprint.md](docs/blueprint/blueprint.md)
