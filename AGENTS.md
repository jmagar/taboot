# Repository Guidelines

## Project Structure & Module Organization
Core logic lives in `src/llamacrawl/`, organized by feature: ingestion readers, embedding pipelines, storage adapters, and CLI entry points (`cli.py`, `cli_firecrawl.py`). Shared helpers sit under `utils/`. Tests mirror the layout in `tests/` with `unit/`, `integration/`, and `perf/` suites plus `conftest.py` fixtures. Documentation and configuration templates reside in `docs/`, while container assets are under `docker/` and `postgres/`. Use `scripts/` for standalone utilities such as auth helpers.

## Build, Test, and Development Commands
Sync dependencies with `uv sync` (respects `pyproject.toml` and `uv.lock`). Run the CLI in place via `uv run llamacrawl --help`. Use `uv run pytest` for the full test suite, or target markers like `uv run pytest -m "unit and not slow"`. Lint and format imports with `uv run ruff check src tests`. Type-check critical changes using `uv run mypy src tests`. When services are required, start the stack with `docker compose up -d`.

## Coding Style & Naming Conventions
The codebase targets Python 3.11 with Ruff enforcing a 100-character line limit and standard `black`-compatible formatting; prefer one import per line as Ruff’s `I` rule mandates. Follow strict MyPy typing—new functions should be fully annotated. Use `snake_case` for modules, functions, and variables, `PascalCase` for classes, and `SCREAMING_SNAKE_CASE` for constants. Keep CLI command names verb-based (`ingest`, `query`) and align new Typer commands with existing patterns.

## Testing Guidelines
Write fast unit tests under `tests/unit/` and integration scenarios in `tests/integration/`—mark them with `@pytest.mark.integration` to allow targeted runs. Favor descriptive test names like `test_<module>_<behavior>`. Maintain meaningful fixtures in `conftest.py` rather than duplicating setup. Use `--cov=llamacrawl` when validating coverage locally, and ensure new features include both happy-path and failure cases.

## Commit & Pull Request Guidelines
Adopt conventional commit prefixes observed in history (`feat:`, `fix:`, `refactor:`) followed by a concise summary. Group related changes per commit and avoid mixing refactors with feature work. Pull requests should link relevant issues, describe the change, outline test coverage (`pytest`, `ruff`, `mypy`), and include screenshots or logs for CLI-facing updates. Flag migrations or infrastructure changes that require operator action.

## Configuration & Security Notes
Never commit credentials; use `.env` and `config.yaml` copied from the `docs/` templates. Document any new environment variables in `docs/configuration.md`. When handling external APIs (GitHub, Gmail, Reddit), ensure rate limits and token scopes are noted in the PR so deployers can review access implications.
