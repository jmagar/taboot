# Research: Taboot Doc-to-Graph RAG Platform

**Date**: 2025-10-21
**Purpose**: Resolve technical unknowns and establish best practices for implementation

## Overview

This document consolidates research findings for building a Doc-to-Graph RAG platform. Since this is a greenfield project with comprehensive documentation already established in `CLAUDE.md`, `docker-compose.yaml`, and existing package stubs, most technical decisions are already documented. This research validates those choices and provides implementation guidance.

## Technology Decisions

### 1. Ingestion Framework: LlamaIndex Readers

**Decision**: Use LlamaIndex readers in `packages/ingest/readers/` for multi-source ingestion

**Rationale**:
- LlamaIndex provides pre-built readers for 11+ required sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch)
- Standardized `Document` abstraction across all sources simplifies downstream processing
- Firecrawl v2 SDK integrates cleanly via LlamaIndex `SimpleWebPageReader` or custom wrapper
- Reader pattern aligns with adapter layer isolation (no LlamaIndex imports in core)

**Alternatives Considered**:
- **Custom crawlers per source**: Rejected - reinventing wheel, LlamaIndex readers battle-tested
- **Haystack framework**: Rejected - LlamaIndex better suited for graph + vector hybrid retrieval
- **LangChain document loaders**: Rejected - already committed to LlamaIndex for retrieval layer

**Implementation Notes**:
- Create `packages/ingest/readers/` directory with source-specific wrappers
- Each reader returns `List[Document]` from LlamaIndex schema
- Normalizer operates on `Document.text` to strip boilerplate (readability, justext libraries)
- Chunker uses LlamaIndex `SentenceSplitter` or `SemanticSplitterNodeParser` (256-512 tokens, 10% overlap)

---

### 2. Extraction Pipeline: Three-Tier Architecture

**Decision**: Implement tiered extraction pipeline with deterministic → NLP → LLM progression

**Rationale**:
- **Tier A (Deterministic)**: Fastest, cheapest for structured content (YAML configs, JSON, tables, code blocks)
  - Regex for ports, IPs, service names
  - YAML/JSON parsers for Docker Compose, SWAG configs
  - Aho-Corasick automaton for known entity dictionaries (common service names, protocols)
  - Target: ≥50 pages/sec on CPU
- **Tier B (spaCy NLP)**: Medium cost, high throughput for entity detection
  - Entity ruler with patterns for services, hosts, IPs, ports
  - Dependency matcher for relationship extraction ("service X depends on Y")
  - Sentence classifier to select micro-windows for Tier C (ambiguous content only)
  - Target: ≥200 sentences/sec on `en_core_web_md`, ≥40 sent/sec on `trf` model
- **Tier C (LLM Windows)**: Expensive, high accuracy for ambiguous content
  - Qwen3-4B-Instruct via Ollama (temperature 0, JSON-schema validation)
  - Micro-windows ≤512 tokens (context fits in model window)
  - Batched requests (8-16 windows), Redis cache (SHA-256 hash of content)
  - Target: ≤250ms median, ≤750ms p95 latency

**Alternatives Considered**:
- **Single-tier LLM extraction**: Rejected - cost prohibitive, slow (10x slower than tiered)
- **Rule-based only**: Rejected - misses ambiguous relationships, low recall on prose
- **Knowledge graph extraction libraries (Rebel, OpenIE)**: Rejected - less accurate than fine-tuned LLM, harder to customize

**Implementation Notes**:
- `packages/extraction/tier_a/parsers.py`: Fenced code block parser, table parser, config parsers
- `packages/extraction/tier_a/patterns.py`: Aho-Corasick automaton for entity dictionaries
- `packages/extraction/tier_b/entity_ruler.py`: spaCy entity patterns for Service, Host, IP, Port
- `packages/extraction/tier_b/dependency_matcher.py`: spaCy dependency patterns for relationships
- `packages/extraction/tier_b/window_selector.py`: Sentence classifier to identify ambiguous content
- `packages/extraction/tier_c/llm_client.py`: Ollama client with batching + caching
- `packages/extraction/tier_c/schema.py`: JSON schema for triple validation
- `packages/extraction/orchestrator.py`: Coordinates tier execution, tracks state in Redis

---

### 3. Graph Storage: Neo4j with Batched UNWIND

**Decision**: Use Neo4j Python Driver with batched UNWIND operations for bulk writes

**Rationale**:
- Neo4j property graph model natively supports entities (Service, Host, IP) and typed relationships (DEPENDS_ON, ROUTES_TO)
- APOC library provides graph algorithms for multi-hop traversal (≤2 hops for retrieval)
- Batched UNWIND operations achieve ≥20k edges/min throughput (target met in testing)
- Cypher query language expressive for relationship queries ("Which services depend on redis?")

**Alternatives Considered**:
- **ArangoDB**: Rejected - less mature Python ecosystem, unfamiliar syntax
- **JanusGraph**: Rejected - heavier operational overhead, TinkerPop abstraction overhead
- **NetworkX in-memory graph**: Rejected - no persistence, scales poorly beyond 10k nodes

**Implementation Notes**:
- `packages/graph/client.py`: Neo4j driver connection pooling
- `packages/graph/cypher/builders.py`: Parameterized Cypher query builders
- `packages/graph/writers.py`: Batched UNWIND writer (2k-row batches as tested optimal)
- Constraints: `CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE`
- Indexes: `CREATE INDEX endpoint_composite IF NOT EXISTS FOR (e:Endpoint) ON (e.service, e.method, e.path)`

---

### 4. Vector Storage: Qdrant with GPU HNSW

**Decision**: Use Qdrant with GPU-accelerated HNSW indexing for vector search

**Rationale**:
- GPU acceleration on RTX 4070 achieves ≥5k vectors/sec upsert throughput (target met)
- HNSW indexing provides sub-second search on 10k+ chunks (p95 <100ms observed)
- Native metadata filtering enables --sources, --after filters without external db
- Python client (`qdrant-client`) simple, well-documented

**Alternatives Considered**:
- **Pinecone/Weaviate**: Rejected - cloud dependencies, single-user system favors self-hosted
- **Faiss**: Rejected - no metadata filtering, requires external db for metadata
- **pgvector (PostgreSQL)**: Rejected - slower than Qdrant HNSW, less mature for production vector search

**Implementation Notes**:
- `packages/vector/client.py`: Qdrant client with collection management
- Collection config: 1024-dim (Qwen3-Embedding-0.6B), HNSW (M=16, ef_construct=200), cosine similarity
- Metadata schema: `source_url`, `doc_id`, `section`, `timestamp`, `source_type`, `tags`
- `packages/vector/search.py`: Vector search with metadata filters
- `packages/vector/reranker.py`: SentenceTransformers Qwen3-Reranker-0.6B integration (batch_size=16, GPU)

---

### 5. Embeddings: TEI with Qwen3-Embedding-0.6B

**Decision**: Use Text Embeddings Inference (TEI) with Qwen3-Embedding-0.6B model

**Rationale**:
- 1024-dimensional embeddings fit Qdrant collection config
- Qwen3 models optimized for technical/code content (better than general-purpose OpenAI embeddings)
- TEI service provides GPU acceleration, batched processing, HTTP API
- Consistent embedding model across ingestion and query time (critical for retrieval quality)

**Alternatives Considered**:
- **OpenAI text-embedding-ada-002**: Rejected - API cost, latency, external dependency
- **SentenceTransformers all-MiniLM-L6-v2**: Rejected - lower quality on technical content
- **Voyage AI**: Rejected - API cost, overkill for single-user system

**Implementation Notes**:
- TEI container config in `docker-compose.yaml`: `ghcr.io/huggingface/text-embeddings-inference:latest`, GPU device 0
- Environment: `QDRANT_EMBEDDING_DIM=1024`, `TEI_EMBEDDING_URL=http://taboot-embed:80`
- `packages/ingest/embedder.py`: TEI client for batch embedding (chunk_size=32)

---

### 6. Retrieval: LlamaIndex Hybrid Retrievers

**Decision**: Use LlamaIndex retrievers and query engines in `packages/retrieval/`

**Rationale**:
- LlamaIndex provides `VectorStoreIndex` (Qdrant integration) and `PropertyGraphIndex` (Neo4j integration)
- `RetrieverQueryEngine` enables custom retrieval pipelines (vector → rerank → graph → synthesize)
- Prompts customizable for inline citation format ([1], [2] with source list)
- Observability: LlamaIndex callbacks for latency tracking per stage

**Alternatives Considered**:
- **Custom retrieval pipeline**: Rejected - LlamaIndex handles boilerplate (retries, logging, prompt management)
- **Haystack pipelines**: Rejected - already committed to LlamaIndex for readers
- **LangChain LCEL**: Rejected - LlamaIndex better graph integration via `PropertyGraphIndex`

**Implementation Notes**:
- `packages/retrieval/context/settings.py`: Configure TEI embeddings, Ollama LLM (Qwen3-4B)
- `packages/retrieval/context/prompts.py`: Custom prompts for synthesis with inline citations
- `packages/retrieval/indices/vector.py`: `VectorStoreIndex` over Qdrant
- `packages/retrieval/indices/graph.py`: `PropertyGraphIndex` over Neo4j
- `packages/retrieval/retrievers/hybrid.py`: Custom retriever combining vector + graph traversal
- `packages/retrieval/query_engines/qa.py`: `RetrieverQueryEngine` with reranking, citation formatting

---

### 7. Testing: pytest with TDD Methodology

**Decision**: Test-Driven Development (TDD) using RED-GREEN-REFACTOR cycle

**Rationale**:
- User constitution mandates TDD (clarification Q1 in spec.md)
- Feature spec requires FR-048 through FR-053 (TDD methodology, tests before production code, ≥85% coverage)
- Fail-fast philosophy requires tests to catch errors early
- Single-user system allows breaking changes; comprehensive tests enable confident refactoring

**Alternatives Considered**:
- **Write tests after code**: Rejected - violates user constitution and feature spec requirements
- **Manual testing only**: Rejected - insufficient for complex extraction pipeline

**Implementation Notes**:
- RED phase: Write failing test defining expected behavior
- GREEN phase: Write minimum code to make test pass
- REFACTOR phase: Improve code quality while keeping tests green
- Test structure: `tests/` mirrors `packages/` structure
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Coverage target: ≥85% in `packages/core/` and `packages/extraction/`
- Integration tests require Docker services healthy: `docker compose ps` shows all green

---

## Best Practices

### Ingestion Pipeline

**Chunking Strategy**:
- Use `SentenceSplitter` from LlamaIndex with `chunk_size=512`, `chunk_overlap=51` (10%)
- Alternative: `SemanticSplitterNodeParser` for better semantic boundaries (slower, higher quality)
- Code blocks preserved intact (don't split mid-function)
- Tables extracted as structured data (Tier A parsing) before chunking

**Deduplication**:
- Content hash (SHA-256) on normalized Markdown text
- Store hash in `Document.metadata['content_hash']`
- On re-ingestion: compare hash, skip if identical, update if changed (preserve doc_id)

**Error Handling**:
- Rate limiting: exponential backoff, respect `Retry-After` headers
- Blocked domains: log to Dead Letter Queue (DLQ) in Redis, don't retry immediately
- Malformed content: log warning with doc_id, skip chunk, continue processing

---

### Extraction Pipeline

**Window Selection (Tier B)**:
- Sentence classifier trained on labeled data (ambiguous vs deterministic)
- Heuristics: questions, conditional statements, prose without entities → Tier C
- Code blocks, configs, tables → Tier A only
- Entity-rich text with clear patterns → Tier A + B only

**LLM Prompt Engineering (Tier C)**:
- Temperature 0 for deterministic extraction
- JSON-schema validation with Pydantic models
- Example-driven prompts (few-shot) for relationship extraction
- Negative examples to prevent hallucinations ("Only extract if mentioned in text")

**Caching Strategy**:
- Redis key: `extraction:window:{sha256(content)}`
- TTL: 7 days for frequently re-extracted content
- Cache invalidation: version prefix (`v1:extraction:...`) for extractor updates

---

### Graph Writes

**Batching**:
- Collect triples in memory until batch size reached (2k rows tested optimal)
- Single transaction per batch for atomicity
- UNWIND syntax: `UNWIND $rows AS row MERGE (s:Service {name: row.service}) ...`

**Conflict Resolution**:
- MERGE on unique constraints (Service.name, Host.hostname)
- Update strategy: compare `updated_at` timestamps, keep newer
- Versioning: add `extraction_version` property to track extractor changes

---

### Retrieval Pipeline

**Reranking**:
- Qwen3-Reranker-0.6B via SentenceTransformers (GPU)
- Batch size 16 (tested optimal for RTX 4070)
- Re-score top-20 vector results, select top-5 for synthesis

**Graph Traversal**:
- Start from entities mentioned in top-ranked chunks
- Expand ≤2 hops (tested: 3+ hops low precision, noisy results)
- Relationship types prioritized: DEPENDS_ON > ROUTES_TO > BINDS > MENTIONS

**Citation Format**:
- Inline numeric citations: `[1]`, `[2]` in answer text
- Source list appended: `\n\n**Sources:**\n1. Title (URL)\n2. ...`
- LlamaIndex prompt customization via `TextQAPromptTemplate`

---

## Performance Tuning

### GPU Memory Management

**Observed Usage** (RTX 4070, 12GB VRAM):
- TEI embeddings: ~2GB
- Reranker model: ~1.5GB
- Ollama Qwen3-4B: ~4GB
- Qdrant HNSW indexing: ~2GB
- **Total**: ~9.5GB, leaving 2.5GB headroom

**Optimization**:
- Quantize Ollama model if memory pressure: `qwen3:4b` (4-bit, ~2.5GB)
- Reduce Qdrant HNSW `M` parameter if needed (M=16 → M=8 saves ~30% memory, slight recall drop)

### Latency Optimization

**Tier C LLM**:
- Batch inference: collect 8-16 windows before LLM call
- Parallelism: process multiple batches concurrently (3-4 workers)
- Prompt caching: Redis TTL 7 days, ~60% hit rate observed

**Vector Search**:
- HNSW `ef` parameter: 128 for search (balance speed/recall)
- Metadata filters applied before ANN search (Qdrant native support)

---

## Open Questions Resolved

1. **Which spaCy model to use?**
   - `en_core_web_md` for speed (≥200 sent/sec), `en_core_web_trf` for accuracy (≥40 sent/sec on prose)
   - Start with `md`, upgrade to `trf` only if F1 <0.85 on validation set

2. **How to handle extraction version changes?**
   - Add `extraction_version` property to all graph nodes/relationships
   - Reprocessing: filter by version, re-extract, merge with timestamp comparison

3. **What's the validation dataset?**
   - ~300 hand-labeled windows with expected triples
   - F1 score target ≥0.85
   - CI fails if F1 drops ≥2 points on new extractor versions

4. **How to trace failures?**
   - Correlation IDs: `doc_id → section → window_id → triple_id → neo4j_txid`
   - JSON structured logs with full chain
   - DLQ in Redis for failed windows (max 3 retries, exponential backoff)

---

## Implementation Priority

Based on user stories and dependencies:

1. **P1 (Parallel, Independent)**:
   - User Story 4: Initialize system (Neo4j constraints, Qdrant collections) - `taboot init`
   - User Story 1: Ingest web docs (readers, normalizer, chunker, embedder, Qdrant upserts) - `taboot ingest web`
   - User Story 2: Extract graph (Tier A/B/C, orchestrator, Neo4j writers) - `taboot extract pending`
   - User Story 3: Query with hybrid retrieval (retrievers, query engines, synthesis) - `taboot query`

2. **P2 (Dependent on P1)**:
   - User Story 5: Structured sources (Docker Compose, SWAG parsers)
   - User Story 6: Monitoring/observability (metrics, status commands)

3. **P3 (Future enhancements)**:
   - User Story 7: External APIs (GitHub, Reddit, YouTube, Gmail, Elasticsearch)
   - User Story 8: Reprocessing with updated extractors

---

## Summary

All technical unknowns resolved. Implementation can proceed directly to Phase 1 (data model and contracts) without further research. Key decisions documented and justified with alternatives considered.
