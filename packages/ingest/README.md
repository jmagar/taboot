# Packages / Ingest

Adapters for pulling content from Firecrawl and other configured sources
(GitHub, Reddit, Docker Compose, etc.). Normalizes raw documents into the format
expected by extraction and vector pipelines.

## Layout

```
packages/ingest/
├── README.md
├── sources/             # Source-specific clients (firecrawl, github, etc.)
├── normalizers/         # HTML/markdown normalization, boilerplate removal
├── chunkers/            # Chunking strategies before embedding
├── services/            # Orchestration utilities (queues, retries)
└── utils/               # Helper functions
```

## Key docs

- [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) – ingestion plane overview
  and supported sources.
- [`apps/api/docs/JOB_LIFECYCLE.md`](../../apps/api/docs/JOB_LIFECYCLE.md) – job
  states and retry semantics that ingest adapters must honor.
- [`apps/api/docs/BACKPRESSURE_RATELIMITING.md`](../../apps/api/docs/BACKPRESSURE_RATELIMITING.md)
  – concurrency and throttle rules for crawlers.
- [`docs/CONFIGURATION.md`](../../docs/CONFIGURATION.md) – source-specific
  credentials and environment variables.

## Guidelines

- Implement ports defined in `packages.core` for ingestion workflows.
- Keep source-specific logic isolated so new sources can be added without
  affecting existing ones.
- Normalize documents (metadata, content) before handing them off to extraction.
- Respect backpressure and rate limiting policies defined in project docs
  (adaptive concurrency, robots handling, circuit breakers).
- Record provenance metadata (`job_id`, `namespace`, `sha256`) for every emitted
  document to enable deduplication downstream.
