See @../../CLAUDE.md for repository-wide conventions.

# Retrieval Package Guidance

- Implement the ports from `packages.core` for retrieval/query answering. Keep
  LlamaIndex-specific code here.
- Organize modules by concern (`context/`, `indices/`, `retrievers/`,
  `query_engines/`). Avoid tightly coupling components so they can be swapped.
- Use configuration values (vector/reranker endpoints) from `packages.common`
  config loaders; do not hardcode URLs.
- Ensure outputs carry citation/provenance metadata expected by API/CLI/MCP.
- Monitor retrieval performance metrics and expose them via observability
  helpers.

# Testing & Quality

- Place tests in `tests/retrieval/`, covering hybrid retrieval flows and
  reranking. Use fixtures for Qdrant/Neo4j mocks or integration setups.
- Run `uv run pytest tests/retrieval -m "not slow"`, `uv run ruff check packages/retrieval`,
  and `uv run mypy packages/retrieval` when modifying this package.
- Update project docs (`docs/EVALUATION_PLAN.md`) if retrieval strategies or
  metrics change meaningfully.
