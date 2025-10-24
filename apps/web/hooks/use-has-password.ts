import { useQuery } from '@tanstack/react-query';

import { api } from '@/lib/api';

export function useHasPassword() {
  return useQuery({
    queryKey: ['has-password'],
    queryFn: async () => {
      const response = await api.get<{ hasPassword: boolean }>('/auth/password');
      if (response.error) {
        throw new Error(response.error);
      }
      return Boolean(response.data?.hasPassword);
    },
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}
