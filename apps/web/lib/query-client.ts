import { QueryClient } from '@tanstack/react-query';
import { cache } from 'react';

/**
 * Server-side query client factory with React cache
 * Uses React's cache() to ensure single instance per request
 */
export const getQueryClient = cache(() => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
        retry: 1,
      },
    },
  });
});
