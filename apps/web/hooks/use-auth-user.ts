import { useSession } from '@taboot/auth/client';

type AuthUser = NonNullable<ReturnType<typeof useSession>['data']>['user'];

interface UseAuthUserReturn {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: ReturnType<typeof useSession>['error'];
  refetch: ReturnType<typeof useSession>['refetch'];
}

interface UseRequiredAuthUserReturn {
  user: AuthUser;
  isLoading: false;
  error: ReturnType<typeof useSession>['error'];
  refetch: ReturnType<typeof useSession>['refetch'];
}

interface UseRequiredAuthUserLoadingReturn {
  user: null;
  isLoading: true;
  error: ReturnType<typeof useSession>['error'];
  refetch: ReturnType<typeof useSession>['refetch'];
}

/**
 * Hook for handling authentication state.
 * Note: Authentication enforcement is handled by middleware at the server level.
 *
 * @returns Authentication state and user data
 */
export function useAuthUser(): UseAuthUserReturn {
  const session = useSession();

  return {
    user: session.data?.user || null,
    isLoading: session.isPending,
    isAuthenticated: !!session.data?.user,
    error: session.error,
    refetch: session.refetch,
  };
}

/**
 * Hook that guarantees an authenticated user is present.
 * Should only be used in components that require authentication.
 * Note: Server-side middleware handles redirects before this component renders.
 *
 * @returns Either user data when authenticated or loading state during auth check
 */
export function useRequiredAuthUser():
  | UseRequiredAuthUserReturn
  | UseRequiredAuthUserLoadingReturn {
  const { user, isLoading, error, refetch } = useAuthUser();

  if (isLoading) {
    return {
      user: null,
      isLoading: true,
      error,
      refetch,
    };
  }

  if (!user) {
    // This should not happen in protected routes due to middleware,
    // but we handle it gracefully by showing loading state
    return {
      user: null,
      isLoading: true,
      error,
      refetch,
    };
  }

  return {
    user,
    isLoading: false,
    error,
    refetch,
  };
}
