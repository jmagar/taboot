/**
 * Validates a callback URL to prevent open redirect vulnerabilities.
 *
 * @param rawUrl - The raw callback URL from user input or query parameters
 * @returns A safe, validated callback URL (defaults to '/' if invalid)
 *
 * Security rules:
 * - Must be a string
 * - Must start with '/' (relative path)
 * - Must NOT start with '//' (protocol-relative URL)
 */
export function validateCallbackUrl(rawUrl: string | null | undefined): string {
  if (typeof rawUrl !== 'string' || rawUrl.length === 0) {
    return '/';
  }

  // Must start with '/' but not '//' to prevent open redirects
  if (rawUrl.startsWith('/') && !rawUrl.startsWith('//')) {
    return rawUrl;
  }

  return '/';
}
