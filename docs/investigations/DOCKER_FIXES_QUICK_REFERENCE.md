# Docker Compose Critical Fixes - Quick Reference

**Status:** 3 Critical Issues Found
**Time to Fix:** ~5-10 minutes
**Testing Time:** ~2-3 minutes

---

## Fix #1: API Service Build Context Path

**File:** `docker-compose.yaml`
**Line:** 252

**Current (BROKEN):**
```yaml
taboot-api:
  build:
    context: apps/api
    dockerfile: ../../docker/api/Dockerfile
    additional_contexts:
      packages: packages  # ← WRONG: looks for apps/api/packages/
```

**Fixed:**
```yaml
taboot-api:
  build:
    context: apps/api
    dockerfile: ../../docker/api/Dockerfile
    additional_contexts:
      packages: ../../packages  # ← CORRECT: reaches to project root
```

**Change:** `packages` → `../../packages`

---

## Fix #2: Web Service Build Context Path

**File:** `docker-compose.yaml`
**Line:** 288

**Current (BROKEN):**
```yaml
taboot-web:
  build:
    context: apps/web
    dockerfile: ../../docker/web/Dockerfile
    additional_contexts:
      packages-ts: packages-ts  # ← WRONG: looks for apps/web/packages-ts/
```

**Fixed:**
```yaml
taboot-web:
  build:
    context: apps/web
    dockerfile: ../../docker/web/Dockerfile
    additional_contexts:
      packages-ts: ../../packages-ts  # ← CORRECT: reaches to project root
```

**Change:** `packages-ts` → `../../packages-ts`

---

## Fix #3: Add Missing Base ML Service

**File:** `docker-compose.yaml`
**Location:** Insert before `taboot-worker` (around line 310)

**Add this entire service:**
```yaml
taboot-base-ml:
  <<: *common-base
  build:
    context: .
    dockerfile: docker/base-ml/Dockerfile
  image: taboot/python-ml:latest
  container_name: taboot-base-ml
  healthcheck:
    test: ["CMD", "python", "-c", "import torch; print(torch.__version__)"]
    interval: 60s
    timeout: 30s
    retries: 3
    start_period: 120s
```

**Then modify taboot-worker service to add dependency:**

Find the `taboot-worker` `depends_on` section (around line 322) and add at the beginning:

```yaml
  taboot-worker:
    <<: *common-base
    build:
      context: .
      dockerfile: docker/worker/Dockerfile
      additional_contexts:
        packages: ./packages
    container_name: taboot-worker
    env_file:
      - .env
    volumes:
      - spacy-models:/root/.spacy/data
    depends_on:
      taboot-base-ml:           # ← ADD THIS LINE
        condition: service_healthy
      taboot-cache:
        condition: service_healthy
      taboot-vectors:
        condition: service_healthy
      # ... rest of deps ...
```

**Key point:** `taboot-base-ml` must be listed FIRST in dependencies and use `service_healthy` condition.

---

## Fix #4: Document Port Conflict (Optional but Recommended)

**File:** `.env.example`
**Line:** 44

**Add comment before PLAYWRIGHT_PORT:**
```bash
# ============================================================
# CRITICAL: Playwright and Web services use different ports!
# ============================================================
# Playwright service (browser automation)
PLAYWRIGHT_PORT="4213"

# Web dashboard (Next.js app) - MUST DIFFER FROM PLAYWRIGHT_PORT!
TABOOT_WEB_PORT="4211"
```

This is already set correctly in the .env.example but needs better documentation.

---

## Verification Steps

After making the 3 fixes above:

```bash
# 1. Validate syntax
docker-compose config > /dev/null && echo "✓ Syntax valid" || echo "✗ Syntax error"

# 2. Build all services (this tests the additional_contexts fixes)
docker-compose build 2>&1 | tail -20

# 3. Check for build errors
# Look for messages like:
#   ✓ "Successfully tagged taboot/python-ml:latest"
#   ✓ "Successfully tagged taboot/rerank:latest"
#   ✓ "Successfully built xxxxxxxx"

# 4. Dry-run the compose file
docker-compose up --dry-run 2>&1 | grep -i error || echo "✓ No errors"

# 5. List services (should show all 12 + base-ml)
docker-compose config --services | wc -l  # Should be 13
```

---

## What Each Fix Does

| Fix | What It Fixes | Impact |
|-----|---------------|--------|
| #1: API context path | Broken COPY --from=packages in docker/api/Dockerfile | API service fails to build or missing dependencies |
| #2: Web context path | Broken COPY --from=packages-ts in docker/web/Dockerfile | Web service fails to build or missing dependencies |
| #3: Base ML service | Worker can't find taboot/python-ml:latest image | Worker service fails to start on first run |
| #4: Documentation | Users unclear about port requirements | Setup confusion, port conflict errors |

---

## Testing After Fixes

```bash
# Full start sequence (takes ~2-3 minutes)
docker-compose up -d

# Wait for all services to be healthy
watch -n 5 docker-compose ps

# Expected output when all healthy:
# STATUS: all showing "healthy" or "Up X seconds"

# Quick health checks
curl http://localhost:4209/health  # API
curl http://localhost:4211/api/health  # Web (note: port 4210, not 4211!)

# Verify ports are listening correctly
lsof -i -P -n | grep -E "(LISTEN|ESTABLISHED)" | grep docker
```

---

## Common Issues After Fixes

### Issue: "Image taboot/python-ml:latest not found"
**Cause:** Fix #3 not applied
**Solution:** Add taboot-base-ml service as shown in Fix #3

### Issue: "Address already in use" on port 4211
**Cause:** Fix #4 not set correctly in .env
**Solution:** Ensure TABOOT_WEB_PORT is set to 4210 (not 4211)

### Issue: "COPY --from=packages" fails during build
**Cause:** Fix #1 or #2 not applied correctly
**Solution:** Check the `additional_contexts` paths end with `../../packages` or `../../packages-ts`

---

## File Change Summary

```diff
# docker-compose.yaml - 3 changes

1. Line 252 (taboot-api):
-        packages: packages
+        packages: ../../packages

2. Line 288 (taboot-web):
-        packages-ts: packages-ts
+        packages-ts: ../../packages-ts

3. Before line 310 (add taboot-base-ml service):
+  taboot-base-ml:
+    <<: *common-base
+    build:
+      context: .
+      dockerfile: docker/base-ml/Dockerfile
+    image: taboot/python-ml:latest
+    container_name: taboot-base-ml
+    healthcheck:
+      test: ["CMD", "python", "-c", "import torch; print(torch.__version__)"]
+      interval: 60s
+      timeout: 30s
+      retries: 3
+      start_period: 120s

4. Line 322+ (taboot-worker):
   Add to depends_on:
+      taboot-base-ml:
+        condition: service_healthy
```

---

## Rollback (If Something Goes Wrong)

```bash
# Restore original docker-compose.yaml
git checkout docker-compose.yaml

# Remove broken images
docker rmi taboot/python-ml:latest taboot/rerank:latest taboot/postgres:16
```

---

## Quick Start After Fixes

```bash
# 1. Apply fixes above to docker-compose.yaml

# 2. Copy .env template
cp .env.example .env

# 3. Build everything
docker-compose build

# 4. Start all services
docker-compose up -d

# 5. Check status
docker-compose ps

# 6. Wait for healthy (~1-2 min)
docker-compose ps --no-trunc

# 7. Test endpoints
curl http://localhost:4209/health
curl http://localhost:4211/api/health
```

---

**Total time to implement:** 5-10 minutes (including re-reading the changes)
**Total time to test:** 2-3 minutes
**Risk level:** 🟢 LOW (YAML-only changes, no logic changes)
