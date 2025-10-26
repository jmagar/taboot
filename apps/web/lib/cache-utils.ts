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
  // Next.js 16 requires a second parameter for revalidateTag
  // Using 'default' profile which expires immediately
  revalidateTag('session', 'default');
}
