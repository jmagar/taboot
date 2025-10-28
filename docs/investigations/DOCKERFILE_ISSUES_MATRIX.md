# Dockerfile Issues - Visual Matrix

## Issues by Severity & File

```
CRITICAL (Build Fails)
├─ docker/api/Dockerfile:93
│  ├─ Type: Broken Build Context
│  ├─ Severity: CRITICAL 🔴
│  ├─ Fix Time: 5min
│  └─ Code: Change COPY --from=packages to COPY packages
│
├─ docker/worker/Dockerfile:6
│  ├─ Type: Missing Base Image
│  ├─ Severity: CRITICAL 🔴
│  ├─ Fix Time: 15min
│  └─ Code: Collapse to single Dockerfile OR auto-build base
│
└─ docker/postgres/Dockerfile
   ├─ Type: Missing Extension Creation
   ├─ Severity: CRITICAL 🔴 (runtime failure)
   ├─ Fix Time: 20min
   └─ Code: Add CREATE EXTENSION pg_cron in init script

HIGH PRIORITY (Performance)
├─ docker/api/Dockerfile:14-22
│  ├─ Type: Build Dependencies Not Removed
│  ├─ Severity: HIGH 🟠 (200-300MB bloat)
│  ├─ Fix Time: 15min
│  └─ Impact: apt-get purge after venv build
│
├─ docker/api/Dockerfile:37-60
│  ├─ Type: Excessive Dependency Installation
│  ├─ Severity: HIGH 🟠 (800MB-1.2GB bloat)
│  ├─ Fix Time: 30min
│  └─ Impact: API installs worker-only LlamaIndex packages
│
├─ docker/worker/Dockerfile:26-27
│  ├─ Type: Cache Mount Misconfigured
│  ├─ Severity: HIGH 🟠 (cache miss on rebuild)
│  ├─ Fix Time: 5min
│  └─ Code: /root/.cache/uv → /root/.cache/pip
│
└─ docker/reranker/Dockerfile:30
   ├─ Type: No Model Download Retry
   ├─ Severity: HIGH 🟠 (build fails on network hiccup)
   ├─ Fix Time: 10min
   └─ Impact: Wrap model download in retry loop

MEDIUM PRIORITY (Robustness)
├─ docker/worker/Dockerfile:81-82
│  ├─ Type: Poor Healthcheck Logic
│  ├─ Severity: MEDIUM 🟡 (can't detect stuck workers)
│  ├─ Fix Time: 10min
│  └─ Code: Add metrics/status endpoint validation
│
├─ docker/web/Dockerfile:58
│  ├─ Type: Suboptimal turbo prune
│  ├─ Severity: MEDIUM 🟡 (400-600MB bloat)
│  ├─ Fix Time: 20min
│  └─ Impact: Use --scope to be more selective
│
├─ docker/postgres/Dockerfile:18
│  ├─ Type: Fragile Regex Configuration
│  ├─ Severity: MEDIUM 🟡 (version-dependent)
│  ├─ Fix Time: 10min
│  └─ Code: Use init SQL script instead
│
└─ docker/base-ml/Dockerfile:56
   ├─ Type: Incomplete Build Tool Cleanup
   ├─ Severity: MEDIUM 🟡 (100-200MB bloat)
   ├─ Fix Time: 5min
   └─ Code: Remove curl, pkg-config, python3-dev

LOW PRIORITY (Nice to Have)
├─ docker/api/Dockerfile:83
│  ├─ Type: User GID Not Explicit
│  ├─ Severity: LOW 🟢
│  ├─ Fix Time: 2min
│  └─ Code: useradd -m -u 10001 -g 10001 llamacrawl
│
├─ docker/api/Dockerfile:31
│  ├─ Type: README in dependency layer
│  ├─ Severity: LOW 🟢 (invalidates cache on doc changes)
│  ├─ Fix Time: 5min
│  └─ Code: Move COPY README.md after dependency layer
│
└─ docker/neo4j/Dockerfile
   ├─ Type: No Image-Level HEALTHCHECK
   ├─ Severity: LOW 🟢 (relies on docker-compose)
   ├─ Fix Time: 5min
   └─ Code: Add HEALTHCHECK in Dockerfile
```

## Issues by Dockerfile

### docker/api/Dockerfile (3 Critical, 3 High)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| Broken `--from=packages` | 93 | CRITICAL | Build | Build fails |
| Build deps not removed | 14-22 | HIGH | Size | +200-300MB |
| LlamaIndex bloat | 37-60 | HIGH | Size | +800MB-1.2GB |
| README in dependency layer | 31 | LOW | Cache | Invalidates cache |
| User GID not explicit | 83 | LOW | Security | Minor |

### docker/web/Dockerfile (1 Medium)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| Suboptimal turbo prune | 58 | MEDIUM | Size | +400-600MB |

### docker/worker/Dockerfile (1 Critical, 2 High, 1 Medium)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| Missing base image | 6 | CRITICAL | Build | Container won't run |
| Cache mount wrong path | 26-27 | HIGH | Cache | pip re-downloads all |
| pgrep-only healthcheck | 81-82 | MEDIUM | Robustness | Can't detect stuck |

### docker/reranker/Dockerfile (1 High)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| Model download no retry | 30 | HIGH | Robustness | Build fails on network hiccup |

### docker/postgres/Dockerfile (1 Critical, 1 Medium)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| pg_cron not created | 10-19 | CRITICAL | Functionality | Extension not available |
| Fragile sed regex | 18 | MEDIUM | Robustness | Version-dependent |

### docker/neo4j/Dockerfile (1 Low)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| No image HEALTHCHECK | - | LOW | Composition | Relies on docker-compose |

### docker/base-ml/Dockerfile (1 Medium)
| Issue | Line | Severity | Type | Impact |
|-------|------|----------|------|--------|
| Build tools not fully cleaned | 56 | MEDIUM | Size | +100-200MB |

## Fix Timeline

### Week 1: Critical Fixes (1-2 hours)
```
Monday:
  ✓ 5min   - Fix docker/api line 93 (COPY --from=packages)
  ✓ 15min  - Fix docker/worker line 6 (base image)
  ✓ 20min  - Fix docker/postgres pg_cron
  ──────────
  40min total (plus testing)

Tuesday:
  ✓ Testing & validation
  ✓ docker compose up verification
  ✓ Health check validation
```

### Week 2: Performance Fixes (1-2 hours)
```
Wednesday:
  ✓ 15min  - Remove build deps from docker/api
  ✓ 5min   - Fix docker/worker cache mount
  ✓ 10min  - Add docker/reranker retry logic
  ──────────
  30min total (plus testing)

Thursday:
  ✓ 30min  - Refactor docker/api dependencies
  ✓ Image size measurement & verification

Friday:
  ✓ 20min  - Optimize docker/web turbo prune
  ✓ 10min  - Clean docker/base-ml build tools
```

### Backlog (Optional)
```
- Standardize healthchecks across images (15min)
- Fix docker/postgres sed regex (10min)
- Add ENTRYPOINT scripts (30min)
- Create unified base-python image (45min)
- Add Dockerfile linting (hadolint) to CI/CD (20min)
- Add security scanning (Trivy) to CI/CD (20min)
```

## Impact Summary

### Current State
```
Total Issues:    14
  - Critical:    3 (block deployment)
  - High:        5 (performance problems)
  - Medium:      4 (robustness)
  - Low:         2 (nice to have)

Estimated Waste: 1.5-1.9 GB image size bloat
Build Problems:  2 (api, worker)
Runtime Problems: 1 (postgres)
```

### After All Fixes
```
Total Issues:    0
  - Fixed:      14 (100%)
  
Image Size Reduction: 900 MB - 1.2 GB
Build Reliability:    100% (no broken builds)
```

## How to Use This Matrix

1. **Get quick overview**: Look at the top section (Issues by Severity)
2. **Find specific issue**: Search your Dockerfile name (Issues by Dockerfile)
3. **Plan timeline**: Follow the Fix Timeline section
4. **Measure success**: Compare "Current State" vs "After All Fixes"

## References

- **Full Analysis**: `DOCKERFILE_AUDIT.md`
- **Action Items**: `DOCKERFILE_CRITICAL_FIXES.md`
- **Executive Summary**: `DOCKERFILE_SUMMARY.txt`
