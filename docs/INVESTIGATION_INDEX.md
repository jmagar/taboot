# Taboot v2 Investigation — Document Index

## Overview

This directory contains comprehensive investigation reports on the data ingestion and extraction planes of the Taboot v2 Doc-to-Graph RAG platform.

**Investigation Date:** 2025-10-20  
**Branch:** 001-taboot-v2-rag-platform  
**Status:** Skeleton Phase (5% Implementation)

---

## Key Reports

### 1. PIPELINE_INVESTIGATION_REPORT.md (24 KB, 753 lines)

**Comprehensive technical investigation** covering:

- **Executive Summary:** Project status and key findings
- **Ingestion Plane Status:** Directory structure, documented intent, implementation gaps
- **Extraction Plane Status:** Tier A/B/C detailed analysis, blocker checklist
- **Neo4j Graph Schema:** Node labels, relationships, constraints (defined but not applied)
- **Docker Services:** All 11 services analyzed (10 running, 1 disabled)
- **Core Package Status:** Empty placeholders, expected content
- **API & CLI Status:** Stub vs. planned functionality
- **Test Status:** Zero coverage (0% implemented)
- **Dependencies & Build System:** All required packages declared
- **Known Blockers:** 30+ blockers organized by tier and component
- **Performance Targets:** Not yet validated
- **Documentation Quality:** Architecture 100%, implementation 85%
- **Maturity Assessment:** 5% overall (infrastructure 95%, code 0%)
- **Recommended Next Steps:** Phased implementation plan
- **Summary Table:** Current vs. Expected state (99.6% gap)
- **Conclusion:** Well-designed, completely unimplemented greenfield project

**Who should read:** Technical leads, architects, implementation team leads

**Use case:** Comprehensive understanding of pipeline state, blockers, and implementation roadmap

---

### 2. PIPELINE_MATURITY_SUMMARY.md (15 KB, 415 lines)

**Executive summary with visual progress bars** covering:

- **At a Glance:** Status badges (Skeleton, 5%, etc.)
- **Maturity by Component:** Visual progress bars for all subsystems
- **Production Code Status:** Table showing 0 LOC across adapters
- **Pipeline Data Flow:** Planned vs. Actual state comparison
- **Three-Tier Extraction System:** Status for Tier A, B, C
- **Services Infrastructure:** GPU and supporting services status
- **Key Files & Documentation:** What's specified, what's missing
- **Critical Dependencies:** All available and ready
- **Implementation Dependencies:** Critical path diagram
- **Development Effort Estimate:** 5–8 weeks for MVP
- **What's Working / What's Missing:** Summary checklist
- **Go/No-Go Decision Points:** Readiness gates
- **Next Immediate Actions:** Priority 1/2/3 tasks
- **Performance Targets:** All pending validation

**Who should read:** Project managers, team leads, stakeholders

**Use case:** Quick executive briefing on project status and timeline

---

## Key Findings

### Pipeline Maturity: 5% (Skeleton Phase)

| Component | Status | Notes |
|-----------|--------|-------|
| Architecture Design | 100% | Complete with data flow diagrams |
| Docker Infrastructure | 95% | All 11 services configured, 10 running |
| Specification | 100% | 10 user stories, acceptance criteria |
| Documentation | 85% | Architecture complete, implementation guides TBD |
| Core Code | 0% | All empty packages (`__init__.py` only) |
| Ingestion Plane | 0% | Zero functional code |
| Extraction Plane | 0% | Zero functional code (all 3 tiers) |
| Retrieval Plane | 0% | Zero functional code |
| Test Suite | 0% | No tests written |
| API Routes | 0% | Stub only (2 endpoints) |
| CLI Commands | 0% | Not implemented |

### Production Code Gap: 99.6%

```text
Expected: ~5500+ LOC
Actual:   ~21 LOC (FastAPI stub app.py only)
Gap:      99.6%
```

### Critical Blockers

1. **Tier A Extraction (Deterministic):** 9 blockers
   - No regex patterns defined
   - No Aho-Corasick setup
   - No YAML/JSON parsers
   - No Neo4j writer integration

2. **Tier B Extraction (spaCy NLP):** 7 blockers
   - No spaCy pipeline
   - No entity ruler
   - No dependency matchers
   - No sentence classifier

3. **Tier C Extraction (LLM):** 7 blockers
   - No Ollama client
   - No window batching
   - No JSON validation
   - No Redis caching

4. **Integration Blockers:** 5 blockers
   - No core domain models
   - No ports/interfaces
   - No use-cases
   - No CLI commands

---

## Implementation Roadmap

### Phase 1: Foundation (1–2 weeks)

- Implement core domain models
- Define ports/interfaces
- Create test fixtures

### Phase 2: Ingest Adapters (1–2 weeks)

- Normalizer (HTML → Markdown)
- Chunker (semantic, token-based)
- Firecrawl adapter

### Phase 3: Tier A Extraction (1 week)

- Deterministic extractors
- Neo4j batch writer
- Benchmarking (target: 50 pages/sec)

### Phase 4: Tier B Extraction (1–2 weeks)

- spaCy pipeline
- Entity ruler + matchers
- Window selection

### Phase 5: Tier C & Orchestration (2 weeks)

- LLM integration (Ollama)
- Batching & caching
- Tier routing

### Phase 6: API & CLI (1 week)

- Routes for ingestion/extraction/query
- CLI commands

### Phase 7: Tests (1–2 weeks)

- Unit + integration tests
- Target: ≥85% coverage

### Phase 8: Performance Tuning (2–3 weeks)

- Benchmark all tiers
- Validate targets
- Optimization

**Total Estimated Effort:** 5–8 weeks for MVP

---

## Architecture Highlights (Well Designed)

### Layering (Strict)

```text
apps (API, CLI, MCP)
    ↓
adapters (ingest, extraction, graph, vector, retrieval)
    ↓
core (domain models, use-cases, ports)
```

**Enforced by:** import-linter rules, CLAUDE.md conventions

### Data Flow (Clean)

```text
Sources (11+) → Ingestion → Extraction (3-tier) → Retrieval → Answers
                    ↓
                  Qdrant
                    ↓
                  Neo4j
```

### Performance Targets (Defined)

| Tier | Target | Status |
|------|--------|--------|
| Tier A | ≥50 pages/sec | Not implemented |
| Tier B | ≥200 sentences/sec | Not implemented |
| Tier C | ≤250ms median/window | Not implemented |
| Neo4j | ≥20k edges/min | Not implemented |
| Qdrant | ≥5k vectors/sec | Service ready |
| E2E | <3s p95 | Not tested |

---

## Services Ready to Use

### GPU-Accelerated (4 services)

- `taboot-vectors` (Qdrant) — Vector indexing
- `taboot-embed` (TEI) — Embedding inference
- `taboot-rerank` (SentenceTransformers) — Reranking
- `taboot-ollama` (Ollama) — LLM inference (Qwen3-4B)

### Supporting (6 services)

- `taboot-graph` (Neo4j) — Graph store
- `taboot-cache` (Redis) — Caching/queuing
- `taboot-db` (PostgreSQL) — Metadata
- `taboot-playwright` (Playwright) — Browser automation
- `taboot-crawler` (Firecrawl) — Web crawling
- `taboot-app` (FastAPI) — HTTP API

### Disabled (1 service, pending implementation)

- `taboot-worker` — Extraction worker (needs implementation)

---

## Next Steps

### Immediate Actions (This Week)

1. Implement core domain models
2. Define core ports/interfaces  
3. Create test structure

### Short-term (Weeks 2–3)

1. Normalizer + Chunker
2. Firecrawl adapter
3. Tier A extractors

### Medium-term (Weeks 4–6)

1. Tier B (spaCy)
2. Tier C (LLM)
3. Orchestration

### Longer-term (Weeks 7–8)

1. API routes + CLI
2. Tests + benchmarks
3. Performance tuning

---

## How to Use These Reports

### For Quick Status Update
→ Read `PIPELINE_MATURITY_SUMMARY.md` (15 min)

### For Complete Analysis
→ Read `PIPELINE_INVESTIGATION_REPORT.md` (45 min)

### For Implementation Planning
→ See both reports, then reference:
- `specs/001-taboot-v2-rag-platform/plan.md` — Implementation plan
- `packages/extraction/docs/EXTRACTION_SPEC.md` — Tier details
- `ARCHITECTURE.md` — System architecture

### For Setting Up Development
→ See:
- `../README.md` — Quick start (docker-compose)
- `.env.example` — Configuration template
- `pyproject.toml` — Dependencies and uv workspace

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Total Services | 11 (10 running, 1 disabled) |
| Total Packages | 10 (all empty except API stub) |
| Total Documented Components | 50+ |
| Implementation Gaps | 30+ blockers |
| Expected Code Volume | ~5500 LOC |
| Current Code | ~21 LOC |
| Architecture Maturity | 100% |
| Implementation Progress | 5% |
| GPU Services | 4 active |
| Performance Targets | 6 defined |
| User Stories | 10 prioritized |
| Acceptance Scenarios | 30+ |

---

## Project Summary

**Taboot v2** is a **well-designed but entirely unimplemented greenfield Doc-to-Graph RAG platform.**

The project has:
- Excellent architecture and layering discipline
- Complete specification and documentation
- Ready-to-use Docker infrastructure with all services running
- Zero production code in critical paths (99.6% gap)

The path forward is clear: implement according to the provided roadmap in phases, starting with core domain models and progressing through the three-tier extraction system. An MVP is achievable in 5–8 weeks with focused effort.

---

**Report Generated:** 2025-10-20
**Investigation Repository:** `[REPO_PATH]`
**Branch:** `001-taboot-v2-rag-platform`

**Quick Navigation:**
- [Full Investigation Report](PIPELINE_INVESTIGATION_REPORT.md)
- [Maturity Summary](PIPELINE_MATURITY_SUMMARY.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Extraction Specification](packages/extraction/docs/EXTRACTION_SPEC.md)
- [README](../README.md)
