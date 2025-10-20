# Packages / Retrieval

Adapters that implement hybrid retrieval (vector + graph + synthesis) using
LlamaIndex and other retrieval tooling. Maps core ports to concrete retrievers,
rerankers, and query engines.

## Layout

```
packages/retrieval/
├── README.md
├── context/          # LlamaIndex settings, prompts, context builders
├── indices/          # Vector/graph index implementations
├── retrievers/       # Hybrid retrievers and post-processors
├── query_engines/    # QA / synthesis engines
├── services/         # Helper services (routing, caching)
└── utils/            # Shared utilities
```

## Key docs

- [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) – hybrid retrieval overview
  (vector → rerank → graph → synthesis).
- [`docs/EVALUATION_PLAN.md`](../../docs/EVALUATION_PLAN.md) – metrics (nDCG, MRR,
  Recall@k) and ablation process.
- [`apps/api/docs/OBSERVABILITY.md`](../../apps/api/docs/OBSERVABILITY.md) – metrics
  to emit (search latency, rerank latency, hit ratios).

## Guidelines

- Keep LlamaIndex usage constrained to this package; core should remain
  framework-agnostic.
- Reuse embeddings/reranker services defined in configuration (TEI, Sentence
  Transformers) and honor latency targets.
- Ensure retrieval outputs include provenance metadata and citation info for the
  API/CLI to surface.
- Coordinate with `packages/vector` and `packages/graph` to keep hybrid search
  behaviour aligned (filter syntax, node/edge schemas).
- Feed evaluation results back into `docs/EVALUATION_PLAN.md` when retrieval
  strategies change significantly.
