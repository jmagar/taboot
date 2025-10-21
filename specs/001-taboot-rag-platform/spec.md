# Feature Specification: Taboot Doc-to-Graph RAG Platform

**Feature Branch**: `001-taboot-rag-platform`
**Created**: 2025-10-20
**Status**: Draft
**Input**: User description: "This is a complete greenfield project, everything needs to be implemented. We've just about scaffolded everything, all the docker services are online and operational, except the worker because it has no code yet. Any python currently in the codebase is a stub. We have proper documentation for how we want everything implemented."

## Clarifications

### Session 2025-10-20

- Q: What development methodology should be followed during implementation? → A: Test-Driven Development (TDD) using RED-GREEN-REFACTOR cycle. Production code must not be written until failing tests exist. RED: Write failing test first. GREEN: Write minimum code to pass. REFACTOR: Improve code while keeping tests green.

## User Scenarios & Testing

### User Story 1 - Ingest Web Documentation (Priority: P1)

As a developer, I want to ingest technical documentation from web sources so that I can build a knowledge base for answering questions about my infrastructure and services.

**Why this priority**: This is the foundation of the entire platform - without ingestion, there's no data to query. Web sources (docs, GitHub, Reddit, etc.) are the primary input channels.

**Independent Test**: Can be fully tested by running `taboot ingest web https://example.com --limit 20` and verifying that documents are successfully crawled, normalized, chunked, embedded, and stored in Qdrant. Delivers immediate value: searchable documentation.

**Acceptance Scenarios**:

1. **Given** a valid web URL, **When** the user runs the ingest command, **Then** the system crawls the page using Firecrawl, extracts content, chunks it semantically, generates embeddings via TEI, and stores vectors in Qdrant with metadata
2. **Given** a web URL with multiple pages (up to specified limit), **When** ingestion completes, **Then** all pages are processed and the user receives a summary showing total pages ingested, chunks created, and any failures
3. **Given** an ingestion job is running, **When** the user checks job status, **Then** they see real-time progress including pages processed, current stage, and estimated time remaining
4. **Given** a previously ingested URL, **When** the user re-ingests the same URL, **Then** the system detects duplicate content and either skips or updates existing chunks based on content hash

---

### User Story 2 - Extract Graph Knowledge (Priority: P1)

As a developer, I want the system to automatically extract structured knowledge from ingested documents and build a property graph so that I can discover relationships between services, hosts, endpoints, and configurations.

**Why this priority**: Graph extraction is co-equal with ingestion - it's what transforms raw text into queryable knowledge. Without this, we only have vector search without relationship context.

**Independent Test**: Can be fully tested by running `taboot extract pending` after ingestion and verifying that Neo4j contains nodes (Service, Host, IP, Endpoint, etc.) and relationships (DEPENDS_ON, ROUTES_TO, etc.) extracted from the documents. Delivers immediate value: relationship discovery.

**Acceptance Scenarios**:

1. **Given** documents waiting in the extraction queue, **When** the extraction worker processes them, **Then** Tier A deterministic extractors parse code blocks, tables, and config files to create initial graph entities
2. **Given** text content with entity mentions, **When** Tier B spaCy extractors run, **Then** named entities (services, hosts, IPs) are identified and candidate micro-windows are selected for LLM processing
3. **Given** candidate micro-windows (≤512 tokens), **When** Tier C LLM extraction runs, **Then** Qwen3-4B-Instruct generates JSON-schema compliant triples (subject, predicate, object) that are batched and cached in Redis
4. **Given** extracted triples, **When** graph writes execute, **Then** Neo4j receives batched UNWIND operations creating/merging nodes and relationships with proper constraints enforced
5. **Given** extraction completion, **When** the user queries the graph, **Then** they can traverse relationships (e.g., "Which services depend on redis?", "Show all endpoints exposed by auth-service")

---

### User Story 3 - Query with Hybrid Retrieval (Priority: P1)

As a developer, I want to ask natural language questions and receive answers with source citations so that I can quickly find relevant information across all ingested documentation and understand the relationships between components.

**Why this priority**: Querying is the primary user-facing capability - it's why the platform exists. All prior work (ingestion, extraction) exists to enable high-quality retrieval and synthesis.

**Independent Test**: Can be fully tested by running `taboot query "Which services expose port 8080?"` and verifying that the system returns an answer with inline citations, source links, and relevant graph context. Delivers immediate value: instant answers from documentation.

**Acceptance Scenarios**:

1. **Given** a natural language question, **When** the user submits a query, **Then** the system generates a query embedding via TEI, searches Qdrant for top-k relevant chunks (filtered by metadata if specified), and returns initial results within 2 seconds
2. **Given** initial vector search results, **When** reranking executes, **Then** Qwen3-Reranker-0.6B re-scores chunks for relevance, selects top candidates, and the quality of top-3 results improves measurably over pure vector search
3. **Given** reranked results, **When** graph traversal executes, **Then** the system identifies related entities in Neo4j (≤2 hops), retrieves connected context, and enriches the result set with relationship information
4. **Given** enriched context, **When** answer synthesis runs, **Then** Qwen3-4B-Instruct generates a coherent answer with inline numeric citations (e.g., [1], [2]) and appends a source list with document titles and URLs
5. **Given** a query with metadata filters (--sources, --after date), **When** retrieval executes, **Then** only matching sources/timeframes are searched, and the user receives targeted results
6. **Given** a complex multi-hop question ("How does service X connect to database Y through proxy Z?"), **When** graph traversal runs, **Then** the system discovers the connection path and includes it in the synthesized answer

---

### User Story 4 - Initialize System Schema and Collections (Priority: P1)

As a developer, I want to initialize the database schemas, vector collections, and indexes so that the platform is ready to ingest and store data.

**Why this priority**: Initialization is a prerequisite for all other functionality - databases must have schemas and collections before ingestion/extraction can begin.

**Independent Test**: Can be fully tested by running `taboot init` and verifying that Neo4j has constraints/indexes created, Qdrant has collections configured with correct dimensionality and HNSW settings, and the system reports readiness. Delivers immediate value: operational infrastructure.

**Acceptance Scenarios**:

1. **Given** a fresh deployment, **When** the user runs init command, **Then** Neo4j constraints are created (Service.name unique, Host.hostname unique, Endpoint composite index) and the system confirms constraint creation
2. **Given** Neo4j initialized, **When** Qdrant initialization runs, **Then** vector collections are created with 768-dimensional vectors, HNSW indexing enabled, and metadata schema configured for filtering
3. **Given** all schemas initialized, **When** the system performs health checks, **Then** all services (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl) report healthy status and the init command completes successfully
4. **Given** an already-initialized system, **When** init runs again, **Then** the system detects existing schemas, skips redundant operations, and reports current configuration status

---

### User Story 5 - Ingest from Structured Sources (Priority: P2)

As a developer, I want to ingest infrastructure configurations (Docker Compose, SWAG reverse proxy, Tailscale, Unifi) so that I can automatically map my deployed services and network topology into the knowledge graph.

**Why this priority**: Structured sources provide high-value, deterministic data that directly populates the graph without LLM processing. This is important but secondary to web ingestion since web docs are the primary knowledge source.

**Independent Test**: Can be fully tested by running `taboot ingest docker-compose ./docker-compose.yml` and verifying that services, networks, volumes, and dependencies are parsed and created as Neo4j nodes/relationships. Delivers immediate value: infrastructure-as-graph.

**Acceptance Scenarios**:

1. **Given** a Docker Compose file, **When** the user ingests it, **Then** the system parses service definitions, creates Service nodes, extracts port bindings (BINDS relationships), and maps dependencies (DEPENDS_ON relationships)
2. **Given** a SWAG reverse proxy configuration, **When** ingestion runs, **Then** Proxy nodes are created, ROUTES_TO relationships link proxies to backend services with host/path/TLS metadata
3. **Given** Tailscale network data, **When** ingested, **Then** Host nodes represent machines, IP nodes represent addresses, and network topology relationships are established
4. **Given** Unifi controller API access, **When** ingestion runs, **Then** network devices, VLANs, and firewall rules are represented in the graph
5. **Given** multiple structured sources ingested, **When** the user queries relationships, **Then** cross-source connections are discoverable (e.g., "Which Docker services are exposed via SWAG proxy?")

---

### User Story 6 - Monitor Extraction Pipeline (Priority: P2)

As a developer, I want to monitor extraction pipeline metrics and status so that I can ensure the system is processing documents efficiently and identify bottlenecks.

**Why this priority**: Observability is critical for production operation but not needed for initial MVP functionality. Monitoring enables optimization and troubleshooting.

**Independent Test**: Can be fully tested by running `taboot extract status` after processing documents and verifying that metrics display tier hit ratios, throughput (windows/sec), LLM latency (p95), cache hit rates, and queue depth. Delivers immediate value: operational visibility.

**Acceptance Scenarios**:

1. **Given** documents processed by the extraction pipeline, **When** the user checks status, **Then** they see tier-by-tier metrics: Tier A (pages/sec), Tier B (sentences/sec), Tier C (windows/sec, median/p95 latency)
2. **Given** active extraction jobs, **When** status is checked, **Then** the system reports current queue depth, processing rate, estimated completion time, and any error rates
3. **Given** completed extractions, **When** the user reviews historical metrics, **Then** they can see trends over time, identify performance regressions, and validate against targets (≥50 pages/sec Tier A, ≥200 sent/sec Tier B, ≤250ms median Tier C)
4. **Given** Redis cache utilization, **When** metrics are displayed, **Then** cache hit rate for LLM prompts is visible, enabling optimization decisions
5. **Given** Neo4j/Qdrant write throughput, **When** the user checks system health, **Then** writes/sec are reported and compared against targets (≥20k edges/min Neo4j, ≥5k vectors/sec Qdrant)

---

### User Story 7 - Ingest from External APIs (Priority: P3)

As a developer, I want to ingest data from external sources (GitHub repos, Reddit threads, YouTube transcripts, Gmail, Elasticsearch indices) so that I can consolidate knowledge from multiple platforms.

**Why this priority**: Multi-source ingestion is valuable for comprehensive knowledge coverage but not critical for initial platform validation. Web + structured sources cover core use cases.

**Independent Test**: Can be fully tested by running `taboot ingest github owner/repo` and verifying that repository README, issues, and code are ingested and queryable. Delivers immediate value: multi-source knowledge aggregation.

**Acceptance Scenarios**:

1. **Given** a GitHub repository URL, **When** the user ingests it, **Then** README files, wiki pages, and open issues are crawled, chunked, and stored with metadata (repo name, file path, commit hash)
2. **Given** a Reddit subreddit, **When** ingestion runs (with --limit), **Then** post titles, bodies, and top comments are extracted, embedded, and made searchable
3. **Given** a YouTube video URL, **When** ingested, **Then** transcripts are fetched, timestamped, chunked, and linked to video segments for citation
4. **Given** Gmail API credentials, **When** email ingestion runs, **Then** relevant threads (filtered by label/date) are processed with sender/recipient metadata preserved
5. **Given** Elasticsearch index access, **When** the user ingests logs/metrics, **Then** structured log entries are parsed, entities extracted, and incidents linked in the graph

---

### User Story 8 - Reprocess Documents with Updated Extractors (Priority: P3)

As a developer, I want to reprocess previously ingested documents when extraction logic improves so that the knowledge graph stays current with better extraction quality.

**Why this priority**: Reprocessing is important for maintaining quality over time but not essential for initial deployment. It enables iterative improvement of extraction logic.

**Independent Test**: Can be fully tested by running `taboot extract reprocess --since 7d` after modifying extraction rules and verifying that recent documents are re-extracted with new logic and graph is updated. Delivers immediate value: continuous quality improvement.

**Acceptance Scenarios**:

1. **Given** documents ingested with version N of extractors, **When** version N+1 extractors are deployed and reprocess runs, **Then** affected documents are re-extracted, new triples generated, and graph nodes/relationships updated or merged
2. **Given** a reprocessing job with date filter, **When** execution starts, **Then** only documents ingested after the specified date are queued for re-extraction
3. **Given** reprocessing in progress, **When** the user checks status, **Then** they see documents reprocessed count, remaining count, and any improvements in extraction metrics (e.g., triples per document)
4. **Given** reprocessing completes, **When** the user queries updated entities, **Then** answers reflect improved extraction quality and new relationships discovered by enhanced extractors

---

### Edge Cases

- What happens when Firecrawl encounters rate limits or blocked domains during web ingestion?
  - System should respect robots.txt, implement exponential backoff, queue failed URLs to Dead Letter Queue (DLQ), and report failures in job summary

- How does the system handle malformed or non-text content (PDFs, images, binary files)?
  - PDFs are extracted via Firecrawl; images ignored unless OCR is explicitly enabled; binary files skipped with warning logged

- What happens when Neo4j constraint violations occur (e.g., duplicate service names with conflicting attributes)?
  - System uses MERGE logic to update existing nodes; conflicting attributes trigger metadata comparison and either merge or create versioned nodes based on source timestamp

- How does Tier C handle LLM failures (timeout, invalid JSON, hallucinations)?
  - Timeout: retry once with backoff, then mark window as failed and move to DLQ
  - Invalid JSON: schema validation rejects response, logs error, retries with clarified prompt
  - Hallucinations: post-processing filters reject triples referencing entities not mentioned in source text

- What happens when Qdrant vector dimension mismatches occur (e.g., model change)?
  - System detects dimension mismatch during upsert, logs critical error, and halts ingestion until collection is recreated or model reverted

- How does the system handle extremely large documents (>10MB text, >1000 pages)?
  - Documents are chunked into smaller units before embedding; if single sections exceed limits, they are split further with overlap to preserve context

- What happens when Redis cache evicts active extraction state?
  - Eviction triggers re-extraction of affected windows; frequent evictions indicate insufficient cache memory and trigger alerts

- How does query processing handle ambiguous questions or zero results?
  - Ambiguous: system returns top-k results with confidence scores, suggests query refinements
  - Zero results: system reports "no relevant documents found," suggests broader search terms or relaxed filters

## Requirements

### Functional Requirements

#### Ingestion Requirements

- **FR-001**: System MUST crawl web pages using Firecrawl API, respecting robots.txt and rate limits
- **FR-002**: System MUST normalize HTML to Markdown, removing navigation, ads, and boilerplate content
- **FR-003**: System MUST chunk documents semantically (target: 256-512 tokens per chunk with 10% overlap)
- **FR-004**: System MUST generate embeddings via TEI service using configured model (default: Qwen3-Embedding-0.6B, 768-dim)
- **FR-005**: System MUST store chunk vectors in Qdrant with metadata (source URL, doc_id, section, timestamp, source type)
- **FR-006**: System MUST support ingestion from multiple sources: web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi
- **FR-007**: System MUST track ingestion jobs with states: pending, running, completed, failed
- **FR-008**: System MUST provide progress reporting during ingestion (pages processed, current stage, ETA)
- **FR-009**: System MUST handle duplicate content by comparing content hashes and skipping or updating chunks
- **FR-010**: System MUST implement configurable concurrency limits for crawling (default: 5 concurrent requests)

#### Extraction Requirements

- **FR-011**: System MUST execute Tier A deterministic extraction to parse fenced code blocks, markdown tables, YAML/JSON configs, and Aho-Corasick patterns for known entities (services, hosts, IPs, ports)
- **FR-012**: System MUST execute Tier B spaCy extraction using entity_ruler and dependency matchers on en_core_web_md (or trf for complex prose) to identify entities and select micro-windows
- **FR-013**: System MUST execute Tier C LLM extraction on micro-windows (≤512 tokens) using Qwen3-4B-Instruct via Ollama with temperature 0, JSON-schema validation, batch size 8-16
- **FR-014**: System MUST cache LLM prompts and responses in Redis using SHA-256 hash of window content as key
- **FR-015**: System MUST generate triples (subject, predicate, object) conforming to predefined relationship types: DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, MENTIONS
- **FR-016**: System MUST write triples to Neo4j in batched UNWIND operations (target: 2k-row batches, ≥20k edges/min throughput)
- **FR-017**: System MUST enforce Neo4j constraints (Service.name unique, Host.hostname unique) and handle merge conflicts
- **FR-018**: System MUST track extraction state per document: pending, tier_a_done, tier_b_done, tier_c_done, completed, failed
- **FR-019**: System MUST log extraction metrics: tier hit ratios, windows/sec, LLM latency (median, p95), cache hit rate, Neo4j/Qdrant throughput
- **FR-020**: System MUST implement Dead Letter Queue (DLQ) in Redis for failed extractions with retry policy (max 3 retries with exponential backoff)

#### Retrieval Requirements

- **FR-021**: System MUST generate query embeddings via TEI using the same model as document embeddings
- **FR-022**: System MUST perform vector search in Qdrant with configurable top-k (default: 20) and optional metadata filters (source, date range, tags)
- **FR-023**: System MUST rerank vector search results using Qwen3-Reranker-0.6B via SentenceTransformers service (batch size 16, GPU if available)
- **FR-024**: System MUST perform graph traversal in Neo4j (≤2 hops) starting from entities mentioned in top-ranked chunks to retrieve related nodes/relationships
- **FR-025**: System MUST synthesize answers using Qwen3-4B-Instruct with enriched context (chunks + graph), generating inline numeric citations [1], [2] and source list
- **FR-026**: System MUST return answers within 5 seconds for typical queries (median) and within 10 seconds for complex multi-hop queries (p95)
- **FR-027**: System MUST support query filters: --sources (comma-separated list), --after (ISO date), --top-k (integer)
- **FR-028**: System MUST handle zero-result queries by suggesting alternative search terms or broader filters
- **FR-029**: System MUST log retrieval metrics: query latency by stage (embed, vector search, rerank, graph, synthesis), result count, cache hits

#### System Initialization Requirements

- **FR-030**: System MUST create Neo4j constraints on first init: Service.name (unique), Host.hostname (unique), Endpoint(service, method, path) composite index
- **FR-031**: System MUST create Qdrant collections with configuration: 768-dim vectors, HNSW indexing, cosine similarity, metadata schema for filtering
- **FR-032**: System MUST verify health of all services (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright) before reporting init success
- **FR-033**: System MUST detect existing schemas on repeat init and skip redundant operations, reporting current configuration
- **FR-034**: System MUST download required models on first run: Qwen3-4B-Instruct (Ollama), Qwen3-Embedding-0.6B (TEI), Qwen3-Reranker-0.6B (SentenceTransformers), en_core_web_md (spaCy)

#### Observability Requirements

- **FR-035**: System MUST emit structured JSON logs with correlation IDs tracing doc_id → section → windows → triples → Neo4j txId
- **FR-036**: System MUST expose metrics endpoint reporting: ingestion rate, extraction throughput by tier, query latency percentiles, cache hit rates, database write rates
- **FR-037**: System MUST provide status commands showing: job progress, queue depth, service health, current configuration
- **FR-038**: System MUST log errors with severity levels and context (document ID, extraction tier, failed operation)
- **FR-039**: System MUST track and report extraction quality metrics: triples per document, entity coverage, F1 score against labeled validation set (target: ≥0.85)

#### CLI Requirements

- **FR-040**: System MUST provide CLI command: `taboot init` (initialize schemas, collections, indexes)
- **FR-041**: System MUST provide CLI command: `taboot ingest SOURCE TARGET [--limit N]` (ingest from specified source)
- **FR-042**: System MUST provide CLI command: `taboot extract pending` (process documents awaiting extraction)
- **FR-043**: System MUST provide CLI command: `taboot extract reprocess --since DATE` (re-extract documents since date)
- **FR-044**: System MUST provide CLI command: `taboot extract status` (show extraction pipeline metrics)
- **FR-045**: System MUST provide CLI command: `taboot query "question" [--sources X,Y] [--after DATE] [--top-k N]` (perform hybrid retrieval)
- **FR-046**: System MUST provide CLI command: `taboot status [--component COMP] [--verbose]` (show system health)
- **FR-047**: System MUST provide CLI command: `taboot list RESOURCE [--limit N] [--filter EXPR]` (list documents, jobs, entities)

#### Development Methodology Requirements

- **FR-048**: All production code MUST be developed using Test-Driven Development (TDD) methodology following the RED-GREEN-REFACTOR cycle
- **FR-049**: Tests MUST be written before any production code (RED phase: write failing test that defines expected behavior)
- **FR-050**: Production code MUST be written only after a failing test exists, implementing minimum necessary logic to make the test pass (GREEN phase)
- **FR-051**: Code MUST be refactored for quality while maintaining passing tests (REFACTOR phase: improve code without changing behavior)
- **FR-052**: Test suite MUST maintain ≥85% code coverage across all packages (core, adapters, apps)
- **FR-053**: Each functional requirement (FR-001 through FR-047) MUST have corresponding test cases validating the specified behavior before implementation

### Key Entities

- **Document (Doc)**: Represents an ingested document with attributes: doc_id (UUID), source_url, source_type (web, github, reddit, etc.), content_hash (SHA-256), ingested_at (timestamp), extraction_state (pending, completed, failed), metadata (JSON)

- **Chunk**: Represents a semantic chunk of a document with attributes: chunk_id (UUID), doc_id (FK to Document), content (text), embedding (768-dim vector), section (heading/path), position (offset in document), token_count

- **Service**: Represents a software service/application with attributes: name (unique), description, image (Docker image or binary path), version, metadata (JSON for arbitrary properties)

- **Host**: Represents a physical or virtual machine with attributes: hostname (unique), ip_addresses (array), os, location, metadata (JSON)

- **IP**: Represents an IP address with attributes: addr (unique, dotted notation or CIDR), ip_type (v4, v6), allocation (static, DHCP), metadata (JSON)

- **Proxy**: Represents a reverse proxy or gateway with attributes: name (unique), proxy_type (nginx, traefik, haproxy, swag), config_path, metadata (JSON)

- **Endpoint**: Represents an HTTP/API endpoint with attributes: service (FK to Service), method (GET, POST, etc.), path (URL path pattern), auth (authentication method), rate_limit, metadata (JSON). Composite unique index on (service, method, path)

- **ExtractionWindow**: Represents a micro-window processed by Tier C with attributes: window_id (UUID), doc_id (FK to Document), content (text, ≤512 tokens), tier (A, B, C), triples_generated (count), llm_latency_ms, cache_hit (boolean), processed_at (timestamp)

- **Triple**: Represents an extracted knowledge triple with attributes: subject (entity name/ID), predicate (relationship type), object (entity name/ID), source_window_id (FK to ExtractionWindow), confidence (0-1), extraction_version (extractor version)

- **IngestionJob**: Represents an ingestion task with attributes: job_id (UUID), source_type, source_target (URL, repo name, etc.), state (pending, running, completed, failed), created_at, started_at, completed_at, pages_processed, chunks_created, errors (JSON array)

- **ExtractionJob**: Represents an extraction task with attributes: job_id (UUID), doc_id (FK to Document), state (pending, tier_a_done, tier_b_done, tier_c_done, completed, failed), tier_a_triples, tier_b_windows, tier_c_triples, started_at, completed_at, retry_count

### Relationships (Neo4j Graph Model)

- **DEPENDS_ON**: Service → Service (captures service dependencies, e.g., "api-service DEPENDS_ON postgres")
- **ROUTES_TO**: Proxy → Service (captures reverse proxy routing with properties: host, path, tls)
- **BINDS**: Service → Port (captures port bindings with properties: port, protocol (tcp/udp))
- **RUNS**: Host → Service (captures which host runs which service with properties: container_id, pid)
- **EXPOSES_ENDPOINT**: Service → Endpoint (captures service endpoints with properties: auth method, rate_limit)
- **MENTIONS**: Chunk → Entity (captures entity mentions in documents with properties: span (text snippet), section (heading), hash (content hash))
- **LOCATED_AT**: Host → IP (captures host IP assignments)
- **CONNECTS_TO**: Service → Host (captures service network connections with properties: port, protocol)

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can ingest a 20-page documentation site in under 60 seconds (end-to-end: crawling through storage)
- **SC-002**: Users can query the knowledge base and receive answers with citations in under 5 seconds for 90% of queries
- **SC-003**: Deterministic extraction pipeline processes at least 50 pages per second
- **SC-004**: NLP-based entity extraction processes at least 200 sentences per second
- **SC-005**: LLM-assisted extraction achieves median latency ≤250ms per text window and p95 ≤750ms
- **SC-006**: Graph database writes achieve throughput of at least 20,000 relationships per minute
- **SC-007**: Vector database upserts achieve throughput of at least 5,000 embeddings per second
- **SC-008**: Prompt caching achieves hit rate ≥60% during typical extraction workloads
- **SC-009**: Extraction quality (F1 score on labeled validation set of ~300 text windows) remains ≥0.85 without regression
- **SC-010**: System handles at least 10,000 document chunks with sub-second search response times
- **SC-011**: Users can discover multi-hop relationships (e.g., "service A → proxy → service B → database") in under 3 seconds
- **SC-012**: System initialization completes successfully on fresh deployment within 5 minutes including all required downloads
- **SC-013**: Reprocessing of 1,000 documents with updated extraction logic completes within 1 hour
- **SC-014**: System reports accurate job progress (pages processed, estimated time) with updates at least every 10 seconds during active work
- **SC-015**: Zero data loss during ingestion failures - all failed jobs are logged with retry information for recovery
- **SC-016**: All production code is developed using TDD with ≥85% test coverage maintained across packages (core, adapters, apps)

