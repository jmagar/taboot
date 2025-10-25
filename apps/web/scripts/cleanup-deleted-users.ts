#!/usr/bin/env tsx
/**
 * Cleanup Deleted Users Script
 *
 * Permanently deletes users that have been soft-deleted for 90+ days.
 * This script should be run periodically via cron job.
 *
 * Usage:
 *   pnpm tsx apps/web/scripts/cleanup-deleted-users.ts [--dry-run] [--retention-days=90]
 *
 * Cron schedule (daily at 2 AM):
 *   0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts
 */

import { prisma } from '@taboot/db';

interface CleanupOptions {
  dryRun: boolean;
  retentionDays: number;
}

/**
 * Log audit entry for hard deletion
 */
async function logHardDeletion(
  userId: string,
  deletedAt: Date,
  retentionDays: number
): Promise<void> {
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
  const { dryRun, retentionDays } = options;

  console.log(`Starting cleanup of users deleted ${retentionDays}+ days ago...`);
  console.log(`Mode: ${dryRun ? 'DRY RUN (no changes will be made)' : 'PRODUCTION'}`);

  // Calculate cutoff date
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - retentionDays);

  console.log(`Cutoff date: ${cutoffDate.toISOString()}`);

  // Find users to delete (bypass soft delete filter)
  const usersToDelete = await prisma.user.findMany({
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
  });

  console.log(`Found ${usersToDelete.length} users to permanently delete`);

  if (usersToDelete.length === 0) {
    console.log('No users to delete. Exiting.');
    return;
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
  if (process.stdin.isTTY && !process.env.CI) {
    const readline = require('readline').createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    const answer = await new Promise<string>((resolve) => {
      readline.question(
        '\nProceed with permanent deletion? (yes/no): ',
        (ans: string) => {
          readline.close();
          resolve(ans);
        }
      );
    });

    if (answer.toLowerCase() !== 'yes') {
      console.log('Deletion cancelled.');
      return;
    }
  }

  // Perform deletions
  console.log('\nDeleting users...');
  let deletedCount = 0;
  let failedCount = 0;

  for (const user of usersToDelete) {
    try {
      // Log deletion before removing
      await logHardDeletion(user.id, user.deletedAt!, retentionDays);

      // Hard delete (cascade will remove related records)
      await prisma.$executeRaw`
        DELETE FROM "user" WHERE id = ${user.id}
      `;

      deletedCount++;
      console.log(`  ✓ Deleted ${user.email}`);
    } catch (error) {
      failedCount++;
      console.error(`  ✗ Failed to delete ${user.email}:`, error);
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
  };

  const retentionArg = args.find((arg) => arg.startsWith('--retention-days='));
  if (retentionArg) {
    const days = parseInt(retentionArg.split('=')[1], 10);
    if (isNaN(days) || days < 1) {
      console.error('Invalid retention days value. Must be a positive integer.');
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

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Unhandled error:', error);
    process.exit(1);
  });
}

export { cleanupDeletedUsers, parseArgs };
