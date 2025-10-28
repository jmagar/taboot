# Docker Build Context and .dockerignore Investigation

**Date:** 2025-10-27
**Scope:** Complete analysis of .dockerignore configuration and build context efficiency across Taboot services

---

## Executive Summary

**Critical Finding:** Multiple services are copying unnecessary files into build contexts, including:
- Test files and directories being copied despite .dockerignore patterns
- Documentation directories (docs/, specs/, todos/) ~1.2MB being copied to all services
- Build artifacts (.next/, .turbo/, node_modules/) in apps/web context
- Conflicting .dockerignore patterns between root and app-level files

**Impact:**
- Increased build context size → slower uploads to Docker daemon
- Cache invalidation from unnecessary file changes
- Security risk: sensitive files potentially exposed in images

---

## Build Context Mapping

### Service: `taboot-api`
**Build Configuration:**
```yaml
context: apps/api
dockerfile: ../../docker/api/Dockerfile
additional_contexts:
  packages: ../../packages
```

**Active .dockerignore:** `apps/api/.dockerignore` (677 bytes)

**What Gets Copied:**
```dockerfile
# From apps/api context:
COPY pyproject.toml README.md ./
COPY --chown=llamacrawl:llamacrawl . ./apps/api

# From additional_contexts (packages):
COPY --from=packages --chown=llamacrawl:llamacrawl . ./packages
```

**Files Being Copied That Shouldn't:**
1. ✅ **CORRECTLY EXCLUDED:**
   - `apps/api/.dockerignore` excludes `apps/web/`, `packages-ts/`, `tests/`
   - Documentation files excluded: `*.md`, `docs/`, `specs/`, `todos/`
   - Node.js artifacts excluded: `node_modules/`, `.next/`, `turbo.json`

2. ❌ **PROBLEMS:**
   - `apps/api/docs/` directory (from git status) is being copied despite `docs/` pattern
   - `apps/api/__pycache__/` directories are being copied (pattern exists but may not be working)
   - `apps/api/CLAUDE.md` being copied (*.md pattern excludes, but should verify)

3. ⚠️ **PACKAGES CONTEXT:**
   - Root `.dockerignore` does NOT apply to `additional_contexts`
   - `packages/` additional context copies EVERYTHING from packages/
   - No .dockerignore at `packages/.dockerignore` to filter this context
   - Potential issues:
     - Test directories in packages (if any)
     - `__pycache__/` directories
     - `.pytest_cache/` directories

---

### Service: `taboot-web`
**Build Configuration:**
```yaml
context: apps/web
dockerfile: ../../docker/web/Dockerfile
additional_contexts:
  packages-ts: ../../packages-ts
```

**Active .dockerignore:** `apps/web/.dockerignore` (643 bytes)

**What Gets Copied:**
```dockerfile
# Builder stage - copies from apps/web context:
COPY . ./apps/web
COPY --from=packages-ts . ./packages-ts
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json turbo.json ./

# Development stage (optional):
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Production stage - from installer build stage only
```

**Files Being Copied That Shouldn't:**
1. ❌ **MAJOR PROBLEMS:**
   - `.next/` directory exists in `apps/web/` (verified via `ls -la`)
   - `.turbo/` directory exists in `apps/web/` (verified via `ls -la`)
   - `node_modules/` directory exists in `apps/web/` (verified via `ls -la`)
   - Test files and directories:
     - `apps/web/__tests__/`
     - `apps/web/lib/__tests__/`
     - `*.test.ts`, `*.test.tsx` files throughout

2. ⚠️ **PATTERNS NOT WORKING:**
   - `.dockerignore` has `.next/` pattern, but directory still exists and gets copied
   - `.dockerignore` has `.turbo/` pattern, but directory still exists
   - `.dockerignore` has `**/__tests__/` pattern, but directories exist
   - Root cause: **Build artifacts from local dev are in the context directory**

3. ❌ **PACKAGES-TS CONTEXT:**
   - Root `.dockerignore` does NOT apply to `additional_contexts`
   - `packages-ts/` context copies EVERYTHING
   - No `.dockerignore` at `packages-ts/.dockerignore`
   - Known test directories being copied:
     - `packages-ts/profile/src/__tests__/`
     - `packages-ts/user-lifecycle/src/__tests__/`
     - `packages-ts/auth/src/__tests__/`
   - Build artifacts being copied:
     - `packages-ts/*/dist/` directories
     - `packages-ts/*/.turbo/` directories
     - `packages-ts/*/node_modules/` directories
     - `packages-ts/**/tsconfig.tsbuildinfo` files

---

### Service: `taboot-worker`
**Build Configuration:**
```yaml
context: .  # ROOT of project
dockerfile: docker/worker/Dockerfile
additional_contexts:
  packages: ./packages
```

**Active .dockerignore:** Root `.dockerignore` (3.1K)

**What Gets Copied:**
```dockerfile
COPY apps ./apps
COPY packages ./packages
COPY pyproject.toml uv.lock README.md ./
```

**Files Being Copied That Shouldn't:**
1. ❌ **ROOT CONTEXT ISSUES:**
   - Context is root of project → ALL files under root are in context
   - Root `.dockerignore` should filter, but may have gaps
   - Entire `apps/` directory copied (includes api, web, cli, mcp)
   - Documentation copied:
     - `docs/` (~792K)
     - `specs/` (~236K)
     - `todos/` (~216K)
   - **BUG:** Root `.dockerignore` has `apps/web/.next/` pattern, but not generic `**/.next/`

2. ❌ **SPECIFIC PROBLEMS:**
   - Git status shows `apps/web/.next/` exists → being copied
   - Git status shows `apps/web/node_modules/` → being copied
   - Root `.dockerignore` excludes `apps/web/node_modules/` specifically, but better pattern needed
   - `.github/` workflows being copied (pattern exists, should verify)
   - All root markdown files copied: `AGENTS.md`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`

3. ⚠️ **PACKAGES CONTEXT:**
   - Same issue as API service
   - No filtering on additional_contexts

---

## .dockerignore Pattern Analysis

### Pattern Effectiveness by Service

| Pattern Category | Root .dockerignore | apps/api/.dockerignore | apps/web/.dockerignore |
|-----------------|-------------------|----------------------|----------------------|
| **Test files** | ✅ `**/__tests__/`, `**/*.test.*`, `**/*.spec.*` | ✅ `**/__tests__/`, `**/*.test.py`, `tests/` | ✅ `**/__tests__/`, `**/*.test.ts`, `**/*.test.tsx` |
| **Build artifacts** | ✅ `.turbo/`, `**/.turbo/`, `.next/` (web-specific) | ✅ `.turbo/`, `build/`, `dist/` | ✅ `.next/`, `.turbo/`, `dist/`, `build/` |
| **Dependencies** | ✅ `node_modules/`, `packages/**/node_modules/`, `__pycache__/` | ✅ `node_modules/`, `__pycache__/`, `.venv/` | ✅ `node_modules/` |
| **Documentation** | ✅ (none - docs will be copied!) | ✅ `*.md`, `docs/`, `specs/`, `todos/` | ✅ `docs/`, `specs/`, `todos/` (but not *.md) |
| **Environment files** | ✅ `.env*`, `!.env.example` | ✅ `.env*`, `!.env.example` | ✅ `.env*`, `!.env.example` |
| **Git** | ✅ `.git/`, `.gitignore`, `.github/` | ✅ `.git/`, `.gitignore`, `.github/` | ✅ `.git/`, `.gitignore`, `.github/` |
| **IDE** | ✅ `.DS_Store` | ✅ `.vscode/`, `.idea/`, `.DS_Store` | ✅ `.vscode/`, `.idea/`, `.DS_Store` |

### Critical Gaps

1. **Root .dockerignore (worker service):**
   ```
   ❌ MISSING: docs/
   ❌ MISSING: specs/
   ❌ MISSING: todos/
   ❌ MISSING: *.md (allows AGENTS.md, CHANGELOG.md, CLAUDE.md)
   ❌ MISSING: apps/*/.venv/
   ❌ MISSING: packages/**/__pycache__/
   ❌ MISSING: packages/**/.pytest_cache/
   ❌ WEAK: apps/web/.next/ (should be **/.next/)
   ❌ WEAK: apps/web/node_modules/ (should be **/node_modules/)
   ```

2. **apps/api/.dockerignore:**
   ```
   ✅ GOOD: Most patterns present
   ⚠️ POTENTIAL: Verify __pycache__/ pattern catches nested directories
   ⚠️ POTENTIAL: No explicit .venv/ exclusion (relies on parent pattern)
   ```

3. **apps/web/.dockerignore:**
   ```
   ❌ SERIOUS: Patterns present but artifacts still in context
   ❌ ROOT CAUSE: Local development build artifacts in apps/web/
   ✅ PATTERNS: Actually good, but need clean context
   ❌ MISSING: Dockerfile* exclusion
   ❌ MISSING: docker-compose*.yml exclusion (present in file, good)
   ```

---

## Additional Contexts Problem

**CRITICAL ISSUE:** `.dockerignore` does NOT apply to `additional_contexts` in Docker Buildx.

**Affected Services:**
- `taboot-api` → `packages` context
- `taboot-web` → `packages-ts` context
- `taboot-worker` → `packages` context (explicit, but also copied via root)

**What Gets Copied:**
```bash
# For packages context (Python):
packages/
├── common/
├── core/
├── extraction/
├── graph/
├── ingest/
├── retrieval/
├── schemas/
└── vector/
    └── **ALL FILES** including:
        - __pycache__/
        - .pytest_cache/
        - *.pyc
        - test files (if any)
```

```bash
# For packages-ts context (TypeScript):
packages-ts/
├── auth/
├── db/
├── logger/
├── profile/
└── user-lifecycle/
    └── **ALL FILES** including:
        - dist/
        - .turbo/
        - node_modules/
        - tsconfig.tsbuildinfo
        - __tests__/ directories (CONFIRMED: 3 packages have test dirs)
```

**Solution Required:**
- Create `packages/.dockerignore`
- Create `packages-ts/.dockerignore`
- Patterns will be relative to those directories

---

## Build Context Size Estimation

### Current State (Estimated)

| Service | Context Path | Estimated Size | Unnecessary Files |
|---------|--------------|---------------|------------------|
| `taboot-api` | `apps/api/` | ~5-10 MB | Minimal (good .dockerignore) |
| `taboot-api` | `packages/` (additional) | ~20-30 MB | ~2-5 MB (__pycache__, .pytest_cache) |
| `taboot-web` | `apps/web/` | ~100-200 MB | ~80-150 MB (.next, node_modules, .turbo) |
| `taboot-web` | `packages-ts/` (additional) | ~50-100 MB | ~30-70 MB (dist, node_modules, tests) |
| `taboot-worker` | `.` (root) | ~150-300 MB | ~100-200 MB (docs, specs, todos, apps/web artifacts) |

**Potential Savings:** 200-425 MB per build (50-70% reduction)

---

## Recommendations

### Priority 1: Immediate Fixes

1. **Add missing .dockerignore files:**
   ```bash
   # Create packages/.dockerignore
   __pycache__/
   *.py[cod]
   *$py.class
   *.so
   .pytest_cache/
   .coverage
   htmlcov/
   .tox/
   *.egg-info/
   **/__tests__/
   **/test_*.py
   tests/

   # Create packages-ts/.dockerignore
   node_modules/
   dist/
   .turbo/
   tsconfig.tsbuildinfo
   **/__tests__/
   **/*.test.ts
   **/*.test.tsx
   **/*.spec.ts
   coverage/
   .nyc_output/
   ```

2. **Fix root .dockerignore for worker service:**
   ```dockerfile
   # Add these lines:
   docs/
   specs/
   todos/
   *.md
   !README.md
   **/.venv/
   **/__pycache__/
   **/.pytest_cache/
   **/.next/
   **/node_modules/
   **/.turbo/
   ```

3. **Clean apps/web/ before building:**
   ```bash
   # In CI/CD or local builds:
   rm -rf apps/web/.next
   rm -rf apps/web/.turbo
   rm -rf apps/web/node_modules

   # Or add to web Dockerfile:
   # No-op: .dockerignore should handle this if patterns work
   ```

### Priority 2: Pattern Improvements

1. **Consolidate patterns across all .dockerignore files:**
   - Use consistent glob patterns (`**/` prefix)
   - Test patterns with `docker build --progress=plain` to verify

2. **Verify pattern effectiveness:**
   ```bash
   # Test what gets sent to build context:
   docker build -f docker/api/Dockerfile apps/api --no-cache --progress=plain 2>&1 | grep "COPY"

   # Or use .dockerignore tester:
   docker build -f docker/api/Dockerfile apps/api -t test --target builder
   docker run --rm test find /app -type f | less
   ```

3. **Document .dockerignore application:**
   - Root `.dockerignore` applies to root context only
   - App-level `.dockerignore` applies to app context only
   - `additional_contexts` need their own `.dockerignore` in their directory

### Priority 3: Architectural Improvements

1. **Consider multi-stage build optimization:**
   - Current API/worker Dockerfiles copy entire directories
   - Could optimize to copy only needed files via explicit patterns

2. **Create .dockerignore template:**
   - Single source of truth for common patterns
   - Copy/customize per context

3. **Add build context validation to CI:**
   - Fail if build context exceeds size threshold
   - Fail if test files detected in final image

---

## Testing Checklist

- [ ] Create `packages/.dockerignore` with patterns above
- [ ] Create `packages-ts/.dockerignore` with patterns above
- [ ] Update root `.dockerignore` with missing patterns
- [ ] Clean `apps/web/.next`, `apps/web/.turbo`, `apps/web/node_modules`
- [ ] Build all services and verify context size reduction:
  ```bash
  docker compose build taboot-api --progress=plain 2>&1 | tee api-build.log
  docker compose build taboot-web --progress=plain 2>&1 | tee web-build.log
  docker compose build taboot-worker --progress=plain 2>&1 | tee worker-build.log
  ```
- [ ] Verify no test files in final images:
  ```bash
  docker run --rm taboot/api:latest find /app -name "__tests__" -o -name "*.test.*"
  docker run --rm taboot/web:latest find /app -name "__tests__" -o -name "*.test.*"
  docker run --rm taboot/worker:latest find /app -name "__tests__" -o -name "*.test.*"
  ```
- [ ] Verify documentation not in images:
  ```bash
  docker run --rm taboot/api:latest ls -la /app/docs 2>&1
  docker run --rm taboot/worker:latest ls -la /app/docs 2>&1
  ```

---

## Appendix: File References

**Key Files:**
- `/home/jmagar/code/taboot/.dockerignore` (3,171 bytes)
- `/home/jmagar/code/taboot/apps/api/.dockerignore` (677 bytes)
- `/home/jmagar/code/taboot/apps/web/.dockerignore` (643 bytes)
- `/home/jmagar/code/taboot/docker-compose.yaml:248-280` (taboot-api build config)
- `/home/jmagar/code/taboot/docker-compose.yaml:282-308` (taboot-web build config)
- `/home/jmagar/code/taboot/docker-compose.yaml:310-341` (taboot-worker build config)
- `/home/jmagar/code/taboot/docker/api/Dockerfile:92-93` (API COPY commands)
- `/home/jmagar/code/taboot/docker/web/Dockerfile:52-53,68,77` (Web COPY commands)
- `/home/jmagar/code/taboot/docker/worker/Dockerfile:21-22,75-77` (Worker COPY commands)

**Confirmed Issues:**
- `apps/web/.next/` directory exists (local dev artifact)
- `apps/web/.turbo/` directory exists (local dev artifact)
- `apps/web/node_modules/` directory exists (local dev artifact)
- `packages-ts/profile/src/__tests__/` exists (test directory)
- `packages-ts/user-lifecycle/src/__tests__/` exists (test directory)
- `packages-ts/auth/src/__tests__/` exists (test directory)
- `docs/` (~792 KB), `specs/` (~236 KB), `todos/` (~216 KB) in root

**Documentation Totals:**
- Root markdown files: ~20 KB (AGENTS.md, CHANGELOG.md, CLAUDE.md, README.md)
- Total documentation overhead: ~1.2 MB per worker build
