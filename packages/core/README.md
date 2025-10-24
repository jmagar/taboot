# Packages / Core

Domain layer: entities, value objects, and use-cases that encode business rules.
This package must remain framework-agnostic and only depend on `packages.schemas`
and `packages.common`.

## Layout

```
packages/core/
├── README.md
├── entities/        # Domain models / aggregates
├── value_objects/   # Immutable value objects
├── use_cases/       # Application services orchestrating workflows
└── services/        # Domain services / policies
```

**Note**: This is a single-user system. We use **direct imports** from adapter packages rather than abstract port interfaces. Adapters are imported directly in use-cases when needed.

Populate directories as we build out the ingestion → extraction → retrieval
flows. Keep modules small and cohesive.

## Key docs

- [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) – details the layering
  rule (`apps → adapters → core`).
- [`README.md`](../../README.md) – high-level pipelines and dependency
  boundaries.
- `packages/schemas/docs/` – contract definitions referenced by ports/use-cases.

## Guidelines

- No imports from apps (apps should import from core, not vice versa).
- **Direct imports from adapters are OK** - import from `packages.graph`, `packages.vector`, etc. as needed in use-cases.
- Use Pydantic models from `packages.schemas` for contract boundaries.
- Keep business rules here so they can be exercised via API, CLI, MCP, or tests
  without duplication.
- Target ≥85 % test coverage, especially for use-cases and domain services (see
  project testing guidelines in `AGENTS.md`).

## Example: Direct Import Pattern

```python
# packages/core/use_cases/ingest_document.py
from packages.graph.client import Neo4jClient
from packages.vector.qdrant_client import QdrantClient
from packages.schemas.models import Document, Chunk

class IngestDocumentUseCase:
    def __init__(self, graph: Neo4jClient, vector: QdrantClient):
        self.graph = graph
        self.vector = vector

    def execute(self, doc: Document) -> None:
        # Business logic here
        chunks = self._chunk_document(doc)
        self.graph.create_nodes(doc.to_nodes())
        self.vector.upsert_chunks(chunks)
```
