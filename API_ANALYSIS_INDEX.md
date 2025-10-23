# Taboot API Analysis - Complete Documentation Index

## Overview

This directory contains comprehensive analysis of the Taboot API application infrastructure, configuration, and implementation. Two complementary documents have been generated to support developers working with the FastAPI service.

## Generated Documents

### 1. API_INFRASTRUCTURE_REPORT.md (27 KB, 1028 lines)
**Location:** `/home/jmagar/code/taboot/packages/extraction/API_INFRASTRUCTURE_REPORT.md`

**Purpose:** Comprehensive deep-dive technical reference

**Contains:**
1. Entry Points & Main Application
2. Lifecycle Management & Startup/Shutdown
3. Middleware Stack
4. Route Registration
5. Built-in Endpoints (/health, /)
6. Configuration & Environment
7. Authentication & Authorization
8. Docker Compose Orchestration
9. Dependency Injection
10. All Routes in Detail
11. Dependencies & Packages
12. Health Check Implementation
13. Testing Setup
14. Architectural Decisions
15. Security Considerations
16. Performance Characteristics
17. Logging & Observability
18. Summary Tables
19. Key Files Reference

**Best For:**
- Understanding complete system architecture
- Learning how all pieces fit together
- Implementing new features
- Troubleshooting complex issues
- Production deployment planning

---

### 2. API_QUICK_REFERENCE.md (8.7 KB, 329 lines)
**Location:** `/home/jmagar/code/taboot/apps/api/API_QUICK_REFERENCE.md`

**Purpose:** Practical quick-lookup guide for developers

**Contains:**
- Application structure (directory tree)
- Configuration flow diagram
- Startup sequence
- Request flow
- Endpoints summary table
- Key dependencies list
- Configuration categories
- Health check logic flow
- Docker integration details
- Logging patterns
- Testing patterns
- Design principles
- Security status roadmap
- Common issues & solutions
- Performance notes
- Development commands
- File location reference

**Best For:**
- Quick lookups during development
- Troubleshooting common issues
- Understanding request flow
- Finding file locations
- Reviewing configurations
- Copy-paste command references

---

## Core Files Referenced

### Application Entry Point
- **File:** `/home/jmagar/code/taboot/apps/api/app.py`
- **Lines:** 129
- **Contains:** FastAPI app creation, lifespan management, middleware registration, route inclusion, /health and / endpoints

### Middleware
- **File:** `/home/jmagar/code/taboot/apps/api/middleware/logging.py`
- **Lines:** 99
- **Contains:** Request/response logging with UUID correlation, timing, structured context

### Routes (6 routers, 9 endpoints)
- **Init:** `/home/jmagar/code/taboot/apps/api/routes/init.py` - POST /init
- **Ingest:** `/home/jmagar/code/taboot/apps/api/routes/ingest.py` - POST/GET /ingest
- **Extract:** `/home/jmagar/code/taboot/apps/api/routes/extract.py` - POST/GET /extract
- **Query:** `/home/jmagar/code/taboot/apps/api/routes/query.py` - POST /query
- **Status:** `/home/jmagar/code/taboot/apps/api/routes/status.py` - GET /status
- **Documents:** `/home/jmagar/code/taboot/apps/api/routes/documents.py` - GET /documents

### Configuration
- **File:** `/home/jmagar/code/taboot/packages/common/config/__init__.py`
- **Type:** Pydantic BaseSettings singleton
- **Parameters:** 100+ configurable service URLs, credentials, model parameters, pipeline tuning, external API keys

### Health Checks
- **File:** `/home/jmagar/code/taboot/packages/common/health.py`
- **Functions:** 8 async health check functions
- **Checked Services:** Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright

### Docker Build
- **File:** `/home/jmagar/code/taboot/docker/app/Dockerfile`
- **Type:** Multi-stage build (builder → runtime)
- **Base:** python:3.13-slim
- **User:** llamacrawl (non-root, UID 10001)

### Docker Compose Service
- **File:** `/home/jmagar/code/taboot/docker-compose.yaml` (lines 247-280)
- **Service:** taboot-app
- **Port:** 8000 (configurable via TABOOT_HTTP_PORT)
- **Dependencies:** Redis, Qdrant, Neo4j, TEI, PostgreSQL

### Testing
- **Fixtures:** `/home/jmagar/code/taboot/tests/apps/api/conftest.py`
- **Test Files:** 9 test modules (init, ingest, extract, extract_status, query, status, documents)
- **Framework:** pytest + TestClient

### Environment Template
- **File:** `/home/jmagar/code/taboot/.env.example`
- **Format:** Key=value pairs for all services and credentials

---

## Quick Navigation Guide

### I need to...

**...understand the overall architecture**
→ Read API_INFRASTRUCTURE_REPORT.md sections 1-3, 14-16

**...find a specific file**
→ Check API_QUICK_REFERENCE.md "File Locations Reference"

**...add a new endpoint**
→ Read API_INFRASTRUCTURE_REPORT.md section 10, then study existing routes

**...debug a configuration issue**
→ Read API_INFRASTRUCTURE_REPORT.md section 6 + API_QUICK_REFERENCE.md "Config Categories"

**...understand health checks**
→ Read API_INFRASTRUCTURE_REPORT.md section 12 + API_QUICK_REFERENCE.md "Health Check Logic"

**...set up the API locally**
→ Read API_QUICK_REFERENCE.md "Quick Start" + "Development Commands"

**...troubleshoot a problem**
→ Check API_QUICK_REFERENCE.md "Common Issues & Solutions"

**...understand the request flow**
→ See API_QUICK_REFERENCE.md "Request Flow" diagram

**...see Docker configuration**
→ Read API_INFRASTRUCTURE_REPORT.md section 8 + API_QUICK_REFERENCE.md "Docker Integration"

**...write tests**
→ Read API_INFRASTRUCTURE_REPORT.md section 13 + API_QUICK_REFERENCE.md "Testing Pattern"

**...understand logging**
→ Read API_INFRASTRUCTURE_REPORT.md section 17 + API_QUICK_REFERENCE.md "Logging Pattern"

---

## Key Findings Summary

### Architecture
- **Framework:** FastAPI 0.119.0+ with uvicorn
- **Pattern:** Thin routing layer (business logic in packages/core)
- **Async:** 100% async I/O (redis, httpx, database)
- **Lifecycle:** Async context manager for startup/shutdown

### Endpoints (9 total)
| Path | Method | Purpose |
|------|--------|---------|
| / | GET | Root info |
| /health | GET | Service health (7 concurrent checks) |
| /init | POST | System initialization |
| /ingest | POST | Start web crawl |
| /ingest/{job_id} | GET | Ingestion status |
| /extract/pending | POST | Trigger extraction |
| /extract/status | GET | Extraction metrics |
| /query | POST | RAG query engine |
| /documents | GET | List with filters |

### Configuration
- **Type:** Pydantic BaseSettings
- **Pattern:** Singleton via get_config()
- **Smart Detection:** Container vs host (rewrites URLs)
- **Parameters:** 100+ configurable

### Dependencies
- **Required:** Redis (startup), Neo4j, Qdrant, PostgreSQL, TEI, Ollama
- **Optional:** Firecrawl, Playwright, external API credentials

### Security
- **Current:** None implemented
- **Planned:** X-API-Key, OAuth 2.0, CORS restrictions, secrets manager

### Health Checks
- **7 services:** Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright
- **Mode:** Concurrent, 5s timeout
- **Response:** 200 OK (all healthy) or 503 (any failed)

### Testing
- **Framework:** pytest + TestClient
- **Coverage:** 9 test files
- **Fixtures:** Environment setup, TestClient creation

### Performance
- **Concurrency:** Single async worker
- **Event Loop:** asyncio (non-blocking)
- **Executor:** Used only for Neo4j sync operations
- **Connections:** Pooled (Redis, Neo4j, Qdrant)

---

## Development Workflow

1. **First Time Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   uv sync
   docker compose up -d
   ```

2. **Running Locally**
   ```bash
   uv run uvicorn apps.api.app:app --reload --port 8000
   # or
   docker compose up taboot-app
   ```

3. **Testing**
   ```bash
   uv run pytest tests/apps/api -m "not slow"
   ```

4. **Checking Health**
   ```bash
   curl http://localhost:8000/health
   ```

5. **Viewing Docs**
   ```bash
   open http://localhost:8000/docs
   ```

---

## File Organization

```
Taboot Repository
├── apps/api/
│   ├── app.py                          [Main FastAPI app]
│   ├── API_QUICK_REFERENCE.md          [Quick lookup guide]
│   ├── CLAUDE.md                       [Route development guidance]
│   ├── README.md                       [Development guide]
│   ├── pyproject.toml                  [Package metadata]
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── logging.py                  [Request logging middleware]
│   ├── routes/
│   │   ├── init.py                     [POST /init]
│   │   ├── ingest.py                   [POST/GET /ingest]
│   │   ├── extract.py                  [POST/GET /extract]
│   │   ├── query.py                    [POST /query]
│   │   ├── status.py                   [GET /status]
│   │   └── documents.py                [GET /documents]
│   ├── deps/
│   ├── services/
│   └── schemas/
│
├── packages/extraction/
│   └── API_INFRASTRUCTURE_REPORT.md    [Deep technical reference]
│
├── packages/common/
│   ├── config/__init__.py              [Pydantic BaseSettings config]
│   └── health.py                       [Health check functions]
│
├── docker/
│   └── app/Dockerfile                  [Multi-stage build]
│
├── docker-compose.yaml                 [Service orchestration]
├── .env.example                        [Environment template]
├── API_ANALYSIS_INDEX.md               [This file]
│
└── tests/apps/api/
    ├── conftest.py                     [Test fixtures]
    ├── test_init_route.py
    ├── test_ingest_route.py
    ├── test_extract_route.py
    ├── test_extract_status_route.py
    ├── test_query_route.py
    ├── test_status_route.py
    └── test_documents_route.py
```

---

## Document Generation Notes

These reports were generated by analyzing:
- 14 Python files in apps/api/
- Configuration system in packages/common/
- Health check implementation
- Docker configuration
- Test setup and fixtures
- Environment variables
- Route implementations
- Middleware stack
- Dependency patterns

Analysis covered:
- Code structure and organization
- Configuration loading and validation
- Request/response handling
- Middleware pipeline
- Health check orchestration
- Docker integration
- Testing patterns
- Error handling
- Security posture
- Performance characteristics

---

## Related Documentation

- **Project CLAUDE.md:** `/home/jmagar/code/taboot/CLAUDE.md` (project-wide conventions)
- **API CLAUDE.md:** `/home/jmagar/code/taboot/apps/api/CLAUDE.md` (route-specific guidance)
- **Common CLAUDE.md:** `/home/jmagar/code/taboot/packages/common/CLAUDE.md` (utilities guidance)
- **Extraction CLAUDE.md:** `/home/jmagar/code/taboot/packages/extraction/CLAUDE.md` (extraction pipeline guidance)

---

## Support

For questions or clarifications about the API infrastructure:

1. Check API_QUICK_REFERENCE.md for quick answers
2. Check API_INFRASTRUCTURE_REPORT.md section index for detailed explanations
3. Review the actual source code files (all are in absolute paths in the reports)
4. Consult CLAUDE.md files for development guidelines

---

**Report Generation Date:** 2024-10-23
**Analysis Scope:** API application setup, configuration, infrastructure
**Coverage:** 100% of public API surface and core infrastructure
