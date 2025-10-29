# Admin Operations: Authorization & Security

## Overview

Taboot implements **fail-closed admin authorization** for privileged operations like user account erasure, restoration, and management. This document explains the authorization pattern, configuration requirements, security design, and testing procedures.

**Key Principle**: Fail closed on admin operations - deny access when configuration is missing or validation fails.

---

## Table of Contents

1. [Authorization Pattern](#authorization-pattern)
2. [Configuration Requirements](#configuration-requirements)
3. [Fail-Closed Security Design](#fail-closed-security-design)
4. [Erase vs Restore Authorization](#erase-vs-restore-authorization)
5. [Implementation Details](#implementation-details)
6. [Testing Admin Endpoints](#testing-admin-endpoints)
7. [Security Considerations](#security-considerations)
8. [Audit Trail](#audit-trail)

---

## Authorization Pattern

### Core Helper: `checkAdminAuthorization`

**File**: `apps/web/lib/auth-helpers.ts`

```typescript
/**
 * Check if the current user is authorized to perform admin operations on a target user.
 *
 * Authorization logic:
 * 1. User can always operate on their own account (currentUserId === targetUserId)
 * 2. Admin can operate on any account (if ADMIN_USER_ID matches currentUserId)
 * 3. If attempting to operate on another user but ADMIN_USER_ID not configured → 503
 * 4. If attempting to operate on another user but not admin → 403
 *
 * @param session - The authenticated session
 * @param targetUserId - The user ID being operated on
 * @param operationName - Name of operation for logging (e.g., "erasure", "deletion")
 * @returns null if authorized, NextResponse with error if unauthorized
 */
export function checkAdminAuthorization(
  session: Session | null,
  targetUserId: string,
  operationName: string = 'operation'
): AdminAuthResult
```

**Return Type**:

```typescript
/**
 * Authorization result for admin operations.
 * - null: User is authorized to proceed
 * - NextResponse: User is not authorized, return this error response
 */
export type AdminAuthResult = NextResponse | null;
```

### Authorization Flow

```mermaid
graph TD
    A[Request] --> B{Has valid session?}
    B -->|No| C[401 Unauthorized]
    B -->|Yes| D{Current user == Target user?}
    D -->|Yes| E[✅ Authorized - Self-operation]
    D -->|No| F{ADMIN_USER_ID configured?}
    F -->|No| G[503 Service Unavailable]
    F -->|Yes| H{Current user == ADMIN_USER_ID?}
    H -->|Yes| I[✅ Authorized - Admin operation]
    H -->|No| J[403 Forbidden]
```

### Usage Example

```typescript
// apps/web/app/api/users/[id]/erase/route.ts
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth.api.getSession({ headers: request.headers });

  // Check authorization before proceeding
  const authError = checkAdminAuthorization(session, id, 'erasure');
  if (authError) {
    return authError;  // Returns 401, 403, or 503 response
  }

  // ✅ Authorized - proceed with erasure
  // ...
}
```

---

## Configuration Requirements

### Environment Variable: `ADMIN_USER_ID`

**Purpose**: Designate a single user as the system administrator with privileged access

**Format**: User ID string (matches `User.id` in database)

**Example**:

```bash
# .env
ADMIN_USER_ID="clx1234567890abcdefg"
```

**How to Get User ID**:

```bash
# Option 1: Query Prisma directly
pnpm --filter @taboot/db prisma studio
# Navigate to User table, copy ID field

# Option 2: SQL query
docker exec -it taboot-db psql -U postgres -d taboot -c \
  "SELECT id FROM auth.user WHERE email = 'admin@example.com';"
```

### Security Notes

**DO**:
- Set `ADMIN_USER_ID` only in production environment
- Use a dedicated admin account (not your personal account)
- Store in secure environment variable store (not committed to git)
- Rotate admin account if compromised

**DO NOT**:
- Hardcode `ADMIN_USER_ID` in application code
- Share admin credentials across multiple people
- Use admin account for day-to-day operations
- Set `ADMIN_USER_ID` in development (use self-operation testing instead)

---

## Fail-Closed Security Design

### Principle: Deny by Default

**Fail-closed** means the system denies access when:
- Configuration is missing (`ADMIN_USER_ID` not set)
- Validation fails (token invalid, session expired)
- Authorization check fails (not admin, not self)
- Any error occurs during authorization

**Why Fail-Closed?**

| Scenario | Fail-Open (insecure) | Fail-Closed (secure) |
|----------|---------------------|---------------------|
| `ADMIN_USER_ID` missing | ❌ Grant admin access | ✅ Deny with 503 error |
| Session validation error | ❌ Assume authenticated | ✅ Deny with 401 error |
| Authorization check throws | ❌ Allow operation | ✅ Deny with 500 error |
| Database connection fails | ❌ Skip authorization | ✅ Deny operation |

### Implementation

```typescript
export function checkAdminAuthorization(
  session: Session | null,
  targetUserId: string,
  operationName: string = 'operation'
): AdminAuthResult {
  // Fail-closed: No session = deny
  if (!session || !session.user) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const currentUserId = session.user.id;
  const adminUserId = process.env.ADMIN_USER_ID?.trim();

  // Fail-closed: Admin operation attempted without configuration = deny
  if (currentUserId !== targetUserId && !adminUserId) {
    logger.error(`Admin ${operationName} attempted but ADMIN_USER_ID not configured`, {
      attemptedBy: currentUserId,
      targetUser: targetUserId,
    });
    return NextResponse.json(
      { error: 'Service not configured for admin operations' },
      { status: 503 }
    );
  }

  const isAdmin = Boolean(adminUserId) && currentUserId === adminUserId;
  const canOperate = currentUserId === targetUserId || isAdmin;

  // Fail-closed: Not authorized = deny
  if (!canOperate) {
    logger.warn(`Unauthorized ${operationName} attempt`, {
      attemptedBy: currentUserId,
      targetUser: targetUserId,
    });
    return NextResponse.json({ error: 'Forbidden' }, { status: 403 });
  }

  // ✅ Authorized - return null (caller proceeds)
  return null;
}
```

### HTTP Status Codes

| Code | Meaning | When Returned |
|------|---------|---------------|
| **401 Unauthorized** | No valid session | Missing or invalid authentication token |
| **403 Forbidden** | Valid session, not authorized | User attempting to operate on another user's account without admin role |
| **503 Service Unavailable** | Configuration missing | `ADMIN_USER_ID` not set when admin operation attempted |

---

## Erase vs Restore Authorization

### User Erasure (GDPR Article 17)

**Endpoint**: `POST /api/users/[id]/erase`

**Authorization**:
- ✅ User can erase **own** account (self-operation)
- ✅ Admin can erase **any** account (privileged operation)

**Why Allow Self-Erasure?**

GDPR Article 17 grants users the **Right to Erasure** ("right to be forgotten"). Users must be able to delete their own data without requiring admin intervention.

**Example**:

```typescript
// User deleting own account
POST /api/users/clx123.../erase
Authorization: Bearer <user_token>
// ✅ Authorized (self-operation)

// Admin deleting user's account
POST /api/users/clx123.../erase
Authorization: Bearer <admin_token>
// ✅ Authorized (admin operation, requires ADMIN_USER_ID)
```

### User Restoration (Admin Only)

**Endpoint**: `POST /api/users/[id]/restore` (hypothetical - not yet implemented)

**Authorization**:
- ❌ User **cannot** restore own account (self-operation denied)
- ✅ Admin **can** restore any account (privileged operation)

**Why Deny Self-Restoration?**

Restoration reverses soft delete, which may have compliance or security implications:
- User may have been banned for abuse
- Deletion may have been legally required
- Multiple restoration attempts could indicate account compromise

**Example**:

```typescript
// User attempting to restore own account
POST /api/users/clx123.../restore
Authorization: Bearer <user_token>
// ❌ 403 Forbidden (self-restoration denied)

// Admin restoring user's account
POST /api/users/clx123.../restore
Authorization: Bearer <admin_token>
// ✅ Authorized (admin operation, requires ADMIN_USER_ID)
```

**Implementation Pattern** (when adding restore endpoint):

```typescript
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const session = await auth.api.getSession({ headers: request.headers });

  // Restoration is ADMIN-ONLY (deny self-restoration)
  const currentUserId = session?.user.id;
  if (currentUserId === id) {
    logger.warn('Self-restoration attempt denied', { userId: id });
    return NextResponse.json(
      { error: 'Users cannot restore their own accounts. Contact support.' },
      { status: 403 }
    );
  }

  // Check admin authorization
  const authError = checkAdminAuthorization(session, id, 'restoration');
  if (authError) {
    return authError;
  }

  // ✅ Authorized admin - proceed with restoration
  // ...
}
```

---

## Implementation Details

### Admin Detection Logic

```typescript
const currentUserId = session!.user.id;
const adminUserId = process.env.ADMIN_USER_ID?.trim();
const isAdmin = Boolean(adminUserId) && currentUserId === adminUserId;
```

**Step-by-step**:

1. **Extract current user ID** from authenticated session
2. **Load admin user ID** from environment variable (trimmed to avoid whitespace issues)
3. **Check both conditions**:
   - `ADMIN_USER_ID` is configured (not empty/undefined)
   - Current user's ID matches `ADMIN_USER_ID`

**Edge Cases Handled**:

```typescript
// ADMIN_USER_ID not set
const adminUserId = process.env.ADMIN_USER_ID?.trim();
// → adminUserId = undefined
const isAdmin = Boolean(undefined) && currentUserId === undefined;
// → isAdmin = false

// ADMIN_USER_ID is empty string
const adminUserId = ''.trim();
// → adminUserId = ''
const isAdmin = Boolean('') && currentUserId === '';
// → isAdmin = false (Boolean('') = false)

// ADMIN_USER_ID has whitespace
const adminUserId = '  clx123...  '.trim();
// → adminUserId = 'clx123...'
const isAdmin = Boolean('clx123...') && currentUserId === 'clx123...';
// → isAdmin = true (if IDs match)
```

### Authorization in Route Handlers

**Pattern**: Check authorization early, return error immediately if unauthorized

```typescript
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  // 1. Get session
  const session = await auth.api.getSession({ headers: request.headers });

  // 2. Check authorization (early return)
  const authError = checkAdminAuthorization(session, id, 'erasure');
  if (authError) {
    return authError;  // Returns 401/403/503 response
  }

  // 3. Determine if admin (for audit logging)
  const currentUserId = session!.user.id;
  const adminUserId = process.env.ADMIN_USER_ID?.trim();
  const isAdmin = Boolean(adminUserId) && currentUserId === adminUserId;

  // 4. Proceed with operation
  // ... (erasure, restoration, etc.)

  // 5. Log action with admin flag
  logger.info('User data erased', {
    userId: id,
    erasedBy: currentUserId,
    isAdmin,
  });
}
```

---

## Testing Admin Endpoints

### Test Setup

**Prerequisites**:

1. **Two test accounts**:
   - User account: `user@example.com` (ID: `user123`)
   - Admin account: `admin@example.com` (ID: `admin456`)

2. **Environment configuration**:

```bash
# .env.test
ADMIN_USER_ID="admin456"
DATABASE_URL="postgresql://postgres:postgres@localhost:4201/taboot_test"
AUTH_SECRET="test-auth-secret-min-32-chars-long"
```

3. **Start test database**:

```bash
docker compose up -d taboot-db
pnpm --filter @taboot/db prisma migrate deploy
```

### Test Case 1: Self-Erasure (User)

**Scenario**: User deletes own account

```bash
# 1. Sign in as user
curl -X POST http://localhost:4211/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
# → Returns session token

# 2. Erase own account
curl -X POST http://localhost:4211/api/users/user123/erase \
  -H "Authorization: Bearer <user_session_token>"
# → Expected: 200 OK (self-operation authorized)
```

**Expected Response**:

```json
{
  "success": true,
  "message": "User data erased per GDPR Article 17 (Right to Erasure)",
  "erasureDetails": {
    "erasedAt": "2025-10-26T12:34:56.789Z",
    "irreversible": true,
    "completeness": {
      "userPII": "anonymized",
      "sessions": "deleted",
      "oauth": "deleted",
      "verifications": "deleted",
      "mfa": "deleted",
      "auditLogs": "pii_removed"
    }
  }
}
```

### Test Case 2: Admin Erasure (Another User)

**Scenario**: Admin deletes another user's account

```bash
# 1. Sign in as admin
curl -X POST http://localhost:4211/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin_password"}'
# → Returns admin session token

# 2. Erase another user's account
curl -X POST http://localhost:4211/api/users/user123/erase \
  -H "Authorization: Bearer <admin_session_token>"
# → Expected: 200 OK (admin operation authorized)
```

**Expected Audit Log**:

```json
{
  "userId": "admin456",
  "action": "USER_ERASE_GDPR",
  "targetType": "user",
  "targetId": "user123",
  "metadata": {
    "timestamp": "2025-10-26T12:34:56.789Z",
    "gdpr_article_17": true,
    "initiatedBy": "admin"
  }
}
```

### Test Case 3: Unauthorized Access (User → Another User)

**Scenario**: Non-admin user attempts to delete another user's account

```bash
# 1. Sign in as user
curl -X POST http://localhost:4211/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
# → Returns session token

# 2. Attempt to erase another user's account
curl -X POST http://localhost:4211/api/users/other_user_id/erase \
  -H "Authorization: Bearer <user_session_token>"
# → Expected: 403 Forbidden (not authorized)
```

**Expected Response**:

```json
{
  "error": "Forbidden"
}
```

**Expected Log**:

```json
{
  "level": "warn",
  "message": "Unauthorized erasure attempt",
  "attemptedBy": "user123",
  "targetUser": "other_user_id"
}
```

### Test Case 4: Missing Admin Configuration

**Scenario**: User attempts admin operation but `ADMIN_USER_ID` not set

```bash
# 1. Unset ADMIN_USER_ID
unset ADMIN_USER_ID

# 2. Restart server
pnpm --filter @taboot/web dev

# 3. Sign in as user
curl -X POST http://localhost:4211/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# 4. Attempt to erase another user's account
curl -X POST http://localhost:4211/api/users/other_user_id/erase \
  -H "Authorization: Bearer <user_session_token>"
# → Expected: 503 Service Unavailable (admin not configured)
```

**Expected Response**:

```json
{
  "error": "Service not configured for admin operations"
}
```

**Expected Log**:

```json
{
  "level": "error",
  "message": "Admin erasure attempted but ADMIN_USER_ID not configured",
  "attemptedBy": "user123",
  "targetUser": "other_user_id"
}
```

### Test Case 5: Unauthenticated Request

**Scenario**: No session token provided

```bash
curl -X POST http://localhost:4211/api/users/user123/erase
# → Expected: 401 Unauthorized (no session)
```

**Expected Response**:

```json
{
  "error": "Unauthorized"
}
```

### Automated Testing

**File**: `apps/web/lib/__tests__/auth-helpers.test.ts` (to be created)

```typescript
import { checkAdminAuthorization } from '@/lib/auth-helpers';
import { Session } from '@taboot/auth';

describe('checkAdminAuthorization', () => {
  const mockSession: Session = {
    user: { id: 'user123', email: 'user@example.com', name: 'User' },
    session: { id: 'session123', userId: 'user123', expiresAt: new Date() },
  };

  beforeEach(() => {
    delete process.env.ADMIN_USER_ID;
  });

  it('should allow self-operation', () => {
    const result = checkAdminAuthorization(mockSession, 'user123', 'test');
    expect(result).toBeNull();  // ✅ Authorized
  });

  it('should deny operation on another user without admin config', () => {
    const result = checkAdminAuthorization(mockSession, 'other_user', 'test');
    expect(result).toMatchObject({
      status: 503,
      body: { error: 'Service not configured for admin operations' },
    });
  });

  it('should allow admin to operate on any user', () => {
    process.env.ADMIN_USER_ID = 'user123';
    const result = checkAdminAuthorization(mockSession, 'other_user', 'test');
    expect(result).toBeNull();  // ✅ Authorized (admin)
  });

  it('should deny non-admin operating on another user', () => {
    process.env.ADMIN_USER_ID = 'admin456';  // Different from mockSession user
    const result = checkAdminAuthorization(mockSession, 'other_user', 'test');
    expect(result).toMatchObject({
      status: 403,
      body: { error: 'Forbidden' },
    });
  });

  it('should deny when session is null', () => {
    const result = checkAdminAuthorization(null, 'user123', 'test');
    expect(result).toMatchObject({
      status: 401,
      body: { error: 'Unauthorized' },
    });
  });
});
```

---

## Security Considerations

### 1. Single Admin Account

**Current Design**: One admin user per environment

**Rationale**:
- Simplifies authorization logic
- Clear audit trail (admin actions easily identifiable)
- Reduces attack surface (fewer privileged accounts)

**Limitation**: Does not scale for multi-admin environments

**Future**: If multiple admins needed, implement role-based access control (RBAC):

```typescript
// Future RBAC pattern
const userRoles = await prisma.userRole.findMany({
  where: { userId: currentUserId },
  include: { role: true },
});

const isAdmin = userRoles.some((ur) => ur.role.name === 'ADMIN');
```

### 2. No Role Escalation

**Design**: Admin role assigned via environment variable only

**Prevention**:
- Users cannot grant themselves admin role
- No API endpoint to modify `ADMIN_USER_ID`
- Admin assignment requires server configuration access

**Attack Prevention**:

| Attack Vector | Prevention |
|--------------|-----------|
| Privilege escalation via API | ❌ No API to modify admin role |
| SQL injection to change role | ✅ Admin role not in database |
| Cookie manipulation | ✅ Session verified via JWT signature |
| Token forgery | ✅ JWT signed with `AUTH_SECRET` |

### 3. Audit Logging

**All admin operations logged** with:
- Admin user ID
- Target user ID
- Operation type (erasure, restoration, etc.)
- Timestamp
- IP address (if available)
- `isAdmin` flag for filtering

**Example Audit Log**:

```typescript
await tx.auditLog.create({
  data: {
    userId: currentUserId,
    action: 'USER_ERASE_GDPR',
    targetType: 'user',
    targetId: userId,
    metadata: {
      timestamp: new Date().toISOString(),
      gdpr_article_17: true,
      ip_address: ipAddress ? 'present' : 'absent',
      initiatedBy: isAdmin ? 'admin' : 'self',
    },
  },
});
```

**Audit Trail Query**:

```sql
-- Find all admin operations in last 30 days
SELECT * FROM auth.audit_log
WHERE metadata->>'initiatedBy' = 'admin'
  AND created_at > NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;
```

### 4. IP Address Validation

**Proxy-Aware IP Detection** (same as CSRF validation):

```typescript
function getClientIp(request: Request): string | undefined {
  const trustProxy = process.env.TRUST_PROXY === 'true';

  if (trustProxy) {
    // Trust X-Forwarded-For only if behind verified proxy
    const xff = request.headers.get('x-forwarded-for') ?? '';
    const leftmost = xff.split(',')[0]?.trim();
    if (leftmost && isValidIp(leftmost)) {
      return leftmost;
    }
  }

  return undefined;
}
```

**See**: `apps/web/middleware.ts` for full IP validation implementation

---

## Audit Trail

### Audit Log Schema

**File**: `packages-ts/db/prisma/schema.prisma`

```prisma
model AuditLog {
  id         String   @id @default(cuid())
  userId     String?  @map("user_id")       // Who performed the action
  targetId   String   @map("target_id")     // What was acted upon
  targetType String   @map("target_type")   // Type of target (e.g., "user")
  action     String                         // Action type (e.g., "USER_ERASE_GDPR")
  metadata   Json?                          // Additional context
  ipAddress  String?  @map("ip_address")    // Client IP (if available)
  userAgent  String?  @map("user_agent")    // Client user agent
  createdAt  DateTime @default(now()) @map("created_at")

  @@index([targetId, targetType])
  @@index([userId])
  @@index([createdAt])
  @@map("audit_log")
  @@schema("auth")
}
```

### Query Examples

**Find all erasure operations**:

```sql
SELECT
  al.created_at,
  al.user_id,
  al.target_id,
  al.metadata->>'initiatedBy' AS initiated_by,
  al.ip_address
FROM auth.audit_log al
WHERE al.action = 'USER_ERASE_GDPR'
ORDER BY al.created_at DESC
LIMIT 100;
```

**Find admin operations by specific admin**:

```sql
SELECT
  al.created_at,
  al.action,
  al.target_type,
  al.target_id,
  al.metadata
FROM auth.audit_log al
WHERE al.user_id = 'admin456'
  AND al.metadata->>'initiatedBy' = 'admin'
ORDER BY al.created_at DESC;
```

**Count admin operations by type**:

```sql
SELECT
  al.action,
  COUNT(*) AS operation_count
FROM auth.audit_log al
WHERE al.metadata->>'initiatedBy' = 'admin'
GROUP BY al.action
ORDER BY operation_count DESC;
```

---

## Related Documentation

- `docs/CSRF_XSS_RISKS.md` - CSRF protection and XSS mitigation
- `docs/SOFT_DELETE_CONTEXT.md` - Soft delete audit trail
- `CLAUDE.md` - Security configuration overview
- `apps/web/lib/auth-helpers.ts` - Implementation file
- `apps/web/app/api/users/[id]/erase/route.ts` - Example usage

---

## Summary

**Authorization Pattern**: Fail-closed, self-or-admin permission model

**Configuration**: Single admin designated via `ADMIN_USER_ID` environment variable

**Self-Operation**: Users can operate on own accounts without admin privileges

**Admin Operation**: Admin can operate on any account (requires `ADMIN_USER_ID` match)

**Audit Trail**: All admin operations logged with full context for compliance

**Security**: Fail-closed design prevents unauthorized access when configuration missing or validation fails
