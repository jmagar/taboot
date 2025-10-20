# Research: LlamaCrawl v2 — Technical Decisions

**Date**: 2025-10-20
**Input**: TECH_STACK_SUMMARY.md + PIPELINE_INVESTIGATION_REPORT.md + EXTRACTION_SPEC.md + Tier B spaCy research
**Status**: Architecture complete, implementation at 5% (skeleton phase per investigation)

---

## Executive Summary

This document consolidates all technical research and decisions for LlamaCrawl v2, a Doc-to-Graph RAG platform. All architectural decisions are complete with comprehensive specifications, but implementation is at 0-5% (empty `__init__.py` files per PIPELINE_INVESTIGATION_REPORT.md). The platform is greenfield with strong design foundations ready for implementation.

**Key Finding**: All adapter packages (ingest, extraction, graph, vector, retrieval) currently contain only empty placeholder files. Docker infrastructure is fully configured with 11 services (4 GPU-accelerated). Performance targets are quantified for all components.

---

## Research Topics

### 1. LlamaIndex Integration Patterns

**Decision**: Use LlamaIndex exclusively in `packages/retrieval/` adapter layer, never in core business logic

**Rationale**:
- Maintains framework-agnostic core layer per hexagonal architecture principles
- Enables swapping retrieval frameworks without touching business logic
- LlamaIndex provides mature abstractions for vector + graph hybrid retrieval
- Native integration with Neo4j (PropertyGraphIndex via Neo4jPGStore) and Qdrant (VectorStoreIndex)
- Supports 6-stage retrieval pipeline: embed → filter → search → rerank → traverse → synthesize

**Implementation Pattern**:
```python
# packages/retrieval/indices/
# - VectorStoreIndex wraps Qdrant client
# - PropertyGraphIndex wraps Neo4j client
# packages/retrieval/retrievers/
# - Hybrid retriever combines vector + graph
# packages/retrieval/query_engines/
# - QA engine with citation builder
```

**Alternatives Considered**:
- **Haystack**: Less mature Neo4j integration, heavier framework overhead
- **LangChain**: More complex abstractions, harder to constrain to adapter layer
- **Custom retrieval**: Rejected due to development time; LlamaIndex provides battle-tested abstractions

**Configuration**:
- TEI embeddings (Qwen3-Embedding-0.6B, 1024-dim)
- Ollama LLM (Qwen3-4B-Instruct, temperature 0)
- Reranker (Qwen/Qwen3-Reranker-0.6B via SentenceTransformers, batch size 16)

**Performance Target**: <3s p95 end-to-end (embed + search + rerank + graph + synthesis)

**References**:
- `/home/jmagar/code/taboot/packages/retrieval/` (current status: empty per investigation)
- TECH_STACK_SUMMARY.md Section 7
- LlamaIndex documentation: Neo4jPGStore, VectorStoreIndex

---

### 2. spaCy Extraction Patterns (Tier B)

**Decision**: Use `en_core_web_md` model with EntityRuler + DependencyMatcher + rule-based sentence classifier

**Rationale**:
- **Performance**: Achieves 200-350 sentences/sec on CPU, exceeding ≥200 sent/sec target
- **Memory**: ~800MB peak (500MB model + 300MB batch), fits within constraints
- **Accuracy**: Balanced model suitable for technical documentation
- **Cost**: No GPU required (CPU-optimized)
- **Research Validation**: Comprehensive benchmarking confirms targets met (RESEARCH_SUMMARY.md)

**Implementation Components**:
1. **EntityRuler**: Domain-specific patterns for Service, IP, Host, Port, Endpoint entities
   - Uses regex token patterns for technical identifiers
   - Trie-based matcher for efficient pattern matching (<10% overhead for <10k patterns)

2. **DependencyMatcher**: Relationship extraction via Semgrex operators
   - Patterns for DEPENDS_ON, ROUTES_TO, BINDS, EXPOSES_ENDPOINT
   - Semgrex operators: `>` (child), `<` (parent), `>>` (descendant), `<<` (ancestor)

3. **Sentence Classifier**: Rule-based filtering for technical vs. non-graph sentences
   - 85-90% accuracy with no training required
   - 200-300 sent/sec throughput

**Configuration**:
- Model: `en_core_web_md` (43MB download, ~500MB loaded)
- Batch size: 1000 (optimal for 500-2000 char technical docs)
- Disabled components: lemmatizer, ner (using EntityRuler instead)
- n_process: 1 (batching sufficient for performance)

**Caching Strategy**:
- Redis cache keyed by SHA-256(content + extractor_version)
- 7-day TTL
- <5ms cache hits (~20k ops/sec)
- 10-50x speedup on repeated content

**Dead Letter Queue (DLQ)**:
- Redis-based retry queue
- Max 3 retries with exponential backoff (1s, 5s, 25s)
- 30-day retention for permanently failed items
- Zero data loss guarantee

**Alternatives Considered**:
- **en_core_web_trf** (transformer model): Only achieves 80-150 sent/sec on GPU, below target; rejected
- **Custom NER training**: Deferred to future; rule-based patterns sufficient for MVP
- **Trained TextCategorizer**: Only 50-100 sent/sec; rule-based classifier faster

**Performance Benchmarks** (from RESEARCH_SUMMARY.md):
- Entity Extraction: 250-350 sent/sec
- Sentence Classification: 200-300 sent/sec
- Relationship Extraction: 150-250 sent/sec
- Full Pipeline: 200-280 sent/sec (TARGET MET)

**References**:
- `/home/jmagar/code/taboot/packages/extraction/tier_b/RESEARCH_SUMMARY.md`
- `/home/jmagar/code/taboot/packages/extraction/tier_b/SPACY_PATTERNS_GUIDE.md`
- `/home/jmagar/code/taboot/packages/extraction/tier_b/QUICK_START.md`
- spaCy 3.8+ documentation (released May 2025)

---

### 3. Redis DLQ Patterns

**Decision**: Use Redis sorted sets with content hash keys and retry count tracking

**Rationale**:
- Deterministic content hashing (SHA-256) enables idempotent retry logic
- Sorted sets provide automatic TTL and priority ordering
- Single Redis instance (taboot-cache) handles cache + DLQ + state
- 30-day retention allows post-mortem analysis of extraction failures
- Retry count tracking prevents infinite loops

**Key Schema**:
```
extraction:{content_hash} → Cached result (TTL: 7d)
extraction:meta:{content_hash} → Metadata with version (TTL: 7d)
dlq:extraction:{content_hash} → Failed extraction (TTL: 30d)
dlq:retry:{content_hash} → Retry count
dlq:failed:{content_hash} → Permanently failed (max retries exceeded)
```

**Retry Strategy**:
- Max 3 retries per content hash
- Exponential backoff: 1s, 5s, 25s
- Version-aware cache invalidation (extractor_version in metadata)
- Batch retry processing (100 items per batch)

**Performance**:
- Cache Hit: <5ms (~20k ops/sec)
- DLQ Add: <10ms (~10k ops/sec)
- Cache Miss + Extract: ~100-500ms (depends on tier)

**Alternatives Considered**:
- **RabbitMQ/Kafka**: Overkill for single-node deployment; Redis simpler
- **PostgreSQL SKIP LOCKED**: Higher latency than Redis for queue operations
- **In-memory queue**: No persistence, data loss on restart; rejected

**Configuration**:
- Redis 7.2 (taboot-cache service)
- RDB + AOF persistence
- 2GB memory limit recommended
- Eviction policy: allkeys-lru for cache keys only

**References**:
- RESEARCH_SUMMARY.md Section 5 (Caching & Dead Letter Queue)
- Docker service: taboot-cache (redis:7.2-alpine)

---

### 4. Qdrant Hybrid Search

**Decision**: Single collection `taboot.documents` with namespace filtering, HNSW GPU indexing, 1024-dim Cosine similarity

**Rationale**:
- **Single collection design**: Simpler ops than per-namespace collections; filtering via payload
- **GPU acceleration**: HNSW indexing on RTX 4070 enables ≥5k vectors/sec upserts
- **1024-dim embeddings**: Qwen3-Embedding-0.6B via TEI (GPU-accelerated)
- **Cosine similarity**: Standard for semantic search, well-supported
- **Payload schema**: 15 fields enable rich metadata filtering (source, date, namespace, tags)

**Collection Configuration**:
```json
{
  "name": "taboot.documents",
  "vectors": {
    "size": 1024,
    "distance": "Cosine"
  },
  "hnsw_config": {
    "m": 32,
    "ef_construct": 128,
    "full_scan_threshold": 10000
  },
  "shard_number": 4,
  "replication_factor": 1
}
```

**Payload Schema** (15 fields):
- **Keyword fields**: doc_id, chunk_id, namespace, url, title, source, job_id, sha256, mime, lang
- **Numeric fields**: chunk_index, text_len
- **Datetime fields**: created_at, updated_at
- **Array fields**: tags

**Deduplication Strategy**:
- By `(sha256, namespace)` tuple
- If content identical, update metadata + `updated_at` timestamp
- Idempotent upserts via `point_id = chunk_id`

**Hybrid Search Pattern**:
1. Query embedding (TEI, 1024-dim)
2. Metadata filtering (source, date, namespace, tags)
3. Vector search (top-k=100 default)
4. Reranking (Qwen/Qwen3-Reranker-0.6B via SentenceTransformers, batch 16)
5. Graph traversal (≤2 hops Neo4j for entity relationships)
6. Synthesis (Qwen3-4B with inline citations)

**Alternatives Considered**:
- **Per-namespace collections**: Harder to manage, cross-namespace search complex; rejected
- **Postgres pgvector**: Lower throughput, no GPU acceleration; rejected
- **Elasticsearch dense_vector**: Less mature HNSW, higher memory overhead; rejected
- **768-dim embeddings**: Rejected in favor of 1024-dim for higher quality

**Performance Targets**:
- Upserts: ≥5k vectors/sec (1024-dim, batched)
- Search latency: <100ms p95 (top-k=100)
- HNSW memory: ~2GB for 1M vectors (1024-dim)

**References**:
- TECH_STACK_SUMMARY.md Section 6 (Vector Storage)
- Docker service: taboot-vectors (qdrant/qdrant:gpu-nvidia)
- Qdrant 1.15.1+ with GPU support

---

### 5. Neo4j Batch Write Patterns

**Decision**: Use UNWIND batches (2-5k rows) with idempotent MERGE operations and deadlock retry logic

**Rationale**:
- **UNWIND performance**: 2k-row batches achieve ≥20k edges/min target
- **Idempotent MERGE**: Supports reprocessing without duplicate edges
- **Deadlock handling**: Automatic retry with exponential backoff
- **Provenance tracking**: Every edge stores `docId`, `source` (tier), `confidence`, `extractionMethod`

**Batch Write Pattern**:
```cypher
UNWIND $batch AS row
MATCH (s:Service {name: row.service})
MATCH (h:Host {hostname: row.host})
MERGE (s)-[r:RUNS_ON]->(h)
SET r.port = row.port,
    r.protocol = row.protocol,
    r.confidence = row.confidence,
    r.source = row.source,
    r.docId = row.docId,
    r.extractionMethod = row.extractionMethod,
    r.since = coalesce(r.since, datetime())
```

**Idempotent Node Creation**:
```cypher
MERGE (s:Service {name: $name})
ON CREATE SET
  s.id = randomUUID(),
  s.createdAt = datetime(),
  s.schemaVersion = "2.0.0"
ON MATCH SET
  s.updatedAt = datetime()
```

**Constraints and Indexes** (14 total):
```cypher
-- Unique constraints
CREATE CONSTRAINT host_hostname FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
CREATE CONSTRAINT service_name FOR (s:Service) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT endpoint_uniq FOR (e:Endpoint) REQUIRE (e.scheme, e.fqdn, e.port, e.path) IS UNIQUE;
CREATE CONSTRAINT network_cidr FOR (n:Network) REQUIRE n.cidr IS UNIQUE;
CREATE CONSTRAINT ip_addr FOR (i:IP) REQUIRE i.addr IS UNIQUE;
CREATE CONSTRAINT doc_docid FOR (d:Document) REQUIRE d.docId IS UNIQUE;

-- Indexes for lookup patterns
CREATE INDEX container_compose FOR (c:Container) ON (c.composeProject, c.composeService);
CREATE INDEX service_proto_port FOR (s:Service) ON (s.protocol, s.port);
CREATE INDEX host_ip FOR (h:Host) ON (h.ip);
CREATE INDEX doc_url FOR (d:Document) ON (d.url);
```

**Deadlock Retry Strategy**:
- Max 5 retries
- Exponential backoff: 100ms, 200ms, 400ms, 800ms, 1600ms
- Log deadlock occurrences for batch size tuning
- Reduce batch size if deadlocks frequent (5k → 2k → 1k)

**Performance Tuning**:
- Batch size: 2k rows (optimal balance)
- Transaction timeout: 30s
- Connection pool: 10 connections
- Bolt protocol: Neo4j 5.23+ with APOC plugin

**Alternatives Considered**:
- **CREATE instead of MERGE**: Faster but not idempotent; rejected for reprocessing needs
- **Larger batches (10k+)**: Increased deadlock rate; rejected
- **Smaller batches (500)**: Lower throughput; rejected
- **APOC bulk operations**: Similar performance to UNWIND; chose UNWIND for clarity

**References**:
- EXTRACTION_SPEC.md Section 7 (Batch Writing and Performance)
- Docker service: taboot-graph (Neo4j 5.23 with APOC)
- Neo4j driver: neo4j 5.26

---

### 6. TEI Embedding Integration

**Decision**: Use Hugging Face Text Embeddings Inference (TEI) with Qwen3-Embedding-0.6B model, GPU-accelerated

**Rationale**:
- **Performance**: GPU-accelerated inference, supports batching
- **Model quality**: Qwen3-Embedding-0.6B provides 1024-dim embeddings with strong semantic understanding
- **Standardization**: TEI is production-ready inference server with health checks, metrics
- **Resource efficiency**: 0.6B parameter model fits within RTX 4070 VRAM (12GB)

**Configuration**:
```yaml
taboot-embed:
  image: ghcr.io/huggingface/text-embeddings-inference:latest
  environment:
    MODEL_ID: Qwen/Qwen3-Embedding-0.6B
    REVISION: main
    MAX_BATCH_TOKENS: 16384
    MAX_CLIENT_BATCH_SIZE: 32
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**API Integration**:
- HTTP endpoint: `http://taboot-embed:80/embed`
- Request: `{"inputs": ["text1", "text2", ...]}`
- Response: `{"embeddings": [[...], [...]], "model": "Qwen3-Embedding-0.6B"}`
- Batching: 32 texts per request (MAX_CLIENT_BATCH_SIZE)

**Performance**:
- Throughput: Estimated 100-200 texts/sec (depends on text length)
- Latency: <50ms per batch (32 texts)
- VRAM usage: ~2-3GB (0.6B model)

**Alternatives Considered**:
- **OpenAI embeddings (ada-002)**: External dependency, cost, latency; rejected
- **SentenceTransformers directly**: No production server, harder to scale; rejected
- **Larger models (7B+)**: VRAM constraints on RTX 4070; rejected
- **Smaller models (<0.5B)**: Lower quality embeddings; rejected

**Model Selection Rationale**:
- Qwen3-Embedding-0.6B balances quality and resource usage
- 1024-dim output matches Qdrant collection configuration
- Open weights, can fine-tune if needed
- Multilingual support (English primary, but supports others)

**Health Check**:
```bash
curl http://taboot-embed:80/health
# Expected: {"status": "ready"}
```

**References**:
- Docker service: taboot-embed (ghcr.io/huggingface/text-embeddings-inference)
- Model: Qwen/Qwen3-Embedding-0.6B (Hugging Face Hub)
- TEI documentation: https://github.com/huggingface/text-embeddings-inference

---

### 7. Citation Builder Patterns

**Decision**: Inline numeric citations `[1][2]` in synthesized text + bibliography section with source links

**Rationale**:
- **Traceability**: Every claim links to source document(s)
- **User experience**: Inline citations familiar from academic/technical writing
- **Provenance chain**: `doc_id → chunk_id → span → triple → Neo4j txId`
- **Multi-source attribution**: Single sentence can cite multiple sources

**Citation Format**:
```markdown
The nginx service [1] depends on postgres [2] and redis [3].
Traefik routes traffic to backend services [1][4].

## Sources
[1] docker-compose.yaml (doc_id: abc123)
    https://example.com/docker-compose.yaml
    Ingested: 2025-10-20 14:30:00 UTC

[2] Database Configuration (doc_id: def456)
    https://example.com/docs/database.md
    Section: "PostgreSQL Setup"
    Ingested: 2025-10-20 14:25:00 UTC

[3] Redis Documentation (doc_id: ghi789)
    https://example.com/docs/redis.md
    Ingested: 2025-10-20 14:20:00 UTC

[4] Reverse Proxy Config (doc_id: jkl012)
    https://example.com/configs/traefik.toml
    Section: "HTTP Routers"
    Ingested: 2025-10-20 14:15:00 UTC
```

**Implementation Pattern**:
```python
class CitationBuilder:
    def __init__(self):
        self.citations: Dict[str, int] = {}  # doc_id → citation number
        self.sources: List[SourceMetadata] = []

    def add_citation(self, doc_id: str, metadata: SourceMetadata) -> int:
        """Add citation, return citation number."""
        if doc_id not in self.citations:
            self.citations[doc_id] = len(self.sources) + 1
            self.sources.append(metadata)
        return self.citations[doc_id]

    def format_inline(self, doc_ids: List[str]) -> str:
        """Format inline citation: [1][2]"""
        numbers = [self.citations[doc_id] for doc_id in doc_ids]
        return "".join(f"[{n}]" for n in sorted(numbers))

    def build_bibliography(self) -> str:
        """Build sources section."""
        lines = ["## Sources"]
        for i, source in enumerate(self.sources, 1):
            lines.append(f"[{i}] {source.title} (doc_id: {source.doc_id})")
            lines.append(f"    {source.url}")
            if source.section:
                lines.append(f'    Section: "{source.section}"')
            lines.append(f"    Ingested: {source.ingested_at}")
            lines.append("")
        return "\n".join(lines)
```

**Provenance Chain**:
1. Document ingested → `doc_id` assigned
2. Chunked → `chunk_id` assigned
3. Extracted → triple with `span` (char offsets)
4. Stored in Neo4j → `(:Document)-[:MENTIONS {span, section}]->(:Entity)`
5. Retrieved → traces back to source document
6. Synthesized → citation number added inline

**Alternatives Considered**:
- **Footnote style citations**: Harder to read inline; rejected
- **Superscript numbers**: Markdown limitation; bracket format clearer
- **Author-date citations**: No authors for config files; rejected
- **No citations**: Violates requirement for strict source attribution; rejected

**LlamaIndex Integration**:
- Custom `CitationQueryEngine` wraps base engine
- Post-processes synthesis output to add citations
- Queries Neo4j for provenance metadata via `MENTIONS` relationships

**References**:
- TECH_STACK_SUMMARY.md Section 7 (Retrieval & Synthesis)
- plan.md Section 7 (Retrieval Plane, 6-Stage Pipeline)
- Requirement: "Strict source attribution" from spec.md

---

### 8. Ollama LLM Integration (Tier C)

**Decision**: Use Ollama with Qwen3-4B-Instruct model for Tier C window extraction, batched 8-16 windows, temperature 0, JSON schema enforcement

**Rationale**:
- **Local deployment**: No external API dependency, no per-token costs
- **GPU quantization**: Fits within RTX 4070 VRAM (12GB) with other services
- **Model selection**: Qwen3-4B-Instruct balances quality and speed
- **JSON mode**: Native structured output support
- **Batching**: 8-16 windows per request enables ≤250ms/window median latency

**Configuration**:
```yaml
taboot-ollama:
  image: ollama/ollama:latest
  environment:
    OLLAMA_NUM_PARALLEL: 8
    OLLAMA_MAX_LOADED_MODELS: 1
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  volumes:
    - ollama_models:/root/.ollama
```

**Model Pull**:
```bash
docker exec taboot-ollama ollama pull qwen2.5:4b-instruct
```

**Tier C Window Extraction Pattern**:
```python
import ollama

def extract_window(
    window_text: str,
    extractor_version: str = "1.0.0"
) -> Dict[str, Any]:
    """Extract entities and relationships from ≤512-token window."""

    # Check cache
    cache_key = sha256(f"{window_text}:{extractor_version}".encode()).hexdigest()
    cached = redis.get(f"extraction:{cache_key}")
    if cached:
        return orjson.loads(cached)

    # LLM extraction
    prompt = build_extraction_prompt(window_text)
    response = ollama.chat(
        model="qwen2.5:4b-instruct",
        messages=[{"role": "user", "content": prompt}],
        format="json",  # Enforce JSON output
        options={
            "temperature": 0.0,
            "top_p": 0.0,
            "num_predict": 512,
        }
    )

    # Validate schema
    result = validate_extraction_schema(response["message"]["content"])

    # Cache result
    redis.setex(f"extraction:{cache_key}", timedelta(days=7), orjson.dumps(result))

    return result
```

**Extraction Schema** (JSON):
```json
{
  "entities": [
    {
      "type": "Service|Host|IP|ReverseProxy|Endpoint|Network|Container|Image|Volume|VPNTunnel|TailscaleNode",
      "name": "nginx",
      "props": {"version": "1.25", "port": 80}
    }
  ],
  "relations": [
    {
      "type": "DEPENDS_ON|ROUTES_TO|BINDS|RUNS|EXPOSES_ENDPOINT|CONNECTS_TO|MOUNTS_VOLUME",
      "src": "nginx",
      "dst": "postgres",
      "props": {"confidence": 0.95}
    }
  ],
  "provenance": {
    "docId": "abc123",
    "section": "Services",
    "span": [120, 245]
  }
}
```

**Batching Strategy**:
- Group 8-16 windows per batch
- Parallel inference via `OLLAMA_NUM_PARALLEL=8`
- Total latency: ~2-4s per batch (250-500ms/window)

**Few-Shot Prompting**:
- 3-5 examples per entity type in prompt
- Examples cover common patterns (Docker Compose, SWAG configs, technical prose)
- Temperature 0 for deterministic output

**Error Handling**:
- Malformed JSON → validate with Pydantic, add to DLQ
- Low confidence (<0.70) → filter out extraction
- Medium confidence (0.70-0.80) → flag for manual review
- High confidence (≥0.80) → accept extraction

**Alternatives Considered**:
- **Larger models (7B+)**: VRAM constraints, slower; rejected
- **Smaller models (1.5B)**: Lower quality; rejected
- **OpenAI GPT-4**: External dependency, cost, latency; rejected
- **Mixtral**: Larger VRAM footprint; rejected
- **Llama 3**: Comparable quality, but Qwen3 better for multilingual

**Performance Targets**:
- Median latency: ≤250ms/window (with caching and batching)
- P95 latency: ≤750ms/window
- Throughput: ~60-120 windows/sec (with 8-16 batch size)
- Cache hit rate: ≥70% after warmup

**VRAM Usage**:
- Qwen3-4B-Instruct quantized: ~4-5GB
- Leaves ~7GB for TEI embeddings and reranker on RTX 4070

**References**:
- EXTRACTION_SPEC.md Section 4.3 (Tier C — LLM Windows)
- RESEARCH_SUMMARY.md (spaCy performance for comparison)
- Docker service: taboot-ollama (ollama/ollama:latest)
- Model: qwen2.5:4b-instruct (Ollama library)

---

## Cross-Cutting Concerns

### Observability

**Metrics to Track**:
- **Ingestion**: Pages/sec, bytes/sec, failure rate, Firecrawl job duration
- **Extraction**: Windows/sec, tier hit ratios (A/B/C), LLM p95 latency, cache hit rate
- **Storage**: Neo4j edges/min, Qdrant vectors/sec, Redis ops/sec
- **Retrieval**: Query latency (p50/p95/p99), rerank time, synthesis time

**Tracing Chain**:
```
doc_id → section → windows → triples → Neo4j txId → query result → citation
```

**Validation**:
- ~300 labeled windows for extraction quality (F1 guardrails)
- CI fails if F1 drops ≥2 points from baseline
- Target: ≥0.80 F1 (precision ≥0.85, recall ≥0.75)

**Logging**:
- JSON structured logs via `python-json-logger`
- All adapters emit structured events
- Correlation ID traces request through all services

### Error Handling Philosophy

**Fail-Fast Strategy**:
- No fallback modes for service failures
- External service down (Firecrawl, TEI, Neo4j, Ollama, Qdrant) → stop execution immediately
- Clear error messages with service name and failure reason
- DLQ for transient failures with automatic retry

**Error Codes**:
```
E_URL_BAD      — Malformed URL
E_ROBOTS       — Blocked by robots.txt
E_403_WAF      — WAF rejection
E_429_RATE     — Rate limit exceeded
E_5XX_ORIGIN   — Origin server error
E_PARSE        — Content parsing failure
E_TIMEOUT      — Request timeout
E_BROWSER      — Playwright/browser error
E_QDRANT       — Vector DB error
E_NEO4J        — Graph DB error
E_GPU_OOM      — GPU out of memory
```

### Type Safety

**Mypy Strict Mode**:
- All functions annotated with types
- No bare `any` type allowed
- Strict checking enabled in all packages
- CI fails on type errors

**Pydantic Schemas**:
- All DTOs in `packages/schemas/`
- Request/response validation
- JSON schema generation for API docs

### Performance Baselines (RTX 4070)

**Summary Table**:

| Component | Target | Status |
|-----------|--------|--------|
| Tier A extraction | ≥50 pages/sec | Not implemented |
| Tier B extraction | ≥200 sentences/sec | Research validates feasible |
| Tier C LLM | ≤250ms/window median | Not implemented |
| Neo4j writes | ≥20k edges/min | Not implemented |
| Qdrant upserts | ≥5k vectors/sec | Service configured |
| Full retrieval | <3s p95 | Not implemented |
| Extraction F1 | ≥0.80 | Not measured |

---

## Implementation Readiness

**Complete**:
- Architecture design (hexagonal, strict layering)
- Specifications (all 10 user stories, acceptance criteria)
- Docker infrastructure (11 services, health checks)
- Documentation (ARCHITECTURE.md, EXTRACTION_SPEC.md, research summaries)
- Tech stack decisions (all 8 research topics resolved)

**Incomplete** (Per PIPELINE_INVESTIGATION_REPORT.md):
- Core domain models (0% — empty packages)
- Adapter implementations (0% — all empty)
- Test suite (0% — no tests written)
- API routes (0% — only health stub)
- CLI commands (0% — not implemented)

**Estimated Implementation Effort**:
- Core + adapters: 2-3 weeks
- Tests: 1-2 weeks
- Performance tuning: 2-3 weeks
- Total: 5-8 weeks for MVP

---

## Appendix: Key File Locations

**Research Documents**:
- `/home/jmagar/code/taboot/.specify/specs/001-llamacrawl-v2-rag-platform/TECH_STACK_SUMMARY.md`
- `/home/jmagar/code/taboot/.specify/specs/001-llamacrawl-v2-rag-platform/PIPELINE_INVESTIGATION_REPORT.md`
- `/home/jmagar/code/taboot/.specify/specs/001-llamacrawl-v2-rag-platform/plan.md`
- `/home/jmagar/code/taboot/packages/extraction/tier_b/RESEARCH_SUMMARY.md`
- `/home/jmagar/code/taboot/packages/extraction/tier_b/SPACY_PATTERNS_GUIDE.md`
- `/home/jmagar/code/taboot/packages/extraction/tier_b/QUICK_START.md`
- `/home/jmagar/code/taboot/packages/extraction/docs/EXTRACTION_SPEC.md`

**Specifications**:
- `/home/jmagar/code/taboot/.specify/specs/001-llamacrawl-v2-rag-platform/spec.md`
- `/home/jmagar/code/taboot/.specify/specs/001-llamacrawl-v2-rag-platform/tasks.md`

**Configuration**:
- `/home/jmagar/code/taboot/docker-compose.yaml` (11 services)
- `/home/jmagar/code/taboot/.env.example` (112 variables)
- `/home/jmagar/code/taboot/pyproject.toml` (workspace config)

**Project Guidance**:
- `/home/jmagar/code/taboot/CLAUDE.md` (repository-wide conventions)
- `/home/jmagar/code/taboot/packages/extraction/CLAUDE.md` (extraction package guidance)

---

**Document Version**: 1.0.0
**Status**: Complete — All technical decisions documented
**Next Phase**: Phase 1 Design (data-model.md, contracts/, quickstart.md)
