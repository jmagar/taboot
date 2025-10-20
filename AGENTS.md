# Repository Guidelines

## Project Structure & Module Organization
- `apps/api`, `apps/cli`, `apps/mcp`, `apps/web`: transport shells; push all orchestration into adapters and core services.
- `packages/core` defines business flows; adapter packages (`ingest`, `extraction`, `graph`, `vector`, `retrieval`, `clients`, `common`, `schemas`) integrate with Firecrawl, Neo4j, Qdrant, and TEI.
- `tests/` mirrors the package tree; keep fixtures near their usage. `docs/` holds runbooks and `docker/` houses service images and overrides.

## Build, Test, and Development Commands
- `uv sync` — install Python workspace deps; rerun after editing `pyproject.toml`.
- `pnpm install` — hydrate the optional web dashboard and generated API clients.
- `docker compose up -d` — start Neo4j, Qdrant, Redis, TEI, Ollama, and Firecrawl.
- `uv run apps/cli --help` — list workflows; `uv run apps/cli ingest web https://example.com --limit 20` is a reliable smoke crawl.
- `uv run pytest -m "not slow"` (add `--cov=packages` when auditing coverage).
- `uv run ruff check .` and `uv run mypy .` — lint and type-check before every PR.

## Coding Style & Naming Conventions
- Ruff enforces formatting and imports (line length 100); avoid `noqa` except for documented edge cases.
- Python modules stay snake_case, classes PascalCase, constants upper snake; name adapters for their external system (`neo4j_writer.py`, `qdrant_client.py`).
- Preserve the dependency rule: apps → adapters → core. If a change needs a reverse import, add a new port in `packages/core` instead.

## Testing Guidelines
- Place tests under `tests/<package>/<module>/test_*.py`; prefer lightweight fixtures over static payloads.
- Use the configured markers (`unit`, `integration`, `slow`, `firecrawl`, `github`, etc.) so CI selects the right layers; skip GPU-heavy suites unless required.
- Target ≥85 % coverage in `packages/core` and extractor logic; log intentional gaps in the PR checklist.

## Commit & Pull Request Guidelines
- Repository snapshot lacks history; default to Conventional Commits (`feat:`, `fix:`, `docs:`) to stay aligned with upstream automation.
- Keep commits focused on a single concern and note the executed test command in the body.
- PRs need a summary, linked issue or doc, test output, and screenshots or CLI samples for behavior changes; request both core and adapter reviewers for cross-layer work.

## Environment & Security Notes
- Copy `.env.example` to `.env`; inject secrets at runtime via `uv run --env-file .env …` and avoid baking credentials into Docker images.
- Rotate Firecrawl, Neo4j, and Qdrant tokens quarterly; scrub PII from logs before checking fixtures into `docs/` or `tests/fixtures`.
