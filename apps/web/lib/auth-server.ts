import { auth } from '@taboot/auth';
import type { Session } from '@taboot/auth';
import { headers as getHeaders, cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { unstable_cache } from 'next/cache';

/**
 * Get the current session from the server with caching.
 * This should be used in server components and server actions.
 *
 * @returns The current session or null if not authenticated
 */
export async function getServerSession(): Promise<Session | null> {
  const headers = await getHeaders();

  // Extract session token for cache key using Next.js cookies API
  const cookieStore = await cookies();
  const sessionToken = cookieStore.get('better-auth.session_token')?.value;

  // Cache session for 1 minute to reduce auth checks
  // Cache key includes session token to ensure different users get different caches
  // CRITICAL: Shorter revalidation time (60s vs better-auth's 300s) to mitigate
  // double-caching issue. Auth state changes (sign-out, password change) should
  // also call revalidateTag('session') to invalidate cache immediately.
  const getCachedSession = unstable_cache(
    async () => {
      return await auth.api.getSession({
        headers,
      });
    },
    ['session', sessionToken || 'anonymous'],
    {
      revalidate: 60, // 1 minute (reduced from 5 min due to double-caching)
      tags: ['session'],
    }
  );

  return await getCachedSession();
}

/**
 * Require an authenticated session or redirect to sign-in.
 * This should be used in server components that require authentication.
 *
 * @param callbackUrl - Optional callback URL to redirect to after sign-in
 * @returns The authenticated session
 * @throws Redirects to sign-in page if not authenticated
 */
export async function requireServerSession(callbackUrl?: string): Promise<Session> {
  const session = await getServerSession();

  if (!session?.user) {
    const signInUrl = callbackUrl
      ? `/sign-in?callbackUrl=${encodeURIComponent(callbackUrl)}`
      : '/sign-in';
    redirect(signInUrl);
  }

  return session;
}
