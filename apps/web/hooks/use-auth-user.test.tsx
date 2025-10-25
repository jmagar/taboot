import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthUser, useRequiredAuthUser } from './use-auth-user';

// Mock the auth client
vi.mock('@taboot/auth/client', () => ({
  useSession: vi.fn(),
}));

// Mock next/navigation
const mockPush = vi.fn();
const mockPathname = '/';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => mockPathname,
}));

describe('useAuthUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return null user when not authenticated', async () => {
    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useAuthUser());

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('should return user when authenticated', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      name: 'Test User',
      image: null,
      emailVerified: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      twoFactorEnabled: false,
    };

    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: { user: mockUser, session: { userId: '123', expiresAt: new Date() } },
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useAuthUser());

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.isLoading).toBe(false);
  });

  it('should be loading when session is pending', async () => {
    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: null,
      isPending: true,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useAuthUser());

    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(true);
  });

  it('should not redirect by default when unauthenticated', async () => {
    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    renderHook(() => useAuthUser());

    expect(mockPush).not.toHaveBeenCalled();
  });
});

describe('useRequiredAuthUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should return loading state when session is pending', async () => {
    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: null,
      isPending: true,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useRequiredAuthUser());

    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(true);
  });

  it('should return loading state when not authenticated', async () => {
    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: null,
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useRequiredAuthUser());

    expect(result.current.user).toBeNull();
    expect(result.current.isLoading).toBe(true);
  });

  it('should return user when authenticated', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      name: 'Test User',
      image: null,
      emailVerified: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      twoFactorEnabled: false,
    };

    const { useSession } = await import('@taboot/auth/client');
    vi.mocked(useSession).mockReturnValue({
      data: { user: mockUser, session: { userId: '123', expiresAt: new Date() } },
      isPending: false,
      error: null,
      refetch: vi.fn(),
    });

    const { result } = renderHook(() => useRequiredAuthUser());

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isLoading).toBe(false);
  });
});
