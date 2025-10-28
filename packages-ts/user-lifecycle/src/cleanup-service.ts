/**
 * User Cleanup Service
 *
 * Core orchestration logic for permanently deleting soft-deleted users.
 * This service is framework-agnostic and can be used from CLI, API, or cron jobs.
 *
 * SECURITY NOTE: Output from this service should be treated as sensitive.
 * Use verbose=false (default) in production to avoid logging PII.
 */

import type {
  CleanupDependencies,
  CleanupOptions,
  CleanupResult,
  UserDeletionSummary,
} from './types';
import { calculateCutoffDate, formatDate, maskEmail } from './utils';

// Batch size for processing large datasets
const BATCH_SIZE = 100;

/**
 * Log audit entry for hard deletion
 *
 * SECURITY: Uses Prisma tagged template literals for SQL injection protection.
 * All ${...} values are sent as query parameters, not string interpolation.
 *
 * @param deps - Dependencies (prisma client)
 * @param userId - ID of user being hard-deleted
 * @param deletedAt - When user was originally soft-deleted
 * @param retentionDays - Retention period in days
 */
async function logHardDeletion(
  deps: CleanupDependencies,
  userId: string,
  deletedAt: Date,
  retentionDays: number
): Promise<void> {
  // SAFE: Prisma tagged templates use parameterized queries
  await deps.prisma.$executeRaw`
    INSERT INTO "auth"."audit_log" (
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
 * Fetch users eligible for permanent deletion
 *
 * @param deps - Dependencies (prisma, logger)
 * @param cutoffDate - Users deleted before this date will be returned
 * @returns Array of users with deletion summaries
 */
async function fetchUsersToDelete(
  deps: CleanupDependencies,
  cutoffDate: Date
): Promise<UserDeletionSummary[]> {
  const users: UserDeletionSummary[] = [];
  let skip = 0;

  while (true) {
    const batch = (await deps.prisma.user.findMany({
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
    })) as Array<{
      id: string;
      email: string | null;
      deletedAt: Date | null;
      deletedBy: string | null;
      _count: { sessions: number; accounts: number; twofactors: number };
    }>;

    if (batch.length === 0) {
      break;
    }

    // Map to summary format (removing email for non-verbose mode)
    users.push(
      ...batch.map((user) => ({
        id: user.id,
        deletedAt: user.deletedAt,
        deletedBy: user.deletedBy,
        relatedRecords: {
          sessions: user._count.sessions,
          accounts: user._count.accounts,
          twofactors: user._count.twofactors,
        },
      }))
    );

    skip += batch.length;
  }

  return users;
}

/**
 * Execute permanent deletion of users
 *
 * @param deps - Dependencies (prisma, logger, verbose)
 * @param users - Users to delete (with summaries)
 * @param retentionDays - Retention period (for audit logging)
 * @param userEmailMap - Map of user IDs to emails (for logging)
 * @returns Counts of successful and failed deletions, plus failed user IDs
 */
async function executeUserDeletions(
  deps: CleanupDependencies,
  users: UserDeletionSummary[],
  retentionDays: number,
  userEmailMap: Map<string, string | null>
): Promise<{ successCount: number; failedCount: number; failedUserIds: string[] }> {
  let successCount = 0;
  let failedCount = 0;
  const failedUserIds: string[] = [];
  let batchNumber = 0;

  for (let i = 0; i < users.length; i += BATCH_SIZE) {
    const batch = users.slice(i, i + BATCH_SIZE);
    batchNumber++;

    deps.logger.log(
      `Processing batch ${batchNumber} (${i + 1}-${i + batch.length} of ${users.length})...`
    );

    for (const user of batch) {
      try {
        // Hard delete using raw SQL to bypass soft-delete middleware
        // Cascade deletes are handled by database foreign key constraints
        await deps.prisma.$executeRaw`DELETE FROM "auth"."user" WHERE id = ${user.id}`;

        // Log deletion AFTER successful removal
        await logHardDeletion(deps, user.id, user.deletedAt!, retentionDays);

        successCount++;

        // Log based on verbose flag
        const userEmail = userEmailMap.get(user.id);
        if (deps.verbose) {
          deps.logger.log(`  ✓ Deleted ${userEmail} (ID: ${user.id})`);
        } else {
          deps.logger.log(`  ✓ Deleted ${maskEmail(userEmail)} (ID: ${user.id})`);
        }
      } catch (error) {
        failedCount++;
        failedUserIds.push(user.id);

        const userEmail = userEmailMap.get(user.id);
        if (deps.verbose) {
          deps.logger.error(`  ✗ Failed to delete ${userEmail} (ID: ${user.id})`, error);
        } else {
          deps.logger.error(`  ✗ Failed to delete ${maskEmail(userEmail)} (ID: ${user.id})`, error);
        }
      }
    }
  }

  return { successCount, failedCount, failedUserIds };
}

/**
 * Permanently delete users that have been soft-deleted beyond retention period
 *
 * This is the main orchestration function that:
 * 1. Calculates cutoff date based on retention policy
 * 2. Fetches eligible users (paginated)
 * 3. Executes batch deletions with audit logging
 * 4. Returns comprehensive results
 *
 * @param options - Cleanup options (retentionDays, dryRun)
 * @param deps - Dependencies (prisma, logger, verbose)
 * @returns Cleanup result with counts, user summaries, and any errors
 *
 * @example
 * const result = await cleanupDeletedUsersService(
 *   { retentionDays: 90, dryRun: false },
 *   { prisma, logger, verbose: false }
 * );
 *
 * if (result.failedCount > 0) {
 *   // Handle failures
 * }
 */
export async function cleanupDeletedUsersService(
  options: CleanupOptions,
  deps: CleanupDependencies
): Promise<CleanupResult> {
  const { retentionDays, dryRun } = options;

  deps.logger.log(`Starting cleanup of users deleted ${retentionDays}+ days ago...`);
  deps.logger.log(`Mode: ${dryRun ? 'DRY RUN (no changes will be made)' : 'PRODUCTION'}`);

  // Calculate cutoff date
  const cutoffDate = calculateCutoffDate(retentionDays);
  deps.logger.log(`Cutoff date: ${formatDate(cutoffDate)}`);

  // Count total users to delete
  const totalCount = await deps.prisma.user.count({
    where: {
      deletedAt: {
        not: null,
        lte: cutoffDate,
      },
    },
  });

  deps.logger.log(`Found ${totalCount} users to permanently delete`);

  if (totalCount === 0) {
    deps.logger.log('No users to delete.');
    return {
      totalFound: 0,
      successCount: 0,
      failedCount: 0,
      cutoffDate,
      wasDryRun: dryRun,
      failedUserIds: [],
      users: [],
    };
  }

  // Fetch users for summary (paginated to avoid memory issues)
  const users = await fetchUsersToDelete(deps, cutoffDate);

  // Build email map for logging (separate from summary to avoid PII in return value)
  const userEmailMap = new Map<string, string | null>();
  let skip = 0;
  while (true) {
    const batch = (await deps.prisma.user.findMany({
      where: {
        deletedAt: {
          not: null,
          lte: cutoffDate,
        },
      },
      select: {
        id: true,
        email: true,
      },
      take: BATCH_SIZE,
      skip,
    })) as Array<{ id: string; email: string | null }>;

    if (batch.length === 0) {
      break;
    }

    batch.forEach((user) => userEmailMap.set(user.id, user.email));
    skip += batch.length;
  }

  // Display summary
  deps.logger.log('\nUsers to be permanently deleted:');
  for (const user of users) {
    const userEmail = userEmailMap.get(user.id);

    if (deps.verbose) {
      deps.logger.log(`  - ${userEmail} (ID: ${user.id})`);
    } else {
      deps.logger.log(`  - ${maskEmail(userEmail)} (ID: ${user.id})`);
    }

    deps.logger.log(`    Deleted at: ${formatDate(user.deletedAt)}`);
    deps.logger.log(`    Deleted by: ${user.deletedBy || 'unknown'}`);
    deps.logger.log(
      `    Related records: ${user.relatedRecords.sessions} sessions, ${user.relatedRecords.accounts} accounts, ${user.relatedRecords.twofactors} 2FA`
    );
  }

  if (dryRun) {
    deps.logger.log('\nDRY RUN: No changes made.');
    return {
      totalFound: totalCount,
      successCount: 0,
      failedCount: 0,
      cutoffDate,
      wasDryRun: true,
      failedUserIds: [],
      users,
    };
  }

  // Perform deletions in batches
  deps.logger.log('\nDeleting users in batches...');

  const { successCount, failedCount, failedUserIds } = await executeUserDeletions(
    deps,
    users,
    retentionDays,
    userEmailMap
  );

  deps.logger.log('\nCleanup completed:');
  deps.logger.log(`  Successfully deleted: ${successCount}`);
  deps.logger.log(`  Failed: ${failedCount}`);

  return {
    totalFound: totalCount,
    successCount,
    failedCount,
    cutoffDate,
    wasDryRun: false,
    failedUserIds,
    users,
  };
}
