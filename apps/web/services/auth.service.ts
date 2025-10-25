import { prisma } from '@taboot/db';
import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';

/**
 * AuthService - Handles authentication and password management operations
 *
 * Provides methods for:
 * - Checking if a user has a password
 * - Setting a new password
 * - Changing an existing password
 *
 * All methods include proper error handling and logging.
 */
export class AuthService {
  /**
   * Check if a user has a password set
   * @param userId - The ID of the user to check
   * @returns true if user has a password, false otherwise
   * @throws Error if database query fails
   */
  async hasPassword(userId: string): Promise<boolean> {
    try {
      const account = await prisma.account.findFirst({
        where: {
          userId,
          providerId: 'credential',
        },
        select: {
          password: true,
        },
      });

      return !!account?.password;
    } catch (error) {
      logger.error('Failed to check if user has password', { userId, error });
      throw new Error('Failed to verify password status');
    }
  }

  /**
   * Set a password for a user who doesn't have one
   * @param userId - The ID of the user
   * @param newPassword - The new password to set
   * @throws Error if user already has a password or if setting fails
   */
  async setPassword(userId: string, newPassword: string, headers: Headers): Promise<void> {
    try {
      // Check if user already has a password
      const existingAccount = await prisma.account.findFirst({
        where: {
          userId,
          providerId: 'credential',
        },
        select: {
          password: true,
        },
      });

      if (existingAccount?.password) {
        logger.warn('Attempted to set password for user who already has one', { userId });
        throw new Error('Password already exists. Please use change password instead.');
      }

      // Use better-auth API to set password
      await auth.api.setPassword({
        body: { newPassword },
        headers,
      });

      logger.info('Password set successfully', { userId });
    } catch (error) {
      if (error instanceof Error && error.message.includes('already exists')) {
        throw error;
      }
      logger.error('Error setting password', { userId, error });
      throw new Error('Failed to set password');
    }
  }

  /**
   * Change a user's existing password
   * @param userId - The ID of the user
   * @param currentPassword - The current password for verification
   * @param newPassword - The new password to set
   * @throws Error if current password is incorrect or if change fails
   */
  async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string,
    headers: Headers,
  ): Promise<void> {
    try {
      // Verify user has a password first
      const hasExistingPassword = await this.hasPassword(userId);
      if (!hasExistingPassword) {
        logger.warn('Attempted to change password for user without one', { userId });
        throw new Error('No password set. Please set a password first.');
      }

      // Use better-auth API to change password
      await auth.api.changePassword({
        body: { currentPassword, newPassword },
        headers,
      });

      logger.info('Password changed successfully', { userId });
    } catch (error) {
      if (error instanceof Error && error.message.includes('No password set')) {
        throw error;
      }
      if (error instanceof Error && error.message.includes('Failed to verify password status')) {
        throw error;
      }
      logger.error('Error changing password', { userId, error });
      throw new Error('Failed to change password');
    }
  }
}

// Export singleton instance
export const authService = new AuthService();
