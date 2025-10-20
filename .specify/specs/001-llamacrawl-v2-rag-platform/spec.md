# Feature Specification: LlamaCrawl v2 — Doc-to-Graph RAG Platform

**Feature Branch**: `001-llamacrawl-v2-rag-platform`
**Created**: 2025-10-20
**Status**: Draft
**Input**: Greenfield build of complete multi-source RAG platform with deterministic extraction, Neo4j graph storage, and hybrid retrieval

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - System Initialization & Health Verification (Priority: P1)

DevOps engineer or operator brings up the entire LlamaCrawl infrastructure and verifies all services are healthy and ready for ingestion.

**Why this priority**: Foundation for all downstream work. Without a healthy, initialized system, no ingestion or querying can occur. This is the critical first step.

**Independent Test**: Can be fully tested by `docker compose up -d`, running health checks, and verifying all 11 services report healthy status. Delivers operational confidence.

**Acceptance Scenarios**:

1. **Given** a clean environment with `.env` configured, **When** running `docker compose up -d`, **Then** all services (Qdrant, Neo4j, Redis, TEI, Ollama, Firecrawl, Playwright, taboot-app, taboot-worker) reach healthy state within 120 seconds.
2. **Given** all services healthy, **When** operator runs `taboot init`, **Then** Neo4j schema constraints are created, Qdrant collections are initialized, and Redis cache is ready.
3. **Given** operator runs `docker compose ps`, **Then** all 11 services show `Up` with health status passing.

---

### User Story 2 - Single-Source Web Ingestion (Priority: P1)

User ingests technical documentation from a single web URL, normalizes it, chunks it semantically, embeds it, and stores in Qdrant and Neo4j.

**Why this priority**: Core value proposition. Single-source ingestion is the MVP for the ingestion plane. Proves the full pipeline works end-to-end.

**Independent Test**: Can be fully tested by `taboot ingest web https://example.com`, verifying chunks appear in Qdrant with metadata, embedding vectors stored, and Doc nodes created in Neo4j. Delivers a queryable corpus.

**Acceptance Scenarios**:

1. **Given** a web URL containing technical documentation, **When** user runs `taboot ingest web <URL>`, **Then** Firecrawl crawls the URL, content is normalized (HTML → Markdown, boilerplate removed), and status is recorded.
2. **Given** normalized content from step 1, **When** chunker processes it, **Then** semantic chunks (≤512 tokens) are created with metadata (source URL, section, chunk_id).
3. **Given** chunks from step 2, **When** TEI embedding service processes them, **Then** vectors (1024-dim) are generated and upserted to Qdrant collection with payload metadata.
4. **Given** chunks in Qdrant, **When** Neo4j writer processes them, **Then** Doc node is created with `doc_id`, and MENTIONS relationships link doc to metadata nodes (Section, Hash).
5. **Given** ingestion completes, **When** user queries `taboot query "example query"`, **Then** results include chunks from the ingested document.

---

### User Story 3 - Deterministic Extraction for Structured Sources (Priority: P1)

User ingests structured configs (Docker Compose, SWAG specs, Tailscale configs) and extracts nodes/edges deterministically without LLM (Tier A extraction).

**Why this priority**: Deterministic parsing is core design principle. Proves Tier A extraction works. Enables fast, reproducible, cache-friendly ingestion of configs.

**Independent Test**: Can be fully tested by ingesting a Docker Compose file, verifying Service/Host/IP nodes and DEPENDS_ON/BINDS edges are created in Neo4j with high precision. Delivers configuration awareness.

**Acceptance Scenarios**:

1. **Given** a Docker Compose YAML file with services, ports, and environment variables, **When** user runs `taboot ingest compose <file>`, **Then** Tier A parser extracts Service nodes with names, Host nodes, IP nodes, and Endpoint nodes.
2. **Given** extracted nodes, **When** Neo4j writer processes them, **Then** DEPENDS_ON relationships are created for service dependencies, BINDS edges for port/protocol pairs, and ROUTES_TO edges for network paths.
3. **Given** extraction metadata, **When** user queries Neo4j for `"MATCH (s:Service)-[:DEPENDS_ON]->(d:Service) RETURN s, d"`, **Then** results correctly represent the service topology.
4. **Given** the same config processed twice, **When** comparing extraction results, **Then** outputs are byte-for-byte identical (deterministic).

---

### User Story 4 - Entity Extraction via spaCy (Tier B) (Priority: P2)

System processes ingested documents through spaCy NLP pipeline to identify named entities (Services, Hosts, IPs) and candidate extraction windows.

**Why this priority**: Tier B enables hybrid extraction. Tier A alone misses free-form prose mentions. spaCy is stateless and can process ≥200 sentences/sec.

**Independent Test**: Can be fully tested by feeding spaCy-processed chunks through entity ruler + matchers, verifying entity spans are identified with correct labels, and micro-windows are selected. Delivers extraction candidate pool.

**Acceptance Scenarios**:

1. **Given** a chunk from ingested documentation, **When** spaCy NLP pipeline processes it with entity_ruler and dependency matchers, **Then** named entities (Service, Host, IP, Proxy) are identified with confidence scores.
2. **Given** entity spans, **When** sentence classifier determines importance, **Then** high-relevance sentences are marked as candidates for LLM extraction (Tier C).
3. **Given** extraction windows selected, **When** user runs `taboot extract pending`, **Then** windows are queued for Tier C processing with correct token counts (≤512).

---

### User Story 5 - LLM-Powered Window Extraction (Tier C) (Priority: P2)

System extracts structured triples (subject, predicate, object) from text windows using Qwen3-4B-Instruct with JSON schema enforcement and Redis caching.

**Why this priority**: Tier C handles nuanced mentions that Tier A/B miss. Caching ensures reproducibility and cost-efficiency. Proves LLM integration works with batching and schema validation.

**Independent Test**: Can be fully tested by feeding a ≤512-token window through Ollama Qwen3-4B, verifying JSON schema output (triples list), checking Redis cache for duplicates, and storing results in Neo4j. Delivers fact extraction at scale.

**Acceptance Scenarios**:

1. **Given** a text window (≤512 tokens) and a JSON schema for triples `{subject, predicate, object}`, **When** Ollama LLM processes it with temperature=0, **Then** output conforms to schema and is parseable JSON.
2. **Given** the same window processed twice, **When** checking Redis cache by SHA-256 hash, **Then** second request returns cached result instead of calling LLM.
3. **Given** extracted triples, **When** Neo4j writer processes them, **Then** nodes are created/merged (idempotent) and relationships are stored with properties (e.g., confidence, span).
4. **Given** batches of 8–16 windows, **When** system processes them in parallel, **Then** throughput is ≥ median 250ms/window.

---

### User Story 6 - Hybrid Retrieval: Vector Search + Reranking (Priority: P2)

User queries the system and receives results ranked by relevance using vector similarity, metadata filtering, and LLM-based reranking.

**Why this priority**: Core retrieval logic. Without hybrid search, vector-only results are noisy. Reranking dramatically improves precision for user queries.

**Independent Test**: Can be fully tested by issuing a query, verifying ≥10 results from vector search, running reranker, and confirming top-5 are semantically relevant. Delivers search quality.

**Acceptance Scenarios**:

1. **Given** user query "Which services expose port 8080?", **When** system embeds query with TEI, **Then** query vector is 1024-dim and ready for Qdrant search.
2. **Given** query vector, **When** Qdrant searches with metadata filter (e.g., source="Docker Compose"), **Then** top-k (default 100) chunks are returned with similarity scores.
3. **Given** top-k chunks, **When** reranker (Qwen/Qwen3-Reranker-0.6B) rescores them, **Then** top-5 are semantically more relevant than raw vector order.
4. **Given** reranked results, **When** Neo4j graph traversal explores ≤2 hops from result nodes, **Then** related context nodes (dependencies, bindings) are discovered.

---

### User Story 7 - Synthesis with Inline Citations (Priority: P2)

System generates natural-language answers to user questions, citing specific sources and document sections with numeric citations.

**Why this priority**: Answers without citations are useless for technical teams. Inline numeric citations enable verification and source traceability.

**Independent Test**: Can be fully tested by querying "What does service X depend on?" and verifying response includes inline `[1]` citations that map to sources in bibliography. Delivers trusted answers.

**Acceptance Scenarios**:

1. **Given** reranked retrieval results with source metadata, **When** Qwen3-4B LLM generates an answer, **Then** answer includes inline numeric citations `[1]`, `[2]`, etc.
2. **Given** inline citations, **When** system builds a source list, **Then** bibliography shows `[1] DocName, Section 2.3, URL` format with document ID and chunk hash for traceability.
3. **Given** user queries spanning multiple sources, **When** synthesis completes, **Then** different sources are clearly distinguished in the bibliography.

---

### User Story 8 - Multi-Source Ingestion (GitHub, Reddit, YouTube, Gmail) (Priority: P3)

System supports ingesting from specialized sources beyond web URLs (GitHub repos, Reddit threads, YouTube transcripts, Gmail attachments).

**Why this priority**: Extends platform capability to diverse data sources. Requires adapter implementations per source. Delivers comprehensive knowledge graph.

**Independent Test**: Can be fully tested by ingesting a GitHub repository, extracting README + code comments, verifying content in Qdrant/Neo4j. Delivers source diversity.

**Acceptance Scenarios**:

1. **Given** GitHub credentials and repo URL, **When** user runs `taboot ingest github <repo>`, **Then** repo is fetched, README and code files are processed, and metadata includes commit hash, author.
2. **Given** Reddit source config, **When** user runs `taboot ingest reddit <subreddit>`, **Then** threads and comments are fetched, normalized, and stored with author/timestamp metadata.
3. **Given** YouTube video URL, **When** user runs `taboot ingest youtube <URL>`, **Then** transcript is extracted (via Firecrawl or Playwright), chunks are created, and metadata includes video title, timestamp markers.

---

### User Story 9 - Extraction Reprocessing & Version Control (Priority: P3)

User can reprocess documents with new/updated extractors, comparing extraction results, and selectively applying updates.

**Why this priority**: Supports iterative improvement of extractors. Enables A/B testing of extraction models. Critical for observability.

**Independent Test**: Can be fully tested by ingesting a doc, reprocessing with improved Tier B model, comparing triple counts/precision, and verifying new triples are stored. Delivers continuous improvement.

**Acceptance Scenarios**:

1. **Given** documents processed 7 days ago, **When** user runs `taboot extract reprocess --since 7d`, **Then** documents are re-extracted with current extractor version.
2. **Given** old and new extraction results, **When** system compares them, **Then** diff shows new triples, removed triples, and confidence changes.
3. **Given** extraction diff, **When** user accepts updates, **Then** Neo4j is updated idempotently (duplicates not created).

---

### User Story 10 - Observability, Metrics & Validation (Priority: P3)

System exports metrics (throughput, latency, cache hit-rate, F1 scores) and validates extraction quality against labeled data.

**Why this priority**: Production readiness. Without observability, performance regressions go undetected. Validation gates ensure quality.

**Independent Test**: Can be fully tested by running extraction pipeline, collecting metrics from Prometheus/logs, computing F1 on ~300 labeled windows, and verifying CI gates. Delivers quality confidence.

**Acceptance Scenarios**:

1. **Given** extraction worker processing documents, **When** system logs metrics, **Then** JSON logs include `windows_processed`, `tier_a_hits`, `tier_b_hits`, `tier_c_duration_ms`, `cache_hit_rate`.
2. **Given** ~300 labeled windows with ground-truth extraction, **When** system computes precision/recall/F1 against Tier C outputs, **Then** F1 ≥ 0.80 (configurable threshold).
3. **Given** extraction F1 drops ≥2 points, **When** CI runs, **Then** pipeline fails and alerts maintainers.

---

### Edge Cases

- **What happens when a web page has no body content (boilerplate-only HTML)?** Accept Firecrawl's judgment. If Firecrawl returns content (even minimal), attempt ingestion. If Firecrawl signals empty/error, log the URL as unprocessable with reason and skip. Increment `skipped_docs` metric for observability.
- What happens when chunker encounters a token-counting discrepancy (estimated ≠ actual)?
- **How does system handle Tier C LLM timeout or malformed JSON output?** Mark window as failed with error details (timeout duration, JSON parse error), add to DLQ (dead-letter queue) in Redis sorted set with timestamp and doc_id, continue processing remaining windows in batch. Operators can query DLQ via `taboot status dlq` and selectively retry failed windows. Prevents single window failure from blocking entire document extraction.
- **What happens when Neo4j constraint violation occurs (duplicate Service.name)?** MERGE nodes idempotently using Cypher MERGE clause. If node exists, update properties with new values (if changed), preserve existing values (if unchanged). Add `updated_at` timestamp for observability. Enables multi-source enrichment: e.g., Service discovered in Docker Compose can be enriched with version info from docs. Last-write-wins for conflicting property values.
- **How does reranker handle very short queries (<3 tokens)?** Skip reranking entirely; return vector search results directly. Reranking cross-encoders require semantic context to meaningfully compare relevance. For queries like "redis", "port 80", vector similarity is sufficient and faster. Threshold configurable via `MIN_RERANK_TOKENS` env var (default: 3). Log skipped reranking events for observability.
- What happens when embeddings service is slow; does ingestion queue back up?
- How does system recover from partial extraction failure (some windows succeed, some fail)?
- What happens when a source is revoked (e.g., GitHub token expires)?

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion Plane**

- **FR-001**: System MUST accept URLs, local files, and credentials for 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions).
- **FR-002**: System MUST normalize ingested content (HTML → Markdown, boilerplate removal, UTF-8 validation).
- **FR-003**: System MUST chunk normalized content semantically with overlap, respecting token limits (≤512).
- **FR-004**: System MUST generate embeddings (1024-dimensional vectors) using TEI for all chunks via GPU acceleration.
- **FR-005**: System MUST upsert vectors to Qdrant with payload metadata (source, doc_id, section, chunk_hash).
- **FR-006**: System MUST support deterministic parsing for structured sources (Docker Compose, SWAG, Tailscale, Unifi configs).

**Extraction Plane (Async, Decoupled)**

- **FR-009**: System MUST buffer all extracted triples (Tier A/B/C output) in Redis during batch processing with 24-hour TTL-based auto-cleanup. DLQ pattern via Redis sorted sets tracks failed windows for manual retry or reprocessing.
- **FR-010**: System MUST implement Tier A extraction (regex, JSON/YAML parsing, Aho-Corasick dictionaries) for deterministic triple extraction ≥50 pages/sec (CPU).
- **FR-011**: System MUST implement Tier B extraction (spaCy entity_ruler, dependency matchers, sentence classifier) for entity recognition and window selection ≥200 sentences/sec (en_core_web_md) or ≥40 (trf).
- **FR-012**: System MUST implement Tier C extraction (Qwen3-4B-Instruct via Ollama) with ≤512-token windows, temperature=0, JSON schema enforcement, batched 8–16, median ≤250ms/window.
- **FR-013**: System MUST cache Tier C LLM requests by SHA-256 window hash in Redis with 24-hour TTL to avoid duplicate calls.
- **FR-014**: System MUST extract deterministic triples (subject, predicate, object) from text, buffer them in Redis during batch processing with configurable TTL, and atomically commit batches to Neo4j. Enables recovery from partial failures, dead-letter queue (DLQ) pattern for failed windows, and observability of pending extractions.
- **FR-015**: System MUST handle service failures by failing fast with clear error reporting. If external service (Firecrawl, TEI, Neo4j, Ollama, Qdrant) fails during ingestion/extraction, stop immediately, log the failure, and require manual intervention to restart. No silent partial data or fallback modes. Aligns with pre-production error-early culture.

**Storage & Graph**

- **FR-020**: System MUST create and maintain Neo4j property graph with node labels: Service, Host, IP, Proxy, Endpoint, Doc. (Section data embedded in Chunk attributes and MENTIONS relationship properties; no explicit Section nodes in MVP.)
- **FR-021**: System MUST enforce unique constraints on Service.name and Host.hostname.
- **FR-022**: System MUST create composite indexes on Endpoint(service, method, path) for query performance.
- **FR-023**: System MUST store relationship types: DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT with properties (host, port, protocol, auth). MENTIONS relationships link Doc → Chunk directly with properties (section, hash, span) for source traceability; no intermediate Section nodes in MVP.
- **FR-024**: System MUST write to Neo4j using batched UNWIND statements (≥2k rows per batch, ≥20k edges/min throughput).
- **FR-025**: System MUST idempotently merge nodes/edges (no duplicates on re-ingestion).

**Retrieval & Synthesis**

- **FR-030**: System MUST embed user queries using TEI to match chunk vectors.
- **FR-031**: System MUST filter retrieval results by metadata (source, date, tags) before vector search.
- **FR-032**: System MUST search Qdrant for top-k (default 100) similar chunks using HNSW indexing.
- **FR-033**: System MUST rerank top-k results using Qwen/Qwen3-Reranker-0.6B to improve precision, except for queries <3 tokens (configurable via MIN_RERANK_TOKENS) where vector results are returned directly.
- **FR-034**: System MUST traverse Neo4j graph (≤2 hops) from result nodes to discover related context (dependencies, relationships).
- **FR-035**: System MUST generate natural-language answers using Qwen3-4B with inline numeric citations `[1]`, `[2]`, etc.
- **FR-036**: System MUST build and return source bibliography with document ID, section, URL, and chunk hash for verification.
- **FR-037**: System MUST support query filtering by source, date range, and custom tags.

**API & CLI**

- **FR-040**: System MUST expose FastAPI REST endpoints for ingestion, querying, and status (documented in OpenAPI 3.0) with Bearer Token (JWT) authentication for all endpoints. Tokens include expiry and support refresh mechanics for long-lived clients.
- **FR-041**: System MUST provide Typer CLI for all operations: ingest, extract, query, graph, status, init.
- **FR-042**: System MUST provide MCP server interface for integration with other AI systems.
- **FR-043**: System MUST validate input (URLs, credentials, query text) with clear error messages.
- **FR-044**: System MUST support async operations for long-running tasks (crawl, extract, graph write).

**Data Governance & Security**

- **FR-050**: System MUST support per-document retention policies (auto-delete after N days).
- **FR-051**: System MUST support per-document erasure (delete all triples, embeddings, and metadata for a given doc_id).
- **FR-052**: System MUST log all data access and modifications for audit trails.
- **FR-053**: System MUST enforce read-only access to Neo4j for query-only roles.
- **FR-054**: System MUST validate credentials for all sources (GitHub token, Reddit API key, Gmail service account, etc.).

**Testing & Validation**

- **FR-060**: System MUST compute extraction precision/recall/F1 against ~300 labeled windows.
- **FR-061**: System MUST fail CI if F1 drops ≥2 points from baseline.
- **FR-062**: System MUST provide unit tests for all adapters with ≥85% coverage in packages/core.
- **FR-063**: System MUST provide integration tests for end-to-end pipelines (ingest → extract → query).
- **FR-064**: System MUST implement unit tests before implementation code following TDD Red-Green-Refactor cycle (write failing test, write minimal passing code, refactor).
- **FR-065**: System MUST achieve ≥85% test coverage in packages/core and extraction logic before merging to main branch.

### Key Entities

- **Document**: Represents a single ingested source (web URL, GitHub repo, Reddit thread, etc.). Attributes: `doc_id` (PK), `source_type`, `url`, `title`, `ingested_at`, `updated_at`, `retention_policy`.

- **Chunk**: Semantic segment of a document. Attributes: `chunk_id` (PK), `doc_id`, `text`, `token_count`, `section`, `chunk_hash`, `embedding` (1024-dim vector in Qdrant).

- **Triple**: Extracted fact (subject, predicate, object). Attributes: `triple_id` (PK), `chunk_id`, `subject`, `predicate`, `object`, `confidence`, `tier` (A/B/C), `span`.

- **Service**: Infrastructure component (deployed microservice, daemon, etc.). Attributes: `name` (PK, unique), `version`, `doc_id`.

- **Host**: Physical or virtual machine. Attributes: `hostname` (PK, unique), `ip_addresses`, `doc_id`.

- **IP**: Network address. Attributes: `addr` (PK, unique), `cidr`, `doc_id`.

- **Endpoint**: HTTP/RPC endpoint exposed by a service. Attributes: `service`, `method`, `path` (composite PK), `auth_required`, `port`, `protocol`.

- **Doc (Neo4j)**: Reference node for each ingested document. Attributes: `doc_id` (PK, unique), `source_type`, `url`, `title`, `ingested_at`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System initialization completes in <120 seconds; all 11 services reach healthy state.
- **SC-002**: Single web page (≤50KB) ingests end-to-end (crawl → normalize → chunk → embed → store) in <10 seconds on RTX 4070.
- **SC-003**: Tier A extraction processes structured configs at ≥50 pages/sec (CPU-bound, deterministic).
- **SC-004**: Tier B extraction processes text at ≥200 sentences/sec (en_core_web_md model) or ≥40 sentences/sec (transformer model).
- **SC-005**: Tier C extraction window processing median ≤250ms, p95 ≤750ms, with batch size 8–16 on RTX 4070.
- **SC-006**: Neo4j bulk writes achieve ≥20,000 edges/minute with 2k-row UNWIND batches.
- **SC-007**: Qdrant vector upserts achieve ≥5,000 vectors/second (1024-dim, HNSW indexing).
- **SC-008**: Extraction precision/recall/F1 ≥0.80 on ~300 labeled windows, with precision-first optimization (target precision ≥0.85, recall ≥0.75). False triples in infrastructure graphs are operationally dangerous; minimize false positives over missed facts. **Note:** F1 ≥0.80 is MVP target; production readiness requires F1 ≥0.90 per constitution.
- **SC-009**: User query retrieval completes in <3 seconds (embedding + vector search + rerank + graph traversal + synthesis).
- **SC-010**: Inline citations in synthesis responses are accurate; 100% of cited sources are correct and relevant.
- **SC-011**: System supports end-to-end ingestion from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions).
- **SC-012**: Multi-source queries return relevant results blended from ≥2 sources with proper attribution.
- **SC-013**: Cache hit rate on Tier C LLM requests ≥60% for repeated document re-processing.
- **SC-014**: System observability exports metrics (throughput, latency, hit-rates, F1) in JSON structured logs consumable by monitoring tools.
- **SC-015**: Data erasure (per-doc) completes in <10 seconds for any document, including all triples, embeddings, and metadata.

---

## Assumptions

- **LLM Model**: Qwen3-4B-Instruct via Ollama is the initial model; others can be swapped by changing config/env vars.
- **Embedding Model**: TEI-served Qwen3-Embedding-0.6B (1024-dim) is baseline; other models supported with config change.
- **Reranker Model**: Qwen/Qwen3-Reranker-0.6B is baseline; alternative rerankers can be plugged in.
- **spaCy Model**: en_core_web_md is baseline for Tier B; en_core_web_trf available for higher accuracy at cost of speed.
- **Graph Traversal Depth**: ≤2 hops is sufficient for most queries; deeper traversal adds noise and latency.
- **Extraction Quality Gate**: F1 ≥0.80 is acceptable baseline; can be tuned per deployment.
- **Vector Search Top-K**: Default 100 candidates before reranking; tunable per query or globally.
- **Batch Size**: Tier C LLM batching at 8–16 windows balances throughput and latency; can be tuned per GPU.
- **GPU Availability**: Platform assumes NVIDIA GPU with ≥8GB VRAM; CPU-only fallbacks degrade performance ≥10x.
- **Production Deployment**: Docker Compose stack is development reference; production uses Kubernetes or managed services (AKS, EKS, GKE).

---

## Non-Goals (Out of Scope)

- **Frontend Analytics Dashboard**: Web UI is optional; API and CLI are primary interfaces.
- **Fine-tuning Extractors**: Custom model fine-tuning is future work (Roadmap item).
- **Real-time Incremental Crawlers**: Batch ingestion only; incremental crawlers with watchers are P3 (Roadmap).
- **Graph Visual Analytics**: Blast radius and impact analysis UI not included in MVP.
- **Multi-tenancy**: Single-tenant deployment; multi-tenant isolation requires architectural changes.
- **Encryption at Rest**: Data encryption and key management deferred to deployment-specific handling (e.g., Kubernetes secrets, vault).

---

## Clarifications

### Session 2025-10-20

- Q: API authentication mechanism for FastAPI endpoints (FR-040)? → A: Bearer Token (JWT) with stateless auth, expiry, and refresh token support. Enables both CLI and external client integration without session management overhead.
- Q: Neo4j MENTIONS relationship target (FR-023)? → A: Doc → Chunk (direct). Chunk carries section, hash, span attributes; MENTIONS properties embed these for traceability. No explicit Section nodes in MVP (can add hierarchical structure later if needed).
- Q: Extraction output lifecycle (FR-014) — where do triples live during processing? → A: Redis with TTL. Enables DLQ pattern, partial failure recovery, observability of pending extractions. Atomic Neo4j batch commits prevent partially-committed data.
- Q: External service failure strategy (FR-015)? → A: Fail fast with clear error. Stop ingestion immediately if any external service fails; require manual restart. No fallback modes or silent partial data. Aligns with pre-production error-early culture.
- Q: Extraction quality trade-off — precision vs recall (SC-008)? → A: Precision-first (target precision ≥0.85, recall ≥0.75). False triples in infrastructure graphs are operationally dangerous; minimize false positives over missed facts.
- Q: Redis buffering TTL duration for extraction triples (FR-009)? → A: 24 hours. Balances memory efficiency with reasonable failure recovery window for batch reprocessing within business day.
- Q: Handling web pages with no body content (boilerplate-only HTML)? → A: Accept Firecrawl's judgment. If it returns content, ingest it; if it returns empty/error, log URL as unprocessable and skip. Delegates boilerplate filtering to specialized crawler.
- Q: Handling Tier C LLM timeout or malformed JSON output? → A: Mark window as failed, add to DLQ (dead-letter queue) in Redis with error details, continue processing other windows. Enables batch resilience while preserving fail-fast culture. Operators can inspect/retry DLQ manually.
- Q: Handling Neo4j constraint violations (duplicate Service.name)? → A: MERGE nodes idempotently. Update properties if changed, preserve existing if unchanged. Enables multi-source enrichment without duplication. Last-write-wins with timestamp tracking for observability.
- Q: Handling very short queries (<3 tokens) for reranking? → A: Skip reranking, return vector search results directly. Reranking models need semantic context; short queries perform adequately with vector similarity alone. Saves GPU cycles. Threshold configurable via MIN_RERANK_TOKENS env var.

