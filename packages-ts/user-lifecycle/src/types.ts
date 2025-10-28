/**
 * User Lifecycle Types
 *
 * Type definitions for user deletion and lifecycle management.
 */

/**
 * Options for cleanup operations
 */
export interface CleanupOptions {
  /** Number of days after deletion before permanent removal */
  retentionDays: number;
  /** Preview mode - no actual deletions will occur */
  dryRun: boolean;
}

/**
 * User deletion summary for reporting
 */
export interface UserDeletionSummary {
  /** User ID */
  id: string;
  /** When the user was soft-deleted (null if not deleted) */
  deletedAt: Date | null;
  /** Who initiated the soft-delete (null if unknown) */
  deletedBy: string | null;
  /** Count of related records */
  relatedRecords: {
    sessions: number;
    accounts: number;
    twofactors: number;
  };
}

/**
 * Cleanup execution result
 */
export interface CleanupResult {
  /** Total users found eligible for deletion */
  totalFound: number;
  /** Number of users successfully deleted */
  successCount: number;
  /** Number of users that failed to delete */
  failedCount: number;
  /** Cutoff date used for filtering */
  cutoffDate: Date;
  /** Was this a dry run? */
  wasDryRun: boolean;
  /** List of user IDs that failed to delete */
  failedUserIds: string[];
  /** Summary of users processed (redacted in production) */
  users: UserDeletionSummary[];
}

/**
 * Logger interface for dependency injection
 */
export interface Logger {
  log(message: string): void;
  error(message: string, error?: unknown): void;
}

/**
 * Dependencies required by cleanup service
 */
export interface CleanupDependencies {
  /** Prisma client instance */
  prisma: {
    user: {
      count(args: unknown): Promise<number>;
      findMany(args: unknown): Promise<unknown[]>;
    };
    $executeRaw(query: TemplateStringsArray, ...values: unknown[]): Promise<unknown>;
  };
  /** Logger instance */
  logger: Logger;
  /** Verbose logging (includes PII like emails) - default: false */
  verbose?: boolean;
}
