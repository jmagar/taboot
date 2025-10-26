'use server';

import { revalidateTag } from 'next/cache';

/**
 * Invalidate the session cache after auth state changes.
 * Call this after sign-out, password changes, or other auth mutations
 * to ensure cached session data is refreshed.
 *
 * This mitigates the double-caching issue where both better-auth (5min)
 * and unstable_cache (60s) cache session data.
 */
export async function revalidateSessionCache(): Promise<void> {
  // Revalidate session cache using Next.js 16's max profile
  // The 'max' profile has: stale=1year, revalidate=1year, expire=1year
  // See: https://nextjs.org/docs/app/api-reference/functions/unstable_cache#revalidate
  revalidateTag('session', 'max');
}
