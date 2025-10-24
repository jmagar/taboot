# ADR 0003: Maintain Three-Tier Extraction Pipeline (A/B/C)

- Status: Accepted
- Date: 2025-02-24
- Stakeholders: Extraction, Graph, Product

## Context

Our extraction stack currently consists of Tier A (rule-based facts), Tier B (markdown windowing), and Tier C (LLM reasoning over windows). Simplifying to a single-tier LLM or expanding to more tiers were considered to reduce latency or complexity.

## Decision

Retain the three-tier architecture with explicit contracts between tiers. Tier A continues to capture high-precision entities, Tier B prepares structured windows for embeddings, and Tier C performs generative reasoning. We will instrument cross-tier metrics via Redis Streams to monitor throughput and error propagation.

## Consequences

- ✅ Enables per-tier scaling and targeted retries without reprocessing entire documents.
- ✅ Keeps deterministic extractions (Tier A) separate from probabilistic LLM outputs (Tier C).
- ⚠️ Higher orchestration overhead compared to a single LLM tier.
- ⚠️ Requires robust configuration management to keep tier interfaces stable.
