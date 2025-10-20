See @../../CLAUDE.md for repository-wide conventions.

# Ingest Package Guidance

- Implement source adapters under `sources/` (e.g., Firecrawl, GitHub). Each
  should conform to ports/interfaces defined in `packages.core`.
- Handle normalization in dedicated modules (`normalizers/`, `chunkers/`) before
  passing documents downstream.
- Apply backpressure/rate limiting policies outlined in
  `apps/api/docs/BACKPRESSURE_RATELIMITING.md`. Keep concurrency knobs and retry
  logic tunable via configuration.
- Annotate ingested documents with provenance metadata (job IDs, namespaces).
- Coordinate with `packages/extraction` to ensure emitted document structures
  contain necessary fields.

# Testing & Quality

- Place tests under `tests/ingest/` mirroring source modules. Include fixtures
  for representative payloads.
- Run `uv run pytest tests/ingest -m "not slow"`, `uv run ruff check packages/ingest`,
  and `uv run mypy packages/ingest` before merging changes.
- Update project docs (`apps/api/docs/JOB_LIFECYCLE.md`, configuration guides) if
  ingestion behaviour changes.
