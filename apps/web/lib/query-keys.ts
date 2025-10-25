/**
 * Query key factory for React Query
 * Provides type-safe, hierarchical cache keys
 */

export const queryKeys = {
  auth: {
    all: ['auth'] as const,
    session: () => [...queryKeys.auth.all, 'session'] as const,
    hasPassword: () => [...queryKeys.auth.all, 'hasPassword'] as const,
  },
  user: {
    all: ['user'] as const,
    profile: (id: string) => [...queryKeys.user.all, 'profile', id] as const,
    settings: () => [...queryKeys.user.all, 'settings'] as const,
  },
  // Add more resource types as needed
} as const;
