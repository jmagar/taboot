# Implementation Plan: PR #5 Security & Reliability Fixes

**Feature ID:** PR5-SECURITY-FIXES
**Type:** Bug Fix / Security Hardening
**Priority:** CRITICAL
**Created:** 2025-10-26
**Status:** Planning Complete

---

## Executive Summary

Fix 5 critical security and reliability issues identified in PR #5 code review:
- C-1: Authentication bypass vulnerability (weak session validation)
- C-2: Silent auth failures crashing middleware
- C-3: CSRF bypass on error
- C-4: Docker build failures are silent
- C-5: Server path regression in supervisord

Plus 3 important issues:
- I-1: Hardcoded cookie names
- I-2: Docker multi-stage inefficiency
- I-3: Supervisord restart loops

**Total Tasks:** 7 discrete tasks
**Execution Strategy:** 3 batches with parallel execution
**Estimated Effort:** 1 business day (6-8 hours)

---

## Investigation Summary

### Source Documents
- **ERROR_HANDLING_AUDIT_PR5.md** - Comprehensive error handling analysis
- **Code Review Report** - Security vulnerability assessment
- **Code Simplification Report** - Refactoring recommendations

### Key Findings

**Critical Security Issue (C-1):**
```typescript
// VULNERABLE: Only checks cookie presence, not validity
isAuthenticated = !!(authHeader?.startsWith('Bearer ') || sessionCookie);
```

This allows:
- Expired sessions to authenticate
- Tampered tokens to pass
- Cross-site session reuse
- No signature verification

**Critical Reliability Issues (C-2, C-3):**
- No error handling around `auth.api.getSession()` - crashes middleware on DB/network errors
- No error handling around `csrfMiddleware()` - may bypass protection on errors

**Critical Build Issues (C-4, C-5):**
- Docker builds continue after failures (missing `set -e`)
- Supervisord references wrong server.js path (regression from commit 938e681)

---

## Task Breakdown

### Batch 1: Foundations (Parallel - No Dependencies)

#### T1: Create Edge-Compatible Session Validation
**File:** `packages-ts/auth/src/edge.ts` (new)

**Objective:** Implement proper JWT verification for edge runtime

**Implementation:**
```typescript
import { verify } from '@taboot/jwt';
import type { Session } from './types';

export async function verifySession(options: {
  sessionToken: string | undefined;
  secret: string;
}): Promise<Session | null> {
  if (!options.sessionToken) return null;

  try {
    const payload = await verify(options.sessionToken, options.secret);

    // Validate expiry
    if (!payload.exp || payload.exp < Date.now() / 1000) {
      return null;
    }

    // Validate required claims
    if (!payload.userId || !payload.sessionId) {
      return null;
    }

    return {
      user: { id: payload.userId },
      sessionId: payload.sessionId,
      expiresAt: new Date(payload.exp * 1000),
    };
  } catch (error) {
    // Invalid signature, malformed token, etc.
    return null;
  }
}
```

**Validation:**
- Unit tests for expired tokens
- Unit tests for tampered signatures
- Unit tests for missing claims
- Unit tests for valid sessions

**Reference:** ERROR_HANDLING_AUDIT_PR5.md:77-110

---

#### T2: Create Centralized Auth Constants
**File:** `packages-ts/auth/src/constants.ts` (new)

**Objective:** Export cookie configuration for middleware reuse

**Implementation:**
```typescript
export const AUTH_COOKIE_NAME = process.env.AUTH_COOKIE_NAME || 'better-auth.session_token';
export const AUTH_COOKIE_LEGACY_NAME = 'authjs.session-token';
export const AUTH_BEARER_PREFIX = 'Bearer ';
```

**Validation:**
- Verify constants match better-auth config
- Test environment variable override

**Reference:** Code Review Report - Issue I-1

---

#### T3: Add Docker SHELL Directive
**Files:**
- `docker/api/Dockerfile`
- `docker/worker/Dockerfile`

**Objective:** Enable fail-fast builds with `set -e`

**Implementation:**
```dockerfile
# Add at top of both Dockerfiles (after FROM)
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]
```

**Validation:**
- Introduce intentional error in build step
- Verify build fails immediately (not continues)
- Test with missing dependency
- Test with compilation error

**Reference:** ERROR_HANDLING_AUDIT_PR5.md:C-3

---

### Batch 2: Core Fixes (Parallel - Depends on Batch 1)

#### T4: Fix Middleware Authentication Logic
**File:** `apps/web/middleware.ts`

**Objective:** Replace weak cookie check with proper session validation and error handling

**Implementation:**
```typescript
import { verifySession } from '@taboot/auth/edge';
import { AUTH_COOKIE_NAME, AUTH_COOKIE_LEGACY_NAME, AUTH_BEARER_PREFIX } from '@taboot/auth/constants';

// Inside middleware function
let isAuthenticated = false;
if (isProtectedRoute || isAuthRoute) {
  try {
    // Get token from cookie or bearer header
    const sessionToken =
      request.cookies.get(AUTH_COOKIE_NAME)?.value ||
      request.cookies.get(AUTH_COOKIE_LEGACY_NAME)?.value;

    const authHeader = request.headers.get('authorization');
    const bearerToken = authHeader?.startsWith(AUTH_BEARER_PREFIX)
      ? authHeader.slice(AUTH_BEARER_PREFIX.length)
      : undefined;

    const token = sessionToken || bearerToken;

    // Verify session with proper JWT validation
    const session = await verifySession({
      sessionToken: token,
      secret: process.env.AUTH_SECRET!,
    });

    isAuthenticated = !!session?.user;
  } catch (error) {
    // FAIL CLOSED: Log error, deny access
    console.error('Auth session check failed - denying access (fail-closed)', {
      pathname: request.nextUrl.pathname,
      error: error instanceof Error ? error.message : String(error),
    });
    isAuthenticated = false;
  }
}
```

**Validation:**
- Test valid session passes
- Test expired session denied
- Test tampered token denied
- Test missing token denied
- Test error during validation denied (fail-closed)
- Test auth header bearer token
- Test cookie-based session

**Reference:** ERROR_HANDLING_AUDIT_PR5.md:C-1, C-2

---

#### T5: Add CSRF Error Handling
**File:** `apps/web/middleware.ts`

**Objective:** Wrap CSRF middleware in try-catch with fail-closed behavior

**Implementation:**
```typescript
// Early in middleware function
try {
  const csrfResponse = await csrfMiddleware(request);
  if (csrfResponse) return csrfResponse;
} catch (error) {
  // FAIL CLOSED: Reject request on CSRF validation error
  console.error('CSRF validation failed - rejecting request (fail-closed)', {
    pathname: request.nextUrl.pathname,
    method: request.method,
    error: error instanceof Error ? error.message : String(error),
  });

  return NextResponse.json(
    { error: 'Security validation failed' },
    { status: 403 }
  );
}
```

**Validation:**
- Test valid CSRF token passes
- Test invalid CSRF token rejected
- Test missing CSRF token rejected
- Test CSRF middleware throws exception → 403
- Test crypto errors during validation → 403

**Reference:** ERROR_HANDLING_AUDIT_PR5.md:C-2

---

#### T6: Fix Supervisord Server Path
**File:** `docker/app/supervisord.conf` (legacy; container replaced by `docker/api` + `docker/web`)

**Objective:** Restore correct Next.js server path

**Implementation:**
```conf
[program:web]
command=node apps/web/server.js
directory=/app
autostart=true
autorestart=true
startretries=3
stderr_logfile=/var/log/supervisor/web-stderr.log
stdout_logfile=/var/log/supervisor/web-stdout.log
```

**Note:** With the unified container deprecated, ensure `docker/web/Dockerfile` launches `node apps/web/server.js` directly.
- Test restart limit prevents infinite loops

**Reference:** Code Review Report - Issues C-5, I-3

---

### Batch 3: Optimizations (Depends on Batch 2)

#### T7: Optimize Worker Docker Multi-Stage
**File:** `docker/worker/Dockerfile`

**Objective:** Copy only .venv instead of entire Python installation

**Implementation:**
```dockerfile
# Runtime stage
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Minimal runtime packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only virtual environment from builder (not entire Python installation)
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY --from=builder /app/apps ./apps
COPY --from=builder /app/packages ./packages
COPY --from=builder /app/README.md /app/pyproject.toml /app/uv.lock ./

# Non-root user
RUN useradd -m -u 10002 taboot && chown -R taboot:taboot /app

USER taboot

CMD ["python", "-m", "apps.worker"]
```

**Validation:**
- Compare image size before/after
- Verify worker starts successfully
- Test all Python dependencies available
- Verify no build tools in final image

**Reference:** Code Review Report - Issue I-2

---

## Execution Strategy

### Batch 1 (Parallel - No Dependencies)
Execute T1, T2, T3 simultaneously:
- T1: Edge session validation (TypeScript package)
- T2: Auth constants (TypeScript package)
- T3: Docker SHELL directive (Dockerfiles)

**Estimated Time:** 1-2 hours

### Batch 2 (Parallel - Depends on Batch 1)
Execute T4, T5, T6 simultaneously:
- T4: Middleware auth fix (uses T1, T2)
- T5: CSRF error handling (independent)
- T6: Supervisord path fix (independent)

**Estimated Time:** 2-3 hours

### Batch 3 (Serial - Depends on Batch 2)
Execute T7:
- T7: Docker optimization (verify no regressions from T6)

**Estimated Time:** 1 hour

---

## Integration Points

### Between T1 ↔ T4 (Session Validation)
- T4 imports `verifySession` from T1
- Interface: `verifySession(options) → Promise<Session | null>`
- Contract: Returns null for invalid/expired, never throws

### Between T2 ↔ T4 (Cookie Names)
- T4 imports cookie constants from T2
- Interface: `AUTH_COOKIE_NAME`, `AUTH_COOKIE_LEGACY_NAME`, `AUTH_BEARER_PREFIX`
- Contract: Matches better-auth configuration

### Between T3 ↔ T7 (Docker Builds)
- Both modify Dockerfiles
- T3 adds SHELL directive (top of file)
- T7 modifies runtime stage (bottom of file)
- No conflicts expected

---

## Risk Assessment

### High Risk Items

**R-1: Breaking Change in Auth Flow**
- **Risk:** Switching to JWT verification may break existing sessions
- **Mitigation:** Support both legacy and new cookie names (T2)
- **Validation:** Test migration path with existing sessions

**R-2: Docker Build Performance Regression**
- **Risk:** Multi-stage optimization (T7) may slow builds
- **Mitigation:** Use Docker cache mounts, measure before/after
- **Validation:** Compare build times in CI

**R-3: Supervisord Configuration Error**
- **Risk:** Wrong path causes web service to fail at startup
- **Mitigation:** Test in Docker container before deploying
- **Validation:** `docker compose up` and verify web responds

### Medium Risk Items

**R-4: CSRF False Positives**
- **Risk:** Overly strict error handling may reject valid requests
- **Mitigation:** Log all rejections with full context
- **Validation:** Monitor logs for unexpected CSRF rejections

**R-5: Edge Runtime Compatibility**
- **Risk:** JWT verification library may not work in edge runtime
- **Mitigation:** Use edge-compatible JWT library, test thoroughly
- **Validation:** Deploy to Vercel edge function for testing

---

## Validation Criteria

### Per-Task Validation
See individual task sections for specific test scenarios.

### Integration Validation

**End-to-End Auth Flow:**
1. User signs in → receives session cookie
2. Middleware validates session → allows access to protected route
3. Session expires → middleware denies access
4. User provides invalid token → middleware denies access (logged)

**Build Validation:**
1. Introduce build error → Docker build fails immediately (T3)
2. Fix error → Docker build succeeds
3. Start containers → All services healthy
4. Check image sizes → Worker image smaller (T7)

**Error Handling Validation:**
1. Simulate auth service failure → middleware returns 500, logs error
2. Simulate CSRF validation error → middleware returns 403, logs error
3. Check logs → All errors have full context

---

## Rollback Plan

### If Critical Issues Arise

**Option 1: Revert Middleware Changes (T4, T5)**
```bash
git revert <commit-hash-t4> <commit-hash-t5>
```

**Option 2: Revert All Changes**
```bash
git revert <commit-hash-batch-1>..<commit-hash-batch-3>
```

**Option 3: Feature Flag (Future)**
Add environment variable to toggle new auth validation:
```typescript
const USE_EDGE_AUTH = process.env.USE_EDGE_AUTH === 'true';
```

---

## Dependencies

### External Dependencies
- `@taboot/jwt` - JWT verification library (must be edge-compatible)
- `@taboot/auth` - Better-auth integration
- `better-auth` - Session management

### Internal Dependencies
- T4 depends on T1 (session validation)
- T4 depends on T2 (cookie constants)
- T7 should run after T6 (Docker stability)

### Environment Variables Required
- `AUTH_SECRET` - JWT signing secret (already exists)
- `AUTH_COOKIE_NAME` - Cookie name override (optional)

---

## Testing Strategy

### Unit Tests
- T1: `packages-ts/auth/src/__tests__/edge.test.ts`
  - Test expired tokens
  - Test tampered signatures
  - Test missing claims
  - Test valid sessions

### Integration Tests
- T4: `apps/web/__tests__/middleware.test.ts`
  - Test auth flow with valid session
  - Test auth flow with expired session
  - Test auth flow with invalid token
  - Test error handling (fail-closed)

### Manual Testing
- Deploy to staging
- Test sign-in flow
- Test protected routes
- Test session expiry
- Monitor error logs

---

## Documentation Updates

### Files to Update
- `CLAUDE.md` - Add note about edge-compatible auth
- `docs/security.md` - Document session validation approach
- `docker/README.md` - Note SHELL directive requirement

### Inline Code Comments
- Document fail-closed error handling rationale
- Explain JWT verification vs. database lookup tradeoff
- Note cookie name compatibility with better-auth config

---

## Success Criteria

### Must Have (Blocking)
- ✅ All 5 critical issues (C-1 through C-5) resolved
- ✅ All validation tests pass
- ✅ Docker builds succeed with intentional errors failing fast
- ✅ Middleware handles errors gracefully (fail-closed)
- ✅ Supervisord starts web service successfully

### Should Have (Important)
- ✅ All 3 important issues (I-1 through I-3) resolved
- ✅ Worker Docker image size reduced by T7
- ✅ Error logs include full context for debugging
- ✅ Unit tests for edge session validation

### Nice to Have (Optional)
- Performance benchmarks for new auth validation
- Monitoring dashboard for auth errors
- Automated security scanning in CI

---

## Post-Implementation

### Monitoring
- Track auth validation errors in logs
- Monitor CSRF rejection rate
- Alert on supervisord restart loops
- Track Docker build times

### Future Improvements
- Add feature flag for gradual rollout
- Implement session refresh on near-expiry
- Add rate limiting for failed auth attempts
- Consider moving to edge-first architecture

---

## Approval Checklist

- [ ] All task descriptions reviewed
- [ ] Dependencies mapped correctly
- [ ] Validation criteria clear
- [ ] Risk assessment complete
- [ ] Rollback plan documented
- [ ] User approval received

**Next Step:** Run `/manage-project/implement/execute PR5-SECURITY-FIXES` to begin implementation.
