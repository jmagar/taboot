# Packages / Vector

Qdrant adapter implementing vector storage and retrieval logic. Aligns with the
schema described in `packages/vector/docs/VECTOR_SCHEMA.md` and implements ports
from `packages.core`.

## Layout

```
packages/vector/
├── README.md
├── docs/                  # Vector schema reference
├── client/                # Qdrant client/session setup
├── writers/               # Upsert/delete pipelines
├── queries/               # Vector search helpers
├── migrations/            # Collection/index management
└── utils/                 # Helpers (payload shaping, filters)
```

## Key docs

- [`packages/vector/docs/VECTOR_SCHEMA.md`](../vector/docs/VECTOR_SCHEMA.md) –
  collection configuration, payload schema, performance targets.
- [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) – Qdrant/TEI environment
  variables.
- [`docs/EVALUATION_PLAN.md`](../../docs/EVALUATION_PLAN.md) – retrieval metrics
  (recall, latency) influenced by vector configuration.

## Guidelines

- Centralize all Qdrant API interactions; keep the rest of the codebase
  framework-agnostic.
- Respect payload schema and namespacing strategy documented in
  `VECTOR_SCHEMA.md` (single collection with `namespace` payload field, chunk
  metadata, dedupe keys).
- Provide bulk upsert/delete utilities that ensure idempotency (`point_id =
  chunk_id`) and deduplication.
- Surface metrics (latency, throughput, point counts, optimizer status) through
  `packages.common` observability helpers.
- Coordinate with extraction and retrieval packages when payload fields change
  so hybrid search filters remain valid.
