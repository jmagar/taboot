See @../../CLAUDE.md for repository-wide conventions.

# Graph Package Guidance

- Implement the ports declared in `packages.core` for graph persistence/querying.
- Centralize Neo4j driver management in `client/`. Use sessions/transactions
  responsibly; avoid long-lived sessions.
- Keep Cypher statements version-controlled in `queries/` and `writers/`.
- Be mindful of batching/transaction sizes (<=10k rows). Follow guidance in
  `GRAPH_SCHEMA.md`.
- Include migration utilities for constraints/indexes under `migrations/` and
  update docs when schema changes.

# Testing & Quality

- Add integration tests under `tests/graph/` (tagged appropriately) to validate
  queries and writers. Use Neo4j test containers or mocks where practical.
- Run `uv run pytest tests/graph -m "not slow"` (or the relevant marker),
  `uv run ruff check packages/graph`, and `uv run mypy packages/graph` before
  merging changes.
