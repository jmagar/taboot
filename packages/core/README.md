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
├── ports/           # Interfaces implemented by adapters
└── services/        # Domain services / policies
```

Populate directories as we build out the ingestion → extraction → retrieval
flows. Keep modules small and cohesive.

## Key docs

- [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) – details the layering
  rule (`apps → adapters → core`).
- [`README.md`](../../README.md) – high-level pipelines and dependency
  boundaries.
- `packages/schemas/docs/` – contract definitions referenced by ports/use-cases.

## Guidelines

- No imports from apps or adapter packages.
- Define ports (interfaces) for adapter functionality (e.g., Firecrawl reader,
  Neo4j writer, Qdrant client) and keep them decoupled from implementation
  details.
- Use Pydantic models from `packages.schemas` for contract boundaries.
- Keep business rules here so they can be exercised via API, CLI, MCP, or tests
  without duplication.
- Target ≥85 % test coverage, especially for use-cases and domain services (see
  project testing guidelines in `AGENTS.md`).
