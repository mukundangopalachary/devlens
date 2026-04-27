.PHONY: bootstrap install verify doctor smoke lint type test package-test check start start-chat tui bundle clean

bootstrap:
	bash scripts/bootstrap.sh

install:
	uv tool install . --editable --force

verify:
	uv run devlens verify-env

doctor:
	uv run devlens doctor --setup

smoke:
	uv run devlens smoke-test --json

lint:
	uv run ruff check .

type:
	uv run mypy src

test:
	uv run pytest -q -m "not packaging"

package-test:
	uv build --wheel
	uv run pytest tests/unit/test_packaging_wheel.py -q
	CI=true uv run pytest tests/integration/test_packaging_integrity.py -q

check: lint type test package-test smoke

start:
	uv run devlens start --mode tui

start-chat:
	uv run devlens start --mode chat

tui:
	uv run devlens tui

bundle:
	bash scripts/release_bundle.sh

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist
