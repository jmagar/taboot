# API App Guidance

- FastAPI shell only—never put business logic here. Import use-cases from
  `packages.core` and DTOs from `packages.schemas`.
- Define routes under `apps/api/routes/`. Organize by resource (e.g.,
  `jobs.py`, `ingestions.py`), and keep handlers thin.
- Shared request/response models belong in `packages/schemas`. Local
  Pydantic classes should be limited to transport-only helpers.
- Use dependency modules (`apps/api/dependencies/`) for auth, DB sessions, and
  other cross-route dependencies. Avoid global state.
- Long-running operations should be delegated to workers via core ports; do not
  block the event loop.
- Update the docs in `apps/api/docs/` and the top-level README when contracts
  change. Regenerate OpenAPI (`openapi.yaml`) as part of the workflow.
- Enforce structured JSON logging (see `apps/api/docs/OBSERVABILITY.md`). Use
  request IDs and job IDs consistently so downstream systems can correlate logs.
- Apply the auth policy described in `apps/api/docs/SECURITY_MODEL.md`—require
  `X-API-Key` headers for privileged routes and scope checks for namespace-bound
  resources. Wire new dependencies through the auth dependency module rather than
  inspecting headers inline.
- When introducing new endpoints, document lifecycle transitions in
  `apps/api/docs/JOB_LIFECYCLE.md` (crawl/ingestion) and backpressure behaviour in
  `apps/api/docs/BACKPRESSURE_RATELIMITING.md` if applicable.
- Follow response envelope conventions (`{"data": ..., "error": ...}`) and use
  canonical error codes as listed in `apps/api/docs/API.md`.

# Testing & Quality

- Add endpoint coverage under `tests/api/` mirroring route modules.
- Run `uv run pytest tests/api -m "not slow"`, `uv run ruff check apps/api`,
  and `uv run mypy apps/api` before submitting changes.
- Ensure new schemas are reflected in `packages/schemas` and that generated
  clients stay in sync.
