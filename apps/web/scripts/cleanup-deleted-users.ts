#!/usr/bin/env tsx
/**
 * Cleanup Deleted Users Script
 *
 * Permanently deletes users that have been soft-deleted for 90+ days.
 * This script should be run periodically via cron job.
 *
 * Usage:
 *   pnpm tsx apps/web/scripts/cleanup-deleted-users.ts [--dry-run] [--retention-days=90] [--force] [--verbose]
 *
 * Flags:
 *   --dry-run: Preview deletions without making changes
 *   --retention-days=N: Custom retention period (default: 90, max: 3650)
 *   --force: Skip interactive confirmation (required for automation)
 *   --verbose: Include email addresses in output (WARNING: logs PII)
 *
 * Cron schedule (daily at 2 AM):
 *   0 2 * * * cd /path/to/taboot && pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --force
 *
 * SECURITY NOTE: Output should be treated as sensitive when using --verbose flag.
 */

import { cleanupDeletedUsersService } from '@taboot/user-lifecycle';
import type { CleanupOptions, Logger } from '@taboot/user-lifecycle';
import { prisma } from '@taboot/db';
import * as readline from 'readline';

interface CliOptions extends CleanupOptions {
  force: boolean;
  verbose: boolean;
}

/**
 * Simple console logger implementation
 */
const consoleLogger: Logger = {
  log: (message: string) => console.log(message),
  error: (message: string, error?: unknown) => {
    console.error(message);
    if (error) {
      console.error(error);
    }
  },
};

/**
 * Parse command line arguments
 */
function parseArgs(): CliOptions {
  const args = process.argv.slice(2);

  const options: CliOptions = {
    dryRun: args.includes('--dry-run'),
    retentionDays: 90,
    force: args.includes('--force'),
    verbose: args.includes('--verbose'),
  };

  const retentionArg = args.find((arg) => arg.startsWith('--retention-days='));
  if (retentionArg) {
    const days = parseInt(retentionArg.split('=')[1] ?? '', 10);
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
 * Prompt user for confirmation in interactive mode
 *
 * @param force - Skip confirmation if true
 * @returns Promise that resolves to true if confirmed, false otherwise
 */
async function confirmDeletion(force: boolean): Promise<boolean> {
  // Check if running in non-interactive mode without --force
  if (!force && !process.stdin.isTTY && !process.env.CI) {
    console.error(
      '\nERROR: Running in non-interactive mode without --force flag.'
    );
    console.error(
      'For automation (Docker/Kubernetes/CI), use: --force to skip confirmation prompt.'
    );
    process.exit(1);
  }

  // Skip confirmation if --force is set
  if (force) {
    console.log('\nSkipping confirmation (--force flag set)');
    return true;
  }

  // Interactive confirmation
  const needsConfirmation = process.stdin.isTTY && !process.env.CI;

  if (!needsConfirmation) {
    return true;
  }

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
    return false;
  }

  return true;
}

/**
 * Main entry point
 */
async function main(): Promise<void> {
  const options = parseArgs();

  try {
    // Show warning if verbose mode is enabled
    if (options.verbose) {
      console.log('\n⚠️  WARNING: Verbose mode enabled - output will contain PII (email addresses)');
      console.log('⚠️  Ensure logs are stored securely and access is restricted.\n');
    }

    // First run: Always start with dry-run to show what will be deleted
    const previewResult = await cleanupDeletedUsersService(
      {
        retentionDays: options.retentionDays,
        dryRun: true,
      },
      {
        prisma,
        logger: consoleLogger,
        verbose: options.verbose,
      }
    );

    // If no users found, exit early
    if (previewResult.totalFound === 0) {
      process.exit(0);
    }

    // If user requested dry-run only, exit after preview
    if (options.dryRun) {
      console.log('\nRun without --dry-run to execute deletions.');
      process.exit(0);
    }

    // Confirm deletion in interactive mode
    const confirmed = await confirmDeletion(options.force);

    if (!confirmed) {
      process.exit(0);
    }

    // Execute actual deletions
    const result = await cleanupDeletedUsersService(
      {
        retentionDays: options.retentionDays,
        dryRun: false,
      },
      {
        prisma,
        logger: consoleLogger,
        verbose: options.verbose,
      }
    );

    // Exit with error code if any deletions failed
    if (result.failedCount > 0) {
      console.error(`\n⚠️  ${result.failedCount} users failed to delete. Review errors above.`);
      process.exit(1);
    }

    process.exit(0);
  } catch (error) {
    console.error('Error during cleanup:', error);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

// Run if executed directly (via tsx or node)
main().catch((error) => {
  console.error('Unhandled error:', error);
  process.exit(1);
});
