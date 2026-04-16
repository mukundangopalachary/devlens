# DevLens Setup

## One-command bootstrap

```bash
bash scripts/bootstrap.sh
```

Or with Make:

```bash
make bootstrap
```

What script does:

- checks required tools (`python3`, `uv`, `git`)
- creates `.venv` if missing
- runs `uv sync`
- creates `.env` from `.env.example` if missing
- runs DB migrations
- runs doctor

## One-command start

```bash
uv run devlens start
```

For active development (recommended), install tool in editable mode:

```bash
uv tool install . --editable --force
```

Reason: package uses src layout + many local modules. Editable install avoids stale wheel issues.

Or with Make:

```bash
make start
make start-chat
```

Modes:

- `uv run devlens start --mode tui`
- `uv run devlens start --mode chat`

Or use wrapper (auto-bootstrap + verify + start):

```bash
bash scripts/devlens.sh
bash scripts/devlens.sh chat
```

## Reproducibility checks

```bash
uv run devlens doctor --setup
uv run devlens verify-env
uv run devlens smoke-test --json
uv run ruff check .
uv run mypy src
uv run pytest -q
```

Or run all quickly:

```bash
make check
```

Packaging sanity check:

```bash
uv build --wheel
uv run pytest tests/unit/test_packaging_wheel.py -q
```

Strict smoke test (includes ask path):

```bash
uv run devlens smoke-test --strict --json
```

## Release bundle (local archive)

```bash
bash scripts/release_bundle.sh
```

Output goes to `dist/devlens_bundle_<timestamp>.tar.gz`.
Checksum goes to `dist/devlens_bundle_<timestamp>.tar.gz.sha256` when checksum tool exists.

## Offline install checklist

On target machine:

1. Unpack bundle tarball.
2. Verify checksum:
   - `sha256sum -c devlens_bundle_<timestamp>.tar.gz.sha256`
3. Enter project directory.
4. Run bootstrap:
   - `bash scripts/bootstrap.sh`
5. Verify:
   - `uv run devlens verify-env`
   - `uv run devlens smoke-test --json`
6. Start:
   - `bash scripts/devlens.sh`

## Common fixes

- DB/schema missing:
  - `uv run alembic upgrade head`
- Ollama not ready:
  - `ollama serve`
  - `ollama pull llama3.2:3b`
  - `ollama pull nomic-embed-text`
- Qdrant index stale:
  - `uv run devlens reindex`
