# @taboot/user-lifecycle

User lifecycle management services including soft-delete cleanup.

## Installation

```bash
pnpm add @taboot/user-lifecycle
```

## Features

- **Soft-delete cleanup**: Permanently delete users that have been soft-deleted beyond retention period
- **PII-safe logging**: Email addresses are masked by default (`u***r@example.com`)
- **Batch processing**: Handles large datasets with pagination
- **Audit logging**: Full audit trail for all hard deletions
- **Framework-agnostic**: Core logic separated from CLI/HTTP layers

## Usage

### Core Service

```typescript
import { cleanupDeletedUsersService } from '@taboot/user-lifecycle';
import { prisma } from '@taboot/db';

const result = await cleanupDeletedUsersService(
  {
    retentionDays: 90,
    dryRun: false,
  },
  {
    prisma,
    logger: {
      log: (msg) => console.log(msg),
      error: (msg, err) => console.error(msg, err),
    },
    verbose: false, // Set to true to log full email addresses (PII)
  }
);

console.log(`Deleted ${result.successCount} users`);
if (result.failedCount > 0) {
  console.error(`Failed to delete ${result.failedCount} users`);
}
```

### CLI Script

The package is used by the cleanup script at `apps/web/scripts/cleanup-deleted-users.ts`:

```bash
# Dry run (preview only)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --dry-run

# Execute deletions with default retention (90 days)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --force

# Custom retention period
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --retention-days=30 --force

# Verbose mode (logs full email addresses - WARNING: logs PII)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --verbose --force
```

## API

### `cleanupDeletedUsersService(options, deps)`

Main service function for deleting soft-deleted users.

**Parameters:**

- `options: CleanupOptions`
  - `retentionDays: number` - Number of days to retain soft-deleted users (default: 90)
  - `dryRun: boolean` - Preview mode, no actual deletions (default: false)

- `deps: CleanupDependencies`
  - `prisma` - Prisma client instance
  - `logger` - Logger instance with `log()` and `error()` methods
  - `verbose?: boolean` - Include email addresses in logs (default: false)

**Returns:** `Promise<CleanupResult>`

```typescript
interface CleanupResult {
  totalFound: number;
  successCount: number;
  failedCount: number;
  cutoffDate: Date;
  wasDryRun: boolean;
  failedUserIds: string[];
  users: UserDeletionSummary[];
}
```

### Utilities

#### `maskEmail(email)`

Mask email addresses for PII-safe logging.

```typescript
import { maskEmail } from '@taboot/user-lifecycle';

maskEmail('john.doe@example.com'); // "j***e@example.com"
maskEmail('a@test.com');           // "a***@test.com"
maskEmail(null);                   // "[no email]"
```

#### `calculateCutoffDate(retentionDays)`

Calculate cutoff date based on retention policy.

```typescript
import { calculateCutoffDate } from '@taboot/user-lifecycle';

const cutoff = calculateCutoffDate(90);
// Returns date 90 days ago
```

## Security

⚠️ **IMPORTANT**: Output from this service should be treated as sensitive.

- **Default behavior**: Email addresses are masked (`u***r@example.com`)
- **Verbose mode**: Full email addresses logged (use with caution in production)
- **Audit trail**: All deletions logged to `auth.audit_log` table
- **SQL injection protection**: Uses Prisma parameterized queries

## Testing

```bash
pnpm test
```

Tests verify:
- Dry run mode (no deletions)
- Production mode (actual deletions)
- PII masking (email addresses)
- Verbose mode (full emails)
- Error handling (failed deletions)
- Audit logging (SQL queries)
- Edge cases (null emails, no users, etc.)

## Architecture

This package follows the project's architecture guidelines:

- **Core logic**: Framework-agnostic service layer (`cleanup-service.ts`)
- **No process.exit**: Services return results instead of exiting
- **No environment-specific behavior**: CLI layer handles interactivity, CI detection, etc.
- **Dependency injection**: Prisma and logger injected, not imported directly
- **Type safety**: Full TypeScript types, no `any`

## Related

- `packages-ts/db` - Prisma client and soft-delete middleware
- `apps/web/scripts/cleanup-deleted-users.ts` - CLI wrapper
- `packages-ts/db/prisma/schema.prisma` - User model with soft-delete

## License

MIT
