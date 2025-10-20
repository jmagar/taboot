
# Schema Package Guidance

- Keep this package framework-agnostic: only Pydantic (and standard library)
  dependencies are allowed in `models/`.
- Treat each schema change as an API contract change. Update `docs/` with
  migration notes so adapters and generated clients can sync versions.
- Whenever you add or modify a model:
  1. Define or update the `BaseModel` inside `models/`.
  2. Regenerate JSON Schema / OpenAPI artifacts (add scripts under
     `jsonschema/` or `openapi/` as they come online).
  3. Bump any version markers the package exports once versioning is in place.
- Prefer explicit field `title`, `description`, and `examples` metadata so the
  generated JSON Schema is self-documenting.
- Avoid business logic—you should only model transport/domain DTOs that cross
  service boundaries.

# Testing & Validation

- Add schema-level tests under `tests/schemas/` (mirroring paths) to ensure
  backwards compatibility and serialization behaviour.
- Before opening a PR, run `uv run pytest tests/schemas -m "not slow"` once the
  test suite lands for this package.
