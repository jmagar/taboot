See @../../CLAUDE.md for repository-wide conventions.

# MCP App Guidance

- Keep the MCP server as a thin transport layer. Implement request handlers in
  `apps/mcp/handlers/` (module to be created) and forward work to
  `packages.core` use-cases.
- Reuse schema definitions from `packages.schemas` for payloads exchanged with
  MCP clients.
- Follow authentication/authorization policies consistent with the API (namespace
  scoping, API keys if applicable).
- When introducing new MCP capabilities, document them in `apps/mcp/README.md`
  and update client-facing docs so downstream users know how to call them.
- Ensure long-running jobs are delegated to worker queues via core ports.

# Testing & Quality

- Add tests under `tests/mcp/` once the suite is scaffolded. Cover handler
  behaviour, validation, and error propagation.
- Run `uv run pytest tests/mcp -m "not slow"`, `uv run ruff check apps/mcp`,
  and `uv run mypy apps/mcp` before submitting changes.
- Coordinate schema updates with `packages/schemas` to keep MCP clients in sync.
