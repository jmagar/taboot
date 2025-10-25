import { auth, Session } from '@taboot/auth';
import { headers as getHeaders } from 'next/headers';
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

  // Extract session token for cache key (if available)
  const cookieHeader = headers.get('cookie') || '';
  const sessionToken = cookieHeader
    .split(';')
    .find((c) => c.trim().startsWith('better-auth.session_token='))
    ?.split('=')[1];

  // Cache session for 5 minutes to reduce auth checks
  // Cache key includes session token to ensure different users get different caches
  const getCachedSession = unstable_cache(
    async () => {
      return await auth.api.getSession({
        headers,
      });
    },
    ['session', sessionToken || 'anonymous'],
    {
      revalidate: 300, // 5 minutes
      tags: ['session'],
    }
  );

  return await getCachedSession();
}

/**
 * Require an authenticated session or redirect to sign-in.
 * This should be used in server components that require authentication.
 *
 * @param callbackUrl - Optional callback URL to redirect to after sign-in (defaults to current path)
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
