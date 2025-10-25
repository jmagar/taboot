# Soft Delete Migration Guide

This guide walks through deploying the soft delete functionality to your Taboot instance.

## Prerequisites

- Prisma CLI installed (`pnpm install` in packages-ts/db)
- Database access (PostgreSQL connection)
- Backup of production database (recommended)

## Step 1: Review Changes

**Schema Changes:**
```bash
# View the updated schema
cat packages-ts/db/prisma/schema.prisma
```

**Key Additions:**
- User model: `deletedAt`, `deletedBy` fields
- New table: `AuditLog`
- Index on `User.deletedAt`

## Step 2: Generate Migration

```bash
cd packages-ts/db

# Generate migration (development)
pnpm prisma migrate dev --name add-soft-delete-and-audit

# This will:
# 1. Create migration file in prisma/migrations/
# 2. Apply migration to development database
# 3. Regenerate Prisma client
```

**Review Migration SQL:**
```bash
# Check the generated migration
cat prisma/migrations/*/add-soft-delete-and-audit/migration.sql
```

Expected SQL:
```sql
-- AlterTable
ALTER TABLE "user" ADD COLUMN "deleted_at" TIMESTAMP,
                   ADD COLUMN "deleted_by" TEXT;

-- CreateTable
CREATE TABLE "audit_log" (
  "id" TEXT NOT NULL,
  "user_id" TEXT,
  "target_id" TEXT NOT NULL,
  "target_type" TEXT NOT NULL,
  "action" TEXT NOT NULL,
  "metadata" JSONB,
  "ip_address" TEXT,
  "user_agent" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "user_deleted_at_idx" ON "user"("deleted_at");
CREATE INDEX "audit_log_target_id_target_type_idx" ON "audit_log"("target_id", "target_type");
CREATE INDEX "audit_log_user_id_idx" ON "audit_log"("user_id");
CREATE INDEX "audit_log_created_at_idx" ON "audit_log"("created_at");
```

## Step 3: Test in Development

**Create Test User:**
```typescript
import { prisma } from '@taboot/db';

// Create user
const user = await prisma.user.create({
  data: {
    id: 'test-user',
    email: 'test@example.com',
    name: 'Test User',
    emailVerified: true,
  },
});

console.log('Created:', user);
```

**Test Soft Delete:**
```typescript
// Delete user (should be soft delete)
await prisma.user.delete({
  where: { id: 'test-user' },
});

// Verify user is soft-deleted
const softDeleted = await prisma.$queryRaw`
  SELECT * FROM "user" WHERE id = 'test-user'
`;

console.log('Soft deleted:', softDeleted);
// Should show deletedAt set

// Verify user not in normal queries
const users = await prisma.user.findMany({
  where: { id: 'test-user' },
});

console.log('Normal query:', users);
// Should be empty array
```

**Test Audit Log:**
```typescript
const auditLogs = await prisma.$queryRaw`
  SELECT * FROM "audit_log"
  WHERE target_id = 'test-user'
  AND action = 'DELETE'
`;

console.log('Audit logs:', auditLogs);
// Should show deletion event
```

**Test Restoration:**
```typescript
import { restoreUser } from '@taboot/db';

await restoreUser(prisma, 'test-user', 'admin-user');

const restored = await prisma.user.findUnique({
  where: { id: 'test-user' },
});

console.log('Restored:', restored);
// Should show user with deletedAt = null
```

## Step 4: Run Automated Tests

```bash
# Run soft delete test suite
pnpm test tests/packages-ts/db/soft-delete.test.ts

# Expected output:
# ✓ should convert DELETE to UPDATE with deletedAt
# ✓ should write audit log on DELETE
# ✓ should filter soft-deleted users from findMany
# ✓ should restore soft-deleted user
# ... (all tests passing)
```

## Step 5: Deploy to Production

### Option A: Direct Migration

```bash
cd packages-ts/db

# Apply migration to production
DATABASE_URL="postgresql://user:pass@prod-host:5432/taboot" \
  pnpm prisma migrate deploy

# Verify migration
DATABASE_URL="postgresql://user:pass@prod-host:5432/taboot" \
  pnpm prisma migrate status
```

### Option B: Docker Deployment

**Update docker-compose.yaml (if needed):**
```yaml
services:
  taboot-db-migrate:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./packages-ts/db:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
    command: sh -c "pnpm install && pnpm prisma migrate deploy"
    depends_on:
      - taboot-db
```

**Run migration:**
```bash
docker compose run --rm taboot-db-migrate
```

### Option C: Manual SQL (if Prisma CLI unavailable)

```sql
-- Connect to production database
psql -h prod-host -U postgres -d taboot

-- Apply migration manually
ALTER TABLE "user" ADD COLUMN "deleted_at" TIMESTAMP;
ALTER TABLE "user" ADD COLUMN "deleted_by" TEXT;

CREATE TABLE "audit_log" (
  "id" TEXT NOT NULL,
  "user_id" TEXT,
  "target_id" TEXT NOT NULL,
  "target_type" TEXT NOT NULL,
  "action" TEXT NOT NULL,
  "metadata" JSONB,
  "ip_address" TEXT,
  "user_agent" TEXT,
  "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id")
);

CREATE INDEX "user_deleted_at_idx" ON "user"("deleted_at");
CREATE INDEX "audit_log_target_id_target_type_idx" ON "audit_log"("target_id", "target_type");
CREATE INDEX "audit_log_user_id_idx" ON "audit_log"("user_id");
CREATE INDEX "audit_log_created_at_idx" ON "audit_log"("created_at");

-- Insert migration record
INSERT INTO "_prisma_migrations" (id, checksum, finished_at, migration_name, logs, rolled_back_at, started_at, applied_steps_count)
VALUES (
  gen_random_uuid()::text,
  'checksum-here',
  NOW(),
  'add-soft-delete-and-audit',
  NULL,
  NULL,
  NOW(),
  1
);
```

## Step 6: Deploy Application Changes

**Rebuild Application:**
```bash
# Regenerate Prisma client
cd packages-ts/db
pnpm prisma generate

# Build application
cd ../..
pnpm build

# Restart services
docker compose restart taboot-app
```

## Step 7: Setup Cleanup Job

### Systemd Timer (Recommended)

**Create service file:**
```bash
sudo tee /etc/systemd/system/taboot-cleanup.service << EOF
[Unit]
Description=Taboot User Cleanup
After=network.target

[Service]
Type=oneshot
User=taboot
WorkingDirectory=/opt/taboot
Environment="NODE_ENV=production"
Environment="DATABASE_URL=postgresql://user:pass@host:5432/taboot"
ExecStart=/usr/bin/pnpm tsx apps/web/scripts/cleanup-deleted-users.ts
StandardOutput=append:/var/log/taboot-cleanup.log
StandardError=append:/var/log/taboot-cleanup.log
EOF
```

**Create timer file:**
```bash
sudo tee /etc/systemd/system/taboot-cleanup.timer << EOF
[Unit]
Description=Run Taboot User Cleanup Daily
Requires=taboot-cleanup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable taboot-cleanup.timer
sudo systemctl start taboot-cleanup.timer
sudo systemctl status taboot-cleanup.timer
```

### Cron Job (Alternative)

```bash
# Edit crontab
crontab -e

# Add daily cleanup at 2 AM
0 2 * * * cd /opt/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts >> /var/log/taboot-cleanup.log 2>&1
```

### Kubernetes CronJob (Alternative)

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: taboot-cleanup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: taboot:latest
            command: ["pnpm", "tsx", "apps/web/scripts/cleanup-deleted-users.ts"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: taboot-secrets
                  key: database-url
          restartPolicy: OnFailure
```

## Step 8: Verify Production Deployment

### 1. Check Database Schema
```sql
-- Verify columns added
\d "user"
-- Should show deleted_at and deleted_by

-- Verify audit_log table
\d "audit_log"

-- Check indexes
\di user_deleted_at_idx
\di audit_log_target_id_target_type_idx
```

### 2. Test Soft Delete Behavior
```bash
# Create test user via API
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "Test"}'

# Delete user (should be soft delete)
curl -X DELETE http://localhost:8000/api/users/test-user-id

# Verify in database
psql -h localhost -U postgres -d taboot -c \
  "SELECT id, email, deleted_at FROM user WHERE id = 'test-user-id'"
```

### 3. Verify Audit Logging
```sql
SELECT * FROM "audit_log" ORDER BY created_at DESC LIMIT 10;
-- Should show recent DELETE actions
```

### 4. Test Cleanup Script
```bash
# Dry run
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --dry-run

# Should show:
# - Number of users to delete
# - User details
# - "DRY RUN: No changes made"
```

## Step 9: Monitor Deployment

### Check Logs
```bash
# Application logs
docker compose logs -f taboot-app

# Cleanup logs
tail -f /var/log/taboot-cleanup.log

# Database logs
docker compose logs -f taboot-db
```

### Verify Metrics
```sql
-- Count soft-deleted users
SELECT COUNT(*) FROM "user" WHERE deleted_at IS NOT NULL;

-- Recent audit events
SELECT action, COUNT(*) FROM "audit_log"
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY action;

-- Oldest soft-deleted user
SELECT email, deleted_at FROM "user"
WHERE deleted_at IS NOT NULL
ORDER BY deleted_at ASC
LIMIT 1;
```

## Rollback Procedure

If issues occur:

### 1. Revert Application Code
```bash
git revert <commit-hash>
pnpm build
docker compose restart taboot-app
```

### 2. Revert Database Migration (if needed)
```bash
cd packages-ts/db

# Rollback last migration
pnpm prisma migrate resolve --rolled-back add-soft-delete-and-audit

# Drop added columns/tables
psql -h localhost -U postgres -d taboot << EOF
DROP TABLE IF EXISTS "audit_log";
ALTER TABLE "user" DROP COLUMN IF EXISTS "deleted_at";
ALTER TABLE "user" DROP COLUMN IF EXISTS "deleted_by";
DROP INDEX IF EXISTS "user_deleted_at_idx";
EOF
```

### 3. Restore from Backup (if needed)
```bash
# Stop application
docker compose stop taboot-app

# Restore database
pg_restore -h localhost -U postgres -d taboot backup.dump

# Restart application
docker compose start taboot-app
```

## Troubleshooting

### Issue: Migration fails with "column already exists"

**Solution:** Drop existing columns first
```sql
ALTER TABLE "user" DROP COLUMN IF EXISTS "deleted_at";
ALTER TABLE "user" DROP COLUMN IF EXISTS "deleted_by";
```

### Issue: Tests fail after migration

**Solution:** Regenerate Prisma client
```bash
cd packages-ts/db
pnpm prisma generate
pnpm test
```

### Issue: Soft delete not working

**Solution:** Verify middleware is applied
```typescript
// Check packages-ts/db/src/client.ts
import { softDeleteMiddleware } from './middleware/soft-delete';
prisma.$use(softDeleteMiddleware());
```

### Issue: Cleanup job not running

**Solution:** Check systemd timer status
```bash
sudo systemctl status taboot-cleanup.timer
sudo journalctl -u taboot-cleanup.service -n 50
```

## Success Criteria

- ✅ Migration applied successfully
- ✅ All tests passing
- ✅ Soft delete working (DELETE sets deletedAt)
- ✅ Queries filter soft-deleted users
- ✅ Audit logs written for deletions
- ✅ Restoration API working
- ✅ Cleanup job scheduled
- ✅ No errors in application logs
- ✅ Production monitoring shows expected behavior

## Post-Deployment

1. **Monitor for 48 hours:**
   - Watch application logs
   - Check audit log growth
   - Verify soft delete behavior

2. **Review audit logs weekly:**
   - Unexpected deletions
   - Restoration requests
   - Cleanup job results

3. **Adjust retention period if needed:**
   - Default: 90 days
   - Can be changed via `--retention-days` flag

4. **Consider UI enhancements:**
   - Admin dashboard for deleted users
   - One-click restoration
   - Audit log viewer

## References

- Implementation Summary: `/home/jmagar/code/taboot/todos/009-IMPLEMENTATION-SUMMARY.md`
- Cleanup Script Guide: `/home/jmagar/code/taboot/apps/web/scripts/README.md`
- Soft Delete Documentation: `/home/jmagar/code/taboot/CLAUDE.md#data-integrity--soft-delete`
