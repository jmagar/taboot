# CLI App

Typer-based command surface for orchestrating crawl, extraction, graph, and
retrieval workflows. Acts as a thin shell over `packages/core` ports and the
adapter layer.

## Architecture

- Commands live in `apps/cli/commands/` (create the module when first command is
  added). Keep command functions small; call into `packages.core` use-cases.
- CLI schemas (argument and response DTOs) should reuse models from
  `packages.schemas` where possible.
- Shared utilities belong in `apps/cli/services/` or `apps/cli/dependencies/`
  once the structure is in place—avoid duplicating logic from adapters.

## Getting started

```bash
# Discover commands
uv run apps/cli --help

# Suggested alias
alias llama='uv run apps/cli'
llama ingest web https://example.com --limit 20
```

The CLI reads environment variables from `.env`. Use `uv run --env-file .env …`
to keep parity with the API and worker containers.

## Common commands

```bash
llama extract pending                # run tiered extractor on new docs
llama extract reprocess --since 7d   # re-run extraction for a window
llama graph query "MATCH ... RETURN ..."
llama query "what changed in auth?" --sources github --after 2025-01-01
```

Refer to the top-level `README.md` for additional workflow examples and to
`docs/CONFIGURATION.md` for all environment knobs.

## Environment

Most commands expect the same configuration as the API. Ensure `.env` provides
Firecrawl, Redis, Qdrant, Neo4j, and model endpoints. When adding new CLI
features, document required variables under `docs/CONFIGURATION.md` and update
the CLI help text.

## Testing

```bash
uv run pytest tests/cli -m "not slow"
uv run ruff check apps/cli
uv run mypy apps/cli
```

Place command-specific tests under `tests/cli/` mirroring the command module
layout. Add fixtures alongside tests when needed.
