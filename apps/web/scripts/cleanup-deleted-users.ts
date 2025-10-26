#!/usr/bin/env tsx
/**
 * Cleanup Deleted Users Script
 *
 * Permanently deletes users that have been soft-deleted for 90+ days.
 * This script should be run periodically via cron job.
 *
 * Usage:
 *   pnpm tsx apps/web/scripts/cleanup-deleted-users.ts [--dry-run] [--retention-days=90] [--force]
 *
 * Flags:
 *   --dry-run: Preview deletions without making changes
 *   --retention-days=N: Custom retention period (default: 90, max: 3650)
 *   --force: Skip interactive confirmation (required for automation)
 *
 * Cron schedule (daily at 2 AM):
 *   0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --force
 */

import { prisma } from '@taboot/db';
import * as readline from 'readline';

interface CleanupOptions {
  dryRun: boolean;
  retentionDays: number;
  force: boolean;
}

// Batch size for processing large datasets
const BATCH_SIZE = 100;

/**
 * Log audit entry for hard deletion
 *
 * SECURITY: Uses Prisma tagged template literals for SQL injection protection.
 * All ${...} values are sent as query parameters, not string interpolation.
 *
 * @see /home/jmagar/code/taboot/docs/security/AUDIT_SQL_INJECTION_AUDIT_LOG.md
 */
async function logHardDeletion(
  userId: string,
  deletedAt: Date,
  retentionDays: number
): Promise<void> {
  // SAFE: Prisma tagged templates use parameterized queries
  await prisma.$executeRaw`
    INSERT INTO "audit_log" (
      id, user_id, target_id, target_type, action,
      metadata, created_at
    ) VALUES (
      gen_random_uuid()::text,
      'system',
      ${userId},
      'User',
      'HARD_DELETE',
      ${JSON.stringify({
        originalDeletedAt: deletedAt,
        retentionPeriod: `${retentionDays} days`,
        hardDeletedAt: new Date(),
      })}::jsonb,
      NOW()
    )
  `;
}

/**
 * Permanently delete users that have been soft-deleted beyond retention period
 */
async function cleanupDeletedUsers(options: CleanupOptions): Promise<void> {
  const { dryRun, retentionDays, force } = options;

  console.log(`Starting cleanup of users deleted ${retentionDays}+ days ago...`);
  console.log(`Mode: ${dryRun ? 'DRY RUN (no changes will be made)' : 'PRODUCTION'}`);

  // Calculate cutoff date
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

  console.log(`Cutoff date: ${cutoffDate.toISOString()}`);

  // Count total users to delete
  const totalCount = await prisma.user.count({
    where: {
      deletedAt: {
        not: null,
        lte: cutoffDate,
      },
    },
  });

  console.log(`Found ${totalCount} users to permanently delete`);

  if (totalCount === 0) {
    console.log('No users to delete. Exiting.');
    return;
  }

  // Collect users for summary (paginated to avoid memory issues)
  const usersToDelete: Array<{
    id: string;
    email: string | null;
    deletedAt: Date | null;
    deletedBy: string | null;
    _count: { sessions: number; accounts: number; twofactors: number };
  }> = [];

  let skip = 0;
  while (true) {
    const batch = await prisma.user.findMany({
      where: {
        deletedAt: {
          not: null,
          lte: cutoffDate,
        },
      },
      select: {
        id: true,
        email: true,
        deletedAt: true,
        deletedBy: true,
        _count: {
          select: {
            sessions: true,
            accounts: true,
            twofactors: true,
          },
        },
      },
      take: BATCH_SIZE,
      skip,
    });

    if (batch.length === 0) {
      break;
    }

    usersToDelete.push(...batch);
    skip += batch.length;
  }

  // Display summary
  console.log('\nUsers to be permanently deleted:');
  for (const user of usersToDelete) {
    console.log(`  - ${user.email} (ID: ${user.id})`);
    console.log(`    Deleted at: ${user.deletedAt?.toISOString()}`);
    console.log(`    Deleted by: ${user.deletedBy || 'unknown'}`);
    console.log(
      `    Related records: ${user._count.sessions} sessions, ${user._count.accounts} accounts, ${user._count.twofactors} 2FA`
    );
  }

  if (dryRun) {
    console.log('\nDRY RUN: No changes made. Run without --dry-run to execute deletions.');
    return;
  }

  // Confirm in interactive mode
  const needsConfirmation = !force && process.stdin.isTTY && !process.env.CI;

  if (!force && !process.stdin.isTTY && !process.env.CI) {
    console.error(
      '\nERROR: Running in non-interactive mode without --force flag.'
    );
    console.error(
      'For automation (Docker/Kubernetes/CI), use: --force to skip confirmation prompt.'
    );
    process.exit(1);
  }

  if (needsConfirmation) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    const answer = await new Promise<string>((resolve) => {
      rl.question(
        '\nProceed with permanent deletion? (yes/no): ',
        (ans: string) => {
          rl.close();
          resolve(ans);
        }
      );
    });

    if (answer.toLowerCase() !== 'yes') {
      console.log('Deletion cancelled.');
      return;
    }
  } else if (force) {
    console.log('\nSkipping confirmation (--force flag set)');
  }

  // Perform deletions in batches
  console.log('\nDeleting users in batches...');
  let deletedCount = 0;
  let failedCount = 0;
  let batchNumber = 0;

  for (let i = 0; i < usersToDelete.length; i += BATCH_SIZE) {
    const batch = usersToDelete.slice(i, i + BATCH_SIZE);
    batchNumber++;
    console.log(
      `\nProcessing batch ${batchNumber} (${i + 1}-${i + batch.length} of ${usersToDelete.length})...`
    );

    for (const user of batch) {
      try {
        // Hard delete (cascade will remove related records)
        await prisma.user.delete({
          where: { id: user.id },
        });

        // Log deletion AFTER successful removal
        await logHardDeletion(user.id, user.deletedAt!, retentionDays);

        deletedCount++;
        console.log(`  ✓ Deleted ${user.email}`);
      } catch (error) {
        failedCount++;
        console.error(`  ✗ Failed to delete ${user.email}:`, error);
      }
    }
  }

  console.log('\nCleanup completed:');
  console.log(`  Successfully deleted: ${deletedCount}`);
  console.log(`  Failed: ${failedCount}`);
}

/**
 * Parse command line arguments
 */
function parseArgs(): CleanupOptions {
  const args = process.argv.slice(2);

  const options: CleanupOptions = {
    dryRun: args.includes('--dry-run'),
    retentionDays: 90,
    force: args.includes('--force'),
  };

  const retentionArg = args.find((arg) => arg.startsWith('--retention-days='));
  if (retentionArg) {
    const days = parseInt(retentionArg.split('=')[1], 10);
    if (isNaN(days) || days < 1 || days > 3650) {
      console.error(
        'Invalid retention days value. Must be between 1 and 3650 (10 years).'
      );
      process.exit(1);
    }
    options.retentionDays = days;
  }

  return options;
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  const options = parseArgs();

  try {
    await cleanupDeletedUsers(options);
  } catch (error) {
    console.error('Error during cleanup:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

// Run if executed directly (ESM module check)
const isMainModule =
  import.meta.url === `file://${process.argv[1]}` ||
  import.meta.url.endsWith(process.argv[1]);

if (isMainModule) {
  main().catch((error) => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

export { cleanupDeletedUsers, parseArgs };
