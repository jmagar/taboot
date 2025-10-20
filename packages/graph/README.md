# Packages / Graph

Neo4j adapter responsible for writing and querying the property graph defined in
`packages/graph/docs/GRAPH_SCHEMA.md`. Implements the ports declared in
`packages.core`.

## Layout

```
packages/graph/
├── README.md
├── docs/                  # Graph schema, migrations
├── client/                # Neo4j driver setup / session management
├── writers/               # Batched write logic (UNWIND, constraints)
├── queries/               # Cypher query helpers
├── migrations/            # Schema migration utilities
└── utils/                 # Helpers (serialization, retries)
```

## Key docs

- [`packages/graph/docs/GRAPH_SCHEMA.md`](../graph/docs/GRAPH_SCHEMA.md) – node
  labels, relationships, constraints, and Cypher patterns.
- [`apps/api/docs/DATA_GOVERNANCE.md`](../../apps/api/docs/DATA_GOVERNANCE.md) –
  purge/retention procedures that rely on graph operations.
- [`apps/api/docs/MIGRATIONS.md`](../../apps/api/docs/MIGRATIONS.md) – zero-downtime
  guidance for Neo4j changes.

## Guidelines

- Keep Cypher statements centralized in `queries/` or `writers/` for reuse.
- Batch writes per the migration doc (e.g., UNWIND with 1–5k rows, retry on
  deadlocks with jitter).
- Surface metrics (latency, deadlocks, node/relationship counts) via
  `packages.common` observability helpers.
- Mirror schema changes in `GRAPH_SCHEMA.md`, update migrations accordingly, and
  ensure they are idempotent/restart-safe.
