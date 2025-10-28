/**
 * User Lifecycle Utilities
 *
 * Utility functions for user lifecycle operations, including PII masking.
 */

/**
 * Mask email addresses to prevent PII exposure in logs
 *
 * Converts: user@example.com → u***r@example.com
 * Converts: a@test.com → a***@test.com (single char preserved)
 * Converts: null/undefined → "[no email]"
 *
 * @param email - Email address to mask (can be null/undefined)
 * @returns Masked email address safe for logging
 *
 * @example
 * maskEmail("john.doe@example.com") // "j***e@example.com"
 * maskEmail("a@test.com")           // "a***@test.com"
 * maskEmail(null)                   // "[no email]"
 */
export function maskEmail(email: string | null | undefined): string {
  if (!email) {
    return '[no email]';
  }

  const [localPart, domain] = email.split('@');

  if (!localPart || !domain) {
    return '[invalid email]';
  }

  // Preserve first and last character if possible
  if (localPart.length === 1) {
    return `${localPart}***@${domain}`;
  }

  const firstChar = localPart[0];
  const lastChar = localPart[localPart.length - 1];

  return `${firstChar}***${lastChar}@${domain}`;
}

/**
 * Format a date for display in logs
 *
 * @param date - Date to format
 * @returns ISO 8601 formatted string
 */
export function formatDate(date: Date | null | undefined): string {
  if (!date) {
    return '[unknown]';
  }

  return date.toISOString();
}

/**
 * Calculate cutoff date for retention policy
 *
 * @param retentionDays - Number of days to retain soft-deleted users
 * @returns Cutoff date (users deleted before this date will be hard-deleted)
 */
export function calculateCutoffDate(retentionDays: number): Date {
  const now = new Date();
  const millisecondsPerDay = 24 * 60 * 60 * 1000;
  const cutoffTime = now.getTime() - retentionDays * millisecondsPerDay;
  return new Date(cutoffTime);
}
