/**
 * Profile Service
 *
 * Business logic layer for profile management operations.
 * Encapsulates orchestration of profile updates across multiple auth endpoints.
 *
 * This service handles:
 * - Name updates via updateUser API
 * - Email changes via changeEmail API (requires verification)
 * - Partial failure scenarios (e.g., name updated but email change failed)
 * - Proper error messages for all failure modes
 */

import { changeEmail, updateUser } from '@taboot/auth/client';
import { UpdateProfileFormValues } from '@taboot/utils/types';
import { logger } from '@/lib/logger';

export interface ProfileUpdateResult {
  nameChanged: boolean;
  emailChanged: boolean;
}

export interface CurrentUser {
  name: string | null;
  email: string;
}

const redactEmail = (email: string): string => {
  const [local = '', domain = ''] = email.split('@');
  if (!domain) {
    return '***';
  }
  if (local.length <= 2) {
    return `***@${domain}`;
  }
  return `${local[0]}***${local[local.length - 1]}@${domain}`;
};

/**
 * Update user profile (name and/or email).
 *
 * This function orchestrates profile updates by:
 * 1. Checking which fields have changed
 * 2. Calling updateUser API if name changed
 * 3. Calling changeEmail API if email changed
 * 4. Handling partial failures with meaningful error messages
 *
 * @param userId - The user's ID (currently unused, but kept for future use)
 * @param currentUser - Current user data for comparison
 * @param values - New profile values from the form
 * @returns Result indicating which fields were successfully updated
 * @throws Error with specific message describing the failure scenario
 *
 * Error scenarios:
 * - "Name updated, but failed to change email" - Name succeeded, email failed
 * - "Failed to update name" - Name update failed
 * - "Failed to change email" - Email update failed (name not attempted)
 */
export async function updateProfile(
  userId: string,
  currentUser: CurrentUser,
  values: UpdateProfileFormValues,
): Promise<ProfileUpdateResult> {
  const nameChanged = values.name !== currentUser.name;
  const emailChanged = values.email !== currentUser.email;

  let nameUpdateSuccess = false;
  let emailUpdateSuccess = false;

  // Update name first (faster, no verification required)
  if (nameChanged) {
    try {
      await updateUser({
        name: values.name,
      });
      nameUpdateSuccess = true;
    } catch (error) {
      logger.error('Name update failed:', {
        userId,
        error: error instanceof Error ? error.message : String(error),
      });
      throw new Error('Failed to update name');
    }
  }

  // Update email second (requires verification flow)
  if (emailChanged) {
    try {
      await changeEmail({
        newEmail: values.email,
        callbackURL: '/settings/general',
      });
      emailUpdateSuccess = true;
    } catch (error) {
      logger.error('Email update failed:', {
        userId,
        currentEmail: redactEmail(currentUser.email),
        newEmail: redactEmail(values.email),
        error: error instanceof Error ? error.message : String(error),
      });

      // Partial failure: name succeeded but email failed
      if (nameUpdateSuccess) {
        throw new Error('Name updated, but failed to change email');
      }

      throw new Error('Failed to change email');
    }
  }

  return {
    nameChanged: nameUpdateSuccess,
    emailChanged: emailUpdateSuccess,
  };
}
