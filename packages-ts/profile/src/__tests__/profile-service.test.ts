/**
 * Profile Service Tests
 *
 * Tests for profile update orchestration logic.
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createProfileService } from '../profile-service';
import type { UpdateProfileFormValues } from '@taboot/utils/types';
import type { Logger } from '@taboot/logger';

// Mock the auth client
vi.mock('@taboot/auth/client', () => ({
  updateUser: vi.fn(),
  changeEmail: vi.fn(),
}));

import { updateUser, changeEmail } from '@taboot/auth/client';

describe('createProfileService', () => {
  const mockLogger: Logger = {
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    debug: vi.fn(),
  };

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
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'john@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

      expect(updateUser).toHaveBeenCalledWith({ name: 'Jane Doe' });
      expect(changeEmail).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });

    it('should not update name when unchanged', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

      expect(updateUser).not.toHaveBeenCalled();
      expect(changeEmail).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: false,
      });
    });

    it('should throw error when name update fails', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'john@example.com',
      };

      const apiError = new Error('API error');
      vi.mocked(updateUser).mockRejectedValueOnce(apiError);

      await expect(service.updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Failed to update name',
      );

      expect(mockLogger.error).toHaveBeenCalledWith('Name update failed:', {
        userId: mockUserId,
        error: 'API error',
      });
      expect(changeEmail).not.toHaveBeenCalled();
    });

    it('should preserve root cause when name update fails', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'john@example.com',
      };

      const apiError = new Error('API error');
      vi.mocked(updateUser).mockRejectedValueOnce(apiError);

      try {
        await service.updateProfile(mockUserId, mockCurrentUser, values);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Failed to update name');
        expect((error as Error).cause).toBe(apiError);
      }
    });

    it('should not attempt email change if name update fails when both fields change', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      vi.mocked(updateUser).mockRejectedValueOnce(new Error('API error'));

      await expect(service.updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Failed to update name',
      );

      expect(changeEmail).not.toHaveBeenCalled();
    });
  });

  describe('email updates', () => {
    it('should update email when changed', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

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

    it('should use custom callback URL when provided', async () => {
      const service = createProfileService(mockLogger, {
        emailChangeCallbackURL: '/custom/callback',
      });
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      await service.updateProfile(mockUserId, mockCurrentUser, values);

      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'jane@example.com',
        callbackURL: '/custom/callback',
      });
    });

    it('should not update email when unchanged', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

      expect(changeEmail).not.toHaveBeenCalled();
      expect(updateUser).not.toHaveBeenCalled();
      expect(result).toEqual({
        nameChanged: false,
        emailChanged: false,
      });
    });

    it('should throw error when email update fails', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      vi.mocked(changeEmail).mockRejectedValueOnce(new Error('Email service error'));

      await expect(service.updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Failed to change email',
      );

      expect(mockLogger.error).toHaveBeenCalledWith('Email update failed:', {
        userId: mockUserId,
        currentEmail: 'j***n@example.com',
        newEmail: 'j***e@example.com',
        error: 'Email service error',
      });
    });

    it('should preserve root cause when email update fails', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'jane@example.com',
      };

      const emailError = new Error('Email service error');
      vi.mocked(changeEmail).mockRejectedValueOnce(emailError);

      try {
        await service.updateProfile(mockUserId, mockCurrentUser, values);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Failed to change email');
        expect((error as Error).cause).toBe(emailError);
      }
    });
  });

  describe('combined updates', () => {
    it('should update both name and email when both changed', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

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
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      vi.mocked(changeEmail).mockRejectedValueOnce(new Error('Email service error'));

      await expect(service.updateProfile(mockUserId, mockCurrentUser, values)).rejects.toThrow(
        'Name updated, but failed to change email',
      );

      expect(updateUser).toHaveBeenCalledWith({ name: 'Jane Doe' });
      expect(changeEmail).toHaveBeenCalledWith({
        newEmail: 'jane@example.com',
        callbackURL: '/settings/general',
      });
      expect(mockLogger.error).toHaveBeenCalledWith('Email update failed:', {
        userId: mockUserId,
        currentEmail: 'j***n@example.com',
        newEmail: 'j***e@example.com',
        error: 'Email service error',
      });
    });

    it('should preserve root cause in partial failure scenario', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'Jane Doe',
        email: 'jane@example.com',
      };

      const emailError = new Error('Email service error');
      vi.mocked(changeEmail).mockRejectedValueOnce(emailError);

      try {
        await service.updateProfile(mockUserId, mockCurrentUser, values);
        expect.fail('Should have thrown error');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Name updated, but failed to change email');
        expect((error as Error).cause).toBe(emailError);
      }
    });
  });

  describe('edge cases', () => {
    it('should handle null name in current user', async () => {
      const service = createProfileService(mockLogger);
      const currentUserWithNullName = {
        name: null,
        email: 'john@example.com',
      };

      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'john@example.com',
      };

      const result = await service.updateProfile(mockUserId, currentUserWithNullName, values);

      expect(updateUser).toHaveBeenCalledWith({ name: 'John Doe' });
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });

    it('should handle email with different casing', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe',
        email: 'JOHN@EXAMPLE.COM',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

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

    it('should treat trailing whitespace in name as a change', async () => {
      const service = createProfileService(mockLogger);
      const values: UpdateProfileFormValues = {
        name: 'John Doe ',
        email: 'john@example.com',
      };

      const result = await service.updateProfile(mockUserId, mockCurrentUser, values);

      // Name change should be attempted (different string with trailing space)
      expect(updateUser).toHaveBeenCalledWith({ name: 'John Doe ' });
      expect(result).toEqual({
        nameChanged: true,
        emailChanged: false,
      });
    });
  });
});
