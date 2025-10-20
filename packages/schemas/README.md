# Packages / Schemas

Shared schema layer for the project. This package holds the canonical
Pydantic models, JSON Schema assets, and OpenAPI fragments that apps,
adapters, and clients import.

## Why it exists

- **Single source of truth** for request/response payloads and domain
  DTOs that cross process boundaries.
- **Generation hub** for downstream artifacts (OpenAPI spec, typed API
  clients, JSON schema bundles).
- **Framework-agnostic**: nothing in here should depend on FastAPI,
  LlamaIndex, or other runtime tooling so schemas stay reusable across
  API, CLI, MCP, and workers.

## Expected layout

```
packages/schemas/
├── README.md
├── docs/                # Schema docs, changelogs, migration notes
├── models/              # Pydantic BaseModel definitions
├── validators/          # Shared validators / field helpers
├── jsonschema/          # Generated JSON Schema files
└── openapi/             # OpenAPI fragments or bundler scripts
```

Populate directories as we formalize the extraction/ingestion contracts.
When adding new schemas:

1. Define the model in `models/`.
2. Export JSON Schema/OpenAPI as needed (scripts will live under
   `jsonschema/` or `openapi/`).
3. Document breaking changes in `docs/` so adapters and clients can
   coordinate version bumps.
4. Update API/MCP/CLI documentation if public payloads change (e.g.
   `apps/api/docs/API.md`, `apps/api/docs/JOB_LIFECYCLE.md`, CLI help text).
   Regenerate generated clients (`packages/clients`) once automation exists.

For reference on how these schemas flow through the stack, see:

- [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) for repository layout and
  layering guidelines.
- [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) for environment variables
  that drive schema-dependent services and clients.

## Testing

When schema tests land, place them under `tests/schemas/` mirroring the package
structure. Aim for backwards-compatibility checks (round-trip encoding,
validation of required fields) and add fixtures next to the tests that consume
them.
