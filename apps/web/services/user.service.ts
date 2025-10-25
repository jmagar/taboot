import { prisma } from '@taboot/db';
import { logger } from '@/lib/logger';
import type { UserProfile } from '@/lib/schemas/user';

/**
 * UserService - Handles user profile management operations
 *
 * Provides methods for:
 * - Getting user profile
 * - Updating user profile (name, image)
 * - Deleting user account
 *
 * All methods include proper error handling and logging.
 */
export class UserService {
  /**
   * Get a user's profile by ID
   * @param userId - The ID of the user
   * @returns User profile data
   * @throws Error if user not found or database query fails
   */
  async getUserProfile(userId: string): Promise<UserProfile> {
    try {
      const user = await prisma.user.findUnique({
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

      if (!user) {
        logger.warn('User not found', { userId });
        throw new Error('User not found');
      }

      return {
        id: user.id,
        email: user.email,
        name: user.name,
        image: user.image,
        createdAt: user.createdAt.toISOString(),
        updatedAt: user.updatedAt.toISOString(),
      };
    } catch (error) {
      if (error instanceof Error && error.message === 'User not found') {
        throw error;
      }
      logger.error('Failed to get user profile', { userId, error });
      throw new Error('Failed to retrieve user profile');
    }
  }

  /**
   * Update a user's profile
   * @param userId - The ID of the user
   * @param data - The profile data to update (name and/or image)
   * @returns Updated user profile
   * @throws Error if user not found or update fails
   */
  async updateUserProfile(
    userId: string,
    data: { name?: string; image?: string },
  ): Promise<UserProfile> {
    try {
      // Ensure at least one field is being updated
      if (!data.name && !data.image) {
        logger.warn('No update data provided', { userId });
        throw new Error('No data provided for update');
      }

      const user = await prisma.user.update({
        where: { id: userId },
        data: {
          ...(data.name !== undefined && { name: data.name }),
          ...(data.image !== undefined && { image: data.image }),
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

      logger.info('User profile updated', { userId, updatedFields: Object.keys(data) });

      return {
        id: user.id,
        email: user.email,
        name: user.name,
        image: user.image,
        createdAt: user.createdAt.toISOString(),
        updatedAt: user.updatedAt.toISOString(),
      };
    } catch (error) {
      if (error instanceof Error && error.message === 'No data provided for update') {
        throw error;
      }
      logger.error('Failed to update user profile', { userId, error });
      throw new Error('Failed to update user profile');
    }
  }

  /**
   * Delete a user account
   * @param userId - The ID of the user to delete
   * @throws Error if user not found or deletion fails
   */
  async deleteUser(userId: string): Promise<void> {
    try {
      // Verify user exists first
      const user = await prisma.user.findUnique({
        where: { id: userId },
        select: { id: true },
      });

      if (!user) {
        logger.warn('Attempted to delete non-existent user', { userId });
        throw new Error('User not found');
      }

      // Delete user (cascade will handle related records)
      await prisma.user.delete({
        where: { id: userId },
      });

      logger.info('User deleted successfully', { userId });
    } catch (error) {
      if (error instanceof Error && error.message === 'User not found') {
        throw error;
      }
      logger.error('Failed to delete user', { userId, error });
      throw new Error('Failed to delete user account');
    }
  }
}

// Export singleton instance
export const userService = new UserService();
