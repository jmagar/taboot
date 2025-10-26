/**
 * Profile Service Tests
 *
 * Tests for profile update orchestration logic.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { updateProfile } from '../profile-service';
import type { UpdateProfileFormValues } from '@taboot/utils/types';

// Mock the auth client
vi.mock('@taboot/auth/client', () => ({
  updateUser: vi.fn(),
  changeEmail: vi.fn(),
}));

// Mock logger
vi.mock('@/lib/logger', () => ({
  logger: {
    error: vi.fn(),
  },
}));

import { updateUser, changeEmail } from '@taboot/auth/client';
import { logger } from '@/lib/logger';

describe('updateProfile', () => {
  const mockUserId = 'user-123';
  const mockCurrentUser = {
    name: 'John Doe',
    email: 'john@example.com',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('name updates', () => {
    it('should update name when changed', async () => {
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'john@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      expect(updateUser).toHaveBeenCalledWith({ name: 'Jane Doe' });
      expect(changeEmail).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });

    it('should not update name when unchanged', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      expect(updateUser).not.toHaveBeenCalled();
      expect(changeEmail).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: false,
      });
    });

    it('should throw error when name update fails', async () => {
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'john@example.com',
      };

      vi.mocked(updateUser).mockRejectedValueOnce(new Error('API error'));

      await expect(updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Failed to update name',
      );

      expect(logger.error).toHaveBeenCalledWith('Name update failed:', {
        userId: mockUserId,
        error: 'API error',
      });
    });
  });

  describe('email updates', () => {
    it('should update email when changed', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'jane@example.com',
        callbackURL: '/settings/general',
      });
      expect(updateUser).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: true,
      });
    });

    it('should not update email when unchanged', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      expect(changeEmail).not.toHaveBeenCalled();
      expect(updateUser).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: false,
      });
    });

    it('should throw error when email update fails', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      vi.mocked(changeEmail).mockRejectedValueOnce(new Error('Email service error'));

      await expect(updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Failed to change email',
      );

      expect(logger.error).toHaveBeenCalledWith('Email update failed:', {
        userId: mockUserId,
        currentEmail: 'john@example.com',
        newEmail: 'jane@example.com',
        error: 'Email service error',
      });
    });
  });

  describe('combined updates', () => {
    it('should update both name and email when both changed', async () => {
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      expect(updateUser).toHaveBeenCalledWith({ name: 'Jane Doe' });
      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'jane@example.com',
        callbackURL: '/settings/general',
      });
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: true,
      });
    });

    it('should handle partial failure when name succeeds but email fails', async () => {
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      vi.mocked(changeEmail).mockRejectedValueOnce(new Error('Email service error'));

      await expect(updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Name updated, but failed to change email',
      );

      expect(updateUser).toHaveBeenCalledWith({ name: 'Jane Doe' });
      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'jane@example.com',
        callbackURL: '/settings/general',
      });
      expect(logger.error).toHaveBeenCalledWith('Email update failed:', {
        userId: mockUserId,
        currentEmail: 'john@example.com',
        newEmail: 'jane@example.com',
        error: 'Email service error',
      });
    });
  });

  describe('edge cases', () => {
    it('should handle null name in current user', async () => {
      const currentUserWithNullName = {
        name: null,
        email: 'john@example.com',
      };

      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await updateProfile(mockUserId, currentUserWithNullName, values);

      expect(updateUser).toHaveBeenCalledWith({ name: 'John Doe' });
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });

    it('should handle email with different casing', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'JOHN@EXAMPLE.COM',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      // Email change should be attempted (different string)
      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'JOHN@EXAMPLE.COM',
        callbackURL: '/settings/general',
      });
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: true,
      });
    });

    it('should handle whitespace trimming in name', async () => {
      const values: UpdateProfileFormValues = {
        name: 'John Doe ',
        email: 'john@example.com',
      };

      const result = await updateProfile(mockUserId, mockCurrentUser, values);

      // Name change should be attempted (different string with trailing space)
      expect(updateUser).toHaveBeenCalledWith({ name: 'John Doe ' });
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });
  });
});
