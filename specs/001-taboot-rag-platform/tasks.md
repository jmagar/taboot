# Implementation Tasks: Taboot Doc-to-Graph RAG Platform

**Branch**: `001-taboot-rag-platform`
**Created**: 2025-10-21
**Total Tasks**: 83

## Summary

This task list implements the Taboot Doc-to-Graph RAG platform using TDD methodology (RED-GREEN-REFACTOR). All tasks follow the checklist format with Task IDs, parallel markers [P], and story labels [USx]. Tasks are organized by user story to enable independent implementation and testing.

**Key Points**:
- Follow TDD: Write failing test (RED) → Min code to pass (GREEN) → Refactor
- Use `[P]` marker for parallelizable tasks (different files, no dependencies)
- Each user story phase is independently testable
- MVP Scope: US4 (init) + US1 (web ingest) + US2 (extraction) + US3 (query)

---

## Phase 1: Setup (Project Initialization)

**Goal**: Establish project structure, configurations, and shared utilities following constitution requirements.

### Tasks

- [X] T001 Create package structure per plan.md (apps/, packages/, tests/)
- [X] T002 Configure pyproject.toml with uv dependencies (LlamaIndex, Neo4j driver, Qdrant client, spaCy, FastAPI, Typer, pytest)
- [X] T003 Configure .env.example with all required service URLs and credentials
- [X] T004 Configure pytest markers in pyproject.toml (unit, integration, slow, source-specific)
- [X] T005 Create packages/common/config.py with environment variable loading using pydantic-settings
- [X] T006 Create packages/common/logging.py with JSON structured logging using python-json-logger
- [X] T007 Create packages/common/tracing.py with correlation ID tracking utilities
- [X] T008 Create packages/schemas/models.py with Pydantic base models for all entities from data-model.md
- [X] T009 Create tests/conftest.py with shared fixtures (mock services, test database configs)

**Completion Criteria**: All packages exist, configs load, logging works, `uv sync` succeeds.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Implement core infrastructure needed by all user stories before parallel implementation begins.

### Tasks

- [X] T010 [P] Create packages/graph/client.py with Neo4j driver connection pooling
- [X] T011 [P] Create packages/vector/client.py with Qdrant client and collection management
- [X] T012 [P] Create packages/common/health.py with service health check utilities
- [X] T013 Write unit test for Neo4j client connection in tests/packages/graph/test_neo4j_client.py
- [X] T014 Implement Neo4j client to pass test T013
- [X] T015 Write unit test for Qdrant client connection in tests/packages/vector/test_qdrant_client.py
- [X] T016 Implement Qdrant client to pass test T015
- [X] T017 Write unit test for health checks in tests/packages/common/test_health.py
- [X] T018 Implement health check utilities to pass test T017

**Completion Criteria**: Neo4j, Qdrant, health check clients all have passing tests, coverage ≥85%.

---

## Phase 3: User Story 4 - Initialize System Schema (P1)

**Goal**: Create Neo4j constraints, Qdrant collections, PostgreSQL tables, verify service health.

**Independent Test**: Run `uv run apps/cli init` and verify all schemas created, services healthy.

### Tasks

- [X] T019 [US4] Write test for Neo4j constraint creation in tests/packages/graph/test_constraints.py
- [X] T020 [US4] Create packages/graph/constraints.py to load and execute contracts/neo4j-constraints.cypher
- [X] T021 [US4] Write test for Qdrant collection creation in tests/packages/vector/test_collections.py
- [X] T022 [US4] Create packages/vector/collections.py to load and execute contracts/qdrant-collection.json
- [X] T023 [US4] Write test for PostgreSQL schema creation in tests/packages/common/test_db_schema.py
- [X] T024 [US4] Create packages/common/db_schema.py to execute contracts/postgresql-schema.sql
- [X] T025 [US4] Write test for init CLI command in tests/apps/cli/test_init.py
- [X] T026 [US4] Create apps/cli/commands/init.py implementing taboot init workflow
- [X] T027 [US4] Write integration test for full init workflow in tests/integration/test_init_e2e.py
- [X] T028 [US4] Create apps/api/routes/init.py implementing POST /init endpoint
- [X] T029 [US4] Write API test for /init endpoint in tests/apps/api/test_init_route.py

**Completion Criteria**: `uv run apps/cli init` succeeds, all constraints/collections/tables created, services healthy, tests pass.

---

## Phase 4: User Story 1 - Ingest Web Documentation (P1)

**Goal**: Crawl web pages, normalize, chunk, embed, store in Qdrant.

**Independent Test**: Run `uv run apps/cli ingest web https://example.com --limit 5` and verify chunks stored in Qdrant.

### Tasks

#### Ingestion Models & Core Logic

- [X] T030 [P] [US1] Write test for Document model validation in tests/packages/schemas/test_document.py
- [X] T031 [P] [US1] Implement Document Pydantic model in packages/schemas/models.py per data-model.md
- [X] T032 [P] [US1] Write test for Chunk model validation in tests/packages/schemas/test_chunk.py
- [X] T033 [P] [US1] Implement Chunk Pydantic model in packages/schemas/models.py per data-model.md
- [X] T034 [P] [US1] Write test for IngestionJob model in tests/packages/schemas/test_ingestion_job.py
- [X] T035 [P] [US1] Implement IngestionJob Pydantic model in packages/schemas/models.py per data-model.md

#### Web Reader

- [X] T036 [US1] Write test for WebReader in tests/packages/ingest/readers/test_web_reader.py
- [X] T037 [US1] Create packages/ingest/readers/web.py implementing Firecrawl-based web crawling using LlamaIndex SimpleWebPageReader
- [X] T038 [US1] Refactor WebReader: add error handling, rate limiting, robots.txt compliance

#### Normalizer

- [X] T039 [P] [US1] Write test for normalizer in tests/packages/ingest/test_normalizer.py
- [X] T040 [P] [US1] Create packages/ingest/normalizer.py implementing HTML-to-Markdown conversion and boilerplate removal using readability/justext

#### Chunker

- [X] T041 [P] [US1] Write test for chunker in tests/packages/ingest/test_chunker.py
- [X] T042 [P] [US1] Create packages/ingest/chunker.py implementing semantic chunking using LlamaIndex SentenceSplitter (512 tokens, 10% overlap)

#### Embedder

- [X] T043 [P] [US1] Write test for embedder in tests/packages/ingest/test_embedder.py
- [X] T044 [P] [US1] Create packages/ingest/embedder.py implementing TEI client for batch embedding (Qwen3-Embedding-0.6B, 768-dim)

#### Qdrant Writer

- [X] T045 [US1] Write test for Qdrant upsert in tests/packages/vector/test_writer.py
- [X] T046 [US1] Create packages/vector/writer.py implementing batched Qdrant upserts with metadata

#### Ingestion Orchestration

- [X] T047 [US1] Write test for ingestion orchestrator in tests/packages/core/use_cases/test_ingest_web.py
- [X] T048 [US1] Create packages/core/use_cases/ingest_web.py orchestrating: reader → normalizer → chunker → embedder → Qdrant writer
- [X] T049 [US1] Write test for ingestion job tracking in tests/packages/core/domain/test_ingestion_job.py
- [X] T050 [US1] Implement ingestion job state management in packages/core/domain/ingestion_job.py (pending → running → completed/failed)

#### CLI & API

- [X] T051 [US1] Write test for CLI ingest web command in tests/apps/cli/test_ingest_web.py
- [X] T052 [US1] Create apps/cli/commands/ingest_web.py implementing `taboot ingest web URL --limit N`
- [X] T053 [US1] Write test for POST /ingest endpoint in tests/apps/api/test_ingest_route.py
- [X] T054 [US1] Create apps/api/routes/ingest.py implementing POST /ingest and GET /ingest/{job_id}

#### Integration Test

- [X] T055 [US1] Write end-to-end integration test for web ingestion in tests/integration/test_ingest_web_e2e.py

**Completion Criteria**: `uv run apps/cli ingest web https://example.com --limit 5` completes in <60s, chunks in Qdrant, job status tracked, tests pass ≥85% coverage.

---

## Phase 5: User Story 2 - Extract Graph Knowledge (P1)

**Goal**: Process documents with multi-tier extraction (Tier A/B/C), write triples to Neo4j.

**Independent Test**: Run `uv run apps/cli extract pending` and verify Neo4j has nodes/relationships from extracted documents.

### Tasks

#### Extraction Models

- [X] T056 [P] [US2] Write test for ExtractionWindow model in tests/packages/schemas/test_extraction_window.py
- [X] T057 [P] [US2] Implement ExtractionWindow Pydantic model in packages/schemas/models.py per data-model.md
- [X] T058 [P] [US2] Write test for ExtractionJob model in tests/packages/schemas/test_extraction_job.py
- [X] T059 [P] [US2] Implement ExtractionJob Pydantic model in packages/schemas/models.py per data-model.md

#### Graph Node Models (Neo4j)

- [X] T060 [P] [US2] Write tests for graph node models (Service, Host, IP, Proxy, Endpoint) in tests/packages/schemas/test_graph_nodes.py
- [X] T061 [P] [US2] Implement graph node Pydantic models in packages/schemas/models.py per data-model.md

#### Tier A: Deterministic Extraction

- [X] T062 [P] [US2] Write test for Tier A code block parser in tests/packages/extraction/tier_a/test_parsers.py
- [X] T063 [P] [US2] Create packages/extraction/tier_a/parsers.py implementing fenced code block, table, YAML/JSON parsing
- [X] T064 [P] [US2] Write test for Tier A entity patterns in tests/packages/extraction/tier_a/test_patterns.py
- [X] T065 [P] [US2] Create packages/extraction/tier_a/patterns.py implementing Aho-Corasick automaton for known entities (services, IPs, ports)

#### Tier B: spaCy NLP Extraction

- [X] T066 [P] [US2] Write test for Tier B entity ruler in tests/packages/extraction/tier_b/test_entity_ruler.py
- [X] T067 [P] [US2] Create packages/extraction/tier_b/entity_ruler.py implementing spaCy entity patterns for Service, Host, IP, Port using en_core_web_md
- [X] T068 [P] [US2] Write test for Tier B dependency matcher in tests/packages/extraction/tier_b/test_dependency_matcher.py
- [X] T069 [P] [US2] Create packages/extraction/tier_b/dependency_matcher.py implementing spaCy dependency patterns for DEPENDS_ON, ROUTES_TO relationships
- [X] T070 [P] [US2] Write test for Tier B window selector in tests/packages/extraction/tier_b/test_window_selector.py
- [X] T071 [P] [US2] Create packages/extraction/tier_b/window_selector.py implementing sentence classifier to select micro-windows (≤512 tokens) for Tier C

#### Tier C: LLM Window Extraction

- [X] T072 [P] [US2] Write test for Tier C LLM client in tests/packages/extraction/tier_c/test_llm_client.py
- [X] T073 [P] [US2] Create packages/extraction/tier_c/llm_client.py implementing Ollama client with batching (8-16 windows), Redis caching (SHA-256 hash), temperature 0
- [X] T074 [P] [US2] Write test for Tier C JSON schema validation in tests/packages/extraction/tier_c/test_schema.py
- [X] T075 [P] [US2] Create packages/extraction/tier_c/schema.py implementing Pydantic schemas for triple validation (subject, predicate, object)

#### Neo4j Graph Writers

- [X] T076 [US2] Write test for Cypher query builders in tests/packages/graph/test_cypher_builders.py
- [X] T077 [US2] Create packages/graph/cypher/builders.py implementing parameterized Cypher builders for MERGE operations
- [X] T078 [US2] Write test for batched Neo4j writer in tests/packages/graph/test_writers.py
- [X] T079 [US2] Create packages/graph/writers.py implementing batched UNWIND operations (2k-row batches, ≥20k edges/min throughput)

#### Extraction Orchestration

- [X] T080 [US2] Write test for extraction orchestrator in tests/packages/extraction/test_orchestrator.py
- [X] T081 [US2] Create packages/extraction/orchestrator.py coordinating Tier A → B → C execution, tracking state in Redis (ExtractionJob states: pending → tier_a_done → tier_b_done → tier_c_done → completed/failed)
- [X] T082 [US2] Write test for extraction use-case in tests/packages/core/use_cases/test_extract_pending.py
- [X] T083 [US2] Create packages/core/use_cases/extract_pending.py orchestrating extraction workflow for pending documents

#### CLI & API

- [X] T084 [US2] Write test for CLI extract pending command in tests/apps/cli/test_extract_pending.py
- [X] T085 [US2] Create apps/cli/commands/extract_pending.py implementing `taboot extract pending`
- [X] T086 [US2] Write test for POST /extract/pending endpoint in tests/apps/api/test_extract_route.py
- [X] T087 [US2] Create apps/api/routes/extract.py implementing POST /extract/pending and GET /extract/status

#### Integration Test

- [X] T088 [US2] Write end-to-end integration test for extraction pipeline in tests/integration/test_extract_e2e.py

**Completion Criteria**: `uv run apps/cli extract pending` processes documents, Neo4j has nodes/relationships, Tier A ≥50 pages/sec, Tier B ≥200 sent/sec, Tier C ≤250ms median, tests pass ≥85% coverage.

---

## Phase 6: User Story 3 - Query with Hybrid Retrieval (P1)

**Goal**: Execute natural language queries with vector search, reranking, graph traversal, answer synthesis.

**Independent Test**: Run `uv run apps/cli query "test question"` and verify answer with citations returned in <5s.

### Tasks

#### Retrieval Context & Settings

- [X] T089 [P] [US3] Write test for retrieval settings in tests/packages/retrieval/context/test_settings.py
- [X] T090 [P] [US3] Create packages/retrieval/context/settings.py configuring TEI embeddings and Ollama LLM (Qwen3-4B)
- [X] T091 [P] [US3] Write test for custom prompts in tests/packages/retrieval/context/test_prompts.py
- [X] T092 [P] [US3] Create packages/retrieval/context/prompts.py with TextQAPromptTemplate for inline citation format ([1], [2] with source list)

#### Vector Search & Reranking

- [X] T093 [P] [US3] Write test for vector search in tests/packages/vector/test_search.py
- [X] T094 [P] [US3] Create packages/vector/search.py implementing Qdrant vector search with metadata filters (--sources, --after, top-k)
- [X] T095 [P] [US3] Write test for reranker in tests/packages/vector/test_reranker.py
- [X] T096 [P] [US3] Create packages/vector/reranker.py implementing Qwen3-Reranker-0.6B via SentenceTransformers (batch_size=16, GPU, top-20 → top-5)

#### Graph Traversal

- [X] T097 [P] [US3] Write test for graph traversal in tests/packages/graph/test_traversal.py
- [X] T098 [P] [US3] Create packages/graph/traversal.py implementing Neo4j graph traversal (≤2 hops, prioritize DEPENDS_ON > ROUTES_TO > BINDS)

#### LlamaIndex Indices

- [X] T099 [P] [US3] Write test for VectorStoreIndex in tests/packages/retrieval/indices/test_vector.py
- [X] T100 [P] [US3] Create packages/retrieval/indices/vector.py implementing LlamaIndex VectorStoreIndex over Qdrant
- [X] T101 [P] [US3] Write test for PropertyGraphIndex in tests/packages/retrieval/indices/test_graph.py
- [X] T102 [P] [US3] Create packages/retrieval/indices/graph.py implementing LlamaIndex PropertyGraphIndex over Neo4j

#### Hybrid Retriever & Query Engine

- [X] T103 [US3] Write test for hybrid retriever in tests/packages/retrieval/retrievers/test_hybrid.py
- [X] T104 [US3] Create packages/retrieval/retrievers/hybrid.py implementing custom retriever combining vector search + graph traversal
- [X] T105 [US3] Write test for query engine in tests/packages/retrieval/query_engines/test_qa.py
- [X] T106 [US3] Create packages/retrieval/query_engines/qa.py implementing RetrieverQueryEngine with reranking, citation formatting, latency tracking

#### Query Orchestration

- [X] T107 [US3] Write test for query use-case in tests/packages/core/use_cases/test_query.py
- [X] T108 [US3] Create packages/core/use_cases/query.py orchestrating: embed query → vector search → rerank → graph traversal → synthesize answer

#### CLI & API

- [X] T109 [US3] Write test for CLI query command in tests/apps/cli/test_query.py
- [X] T110 [US3] Create apps/cli/commands/query.py implementing `taboot query "question" --sources X,Y --after DATE --top-k N`
- [X] T111 [US3] Write test for POST /query endpoint in tests/apps/api/test_query_route.py
- [X] T112 [US3] Create apps/api/routes/query.py implementing POST /query

#### Integration Test

- [X] T113 [US3] Write end-to-end integration test for query workflow in tests/integration/test_query_e2e.py

**Completion Criteria**: `uv run apps/cli query "test question"` returns answer with citations in <5s median, latency breakdown logged, tests pass ≥85% coverage.

---

## Phase 7: User Story 5 - Ingest Structured Sources (P2)

**Goal**: Ingest Docker Compose, SWAG configs, Tailscale, Unifi data directly into graph.

**Independent Test**: Run `uv run apps/cli ingest docker-compose ./docker-compose.yml` and verify services/dependencies in Neo4j.

**Dependencies**: Requires US1 (ingestion framework) and US2 (graph writers).

### Tasks

#### Docker Compose Parser

- [X] T114 [P] [US5] Write test for Docker Compose parser in tests/packages/ingest/readers/test_docker_compose.py
- [X] T115 [P] [US5] Create packages/ingest/readers/docker_compose.py implementing YAML parsing, Service/DEPENDS_ON/BINDS extraction

#### SWAG Config Parser

- [X] T116 [P] [US5] Write test for SWAG parser in tests/packages/ingest/readers/test_swag.py
- [X] T117 [P] [US5] Create packages/ingest/readers/swag.py implementing nginx config parsing, Proxy/ROUTES_TO extraction

#### Tailscale Network Parser

- [X] T118 [P] [US5] Write test for Tailscale parser in tests/packages/ingest/readers/test_tailscale.py
- [X] T119 [P] [US5] Create packages/ingest/readers/tailscale.py implementing Tailscale API client, Host/IP/LOCATED_AT extraction

#### Unifi Controller Parser

- [X] T120 [P] [US5] Write test for Unifi parser in tests/packages/ingest/readers/test_unifi.py
- [X] T121 [P] [US5] Create packages/ingest/readers/unifi.py implementing Unifi API client, network topology extraction

#### CLI Commands

- [X] T122 [US5] Write test for CLI docker-compose command in tests/apps/cli/test_cli_ingest_docker_compose.py
- [X] T123 [US5] Create apps/cli/commands/ingest_docker_compose.py implementing `taboot ingest docker-compose FILE`
- [X] T124 [US5] Write test for CLI swag command in tests/apps/cli/test_cli_ingest_swag.py
- [X] T125 [US5] Create apps/cli/commands/ingest_swag.py implementing `taboot ingest swag PATH`

#### Integration Test

- [X] T126 [US5] Write end-to-end integration test for structured source ingestion in tests/integration/test_ingest_structured_e2e.py

**Completion Criteria**: Structured sources ingest successfully, graph contains accurate topology, tests pass.

---

## Phase 8: User Story 6 - Monitor Extraction Pipeline (P2)

**Goal**: Expose extraction metrics (throughput, latency, cache hit rate) via CLI and API.

**Independent Test**: Run `uv run apps/cli extract status` and verify metrics displayed.

**Dependencies**: Requires US2 (extraction pipeline) to generate metrics.

### Tasks

#### Metrics Collection

- [X] T127 [P] [US6] Write test for metrics collector in tests/packages/common/test_metrics.py
- [X] T128 [P] [US6] Create packages/common/metrics.py implementing metrics tracking (windows/sec, tier hit ratios, LLM p95, cache hit rate, DB throughput)

#### Status Reporting

- [X] T129 [US6] Write test for status use-case in tests/packages/core/use_cases/test_get_status.py
- [X] T130 [US6] Create packages/core/use_cases/get_status.py implementing status aggregation (service health, queue depth, metrics)

#### CLI & API

- [X] T131 [US6] Write test for CLI extract status command in tests/apps/cli/test_extract_status.py
- [X] T132 [US6] Create apps/cli/commands/extract_status.py implementing `taboot extract status`
- [X] T133 [US6] Write test for GET /extract/status endpoint in tests/apps/api/test_extract_status_route.py
- [X] T134 [US6] Update apps/api/routes/extract.py to implement GET /extract/status
- [X] T135 [US6] Write test for GET /status endpoint in tests/apps/api/test_status_route.py
- [X] T136 [US6] Create apps/api/routes/status.py implementing GET /status

#### Integration Test

- [X] T137 [US6] Write integration test for metrics reporting in tests/integration/test_metrics_e2e.py

**Completion Criteria**: Metrics reported accurately, CLI and API endpoints functional, tests pass.

---

## Phase 9: User Story 7 - Ingest External APIs (P3)

**Goal**: Ingest from GitHub, Reddit, YouTube, Gmail, Elasticsearch.

**Independent Test**: Run `uv run apps/cli ingest github owner/repo --limit 10` and verify data ingested.

**Dependencies**: Requires US1 (ingestion framework).

### Tasks

#### GitHub Reader

- [X] T138 [P] [US7] Write test for GitHub reader in tests/packages/ingest/readers/test_github.py
- [X] T139 [P] [US7] Create packages/ingest/readers/github.py implementing LlamaIndex GithubRepositoryReader wrapper (README, wiki, issues)

#### Reddit Reader

- [X] T140 [P] [US7] Write test for Reddit reader in tests/packages/ingest/readers/test_reddit.py
- [X] T141 [P] [US7] Create packages/ingest/readers/reddit.py implementing LlamaIndex RedditReader wrapper (posts + comments)

#### YouTube Reader

- [X] T142 [P] [US7] Write test for YouTube reader in tests/packages/ingest/readers/test_youtube.py
- [X] T143 [P] [US7] Create packages/ingest/readers/youtube.py implementing LlamaIndex YoutubeTranscriptReader wrapper

#### Gmail Reader

- [X] T144 [P] [US7] Write test for Gmail reader in tests/packages/ingest/readers/test_gmail.py
- [X] T145 [P] [US7] Create packages/ingest/readers/gmail.py implementing LlamaIndex GmailReader wrapper (OAuth credentials)

#### Elasticsearch Reader

- [X] T146 [P] [US7] Write test for Elasticsearch reader in tests/packages/ingest/readers/test_elasticsearch.py
- [X] T147 [P] [US7] Create packages/ingest/readers/elasticsearch.py implementing LlamaIndex ElasticsearchReader wrapper

#### CLI Commands

- [X] T148 [US7] Write test for CLI github command in tests/apps/cli/test_ingest_github.py
- [X] T149 [US7] Create apps/cli/commands/ingest_github.py implementing `taboot ingest github REPO --limit N`
- [X] T150 [US7] Repeat for reddit, youtube, gmail, elasticsearch CLI commands (5 tasks total: T150-T154)

#### Integration Test

- [X] T155 [US7] Write end-to-end integration test for external API ingestion in tests/integration/test_ingest_apis_e2e.py

**Completion Criteria**: External sources ingest successfully, API credentials configured, tests pass.

---

## Phase 10: User Story 8 - Reprocess Documents (P3)

**Goal**: Re-extract documents with updated extractors.

**Independent Test**: Run `uv run apps/cli extract reprocess --since 7d` and verify documents re-extracted.

**Dependencies**: Requires US2 (extraction pipeline).

### Tasks

#### Reprocessing Logic

- [X] T156 [US8] Write test for reprocess use-case in tests/packages/core/use_cases/test_reprocess.py
- [X] T157 [US8] Create packages/core/use_cases/reprocess.py implementing date filtering, queuing documents for re-extraction

#### CLI & API

- [X] T158 [US8] Write test for CLI reprocess command in tests/apps/cli/test_extract_reprocess.py
- [X] T159 [US8] Create apps/cli/commands/extract_reprocess.py implementing `taboot extract reprocess --since DATE`
- [X] T160 [US8] Write test for POST /extract/reprocess endpoint in tests/apps/api/test_reprocess_route.py
- [X] T161 [US8] Update apps/api/routes/extract.py to implement POST /extract/reprocess

#### Integration Test

- [X] T162 [US8] Write integration test for reprocessing workflow in tests/integration/test_reprocess_e2e.py

**Completion Criteria**: Reprocessing queues documents correctly, extraction updates graph, tests pass.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Goal**: Add list documents CLI/API, improve error handling, optimize performance.

### Tasks

#### List Documents

- [X] T163 [P] Write test for list documents use-case in tests/packages/core/use_cases/test_list_documents.py
- [X] T164 [P] Create packages/core/use_cases/list_documents.py implementing pagination, filtering by source_type/extraction_state
- [X] T165 Write test for CLI list documents command in tests/apps/cli/test_list_documents.py
- [X] T166 Create apps/cli/commands/list_documents.py implementing `taboot list documents --limit N --source-type X`
- [X] T167 Write test for GET /documents endpoint in tests/apps/api/test_documents_route.py
- [X] T168 Create apps/api/routes/documents.py implementing GET /documents

#### Background Worker

- [X] T169 Write test for extraction worker in tests/apps/worker/test_main.py
- [X] T170 Create apps/worker/main.py implementing background extraction worker (polls Redis queue, processes documents)

#### Error Handling & DLQ

- [X] T171 [P] Write test for Dead Letter Queue in tests/packages/common/test_dlq.py
- [X] T172 [P] Create packages/common/dlq.py implementing Redis DLQ with retry policy (max 3 retries, exponential backoff)

#### Performance Optimization

- [X] T173 [P] Create docs/PERFORMANCE_TUNING.md with Tier C batch size tuning guidance (8-16 windows)
- [X] T174 [P] Document Neo4j write batch size optimization (2k-4k rows based on heap size)
- [X] T175 [P] Document Qdrant upsert batch size tuning (50-500 vectors based on network latency)

#### Documentation

- [X] T176 Update README.md with quickstart examples from quickstart.md
- [X] T177 docs/TESTING.md already comprehensive with TDD workflow, test markers, coverage targets
- [X] T178 Update CHANGELOG.md with v1.0.0 release notes

**Completion Criteria**: All polish tasks complete, performance targets met, documentation updated.

---

## Dependencies & Execution Order

### User Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational)
                      ↓
        ┌─────────────┴─────────────┬─────────────┐
        ↓                           ↓             ↓
    Phase 3 (US4: Init)     Phase 4 (US1: Web)   Phase 5 (US2: Extract)
        ↓                           ↓             ↓
        └─────────────┬─────────────┴─────────────┘
                      ↓
              Phase 6 (US3: Query)
                      ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
    Phase 7 (US5: Structured)   Phase 8 (US6: Monitor)
        ↓                           ↓
        └─────────────┬─────────────┘
                      ↓
        ┌─────────────┴─────────────┐
        ↓                           ↓
    Phase 9 (US7: External)     Phase 10 (US8: Reprocess)
        ↓                           ↓
        └─────────────┬─────────────┘
                      ↓
              Phase 11 (Polish)
```

### Independent User Stories (Can Execute in Parallel After Foundational)

- **US4 (Init)**: No dependencies on other stories after Foundational
- **US1 (Web Ingest)**: No dependencies on other stories after Foundational
- **US2 (Extract)**: No dependencies on other stories after Foundational
- **US3 (Query)**: No dependencies on other stories after Foundational

**These 4 stories (US4, US1, US2, US3) can be implemented in parallel after Phase 2 completes.**

### Dependent User Stories

- **US5 (Structured)**: Requires US1 (ingestion framework) and US2 (graph writers)
- **US6 (Monitor)**: Requires US2 (extraction pipeline)
- **US7 (External APIs)**: Requires US1 (ingestion framework)
- **US8 (Reprocess)**: Requires US2 (extraction pipeline)

---

## Parallel Execution Examples

### After Phase 2 (Foundational)

**Engineer A**: Implements US4 (Initialize System) - T019-T029
**Engineer B**: Implements US1 (Ingest Web) - T030-T055
**Engineer C**: Implements US2 (Extract Graph) - T056-T088
**Engineer D**: Implements US3 (Query) - T089-T113

All 4 engineers work independently, then integrate.

### Within User Story 1 (Ingest Web)

**Parallel Tasks** (different files, no dependencies):
- T030-T031 (Document model) [P]
- T032-T033 (Chunk model) [P]
- T034-T035 (IngestionJob model) [P]
- T039-T040 (Normalizer) [P]
- T041-T042 (Chunker) [P]
- T043-T044 (Embedder) [P]

**Sequential Tasks** (dependencies):
- T036-T038 (WebReader) must complete before T047-T050 (Orchestrator)
- T045-T046 (Qdrant Writer) must complete before T047-T050 (Orchestrator)

### Within User Story 2 (Extract Graph)

**Parallel Tasks**:
- T062-T065 (Tier A) [P]
- T066-T071 (Tier B) [P]
- T072-T075 (Tier C) [P]
- T060-T061 (Graph node models) [P]

**Sequential Tasks**:
- T076-T079 (Neo4j writers) must complete before T080-T083 (Orchestrator)

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

Focus on delivering end-to-end value quickly:

**Phase 1 → Phase 2 → US4 (Init) + US1 (Web Ingest) + US2 (Extract) + US3 (Query)**

This provides:
- ✅ System initialization
- ✅ Web documentation ingestion
- ✅ Knowledge graph extraction
- ✅ Natural language querying

**Estimated: ~120 tasks (T001-T113 + Phase 11 polish)**

### Incremental Delivery

After MVP:
1. **US5 (Structured Sources)** - Docker Compose, SWAG (DevOps use case)
2. **US6 (Monitoring)** - Observability (operational visibility)
3. **US7 (External APIs)** - GitHub, Reddit, etc. (broader knowledge base)
4. **US8 (Reprocessing)** - Continuous improvement (extractor versioning)

### Testing Strategy

**Per User Story**:
1. Write failing tests (RED)
2. Implement minimum code (GREEN)
3. Refactor for quality (REFACTOR)
4. Run story-specific integration test
5. Verify independent test criteria

**Coverage Targets**:
- `packages/core/`: ≥85%
- `packages/extraction/`: ≥85%
- `packages/ingest/`: ≥80%
- `packages/retrieval/`: ≥80%
- `apps/`: ≥70%

---

## Task Validation Summary

**Total Tasks**: 178
**Tasks Per User Story**:
- Setup (Phase 1): 9 tasks
- Foundational (Phase 2): 9 tasks
- US4 (Initialize): 11 tasks
- US1 (Web Ingest): 26 tasks
- US2 (Extract Graph): 33 tasks
- US3 (Query): 25 tasks
- US5 (Structured): 13 tasks
- US6 (Monitor): 11 tasks
- US7 (External APIs): 18 tasks
- US8 (Reprocess): 7 tasks
- Polish (Phase 11): 16 tasks

**Parallel Opportunities**: 57 tasks marked [P] (32% parallelizable)

**Format Compliance**: ✅ All tasks follow checklist format with Task ID, optional [P] marker, story labels [USx], and file paths.

**Independent Test Criteria**: ✅ Each user story phase has clear test criteria defined.

**MVP Suggestion**: Phases 1-6 (US4 + US1 + US2 + US3) = ~120 tasks for complete end-to-end platform.
