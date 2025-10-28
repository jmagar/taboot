# Soft Delete: Context API & Audit Trail

## Overview

Taboot implements **soft delete with automatic audit trail** for user account deletions. This provides GDPR compliance (Article 30 audit requirements), protection against accidental deletions, and full restoration capability within a configurable retention period.

**Key Features**:
- Soft delete middleware converts `DELETE` to `UPDATE`
- Context API tracks who, when, from where
- Automatic filtering of deleted records
- 90-day retention with hard cleanup
- Full restoration capability

---

## Table of Contents

1. [Soft Delete Middleware Architecture](#soft-delete-middleware-architecture)
2. [Context API](#context-api)
3. [Middleware Auto-Context Pattern](#middleware-auto-context-pattern)
4. [Audit Trail Requirements](#audit-trail-requirements)
5. [Implementation Examples](#implementation-examples)
6. [Restoration Process](#restoration-process)
7. [Hard Cleanup](#hard-cleanup)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Soft Delete Middleware Architecture

### Overview

Soft delete is implemented using **Prisma Client Extensions** (Prisma 6.x), replacing the older middleware pattern. This provides type-safe query interception and better composability.

**File**: `packages-ts/db/src/middleware/soft-delete.ts`

### How It Works

```typescript
export function softDeleteMiddleware(requestId?: string) {
  return {
    query: {
      user: {
        // 1. Convert DELETE to UPDATE (sets deletedAt timestamp)
        async delete({ args, query }: any) {
          const context = getContext(requestId);
          const userId = (args as any).where?.id;

          return (query as any)({
            ...args,
            data: {
              deletedAt: new Date(),
              deletedBy: context.userId || 'system',
            },
          });
        },

        // 2. Filter deleted records from queries
        async findMany({ args, query }: any) {
          const where = (args as any).where || {};

          if (where.deletedAt === undefined) {
            return query({
              ...args,
              where: { ...where, deletedAt: null },
            });
          }

          return query(args);
        },
      },
    },
  };
}
```

### Key Behaviors

| Operation | Original | Transformed |
|-----------|----------|-------------|
| `user.delete({ where: { id } })` | `DELETE FROM user WHERE id = $1` | `UPDATE user SET deleted_at = NOW(), deleted_by = $2 WHERE id = $1` |
| `user.findMany()` | `SELECT * FROM user` | `SELECT * FROM user WHERE deleted_at IS NULL` |
| `user.findMany({ where: { deletedAt: { not: null } } })` | Explicitly query deleted | No filter added (query deleted records) |

### Database Schema

**File**: `packages-ts/db/prisma/schema.prisma`

```prisma
model User {
  id               String      @id
  name             String
  email            String
  emailVerified    Boolean     @default(false)
  image            String?
  createdAt        DateTime    @default(now())
  updatedAt        DateTime    @default(now()) @updatedAt

  // Soft delete fields
  deletedAt        DateTime?   @map("deleted_at")
  deletedBy        String?     @map("deleted_by")

  sessions         Session[]
  accounts         Account[]
  twofactors       TwoFactor[]

  @@unique([email])
  @@index([deletedAt])  // ← Index for filtering deleted records
  @@map("user")
  @@schema("auth")
}
```

---

## Context API

### Purpose

The context API tracks **who**, **when**, and **from where** deletions occur for audit trail compliance.

**File**: `packages-ts/db/src/middleware/soft-delete.ts`

### Context Interface

```typescript
interface SoftDeleteContext {
  userId?: string;      // ID of user performing deletion
  ipAddress?: string;   // Client IP address (proxy-aware)
  userAgent?: string;   // Client user agent string
}
```

### Context Storage

```typescript
// Global context store (keyed by request ID)
const contextStore = new Map<string, SoftDeleteContext>();

/**
 * Set current user context for soft delete operations
 */
export function setSoftDeleteContext(requestId: string, context: SoftDeleteContext): void {
  contextStore.set(requestId, context);
}

/**
 * Get current user context
 */
function getContext(requestId?: string): SoftDeleteContext {
  if (!requestId) {
    return {};
  }
  return contextStore.get(requestId) || {};
}

/**
 * Clear context after request completes
 */
export function clearSoftDeleteContext(requestId: string): void {
  contextStore.delete(requestId);
}
```

### Usage Pattern

**1. Set context at request start**:

```typescript
import { setSoftDeleteContext } from '@taboot/db';

const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;
setSoftDeleteContext(requestId, {
  userId: session.user.id,
  ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
  userAgent: request.headers.get('user-agent') || 'unknown',
});
```

**2. Perform operations** (context automatically applied):

```typescript
await prisma.user.delete({ where: { id: userId } });
// → Sets deletedAt = NOW(), deletedBy = context.userId
```

**3. Clear context after request**:

```typescript
clearSoftDeleteContext(requestId);
```

### Why Request ID?

Request IDs allow **concurrent request handling** without context collision:

- Web server handles multiple requests simultaneously
- Each request has unique ID → unique context
- Context for Request A doesn't leak into Request B

**Example**:

```
Request A (req-1234): User Alice deletes account → context.userId = "alice123"
Request B (req-5678): User Bob deletes account → context.userId = "bob456"

Without request ID: Race condition (Bob's deletion might be logged as Alice's)
With request ID: Safe concurrent handling (correct userId in each context)
```

---

## Middleware Auto-Context Pattern

### Current State: Manual Context Management

**Problem**: API routes must manually set/clear context

```typescript
// apps/web/app/api/users/[id]/delete/route.ts
export async function DELETE(request: NextRequest) {
  const requestId = generateRequestId();
  const session = await auth.api.getSession({ headers: request.headers });

  // Manual context setup
  setSoftDeleteContext(requestId, {
    userId: session.user.id,
    ipAddress: getClientIp(request),
    userAgent: request.headers.get('user-agent'),
  });

  try {
    await prisma.user.delete({ where: { id: userId } });
  } finally {
    // Manual cleanup
    clearSoftDeleteContext(requestId);
  }
}
```

**Issues**:
- Boilerplate in every API route
- Easy to forget cleanup (memory leak)
- No centralized enforcement

### Target: Automatic Context in Middleware

**Goal**: Middleware automatically sets context for all authenticated requests

**File**: `apps/web/middleware.ts` (to be updated)

```typescript
import { setSoftDeleteContext, clearSoftDeleteContext } from '@taboot/db';
import { verifySession } from '@taboot/auth/edge';
import { v4 as uuidv4 } from 'uuid';

export async function middleware(request: NextRequest) {
  const requestId = uuidv4();
  let contextSet = false;

  try {
    // Verify session for authenticated requests
    const session = await verifySession({
      sessionToken: getSessionToken(request),
      secret: process.env.AUTH_SECRET!,
    });

    if (session?.user) {
      // Automatically set context for authenticated requests
      setSoftDeleteContext(requestId, {
        userId: session.user.id,
        ipAddress: getClientIp(request),
        userAgent: request.headers.get('user-agent') || undefined,
      });
      contextSet = true;

      // Pass requestId in header for route handlers
      const response = NextResponse.next();
      response.headers.set('x-request-id', requestId);
      return response;
    }

    return NextResponse.next();
  } finally {
    // Automatically clean up context after request
    if (contextSet) {
      // Delay cleanup to allow async operations to complete
      setTimeout(() => clearSoftDeleteContext(requestId), 100);
    }
  }
}
```

### Route Handler Usage (After Middleware Update)

```typescript
// apps/web/app/api/users/[id]/delete/route.ts
export async function DELETE(request: NextRequest) {
  const requestId = request.headers.get('x-request-id') || generateRequestId();

  // ✅ Context already set by middleware - no manual setup needed
  await prisma.user.delete({ where: { id: userId } });

  // ✅ Middleware handles cleanup - no manual cleanup needed
  return NextResponse.json({ success: true });
}
```

### Implementation Checklist

- [ ] **Add request ID generation** in middleware (`uuid` or `Date.now() + random`)
- [ ] **Set context automatically** for authenticated requests
- [ ] **Pass request ID in header** (`x-request-id`) for route handlers
- [ ] **Clean up context after request** (with delay for async operations)
- [ ] **Test concurrent requests** (ensure no context collision)
- [ ] **Update API routes** to use `x-request-id` header instead of manual context
- [ ] **Document pattern** for new API routes

---

## Audit Trail Requirements

### GDPR Article 30: Record of Processing Activities

**Requirement**: Maintain records of all data processing activities, including:
- Who performed the operation
- When it occurred
- What data was affected
- Why the operation was performed (if applicable)

### Audit Log Schema

**File**: `packages-ts/db/prisma/schema.prisma`

```prisma
model AuditLog {
  id         String   @id @default(cuid())
  userId     String?  @map("user_id")       // Who
  targetId   String   @map("target_id")     // What (target resource ID)
  targetType String   @map("target_type")   // What (resource type)
  action     String                         // What (operation type)
  metadata   Json?                          // Additional context
  ipAddress  String?  @map("ip_address")    // From where
  userAgent  String?  @map("user_agent")    // Client details
  createdAt  DateTime @default(now()) @map("created_at")  // When

  @@index([targetId, targetType])
  @@index([userId])
  @@index([createdAt])
  @@map("audit_log")
  @@schema("auth")
}
```

### Audit Log Entry Example

```typescript
// Soft delete operation
await prisma.user.delete({ where: { id: 'user123' } });
// → User.deletedAt = NOW(), User.deletedBy = 'current_user_id'

// Corresponding audit log (created separately)
await prisma.auditLog.create({
  data: {
    userId: 'current_user_id',
    action: 'USER_DELETE',
    targetType: 'User',
    targetId: 'user123',
    metadata: {
      reason: 'user_requested',
      retention_days: 90,
    },
    ipAddress: '192.168.1.100',
    userAgent: 'Mozilla/5.0 ...',
  },
});
```

### SQL Injection Protection

**SECURITY NOTE**: Audit logging uses raw SQL to avoid middleware recursion. Prisma tagged template literals provide automatic parameterization.

**File**: `packages-ts/db/src/middleware/soft-delete.ts`

```typescript
/**
 * Log audit trail for data operations
 *
 * SECURITY: Uses raw SQL to avoid middleware recursion.
 * SQL injection protection is provided by:
 * 1. Prisma tagged template literals (automatic parameterization)
 * 2. JSON.stringify() serialization before parameterization
 * 3. PostgreSQL JSONB type validation
 *
 * All ${...} values are sent as query parameters ($1, $2, etc.),
 * NOT string interpolation. Verified safe by security audit.
 */
async function logAudit(
  prisma: any,
  params: {
    userId?: string;
    targetId: string;
    targetType: string;
    action: string;
    metadata?: Record<string, any>;
    ipAddress?: string;
    userAgent?: string;
  }
): Promise<void> {
  try {
    // SAFE: Prisma tagged templates use parameterized queries
    await prisma.$executeRaw`
      INSERT INTO "audit_log" (
        id, user_id, target_id, target_type, action,
        metadata, ip_address, user_agent, created_at
      ) VALUES (
        gen_random_uuid()::text,
        ${params.userId || null},
        ${params.targetId},
        ${params.targetType},
        ${params.action},
        ${params.metadata ? JSON.stringify(params.metadata) : null}::jsonb,
        ${params.ipAddress || null},
        ${params.userAgent || null},
        NOW()
      )
    `;
  } catch (error) {
    console.error('Failed to write audit log:', error);
  }
}
```

**Why This Is Safe**:

1. **Prisma tagged templates**: All `${...}` values become parameterized query placeholders (`$1`, `$2`, etc.)
2. **No string concatenation**: Never uses `+` or template strings for SQL construction
3. **Type validation**: PostgreSQL validates JSONB structure before insert

**See**: `/home/jmagar/code/taboot/docs/security/AUDIT_SQL_INJECTION_AUDIT_LOG.md` for full security audit

---

## Implementation Examples

### Example 1: User Self-Deletion

```typescript
// apps/web/app/api/profile/delete/route.ts
import { prisma, setSoftDeleteContext, clearSoftDeleteContext } from '@taboot/db';
import { auth } from '@taboot/auth';
import { NextRequest, NextResponse } from 'next/server';

export async function DELETE(request: NextRequest) {
  const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  try {
    // 1. Verify authentication
    const session = await auth.api.getSession({ headers: request.headers });
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // 2. Set soft delete context
    setSoftDeleteContext(requestId, {
      userId: session.user.id,
      ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
      userAgent: request.headers.get('user-agent') || 'unknown',
    });

    // 3. Soft delete user (converts to UPDATE)
    await prisma.user.delete({
      where: { id: session.user.id },
    });

    // 4. Create audit log entry
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        action: 'USER_DELETE',
        targetType: 'User',
        targetId: session.user.id,
        metadata: {
          reason: 'user_requested',
          retention_days: 90,
        },
        ipAddress: request.headers.get('x-forwarded-for') || undefined,
        userAgent: request.headers.get('user-agent') || undefined,
      },
    });

    return NextResponse.json({
      success: true,
      message: 'Account deleted. Data will be retained for 90 days.',
    });
  } finally {
    // 5. Clean up context
    clearSoftDeleteContext(requestId);
  }
}
```

### Example 2: Admin Deletion of User

```typescript
// apps/web/app/api/admin/users/[id]/delete/route.ts
import { prisma, setSoftDeleteContext, clearSoftDeleteContext } from '@taboot/db';
import { auth } from '@taboot/auth';
import { checkAdminAuthorization } from '@/lib/auth-helpers';
import { NextRequest, NextResponse } from 'next/server';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;

  try {
    // 1. Verify authentication + authorization
    const session = await auth.api.getSession({ headers: request.headers });
    const authError = checkAdminAuthorization(session, id, 'deletion');
    if (authError) {
      return authError;
    }

    // 2. Set soft delete context (admin context)
    setSoftDeleteContext(requestId, {
      userId: session!.user.id,
      ipAddress: request.headers.get('x-forwarded-for') || 'unknown',
      userAgent: request.headers.get('user-agent') || 'unknown',
    });

    // 3. Soft delete target user
    await prisma.user.delete({
      where: { id },
    });

    // 4. Create audit log entry
    await prisma.auditLog.create({
      data: {
        userId: session!.user.id,
        action: 'USER_DELETE_ADMIN',
        targetType: 'User',
        targetId: id,
        metadata: {
          reason: 'admin_requested',
          retention_days: 90,
        },
        ipAddress: request.headers.get('x-forwarded-for') || undefined,
        userAgent: request.headers.get('user-agent') || undefined,
      },
    });

    return NextResponse.json({
      success: true,
      message: 'User deleted by admin. Data retained for 90 days.',
    });
  } finally {
    // 5. Clean up context
    clearSoftDeleteContext(requestId);
  }
}
```

### Example 3: Querying Deleted Users (Admin)

```typescript
// Query only deleted users
const deletedUsers = await prisma.user.findMany({
  where: {
    deletedAt: { not: null },  // Explicit query for deleted records
  },
  orderBy: {
    deletedAt: 'desc',
  },
});

// Query users deleted in last 30 days
const recentlyDeleted = await prisma.user.findMany({
  where: {
    deletedAt: {
      gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    },
  },
});
```

---

## Restoration Process

### Helper Function: `restoreUser`

**File**: `packages-ts/db/src/middleware/soft-delete.ts`

```typescript
/**
 * Helper function to restore a soft-deleted user
 */
export async function restoreUser(
  prisma: any,
  userId: string,
  restoredBy: string,
  context?: Pick<SoftDeleteContext, 'ipAddress' | 'userAgent'>
): Promise<void> {
  // 1. Get the deleted user (bypass soft delete filter)
  const user = await prisma.user.findUnique({
    where: { id: userId, deletedAt: { not: null } },
  });

  if (!user || !user.deletedAt) {
    throw new Error('User not found or not deleted');
  }

  // 2. Restore user
  await prisma.user.update({
    where: { id: userId },
    data: {
      deletedAt: null,
      deletedBy: null,
    },
  });

  // 3. Log restoration
  await logAudit(prisma, {
    userId: restoredBy,
    targetId: userId,
    targetType: 'User',
    action: 'RESTORE',
    metadata: {
      originalDeletedAt: user.deletedAt,
      originalDeletedBy: user.deletedBy,
    },
    ipAddress: context?.ipAddress,
    userAgent: context?.userAgent,
  });
}
```

### Example API Endpoint: Restore User

```typescript
// apps/web/app/api/admin/users/[id]/restore/route.ts
import { prisma, restoreUser } from '@taboot/db';
import { auth } from '@taboot/auth';
import { checkAdminAuthorization } from '@/lib/auth-helpers';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  try {
    // 1. Verify admin authorization
    const session = await auth.api.getSession({ headers: request.headers });

    // Restoration is admin-only (deny self-restoration)
    if (session?.user.id === id) {
      return NextResponse.json(
        { error: 'Users cannot restore their own accounts. Contact support.' },
        { status: 403 }
      );
    }

    const authError = checkAdminAuthorization(session, id, 'restoration');
    if (authError) {
      return authError;
    }

    // 2. Restore user
    await restoreUser(prisma, id, session!.user.id, {
      ipAddress: request.headers.get('x-forwarded-for') || undefined,
      userAgent: request.headers.get('user-agent') || undefined,
    });

    return NextResponse.json({
      success: true,
      message: 'User account restored successfully',
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to restore user',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
```

---

## Hard Cleanup

### Cleanup Script

**File**: `apps/web/scripts/cleanup-deleted-users.ts`

```typescript
import { PrismaClient } from '@taboot/db';

const prisma = new PrismaClient();

async function cleanupDeletedUsers(
  retentionDays: number = 90,
  dryRun: boolean = false
) {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

  console.log(`Retention cutoff: ${cutoffDate.toISOString()}`);
  console.log(`Dry run: ${dryRun}`);

  // Find users deleted before cutoff date
  const usersToHardDelete = await prisma.user.findMany({
    where: {
      deletedAt: {
        lt: cutoffDate,
      },
    },
    select: {
      id: true,
      email: true,
      deletedAt: true,
      deletedBy: true,
    },
  });

  console.log(`Found ${usersToHardDelete.length} users to hard delete`);

  if (dryRun) {
    console.log('Dry run - no changes made');
    console.table(usersToHardDelete);
    return;
  }

  // Hard delete users (bypass soft delete middleware)
  for (const user of usersToHardDelete) {
    await prisma.$executeRaw`
      DELETE FROM auth.user WHERE id = ${user.id}
    `;
    console.log(`Hard deleted user: ${user.id} (${user.email})`);
  }

  console.log('Cleanup complete');
}

// CLI usage
const retentionDays = parseInt(process.env.RETENTION_DAYS || '90');
const dryRun = process.argv.includes('--dry-run');

cleanupDeletedUsers(retentionDays, dryRun).catch(console.error).finally(() => prisma.$disconnect());
```

### Running Cleanup

```bash
# Dry run (see what would be deleted)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --dry-run

# Production cleanup (default 90-day retention)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts

# Custom retention period (e.g., 30 days)
RETENTION_DAYS=30 pnpm tsx apps/web/scripts/cleanup-deleted-users.ts
```

### Automated Cleanup (Cron)

**Option 1: Docker Compose Service** (recommended)

```yaml
# docker-compose.yaml
services:
  taboot-cleanup:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./apps/web:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - RETENTION_DAYS=90
    command: sh -c "while true; do pnpm tsx scripts/cleanup-deleted-users.ts; sleep 86400; done"
```

**Option 2: System Cron**

```bash
# /etc/cron.d/taboot-cleanup
0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts >> /var/log/taboot-cleanup.log 2>&1
```

---

## Testing

### Unit Tests

**File**: `packages-ts/db/src/__tests__/soft-delete.test.ts` (to be created)

```typescript
import { PrismaClient } from '@taboot/db';
import { setSoftDeleteContext, clearSoftDeleteContext } from '../middleware/soft-delete';

const prisma = new PrismaClient();

describe('Soft Delete Middleware', () => {
  const requestId = 'test-request-123';

  beforeEach(async () => {
    // Clear test data
    await prisma.$executeRaw`DELETE FROM auth.user WHERE email LIKE 'test-%'`;
  });

  afterEach(() => {
    clearSoftDeleteContext(requestId);
  });

  it('should convert DELETE to UPDATE', async () => {
    // Create test user
    const user = await prisma.user.create({
      data: {
        id: 'test-user-1',
        email: 'test-delete@example.com',
        name: 'Test User',
      },
    });

    // Set context
    setSoftDeleteContext(requestId, { userId: 'admin' });

    // Delete user (should soft delete)
    await prisma.user.delete({ where: { id: user.id } });

    // Verify soft delete
    const deletedUser = await prisma.user.findUnique({
      where: { id: user.id, deletedAt: { not: null } },
    });

    expect(deletedUser).toBeTruthy();
    expect(deletedUser?.deletedAt).toBeInstanceOf(Date);
    expect(deletedUser?.deletedBy).toBe('admin');
  });

  it('should filter deleted users from queries', async () => {
    // Create and soft delete user
    const user = await prisma.user.create({
      data: {
        id: 'test-user-2',
        email: 'test-filter@example.com',
        name: 'Test User',
      },
    });

    await prisma.user.update({
      where: { id: user.id },
      data: { deletedAt: new Date(), deletedBy: 'system' },
    });

    // Query should not include deleted user
    const activeUsers = await prisma.user.findMany({
      where: { email: 'test-filter@example.com' },
    });

    expect(activeUsers).toHaveLength(0);

    // Explicit query for deleted users should work
    const deletedUsers = await prisma.user.findMany({
      where: {
        email: 'test-filter@example.com',
        deletedAt: { not: null },
      },
    });

    expect(deletedUsers).toHaveLength(1);
  });
});
```

### Integration Tests

```bash
# Run all soft delete tests
pnpm --filter @taboot/db test middleware/soft-delete

# Run with coverage
pnpm --filter @taboot/db test --coverage middleware/soft-delete
```

---

## Troubleshooting

### Issue 1: Context Not Applied

**Symptom**: `deletedBy` is `null` or `'system'` instead of user ID

**Cause**: Context not set before deletion

**Solution**:

```typescript
// ❌ Wrong - context not set
await prisma.user.delete({ where: { id } });
// → deletedBy = 'system'

// ✅ Correct - set context first
setSoftDeleteContext(requestId, { userId: session.user.id });
await prisma.user.delete({ where: { id } });
// → deletedBy = session.user.id
```

### Issue 2: Deleted Records Appearing in Queries

**Symptom**: Soft-deleted users still show up in `findMany()` results

**Cause**: Middleware not applied to Prisma client

**Solution**: Ensure Prisma client uses soft delete extension

```typescript
// packages-ts/db/src/client.ts
import { PrismaClient } from '../generated/prisma';
import { softDeleteMiddleware } from './middleware/soft-delete';

export const prisma = new PrismaClient().$extends(softDeleteMiddleware());
```

### Issue 3: Memory Leak from Uncleaned Context

**Symptom**: Memory usage grows over time

**Cause**: `clearSoftDeleteContext()` not called after requests

**Solution**: Always use try-finally pattern

```typescript
const requestId = generateRequestId();
setSoftDeleteContext(requestId, context);

try {
  await performOperations();
} finally {
  clearSoftDeleteContext(requestId);  // ← Always cleanup
}
```

### Issue 4: Concurrent Request Context Collision

**Symptom**: Wrong user ID in `deletedBy` for some deletions

**Cause**: Request ID collision or missing request ID

**Solution**: Use UUID or high-entropy random ID

```typescript
// ❌ Wrong - timestamp only (collision risk)
const requestId = `req-${Date.now()}`;

// ✅ Correct - timestamp + random (low collision risk)
const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2)}`;

// ✅ Best - UUID v4 (virtually no collision risk)
import { v4 as uuidv4 } from 'uuid';
const requestId = uuidv4();
```

---

## Related Documentation

- `docs/ADMIN_OPERATIONS.md` - Admin authorization patterns
- `docs/CSRF_XSS_RISKS.md` - CSRF protection and XSS mitigation
- `CLAUDE.md` - Soft delete overview and usage
- `packages-ts/db/src/middleware/soft-delete.ts` - Implementation
- `apps/web/scripts/cleanup-deleted-users.ts` - Hard cleanup script

---

## Summary

**Architecture**: Prisma Client Extensions for type-safe query interception

**Context API**: Track who, when, from where for audit trail

**Middleware Auto-Context**: Automatic context setup/cleanup (to be implemented)

**Audit Trail**: Full GDPR Article 30 compliance with audit logging

**Restoration**: Admin-only restoration within retention period

**Hard Cleanup**: Scheduled script for permanent deletion after retention expires
