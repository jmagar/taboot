# API App

FastAPI shell that exposes ingestion, crawl, and administration endpoints.
Business rules live in `packages/core`; this layer handles transport concerns
only.

## Architecture

- Routers live under `apps/api/routes/` and should stay thin—call into
  `packages/core` use-cases or adapter abstractions.
- Request/response payloads must be defined in `packages/schemas`. Import the
  shared models instead of redefining Pydantic classes locally.
- Long-running work (crawl, extraction, ingestion writes) should be delegated to
  background workers via core ports rather than run on the request thread.

## Key docs

- [`apps/api/docs/API.md`](../api/docs/API.md) – endpoint catalog and schemas.
- [`apps/api/docs/API_EXAMPLES.md`](../api/docs/API_EXAMPLES.md) – curl and Python
  snippets.
- [`apps/api/docs/JOB_LIFECYCLE.md`](../api/docs/JOB_LIFECYCLE.md) – crawl /
  ingestion state machine.
- [`apps/api/docs/OBSERVABILITY.md`](../api/docs/OBSERVABILITY.md),
  [`RUNBOOK.md`](../api/docs/RUNBOOK.md),
  [`SECURITY_MODEL.md`](../api/docs/SECURITY_MODEL.md),
  [`DATA_GOVERNANCE.md`](../api/docs/DATA_GOVERNANCE.md) for ops guidance.

## Local development

```bash
# CLI entry (FastAPI uvicorn dev server)
uv run uvicorn taboot.api.app:app --reload --port 8000

# Inspect OpenAPI once server is running
open http://localhost:4209/docs
```

Use the `taboot-app` service in `docker-compose.yaml` for a containerized stack.
It bundles API, MCP, and web dashboard processes; adjust the command in
`docker/api/Dockerfile` if you need a custom process manager.

## Environment

The API reads configuration from `.env` (or the compose stack). Key vars:

- `FIRECRAWL_API_URL`, `FIRECRAWL_API_KEY`
- `REDIS_URL`
- `QDRANT_URL`, `QDRANT_HTTP_PORT`, `QDRANT_GRPC_PORT`
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `TEI_EMBEDDING_URL`, `RERANKER_URL`, `OLLAMA_PORT`

See [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) for the complete list.

## Testing

```bash
uv run pytest tests/api -m "not slow"
uv run ruff check apps/api
uv run mypy apps/api
```

Add new endpoint coverage under `tests/api/` and update the docs in
`apps/api/docs/` when contracts change. Coordinate schema updates with
`packages/schemas` to keep generated clients in sync.
