# Security Audit: SQL Injection Risk in Audit Log Metadata

**Audit Date:** 2025-10-25
**Auditor:** Claude Code (Automated Security Verification)
**Severity:** VERIFIED SAFE
**Status:** NO ACTION REQUIRED

## Executive Summary

This audit verifies the SQL injection risk assessment for audit log metadata handling in the Taboot authentication system. After comprehensive code review, **ALL audit log insertions use Prisma's parameterized query system**, which provides automatic SQL injection protection.

## Scope

### Files Audited

1. `/home/jmagar/code/taboot/packages-ts/db/src/middleware/soft-delete.ts` (lines 42-76)
   - `logAudit()` function - audit trail logging
   - Soft delete middleware implementation

2. `/home/jmagar/code/taboot/apps/web/scripts/cleanup-deleted-users.ts` (lines 33-58)
   - `logHardDeletion()` function - hard delete audit logging
   - Cleanup script for expired soft-deleted users

3. `/home/jmagar/code/taboot/apps/web/app/api/admin/users/[id]/restore/route.ts`
   - User restoration endpoint
   - Uses `restoreUser()` helper (calls `logAudit()`)

4. `/home/jmagar/code/taboot/tests/packages-ts/db/soft-delete.test.ts`
   - Test suite using `$queryRaw` and `$executeRaw` (test-only, not production code)

### Database Schema

```prisma
model AuditLog {
  id         String   @id @default(cuid())
  userId     String?  @map("user_id")
  targetId   String   @map("target_id")
  targetType String   @map("target_type")
  action     String
  metadata   Json?    // <- JSONB column (SQL injection concern)
  ipAddress  String?  @map("ip_address")
  userAgent  String?  @map("user_agent")
  createdAt  DateTime @default(now()) @map("created_at")

  @@schema("auth")
}
```

## Findings

### 1. Raw SQL Usage (Prisma Tagged Templates)

Both production audit logging functions use Prisma's `$executeRaw` with **tagged template literals**:

**File:** `packages-ts/db/src/middleware/soft-delete.ts:56-71`

```typescript
await prisma.$executeRaw`
  INSERT INTO "audit_log" (
    id, user_id, target_id, target_type, action,
    metadata, ip_address, user_agent, created_at
  ) VALUES (
    gen_random_uuid()::text,
    ${params.userId || null},           // <- PARAMETERIZED
    ${params.targetId},                 // <- PARAMETERIZED
    ${params.targetType},               // <- PARAMETERIZED
    ${params.action},                   // <- PARAMETERIZED
    ${params.metadata ? JSON.stringify(params.metadata) : null}::jsonb,  // <- PARAMETERIZED
    ${params.ipAddress || null},        // <- PARAMETERIZED
    ${params.userAgent || null},        // <- PARAMETERIZED
    NOW()
  )
`;
```

**File:** `apps/web/scripts/cleanup-deleted-users.ts:40-57`

```typescript
await prisma.$executeRaw`
  INSERT INTO "audit_log" (
    id, user_id, target_id, target_type, action,
    metadata, created_at
  ) VALUES (
    gen_random_uuid()::text,
    'system',                           // <- LITERAL STRING (SAFE)
    ${userId},                          // <- PARAMETERIZED
    'User',                             // <- LITERAL STRING (SAFE)
    'HARD_DELETE',                      // <- LITERAL STRING (SAFE)
    ${JSON.stringify({                  // <- PARAMETERIZED (metadata)
      originalDeletedAt: deletedAt,
      retentionPeriod: `${retentionDays} days`,
      hardDeletedAt: new Date(),
    })}::jsonb,
    NOW()
  )
`;
```

### 2. Prisma Parameterization Mechanism

Prisma's `$executeRaw` with tagged template literals (backticks) uses **automatic parameterization**:

```typescript
// SAFE: Tagged template literal (automatic parameterization)
await prisma.$executeRaw`
  INSERT INTO table (col) VALUES (${userInput})
`;
// SQL sent to PostgreSQL:
// INSERT INTO table (col) VALUES ($1)
// Parameters: [userInput]

// UNSAFE: String concatenation (would be vulnerable)
await prisma.$executeRawUnsafe(
  `INSERT INTO table (col) VALUES (${userInput})`
);
// This is NOT used anywhere in the codebase
```

**Key Evidence:**

- Tagged templates (`` $executeRaw`...` ``) = **Parameterized** (SAFE)
- `.stringify()` happens in JavaScript **before** parameterization
- PostgreSQL receives pre-serialized JSON string as parameter
- No string concatenation or interpolation at SQL level

### 3. Metadata Handling

**Metadata Construction:**

```typescript
// soft-delete.ts:114-117
metadata: {
  reason: context.userId ? 'user-initiated' : 'system-initiated',
  originalWhere: params.args.where,  // <- Prisma query object
},
```

**Serialization:**

```typescript
// soft-delete.ts:66
${params.metadata ? JSON.stringify(params.metadata) : null}::jsonb
```

**Security Analysis:**

1. `JSON.stringify()` escapes all special characters
2. Resulting string is passed as **query parameter** (not concatenated)
3. PostgreSQL JSONB type performs additional validation
4. Even if malicious JSON, it's treated as data, not SQL code

**Example Attack Scenario (MITIGATED):**

```typescript
// Attacker tries to inject SQL via metadata
const maliciousMetadata = {
  reason: "'; DROP TABLE audit_log; --",
};

// What actually happens:
// 1. JSON.stringify() produces: "{\"reason\":\"'; DROP TABLE audit_log; --\"}"
// 2. Prisma sends as parameter: $1 = "{\"reason\":\"'; DROP TABLE audit_log; --\"}"
// 3. PostgreSQL executes: INSERT INTO "audit_log" (...) VALUES (..., $1::jsonb, ...)
// 4. Result: Audit log contains literal string, no SQL injection
```

### 4. Codebase Scan Results

**Search for Raw SQL:**

```bash
grep -r "\$executeRaw\|\$queryRaw" apps/web packages-ts/db
```

**Results:**

- `packages-ts/db/src/middleware/soft-delete.ts` - **SAFE** (parameterized)
- `apps/web/scripts/cleanup-deleted-users.ts` - **SAFE** (parameterized)
- `tests/packages-ts/db/soft-delete.test.ts` - **TEST ONLY** (not production)

**Search for Audit Log Operations:**

```bash
grep -r "audit.*log\|AuditLog" --include="*.ts"
```

**Results:**

- No usage of `prisma.auditLog.create()` (ORM method)
- All insertions via `$executeRaw` (parameterized tagged templates)
- Reason: Avoid middleware recursion (documented in code comment)

### 5. Alternative to Raw SQL (Not Used)

**Why not use Prisma ORM method?**

```typescript
// NOT USED: This would cause middleware recursion
await prisma.auditLog.create({
  data: {
    userId: params.userId,
    targetId: params.targetId,
    targetType: params.targetType,
    action: params.action,
    metadata: params.metadata,  // Prisma automatically handles JSON
    ipAddress: params.ipAddress,
    userAgent: params.userAgent,
  },
});
```

**Reason for Raw SQL (from code comment):**

```typescript
// soft-delete.ts:55
// Use raw query to avoid middleware recursion
```

The middleware intercepts ALL Prisma operations. If audit logging used `prisma.auditLog.create()`, it would trigger the middleware again, causing infinite recursion.

## Security Assessment

### Risk Levels

| Component | Risk Level | Justification |
|-----------|-----------|---------------|
| `logAudit()` metadata | **NONE** | Prisma parameterization + JSON serialization |
| `logHardDeletion()` metadata | **NONE** | Prisma parameterization + JSON serialization |
| `restoreUser()` (uses `logAudit()`) | **NONE** | Inherits safety from `logAudit()` |
| Test suite raw SQL | **NONE** | Not production code |

### Attack Vectors Analyzed

1. **Malicious metadata object:**
   - Mitigated by `JSON.stringify()` + parameterization

2. **Malicious user input in IP/User-Agent:**
   - Mitigated by parameterization (strings passed as parameters)

3. **SQL injection via `params.targetId`:**
   - Mitigated by parameterization

4. **JSONB type confusion:**
   - PostgreSQL validates JSONB format; invalid JSON rejected

### Best Practices Verification

- [x] **Parameterized queries:** ALL user inputs passed as parameters
- [x] **No string concatenation:** No `+` or `${}` in SQL strings
- [x] **Tagged template literals:** Using `` $executeRaw`...` `` (safe)
- [x] **JSON sanitization:** `JSON.stringify()` before database insertion
- [x] **Type casting:** `::jsonb` ensures PostgreSQL type validation
- [x] **Error handling:** Audit failures don't crash operations

## Recommendations

### 1. Document Parameterization (OPTIONAL)

Add inline comments to clarify safety:

```typescript
// SAFE: Prisma tagged templates use parameterized queries
// All ${...} values are sent as query parameters, not string interpolation
await prisma.$executeRaw`
  INSERT INTO "audit_log" (
    id, user_id, target_id, target_type, action,
    metadata, ip_address, user_agent, created_at
  ) VALUES (
    gen_random_uuid()::text,
    ${params.userId || null},           // Parameter $1
    ${params.targetId},                 // Parameter $2
    ${params.targetType},               // Parameter $3
    ${params.action},                   // Parameter $4
    ${params.metadata ? JSON.stringify(params.metadata) : null}::jsonb,  // Parameter $5
    ${params.ipAddress || null},        // Parameter $6
    ${params.userAgent || null},        // Parameter $7
    NOW()
  )
`;
```

### 2. Add Security Test (OPTIONAL)

Create explicit SQL injection test:

```typescript
// tests/packages-ts/db/sql-injection.test.ts
it('should prevent SQL injection via metadata', async () => {
  const maliciousMetadata = {
    reason: "'; DROP TABLE audit_log; --",
    attack: "1' OR '1'='1",
  };

  setSoftDeleteContext(testRequestId, {
    userId: 'attacker',
    ipAddress: "127.0.0.1'; DROP TABLE audit_log; --",
    userAgent: "Mozilla'; DELETE FROM user; --",
  });

  await prisma.user.delete({ where: { id: testUserId } });

  // Verify audit log exists (table not dropped)
  const logs = await prisma.$queryRaw`
    SELECT * FROM "audit_log" WHERE target_id = ${testUserId}
  `;

  expect(logs).toHaveLength(1);
  // Verify malicious strings stored as literals
  expect(logs[0].metadata.reason).toBe("'; DROP TABLE audit_log; --");
  expect(logs[0].ip_address).toBe("127.0.0.1'; DROP TABLE audit_log; --");
});
```

### 3. Static Analysis Tool (OPTIONAL)

Add ESLint rule to prevent `$executeRawUnsafe`:

```json
// .eslintrc.json
{
  "rules": {
    "no-restricted-syntax": [
      "error",
      {
        "selector": "MemberExpression[object.name='prisma'][property.name='$executeRawUnsafe']",
        "message": "Use $executeRaw with tagged templates instead of $executeRawUnsafe"
      }
    ]
  }
}
```

## Conclusion

**VERIFIED SAFE:** All audit log insertions use Prisma's parameterized query system via tagged template literals (`` $executeRaw`...` ``). The combination of:

1. Prisma's automatic parameterization
2. `JSON.stringify()` serialization
3. PostgreSQL JSONB type validation

...provides **defense-in-depth** against SQL injection attacks.

**NO CODE CHANGES REQUIRED.** The current implementation follows security best practices.

---

## References

- [Prisma: Raw database access](https://www.prisma.io/docs/orm/prisma-client/using-raw-sql/raw-queries)
- [Prisma: SQL injection prevention](https://www.prisma.io/docs/orm/prisma-client/using-raw-sql/sql-injection-prevention)
- [OWASP: SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [PostgreSQL: JSONB Type](https://www.postgresql.org/docs/current/datatype-json.html)

## Appendix: Code Locations

### Production Code

1. **Audit Logging Function**
   - File: `/home/jmagar/code/taboot/packages-ts/db/src/middleware/soft-delete.ts`
   - Function: `logAudit()` (lines 42-76)
   - Usage: Called by soft delete middleware

2. **Hard Delete Logging**
   - File: `/home/jmagar/code/taboot/apps/web/scripts/cleanup-deleted-users.ts`
   - Function: `logHardDeletion()` (lines 33-58)
   - Usage: Cleanup script (cron job)

3. **User Restoration**
   - File: `/home/jmagar/code/taboot/packages-ts/db/src/middleware/soft-delete.ts`
   - Function: `restoreUser()` (lines 213-250)
   - Usage: Admin API endpoint

4. **Restore Endpoint**
   - File: `/home/jmagar/code/taboot/apps/web/app/api/admin/users/[id]/restore/route.ts`
   - Function: `POST()` handler (lines 68-140)
   - Usage: Calls `restoreUser()` helper

### Test Code

- File: `/home/jmagar/code/taboot/tests/packages-ts/db/soft-delete.test.ts`
- Lines: 38-39, 59-61, 78-82, 113-116, 123-124, 131-135, 147-151, 167-171, 201-205, 235-239, 271-275, 287-291, 307-311, 365-369, 388
- Purpose: Test setup/cleanup and verification (not production code)

### Database Schema

- File: `/home/jmagar/code/taboot/packages-ts/db/prisma/schema.prisma`
- Model: `AuditLog` (lines 103-119)
- Schema: `auth` (PostgreSQL schema isolation)
