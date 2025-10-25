import { useQuery } from '@tanstack/react-query';

import { typedApi } from '@/lib/api-typed';
import { queryKeys } from '@/lib/query-keys';
import { hasPasswordResponseSchema, type HasPasswordResponse } from '@/lib/schemas/auth';

export function useHasPassword() {
  return useQuery({
    queryKey: queryKeys.auth.hasPassword(),
    queryFn: async (): Promise<boolean> => {
      const response: HasPasswordResponse = await typedApi.get({
        path: '/auth/password',
        responseSchema: hasPasswordResponseSchema,
      });
      return response.hasPassword;
    },
    staleTime: 30 * 60 * 1000, // 30 minutes - password state changes infrequently
    gcTime: 60 * 60 * 1000, // 1 hour - keep in cache longer
  });
}
