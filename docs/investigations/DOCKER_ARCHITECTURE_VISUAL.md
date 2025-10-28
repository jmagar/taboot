# Docker Compose Architecture - Visual Reference

> **Status:** Complete service architecture with 3 critical fixes needed
> **Last Updated:** October 27, 2025
> **Scope:** Full deployment topology, dependencies, and performance metrics

---

## Dependency Graph & Startup Order

```
                          ┌─────────────────────────────────────┐
                          │      TIER 0: Pre-requisites        │
                          │  (Must exist before docker-compose) │
                          │    - NVIDIA Docker Runtime          │
                          │    - Docker 20.10+ (buildkit)       │
                          │    - Docker Compose 1.29+           │
                          └─────────────────────────────────────┘
                                        │
                                        ▼
        ┌───────────────────────────────────────────────────────────┐
        │             TIER 1: Foundation (No Dependencies)          │
        │                                                           │
        │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐  │
        │  │taboot-db │  │taboot-    │  │taboot-   │  │taboot- │  │
        │  │(Postgres)│  │vectors    │  │graph     │  │cache   │  │
        │  │port 5432 │  │(Qdrant GPU)  (Neo4j)   │  │(Redis) │  │
        │  └──────────┘  └───────────┘  └──────────┘  └────────┘  │
        │                                     │                     │
        │  ┌──────────────────┐               │                     │
        │  │  taboot-ollama   │               │                     │
        │  │  (Ollama LLM)    │               │                     │
        │  │  GPU              │               │                     │
        │  └──────────────────┘               │                     │
        └───────────────────────────────────────────────────────────┘
                            │                 │
                            ▼                 ▼
        ┌────────────────────────────────────────────────────────┐
        │  TIER 2: GPU-Based Processors (Parallel Startup)      │
        │                                                        │
        │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
        │  │taboot-embed  │ │taboot-       │ │taboot-       │   │
        │  │(TEI GPU)     │ │rerank        │ │playwright    │   │
        │  │port 8080     │ │(SentenceTran)│ │port 3000     │   │
        │  │depends on    │ │GPU           │ │port 3000     │   │
        │  │vectors       │ │port 8081     │ │(BROWSER!)    │   │
        │  └──────────────┘ └──────────────┘ └──────────────┘   │
        │                                                        │
        │  ┌──────────────────────────────────────────┐          │
        │  │  taboot-base-ml (Build Base Image)      │          │
        │  │  Builds: taboot/python-ml:latest        │          │
        │  │  Installs: torch, transformers, spacy   │          │
        │  │  GPU enabled, ~120s startup             │          │
        │  └──────────────────────────────────────────┘          │
        └────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────────────────────┐
        │     TIER 3: API & Integration Services                │
        │                                                        │
        │  ┌──────────────────┐    ┌──────────────────────┐     │
        │  │  taboot-crawler  │    │   taboot-api         │     │
        │  │  (Firecrawl)     │    │   (FastAPI)          │     │
        │  │  port 3002       │    │   port 8000          │     │
        │  │  Depends on:     │    │   Depends on:        │     │
        │  │  - db            │    │   - db               │     │
        │  │  - cache         │    │   - cache            │     │
        │  │  - playwright    │    │   - vectors          │     │
        │  │                  │    │   - graph            │     │
        │  └──────────────────┘    │   - embed            │     │
        │                          │   - rerank           │     │
        │                          └──────────────────────┘     │
        └────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────────────────────┐
        │        TIER 4: User-Facing & Workers                 │
        │                                                        │
        │  ┌──────────────────┐    ┌──────────────────────┐     │
        │  │  taboot-web      │    │  taboot-worker       │     │
        │  │  (Next.js)       │    │  (Extraction)        │     │
        │  │  port 3005       │    │  No ports (internal) │     │
        │  │  Depends on:     │    │  Depends on:         │     │
        │  │  - api           │    │  - base-ml           │     │
        │  │  - db            │    │  - cache             │     │
        │  │                  │    │  - vectors           │     │
        │  │  (transitive:    │    │  - graph             │     │
        │  │   api → graph)   │    │  - embed             │     │
        │  │                  │    │  - rerank            │     │
        │  │                  │    │  - db                │     │
        │  └──────────────────┘    └──────────────────────┘     │
        └────────────────────────────────────────────────────────┘
```

---

## Port Assignments (After Fixes)

```
Development/Browser        Service                Port
─────────────────────────  ──────────────────────  ────
http://localhost:3000      taboot-playwright      3000
http://localhost:3002      taboot-crawler         3002
http://localhost:3005      taboot-web             3005

(Internal only)
                           taboot-db              5432
                           taboot-cache           6379
                           taboot-vectors HTTP    7000
                           taboot-vectors gRPC    7001
                           taboot-graph HTTP      7474
                           taboot-graph Bolt      7687
                           taboot-api             8000
                           taboot-embed           8080
                           taboot-rerank          8081
                           taboot-ollama          11434
```

---

## Build Contexts & Paths (After Fixes)

```
taboot-api:
├── context: apps/api/
├── dockerfile: ../../docker/api/Dockerfile
└── additional_contexts:
    └── packages: ../../packages ✓ FIXED

taboot-web:
├── context: apps/web/
├── dockerfile: ../../docker/web/Dockerfile
└── additional_contexts:
    └── packages-ts: ../../packages-ts ✓ FIXED

taboot-worker:
├── context: ./
├── dockerfile: docker/worker/Dockerfile
└── additional_contexts:
    └── packages: ./packages ✓ CORRECT

taboot-base-ml:
├── context: ./
├── dockerfile: docker/base-ml/Dockerfile
└── image: taboot/python-ml:latest ✓ NEW SERVICE
```

---

## Multi-Stage Build Strategies

### taboot-api (Python - 2 stages)

```
┌──────────────────────┐
│ Stage 1: builder     │
│ (python:3.13-slim)   │
│                      │
│ - uv install         │
│ - pip packages       │
│ - venv: .venv        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Stage 2: runtime     │
│ (python:3.13-slim)   │
│                      │
│ - COPY from builder  │
│ - Non-root user      │
│ - uvicorn app        │
└──────────────────────┘
```

### taboot-web (Node.js - 4 stages)

```
┌──────────────────────┐
│ Stage 1: base        │
│ (node:22-alpine)     │
│ - pnpm, turbo        │
└──────┬───────────────┘
       │
       ├─────────────────────────────────────┐
       ▼                                     ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Stage 2: builder     │  │ Stage 3: installer   │
│ - turbo prune        │  │ - pnpm install       │
│ - workspace prune    │  │ - turbo build        │
└──────┬───────────────┘  └──────┬───────────────┘
       │                         │
       └─────────────────────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ Stage 4: production  │
      │ (node:22-alpine)     │
      │                      │
      │ - COPY standalone    │
      │ - Non-root user      │
      │ - node server.js     │
      └──────────────────────┘
```

### taboot-worker (Python - 2 stages)

```
┌──────────────────────────────┐
│ Stage 1: builder             │
│ (taboot/python-ml:latest)    │
│                              │
│ - Pre-built ML deps          │
│ - workspace packages         │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Stage 2: runtime     │
│ (python:3.13-slim)   │
│                      │
│ - COPY from builder  │
│ - Non-root user      │
│ - python worker main │
└──────────────────────┘
```

---

## Health Check Strategy

| Service | Check Type | Endpoint | Interval | Timeout |
|---------|-----------|----------|----------|---------|
| taboot-db | Process | `pg_isready` | 5s | 5s |
| taboot-cache | Command | `redis-cli ping` | 30s | 10s |
| taboot-graph | Cypher Shell | cypher-shell query | 30s | 10s |
| taboot-vectors | HTTP | `/readyz` (via TCP) | 30s | 10s |
| taboot-embed | HTTP | `curl /health` | 30s | 10s |
| taboot-rerank | HTTP | `curl /healthz` | 30s | 10s |
| taboot-api | HTTP | `curl /health` | 30s | 10s |
| taboot-web | HTTP | `curl /api/health` | 30s | 10s |
| taboot-worker | Process | `pgrep -f worker.main` | 30s | 10s |
| taboot-ollama | HTTP | `curl /api/version` | 30s | 10s |
| taboot-crawler | HTTP | `curl /health` | 30s | 10s |
| taboot-playwright | HTTP | `curl /health` | 30s | 10s |

---

## Storage Topology

```
Persistent Volumes (Docker named volumes):
├── taboot-embed/          ~2GB (TEI models)
├── taboot-rerank/         ~500MB (Reranker models)
├── taboot-vectors/        ~5GB (Qdrant HNSW index)
├── taboot-graph_data/     ~5GB (Neo4j database)
├── taboot-graph_logs/     ~100MB (Neo4j logs)
├── taboot-graph_plugins/  ~100MB (Neo4j plugins)
├── taboot-cache/          ~500MB (Redis RDB)
├── taboot-ollama/         ~5GB (Model cache)
├── taboot-db/             ~2GB (PostgreSQL)
├── taboot-api/            ~500MB (venv cache)
├── huggingface-cache/     ~1GB (HF models)
└── spacy-models/          ~300MB (spaCy models)

Total: ~25GB+ persistent storage
```

---

## Network Topology

```
Docker Bridge Network: taboot-net

┌─────────────────────────────────────────────────────┐
│                   taboot-net                         │
│                                                     │
│  Service Discovery (DNS within network):           │
│                                                     │
│  taboot-api:8000         (FastAPI)                  │
│  taboot-web:3000         (Next.js)                  │
│  taboot-crawler:3002     (Firecrawl)                │
│  taboot-embed:80         (TEI)                      │
│  taboot-rerank:8000      (Reranker)                 │
│  taboot-vectors:6333    (Qdrant HTTP)               │
│  taboot-vectors:6334    (Qdrant gRPC)               │
│  taboot-graph:7474       (Neo4j HTTP)               │
│  taboot-graph:7687       (Neo4j Bolt)               │
│  taboot-cache:6379       (Redis)                    │
│  taboot-db:5432          (PostgreSQL)               │
│  taboot-ollama:11434     (Ollama)                   │
│  taboot-playwright:3000  (Playwright)               │
│                                                     │
│  All services reach each other by name              │
│  Example: http://taboot-api:8000/health             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Startup Sequence (with timing)

```
┌──── 0s ────────────────────────────────┐
│ docker-compose up -d                  │
└───────────────────────────────────────┘
              │
              ▼ 0-10s
         ┌─────────────────────────────────────────────┐
         │ TIER 1 (All Parallel - ~10-40s)            │
         │ ├─ taboot-cache       (Redis)     ~1s      │
         │ ├─ taboot-db          (Postgres) ~10s      │
         │ ├─ taboot-graph       (Neo4j)    ~30s      │
         │ ├─ taboot-vectors     (Qdrant)   ~40s      │
         │ └─ taboot-ollama      (LLM)      ~10s      │
         └─────────────────────────────────────────────┘
              │
        (health checks: ✓ all healthy)
              │
              ▼ 10-40s
         ┌─────────────────────────────────────────────┐
         │ TIER 2 (All Parallel - ~20-60s)            │
         │ ├─ taboot-embed       (TEI GPU)   ~60s    │
         │ ├─ taboot-rerank      (GPU)       ~30s    │
         │ ├─ taboot-base-ml     (Base)      ~120s   │
         │ └─ taboot-playwright  (Browser)   ~5s     │
         └─────────────────────────────────────────────┘
              │
        (health checks: ✓ all healthy)
              │
              ▼ 30-120s
         ┌─────────────────────────────────────────────┐
         │ TIER 3 (All Parallel - ~30-40s)            │
         │ ├─ taboot-crawler     (Firecrawl) ~30s    │
         │ └─ taboot-api         (FastAPI)   ~40s    │
         └─────────────────────────────────────────────┘
              │
        (health checks: ✓ all healthy)
              │
              ▼ 60-160s
         ┌─────────────────────────────────────────────┐
         │ TIER 4 (All Parallel - ~30-40s)            │
         │ ├─ taboot-web         (Next.js)   ~40s    │
         │ └─ taboot-worker      (Extract)   ~30s    │
         └─────────────────────────────────────────────┘
              │
        (health checks: ✓ all healthy)
              │
              ▼
┌──── ~160s total ────────────────────────┐
│ All services healthy and ready         │
│ docker-compose ps shows: healthy       │
└────────────────────────────────────────┘
```

---

## Performance Profile (RTX 4070 GPU)

```
Extraction Performance Targets:
├── Tier A (Deterministic):  ≥50 pages/sec (CPU)
├── Tier B (spaCy):          ≥200 sentences/sec
└── Tier C (LLM):            median ≤250ms/window

GPU Services:
├── taboot-vectors:  HNSW indexing
├── taboot-embed:    Sentence embeddings (Qwen3-Embedding-0.6B)
├── taboot-rerank:   Passage reranking (Qwen3-Reranker-0.6B)
└── taboot-ollama:   LLM inference (Qwen3-4B-Instruct)

Memory Requirements (approximate):
├── VRAM:
│   ├─ taboot-embed:      4GB
│   ├─ taboot-rerank:     2GB
│   ├─ taboot-vectors:    4GB
│   └─ taboot-ollama:     6GB
│
├── RAM:
│   ├─ taboot-graph:      4GB
│   ├─ taboot-api:        1GB
│   ├─ taboot-web:        512MB
│   ├─ taboot-worker:     2GB
│   └─ taboot-db:         2GB
│
└── Total: ~25GB RAM + 16GB VRAM (RTX 4070: 12GB VRAM)
```

---

## Service Characteristics

### Data Services (Single Instance, Non-Scalable)
- **taboot-db** (PostgreSQL): Primary data store
- **taboot-cache** (Redis): Session and rate-limit cache
- **taboot-graph** (Neo4j): Knowledge graph
- **taboot-vectors** (Qdrant): Vector embeddings
- **taboot-embed** (TEI): Embedding model
- **taboot-rerank** (SentenceTransformers): Reranking model
- **taboot-ollama** (Ollama): LLM inference

### Application Services (Stateless, Scalable)
- **taboot-api** (FastAPI): REST API → Can scale to 3-5 replicas
- **taboot-web** (Next.js): Web dashboard → Can scale to 3-5 replicas
- **taboot-worker** (Extraction): Background jobs → Can scale to 5-10 replicas

### Utility Services
- **taboot-crawler** (Firecrawl): Web crawling
- **taboot-playwright** (Playwright): Browser automation
- **taboot-base-ml**: Build base image (not at runtime)

---

## Production Readiness Checklist

✅ **Excellent:**
- Multi-stage builds used effectively
- Non-root users in all containers
- Health checks on all services (100%)
- .dockerignore files present
- Layer caching optimized
- Reproducible builds (uv.lock, pnpm-lock.yaml)

⚠️ **Needs Attention (Priority 2):**
- Some images use `:latest` tag (not reproducible)
- GPU configuration not documented
- No image scanning in pipeline
- Qdrant health check overly complex

🔴 **Critical Fixes Required (Priority 1):**
- Fix additional_contexts paths (API, Web)
- Add taboot-base-ml service
- Document port conflict requirements

---

## Quick Commands

```bash
# Full system startup
docker-compose up -d

# Check service status
docker-compose ps

# Watch services become healthy
watch -n 5 docker-compose ps

# View logs for specific service
docker-compose logs -f taboot-api

# Stop everything
docker-compose down

# Remove volumes and start fresh
docker-compose down -v
docker-compose up -d

# Scale API service
docker-compose up -d --scale taboot-api=3

# Health check endpoints
curl http://localhost:8000/health        # API
curl http://localhost:3005/api/health    # Web

# Database queries
docker-compose exec taboot-db psql -U taboot -d taboot -c "SELECT * FROM users;"

# Neo4j console
docker-compose exec taboot-graph cypher-shell -u neo4j -p "<password>"
```

---

## Summary

- **12 Services** (+ 1 base image service after fixes)
- **5 GPU Services** (Vectors, Embed, Rerank, Ollama, base-ml)
- **100% Health Check Coverage**
- **Multi-stage Builds** for all services
- **Microservices Architecture** with excellent separation of concerns
- **~160 seconds** typical startup time (all tiers)
- **~25GB+** total persistent storage
- **~25GB RAM + 16GB VRAM** recommended

After applying the 3 critical fixes, the system is production-ready from a Docker perspective.
