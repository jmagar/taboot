/**
 * AuthService Tests
 *
 * These tests verify:
 * 1. hasPassword correctly checks for user passwords
 * 2. setPassword creates passwords for users without one
 * 3. setPassword throws error if password already exists
 * 4. changePassword updates existing passwords
 * 5. changePassword throws error if no password exists
 * 6. Proper error handling and logging
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AuthService } from '../auth.service';

// Mock dependencies
vi.mock('@taboot/db', () => ({
  prisma: {
    account: {
      findFirst: vi.fn(),
      findUnique: vi.fn(),
      update: vi.fn(),
    },
  },
}));

vi.mock('@taboot/auth', () => ({
  auth: {
    api: {
      setPassword: vi.fn(),
      changePassword: vi.fn(),
      getSession: vi.fn(),
    },
  },
}));

vi.mock('@/lib/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Import mocked modules
import { prisma } from '@taboot/db';
import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';

describe('AuthService', () => {
  let authService: AuthService;

  beforeEach(() => {
    authService = new AuthService();
    vi.clearAllMocks();
  });

  describe('hasPassword', () => {
    it('should return true when user has a password', async () => {
      const userId = 'user-123';
      vi.mocked(prisma.account.findFirst).mockResolvedValue({
        id: 'account-1',
        userId,
        providerId: 'credential',
        password: 'hashed-password',
        accountId: 'acc-1',
        accessToken: null,
        refreshToken: null,
        idToken: null,
        accessTokenExpiresAt: null,
        refreshTokenExpiresAt: null,
        scope: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      const result = await authService.hasPassword(userId);

      expect(result).toBe(true);
      expect(prisma.account.findFirst).toHaveBeenCalledWith({
        where: {
          userId,
          providerId: 'credential',
        },
        select: {
          password: true,
        },
      });
    });

    it('should return false when user has no password', async () => {
      const userId = 'user-123';
      vi.mocked(prisma.account.findFirst).mockResolvedValue({
        id: 'account-1',
        userId,
        providerId: 'credential',
        password: null,
        accountId: 'acc-1',
        accessToken: null,
        refreshToken: null,
        idToken: null,
        accessTokenExpiresAt: null,
        refreshTokenExpiresAt: null,
        scope: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      const result = await authService.hasPassword(userId);

      expect(result).toBe(false);
    });

    it('should return false when no credential account exists', async () => {
      const userId = 'user-123';
      vi.mocked(prisma.account.findFirst).mockResolvedValue(null);

      const result = await authService.hasPassword(userId);

      expect(result).toBe(false);
    });

    it('should throw error and log when database query fails', async () => {
      const userId = 'user-123';
      const dbError = new Error('Database connection failed');
      vi.mocked(prisma.account.findFirst).mockRejectedValue(dbError);

      await expect(authService.hasPassword(userId)).rejects.toThrow('Failed to verify password status');
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to check if user has password',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });

  describe('setPassword', () => {
    it('should successfully set password when user has none', async () => {
      const userId = 'user-123';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      // Mock: no existing password
      vi.mocked(prisma.account.findFirst).mockResolvedValue(null);

      // Mock: successful password set (better-auth returns void on success)
      vi.mocked(auth.api.setPassword).mockResolvedValue(undefined);

      await authService.setPassword(userId, newPassword, headers);

      expect(prisma.account.findFirst).toHaveBeenCalledWith({
        where: { userId, providerId: 'credential' },
        select: { password: true },
      });
      expect(auth.api.setPassword).toHaveBeenCalledWith({
        body: { newPassword },
        headers,
      });
      expect(logger.info).toHaveBeenCalledWith('Password set successfully', { userId });
    });

    it('should throw error when user already has a password', async () => {
      const userId = 'user-123';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      // Mock: existing password
      vi.mocked(prisma.account.findFirst).mockResolvedValue({
        id: 'account-1',
        userId,
        providerId: 'credential',
        password: 'existing-hashed-password',
        accountId: 'acc-1',
        accessToken: null,
        refreshToken: null,
        idToken: null,
        accessTokenExpiresAt: null,
        refreshTokenExpiresAt: null,
        scope: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      await expect(authService.setPassword(userId, newPassword, headers)).rejects.toThrow(
        'Password already exists. Please use change password instead.'
      );
      expect(logger.warn).toHaveBeenCalledWith(
        'Attempted to set password for user who already has one',
        { userId }
      );
      expect(auth.api.setPassword).not.toHaveBeenCalled();
    });

    it('should throw error when better-auth setPassword fails', async () => {
      const userId = 'user-123';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      vi.mocked(prisma.account.findFirst).mockResolvedValue(null);
      // Mock: auth API throws error
      vi.mocked(auth.api.setPassword).mockRejectedValue(new Error('Auth API error'));

      await expect(authService.setPassword(userId, newPassword, headers)).rejects.toThrow(
        'Failed to set password'
      );
      expect(logger.error).toHaveBeenCalledWith(
        'Error setting password',
        expect.objectContaining({ userId })
      );
    });

    it('should handle database errors properly', async () => {
      const userId = 'user-123';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();
      const dbError = new Error('Database error');

      vi.mocked(prisma.account.findFirst).mockRejectedValue(dbError);

      await expect(authService.setPassword(userId, newPassword, headers)).rejects.toThrow(
        'Failed to set password'
      );
      expect(logger.error).toHaveBeenCalledWith(
        'Error setting password',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });

  describe('changePassword', () => {
    it('should successfully change password when user has existing password', async () => {
      const userId = 'user-123';
      const currentPassword = 'oldPassword123!';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      // Mock: user has existing password
      vi.mocked(prisma.account.findFirst).mockResolvedValue({
        id: 'account-1',
        userId,
        providerId: 'credential',
        password: 'hashed-password',
        accountId: 'acc-1',
        accessToken: null,
        refreshToken: null,
        idToken: null,
        accessTokenExpiresAt: null,
        refreshTokenExpiresAt: null,
        scope: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      // Mock: successful password change (better-auth returns void on success)
      vi.mocked(auth.api.changePassword).mockResolvedValue(undefined);

      await authService.changePassword(userId, currentPassword, newPassword, headers);

      expect(auth.api.changePassword).toHaveBeenCalledWith({
        body: { currentPassword, newPassword },
        headers,
      });
      expect(logger.info).toHaveBeenCalledWith('Password changed successfully', { userId });
    });

    it('should throw error when user has no password', async () => {
      const userId = 'user-123';
      const currentPassword = 'oldPassword123!';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      // Mock: no existing password
      vi.mocked(prisma.account.findFirst).mockResolvedValue(null);

      await expect(authService.changePassword(userId, currentPassword, newPassword, headers)).rejects.toThrow(
        'No password set. Please set a password first.'
      );
      expect(logger.warn).toHaveBeenCalledWith(
        'Attempted to change password for user without one',
        { userId }
      );
      expect(auth.api.changePassword).not.toHaveBeenCalled();
    });

    it('should throw error when better-auth changePassword fails', async () => {
      const userId = 'user-123';
      const currentPassword = 'oldPassword123!';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();

      vi.mocked(prisma.account.findFirst).mockResolvedValue({
        id: 'account-1',
        userId,
        providerId: 'credential',
        password: 'hashed-password',
        accountId: 'acc-1',
        accessToken: null,
        refreshToken: null,
        idToken: null,
        accessTokenExpiresAt: null,
        refreshTokenExpiresAt: null,
        scope: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      // Mock: auth API throws error
      vi.mocked(auth.api.changePassword).mockRejectedValue(new Error('Auth API error'));

      await expect(authService.changePassword(userId, currentPassword, newPassword, headers)).rejects.toThrow(
        'Failed to change password'
      );
      expect(logger.error).toHaveBeenCalledWith(
        'Error changing password',
        expect.objectContaining({ userId })
      );
    });

    it('should handle database errors properly', async () => {
      const userId = 'user-123';
      const currentPassword = 'oldPassword123!';
      const newPassword = 'newSecurePassword123!';
      const headers = new Headers();
      const dbError = new Error('Database error');

      vi.mocked(prisma.account.findFirst).mockRejectedValue(dbError);

      // The error will be thrown from hasPassword method, which gets re-thrown
      await expect(authService.changePassword(userId, currentPassword, newPassword, headers)).rejects.toThrow(
        'Failed to verify password status'
      );
      // The error should be logged by hasPassword, not by changePassword
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to check if user has password',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });
});
