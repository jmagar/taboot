# Error Handling Audit Report: PR #5
## Silent Failures and Inadequate Error Handling Analysis

**Audit Date:** 2025-10-26
**Auditor:** Error Handling Specialist
**Scope:** apps/web/middleware.ts, docker/app/Dockerfile, docker/worker/Dockerfile, docker/app/supervisord.conf
**Branch:** `feat/web`
**Commits Analyzed:** HEAD~5..HEAD (938e681)

---

## Executive Summary

This audit examines the code changes in the recent commits for **silent failures, swallowed exceptions, and inadequate error handling**. The analysis focuses on three critical areas:
1. Authentication middleware in Next.js
2. Docker build processes
3. Process supervision configuration

### Risk Assessment Summary

| Severity | Count | Category |
|----------|-------|----------|
| **CRITICAL** 🔴 | 3 | Silent failures that could cause production outages |
| **HIGH** 🟠 | 2 | Missing error handling with security implications |
| **MEDIUM** 🟡 | 2 | Inadequate error messages |
| **LOW** 🟢 | 1 | Minor improvements |

**Overall Assessment:** ⚠️ **CRITICAL ISSUES FOUND** - Production deployment is **NOT RECOMMENDED** until critical issues are resolved.

---

## CRITICAL Findings

### C-1: Silent Auth Session Failure in Middleware

**Location:** `/home/jmagar/code/taboot/apps/web/middleware.ts:63-74`
**Severity:** 🔴 CRITICAL
**Impact:** Authentication bypass, unauthorized access to protected routes

**Issue Description:**

The authentication check uses `auth.api.getSession()` without any error handling. If the auth service throws an error (network failure, invalid token format, database connection error, etc.), the middleware will crash and the **entire application becomes unavailable**.

**Problematic Code:**

```typescript
// Line 63-74
let isAuthenticated = false;
if (isProtectedRoute || isAuthRoute) {
  const session = await auth.api.getSession({
    headers: request.headers,
  });
  isAuthenticated = !!session?.user;
}
```

**Hidden Errors This Catch Block Could Hide:**

Since there is **NO catch block**, ALL errors will bubble up and crash the middleware:

1. ❌ **Network errors** - Auth service unreachable
2. ❌ **Database errors** - Session store unavailable
3. ❌ **Invalid JWT** - Malformed token throws parsing error
4. ❌ **Expired session** - Could throw instead of returning null
5. ❌ **Better-auth library bugs** - Any uncaught exception in the library
6. ❌ **Memory errors** - Out of memory during session deserialization
7. ❌ **Redis connection failures** - If session cache is down
8. ❌ **Type validation errors** - If session data is corrupted

**User Impact:**

- **Best case:** User sees a 500 error page and can't access the application
- **Worst case:** Middleware crashes repeatedly, entire site goes down until restart
- **Debugging nightmare:** No error context logged, just "middleware failed"
- **Security risk:** If error handling defaults to allowing access, authentication is bypassed

**Recommendation:**

```typescript
// REQUIRED: Wrap auth check in try-catch with explicit fail-closed behavior
let isAuthenticated = false;
if (isProtectedRoute || isAuthRoute) {
  try {
    const session = await auth.api.getSession({
      headers: request.headers,
    });
    isAuthenticated = !!session?.user;
  } catch (error) {
    // CRITICAL: Log error with full context for debugging
    logger.error('Authentication session check failed - denying access (fail-closed)', {
      pathname,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
      headers: {
        authorization: request.headers.get('authorization') ? 'present' : 'missing',
        cookie: request.headers.get('cookie') ? 'present' : 'missing',
      },
    });

    // FAIL CLOSED: Deny access on error (security-first approach)
    isAuthenticated = false;

    // For protected routes, show user-friendly error instead of crash
    if (isProtectedRoute) {
      return NextResponse.json(
        {
          error: 'Authentication service temporarily unavailable',
          message: 'Please try again in a few moments',
        },
        { status: 503, headers: { 'Retry-After': '30' } }
      );
    }

    // For auth routes, allow through (so users can sign in/up during outage)
    // Auth will fail at the API level with proper error messages
  }
}
```

**Remediation Effort:** High (1 hour to implement and test all error paths)

---

### C-2: CSRF Middleware Error Swallowing

**Location:** `/home/jmagar/code/taboot/apps/web/middleware.ts:30-52`
**Severity:** 🔴 CRITICAL
**Impact:** Silent CSRF validation failures, potential security bypass

**Issue Description:**

The CSRF middleware is called but there is **no error handling** for failures. If `csrfMiddleware()` throws an exception (crypto failure, invalid token format, etc.), the middleware crashes.

**Problematic Code:**

```typescript
// Line 28-52
if (!isExcluded) {
  // Fix #4: Call CSRF middleware only once
  const csrfResponse = await csrfMiddleware(request);

  // For safe methods (GET/HEAD/OPTIONS), merge CSRF cookies/headers and continue
  if (request.method === 'GET' || request.method === 'HEAD' || request.method === 'OPTIONS') {
    const response = NextResponse.next();

    // Copy CSRF cookies and headers to the response
    csrfResponse.cookies.getAll().forEach((cookie) => {
      response.cookies.set(cookie);
    });
    csrfResponse.headers.forEach((value, key) => {
      if (key.toLowerCase().startsWith('x-csrf')) {
        response.headers.set(key, value);
      }
    });

    return response;
  }

  // For unsafe methods (POST/PUT/PATCH/DELETE), return 403 if CSRF check failed
  if (csrfResponse.status === 403) {
    return csrfResponse;
  }
}
```

**Hidden Errors This Code Could Hide:**

1. ❌ **Crypto API failures** - `crypto.subtle.sign()` throws on invalid key
2. ❌ **Token parsing errors** - Malformed tokens throw during split/decode
3. ❌ **Header iteration errors** - `headers.forEach()` could throw if corrupted
4. ❌ **Cookie setting errors** - `cookies.set()` throws on invalid values
5. ❌ **Response construction errors** - NextResponse.json() throws on invalid JSON
6. ❌ **Memory errors** - Out of memory during HMAC computation

**Additional Issue:**

The code **assumes** `csrfMiddleware()` always returns a Response object. What if it throws? What if it returns undefined due to a bug? This is a **silent failure** waiting to happen.

**User Impact:**

- POST/PUT/PATCH/DELETE requests silently bypass CSRF protection on error
- Users experience application crashes instead of security errors
- No logging = impossible to debug CSRF-related issues
- Potential security vulnerability if CSRF checks are bypassed due to errors

**Recommendation:**

```typescript
// REQUIRED: Wrap CSRF middleware in try-catch
if (!isExcluded) {
  try {
    const csrfResponse = await csrfMiddleware(request);

    // VALIDATE: Ensure we got a valid response
    if (!csrfResponse || !(csrfResponse instanceof NextResponse)) {
      throw new Error('CSRF middleware returned invalid response');
    }

    // For safe methods (GET/HEAD/OPTIONS), merge CSRF cookies/headers and continue
    if (request.method === 'GET' || request.method === 'HEAD' || request.method === 'OPTIONS') {
      const response = NextResponse.next();

      // Copy CSRF cookies and headers to the response
      try {
        csrfResponse.cookies.getAll().forEach((cookie) => {
          response.cookies.set(cookie);
        });
        csrfResponse.headers.forEach((value, key) => {
          if (key.toLowerCase().startsWith('x-csrf')) {
            response.headers.set(key, value);
          }
        });
      } catch (cookieError) {
        // Log but don't fail - CSRF token setting is not critical for GET requests
        logger.warn('Failed to set CSRF cookies/headers on GET request', {
          pathname,
          error: cookieError instanceof Error ? cookieError.message : String(cookieError),
        });
      }

      return response;
    }

    // For unsafe methods (POST/PUT/PATCH/DELETE), return 403 if CSRF check failed
    if (csrfResponse.status === 403) {
      return csrfResponse;
    }

  } catch (error) {
    // CRITICAL: CSRF validation failure - fail closed
    logger.error('CSRF middleware failed - rejecting request (fail-closed)', {
      pathname,
      method: request.method,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });

    // FAIL CLOSED: Reject state-changing requests if CSRF check fails
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) {
      return NextResponse.json(
        {
          error: 'CSRF validation failed',
          message: 'Security check could not be completed. Please refresh and try again.',
        },
        { status: 503 }
      );
    }

    // For GET requests, continue but log the error
    return NextResponse.next();
  }
}
```

**Remediation Effort:** High (1 hour to implement and test all error paths)

---

### C-3: Docker Build Failures Are Silent

**Location:** `/home/jmagar/code/taboot/docker/app/Dockerfile:42-57`
**Severity:** 🔴 CRITICAL
**Impact:** Failed builds may produce broken images that crash at runtime

**Issue Description:**

The Docker build process uses RUN commands without `set -e` or explicit error checking. If `pnpm install` or `pnpm build` fail, **the build may continue** and produce a broken image.

**Problematic Code:**

```dockerfile
# Line 42-57
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy Node.js workspace files for web app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install Node.js dependencies with frozen lockfile (cached across builds)
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# Build Next.js production bundle
RUN pnpm --filter @taboot/web build
```

**Hidden Errors This Could Hide:**

1. ❌ **Missing dependencies** - If pnpm-lock.yaml is corrupted
2. ❌ **TypeScript errors** - Next.js build fails but Docker continues
3. ❌ **Out of memory** - Build process OOMs, creates partial bundle
4. ❌ **Disk space errors** - No space left for node_modules
5. ❌ **Network errors** - pnpm can't download packages (with cache mount, this is less likely but possible)
6. ❌ **Cache corruption** - Cached dependencies are broken
7. ❌ **Build script errors** - Any error in Next.js build process

**Why This Is Critical:**

Docker builds should **fail fast** if any step fails. Without explicit error handling:
- Image builds successfully even though the app is broken
- Runtime errors instead of build-time errors (harder to debug)
- Potentially deploys broken code to production
- No clear indication of which step failed

**User Impact:**

- Broken builds are pushed to production
- Application crashes on startup with cryptic errors
- "It built successfully" but the app doesn't work
- Debugging requires manual inspection of build logs

**Recommendation:**

```dockerfile
# SHELL directive ensures ALL commands fail on error
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Install Python workspace dependencies - will fail build if this fails
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev || { echo "ERROR: Python dependency installation failed"; exit 1; }

# Copy Node.js workspace files for web app
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./
COPY packages-ts ./packages-ts
COPY apps/web ./apps/web

# Install Node.js dependencies - will fail build if this fails
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile || { echo "ERROR: pnpm install failed"; exit 1; }

# Build Next.js production bundle - will fail build if this fails
# Use --no-lint to ensure TypeScript/lint errors fail the build
RUN pnpm --filter @taboot/web build || { echo "ERROR: Next.js build failed - check TypeScript/build errors"; exit 1; }

# Verify build artifacts exist (fail-fast validation)
RUN test -d apps/web/.next/standalone || { echo "ERROR: Next.js standalone build not found"; exit 1; }
RUN test -d apps/web/.next/static || { echo "ERROR: Next.js static assets not found"; exit 1; }
```

**Note:** Line 8 already has `SHELL ["/bin/bash", "-o", "pipefail", "-c"]` but it's missing the `-e` flag. Change it to:

```dockerfile
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
```

**Remediation Effort:** Medium (30 minutes to add error checking and test)

---

## HIGH Severity Findings

### H-1: Supervisord Process Crash Handling

**Location:** `/home/jmagar/code/taboot/docker/app/supervisord.conf`
**Severity:** 🟠 HIGH
**Impact:** Silent process crashes, no alerting, no health check correlation

**Issue Description:**

The supervisord configuration uses `autorestart=true` for both API and web processes, but there is **no maximum restart count**, **no notification on failure**, and **no logging of crash reasons**.

**Problematic Code:**

```ini
[program:api]
command=uvicorn apps.api.app:app --host 0.0.0.0 --port 8000
directory=/app
user=llamacrawl
autostart=true
autorestart=true  # ⚠️ INFINITE RESTARTS - no limit
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=PYTHONUNBUFFERED="1",PYTHONPATH="/app"

[program:web]
command=node server.js
directory=/app
user=llamacrawl
autostart=true
autorestart=true  # ⚠️ INFINITE RESTARTS - no limit
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=NODE_ENV="production",PORT="3000",HOSTNAME="0.0.0.0"
```

**Hidden Problems:**

1. ❌ **Crash loops** - If process crashes on startup, it restarts forever
2. ❌ **No failure threshold** - No `startretries` or `stopasgroup` configured
3. ❌ **No exit code tracking** - Can't distinguish between clean shutdown and crash
4. ❌ **No notification** - Nobody knows when processes are restarting
5. ❌ **Health check mismatch** - HEALTHCHECK in Dockerfile doesn't prevent restart loops

**User Impact:**

- Application appears "up" (container running) but is actually crash-looping
- Health checks may pass even if processes are rapidly restarting
- No visibility into why processes are crashing
- Resource exhaustion from rapid restarts
- Users experience intermittent "service unavailable" errors

**Recommendation:**

```ini
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor

[program:api]
command=uvicorn apps.api.app:app --host 0.0.0.0 --port 8000
directory=/app
user=llamacrawl
autostart=true
autorestart=true
# REQUIRED: Limit restart attempts to prevent infinite loops
startretries=3
startsecs=10
# REQUIRED: Log exit codes to understand crash reasons
exitcodes=0
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=PYTHONUNBUFFERED="1",PYTHONPATH="/app"
# OPTIONAL: Send alert on failure (requires email config)
# stopwaitsecs=30
# stopsignal=TERM

[program:web]
command=node server.js
directory=/app
user=llamacrawl
autostart=true
autorestart=true
# REQUIRED: Limit restart attempts to prevent infinite loops
startretries=3
startsecs=10
# REQUIRED: Log exit codes to understand crash reasons
exitcodes=0
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
environment=NODE_ENV="production",PORT="3000",HOSTNAME="0.0.0.0"

# RECOMMENDED: Add event listener for crash notifications
[eventlistener:crashmail]
command=/usr/local/bin/crashmail -a -m alerts@taboot.io
events=PROCESS_STATE_FATAL
```

**Also Update Docker HEALTHCHECK:**

```dockerfile
# Current HEALTHCHECK may not detect crash loops
# Add dependency on supervisorctl to check ALL programs are RUNNING
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD supervisorctl status | grep -E "(api|web)" | grep -v RUNNING && exit 1 || \
        (curl -f http://localhost:8000/health && curl -f http://localhost:3000/api/test)
```

**Remediation Effort:** Medium (1 hour to configure and test crash scenarios)

---

### H-2: Docker Build Path Correction Without Validation

**Location:** `/home/jmagar/code/taboot/docker/app/supervisord.conf:21` (commit 938e681)
**Severity:** 🟠 HIGH
**Impact:** Silent failure if server.js doesn't exist at new path

**Issue Description:**

The recent commit changed the Next.js server path from `apps/web/server.js` to `server.js`, but there is **no validation** that this file exists at the expected location.

**Code Change:**

```diff
-command=node apps/web/server.js
+command=node server.js
```

**What Could Go Wrong:**

1. ❌ **File doesn't exist** - If standalone build structure changes, `server.js` may not be in `/app`
2. ❌ **Wrong file** - Could accidentally run a different server.js
3. ❌ **Build artifact missing** - If Next.js build fails to create standalone, supervisord starts with wrong file
4. ❌ **No error message** - Node just says "Cannot find module" with no context

**Current Docker COPY:**

```dockerfile
# Line 103-106
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public
```

**The Problem:**

The standalone build from Next.js places `server.js` at the root of the standalone directory, but this is **not guaranteed** and depends on Next.js version and configuration.

**User Impact:**

- Container starts successfully (supervisord runs)
- Web process immediately crashes with "Cannot find module"
- Autorestart=true causes infinite restart loop
- Health check fails but container doesn't exit (due to supervisord)
- Deployment appears successful but web app is down

**Recommendation:**

**1. Add validation to Dockerfile (build-time check):**

```dockerfile
# After copying standalone build, verify server.js exists
COPY --from=builder /app/apps/web/.next/standalone ./
RUN test -f server.js || { echo "ERROR: server.js not found in standalone build - check Next.js output structure"; ls -la; exit 1; }

COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /app/apps/web/public ./apps/web/public
```

**2. Add validation to supervisord (runtime check):**

```ini
[program:web]
command=/bin/bash -c "test -f /app/server.js && node /app/server.js || { echo 'ERROR: /app/server.js not found'; exit 1; }"
directory=/app
user=llamacrawl
autostart=true
autorestart=true
# ... rest of config
```

**3. Alternative - use explicit path to be defensive:**

```ini
[program:web]
command=node /app/server.js
directory=/app
user=llamacrawl
autostart=true
autorestart=true
```

**Remediation Effort:** Low (15 minutes to add validation)

---

## MEDIUM Severity Findings

### M-1: Cookie Validation Errors Are Silent

**Location:** `/home/jmagar/code/taboot/apps/web/middleware.ts:69-70`
**Severity:** 🟡 MEDIUM
**Impact:** Cookie parsing errors may lead to silent auth failures

**Issue Description:**

The code reads session cookies without error handling. If the cookie value is corrupted or malformed, `.value` may throw or return undefined unexpectedly.

**Problematic Code:**

```typescript
const sessionCookie = request.cookies.get('better-auth.session_token')?.value ||
                      request.cookies.get('authjs.session-token')?.value;
```

**What Could Go Wrong:**

1. ⚠️ **Corrupted cookie encoding** - Malformed base64 in cookie value
2. ⚠️ **Oversized cookie** - Cookie exceeds size limits, gets truncated
3. ⚠️ **Special characters** - Unescaped characters in cookie value
4. ⚠️ **Cookie spoofing** - Attacker sends malformed cookie to crash middleware

**User Impact:**

- Users with corrupted cookies can't authenticate
- No error message explaining the issue
- No way to clear bad cookies automatically

**Recommendation:**

```typescript
// Add error handling for cookie parsing
let sessionCookie: string | undefined;
try {
  sessionCookie = request.cookies.get('better-auth.session_token')?.value ||
                  request.cookies.get('authjs.session-token')?.value;

  // Validate cookie format (if you know the expected format)
  if (sessionCookie && !/^[A-Za-z0-9_-]+$/.test(sessionCookie)) {
    logger.warn('Invalid session cookie format detected', {
      pathname,
      cookiePrefix: sessionCookie.substring(0, 10),
    });
    sessionCookie = undefined;
  }
} catch (error) {
  logger.warn('Failed to parse session cookie', {
    pathname,
    error: error instanceof Error ? error.message : String(error),
  });
  sessionCookie = undefined;
}

// Check for authorization header (bearer token) or session cookie
const authHeader = request.headers.get('authorization');
isAuthenticated = !!(authHeader?.startsWith('Bearer ') || sessionCookie);
```

**Remediation Effort:** Low (30 minutes)

---

### M-2: Worker Dockerfile Health Check Is Meaningless

**Location:** `/home/jmagar/code/taboot/docker/worker/Dockerfile:79-80`
**Severity:** 🟡 MEDIUM
**Impact:** Health check always passes even if worker is broken

**Issue Description:**

The worker health check just runs `python -c "import sys; sys.exit(0)"` which tests if Python works, not if the worker is actually healthy.

**Problematic Code:**

```dockerfile
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1
```

**This Health Check:**

- ✅ Passes if Python interpreter exists
- ❌ Doesn't check if worker process is running
- ❌ Doesn't check if worker can connect to Redis/Neo4j/Qdrant
- ❌ Doesn't check if worker is processing jobs
- ❌ Doesn't check if worker has crashed

**User Impact:**

- Docker reports container as "healthy" even when worker is completely broken
- Orchestration systems (Kubernetes, Docker Swarm) won't restart failed workers
- Silent failures in extraction pipeline
- No alerting when worker crashes

**Recommendation:**

```dockerfile
# OPTION 1: Check process is running (requires ps)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "apps.worker.main" || exit 1

# OPTION 2: Add health check endpoint to worker
# apps/worker/main.py should expose a simple HTTP server on port 8001
# GET /health returns 200 if worker is healthy, connections OK
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# OPTION 3: Check worker can access dependencies (most thorough)
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "
import sys
from packages.common.redis_client import get_redis_client
from packages.graph.neo4j_writer import Neo4jWriter
try:
    # Quick connection check
    redis_client = get_redis_client()
    redis_client.ping()
    sys.exit(0)
except Exception as e:
    print(f'Health check failed: {e}', file=sys.stderr)
    sys.exit(1)
" || exit 1
```

**Remediation Effort:** Medium (2 hours to implement proper health check)

---

## LOW Severity Findings

### L-1: Build Cache Mount Errors Are Silent

**Location:** `/home/jmagar/code/taboot/docker/app/Dockerfile:42,52`
**Severity:** 🟢 LOW
**Impact:** Build may succeed even if cache mount fails

**Issue Description:**

The `--mount=type=cache` directives will silently fall back to no caching if they fail. This is usually fine, but errors should be logged.

**Code:**

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
```

**Recommendation:**

Add `|| echo "WARNING: Cache mount failed, build may be slower"` if you want visibility, but this is low priority since it's just a performance optimization.

---

## Summary of Required Changes

### CRITICAL (Fix Before Merge)

1. **C-1:** Add try-catch around `auth.api.getSession()` with fail-closed error handling
2. **C-2:** Add try-catch around `csrfMiddleware()` with validation and fail-closed behavior
3. **C-3:** Add `SHELL ["/bin/bash", "-euo", "pipefail", "-c"]` and explicit error checking to Docker builds

### HIGH (Fix Before Production)

4. **H-1:** Configure supervisord restart limits and crash detection
5. **H-2:** Add validation that `server.js` exists before starting web process

### MEDIUM (Fix in Next Sprint)

6. **M-1:** Add error handling for cookie parsing
7. **M-2:** Implement proper health check for worker container

### LOW (Optional)

8. **L-1:** Add cache mount failure warnings

---

## Testing Recommendations

After implementing fixes, test these failure scenarios:

### Authentication Failures
```bash
# Test auth service unavailable
docker compose stop taboot-db
# Access protected route - should see 503 error, not crash

# Test malformed session cookie
curl -b "better-auth.session_token=CORRUPTED_VALUE" http://localhost:3000/dashboard
# Should redirect to sign-in, not crash
```

### CSRF Failures
```bash
# Test CSRF with invalid token
curl -X POST http://localhost:3000/api/auth/password \
  -H "x-csrf-token: INVALID" \
  -H "Content-Type: application/json"
# Should see 403 error, not crash

# Test CSRF with missing secret
unset CSRF_SECRET
# App should fail to start with clear error message
```

### Docker Build Failures
```bash
# Test build with TypeScript errors
# Add intentional error to apps/web/middleware.ts
docker build -f docker/app/Dockerfile .
# Should fail with clear error message pointing to TypeScript error

# Test build with missing server.js
# Corrupt Next.js build in builder stage
docker build -f docker/app/Dockerfile .
# Should fail with "server.js not found" error
```

### Supervisor Crash Loops
```bash
# Test API crash
docker exec taboot-app kill -9 $(pgrep uvicorn)
# Check: supervisord should restart API but stop after 3 attempts

# Test web crash
docker exec taboot-app kill -9 $(pgrep node)
# Check: supervisord should restart web but stop after 3 attempts
```

---

## Conclusion

This PR introduces **3 CRITICAL silent failure risks** that could cause production outages:

1. Unhandled auth session errors → entire middleware crashes
2. Unhandled CSRF errors → security bypass or crashes
3. Silent Docker build failures → broken images deployed to production

**RECOMMENDATION:** ❌ **DO NOT MERGE** until critical issues (C-1, C-2, C-3) are resolved.

The authentication and CSRF middleware are **security-critical paths** that handle every request. Any unhandled exception in these paths will crash the entire application. This is a **fail-open** security model (crash = service unavailable = no security enforcement).

**Required Actions Before Merge:**
1. Add comprehensive error handling to middleware.ts (C-1, C-2)
2. Add explicit error checking to Dockerfile RUN commands (C-3)
3. Test all error paths with the scenarios above
4. Add error handling tests to the test suite

**Estimated Remediation Time:** 4-6 hours

---

## Appendix: Error Handling Best Practices

### Fail-Closed vs Fail-Open

**Fail-Closed (Recommended):**
- On error, deny access/action
- Better for security-critical paths
- Example: Auth error → deny access

**Fail-Open (Dangerous):**
- On error, allow access/action
- Only use for non-critical features
- Example: Analytics error → continue

### Error Logging Requirements

Every caught error should log:
1. **What operation failed** - Context about what was being attempted
2. **Why it failed** - Error message and stack trace
3. **Who it affected** - User ID, request ID, session ID
4. **When it happened** - Timestamp (automatic in most loggers)
5. **How to fix it** - For operators, what actions to take

### Example of Good Error Handling

```typescript
try {
  const session = await auth.api.getSession({ headers: request.headers });
  isAuthenticated = !!session?.user;
} catch (error) {
  // 1. WHAT: Authentication session check
  // 2. WHY: Error message and stack
  // 3. WHO: Request context (pathname, IP)
  // 4. WHEN: Automatic timestamp
  // 5. HOW: "Check auth service health"
  logger.error('Authentication session check failed - denying access (fail-closed)', {
    operation: 'auth.api.getSession',
    pathname: request.nextUrl.pathname,
    error: error instanceof Error ? error.message : String(error),
    stack: error instanceof Error ? error.stack : undefined,
    clientIp: request.headers.get('x-forwarded-for') || 'unknown',
    userAgent: request.headers.get('user-agent'),
    recommendation: 'Check database and auth service connectivity',
  });

  // FAIL CLOSED: Deny access on error
  isAuthenticated = false;

  // USER FEEDBACK: Clear, actionable error message
  if (isProtectedRoute) {
    return NextResponse.json(
      {
        error: 'Authentication service temporarily unavailable',
        message: 'Please try again in a few moments',
        code: 'AUTH_SERVICE_ERROR',
      },
      { status: 503, headers: { 'Retry-After': '30' } }
    );
  }
}
```

---

**End of Report**
