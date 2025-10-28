# Docker Infrastructure Audit Report
## Network, Volumes, and Resource Allocation Analysis

**Generated:** 2025-10-27
**Scope:** docker-compose.yaml, Dockerfiles, environment configuration
**Severity Levels:** Critical, High, Medium, Low

---

## Executive Summary

The Taboot infrastructure demonstrates **solid foundational design** with bridge networking, GPU support, and appropriate volume persistence. However, several **resource allocation gaps** and **network isolation concerns** require immediate attention before production deployment.

**Key Findings:**
- **11/13 services** lack explicit resource limits (memory, CPU)
- **GPU allocation** uses singleton approach (potential contention)
- **Network security** relies on bridge isolation without egress controls
- **Volume persistence** strategy is robust but backup concerns exist
- **Health checks** are well-implemented across all critical services

---

## 1. Network Configuration Analysis

### Current Architecture
```
taboot-net (bridge driver)
├── All 13 services connected
├── Internal DNS resolution (service names)
└── Host port mapping via port bindings
```

### Issues Found

#### 1.1 No Network Isolation (Low Priority, Design Choice)
**Status:** ⚠️ By Design
**Finding:** All services share single bridge network (`taboot-net`)

**Impact:**
- Service-to-service communication unprotected
- No microsegmentation for defense-in-depth
- Single compromise could access any service

**Recommendation:**
```yaml
# For future high-security deployments, consider separate networks:
networks:
  taboot-net:     # Application tier (api, web, worker)
    driver: bridge
  data-net:       # Data tier (db, cache, graph, vectors)
    driver: bridge
  gpu-net:        # GPU services (embedding, rerank, ollama)
    driver: bridge
```

**Current Impact on This Project:** Medium (single-user, development-focused system)

---

#### 1.2 Port Exposure on All Interfaces (Medium Priority)
**Status:** ⚠️ Needs Configuration
**Finding:** All port bindings map to `0.0.0.0` (all interfaces)

**Problematic Services:**
- Qdrant: `7000:6333`, `7001:6334` (vector search engine)
- Neo4j: `7474:7474`, `7687:7687` (graph database)
- PostgreSQL: `5432:5432` (main database)
- Redis: `6379:6379` (cache/session store)

**Impact:**
- Anyone on network can access databases directly
- No firewall boundary between internal/external services
- Bypasses API authentication entirely

**Recommended Fix:**
```yaml
# docker-compose.yaml - Change port bindings to localhost only
taboot-graph:
  ports:
    - "127.0.0.1:7474:7474"
    - "127.0.0.1:7687:7687"

taboot-vectors:
  ports:
    - "127.0.0.1:7000:6333"
    - "127.0.0.1:7001:6334"

taboot-cache:
  ports:
    - "127.0.0.1:6379:6379"

taboot-db:
  ports:
    - "127.0.0.1:5432:5432"
```

**Note:** Keep external ports for Firecrawl (3002), Playwright (3000), Ollama (11434), API (8000), Web (3000) if needed for local development.

---

#### 1.3 No Egress Network Policies (Low Priority, Infrastructure Limitation)
**Status:** ⚠️ Docker Limitation
**Finding:** Docker bridge driver doesn't support egress filtering

**Impact:**
- Compromised container could connect to external systems
- No rate limiting on outbound connections
- No control over which services can reach external APIs

**Current Mitigation:**
- Run behind NAT/firewall at infrastructure level
- Use iptables rules on host (advanced)
- Monitor outbound connections with netflow

**Not Critical For:** Single-user development environment

---

### Network Security Recommendations Summary
| Issue | Priority | Effort | Impact |
|-------|----------|--------|--------|
| Database port exposure | High | Low | Immediate fix: bind to 127.0.0.1 |
| Service isolation | Medium | High | Future: separate networks by tier |
| Egress filtering | Low | High | Defer to infrastructure layer |

---

## 2. Resource Allocation Analysis

### Critical Finding: Most Services Lack Resource Limits

**Status:** 🔴 CRITICAL FOR PRODUCTION

#### 2.1 Memory Allocation Summary

| Service | Memory Limit | Memory Reserved | Status |
|---------|--------------|-----------------|--------|
| **taboot-vectors** (Qdrant) | ❌ None | ❌ None | UNPROTECTED |
| **taboot-embed** (TEI) | ❌ None | ❌ None | UNPROTECTED |
| **taboot-rerank** | ❌ None | ❌ None | UNPROTECTED |
| **taboot-ollama** | ❌ None | ❌ None | UNPROTECTED |
| **taboot-graph** (Neo4j) | ❌ None | 6GB (config) | PARTIAL |
| **taboot-cache** (Redis) | ❌ None | ❌ None | UNPROTECTED |
| **taboot-db** (PostgreSQL) | ❌ None | ❌ None | UNPROTECTED |
| **taboot-api** | ❌ None | ❌ None | UNPROTECTED |
| **taboot-web** | ❌ None | ❌ None | UNPROTECTED |
| **taboot-worker** | ❌ None | ❌ None | UNPROTECTED |
| **taboot-crawler** (Firecrawl) | ❌ None | ❌ None | UNPROTECTED |
| **taboot-playwright** | ❌ None | ❌ None | UNPROTECTED |

**Neo4j Partial Protection:**
```yaml
environment:
  NEO4J_server_memory_heap_initial__size: 2G
  NEO4J_server_memory_heap_max__size: 2G
  NEO4J_server_memory_pagecache_size: 2G
```
✅ Good: Application-level config (JVM controlled)
❌ Missing: Docker-level hard limits (prevents host OOM)

---

#### 2.2 Recommended Resource Allocation (RTX 4070 System)

**System Assumptions:**
- RTX 4070 (24GB VRAM)
- 32GB System RAM
- 8-core CPU
- Single-user development system

**Proposed Configuration:**
```yaml
# GPU Services (RTX 4070 = 24GB total)
taboot-vectors:
  deploy:
    resources:
      limits:
        memory: 8G      # Qdrant: HNSW indexing
      reservations:
        memory: 6G
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

taboot-embed:  # TEI embeddings
  deploy:
    resources:
      limits:
        memory: 6G
      reservations:
        memory: 5G
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

taboot-rerank:  # Reranking model
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 3G
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

taboot-ollama:  # LLM inference
  deploy:
    resources:
      limits:
        memory: 8G
      reservations:
        memory: 6G
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]

# Data Services (System RAM = 32GB)
taboot-graph:  # Neo4j
  deploy:
    resources:
      limits:
        memory: 6G
      reservations:
        memory: 5G

taboot-cache:  # Redis
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1.5G

taboot-db:  # PostgreSQL
  deploy:
    resources:
      limits:
        memory: 4G
      reservations:
        memory: 3G

# Application Services
taboot-api:
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "1.0"
      reservations:
        memory: 1G
        cpus: "0.5"

taboot-web:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "0.5"
      reservations:
        memory: 512m
        cpus: "0.25"

taboot-worker:
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: "2.0"
      reservations:
        memory: 2G
        cpus: "1.0"

taboot-crawler:
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "1.0"
      reservations:
        memory: 1G
        cpus: "0.5"

taboot-playwright:
  deploy:
    resources:
      limits:
        memory: 1G
      reservations:
        memory: 512m
```

**Verification After Implementation:**
```bash
# Check actual resource usage
docker stats --no-stream

# Monitor OOM events
docker events --filter type=container --filter status=die
```

---

### 2.3 GPU Resource Allocation Issues

#### Current GPU Configuration
```yaml
x-gpu-deploy: &gpu-deploy
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**Issues:**
1. ❌ All 4 GPU services request `count: 1` (full GPU)
2. ❌ Only one can actually run at a time
3. ❌ No device ID specification (undefined behavior if multiple GPUs)
4. ❌ No fallback for missing NVIDIA runtime

#### Problem Scenario
```
✅ taboot-vectors starts (claims GPU #0) → 24GB allocated
⏳ taboot-embed tries to start (wants full GPU) → WAIT
⏳ taboot-rerank tries to start (wants full GPU) → WAIT
⏳ taboot-ollama tries to start (wants full GPU) → WAIT

Result: Only 1 of 4 GPU services runs at any time!
```

#### Recommended Fix: GPU Time-Sharing

**Option 1: MIG (Multi-Instance GPU) - RTX 4070 Not Supported**
- RTX 4070 doesn't support MIG (enterprise GPUs only)
- Not applicable to this system

**Option 2: CUDA Context Isolation (Recommended)**
```yaml
# docker-compose.yaml
x-gpu-deploy: &gpu-deploy
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            device_ids: ["0"]      # Explicit GPU ID
            capabilities: [gpu]

# Services share GPU, each gets own CUDA context
taboot-vectors:
  <<: [*common-base, *gpu-deploy]
  environment:
    <<: *gpu-env
    # Memory management crucial for sharing
    PYTORCH_CUDA_ALLOC_CONF: "max_split_size_mb:512"

taboot-embed:
  <<: [*common-base, *gpu-deploy]
  environment:
    <<: *gpu-env
    PYTORCH_CUDA_ALLOC_CONF: "max_split_size_mb:512"
    # Limit concurrent requests to prevent OOM
    TEI_MAX_CONCURRENT_REQUESTS: "40"  # Reduced from 80

taboot-rerank:
  <<: [*common-base, *gpu-deploy]
  environment:
    <<: *gpu-env
    # Smaller batch to prevent contention
    RERANKER_BATCH_SIZE: "8"  # Reduced from 16

taboot-ollama:
  <<: [*common-base, *gpu-deploy]
  environment:
    <<: *gpu-env
    OLLAMA_MAX_QUEUE: "10000"  # Reduced from 20000
```

**Option 3: CPU Fallback (Development Only)**
```bash
# Start without GPU dependency
docker-compose up --scale taboot-embed=0 taboot-rerank=0
# Use local Python fallback for embeddings/reranking
```

**Option 4: Sequential Startup with Health Checks**
```yaml
# docker-compose.yaml - Enforce startup order
taboot-embed:
  depends_on:
    taboot-vectors:
      condition: service_healthy

taboot-rerank:
  depends_on:
    taboot-embed:
      condition: service_healthy

taboot-ollama:
  depends_on:
    taboot-rerank:
      condition: service_healthy
```

---

### 2.4 CPU Allocation

**Current State:** ❌ No CPU limits defined

**Potential Issues:**
- Single service can consume all 8 cores
- No isolation between application tiers
- Worker process can starve API service

**Recommended CPU Allocation:**
```yaml
# Heavy compute services
taboot-worker:
  deploy:
    resources:
      limits:
        cpus: "4.0"      # Up to 4 cores for extraction
      reservations:
        cpus: "2.0"      # Guaranteed 2 cores

# Medium compute
taboot-ollama:
  deploy:
    resources:
      limits:
        cpus: "2.0"
      reservations:
        cpus: "1.0"

# Light services
taboot-api:
  deploy:
    resources:
      limits:
        cpus: "1.0"
      reservations:
        cpus: "0.5"

taboot-web:
  deploy:
    resources:
      limits:
        cpus: "0.5"
      reservations:
        cpus: "0.25"
```

---

## 3. Volume Management Analysis

### 3.1 Volume Inventory

| Volume | Mount Point | Service(s) | Type | Purpose |
|--------|------------|-----------|------|---------|
| **taboot-vectors** | `/qdrant/storage` | qdrant | Data | Vector DB persistence |
| **taboot-embed** | `/data` | tei-embed | Cache | Model cache (HF_HUB_CACHE) |
| **taboot-rerank** | huggingface-cache | rerank | Cache | Transformer model cache |
| **taboot-ollama** | `/root/.ollama` | ollama | Data | LLM models |
| **taboot-graph_data** | `/data` | neo4j | Data | Graph DB data files |
| **taboot-graph_logs** | `/logs` | neo4j | Logs | Audit/debug logs |
| **taboot-graph_plugins** | `/plugins` | neo4j | Code | APOC plugins |
| **taboot-cache** | `/data` | redis | Data | Persistence (AOF) |
| **taboot-db** | `/var/lib/postgresql/data` | postgres | Data | Relational DB |
| **taboot-api** | `/app/.venv` | api | Cache | Python venv (layer caching) |
| **spacy-models** | `/root/.spacy/data` | worker | Data | NLP model cache |

### 3.2 Volume Drivers & Options

**Current:** All volumes use default Docker volume driver (local)

**Observations:**
✅ **Good:**
- Named volumes (not bind mounts) = better security
- Persistent across container recreation
- Volume driver default suitable for single-host

❌ **Gaps:**
- No explicit backup strategy documented
- No volume labels for lifecycle management
- No replication for disaster recovery

### 3.3 Data Lifecycle Concerns

#### Critical Data Volumes (PRODUCTION BACKUP REQUIRED)
1. **taboot-db** (PostgreSQL)
   - User accounts, sessions, audit logs
   - Soft-delete records with retention period
   - Contains authentication state
   - **Backup Frequency:** Daily
   - **Retention:** 30 days (with point-in-time recovery)

2. **taboot-graph_data** (Neo4j)
   - Knowledge graph, extracted entities
   - Non-recoverable if lost (requires re-ingestion)
   - **Backup Frequency:** Daily
   - **Retention:** 7 days

3. **taboot-cache** (Redis)
   - Session state, extraction cursors, DLQ
   - Recoverable if lost (data regenerates)
   - **Backup Frequency:** Optional (not critical)

#### Cache Volumes (EPHEMERAL, NO BACKUP NEEDED)
- **taboot-embed** - Re-downloads from HuggingFace
- **taboot-rerank** - Re-downloads from HuggingFace
- **taboot-ollama** - Re-downloads from Ollama registry
- **spacy-models** - Re-downloads from spaCy
- **taboot-api** - Rebuilt on next deployment

#### Vector DB (CRITICAL BUT REGENERABLE)
- **taboot-vectors** (Qdrant)
  - Regenerated from PostgreSQL document chunks
  - Loss means re-running extraction pipeline
  - **Backup Frequency:** Daily
  - **Retention:** 3 days

### 3.4 Volume Backup Strategy (Recommended)

```bash
#!/bin/bash
# backup-taboot-volumes.sh - Run daily via cron

BACKUP_DIR="/backup/taboot/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Critical database backup (point-in-time recovery)
docker exec taboot-db pg_dump -U taboot taboot | \
  gzip > "$BACKUP_DIR/postgres_dump.sql.gz"

# Neo4j backup
docker exec taboot-graph neo4j-admin dump --database=neo4j \
  --to=/tmp/neo4j-backup.dump
docker cp taboot-graph:/tmp/neo4j-backup.dump \
  "$BACKUP_DIR/neo4j-backup.dump"

# Qdrant snapshot
docker exec taboot-vectors qdrant-cli snapshot create \
  --path /qdrant/storage/snapshots

# Copy snapshots to host
docker cp taboot-vectors:/qdrant/storage/snapshots \
  "$BACKUP_DIR/qdrant-snapshots"

# Cleanup old backups (30 days)
find /backup/taboot -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

---

### 3.5 Volume Permission Issues

**Current Vulnerabilities:**
1. ❌ No explicit `chown` in volume initialization
2. ❌ Container user permissions unclear
3. ❌ Cross-container volume access not restricted

**Current Mitigations:**
✅ Dockerfile uses non-root users:
- API: `llamacrawl` (UID 10001)
- Worker: `taboot` (UID 10002)
- Web: `nextjs` (UID 1001)

✅ Volume ownership set during COPY:
```dockerfile
COPY --chown=taboot:taboot /app/packages ./packages
```

**Recommendation:** Add volume init script
```yaml
# docker-compose.yaml
taboot-db:
  volumes:
    - taboot-db:/var/lib/postgresql/data
  # Create volume with correct permissions
  init: true  # Enable init process for volume setup
```

---

## 4. Health Check Configuration

### Status: ✅ WELL IMPLEMENTED

All 13 services have health checks:

| Service | Check Type | Interval | Timeout | Retries | Start Period |
|---------|-----------|----------|---------|---------|--------------|
| taboot-vectors | TCP (bash) | 30s | 10s | 3 | 40s |
| taboot-embed | HTTP GET | 30s | 10s | 3 | 20s |
| taboot-rerank | HTTP GET | 30s | 10s | 3 | 20s |
| taboot-graph | Cypher | 30s | 10s | 3 | 40s |
| taboot-cache | PING | 30s | 10s | 3 | 10s |
| taboot-ollama | HTTP GET | 30s | 10s | 3 | 60s |
| taboot-playwright | HTTP GET | 30s | 10s | 3 | 20s |
| taboot-crawler | HTTP GET | 30s | 10s | 3 | 30s |
| taboot-db | pg_isready | 5s | 5s | 5 | 15s |
| taboot-api | HTTP GET | 30s | 10s | 3 | 40s |
| taboot-web | HTTP GET | 30s | 10s | 3 | 40s |
| taboot-worker | Process grep | 30s | 10s | 3 | 30s |

**Strengths:**
- ✅ Consistent timeout/retry logic
- ✅ Realistic start periods for ML services (20-60s)
- ✅ Service-specific checks (not generic TCP)
- ✅ Critical path dependencies defined

**Minor Issues:**
- Worker healthcheck uses `pgrep` (fragile if process renamed)
- Qdrant healthcheck is fragile (bash TCP dance)

**Recommended Improvement:**
```yaml
# More robust worker healthcheck
taboot-worker:
  healthcheck:
    test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]  # Placeholder
    # Better: Have worker expose /health endpoint
```

---

## 5. Dependency Order & Startup

### Current Configuration

```
docker-compose up -d
```

**Explicit Dependencies:**
```
taboot-vectors → taboot-embed (depends_on, condition: service_healthy)
taboot-vectors → taboot-api (depends_on, condition: service_healthy)
taboot-graph → taboot-api (depends_on, condition: service_healthy)
taboot-cache → taboot-api (depends_on, condition: service_healthy)
taboot-db → taboot-api (depends_on, condition: service_healthy)
taboot-api → taboot-web (depends_on, condition: service_healthy)

taboot-worker (depends on all data services):
  ├── taboot-cache
  ├── taboot-vectors
  ├── taboot-graph
  ├── taboot-embed
  ├── taboot-rerank
  └── taboot-db
```

**Startup Sequence (Actual):**
1. PostgreSQL, Redis, Neo4j (no deps) - start immediately
2. Wait 15-40s for healthchecks to pass
3. TEI Embedding (depends on Vectors healthy) - starts
4. API (depends on all data layers healthy) - starts ~80s
5. Web (depends on API healthy) - starts ~120s
6. Worker (depends on all) - starts ~150s

**Total Time to Ready:** ~2-3 minutes

**Potential Issues:**
- ⚠️ If any service fails healthcheck, dependent services never start
- ⚠️ No automatic retry (cascade failure)
- ⚠️ No logging of why healthchecks failed

---

## 6. Docker Build Optimizations

### Analysis of Dockerfile Strategies

#### API Service (Python, FastAPI)
**Status:** ✅ GOOD

```dockerfile
# Multi-stage: builder → runtime
FROM python:3.13-slim AS builder
  # Install deps into venv

FROM python:3.13-slim AS runtime
  # Copy venv from builder
  # Copy non-root user
  # Lean runtime image
```

**Strengths:**
- Separates build tools from runtime
- Uses slim base image
- Non-root user (`llamacrawl:10001`)
- Build cache friendly

**Size:** ~500MB (slim + Python + deps)

#### Web Service (Next.js, Node)
**Status:** ✅ EXCELLENT

```dockerfile
# Multi-stage: base → development → builder → installer → production
FROM node:22-alpine AS base
  # pnpm + turbo setup

FROM base AS builder
  # Prune workspace for @taboot/web only

FROM base AS installer
  # Install deps from pruned workspace
  # Build Next.js standalone

FROM node:22-alpine AS production
  # Copy .next/standalone only (~20MB!)
```

**Strengths:**
- Turbo prune (monorepo optimization)
- Alpine base (tiny)
- Standalone Next.js output (no node_modules in runtime)
- Non-root user

**Size:** ~250MB (Alpine + Node + standalone build)

#### Worker Service (Python ML)
**Status:** ⚠️ NEEDS IMPROVEMENT

```dockerfile
# Multi-stage: builder → runtime
FROM taboot/python-ml:latest AS builder
  # Uses pre-built base image (good for reproducibility)

FROM python:3.13-slim AS runtime
  # Rebuilds Python layer (redundant!)
  # spaCy + transformers not included
```

**Issues:**
- ❌ `taboot/python-ml:latest` base not included in this repo
- ❌ Worker rebuilds Python layer unnecessarily
- ❌ Unclear what's in ML base image

**Recommendation:** Document ML base image or inline it

#### Database Services
**Status:** ✅ MINIMAL

Neo4j: Single-stage wrapper
```dockerfile
FROM neo4j:5.23-community
RUN ln -sf /var/lib/neo4j/bin/cypher-shell /usr/local/bin/cypher-shell
```

PostgreSQL: Adds pg_cron plugin + schema
```dockerfile
FROM postgres:16
RUN apt-get install postgresql-${PG_MAJOR}-cron
# Copy nuq.sql for job queue schema
```

---

## 7. Security Findings

### 7.1 Container Users

| Service | User | UID | Status |
|---------|------|-----|--------|
| taboot-api | llamacrawl | 10001 | ✅ Non-root |
| taboot-web | nextjs | 1001 | ✅ Non-root |
| taboot-worker | taboot | 10002 | ✅ Non-root |
| taboot-graph | neo4j | 101 | ✅ Non-root (image) |
| taboot-cache | redis | 999 | ✅ Non-root (image) |
| taboot-db | postgres | 999 | ✅ Non-root (image) |

✅ **Good:** All services run non-root

### 7.2 Volume Mounts

| Service | Mount | Flags | Issue |
|---------|-------|-------|-------|
| taboot-api | `/home/llamacrawl/.ssh` | `:ro` | ✅ Read-only SSH keys |
| taboot-api | `/app/.venv` | rw | ✅ Writable venv cache |
| taboot-vectors | `/qdrant/storage` | rw | ✅ Data persistence |
| taboot-db | `/var/lib/postgresql/data` | rw | ✅ Data persistence |

✅ **Good:** Minimal mounts, appropriate permissions

### 7.3 Image Security

**Issues Found:**
- ⚠️ No image signing/verification
- ⚠️ Third-party images pulled without hash pinning
- ⚠️ `latest` tags used for multiple services

**Recommended Hardening:**
```yaml
# Pin specific image versions and digests
taboot-embed:
  image: ghcr.io/huggingface/text-embeddings-inference:sha256:abc123@latest
  # Better:
  image: ghcr.io/huggingface/text-embeddings-inference:v1.5.0

taboot-vectors:
  # Pin Qdrant version
  image: qdrant/qdrant:v1.10.1-gpu-nvidia-latest

taboot-graph:
  # Pin Neo4j version
  image: neo4j:5.23-community
```

---

## 8. Production Readiness Checklist

| Category | Item | Status | Severity |
|----------|------|--------|----------|
| **Network** | Database port exposure (0.0.0.0) | ❌ Not Fixed | HIGH |
| **Network** | Service isolation | ⚠️ Partial | MEDIUM |
| **Resources** | Memory limits | ❌ Missing | CRITICAL |
| **Resources** | CPU limits | ❌ Missing | CRITICAL |
| **Resources** | GPU resource contention | ⚠️ Potential | HIGH |
| **Storage** | Backup strategy | ⚠️ Documented only | HIGH |
| **Storage** | Volume permissions | ✅ Good | - |
| **Health** | Health checks | ✅ Excellent | - |
| **Security** | Non-root users | ✅ Good | - |
| **Security** | Image pinning | ❌ Missing | MEDIUM |
| **Observability** | Logging | ⚠️ Basic | MEDIUM |
| **Monitoring** | Resource metrics | ❌ None | MEDIUM |

---

## 9. Recommended Action Plan

### Immediate (Week 1) - CRITICAL
**Effort:** 2-4 hours

1. **Bind databases to localhost only**
   ```bash
   # Edit docker-compose.yaml
   # Change 0.0.0.0:XXXX:YYYY → 127.0.0.1:XXXX:YYYY
   # for: PostgreSQL, Redis, Neo4j, Qdrant
   ```
   **Impact:** Closes direct database access from network

2. **Add memory limits to all services**
   ```bash
   # Add deploy.resources.limits.memory to each service
   # Reference: Section 2.2 above
   ```
   **Impact:** Prevents OOM cascade failures

### Short Term (Week 2-3) - HIGH PRIORITY
**Effort:** 4-8 hours

3. **Implement GPU resource sharing**
   ```bash
   # Update docker-compose.yaml per Section 2.3
   # Reduce batch sizes and concurrent requests
   # Test startup sequence
   ```
   **Impact:** Allows multiple GPU services to run simultaneously

4. **Document backup strategy**
   ```bash
   # Create backup-taboot-volumes.sh
   # Schedule with cron: 0 2 * * * /path/to/backup.sh
   # Verify restore procedure
   ```
   **Impact:** Enables disaster recovery

### Medium Term (Month 1) - MEDIUM PRIORITY
**Effort:** 8-16 hours

5. **Add resource monitoring**
   ```bash
   # Docker stats collection
   # Prometheus metrics export
   # Grafana dashboards
   ```
   **Impact:** Visibility into resource usage patterns

6. **Pin image versions**
   ```bash
   # Identify current versions: docker images
   # Update docker-compose.yaml with specific tags
   # Document rationale for each pin
   ```
   **Impact:** Reproducible deployments

### Future (Month 2+) - NICE TO HAVE
**Effort:** 16+ hours

7. **Network segmentation**
   ```bash
   # Create separate networks by tier
   # Update service dependencies
   # Add network policies
   ```
   **Impact:** Defense-in-depth network security

8. **Observability stack**
   ```bash
   # Add: Prometheus, Grafana, Loki, Jaeger
   # Instrument services with metrics/traces
   # Create dashboards
   ```
   **Impact:** Production visibility

---

## 10. Configuration Examples

### docker-compose.yaml - Critical Fixes (Copy-Paste Ready)

```yaml
# BEFORE: Insecure port binding
taboot-graph:
  ports:
    - "${NEO4J_HTTP_PORT:-7474}:7474"

# AFTER: Localhost only
taboot-graph:
  ports:
    - "127.0.0.1:${NEO4J_HTTP_PORT:-7474}:7474"

# BEFORE: No resource limits
taboot-api:
  build:
    context: apps/api

# AFTER: With resource limits
taboot-api:
  build:
    context: apps/api
  deploy:
    resources:
      limits:
        memory: 2G
        cpus: "1.0"
      reservations:
        memory: 1G
        cpus: "0.5"
```

### Verification Commands

```bash
# Check port bindings
docker-compose config | grep -A5 "ports:"

# Verify memory limits applied
docker inspect taboot-api | grep -i memory

# Monitor resource usage
watch -n 1 'docker stats --no-stream'

# Test database accessibility
nc -zv localhost 5432  # Should fail if bound to 127.0.0.1
```

---

## 11. Appendix: Service-by-Service Audit

### taboot-vectors (Qdrant)
- ✅ GPU support configured
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ✅ Health check robust
- ⚠️ HNSW indexing memory-hungry (8GB recommended)

### taboot-embed (TEI)
- ✅ GPU support configured
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ⚠️ High max batch tokens (163840) - memory risk
- ✅ HF_HUB_CACHE configured for model caching

### taboot-rerank
- ✅ GPU support configured
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ✅ Batch size reasonable (16)
- ⚠️ Built image (not public registry)

### taboot-graph (Neo4j)
- ⚠️ JVM memory configured (2G) but no Docker limit
- ⚠️ Port exposed to 0.0.0.0
- ✅ APOC plugin included
- ✅ Health check via Cypher
- ⚠️ Single replica (no HA)

### taboot-cache (Redis)
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ✅ AOF persistence enabled
- ✅ Health check reliable
- ⚠️ No authentication configured

### taboot-db (PostgreSQL)
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ✅ Schema initialized with nuq.sql
- ✅ pg_cron enabled for maintenance
- ✅ Health check reliable

### taboot-api (FastAPI)
- ✅ Non-root user (llamacrawl)
- ❌ No resource limits
- ✅ Multi-stage build optimized
- ✅ uvicorn autoreload disabled
- ✅ Health endpoint available

### taboot-web (Next.js)
- ✅ Non-root user (nextjs)
- ❌ No resource limits
- ✅ Standalone build (minimal)
- ✅ Alpine base (small)
- ✅ Turbo prune (monorepo optimized)

### taboot-worker (Extraction)
- ✅ Non-root user (taboot)
- ❌ No resource limits (heavy compute!)
- ⚠️ Depends on ML base image
- ⚠️ Uses pgrep for healthcheck (fragile)
- ⚠️ No max parallelism defined

### taboot-crawler (Firecrawl)
- ⚠️ Port exposed to 0.0.0.0
- ❌ No resource limits
- ✅ ulimits configured (nofile)
- ⚠️ Loads .env (credential exposure risk)
- ✅ extra_hosts for host.docker.internal

### taboot-playwright
- ⚠️ Port exposed to 0.0.0.0
- ❌ No resource limits
- ✅ Minimal healthcheck
- ⚠️ Browser service (resource-heavy)
- ⚠️ No headless mode specified

### taboot-ollama
- ✅ GPU support configured
- ⚠️ Port exposed to 0.0.0.0
- ❌ No memory limit
- ✅ Flash attention enabled
- ⚠️ Max queue high (20000) - memory risk

---

## Summary

**Network & Security:** ⚠️ Moderate Risk
- Primary issue: Database port exposure
- Easy to fix (localhost binding)
- Good use of non-root users

**Resource Allocation:** 🔴 Critical Risk
- All services lack memory limits
- GPU contention unresolved
- OOM scenarios likely under load

**Volume Management:** ✅ Good
- Named volumes for persistence
- No backup strategy documented
- Permission inheritance unclear

**Operational Readiness:** ⚠️ Partial
- Excellent health checks
- Good startup dependencies
- Missing observability/monitoring

**Recommended Priority:**
1. Fix database port exposure (immediate)
2. Add memory limits (immediate)
3. Resolve GPU resource contention (week 1)
4. Document backup/restore (week 2)
5. Add monitoring/observability (month 1)

---

**Report Version:** 1.0
**Last Updated:** 2025-10-27
**Reviewed By:** Infrastructure Audit
**Next Review:** Post-remediation
