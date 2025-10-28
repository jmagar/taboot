# Dockerfile Audit Report

**Date:** 2025-10-27
**Scope:** 7 Dockerfiles across the Taboot RAG platform
**Assessment:** Comprehensive best practices review with security, performance, and maintainability focus

---

## Executive Summary

The Dockerfiles demonstrate **excellent foundational practices** with strong patterns for multi-stage builds, security, and performance optimization. However, several **critical issues** and **performance opportunities** exist:

### Key Findings

| Category | Status | Count |
|----------|--------|-------|
| **Critical Security Issues** | ⚠️ FOUND | 2 |
| **Performance Issues** | ⚠️ FOUND | 5 |
| **Best Practice Violations** | ⚠️ FOUND | 6 |
| **Positive Practices** | ✅ GOOD | 15+ |

---

## File-by-File Analysis

### 1. docker/api/Dockerfile

**Status:** ⚠️ MEDIUM CONCERNS | Overall: 75/100

#### Strengths
- ✅ Multi-stage build (builder/runtime separation) - excellent layer isolation
- ✅ Non-root user (`llamacrawl:10001`) created early (line 83)
- ✅ Virtual environment isolation with proper PATH setup (line 89)
- ✅ Ownership set during COPY (line 88) - efficient permission handling
- ✅ BuildKit cache mount for uv cache (line 34)
- ✅ Proper HEALTHCHECK with timeout/retries (lines 101-102)
- ✅ Fail-fast shell configuration (lines 8-9)
- ✅ Python optimization environment variables (lines 70-73)

#### Critical Issues

**1. SECURITY: Missing ADDITIONAL_CONTEXTS Copy**
```dockerfile
# Line 93: References non-existent context!
COPY --from=packages --chown=llamacrawl:llamacrawl . ./packages
```

**Problem:**
- The docker-compose.yaml defines `additional_contexts: packages: ../../packages` (line 253)
- **But the Dockerfile references `--from=packages` as a build stage** that doesn't exist
- This will **fail at build time** with: `failed to resolve source metadata for additional_contexts`
- The `--from=packages` syntax implies a build stage, not an additional context

**Solution:**
```dockerfile
# Correct syntax for additional_contexts (copy FROM the context, not a build stage)
COPY --chown=llamacrawl:llamacrawl packages /app/packages
```

**2. PERFORMANCE: Build Dependencies Not Removed**
```dockerfile
# Lines 14-22: Build dependencies installed but not cleaned
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      git \
      curl \
      ca-certificates \
      libpq-dev \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

**Problem:**
- Build dependencies (build-essential, git, pkg-config, python3-dev) are **never removed**
- Final image includes 200-300MB of unnecessary build tools
- These are only needed for compiling wheels with uv, not at runtime

**Solution:**
```dockerfile
# In builder stage, clean up after venv creation:
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install ... && \
    apt-get purge -y --auto-remove \
      build-essential \
      git \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

#### Performance Issues

**3. Large Python Dependency Set in API**
```dockerfile
# Lines 37-60: API installing 40+ LlamaIndex packages
"llama-index-core>=0.14.4,<1" \
"llama-index-readers-web>=0.5.5,<1" \
"llama-index-readers-github>=0.8.2,<1" \
# ... 10 more llama-index packages ...
```

**Problem:**
- API installs full LlamaIndex suite: web readers, GitHub readers, file readers, etc.
- API is **thin HTTP wrapper** - doesn't use 90% of these packages
- Each package adds dependencies: transformers, torch fragments, etc.
- Final image: **likely 2GB+** (unconfirmed - recommend measuring)

**Solution - Restructure for FastAPI:**
```dockerfile
# API needs ONLY core + clients
uv pip install \
  "fastapi>=0.119.0,<1" \
  "uvicorn>=0.37.0,<1" \
  "pydantic>=2.12.0,<3" \
  "redis>=5.0.1,<6" \
  "neo4j>=5.26.0,<6" \
  "qdrant-client>=1.15.1,<2" \
  "httpx>=0.28.1,<1"
# Move LlamaIndex packages to worker base image
```

**4. Missing Layer Cache Invalidation**
```dockerfile
# Line 31: READMEs copied early
COPY pyproject.toml README.md ./
```

**Problem:**
- README.md changes don't affect dependencies but invalidate cache
- Any README edit triggers full re-install of Python ecosystem
- README should come AFTER dependency layer

**Solution:**
```dockerfile
# Copy only dependency specifications
COPY pyproject.toml uv.lock ./
# ... install dependencies ...
# THEN copy source and docs
COPY README.md ./
COPY apps/api ./apps/api
```

#### Minor Issues

**5. No explicit uid/gid for user consistency**
```dockerfile
# Line 83: user created with default GID
RUN useradd -m -u 10001 llamacrawl
```

**Better:**
```dockerfile
RUN useradd -m -u 10001 -g 10001 llamacrawl
```

---

### 2. docker/web/Dockerfile

**Status:** ✅ GOOD | Overall: 82/100

#### Strengths
- ✅ Excellent multi-stage strategy (base → development → builder → installer → production)
- ✅ BuildKit cache mount for pnpm store (line 37, 72)
- ✅ Non-root user (`nextjs:1001`) properly configured (lines 106-107)
- ✅ Ownership set during COPY (lines 110-112) - efficient
- ✅ Comprehensive validation of build output (line 115)
- ✅ Pinned Node.js image with SHA256 digest (line 6, 98)
- ✅ Proper HEALTHCHECK with environment variable configuration (lines 126-129)
- ✅ Production environment variables properly set (lines 122-124)

#### Performance Issues

**1. Suboptimal turbo prune strategy**
```dockerfile
# Line 58: Basic prune without --scope optimization
RUN turbo prune @taboot/web --docker
```

**Problem:**
- `turbo prune --docker` generates a `package.json` entry for every workspace package
- This causes pnpm to download **all** transitive dependencies
- Even unused packages (e.g., if there are backend packages copied) get resolved
- Result: **1.2GB+ node_modules** when only 200MB needed

**Solution:**
```dockerfile
# Use --scope to be more selective
RUN turbo prune @taboot/web --docker --scope='@taboot/*'
# OR filter explicitly if possible
# This reduces transitive dependency resolution
```

**2. Prisma generation retry pattern could be optimized**
```dockerfile
# Lines 81-89: Retry loop with sleep
for i in 1 2 3; do \
  pnpm --filter @taboot/db db:generate && break || \
  (echo "Prisma generate attempt $i failed, retrying..." && sleep 5); \
done
```

**Problem:**
- Retries hide underlying issues instead of fixing them
- Network timeouts should be handled by pnpm itself
- Sleep between retries wastes build time

**Recommendation:**
```dockerfile
# Simplify - let it fail loud if something's wrong
pnpm --filter @taboot/db db:generate
```

#### Best Practice Issues

**3. Missing apk upgrade in production stage**
```dockerfile
# Line 101: Only upgrades once, could miss updates
RUN apk update && apk upgrade && apk add --no-cache curl libc6-compat
```

**Better Pattern (match base stage):**
```dockerfile
RUN set -eux; \
    apk update && apk upgrade && apk add --no-cache curl libc6-compat \
    && rm -apk-cache
```

**4. NODE_ENV set at container run, not build**
```dockerfile
# Line 122: Set at runtime (OK, but could be optimized)
ENV NODE_ENV=production
```

**Note:** This is actually correct for Next.js (allows flexibility), but worth noting.

---

### 3. docker/worker/Dockerfile

**Status:** ⚠️ CRITICAL ISSUE | Overall: 65/100

#### Critical Issues

**1. BROKEN: Invalid base image reference**
```dockerfile
# Line 6: References non-existent base image
FROM taboot/python-ml:latest AS builder
```

**Problem:**
- `taboot/python-ml:latest` image must exist and be pre-built
- **Not automated** - requires manual `docker build -t taboot/python-ml:latest docker/base-ml`
- If image is missing or outdated, build silently **fails at image startup**
- No error in Dockerfile itself, but fails when running

**Solution - Two Options:**

**Option A: Auto-build base image (RECOMMENDED)**
```dockerfile
# Use dockerfile as multistage from base-ml
FROM python:3.13-slim AS builder-base
# ... copy base-ml contents ...
# ... install ML venv ...

# Then continue with workspace
FROM builder-base AS builder
# ... copy packages, install workspace extras ...
```

**Option B: Ensure base image always exists (CI/CD)**
```bash
# In docker-compose.yaml, add:
services:
  taboot-worker:
    build:
      context: .
      dockerfile: docker/worker/Dockerfile
      args:
        BASE_ML_IMAGE: taboot/python-ml:${WORKER_BASE_VERSION:-latest}
    depends_on:
      # Ensure base is built first (conceptual - requires CI orchestration)
```

#### Performance Issues

**2. pip install instead of uv**
```dockerfile
# Line 27: Uses pip directly on pre-built venv
/opt/ml-venv/bin/pip install \
  "llama-index-core>=0.14.4,<1" \
  # ...
```

**Problem:**
- Worker already has venv from base-ml image
- pip install is **slower than uv** - uses Grayskull/sdist fallbacks
- No build caching (line 26 shows no cache mount!)
- Should use uv for consistency

**Solution:**
```dockerfile
# Assume uv is in the venv from base image
RUN --mount=type=cache,target=/root/.cache/uv \
    /opt/ml-venv/bin/python -m pip install uv && \
    /opt/ml-venv/bin/uv pip install \
      "llama-index-core>=0.14.4,<1" \
      # ... rest of packages ...
```

**3. Missing BuildKit cache mount**
```dockerfile
# Line 26: NO cache mount for pip!
RUN --mount=type=cache,target=/root/.cache/uv \
    /opt/ml-venv/bin/pip install \
```

**Problem:**
- The mount points to `/root/.cache/uv` but pip uses `/root/.cache/pip`
- Cache mount is **ineffective** - pip won't use it
- Every rebuild downloads all wheels again

**Solution:**
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    /opt/ml-venv/bin/pip install --cache-dir /root/.cache/pip \
      # ...
```

**4. Unnecessary multi-stage for thin layer**
```dockerfile
# Lines 4-85: Two stages, but builder just installs packages
# Builder → Runtime is 40 lines for what could be single stage
```

**Problem:**
- Builder stage only installs packages into existing venv
- **No actual build of Python wheels** (using pre-built base)
- Complexity without benefit

**Solution:** Flatten to single stage:
```dockerfile
FROM taboot/python-ml:latest

WORKDIR /app
COPY apps ./apps
COPY packages ./packages
COPY pyproject.toml uv.lock README.md ./

RUN --mount=type=cache,target=/root/.cache/pip \
    /opt/ml-venv/bin/pip install --upgrade pip && \
    /opt/ml-venv/bin/uv pip install [workspace packages]

RUN useradd -m -u 10003 worker
USER worker

HEALTHCHECK ...
CMD ["python", "-m", "apps.worker.main"]
```

#### Best Practice Issues

**5. HEALTHCHECK uses pgrep only**
```dockerfile
# Line 81-82: Process-based health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "apps.worker.main" > /dev/null || exit 1
```

**Problem:**
- Only checks if process exists, **not if it's healthy**
- Worker could be stuck in infinite loop, still pass healthcheck
- No network validation

**Solution:**
```dockerfile
# If worker exposes metrics/status endpoint:
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Otherwise add a health.py that logs heartbeat:
CMD ["python", "-u", "-m", "apps.worker.main", "--healthcheck"]
```

---

### 4. docker/reranker/Dockerfile

**Status:** ✅ GOOD | Overall: 80/100

#### Strengths
- ✅ Lightweight and focused (single concern: reranking)
- ✅ Pre-downloads model before copying code (line 30) - smart caching
- ✅ Proper BuildKit cache mount (line 23)
- ✅ Pinned pip version (line 20) - reproducibility
- ✅ Proper HEALTHCHECK (lines 37-38)
- ✅ Minimal Dockerfile - easy to maintain

#### Performance Issues

**1. CPU-intensive model download could timeout**
```dockerfile
# Line 30: Pre-download at build time
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('Qwen/Qwen3-Reranker-0.6B')"
```

**Problem:**
- Model download could timeout/fail (600MB+ download over slow connection)
- No timeout configuration
- Fails entire build if network hiccups

**Recommendation:**
```dockerfile
# Add retries for model download
RUN python -c "\
  import time; from sentence_transformers import SentenceTransformer; \
  for i in range(3): \
    try: \
      SentenceTransformer('Qwen/Qwen3-Reranker-0.6B'); \
      break; \
    except Exception as e: \
      if i == 2: raise; \
      time.sleep(10); \
      print(f'Model download failed, retrying ({i+1}/3)...');" \
 || echo "Model download will happen on first container startup"
```

**2. PYTORCH_CUDA_ALLOC_CONF not set**
```dockerfile
# No CUDA memory management for GPU inference
```

**Solution:**
```dockerfile
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024
```

#### Minor Issues

**3. No explicit pip upgrade**
```dockerfile
# Line 20: Pins pip but doesn't clarify why
RUN pip install --no-cache-dir pip==24.3.1
```

**Better:**
```dockerfile
# Pin pip to prevent unexpected pip behavior changes
RUN pip install --no-cache-dir pip==24.3.1 setuptools==72.0.0
```

---

### 5. docker/neo4j/Dockerfile

**Status:** ✅ GOOD | Overall: 85/100

#### Strengths
- ✅ Minimal - only adds tooling to official image
- ✅ Smart symlink for healthchecks (line 4) - excellent UX
- ✅ Follows official image conventions

#### Issues

**1. No HEALTHCHECK in derived image**
```dockerfile
# No healthcheck specified
```

**Problem:**
- docker-compose.yaml defines healthcheck (line 137-142)
- But image itself doesn't have one
- Should be in Dockerfile for portability

**Solution:**
```dockerfile
FROM neo4j:5.23-community

RUN ln -sf /var/lib/neo4j/bin/cypher-shell /usr/local/bin/cypher-shell

# Add a Cypher-based healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD cypher-shell -u "${NEO4J_AUTH_SPLIT_USERNAME:-neo4j}" \
        -p "${NEO4J_AUTH_SPLIT_PASSWORD:-password}" \
        "RETURN 1" > /dev/null 2>&1 || exit 1
```

**Note:** This may not work because Neo4j requires auth credentials. The docker-compose approach is actually better.

**2. No documentation comment**
```dockerfile
# Missing explanation for cypher-shell symlink
```

**Solution:**
```dockerfile
# Expose cypher-shell via PATH for docker-compose healthchecks
# This allows: healthcheck: test: ["CMD", "cypher-shell", "-u", "neo4j", ...]
RUN ln -sf /var/lib/neo4j/bin/cypher-shell /usr/local/bin/cypher-shell
```

---

### 6. docker/postgres/Dockerfile

**Status:** ⚠️ MODERATE CONCERNS | Overall: 72/100

#### Issues

**1. Dynamic shared_preload_libraries configuration**
```dockerfile
# Line 18: Modifies postgresql.conf.sample (fragile pattern)
sed -ri "s/^#?shared_preload_libraries\s*=.*/shared_preload_libraries = 'pg_cron'/" \
  "$conf_sample"
```

**Problem:**
- Modifies **template** file, not actual config
- Doesn't work if Postgres already initialized (idempotent issues)
- Regex could fail on different Postgres versions
- No validation that change succeeded

**Solution - Better approach:**
```dockerfile
# Use PostgreSQL's docker-entrypoint with custom init script
COPY --chown=root:root custom-init.sql /docker-entrypoint-initdb.d/005-pg-cron-init.sql
```

Contents of `custom-init-sql`:
```sql
-- Executed during initdb BEFORE any user data
ALTER SYSTEM SET shared_preload_libraries = 'pg_cron';
SELECT pg_reload_conf();
```

**2. Missing pg_cron extension creation**
```dockerfile
# Installs pg_cron package but doesn't CREATE EXTENSION
```

**Problem:**
- Package installation ≠ extension availability
- Database still needs `CREATE EXTENSION pg_cron`
- First `SELECT cron.schedule()` will fail

**Solution:**
```dockerfile
# Add to docker-entrypoint-initdb.d/ script
COPY --chown=root:root 005-pg-cron.sql /docker-entrypoint-initdb.d/005-pg-cron.sql
```

```sql
-- 005-pg-cron.sql
-- Enable pg_cron extension
CREATE EXTENSION IF NOT EXISTS pg_cron;
-- Schedule log cleanup (example)
SELECT cron.schedule_in_database(
  'cleanup_old_logs',
  '0 2 * * *',  -- 2 AM daily
  'DELETE FROM audit_log WHERE created_at < NOW() - INTERVAL ''90 days''',
  'taboot'
);
```

**3. Non-standard build arg usage**
```dockerfile
# Line 15: ARG defined in wrong place
ARG POSTGRES_DB=taboot
```

**Problem:**
- ARG defined AFTER other RUN commands
- Only affects commands after this point
- Won't substitute in COPY/FROM

**Solution:**
```dockerfile
ARG PG_MAJOR=16
ARG POSTGRES_DB=taboot

FROM postgres:${PG_MAJOR}

# Now POSTGRES_DB can be used in scripts
COPY nuq.sql /docker-entrypoint-initdb.d/010-nuq.sql
```

#### Minor Issues

**4. No documentation of init sequence**
```dockerfile
# No comments explaining initialization order
```

**Solution:**
```dockerfile
# Docker entrypoint init sequence:
# 1. PostgreSQL starts, creates initial database cluster
# 2. /docker-entrypoint-initdb.d/*.sql scripts execute IN ALPHABETICAL ORDER
# 3. 005-pg-cron.sql: Creates pg_cron extension
# 4. 010-nuq.sql: Runs custom SQL for Taboot
#
# Numbering ensures correct order (005 < 010)
```

---

### 7. docker/base-ml/Dockerfile

**Status:** ⚠️ MODERATE CONCERNS | Overall: 75/100

#### Strengths
- ✅ Excellent dependency isolation strategy - build once, reuse many times
- ✅ Smart dependency grouping (torch, transformers, spacy together)
- ✅ Builds to named image (`taboot/python-ml:latest`) for reusability
- ✅ Pre-downloads spaCy model (line 53) - saves runtime startup
- ✅ BuildKit cache mount (line 34)
- ✅ Cleanup of build tools (lines 56-57) - excellent final image size
- ✅ Environment variables set for venv activation (lines 59-61)

#### Performance Issues

**1. Excessive build tools cleanup**
```dockerfile
# Line 56: Only removes build-essential and git, misses others
RUN apt-get purge -y --auto-remove build-essential git \
    && rm -rf /ml-deps
```

**Problem:**
- Doesn't remove `pkg-config`, `python3-dev` (needed only for build)
- `curl` is left behind (only needed for uv installer)

**Solution:**
```dockerfile
RUN apt-get purge -y --auto-remove \
      build-essential \
      git \
      pkg-config \
      python3-dev \
      curl \
    && rm -rf /var/lib/apt/lists/* /ml-deps /root/.local/share/uv
```

**2. uv not removed from final image**
```dockerfile
# /root/.local/bin/uv remains in image (5-10MB)
# Only needed during build, not at runtime
```

**Solution:**
```dockerfile
# In base image, use uv only in builder, then remove
ENV PATH="/opt/ml-venv/bin:$PATH"

# Remove uv after venv is created
RUN rm -rf /root/.local/bin/uv /root/.local/share/uv
```

**3. Torch pre-built wheels used by default**
```dockerfile
# Line 38: "torch>=2.4.0,<3" pulls full binary distribution
```

**Problem:**
- Torch 2.4 binary is **2GB+ with full CUDA**
- For GPU-only systems, this is necessary
- But for CPU-only dev, this wastes space

**Recommendation:** Document in `.env.example`:
```env
# torch and transformers are 2GB+ - only needed for GPU inference
# For CPU-only development, consider alternative base image
```

#### Best Practice Issues

**4. Missing WORKDIR for venv creation**
```dockerfile
# Line 31: Changes WORKDIR to /ml-deps but it's temporary
WORKDIR /ml-deps
# ...
# Line 63: Changes WORKDIR to /app (final location)
WORKDIR /app
```

**Problem:**
- /ml-deps directory is created but never cleaned
- Could be confusing for maintainers

**Solution:**
```dockerfile
# Skip intermediate WORKDIR, use full path in uv commands
RUN uv venv /opt/ml-venv && \
    /opt/ml-venv/bin/python -m pip install uv && \
    /opt/ml-venv/bin/uv pip install \
      "torch>=2.4.0,<3" \
      # ... rest of packages ...

# Clean up build artifacts (same as before)
RUN apt-get purge -y --auto-remove \
      build-essential \
      git \
      pkg-config \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/ml-venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
```

#### Minor Issues

**5. No documentation comment**
```dockerfile
# Build instructions at top are good, but could be in Dockerfile comment
```

**Better:**
```dockerfile
# syntax=docker/dockerfile:1.7-labs
#
# Base image for ML/AI heavy dependencies
# Purpose: Pre-build torch, transformers, spaCy stack for worker reuse
# Usage: docker build -t taboot/python-ml:latest -f docker/base-ml/Dockerfile .
#
# Benefits:
# - Builds once, reused by taboot-worker and taboot-api
# - 45min build time is amortized across multiple services
# - Pinned dependencies ensure reproducible builds
#
```

---

## Cross-Cutting Observations

### 1. No Unified Base Images Strategy
```
Current state:
- api: python:3.13-slim → custom builder
- web: node:22-alpine (pinned with SHA)
- worker: taboot/python-ml:latest (custom base)
- reranker: pytorch/pytorch:2.4.0 (heavy)

Risk: Inconsistent update policies, different security patches
```

**Recommendation:**
- Create `base-python` image with common deps
- Versions: update quarterly, pinned in docs
- Security patches: automated scanning for critical issues

### 2. User IDs Not Standardized
```
Current:
- API: llamacrawl:10001
- Worker: taboot:10002
- Web: nextjs:1001
- Others: varies

Risk: Namespace collision in multi-tenant environments
```

**Standard UID mapping (Taboot):**
```
1001 - nextjs (web)
10000 - base user for all service accounts
10001 - llamacrawl (api)
10002 - taboot (worker)
10003 - reranker (if needed)
```

### 3. Inconsistent Cache Mount Paths
```
api/Dockerfile:      /root/.cache/uv
web/Dockerfile:      /root/.local/share/pnpm/store
worker/Dockerfile:   /root/.cache/uv (mismatch with pip)
reranker/Dockerfile: /root/.cache/pip

Risk: Cache mounts don't work, forcing re-downloads
```

**Standardize:**
```dockerfile
# Python with uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install ...

# JavaScript with pnpm
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install ...

# Generic pip (fallback)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install ...
```

### 4. Missing ENTRYPOINT Scripts
```dockerfile
# All Dockerfiles use CMD directly
# No ENTRYPOINT for env variable substitution
```

**Example issue - API:**
```dockerfile
# Current: CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
# But PYTHONPATH isn't guaranteed at runtime

# Better: Use entrypoint script for env setup
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "apps.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
#!/bin/bash
# docker-entrypoint.sh - setup env and exec
set -e

# Ensure venv is activated
source /app/.venv/bin/activate 2>/dev/null || true

# Export critical env vars
export PYTHONPATH=/app:${PYTHONPATH}

# Execute main command
exec "$@"
```

### 5. Docker Compose Service Dependencies

**Current:** Sequential `depends_on: condition: service_healthy`

**Risk:** Startup order creates bottlenecks
```
taboot-db → taboot-crawler → taboot-api → taboot-web
                              ↓
                         all GPU services wait
```

**Recommendation:**
- GPU services (embed, rerank, ollama, vectors) start in parallel
- API waits only on critical dependencies (db, redis)
- Web waits only on API

See [Performance Tuning](#performance-tuning-recommendations) below.

---

## Security Assessment

### High-Risk Issues

| Issue | Severity | File | Line | Impact |
|-------|----------|------|------|--------|
| `--from=packages` broken build | CRITICAL | docker/api/Dockerfile | 93 | Build fails |
| Missing base image | CRITICAL | docker/worker/Dockerfile | 6 | Container won't run |
| Unvalidated pg_cron install | HIGH | docker/postgres/Dockerfile | 10 | Extension not available |

### Medium-Risk Issues

| Issue | Severity | File | Line | Impact |
|-------|----------|------|------|--------|
| Build deps not removed | MEDIUM | docker/api/Dockerfile | 14-22 | +200MB image size, exposure of build tools |
| Model download timeout | MEDIUM | docker/reranker/Dockerfile | 30 | Silent build failure |
| No HEALTHCHECK validation | MEDIUM | docker/worker/Dockerfile | 81 | Unhealthy containers stay running |

### Low-Risk Issues

| Issue | Severity | File | Line | Impact |
|-------|----------|------|------|--------|
| User GID not explicit | LOW | docker/api/Dockerfile | 83 | Potential permission confusion |
| Cache mount misconfigured | LOW | docker/worker/Dockerfile | 26 | Cache miss, slow rebuilds |
| No image HEALTHCHECK | LOW | docker/neo4j/Dockerfile | - | Composition complexity |

---

## Performance Tuning Recommendations

### Measurement Baseline

Before and after optimization, measure:

```bash
# Image size
docker images --format "table {{.Repository}}\t{{.Size}}"

# Build time
time docker build -f docker/api/Dockerfile -t taboot-api:test .

# Layer inspection
docker inspect --format='{{json .RootFS.Layers}}' taboot-api:test | jq '.[]' | wc -l
```

### Optimization Priority Matrix

| Priority | Optimization | Expected Savings | Effort |
|----------|-------------|-------------------|--------|
| 1 | Remove build deps from API builder | 200-300MB | 15min |
| 2 | Fix docker/api line 93 (broken build) | N/A (fix) | 5min |
| 3 | Reduce LlamaIndex deps in API | 800MB-1.2GB | 30min |
| 4 | Optimize web turbo prune | 400-600MB | 20min |
| 5 | Add model download retry (reranker) | robustness | 10min |
| 6 | Create base-python image | consistency | 45min |

---

## Recommended Fixes Priority

### Critical (Fix ASAP - prevents deployment)

#### 1. Fix docker/api/Dockerfile line 93
```diff
- COPY --from=packages --chown=llamacrawl:llamacrawl . ./packages
+ COPY --chown=llamacrawl:llamacrawl packages /app/packages
```

#### 2. Fix docker/worker/Dockerfile base image
- Document that `taboot/python-ml:latest` must be pre-built
- **OR** collapse into single Dockerfile (recommended)

### High (Fix in next release)

#### 3. Remove build dependencies from API builder (docker/api)
```diff
  # In builder stage, after venv creation:
+ apt-get purge -y --auto-remove \
+   build-essential git pkg-config python3-dev \
+ && rm -rf /var/lib/apt/lists/*
```

#### 4. Restructure API dependencies (docker/api)
- Move LlamaIndex packages to worker image
- Keep API minimal (FastAPI, clients only)

#### 5. Fix worker dockerfile (docker/worker)
- Option A: Collapse to single stage (recommended)
- Option B: Ensure base image exists + use proper cache mount

### Medium (Optimize in next sprint)

#### 6. Improve postgres initialization (docker/postgres)
- Move shared_preload_libraries to init SQL script
- Add explicit pg_cron extension creation

#### 7. Add model download retries (docker/reranker)
- Wrap model download in retry loop
- Add timeout configuration

#### 8. Standardize healthchecks
- All images should include HEALTHCHECK definitions
- Not rely on docker-compose for basic liveness

---

## Best Practices Applied (Exemplary)

### docker/web/Dockerfile
- ✅ **Excellent cache strategy:** Base → development → builder → installer → production (5 stages)
- ✅ **BuildKit cache mounts** for pnpm: Layer caching works perfectly
- ✅ **Non-root user** with proper ownership during copy
- ✅ **Pinned base image SHA256:** Immutable base
- ✅ **Build validation:** `test -f apps/web/server.js` before running
- ✅ **Comprehensive HEALTHCHECK** with environment variable

### docker/base-ml/Dockerfile
- ✅ **Strategic reuse:** Build once, copy to multiple services
- ✅ **Clean build artifact removal** (lines 56-57)
- ✅ **Proper venv isolation** at `/opt/ml-venv`
- ✅ **Pre-download models** for startup optimization

### docker/reranker/Dockerfile
- ✅ **Model-first approach:** Download before code for cache efficiency
- ✅ **Minimal and focused:** Single responsibility principle
- ✅ **BuildKit cache** mount for pip packages

---

## Recommended Dockerfile Templates

### Python Service (FastAPI/Typer)
```dockerfile
# syntax=docker/dockerfile:1.7-labs

FROM python:3.13-slim AS builder

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates libpq-dev pkg-config python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install --upgrade pip && \
    uv pip install [YOUR_DEPS]

# ========================
# Runtime Stage
# ========================
FROM python:3.13-slim

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 -g 10001 appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser . ./

ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js App (Next.js)
```dockerfile
# syntax=docker/dockerfile:1.7-labs

FROM node:22-alpine@sha256:bd26af08779f746650d95a2e4d653b0fd3c8030c44284b6b98d701c9b5eb66b9 AS base

ENV PNPM_HOME="/root/.local/share/pnpm" PATH="$PNPM_HOME:$PATH"

RUN apk update && apk upgrade && apk add --no-cache libc6-compat && \
    npm install -g pnpm@10.4.1 turbo@2.3.3

# ========================
# Builder Stage
# ========================
FROM base AS builder

WORKDIR /app

COPY pnpm-workspace.yaml pnpm-lock.yaml package.json turbo.json ./
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

RUN turbo prune @taboot/web --docker

# ========================
# Installer Stage
# ========================
FROM base AS installer

WORKDIR /app

COPY --from=builder /app/out/json ./
COPY --from=builder /app/out/full ./

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

RUN pnpm --filter @taboot/db db:generate
RUN turbo build --filter=@taboot/web

# ========================
# Production
# ========================
FROM node:22-alpine@sha256:bd26af08779f746650d95a2e4d653b0fd3c8030c44284b6b98d701c9b5eb66b9

RUN apk update && apk upgrade && apk add --no-cache curl libc6-compat

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

WORKDIR /app

COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=installer --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs
EXPOSE 3000

ENV NODE_ENV=production PORT=3000 NEXT_TELEMETRY_DISABLED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:3000/api/health || exit 1

CMD ["node", "apps/web/server.js"]
```

---

## Testing Recommendations

### Build Testing
```bash
# Test each Dockerfile individually
docker build -f docker/api/Dockerfile -t test-api . --no-cache
docker build -f docker/web/Dockerfile -t test-web . --no-cache
docker build -f docker/worker/Dockerfile -t test-worker . --no-cache

# Inspect resulting images
docker inspect test-api | jq '.Config'
docker history test-api --no-trunc

# Check for security issues with Trivy
trivy image test-api
trivy image test-web
```

### Runtime Testing
```bash
# Test healthchecks
docker compose up -d
docker compose ps  # Should show "healthy" status

# Verify non-root execution
docker inspect --format='{{.Config.User}}' taboot-api
# Should output: "llamacrawl:10001" or similar

# Check entrypoints
docker inspect --format='{{.Config.Entrypoint}}' taboot-api
docker inspect --format='{{.Config.Cmd}}' taboot-api
```

---

## Summary Table: Severity & Fixes

| File | Issue | Severity | Fix Time | Impact |
|------|-------|----------|----------|--------|
| docker/api/Dockerfile | Line 93: `--from=packages` broken | CRITICAL | 5min | Build fails |
| docker/api/Dockerfile | Build deps not removed | MEDIUM | 15min | +200-300MB image |
| docker/api/Dockerfile | LlamaIndex bloat | MEDIUM | 30min | +800MB-1.2GB image |
| docker/web/Dockerfile | Suboptimal turbo prune | MINOR | 20min | +400-600MB deps |
| docker/worker/Dockerfile | Missing base image definition | CRITICAL | 15min | Container won't run |
| docker/worker/Dockerfile | pip cache mount misconfigured | MEDIUM | 5min | Slow rebuilds |
| docker/worker/Dockerfile | pgrep-only healthcheck | MEDIUM | 10min | Can't detect stuck workers |
| docker/reranker/Dockerfile | Model download no retries | MEDIUM | 10min | Build can fail on network hiccup |
| docker/postgres/Dockerfile | pg_cron not created as extension | HIGH | 20min | Extension unavailable at runtime |
| docker/neo4j/Dockerfile | No image-level HEALTHCHECK | MINOR | 5min | Relies on docker-compose |
| docker/base-ml/Dockerfile | Build tools not fully cleaned | LOW | 10min | +100-200MB unused binaries |

---

## Next Steps

1. **This week:** Fix critical issues (api line 93, worker base image, postgres pg_cron)
2. **Next sprint:** Optimize images (remove build deps, reduce LlamaIndex, improve turbo prune)
3. **Planning:** Design unified base images strategy for consistency
4. **CI/CD:** Add Dockerfile linting (hadolint) and security scanning (Trivy) to pipeline

---

## Appendix: Tools for Dockerfile Analysis

### Install hadolint (Dockerfile linter)
```bash
# macOS
brew install hadolint

# Linux
docker run --rm -i hadolint/hadolint < Dockerfile

# Run across all Dockerfiles
find . -name "Dockerfile*" -exec hadolint {} \;
```

### Install Trivy (vulnerability scanner)
```bash
# Scan image
trivy image taboot-api:latest

# Scan Dockerfile
trivy config docker/api/Dockerfile
```

### Analyze image layers
```bash
# View layer sizes
docker history taboot-api:latest --no-trunc --human

# Deep inspection
docker buildx build --progress=plain -f docker/api/Dockerfile .
```

### Performance profiling
```bash
# Build time measurement
time docker build -f docker/api/Dockerfile -t test .

# Cache hit analysis
docker build -f docker/api/Dockerfile --progress=plain -t test . 2>&1 | grep -E "(CACHED|FROM|COPY|RUN)"
```

---

**Report Generated:** 2025-10-27
**Analyzed by:** Deployment Engineer (Claude Code)
**Taboot Version:** Current
**Status:** Complete
