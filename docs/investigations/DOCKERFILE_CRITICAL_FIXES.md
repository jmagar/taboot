# Critical Dockerfile Fixes - Immediate Action Items

**Priority:** URGENT - These prevent successful deployment

---

## 1. docker/api/Dockerfile - Line 93: Broken Build Context

### Current Code (BROKEN)
```dockerfile
# Line 93: References non-existent build stage
COPY --from=packages --chown=llamacrawl:llamacrawl . ./packages
```

### Problem
- Docker compose defines `additional_contexts: packages: ../../packages`
- Dockerfile incorrectly uses `--from=packages` (build stage syntax)
- **Build fails with:** `failed to resolve source metadata for additional_contexts`

### Fix
```dockerfile
# CORRECT: Copy FROM additional_context (not a build stage)
COPY --chown=llamacrawl:llamacrawl packages /app/packages
```

### Test After Fix
```bash
docker build -f docker/api/Dockerfile \
  --build-context packages=./packages \
  -t test-api:fix .
# Should succeed without "failed to resolve source metadata" error
```

---

## 2. docker/worker/Dockerfile - Line 6: Missing Base Image

### Current Code (BROKEN)
```dockerfile
# Line 6: References image that may not exist
FROM taboot/python-ml:latest AS builder
```

### Problem
- `taboot/python-ml:latest` is not automatically built
- Image may not exist, causing silent failures
- No automation to ensure base image is current

### Fix Option A: Auto-build (RECOMMENDED for single developers)
Collapse multi-stage into single Dockerfile:

```dockerfile
# syntax=docker/dockerfile:1.7-labs

# Use official Python, not custom base
FROM python:3.13-slim AS base

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

ARG DEBIAN_FRONTEND=noninteractive

# Install ML dependencies directly
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates libpq-dev pkg-config python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# Copy ML dependency specs
COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages

# Install ML venv with all dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/ml-venv && \
    /opt/ml-venv/bin/python -m pip install --upgrade pip && \
    /opt/ml-venv/bin/uv pip install \
      "torch>=2.4.0,<3" \
      "transformers>=4.44.0,<5" \
      "spacy>=3.8.1,<4" \
      "llama-index-core>=0.14.4,<1" \
      # ... rest of dependencies ...

# Download spaCy model
RUN /opt/ml-venv/bin/python -m spacy download en_core_web_md

# Cleanup build tools
RUN apt-get purge -y --auto-remove \
      build-essential git pkg-config python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 10002 -g 10002 taboot

ENV PATH="/opt/ml-venv/bin:$PATH"

USER taboot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "apps.worker.main" > /dev/null || exit 1

CMD ["python", "-m", "apps.worker.main"]
```

### Fix Option B: Keep base image (for multi-stage teams)
Add documentation and CI/CD step:

```dockerfile
# docker/worker/Dockerfile (updated)
# IMPORTANT: This image requires taboot/python-ml:latest to be pre-built
# Build with: docker build -t taboot/python-ml:latest -f docker/base-ml/Dockerfile .
# BEFORE building worker image

FROM taboot/python-ml:latest

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY packages ./packages

# Install workspace packages into existing ML venv
RUN --mount=type=cache,target=/root/.cache/pip \
    /opt/ml-venv/bin/python -m pip install --upgrade pip && \
    /opt/ml-venv/bin/python -m pip install \
      "llama-index-core>=0.14.4,<1" \
      "qdrant-client>=1.15.1,<2"

RUN useradd -m -u 10002 -g 10002 taboot
USER taboot

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "apps.worker.main" > /dev/null || exit 1

CMD ["python", "-m", "apps.worker.main"]
```

**Then in CI/CD (GitHub Actions example):**
```yaml
- name: Build base ML image
  run: docker build -t taboot/python-ml:latest -f docker/base-ml/Dockerfile .

- name: Build worker image
  run: docker build -f docker/worker/Dockerfile -t taboot-worker:latest .
```

### Test After Fix
```bash
# Option A: Collapsed single Dockerfile
docker build -f docker/worker/Dockerfile -t test-worker:fix .
docker run test-worker:fix python -c "import torch; print(torch.__version__)"

# Option B: Base image approach
docker build -t taboot/python-ml:latest -f docker/base-ml/Dockerfile .
docker build -f docker/worker/Dockerfile -t test-worker:fix .
```

---

## 3. docker/postgres/Dockerfile - Missing pg_cron Extension

### Current Code (INCOMPLETE)
```dockerfile
# Lines 9-10: Installs package but doesn't create extension
apt-get install -y --no-install-recommends \
    postgresql-${PG_MAJOR}-cron;

# Lines 16-19: Modifies template (fragile)
sed -ri "s/^#?shared_preload_libraries\s*=.*/shared_preload_libraries = 'pg_cron'/" \
  "$conf_sample"
```

### Problem
1. Package installed ≠ extension available
2. Database still needs `CREATE EXTENSION pg_cron`
3. First `SELECT cron.schedule()` call will fail with "extension not found"

### Fix
Create init SQL script:

**File: docker/postgres/005-pg-cron.sql**
```sql
-- Enable pg_cron extension (requires postgresql-16-cron package installed)
-- This runs AFTER initial database creation
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Verify extension is available
SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'
  OR (SELECT COUNT(*) FROM pg_proc WHERE proname = 'cron.schedule') > 0;
```

**File: docker/postgres/Dockerfile (UPDATED)**
```dockerfile
ARG PG_MAJOR=16
FROM postgres:${PG_MAJOR}

# Install pg_cron extension
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        postgresql-${PG_MAJOR}-cron; \
    rm -rf /var/lib/apt/lists/*

# Enable shared_preload_libraries via custom init script
# Note: This runs DURING first database initialization
COPY 005-pg-cron.sql /docker-entrypoint-initdb.d/005-pg-cron.sql

# Copy main schema
COPY nuq.sql /docker-entrypoint-initdb.d/010-nuq.sql
```

**Update PostgreSQL conf via environment (SIMPLER APPROACH):**
```dockerfile
# In docker-compose.yaml, add to taboot-db environment:
environment:
  POSTGRES_INIT_ARGS: >
    -c shared_preload_libraries=pg_cron
```

**OR in Dockerfile (most reliable):**
```dockerfile
ARG PG_MAJOR=16
FROM postgres:${PG_MAJOR}

# Install pg_cron
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-${PG_MAJOR}-cron; \
    rm -rf /var/lib/apt/lists/*

# Create extension during init
COPY 005-pg-cron.sql /docker-entrypoint-initdb.d/005-pg-cron.sql
COPY nuq.sql /docker-entrypoint-initdb.d/010-nuq.sql
```

### Test After Fix
```bash
docker compose up taboot-db -d
docker compose exec taboot-db psql -U taboot -d taboot -c "SELECT * FROM pg_extension WHERE extname = 'pg_cron';"
# Should return: (1 row with pg_cron extension)

# Try to use pg_cron
docker compose exec taboot-db psql -U taboot -d taboot -c \
  "SELECT cron.schedule('test', '0 * * * *', 'SELECT 1');"
# Should succeed (not error: "pg_cron is not installed")
```

---

## Secondary High-Priority Fixes

### 4. docker/api/Dockerfile - Remove Build Dependencies

**Problem:** Build tools (build-essential, git, etc.) left in final image (+200-300MB)

**Current (Lines 14-22):**
```dockerfile
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

**Fix - In builder stage, cleanup after venv:**
```dockerfile
# ============== BUILDER STAGE ==============
FROM python:3.13-slim AS builder

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git curl ca-certificates libpq-dev pkg-config python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv pip install [DEPS] && \
    # CLEANUP: Remove build tools (not needed in runtime stage)
    apt-get purge -y --auto-remove \
      build-essential git pkg-config python3-dev \
    && rm -rf /var/lib/apt/lists/* /root/.local/share/uv

# ============== RUNTIME STAGE ==============
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Runtime deps only (smaller set)
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 10001 -g 10001 llamacrawl

WORKDIR /app

# Copy clean venv from builder
COPY --from=builder --chown=llamacrawl:llamacrawl /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# ... rest of runtime stage ...
```

**Verify the fix:**
```bash
# Before cleanup
docker build -f docker/api/Dockerfile -t api:before . --progress=plain
docker images api:before --format "{{.Size}}"

# After cleanup
docker build -f docker/api/Dockerfile -t api:after . --progress=plain
docker images api:after --format "{{.Size}}"

# Should see 200-300MB size reduction
```

---

## Verification Checklist

After applying all fixes, verify:

```bash
# 1. API Dockerfile builds
docker build -f docker/api/Dockerfile \
  --build-context packages=./packages \
  -t test-api:v1 . && echo "✓ API builds"

# 2. Worker Dockerfile builds (Option A: collapsed)
docker build -f docker/worker/Dockerfile \
  -t test-worker:v1 . && echo "✓ Worker builds"

# 3. Postgres has pg_cron extension
docker compose up taboot-db -d
docker compose exec taboot-db psql -U taboot -d taboot \
  -c "SELECT extname FROM pg_extension WHERE extname = 'pg_cron';" \
  && echo "✓ pg_cron extension available"

# 4. Test healthchecks pass
docker compose up -d
docker compose ps | grep -E "healthy|unhealthy"
# All services should show "healthy"

# 5. API accepts requests
curl http://localhost:4209/health | jq .
# Should return: {"status":"ok"} or similar

# 6. Worker healthcheck works
docker exec taboot-worker pgrep -f "apps.worker.main"
# Should return process ID (not empty)
```

---

## Rollback Plan

If fixes cause issues:

```bash
# 1. Revert Dockerfile changes
git checkout docker/api/Dockerfile docker/worker/Dockerfile docker/postgres/Dockerfile

# 2. Rebuild with original images
docker-compose down
docker system prune -a
docker-compose up -d

# 3. Verify original state
docker compose ps
```

---

## Implementation Order

1. **First:** Fix docker/api/Dockerfile line 93 (CRITICAL - prevents API build)
2. **Second:** Fix docker/worker/Dockerfile (CRITICAL - prevents worker build)
3. **Third:** Fix docker/postgres/Dockerfile pg_cron (HIGH - breaks database features)
4. **Fourth:** Clean build deps from docker/api/Dockerfile (IMPORTANT - performance)

Estimated total fix time: **1-2 hours** (including testing)

---

## References

- Full analysis: `/home/jmagar/code/taboot/docs/DOCKERFILE_AUDIT.md`
- Docker BuildKit docs: https://docs.docker.com/build/buildkit/
- Docker compose additional_contexts: https://docs.docker.com/compose/compose-file/build/#additional_contexts
- PostgreSQL pg_cron extension: https://github.com/citusdata/pg_cron
