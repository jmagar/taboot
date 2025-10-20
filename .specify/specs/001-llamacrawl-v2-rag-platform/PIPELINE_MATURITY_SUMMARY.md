# LlamaCrawl v2 — Pipeline Maturity Summary

## At a Glance

**Status:** Skeleton Phase (5% Implementation)  
**Architecture:** Fully Designed (100%)  
**Docker Infrastructure:** Ready (95%)  
**Code Implementation:** Missing (0%)

---

## Maturity by Component

```
┌─────────────────────────────────────────────────────────────────┐
│ ARCHITECTURE & DESIGN                                    ██████ │ 100%
├─────────────────────────────────────────────────────────────────┤
│ Docker Compose Infrastructure                            █████  │ 95%
├─────────────────────────────────────────────────────────────────┤
│ Specification & Documentation                            ████░░ │ 85%
├─────────────────────────────────────────────────────────────────┤
│ API Routes Implementation                                ░░░░░░ │ 0%
│   └─ (21 LOC stub: /health, / only)                             │
├─────────────────────────────────────────────────────────────────┤
│ CLI Commands                                             ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ Core Domain Models & Ports                               ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ INGESTION PLANE                                          ░░░░░░ │ 0%
│   ├─ Normalizer                                          ░░░░░░ │ 0%
│   ├─ Chunker                                             ░░░░░░ │ 0%
│   └─ Source Adapters (11 sources)                        ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ EXTRACTION PLANE                                         ░░░░░░ │ 0%
│   ├─ Tier A (Deterministic)                              ░░░░░░ │ 0%
│   ├─ Tier B (spaCy NLP)                                  ░░░░░░ │ 0%
│   ├─ Tier C (LLM Windows)                                ░░░░░░ │ 0%
│   └─ Orchestration & Queue                               ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ Neo4j Adapter                                            ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ Qdrant Adapter                                           ░░░░░░ │ 0%
├─────────────────────────────────────────────────────────────────┤
│ Test Suite                                               ░░░░░░ │ 0%
└─────────────────────────────────────────────────────────────────┘
```

---

## Production Code Status

| Layer | Component | Status | Code | Blockers |
|-------|-----------|--------|------|----------|
| **Core** | Domain models | ✗ BLOCKED | 0 LOC | Base layer required |
| **Core** | Ports/Interfaces | ✗ BLOCKED | 0 LOC | Base layer required |
| **Core** | Use-cases | ✗ BLOCKED | 0 LOC | Base layer required |
| **Ingest** | Normalizer | ✗ BLOCKED | 0 LOC | Core required |
| **Ingest** | Chunker | ✗ BLOCKED | 0 LOC | Core required |
| **Ingest** | Source adapters | ✗ BLOCKED | 0 LOC | Core required |
| **Extract** | Tier A | ✗ BLOCKED | 0 LOC | Core + Ingest required |
| **Extract** | Tier B | ✗ BLOCKED | 0 LOC | Core + Ingest required |
| **Extract** | Tier C | ✗ BLOCKED | 0 LOC | Core + Ingest required |
| **Extract** | Orchestration | ✗ BLOCKED | 0 LOC | All tiers required |
| **Graph** | Neo4j adapter | ✗ BLOCKED | 0 LOC | Core + schema required |
| **Vector** | Qdrant adapter | ✗ BLOCKED | 0 LOC | Core + schema required |
| **Retrieval** | Retrievers | ✗ BLOCKED | 0 LOC | Core + adapters required |
| **API** | Routes | ✗ PARTIAL | 21 LOC | All adapters required |
| **CLI** | Commands | ✗ BLOCKED | 0 LOC | All adapters required |
| **Tests** | Full suite | ✗ BLOCKED | 0 LOC | Core + adapters required |

---

## Pipeline Data Flow (Planned vs. Actual)

### PLANNED ARCHITECTURE

```
WEB/APIs (Firecrawl, GitHub, Reddit, etc.)
    ↓
[INGESTION PLANE] — Normalizer → Chunker → TEI Embeddings
    ↓ ↓
QDRANT       Neo4j (Doc nodes)
    ↓
[EXTRACTION PLANE] — Tier A → Tier B → Tier C
    ↓
Neo4j (Service, Host, IP, Endpoint, Relation nodes)
    ↓
[RETRIEVAL PLANE] — Vector Search → Rerank → Graph Traversal → LLM Synthesis
    ↓
ANSWERS (with citations)
```

### ACTUAL STATE

```
WEB/APIs (Firecrawl, GitHub, etc.)
    ↓
[INGESTION PLANE] ✗ NOT IMPLEMENTED
    ↓
Normalizer: ✗ EMPTY
Chunker: ✗ EMPTY
TEI Client: ✗ EMPTY
    ↓
QDRANT ✓ (service running, unused)
Neo4j ✓ (service running, no schema applied)
    ↓
[EXTRACTION PLANE] ✗ NOT IMPLEMENTED
    ↓
Tier A: ✗ EMPTY
Tier B: ✗ EMPTY
Tier C: ✗ EMPTY
Orchestration: ✗ EMPTY
    ↓
[RETRIEVAL PLANE] ✗ NOT IMPLEMENTED
```

---

## Three-Tier Extraction System

### TIER A — Deterministic Extraction

```
Status: ✗ NOT IMPLEMENTED
Target: ≥50 pages/sec
Progress: 0%

Planned:
  ├─ Regex patterns for configs
  ├─ YAML/JSON parsing
  ├─ Aho-Corasick dictionary (services, IPs, hosts)
  ├─ Table extraction
  ├─ Link graph parsing
  └─ Fenced code extraction

Blockers:
  - No regex library defined
  - No pattern dictionary created
  - No YAML/JSON parser
  - No Neo4j writer
  - Zero code
```

### TIER B — NLP Extraction (spaCy)

```
Status: ✗ NOT IMPLEMENTED
Target: ≥200 sentences/sec (md model)
Progress: 0%

Planned:
  ├─ spaCy pipeline with en_core_web_md
  ├─ Entity ruler (custom patterns)
  ├─ Dependency matcher (verb relations)
  ├─ Sentence classifier (technical filter)
  └─ Window selection

Blockers:
  - No spaCy pipeline setup
  - No entity patterns defined
  - No matchers configured
  - No model initialization
  - Zero code
```

### TIER C — LLM Window Extraction

```
Status: ✗ NOT IMPLEMENTED
Target: ≤250ms median per window
Progress: 0%

Planned:
  ├─ Ollama + Qwen3-4B-Instruct
  ├─ ≤512-token windows
  ├─ Batch 8–16 per request
  ├─ JSON schema validation
  ├─ Redis caching (SHA-256)
  └─ Temperature 0.0 decoding

Blockers:
  - No Ollama client
  - No window batching
  - No JSON validation
  - No Redis caching
  - No prompt template
  - Zero code
```

---

## Services Infrastructure (Docker Compose)

### GPU-Accelerated Services (Ready)

| Service | Status | Purpose |
|---------|--------|---------|
| `taboot-vectors` | ✓ Running | Qdrant (HNSW indexing) |
| `taboot-embed` | ✓ Running | TEI embeddings |
| `taboot-rerank` | ✓ Running | SentenceTransformers reranking |
| `taboot-ollama` | ✓ Running | Ollama LLM (Qwen3-4B) |

### Supporting Services (Ready)

| Service | Status | Purpose |
|---------|--------|---------|
| `taboot-graph` | ✓ Running | Neo4j 5.23 (no schema applied) |
| `taboot-cache` | ✓ Running | Redis 7.2 (for caching/queues) |
| `taboot-db` | ✓ Running | PostgreSQL 16 |
| `taboot-playwright` | ✓ Running | Firecrawl browser |
| `taboot-crawler` | ✓ Running | Firecrawl orchestrator |
| `taboot-app` | ✓ Running | FastAPI HTTP service |

### Disabled Services

| Service | Status | Reason |
|---------|--------|--------|
| `taboot-worker` | ✗ Disabled | Extraction pipeline not implemented |

---

## Key Files & Documentation

### Fully Specified

- `docs/ARCHITECTURE.md` — Complete platform architecture (174 lines)
- `packages/extraction/docs/EXTRACTION_SPEC.md` — Detailed tier spec (188 lines)
- `packages/ingest/README.md` — Ingest layer overview (40 lines)
- `packages/extraction/README.md` — Extraction layer overview (42 lines)
- `packages/core/README.md` — Core layer guidance (41 lines)
- `CLAUDE.md` (repo root) — Project conventions (complete)
- `specs/001-llamacrawl-v2-rag-platform/spec.md` — Feature spec (200+ lines)
- `specs/001-llamacrawl-v2-rag-platform/plan.md` — Implementation plan (150+ lines)

### Implementation Stubs

- `apps/api/app.py` — 21 LOC (2 endpoints only)
- All package directories — Empty `__init__.py` only

---

## Critical Dependencies

### Available ✓

```
firecrawl-py>=4.4.0       # Web crawling
spacy>=3.8.1              # NLP extraction
torch>=2.4.0              # Deep learning
transformers>=4.44.0      # Embedding models
llama-index-*             # RAG framework (11 packages)
neo4j>=5.26.0             # Graph database
qdrant-client>=1.15.1     # Vector database
redis>=5.0.1              # Caching/queuing
pydantic>=2.12.0          # Data validation
fastapi>=0.119.0          # HTTP framework
```

### Ready to Use ✓

- **NEO4J:** Schema defined, service running (health check passing)
- **QDRANT:** Collection schema defined, service running
- **OLLAMA:** Qwen3-4B configured, service running
- **TEI:** Embeddings service running
- **FIRECRAWL:** API configured and running
- **REDIS:** Cache ready for Tier C

---

## Implementation Dependencies (Critical Path)

```
1. Core Domain Models
   ↓
2. Core Ports/Interfaces
   ↓
3. Adapter Implementation (Ingest, Graph, Vector)
   ├─→ 4. Neo4j Batch Writer
   ├─→ 5. Qdrant Upsert Logic
   └─→ 6. Document → Neo4j flows
   
7. Ingestion Pipeline
   ├─→ Normalizer
   ├─→ Chunker  
   └─→ TEI integration
   
8. Tier A Extraction (Deterministic)
   ↓
9. Tier B Extraction (spaCy)
   ↓
10. Tier C Extraction (LLM)
    ↓
11. Extraction Orchestration
    ├─→ Redis queue
    ├─→ Tier routing
    ├─→ Entity resolution
    └─→ Batch writes
    
12. API Routes
    ↓
13. CLI Commands
    ↓
14. Test Suite
    ↓
15. Performance Tuning & Benchmarks
```

---

## Development Effort Estimate

| Phase | Component | Estimated Time | Complexity |
|-------|-----------|-----------------|-----------|
| **Phase 1** | Core + Ports | 1–2 weeks | High |
| **Phase 2** | Ingest adapters | 1–2 weeks | Medium |
| **Phase 3** | Tier A extraction | 1 week | Medium |
| **Phase 4** | Tier B extraction | 1–2 weeks | High |
| **Phase 5** | Tier C + Orchestration | 2 weeks | High |
| **Phase 6** | API + CLI | 1 week | Low |
| **Phase 7** | Tests | 1–2 weeks | Medium |
| **Phase 8** | Performance tuning | 2–3 weeks | High |
| | **TOTAL MVP** | **5–8 weeks** | — |

---

## What's Working

- Docker infrastructure (all 10 services healthy)
- FastAPI stub server
- Project structure and layering rules
- Comprehensive specification and documentation
- Dependency management (uv + pyproject.toml)
- Type checking setup (mypy strict mode)

## What's Missing

- All business logic implementation
- All adapter implementations
- Entire extraction pipeline
- Test suite
- API routes (beyond health check)
- CLI commands
- Integration glue

---

## Go/No-Go Decision Points

### Current Status: SKELETON (5% Complete)

| Gate | Status | Requirement |
|------|--------|-------------|
| Architecture reviewed | ✓ PASS | Clear, documented |
| Dependencies defined | ✓ PASS | All declared in pyproject.toml |
| Docker infrastructure | ✓ PASS | All services healthy |
| Core domain models | ✗ FAIL | **BLOCKER** — Must implement first |
| Integration tests | ✗ FAIL | Not written (0% coverage) |
| Performance targets | ✗ FAIL | Not validated under load |

### Ready for Implementation? ✓ YES

Pre-requisites met:
- Architecture is clear and well-designed
- Specification is complete
- Dependencies are available
- Docker infrastructure is ready
- No architectural unknowns remain

### Ready for Production? ✗ NO

Blockers:
- Zero production code in critical paths
- No test coverage
- No performance validation
- No monitoring/alerting
- No error handling at scale

---

## Next Immediate Actions

**Priority 1 (This Week):**
1. Implement core domain models (Document, Entity, Relation, etc.)
2. Define core ports/interfaces (IngestPort, ExtractorPort, etc.)
3. Create test fixtures and structure

**Priority 2 (Next Week):**
1. Implement Normalizer and Chunker
2. Implement basic Firecrawl adapter
3. Create integration tests for ingest flow

**Priority 3 (Week 3):**
1. Implement Tier A extraction (deterministic)
2. Implement Neo4j batch writer
3. Benchmark Tier A throughput

---

## Key Performance Targets (Pending Validation)

| Component | Target | Status |
|-----------|--------|--------|
| Tier A throughput | ≥50 pages/sec | Not measured |
| Tier B throughput | ≥200 sentences/sec | Not measured |
| Tier C latency | ≤250ms median/window | Not measured |
| Neo4j writes | ≥20k edges/min | Not measured |
| Qdrant upserts | ≥5k vectors/sec | Not measured |
| E2E retrieval | <3s p95 | Not measured |

---

**Report Generated:** 2025-10-20  
**Full Investigation:** See `PIPELINE_INVESTIGATION_REPORT.md` (24 KB, 15 sections)  
**Repository:** `/home/jmagar/code/taboot`  
**Branch:** `001-llamacrawl-v2-rag-platform`
