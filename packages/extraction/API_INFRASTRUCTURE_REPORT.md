# Taboot API Application Analysis Report

## Executive Summary

The Taboot API is a FastAPI-based HTTP service (v0.4.0) serving as the primary entry point for the Doc-to-Graph RAG platform. It follows strict architectural principles with thin routing layers, asynchronous lifecycle management, comprehensive health checks, and event-driven middleware. The API is containerized with multi-stage Docker builds and orchestrated through docker-compose with 10+ backing services.

---

## 1. ENTRY POINTS & MAIN APPLICATION

### Primary Entry Point: `apps/api/app.py`

**File:** `/home/jmagar/code/taboot/apps/api/app.py`

**Application Creation:**
- Framework: FastAPI 0.119.0+
- Version: 0.4.0
- Title: "Taboot API"
- Description: "Doc-to-Graph RAG Platform"
- Document server: `/docs` (Swagger UI), `/redoc` (ReDoc)

**Key Pattern:**
```python
app = FastAPI(
    title="Taboot API",
    version="0.4.0",
    description="Doc-to-Graph RAG Platform",
    lifespan=lifespan,  # Async context manager
)
```

### Entry Point Context: Docker

**Docker Service:** `taboot-api` (line 247 in docker-compose.yaml)

**Container Entry Command:**
```bash
uvicorn apps.api.app:app --host 0.0.0.0 --port 8000
```

**Dockerfile:** `/home/jmagar/code/taboot/docker/api/Dockerfile`
- Multi-stage build (builder + runtime)
- Base image: `python:3.13-slim`
- Non-root user: `llamacrawl` (UID 10001)
- Dependencies installed with `uv sync --frozen --no-dev`, copied into runtime layer

---

## 2. LIFECYCLE MANAGEMENT & STARTUP/SHUTDOWN

### Async Lifespan Context Manager

**Location:** `apps/api/app.py:18-58`

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown."""
    config = get_config()

    # STARTUP
    logger.info("Starting Taboot API", extra={"version": "0.4.0"})
    
    try:
        # Initialize Redis for caching and job queues
        redis_client = await redis.from_url(
            config.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        app.state.redis = redis_client
        logger.info("Redis client initialized", extra={"url": config.redis_url})
    except Exception as e:
        logger.error("Failed to initialize Redis client", exc_info=True)
        raise  # Fail fast on startup

    logger.info("Taboot API startup complete")

    yield  # Application running

    # SHUTDOWN
    logger.info("Shutting down Taboot API")
    
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
        logger.info("Redis client closed")

    logger.info("Taboot API shutdown complete")
```

**Key Points:**
- Fails fast on Redis connection error (no fallback)
- Stores Redis client in app.state for access in routes
- Structured JSON logging with context
- Graceful shutdown with resource cleanup

---

## 3. MIDDLEWARE STACK

### Applied Middleware (in order)

1. **CORS Middleware** (line 69-75)
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # TODO: Configure for production via env var
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
   - All origins allowed (development mode)
   - Note: marked for production hardening

2. **Request Logging Middleware** (line 78)
   ```python
   app.add_middleware(RequestLoggingMiddleware)
   ```

### Request Logging Middleware Implementation

**File:** `/home/jmagar/code/taboot/apps/api/middleware/logging.py`

**Features:**
- Auto-generates UUID `request_id` for correlation tracing
- Logs request start, completion, and failures
- Measures elapsed time (milliseconds)
- Includes method, path, query params, client IP
- Adds `X-Request-ID` header to response
- Structured JSON output via `logger.extra`
- Propagates exceptions to FastAPI error handlers

**Example Log Output:**
```json
{
  "message": "Request started",
  "request_id": "uuid-1234",
  "method": "POST",
  "path": "/ingest",
  "query_params": "limit=20",
  "client_host": "127.0.0.1"
}
```

---

## 4. ROUTE REGISTRATION

**Location:** `apps/api/app.py:80-86`

Six routers registered with prefix-based organization:

```python
app.include_router(init.router)                                    # POST /init
app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(extract.router, prefix="/extract", tags=["extraction"])
app.include_router(query.router, tags=["query"])                   # /query
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(documents.router, tags=["documents"])           # /documents
```

### Endpoint Overview

| Route File | Endpoints | Purpose |
|-----------|-----------|---------|
| `init.py` | POST /init | System initialization (constraints, collections, schema) |
| `ingest.py` | POST /ingest, GET /ingest/{job_id} | Web ingestion with job tracking |
| `extract.py` | POST /extract/pending, GET /extract/status | Document extraction pipeline |
| `query.py` | POST /query | Natural language queries with hybrid retrieval |
| `status.py` | GET /status | System health and metrics |
| `documents.py` | GET /documents | List documents with filters and pagination |

---

## 5. BUILT-IN ENDPOINTS

### Health Check Endpoint

**Location:** `apps/api/app.py:89-122`

```python
@app.get("/health")
async def health() -> dict:
    """Health check with per-service validation."""
    health_status = await check_system_health()
    
    status_code = (
        http_status.HTTP_200_OK 
        if health_status["overall_healthy"] 
        else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return JSONResponse(
        content=health_status,
        status_code=status_code,
    )
```

**Services Checked:**
1. Neo4j (Bolt driver connectivity)
2. Qdrant (HTTP GET to root endpoint)
3. Redis (PING command)
4. TEI (GET /health endpoint)
5. Ollama (GET /api/tags endpoint)
6. Firecrawl (GET /health endpoint)
7. Playwright (GET /health endpoint)

**Response Example (200 OK):**
```json
{
  "overall_healthy": true,
  "services": {
    "neo4j": true,
    "qdrant": true,
    "redis": true,
    "tei": true,
    "ollama": true,
    "firecrawl": true,
    "playwright": true
  }
}
```

**Response Code:**
- 200 OK: All services healthy
- 503 Service Unavailable: Any service unhealthy

### Root Endpoint

**Location:** `apps/api/app.py:125-128`

```python
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Taboot API v0.4.0", "docs": "/docs"}
```

---

## 6. CONFIGURATION & ENVIRONMENT

### Configuration Class: `TabootConfig`

**File:** `/home/jmagar/code/taboot/packages/common/config/__init__.py`

**Type System:** Pydantic BaseSettings with type validation

**Configuration Categories:**

#### Service URLs (with defaults)
```python
firecrawl_api_url: str = "http://taboot-crawler:3002"
redis_url: str = "redis://taboot-cache:6379"
qdrant_url: str = "http://taboot-vectors:6333"
neo4j_uri: str = "bolt://taboot-graph:7687"
tei_embedding_url: str = "http://taboot-embed:80"
reranker_url: str = "http://taboot-rerank:8000"
playwright_microservice_url: str = "http://taboot-playwright:3000/scrape"
```

#### Database Credentials
```python
neo4j_user: str = "neo4j"
neo4j_password: str = "changeme"
neo4j_db: str = "neo4j"

postgres_user: str = "taboot"
postgres_password: str = "changeme"
postgres_db: str = "taboot"
postgres_port: int = 5432
```

#### Vector & Embedding Configuration
```python
collection_name: str = "documents"
tei_embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
qdrant_embedding_dim: int = 1024
```

#### Reranker Configuration
```python
reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"
reranker_batch_size: int = 16
reranker_device: str = "auto"  # "auto", "cuda", or "cpu"
```

#### Ollama LLM Configuration
```python
ollama_port: int = 11434
ollama_flash_attention: bool = True
ollama_keep_alive: str = "30m"
ollama_use_mmap: bool = True
ollama_max_queue: int = 20000
```

#### Extraction Pipeline Tuning
```python
tier_c_batch_size: int = 16  # LLM batch size
tier_c_workers: int = 4      # Concurrent LLM workers
redis_cache_ttl: int = 604800  # 7 days
neo4j_batch_size: int = 2000   # UNWIND batch size
```

#### Ingestion Tuning
```python
crawl_concurrency: int = 5
embedding_batch_size: int = 32
```

#### External API Credentials (Optional)
```python
github_token: str | None = None
reddit_client_id: str | None = None
reddit_client_secret: str | None = None
google_client_id: str | None = None
google_client_secret: str | None = None
google_oauth_refresh_token: str | None = None
elasticsearch_url: str | None = None
elasticsearch_api_key: str | None = None
tailscale_api_key: str | None = None
unifi_username: str | None = None
unifi_password: str | None = None
```

#### Firecrawl Configuration
```python
firecrawl_api_key: str = "changeme"
num_workers_per_queue: int = 16
worker_concurrency: int = 8
scrape_concurrency: int = 8
retry_delay: int = 1000
max_retries: int = 1
```

#### Observability
```python
log_level: str = "INFO"
health_check_timeout: float = 5.0
```

#### API Service
```python
taboot_http_port: int = 8000
host: str = "0.0.0.0"
```

### Smart URL Rewriting (Container vs Host)

**Feature:** `_is_running_in_container()` detection and `model_post_init()` hook

When running on host (not in container), URLs are rewritten to localhost with mapped ports:

```python
if not _is_running_in_container():
    self.tei_embedding_url = "http://localhost:4207"
    self.qdrant_url = "http://localhost:4203"
    self.neo4j_uri = "bolt://localhost:4206"
    self.redis_url = "redis://localhost:4202"
    self.reranker_url = "http://localhost:4208"
    self.firecrawl_api_url = "http://localhost:4200"
    self.playwright_microservice_url = "http://localhost:4213/scrape"
```

### Configuration Access

**Singleton Pattern:**
```python
def get_config() -> TabootConfig:
    global _config
    if _config is None:
        _config = TabootConfig()
    return _config
```

**Usage in Routes:**
```python
from packages.common.config import get_config

config = get_config()
# Access: config.redis_url, config.neo4j_uri, etc.
```

### Environment Files

**Primary:** `.env` (created from `.env.example`)

**Location Reference:** `/home/jmagar/code/taboot/.env.example`

**Key Variables Loaded:**
- FIRECRAWL_PORT, FIRECRAWL_INTERNAL_PORT, FIRECRAWL_API_KEY
- POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT
- OPENAI_API_KEY, MODEL_NAME, SEARXNG_ENDPOINT
- PLAYWRIGHT_PORT, PLAYWRIGHT_MICROSERVICE_URL
- REDIS_PORT, REDIS_URL, REDIS_RATE_LIMIT_URL
- QDRANT_HTTP_PORT, QDRANT_GRPC_PORT, QDRANT_URL, QDRANT_LOG_LEVEL, COLLECTION_NAME
- NEO4J_USER, NEO4J_PASSWORD, NEO4J_DB, NEO4J_HTTP_PORT, NEO4J_BOLT_PORT, NEO4J_URI
- TEI_HTTP_PORT, TEI_EMBEDDING_URL, TEI_EMBEDDING_MODEL
- RERANKER_HTTP_PORT, RERANKER_URL, RERANKER_MODEL, RERANKER_BATCH_SIZE, RERANKER_DEVICE
- GITHUB_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN
- ELASTICSEARCH_URL, ELASTICSEARCH_API_KEY
- UNIFI_API_TOKEN, UNIFI_USERNAME, UNIFI_PASSWORD
- TAILSCALE_API_KEY
- OLLAMA_PORT, OLLAMA_FLASH_ATTENTION, OLLAMA_KEEP_ALIVE, OLLAMA_USE_MMAP, OLLAMA_MAX_QUEUE
- LOG_LEVEL, FASTTEXT_HOME
- TABOOT_HTTP_PORT, TABOOT_API_URL

---

## 7. AUTHENTICATION & AUTHORIZATION

**Current Status:** NONE IMPLEMENTED

**Framework:** FastAPI with Pydantic models

**Security Notes:**
- CORS configured to allow all origins (development mode)
- No API key validation implemented
- All endpoints are publicly accessible
- Project guidance references future auth in SECURITY_MODEL.md (not yet implemented)

**Future Scope (from CLAUDE.md):**
- X-API-Key header requirement for privileged routes
- OAuth 2.0 support for data sources (GitHub, Google, Reddit)
- Request ID correlation for audit trails

---

## 8. DOCKER COMPOSE ORCHESTRATION

**File:** `/home/jmagar/code/taboot/docker-compose.yaml` (lines 247-280)

### Service Configuration

**Service Name:** `taboot-api`
**Build Context:** `.` (root of repository)
**Dockerfile:** `docker/api/Dockerfile`
**Image:** Auto-built
**Container Name:** `taboot-api`

### Networking

**Network:** `taboot-net` (bridge driver)
**Port Binding:** `${TABOOT_HTTP_PORT:-8000}:8000`

### Volume Mounts

```yaml
volumes:
  - taboot-api:/app/.venv
  - ${HOME}/.ssh:/home/llamacrawl/.ssh:ro
```

### Environment Configuration

```yaml
env_file:
  - .env
environment:
  LOG_LEVEL: ${LOG_LEVEL:-INFO}
```

### Startup Command

```bash
uvicorn apps.api.app:app --host 0.0.0.0 --port 8000
```

### Dependency Chain

```yaml
depends_on:
  taboot-cache:
    condition: service_healthy         # Redis
  taboot-vectors:
    condition: service_healthy         # Qdrant
  taboot-graph:
    condition: service_healthy         # Neo4j
  taboot-embed:
    condition: service_healthy         # TEI
  taboot-db:
    condition: service_healthy         # PostgreSQL
```

**All dependencies wait for healthchecks before API startup.**

### Health Check Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:4209/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 20s
```

---

## 9. DEPENDENCY INJECTION

### Route-Level Dependency Factories

**Pattern:** Factory functions return configured use-case instances

#### Example: Ingest Route (`ingest.py:95-132`)

```python
def get_ingest_use_case() -> IngestWebUseCase:
    """Dependency factory for IngestWebUseCase."""
    from packages.common.config import get_config
    from packages.common.db_schema import get_postgres_client
    from packages.clients.postgres_document_store import PostgresDocumentStore

    config = get_config()

    # Initialize adapters
    web_reader = WebReader(
        firecrawl_url=config.firecrawl_api_url,
        firecrawl_api_key=config.firecrawl_api_key,
    )
    normalizer = Normalizer()
    chunker = Chunker()
    embedder = Embedder(tei_url=config.tei_embedding_url)
    qdrant_writer = QdrantWriter(
        url=config.qdrant_url,
        collection_name=config.collection_name,
    )

    pg_conn = get_postgres_client()
    document_store = PostgresDocumentStore(pg_conn)

    return IngestWebUseCase(
        web_reader=web_reader,
        normalizer=normalizer,
        chunker=chunker,
        embedder=embedder,
        qdrant_writer=qdrant_writer,
        document_store=document_store,
        collection_name=config.collection_name,
    )
```

### Global State (Redis Client)

**Stored in app.state during lifespan:**
```python
app.state.redis = redis_client
```

**Access in routes:**
```python
redis_client = request.app.state.redis
# or via config and direct instantiation
```

---

## 10. ROUTES IN DETAIL

### Route 1: System Initialization (`/init`)

**File:** `apps/api/routes/init.py`
**Endpoint:** `POST /init`
**Status Code:** 200 OK

**Purpose:** Initialize schemas and collections across all databases

**Steps:**
1. Check system health
2. Create Neo4j constraints
3. Create Qdrant collections
4. Create PostgreSQL schema

**Response Schema:**
```python
class InitResponse(BaseModel):
    status: str              # "initialized"
    message: str
    services: dict[str, Any]  # Health status breakdown
```

---

### Route 2: Web Ingestion (`/ingest`)

**File:** `apps/api/routes/ingest.py`
**Endpoints:**
- `POST /ingest` — Start ingestion
- `GET /ingest/{job_id}` — Get status

#### POST /ingest

**Status Code:** 202 Accepted

**Request Schema:**
```python
class IngestionRequest(BaseModel):
    source_type: SourceType     # Enum: web, github, reddit, youtube, gmail, etc.
    source_target: str          # URL or identifier
    limit: int | None = None    # Max pages
```

**Response Schema:**
```python
class IngestionJobResponse(BaseModel):
    job_id: str
    state: str                  # "pending"
    source_type: str
    source_target: str
    created_at: str             # ISO 8601
```

**Storage:** In-memory dict (TODO: Replace with persistent storage)

#### GET /ingest/{job_id}

**Status Code:** 200 OK (or 404 if not found)

**Response Schema:**
```python
class IngestionJobStatus(BaseModel):
    job_id: str
    state: str
    source_type: str
    source_target: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    pages_processed: int
    chunks_created: int
    errors: list[dict[str, Any]] | None
```

---

### Route 3: Document Extraction (`/extract`)

**File:** `apps/api/routes/extract.py`
**Endpoints:**
- `POST /extract/pending` — Trigger extraction
- `GET /extract/status` — Get system status

#### POST /extract/pending

**Status Code:** 202 Accepted

**Response Schema:**
```python
class ExtractionResponse(BaseModel):
    processed: int    # Total attempted
    succeeded: int    # Successfully extracted
    failed: int       # Failed documents
```

**Components Used:**
- ExtractionOrchestrator
- Tier A: EntityPatternMatcher
- Tier B: WindowSelector
- Tier C: TierCLLMClient (Ollama, qwen3:4b, temperature=0, batch_size=16)

---

### Route 4: Query (`/query`)

**File:** `apps/api/routes/query.py`
**Endpoint:** `POST /query`
**Status Code:** 200 OK

**Request Schema:**
```python
class QueryRequest(BaseModel):
    question: str                           # min_length=1
    top_k: int = 20                        # 1-100, vector search candidates
    rerank_top_n: int = 5                  # 1-20, after reranking
    source_types: Optional[List[str]] = None  # Filter by source
    after: Optional[datetime] = None       # Filter by ingestion date
```

**Response Schema:**
```python
class QueryResponse(BaseModel):
    answer: str
    sources: List[tuple[str, str]]      # (source_name, url)
    latency_ms: int
    latency_breakdown: dict             # Stage timings
    vector_count: int                   # Chunks from vector search
    graph_count: int                    # Results from graph traversal
```

**Retrieval Pipeline:**
1. Embed query (TEI)
2. Filter by metadata (source, date)
3. Vector search (Qdrant, top-k)
4. Rerank (Qwen3-Reranker-0.6B)
5. Graph traversal (Neo4j, ≤2 hops)
6. Synthesis (Qwen3-4B with citations)

---

### Route 5: System Status (`/status`)

**File:** `apps/api/routes/status.py`
**Endpoint:** `GET /status`
**Status Code:** 200 OK

**Response Schema:**
```python
class SystemStatusResponse(BaseModel):
    overall_healthy: bool
    services: dict[str, ServiceHealth]
    queue_depth: QueueDepth
    metrics: MetricsSnapshot
```

**Uses:** GetStatusUseCase from core

---

### Route 6: Documents (`/documents`)

**File:** `apps/api/routes/documents.py`
**Endpoint:** `GET /documents`
**Status Code:** 200 OK

**Query Parameters:**
- `limit` (1-100, default 10)
- `offset` (default 0)
- `source_type` (optional, filters by SourceType enum)
- `extraction_state` (optional, filters by ExtractionState enum)

**Response Schema:**
```python
class DocumentListResponse(BaseModel):
    documents: List[Document]
    total: int
    limit: int
    offset: int
```

**Valid source_types:**
- web, github, reddit, youtube, gmail, elasticsearch, docker_compose, swag, tailscale, unifi, ai_session

**Valid extraction_states:**
- pending, tier_a_done, tier_b_done, tier_c_done, completed, failed

---

## 11. DEPENDENCIES & PACKAGES

### Direct Imports in app.py

```python
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware import RequestLoggingMiddleware
from apps.api.routes import documents, extract, ingest, init, query, status
from packages.common.config import get_config
```

### Route Dependencies

**packages/core/use_cases:**
- `ingest_web.IngestWebUseCase`
- `extract_pending.ExtractPendingUseCase`
- `query.execute_query`
- `get_status.GetStatusUseCase`
- `list_documents.ListDocumentsUseCase`

**packages/ingest:**
- `chunker.Chunker`
- `embedder.Embedder`
- `normalizer.Normalizer`
- `readers.web.WebReader`

**packages/extraction:**
- `orchestrator.ExtractionOrchestrator`
- `tier_a.parsers` (module)
- `tier_a.patterns.EntityPatternMatcher`
- `tier_b.window_selector.WindowSelector`
- `tier_c.llm_client.TierCLLMClient`

**packages/vector:**
- `writer.QdrantWriter`
- `collections` (module)

**packages/graph:**
- `constraints` (module)

**packages/common:**
- `config.get_config`
- `db_schema.get_postgres_client`, `create_postgresql_schema`
- `health.check_system_health`
- `postgres_document_store.PostgresDocumentStore`
- `logging.get_logger`

**packages/schemas:**
- `models.IngestionJob`, `SourceType`, `Document`, `ExtractionState`

---

## 12. HEALTH CHECK IMPLEMENTATION

**File:** `/home/jmagar/code/taboot/packages/common/health.py`

### Health Check Functions (Async)

1. **check_neo4j_health()** — Verify Bolt driver connectivity
2. **check_qdrant_health()** — HTTP GET to Qdrant root
3. **check_redis_health()** — Redis PING
4. **check_tei_health()** — HTTP GET to /health
5. **check_ollama_health()** — HTTP GET to /api/tags
6. **check_firecrawl_health()** — HTTP GET to /health
7. **check_playwright_health()** — HTTP GET to /health

### System Health Aggregation

```python
async def check_system_health() -> SystemHealthStatus:
    """Check all services concurrently with timeout."""
    results = await asyncio.gather(
        check_neo4j_health(),
        check_qdrant_health(),
        check_redis_health(),
        check_tei_health(),
        check_ollama_health(),
        check_firecrawl_health(),
        check_playwright_health(),
        return_exceptions=True,
    )
    
    services = {
        "neo4j": bool(results[0]) if not isinstance(results[0], Exception) else False,
        "qdrant": bool(results[1]) if not isinstance(results[1], Exception) else False,
        # ... etc
    }
    
    healthy = all(services.values())
    
    return SystemHealthStatus(healthy=healthy, services=services)
```

**Timeout:** Configurable via `config.health_check_timeout` (default 5.0 seconds)

---

## 13. TESTING SETUP

**Test Configuration File:** `/home/jmagar/code/taboot/tests/apps/api/conftest.py`

### Test Fixtures

```python
@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set environment variables before TestClient creation."""
    os.environ["RERANKER_BATCH_SIZE"] = "16"
    os.environ["OLLAMA_PORT"] = "11434"
    os.environ["FIRECRAWL_API_URL"] = "http://localhost:4200"
    os.environ["REDIS_URL"] = "redis://localhost:4202"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    os.environ["NEO4J_URI"] = "bolt://localhost:4206"
    os.environ["TEI_EMBEDDING_URL"] = "http://localhost:80"
    yield

@pytest.fixture(scope="module")
def client():
    """Create FastAPI TestClient after env setup."""
    from apps.api.app import app
    with TestClient(app) as test_client:
        yield test_client
```

### Test Files

- `/tests/apps/api/test_init_route.py` — /init endpoint
- `/tests/apps/api/test_ingest_route.py` — /ingest endpoints
- `/tests/apps/api/test_extract_route.py` — /extract endpoints
- `/tests/apps/api/test_extract_status_route.py` — /extract/status
- `/tests/apps/api/test_query_route.py` — /query endpoint
- `/tests/apps/api/test_status_route.py` — /status endpoint
- `/tests/apps/api/test_documents_route.py` — /documents endpoint

**Run Tests:**
```bash
uv run pytest tests/apps/api -m "not slow"
```

---

## 14. ARCHITECTURAL DECISIONS

### Principle 1: Thin Routing Layer

All business logic is in `packages/core` use-cases. Routes only:
- Validate request syntax
- Call use-case
- Transform response

### Principle 2: Fail Fast

Redis connection failure in startup kills the app. No fallbacks allowed.

### Principle 3: Structured JSON Logging

All logging uses Python's logging module with JSON formatter. Every log includes:
- Timestamp (implicit via logger)
- Message
- extra dict (for context)
- exc_info (for exceptions)

### Principle 4: Configuration is Centralized

Single `get_config()` singleton provides all env vars with type validation.

### Principle 5: Health Checks Are Comprehensive

Every critical service is checked. /health endpoint returns service-level granularity.

### Principle 6: Async-First

All I/O is async (redis, httpx, database operations).

---

## 15. SECURITY CONSIDERATIONS

**Current Limitations:**
- No API key validation
- No authentication/authorization
- CORS allows all origins
- All endpoints publicly accessible
- Credentials in .env (not secrets manager)

**Production Checklist (from CLAUDE.md):**
- Implement X-API-Key validation for privileged routes
- Restrict CORS to specific origins
- Add OAuth 2.0 for data sources
- Use secrets manager for credentials
- Implement request ID correlation for audit trails
- Add rate limiting per source

---

## 16. PERFORMANCE CHARACTERISTICS

### Concurrency Model
- Uvicorn worker processes: 1 (single process, async)
- FastAPI/Starlette event loop: asyncio
- Thread pool: Used for blocking Neo4j operations

### Timeouts
- Health checks: 5 seconds (configurable)
- Redis connect: Default from redis-py (no explicit timeout in lifespan)

### Resource Usage
- Memory: Main process + Redis client
- Connections: 1 Redis connection pool + Neo4j driver + Qdrant client + Ollama client

---

## 17. LOGGING & OBSERVABILITY

### Log Configuration

**Via:** Standard Python logging module
**Formatter:** JSON (via `python-json-logger`)
**Level:** Configurable via LOG_LEVEL env var (default INFO)

### Request Correlation

**Request ID:** UUID generated per request
**Header:** X-Request-ID (added to response)
**Availability:** In request.state.request_id for handlers

### Structured Context

All logger.info/error calls include extra dict:
```python
logger.info("Message", extra={"key1": value1, "key2": value2})
```

---

## 18. SUMMARY TABLE

| Aspect | Value |
|--------|-------|
| Framework | FastAPI 0.119.0+ |
| Python Version | 3.11+ (3.13 in Docker) |
| Port | 8000 (configurable) |
| Lifespan | Async context manager |
| Middleware | CORS + RequestLogging |
| Routes | 6 routers, 9 endpoints |
| Configuration | Pydantic BaseSettings |
| Database Clients | Redis, Neo4j, Qdrant, PostgreSQL |
| Health Endpoints | /health, /status |
| Authentication | None (planned) |
| Logging | JSON structured |
| Testing | pytest + TestClient |

---

## 19. KEY FILES REFERENCE

| Path | Purpose |
|------|---------|
| `/apps/api/app.py` | Main FastAPI app, lifespan, middleware, routes |
| `/apps/api/middleware/logging.py` | Request logging middleware |
| `/apps/api/routes/*.py` | Endpoint implementations |
| `/docker/api/Dockerfile` | Multi-stage Docker build |
| `/docker-compose.yaml` | Service orchestration (`taboot-api` section) |
| `/packages/common/config/__init__.py` | Configuration singleton |
| `/packages/common/health.py` | Health check functions |
| `/tests/apps/api/conftest.py` | Test fixtures |
| `/.env.example` | Environment template |
