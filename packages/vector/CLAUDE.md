See @../../CLAUDE.md for repository-wide conventions.

# Vector Package Guidance

- Implement vector storage/search ports defined in `packages.core`.
- Use `client/` for Qdrant connection management. Configure endpoints via
  environment loaders (`packages.common`).
- Keep upsert/delete logic in `writers/` and query helpers in `queries/`.
- Ensure payloads match `docs/VECTOR_SCHEMA.md` and include provenance metadata
  (namespace, job_id, sha256, etc.).
- Monitor performance targets (≥5k vectors/sec upsert) and expose metrics.

# Testing & Quality

- Add tests under `tests/vector/` for upsert/query behaviour. Use Qdrant test
  containers or mocks where practical.
- Run `uv run pytest tests/vector -m "not slow"`, `uv run ruff check packages/vector`,
  and `uv run mypy packages/vector` before submitting changes.
- Update the schema doc when payload fields or collection settings change.
