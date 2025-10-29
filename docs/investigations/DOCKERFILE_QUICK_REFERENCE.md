# Dockerfile Audit - Quick Reference Card

## One-Page Summary

### Critical Issues (Fix ASAP)
| File | Line | Issue | Fix |
|------|------|-------|-----|
| `docker/api/Dockerfile` | 93 | `--from=packages` broken | `COPY packages` |
| `docker/worker/Dockerfile` | 6 | Missing base image | Collapse or auto-build |
| `docker/postgres/Dockerfile` | - | pg_cron not created | Add init SQL script |

### Image Size Breakdown
```
Current Estimated Sizes:
  api:       1.5-2.0 GB  (too large: build deps + deps bloat)
  web:       600-800 MB  (good)
  worker:    2.0-2.5 GB  (expected: ML stack)
  reranker:  8-10 GB     (expected: pytorch)

After Fixes:
  api:       600-800 MB  (save 900 MB-1.2 GB total)
  web:       600-800 MB  (no change)
  worker:    2.0-2.5 GB  (no change)
  reranker:  8-10 GB     (no change)
```

### Fix Checklist
```
Week 1 (40 min - CRITICAL):
  □ docker/api line 93: Fix broken build context (5 min)
  □ docker/worker line 6: Fix base image (15 min)
  □ docker/postgres: Add pg_cron extension (20 min)
  □ Test: docker compose up

Week 2 (90 min - HIGH PRIORITY):
  □ docker/api: Remove build deps (15 min)
  □ docker/api: Trim LlamaIndex (30 min)
  □ docker/worker: Fix cache mount (5 min)
  □ docker/reranker: Add retry logic (10 min)
  □ docker/web: Optimize turbo prune (20 min)
  □ docker/base-ml: Clean build tools (10 min)
  □ Measure image sizes

Backlog (Optional):
  □ Standardize healthchecks
  □ Add ENTRYPOINT scripts
  □ Create base-python image
  □ Add hadolint linting
  □ Add Trivy scanning
```

### Files Reference
| Document | Purpose | Use When |
|----------|---------|----------|
| **DOCKERFILE_SUMMARY.txt** | Executive overview | Need quick understanding |
| **DOCKERFILE_CRITICAL_FIXES.md** | Action items | Ready to implement |
| **DOCKERFILE_AUDIT.md** | Full analysis | Need details & rationale |
| **DOCKERFILE_ISSUES_MATRIX.md** | Visual reference | Planning fixes |
| **DOCKERFILE_QUICK_REFERENCE.md** | This card | Need instant reference |

### Common Commands
```bash
# Check current state
docker images --format "table {{.Repository}}\t{{.Size}}"
docker compose ps

# Test after fixes
docker build -f docker/api/Dockerfile -t test-api:fix .
docker build -f docker/worker/Dockerfile -t test-worker:fix .
docker build -f docker/postgres/Dockerfile -t test-postgres:fix .

# Verify
docker compose up -d
docker compose ps  # All should be "healthy"
curl http://localhost:4209/health
curl http://localhost:4211/api/health
```

### Issue Severity Legend
- 🔴 CRITICAL (blocks deployment) - Fix immediately
- 🟠 HIGH (performance impact) - Fix this sprint
- 🟡 MEDIUM (robustness) - Fix when convenient
- 🟢 LOW (nice to have) - Backlog

### Key Metrics
- **Total Issues:** 14 (3 critical, 5 high, 4 medium, 2 low)
- **Fix Time:** 3 hours total (40 min critical, 90 min high priority)
- **Image Size Waste:** 1.5-1.9 GB (900 MB-1.2 GB saveable)
- **Build Reliability:** 2/7 broken → 7/7 working (100% success)

### Most Important First
1. Read `DOCKERFILE_CRITICAL_FIXES.md` (15 min)
2. Fix 3 critical issues (40 min)
3. Run `docker compose up` (5 min)
4. Fix 5 high-priority issues (90 min)
5. Measure improvements (15 min)

---

**Status:** Ready for implementation  
**Generated:** 2025-10-27  
**Total Prep Time:** ~2 hours analysis + documentation  
**Implementation Time:** 3 hours for all fixes
