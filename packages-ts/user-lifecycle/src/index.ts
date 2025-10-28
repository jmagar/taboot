/**
 * @taboot/user-lifecycle
 *
 * User lifecycle management services including soft-delete cleanup.
 *
 * SECURITY NOTE: This package handles PII. Use verbose=false in production
 * to avoid logging email addresses.
 */

export { cleanupDeletedUsersService } from './cleanup-service';
export type {
  CleanupDependencies,
  CleanupOptions,
  CleanupResult,
  Logger,
  UserDeletionSummary,
} from './types';
export { calculateCutoffDate, formatDate, maskEmail } from './utils';
