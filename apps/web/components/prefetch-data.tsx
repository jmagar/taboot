import { HydrationBoundary, QueryClient, dehydrate } from '@tanstack/react-query';
import { auth } from '@taboot/auth';
import { headers } from 'next/headers';

import { queryClientConfig } from '@/lib/query-client';
import { queryKeys } from '@/lib/query-keys';
import { authService } from '@/services/auth.service';

/**
 * Server component that prefetches common queries for faster page loads
 * Renders children with dehydrated state for client-side hydration
 */
export async function PrefetchData({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: queryClientConfig,
  });

  // Get session using real incoming request headers (includes cookies)
  const h = await headers();
  const session = await auth.api.getSession({ headers: h });

  if (session?.user) {
    // Prefetch hasPassword query for authenticated users
    // This will be available immediately on client-side when useHasPassword is called
    try {
      const hasPassword = await authService.hasPassword(session.user.id);
      queryClient.setQueryData(queryKeys.auth.hasPassword(), hasPassword);
    } catch {
      // Silently fail during prefetch - query will run on client if needed
    }

    // Add more prefetch queries here as needed
    // Example:
    // try {
    //   const settings = await fetchUserSettings(session.user.id);
    //   queryClient.setQueryData(queryKeys.user.settings(), settings);
    // } catch {
    //   // Silently fail
    // }
  }

  return <HydrationBoundary state={dehydrate(queryClient)}>{children}</HydrationBoundary>;
}
