import { prisma } from '@taboot/db';
import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';
import { revalidateSessionCache } from '@/lib/cache-utils';

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
          password: { not: null },
        },
        select: {
          id: true,
        },
      });

      return !!account;
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
      // Call API directly - let upstream enforce uniqueness constraints
      await auth.api.setPassword({
        body: { newPassword },
        headers,
      });

      // Invalidate session cache after password change
      await revalidateSessionCache();

      logger.info('Password set successfully', { userId });
    } catch (error) {
      if (error instanceof Error && /already exists/i.test(error.message)) {
        logger.warn('Attempted to set password for user who already has one', { userId });
        throw new Error('Password already exists. Please use change password instead.');
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
      // Call API directly - let upstream enforce password existence
      await auth.api.changePassword({
        body: { currentPassword, newPassword },
        headers,
      });

      // Invalidate session cache after password change
      await revalidateSessionCache();

      logger.info('Password changed successfully', { userId });
    } catch (error) {
      if (error instanceof Error && /no password/i.test(error.message)) {
        logger.warn('Attempted to change password for user without one', { userId });
        throw new Error('No password set. Please set a password first.');
      }
      logger.error('Error changing password', { userId, error });
      throw new Error('Failed to change password');
    }
  }
}

// Export singleton instance
export const authService = new AuthService();
