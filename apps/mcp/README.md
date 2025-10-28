# MCP App

FastMCP server exposing Taboot workflows to MCP-compatible clients.
Implements the MCP transport shell; relies on `packages/core` for business
logic.

## Architecture

- MCP handlers should live in `apps/mcp/handlers/` (create when first handler is
  added). They bridge MCP requests to core use-cases.
- Shared schema definitions must come from `packages.schemas` to keep clients in
  sync.
- Keep transport concerns (authentication, connection lifecycle) within MCP
  modules; delegate business steps to ports.

## Running locally

```bash
uv run python -m taboot.mcp.server --help
uv run python -m taboot.mcp.server --port 8020
```

The `taboot-api` container runs the MCP server alongside the FastAPI surface.
Override its command or provide a supervisor if you need separate lifecycles.

## Configuration

MCP uses the same environment variables as the API/CLI. See
[`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) for required credentials.
Keep secrets in `.env` locally and rely on the compose stack for container
injection.

## Development notes

- Keep handlers thin; call into `packages/core` ports for orchestration.
- Add new capabilities alongside documentation updates so downstream MCP clients
  can adopt them quickly.
- Validate payload schemas against `packages/schemas` whenever contracts change.
- Document new MCP capabilities in the project README or a dedicated MCP guide so
  consumers know how to invoke them.
