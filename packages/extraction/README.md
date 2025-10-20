# Packages / Extraction

Implements the tiered extraction pipeline described in
`packages/extraction/docs/EXTRACTION_SPEC.md`. Converts normalized documents into
graph entities/relations via deterministic, NLP, and LLM stages.

## Layout

```
packages/extraction/
├── README.md
├── docs/                     # Specification and design notes
├── pipelines/                # Orchestration glue between tiers
├── tier_a/                   # Deterministic extractors (regex, parsers)
├── tier_b/                   # spaCy-based extraction components
├── tier_c/                   # LLM window extraction
├── services/                 # Shared services (queueing, caching)
└── utils/                    # Helper modules (normalization, batching)
```

## Key docs

- [`packages/extraction/docs/EXTRACTION_SPEC.md`](../extraction/docs/EXTRACTION_SPEC.md)
  – canonical design and performance targets (Tier A/B/C throughput, caching,
  versioning).
- [`apps/api/docs/JOB_LIFECYCLE.md`](../../apps/api/docs/JOB_LIFECYCLE.md) – job
  state transitions relevant to extractor workers.
- [`apps/api/docs/BACKPRESSURE_RATELIMITING.md`](../../apps/api/docs/BACKPRESSURE_RATELIMITING.md)
  – crawler throttling/backpressure rules to respect when pulling new documents.

## Guidelines

- Keep tiers modular so they can be tested independently.
- Use ports defined in `packages.core` for persistence (graph/vector writes).
- Respect the performance targets, batching, and caching strategies outlined in
  the extraction spec (Tier A ≥50 pages/sec, Tier B ≥200 sentences/sec, Tier C
  median ≤250 ms/window with Redis caching).
- Store version metadata with outputs so downstream systems can audit extraction
  behaviour and reprocess by version.
- Surface metrics (windows/sec, hit ratios, LLM latency) through the
  observability utilities provided in `packages.common`.
