/**
 * UserService Tests
 *
 * These tests verify:
 * 1. getUserProfile retrieves user data correctly
 * 2. getUserProfile throws error when user not found
 * 3. updateUserProfile updates name and/or image
 * 4. updateUserProfile validates that data is provided
 * 5. deleteUser removes user account
 * 6. deleteUser throws error when user not found
 * 7. Proper error handling and logging
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { UserService } from '../user.service';

// Mock dependencies
vi.mock('@taboot/db', () => ({
  prisma: {
    user: {
      findUnique: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
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
import { logger } from '@/lib/logger';

describe('UserService', () => {
  let userService: UserService;

  beforeEach(() => {
    userService = new UserService();
    vi.clearAllMocks();
  });

  describe('getUserProfile', () => {
    it('should return user profile when user exists', async () => {
      const userId = 'user-123';
      const mockUser = {
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: 'https://example.com/avatar.jpg',
        createdAt: new Date('2024-01-01T00:00:00.000Z'),
        updatedAt: new Date('2024-01-02T00:00:00.000Z'),
      };

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        ...mockUser,
        emailVerified: false,
        twoFactorEnabled: false,
      });

      const result = await userService.getUserProfile(userId);

      expect(result).toEqual({
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: 'https://example.com/avatar.jpg',
        createdAt: '2024-01-01T00:00:00.000Z',
        updatedAt: '2024-01-02T00:00:00.000Z',
      });
      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { id: userId },
        select: {
          id: true,
          email: true,
          name: true,
          image: true,
          createdAt: true,
          updatedAt: true,
        },
      });
    });

    it('should throw error when user not found', async () => {
      const userId = 'nonexistent-user';
      vi.mocked(prisma.user.findUnique).mockResolvedValue(null);

      await expect(userService.getUserProfile(userId)).rejects.toThrow('User not found');
      expect(logger.warn).toHaveBeenCalledWith('User not found', { userId });
    });

    it('should throw error and log when database query fails', async () => {
      const userId = 'user-123';
      const dbError = new Error('Database connection failed');
      vi.mocked(prisma.user.findUnique).mockRejectedValue(dbError);

      await expect(userService.getUserProfile(userId)).rejects.toThrow('Failed to retrieve user profile');
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to get user profile',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });

  describe('updateUserProfile', () => {
    it('should successfully update user name', async () => {
      const userId = 'user-123';
      const updateData = { name: 'Updated Name' };
      const mockUpdatedUser = {
        id: userId,
        email: 'test@example.com',
        name: 'Updated Name',
        image: null,
        createdAt: new Date('2024-01-01T00:00:00.000Z'),
        updatedAt: new Date('2024-01-03T00:00:00.000Z'),
      };

      vi.mocked(prisma.user.update).mockResolvedValue({
        ...mockUpdatedUser,
        emailVerified: false,
        twoFactorEnabled: false,
      });

      const result = await userService.updateUserProfile(userId, updateData);

      expect(result).toEqual({
        id: userId,
        email: 'test@example.com',
        name: 'Updated Name',
        image: null,
        createdAt: '2024-01-01T00:00:00.000Z',
        updatedAt: '2024-01-03T00:00:00.000Z',
      });
      expect(prisma.user.update).toHaveBeenCalledWith({
        where: { id: userId },
        data: { name: 'Updated Name' },
        select: {
          id: true,
          email: true,
          name: true,
          image: true,
          createdAt: true,
          updatedAt: true,
        },
      });
      expect(logger.info).toHaveBeenCalledWith(
        'User profile updated',
        { userId, updatedFields: ['name'] }
      );
    });

    it('should successfully update user image', async () => {
      const userId = 'user-123';
      const updateData = { image: 'https://example.com/new-avatar.jpg' };
      const mockUpdatedUser = {
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: 'https://example.com/new-avatar.jpg',
        createdAt: new Date('2024-01-01T00:00:00.000Z'),
        updatedAt: new Date('2024-01-03T00:00:00.000Z'),
      };

      vi.mocked(prisma.user.update).mockResolvedValue({
        ...mockUpdatedUser,
        emailVerified: false,
        twoFactorEnabled: false,
      });

      const result = await userService.updateUserProfile(userId, updateData);

      expect(result.image).toBe('https://example.com/new-avatar.jpg');
      expect(prisma.user.update).toHaveBeenCalledWith({
        where: { id: userId },
        data: { image: 'https://example.com/new-avatar.jpg' },
        select: {
          id: true,
          email: true,
          name: true,
          image: true,
          createdAt: true,
          updatedAt: true,
        },
      });
    });

    it('should update both name and image', async () => {
      const userId = 'user-123';
      const updateData = {
        name: 'Updated Name',
        image: 'https://example.com/new-avatar.jpg',
      };
      const mockUpdatedUser = {
        id: userId,
        email: 'test@example.com',
        name: 'Updated Name',
        image: 'https://example.com/new-avatar.jpg',
        createdAt: new Date('2024-01-01T00:00:00.000Z'),
        updatedAt: new Date('2024-01-03T00:00:00.000Z'),
      };

      vi.mocked(prisma.user.update).mockResolvedValue({
        ...mockUpdatedUser,
        emailVerified: false,
        twoFactorEnabled: false,
      });

      await userService.updateUserProfile(userId, updateData);

      expect(prisma.user.update).toHaveBeenCalledWith({
        where: { id: userId },
        data: {
          name: 'Updated Name',
          image: 'https://example.com/new-avatar.jpg',
        },
        select: {
          id: true,
          email: true,
          name: true,
          image: true,
          createdAt: true,
          updatedAt: true,
        },
      });
      expect(logger.info).toHaveBeenCalledWith(
        'User profile updated',
        { userId, updatedFields: ['name', 'image'] }
      );
    });

    it('should throw error when no update data provided', async () => {
      const userId = 'user-123';
      const updateData = {};

      await expect(userService.updateUserProfile(userId, updateData)).rejects.toThrow(
        'No data provided for update'
      );
      expect(logger.warn).toHaveBeenCalledWith('No update data provided', { userId });
      expect(prisma.user.update).not.toHaveBeenCalled();
    });

    it('should handle database errors properly', async () => {
      const userId = 'user-123';
      const updateData = { name: 'Updated Name' };
      const dbError = new Error('Database error');

      vi.mocked(prisma.user.update).mockRejectedValue(dbError);

      await expect(userService.updateUserProfile(userId, updateData)).rejects.toThrow(
        'Failed to update user profile'
      );
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to update user profile',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });

  describe('deleteUser', () => {
    it('should successfully delete user', async () => {
      const userId = 'user-123';

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: null,
        emailVerified: false,
        twoFactorEnabled: false,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      vi.mocked(prisma.user.delete).mockResolvedValue({
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: null,
        emailVerified: false,
        twoFactorEnabled: false,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      await userService.deleteUser(userId);

      expect(prisma.user.findUnique).toHaveBeenCalledWith({
        where: { id: userId },
        select: { id: true },
      });
      expect(prisma.user.delete).toHaveBeenCalledWith({
        where: { id: userId },
      });
      expect(logger.info).toHaveBeenCalledWith('User deleted successfully', { userId });
    });

    it('should throw error when user not found', async () => {
      const userId = 'nonexistent-user';
      vi.mocked(prisma.user.findUnique).mockResolvedValue(null);

      await expect(userService.deleteUser(userId)).rejects.toThrow('User not found');
      expect(logger.warn).toHaveBeenCalledWith('Attempted to delete non-existent user', { userId });
      expect(prisma.user.delete).not.toHaveBeenCalled();
    });

    it('should handle database errors properly', async () => {
      const userId = 'user-123';
      const dbError = new Error('Database error');

      vi.mocked(prisma.user.findUnique).mockResolvedValue({
        id: userId,
        email: 'test@example.com',
        name: 'Test User',
        image: null,
        emailVerified: false,
        twoFactorEnabled: false,
        createdAt: new Date(),
        updatedAt: new Date(),
      });

      vi.mocked(prisma.user.delete).mockRejectedValue(dbError);

      await expect(userService.deleteUser(userId)).rejects.toThrow('Failed to delete user account');
      expect(logger.error).toHaveBeenCalledWith(
        'Failed to delete user',
        expect.objectContaining({ userId, error: dbError })
      );
    });
  });
});
