# Soft Delete Context Middleware Integration

## Overview

This document describes the automatic soft delete context integration implemented across the web application. The context system ensures that all database delete operations have proper audit trail metadata (user ID, IP address, user-agent) without requiring manual context management in routes or services.

## Architecture

### Components

1. **Middleware Helper** (`apps/web/lib/soft-delete-context.ts`)
   - Extracts context from NextRequest and Session
   - Generates unique request IDs
   - Validates IP addresses (IPv4/IPv6)
   - Provides setup and cleanup functions

2. **Middleware Integration** (`apps/web/middleware.ts`)
   - Automatically sets context for authenticated API requests
   - Cleans up context after response using microtask queue
   - Handles errors gracefully (non-critical failures)

3. **Database Layer** (`packages-ts/db/src/middleware/soft-delete.ts`)
   - Retrieves context from global store using request ID
   - Applies context to soft delete operations
   - Creates audit trail with user/IP/user-agent metadata

## Flow Diagram

```
┌─────────────────┐
│  HTTP Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  middleware.ts                      │
│  1. Validate session                │
│  2. Generate request ID (UUID)      │
│  3. Extract IP, user-agent          │
│  4. Call setupSoftDeleteContext()   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  @taboot/db (global context store)  │
│  Map<requestId, {userId, IP, UA}>   │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Route Handler                      │
│  (e.g., /api/users/[id]/erase)      │
│  - Calls prisma.user.delete()       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Prisma Middleware                  │
│  1. Retrieve context by requestId   │
│  2. Convert DELETE to UPDATE        │
│  3. Set deletedAt, deletedBy        │
│  4. Create audit log entry          │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Response sent                      │
│  middleware.ts finally block:       │
│  - queueMicrotask() for cleanup     │
│  - clearSoftDeleteContext()         │
└─────────────────────────────────────┘
```

## Implementation Details

### 1. Context Setup (Middleware)

**File:** `apps/web/middleware.ts`

```typescript
// Setup context for authenticated API requests
const session = await getValidSession(request);
if (session) {
  try {
    softDeleteRequestId = setupSoftDeleteContext(request, session);
  } catch (error) {
    // Log error but don't fail request - context is non-critical
    logger.error('Failed to setup soft delete context', { ... });
  }
}
```

**When:** After session validation, before route handler execution  
**For:** All authenticated `/api/*` routes (except CSRF-excluded routes)

### 2. Context Extraction

**File:** `apps/web/lib/soft-delete-context.ts`

```typescript
export function extractContextMetadata(
  request: NextRequest,
  session: Session | null
): SoftDeleteContextMetadata {
  return {
    requestId: crypto.randomUUID(),
    userId: session?.user?.id,
    ipAddress: getClientIp(request), // Respects TRUST_PROXY env var
    userAgent: request.headers.get('user-agent') || undefined,
  };
}
```

**Security:** IP extraction follows same proxy trust logic as rate limiting (see `TRUST_PROXY` env var)

### 3. Context Cleanup

**File:** `apps/web/middleware.ts`

```typescript
finally {
  if (softDeleteRequestId) {
    const requestId = softDeleteRequestId;
    queueMicrotask(() => {
      try {
        cleanupSoftDeleteContext(requestId);
      } catch (error) {
        logger.error('Failed to cleanup soft delete context', { ... });
      }
    });
  }
}
```

**Why microtask?** Ensures response has been sent before cleanup  
**Error handling:** Cleanup errors are logged but not propagated

## Route Integration

### No Manual Context Management Required

Routes that perform deletions **do not** need manual context management:

```typescript
// ❌ OLD: Manual context management
const requestId = generateRequestId();
setSoftDeleteContext(requestId, { userId, ipAddress, userAgent });
try {
  await prisma.user.delete({ where: { id: userId } });
} finally {
  clearSoftDeleteContext(requestId);
}

// ✅ NEW: Automatic context (via middleware)
await prisma.user.delete({ where: { id: userId } });
// Context automatically available from middleware
```

### Example: User Erasure Route

**File:** `apps/web/app/api/users/[id]/erase/route.ts`

```typescript
/**
 * SOFT DELETE CONTEXT:
 * Soft delete context (user ID, IP, user-agent) is automatically set by
 * apps/web/middleware.ts for all authenticated API requests.
 * No manual context management is needed in this route.
 * All Prisma delete operations will have proper audit trail metadata.
 */
export async function POST(request: NextRequest, { params }) {
  const session = await auth.api.getSession({ headers: request.headers });
  // ... authorization checks ...
  
  // Context automatically available from middleware
  await prisma.user.update({
    where: { id: userId },
    data: { deletedAt: new Date(), deletedBy: session.user.id }
  });
  
  // Audit log created automatically by Prisma middleware
}
```

## Service Integration

### Profile Service

**File:** `apps/web/lib/services/profile-service.ts`

```typescript
/**
 * SOFT DELETE CONTEXT:
 * Soft delete context (user ID, IP, user-agent) is automatically set by
 * apps/web/middleware.ts for all authenticated API requests.
 * No manual context management is needed in this service.
 */
```

**Note:** Current profile service only performs updates (no deletions), but context would be automatically available if needed.

## Environment Variables

### TRUST_PROXY

**Purpose:** Controls whether to trust proxy headers for IP extraction  
**Values:** `"true"` or `"false"` (default: `"false"`)

**Security Warning:**
- Only set to `"true"` if behind verified reverse proxy (Cloudflare, nginx, AWS ALB)
- When `"false"`, X-Forwarded-For headers are ignored to prevent IP spoofing

**Example (.env):**
```bash
# Production behind Cloudflare
TRUST_PROXY="true"

# Development (direct connection)
TRUST_PROXY="false"
```

## Error Handling

### Non-Critical Failures

Context setup and cleanup failures are **non-critical**:

1. **Setup failure:** Request continues, operations use fallback context (`userId: 'system'`)
2. **Cleanup failure:** Memory leak risk, but logged for monitoring

**Rationale:** Context enhances audit trails but shouldn't block operations

### Critical Failures

Soft delete operations **do** fail if:
- Prisma middleware encounters database errors
- Audit log creation fails (per GDPR requirements)

## Testing

### Manual Testing

```bash
# 1. Start services
docker compose up taboot-api taboot-web taboot-db

# 2. Authenticate and get session token
curl -X POST http://localhost:4211/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# 3. Perform deletion with context
curl -X DELETE http://localhost:4211/api/users/USER_ID \
  -H "Authorization: Bearer SESSION_TOKEN" \
  -H "X-Forwarded-For: 203.0.113.42"

# 4. Verify audit log has IP and user-agent
SELECT * FROM audit_log WHERE target_id = 'USER_ID' ORDER BY created_at DESC LIMIT 1;
```

### Unit Testing

Context functions are testable in isolation:

```typescript
import { extractContextMetadata, generateRequestId } from '@/lib/soft-delete-context';

describe('soft-delete-context', () => {
  it('generates valid UUID request IDs', () => {
    const id = generateRequestId();
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  });

  it('extracts context from request and session', () => {
    const request = new NextRequest('http://localhost/api/test', {
      headers: { 'user-agent': 'test-agent', 'x-forwarded-for': '203.0.113.42' }
    });
    const session = { user: { id: 'user-123' } };
    
    const context = extractContextMetadata(request, session);
    expect(context.userId).toBe('user-123');
    expect(context.userAgent).toBe('test-agent');
    // IP extraction depends on TRUST_PROXY env var
  });
});
```

## Migration Notes

### Existing Routes

Routes that manually manage context can be simplified:

**Before:**
```typescript
import { setSoftDeleteContext, clearSoftDeleteContext } from '@taboot/db';

export async function DELETE(request: NextRequest) {
  const requestId = crypto.randomUUID();
  const ipAddress = getClientIp(request);
  const userAgent = request.headers.get('user-agent');
  
  setSoftDeleteContext(requestId, { userId, ipAddress, userAgent });
  try {
    await prisma.user.delete({ where: { id } });
  } finally {
    clearSoftDeleteContext(requestId);
  }
}
```

**After:**
```typescript
// No imports needed - middleware handles context

export async function DELETE(request: NextRequest) {
  // Context automatically available
  await prisma.user.delete({ where: { id } });
}
```

### New Routes

New routes automatically inherit context behavior:

```typescript
// Just perform database operations normally
export async function POST(request: NextRequest) {
  const session = await auth.api.getSession({ headers: request.headers });
  
  // Context automatically includes:
  // - userId: session.user.id
  // - ipAddress: extracted from request
  // - userAgent: extracted from request
  
  await prisma.someModel.delete({ where: { id } });
  // Audit trail created automatically
}
```

## Monitoring

### Key Metrics

1. **Context setup success rate:** Monitor `Failed to setup soft delete context` errors
2. **Context cleanup success rate:** Monitor `Failed to cleanup soft delete context` errors
3. **Memory leak detection:** Check context store size over time (should be ~0 between requests)

### Logging

All context operations are logged:

```typescript
logger.error('Failed to setup soft delete context', {
  pathname: request.nextUrl.pathname,
  error: error.message
});

logger.error('Failed to cleanup soft delete context', {
  requestId,
  error: error.message
});
```

## References

- **Middleware:** `apps/web/middleware.ts`
- **Context Helper:** `apps/web/lib/soft-delete-context.ts`
- **Database Middleware:** `packages-ts/db/src/middleware/soft-delete.ts`
- **CSRF Integration:** `apps/web/lib/csrf.ts` (similar pattern)
- **Rate Limiting:** `apps/web/lib/rate-limit.ts` (similar IP extraction)

## Future Enhancements

1. **Context Store Metrics:** Add Prometheus metrics for context store size
2. **Request Tracing:** Include request ID in all log messages for correlation
3. **Context Validation:** Add runtime validation of context before database operations
4. **Testing Utilities:** Provide test helpers for context setup/teardown
