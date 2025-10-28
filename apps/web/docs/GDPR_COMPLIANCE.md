# GDPR Compliance Implementation

## Overview

Taboot implements comprehensive GDPR compliance with dual delete mechanisms:

1. **Soft Delete** (90-day retention): Accidental deletion recovery
2. **GDPR Erasure** (immediate): Article 17 right to erasure

This document covers the erasure mechanism required by EU data protection law.

## Legal Basis

### GDPR Article 17 - Right to Erasure

**User Right**: Individual has the right to request immediate erasure of personal data

**Conditions**:
- Data no longer necessary for original purpose
- User withdraws consent
- User objects to processing
- Data collected unlawfully
- Data must be deleted for legal obligation

**Our Implementation**: Covers all conditions via POST `/api/users/[id]/erase`

### Key Provisions

**Article 17(1)**: Right to erasure without undue delay
→ Implemented immediately in transaction

**Article 17(3)(b)**: Exception for "legal obligation" storage
→ Audit logs keep action, remove PII (compliant)

**Article 5(1)(e)**: Storage limitation principle
→ PII not kept indefinitely; audit trail anonymized after erasure

## Implementation

### Endpoints

#### POST /api/users/[id]/erase

**Purpose**: Immediate GDPR-compliant erasure (IRREVERSIBLE)

**Authorization**:
- User can erase own account
- Admin can erase any account
- Non-admin cannot erase others' accounts

**What Gets Erased**:
1. **User PII**: Email → `anonymized-{id}@example.local`, Name → `Anonymized User`, Image → null
2. **Sessions**: All deleted (forces re-authentication)
3. **OAuth Accounts**: All deleted
4. **Verification Tokens**: All deleted
5. **2FA/MFA**: All deleted
6. **Audit Log PII**: `ipAddress` and `userAgent` → `"anonymized"`
7. **Audit Trail**: New entry logged: `USER_ERASE_GDPR` action with minimal PII

**Request**:

```bash
POST /api/users/{userId}/erase
Authorization: Bearer {token}
Content-Type: application/json
```

**Response** (200 OK):

```json
{
  "success": true,
  "message": "User data erased per GDPR Article 17 (Right to Erasure)",
  "erasureDetails": {
    "erasedAt": "2025-10-25T23:45:00Z",
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

#### GET /api/users/[id]/erase

**Purpose**: Preview what will be erased (for confirmation UI)

**Authorization**: Same as POST (user or admin)

**Response** (200 OK):

```json
{
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe",
    "createdAt": "2025-01-15T10:00:00Z"
  },
  "willBeErased": {
    "pii": {
      "email": "user@example.com",
      "name": "John Doe",
      "profileImage": "if_present"
    },
    "data": {
      "sessions": 3,
      "oauthAccounts": 1,
      "verificationTokens": 0,
      "twoFactorAuth": 1
    },
    "auditTrail": {
      "total": 47,
      "action": "PII removed, action log retained for compliance"
    }
  },
  "warning": "This action is IRREVERSIBLE. All PII will be permanently anonymized.",
  "gdprCompliance": "Article 17 - Right to Erasure"
}
```

## Data Retention

### Soft Delete (90 Days)

```typescript
// user.deletedAt is set, PII retained
// user.deletedBy tracks who deleted

// After 90 days: Hard delete via cleanup script
// pnpm tsx apps/web/scripts/cleanup-deleted-users.ts
```

**Purpose**: Accidental deletion recovery, reversible

### GDPR Erasure (Immediate)

```typescript
// user.email → "anonymized-{id}@example.local"
// user.name → "Anonymized User"
// user.image → null
// All sessions/accounts deleted
// Audit logs anonymized: ipAddress/userAgent → "anonymized"
```

**Purpose**: Right to erasure compliance, irreversible

### Audit Log Retention

**Before Erasure**:

```json
{
  "userId": "user-123",
  "action": "LOGIN",
  "ipAddress": "192.168.1.1",
  "userAgent": "Mozilla/5.0..."
}
```

**After Erasure**:

```json
{
  "userId": "user-123",
  "action": "LOGIN",
  "ipAddress": "anonymized",
  "userAgent": "anonymized",
  "metadata": { "gdpr_erased": true }
}
```

**Compliance**: Keeps audit trail for other regulations (SOC 2, etc.) while removing PII

## User Flow

### 1. User Requests Erasure (via UI)

```text
User → Settings → "Delete Account" → Confirmation
     → Confirm → POST /api/users/{id}/erase
     → Success → Redirect to login (sessions deleted)
```

### 2. User Sees Preview (optional)

```text
GET /api/users/{id}/erase
↓
Display what will be deleted
↓
User confirms
↓
POST /api/users/{id}/erase
```

### 3. Admin Erases User (compliance/support)

```text
Admin → Admin Dashboard → Users → [user] → "Erase Account"
     → Confirm GDPR erasure
     → POST /api/admin/users/{id} (or uses regular endpoint with admin token)
     → Audit logged: initiatedBy=admin
```

## Compliance Checklist

- [x] Immediate erasure without undue delay (Article 17(1))
- [x] PII anonymization (no indefinite retention)
- [x] Audit trail preserved (legal obligation exception)
- [x] Sessions deleted (no continued access)
- [x] OAuth accounts deleted
- [x] Verification tokens deleted
- [x] 2FA/MFA deleted
- [x] User authorization (own account or admin)
- [x] Audit logging of erasure action
- [x] Clear response indicating completeness
- [x] Preview endpoint for user confirmation
- [x] Irreversible action warning

## Testing

### Manual Testing

```bash
# 1. Sign in as user
curl -X POST http://localhost:3000/api/auth/sign-in \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"..."}'

# 2. Preview erasure
curl http://localhost:3000/api/users/{user-id}/erase \
  -H "Authorization: Bearer {token}"

# 3. Perform erasure
curl -X POST http://localhost:3000/api/users/{user-id}/erase \
  -H "Authorization: Bearer {token}"

# 4. Verify email anonymized
# Check database: email = "anonymized-{id}@example.local"
```

### Automated Testing

```bash
# Run GDPR erasure tests
pnpm --filter @taboot/web test api/users/\[id\]/erase

# Integration tests cover:
# - User can erase own account
# - Admin can erase any account
# - Non-admin cannot erase others
# - All PII anonymized
# - Sessions deleted
# - Audit log created
```

## Security Considerations

### Authorization

```typescript
const canErase = currentUserId === userId || isAdmin;
if (!canErase) {
  return 403 Forbidden;
}
```

#### Non-admin users cannot erase other accounts

### Transaction Safety

```typescript
await prisma.$transaction(async (tx) => {
  // All operations in single transaction
  // Failure on any step → rollback all
  // No partial erasures
});
```

**Atomicity**: All-or-nothing erasure

### Audit Trail

```typescript
await tx.auditLog.create({
  data: {
    userId: currentUserId,
    action: 'USER_ERASE_GDPR',
    metadata: {
      targetUserId: userId,
      initiatedBy: isAdmin ? 'admin' : 'self',
      // No PII in metadata
    }
  }
});
```

**Logging**: Tracks erasure without exposing deleted PII

## Monitoring

### Queries

```sql
-- Count erasure requests
SELECT COUNT(*) FROM "AuditLog" WHERE action = 'USER_ERASE_GDPR';

-- Check anonymization
SELECT email, name FROM "User" WHERE email LIKE 'anonymized-%';

-- Verify audit log anonymization
SELECT COUNT(*) FROM "AuditLog"
WHERE userId = 'user-id' AND ipAddress = 'anonymized';
```

### Metrics

- Erasure requests per month
- Average erasure response time
- Audit log anonymization success rate
- Authorization failures (security monitoring)

## References

- [GDPR Article 17 Text](https://gdpr-info.eu/art-17-gdpr/)
- [GDPR Article 5(1)(e) - Storage Limitation](https://gdpr-info.eu/art-5-gdpr/)
- [ICO Right to Erasure Guidance](https://ico.org.uk/for-organisations/guide-to-data-protection/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/)
- [Microsoft GDPR Implementation](https://learn.microsoft.com/en-us/azure/security/fundamentals/gdpr)
- [DPO Handbook](https://ico.org.uk/for-organisations/data-protection-officer/)

## Future Improvements

- [ ] Bulk erasure API for admin (with rate limiting)
- [ ] Erasure status monitoring dashboard
- [ ] Configurable anonymization values
- [ ] Erasure request queue (for large datasets)
- [ ] Post-erasure webhook notifications
- [ ] GDPR compliance audit reports
