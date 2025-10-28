/**
 * Authorization Helper Tests
 *
 * These tests verify the checkAdminAuthorization() helper function:
 * 1. No session → returns 401
 * 2. ADMIN_USER_ID not configured + attempting admin operation → returns 503
 * 3. Non-admin attempting admin operation → returns 403
 * 4. User operating on own account → returns 200 (authorized)
 * 5. Admin operating on other account → returns 200 (authorized)
 * 6. Admin operating on own account → returns 200 (authorized)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { checkAdminAuthorization } from '../auth-helpers';
import type { Session } from '@taboot/auth';

describe('checkAdminAuthorization', () => {
  let originalAdminUserId: string | undefined;

  beforeEach(() => {
    // Save original env var
    originalAdminUserId = process.env.ADMIN_USER_ID;

    // Mock console to avoid noise in test output
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    // Restore original env var
    if (originalAdminUserId === undefined) {
      delete process.env.ADMIN_USER_ID;
    } else {
      process.env.ADMIN_USER_ID = originalAdminUserId;
    }

    // Restore all mocks including console
    vi.restoreAllMocks();
  });

  describe('authentication failures', () => {
    it('should return 401 when session is null', async () => {
      const result = checkAdminAuthorization(null, 'user-123', 'test operation');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(401);

      // Verify error response body
      const body = await result!.json();
      expect(body.error).toBe('Unauthorized');
    });

    it('should return 401 when session has no user', async () => {
      const invalidSession = { user: null } as any as Session;
      const result = checkAdminAuthorization(invalidSession, 'user-123', 'test operation');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(401);

      const body = await result!.json();
      expect(body.error).toBe('Unauthorized');
    });
  });

  describe('admin configuration validation', () => {
    it('should return 503 when ADMIN_USER_ID not configured and attempting admin operation', async () => {
      // Remove ADMIN_USER_ID from environment
      delete process.env.ADMIN_USER_ID;

      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User attempting to operate on a different user's account
      const result = checkAdminAuthorization(session, 'user-456', 'erasure');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(503);

      // Verify error response body
      const body = await result!.json();
      expect(body.error).toBe('Service not configured for admin operations');

      // Verify logging occurred
      expect(mockError).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'Admin erasure attempted but ADMIN_USER_ID not configured',
          meta: expect.objectContaining({
            attemptedBy: 'user-123',
            targetUser: 'user-456',
          }),
        })
      );
    });

    it('should return 503 with custom operation name in log', () => {
      delete process.env.ADMIN_USER_ID;

      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'user-100',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      const result = checkAdminAuthorization(session, 'user-200', 'deletion');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(503);

      // Verify custom operation name appears in log
      expect(mockError).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'Admin deletion attempted but ADMIN_USER_ID not configured',
          meta: expect.objectContaining({
            attemptedBy: 'user-100',
            targetUser: 'user-200',
          }),
        })
      );
    });

    it('should handle ADMIN_USER_ID with whitespace correctly', () => {
      // Set ADMIN_USER_ID with leading/trailing whitespace
      process.env.ADMIN_USER_ID = '  admin-user-id  ';

      const session: Session = {
        user: {
          id: 'admin-user-id',
          email: 'admin@example.com',
          name: 'Admin User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Admin operating on another user's account
      const result = checkAdminAuthorization(session, 'user-789', 'erasure');

      // Should authorize (whitespace should be trimmed)
      expect(result).toBeNull();
    });
  });

  describe('authorization failures', () => {
    it('should return 403 when non-admin attempts admin operation', async () => {
      // Configure admin user
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const mockWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'regular-user-id',
          email: 'regular@example.com',
          name: 'Regular User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Regular user attempting to operate on different user's account
      const result = checkAdminAuthorization(session, 'target-user-id', 'erasure');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(403);

      // Verify error response body
      const body = await result!.json();
      expect(body.error).toBe('Forbidden');

      // Verify logging occurred
      expect(mockWarn).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'warn',
          message: 'Unauthorized erasure attempt',
          meta: expect.objectContaining({
            attemptedBy: 'regular-user-id',
            targetUser: 'target-user-id',
          }),
        })
      );
    });

    it('should log custom operation name on 403', () => {
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const mockWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'user-abc',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      const result = checkAdminAuthorization(session, 'user-xyz', 'profile update');

      expect(result).not.toBeNull();
      expect(result?.status).toBe(403);

      // Verify custom operation name appears in log
      expect(mockWarn).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'warn',
          message: 'Unauthorized profile update attempt',
          meta: expect.objectContaining({
            attemptedBy: 'user-abc',
            targetUser: 'user-xyz',
          }),
        })
      );
    });
  });

  describe('successful authorization', () => {
    it('should authorize user operating on own account', () => {
      // ADMIN_USER_ID not configured
      delete process.env.ADMIN_USER_ID;

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User operating on their own account
      const result = checkAdminAuthorization(session, 'user-123', 'erasure');

      // Should be authorized (null = success)
      expect(result).toBeNull();
    });

    it('should authorize user operating on own account even when ADMIN_USER_ID configured', () => {
      // Configure admin user (different from current user)
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User operating on their own account
      const result = checkAdminAuthorization(session, 'user-123', 'erasure');

      // Should be authorized
      expect(result).toBeNull();
    });

    it('should authorize admin operating on other user account', () => {
      // Configure admin user
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const session: Session = {
        user: {
          id: 'admin-user-id',
          email: 'admin@example.com',
          name: 'Admin User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Admin operating on different user's account
      const result = checkAdminAuthorization(session, 'user-456', 'erasure');

      // Should be authorized
      expect(result).toBeNull();
    });

    it('should authorize admin operating on own account', () => {
      // Configure admin user
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const session: Session = {
        user: {
          id: 'admin-user-id',
          email: 'admin@example.com',
          name: 'Admin User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Admin operating on their own account
      const result = checkAdminAuthorization(session, 'admin-user-id', 'erasure');

      // Should be authorized
      expect(result).toBeNull();
    });

    it('should not log anything on successful authorization', () => {
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const mockWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'admin-user-id',
          email: 'admin@example.com',
          name: 'Admin User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      checkAdminAuthorization(session, 'user-789', 'erasure');

      // No logging should occur on successful authorization
      expect(mockWarn).not.toHaveBeenCalled();
      expect(mockError).not.toHaveBeenCalled();
    });
  });

  describe('operation name parameter', () => {
    it('should use default operation name when not provided', () => {
      delete process.env.ADMIN_USER_ID;

      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Call without operation name (defaults to 'operation')
      checkAdminAuthorization(session, 'user-456');

      // Verify default operation name used in log
      expect(mockError).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'Admin operation attempted but ADMIN_USER_ID not configured',
        })
      );
    });

    it('should use custom operation name when provided', () => {
      delete process.env.ADMIN_USER_ID;

      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // Call with custom operation name
      checkAdminAuthorization(session, 'user-456', 'profile erasure');

      // Verify custom operation name used in log
      expect(mockError).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'Admin profile erasure attempted but ADMIN_USER_ID not configured',
        })
      );
    });
  });

  describe('edge cases', () => {
    it('should handle empty string ADMIN_USER_ID', () => {
      // Set to empty string (should be treated as not configured after trim)
      process.env.ADMIN_USER_ID = '   ';

      const session: Session = {
        user: {
          id: 'user-123',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User attempting to operate on different account
      const result = checkAdminAuthorization(session, 'user-456', 'erasure');

      // Should return 503 (empty string after trim = not configured)
      expect(result).not.toBeNull();
      expect(result?.status).toBe(503);
    });

    it('should handle user IDs with special characters', () => {
      process.env.ADMIN_USER_ID = 'admin-user-id-123';

      const session: Session = {
        user: {
          id: 'user-id-with-dashes-and-numbers-456',
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User operating on own account with special characters
      const result = checkAdminAuthorization(
        session,
        'user-id-with-dashes-and-numbers-456',
        'erasure'
      );

      // Should be authorized
      expect(result).toBeNull();
    });

    it('should handle very long user IDs', () => {
      const longUserId = 'user-' + 'a'.repeat(1000);
      process.env.ADMIN_USER_ID = 'admin-user-id';

      const session: Session = {
        user: {
          id: longUserId,
          email: 'user@example.com',
          name: 'Test User',
        },
        expires: new Date(Date.now() + 3600000).toISOString(),
      };

      // User operating on own account with very long ID
      const result = checkAdminAuthorization(session, longUserId, 'erasure');

      // Should be authorized
      expect(result).toBeNull();
    });
  });
});
