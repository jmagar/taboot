/**
 * Profile Service Types
 *
 * Type definitions for profile management operations.
 */

export interface ProfileUpdateResult {
  nameChanged: boolean;
  emailChanged: boolean;
}

export interface CurrentUser {
  name: string | null;
  email: string;
}

export interface ProfileServiceOptions {
  /**
   * Callback URL to redirect to after email verification.
   * Defaults to '/settings/general'
   */
  emailChangeCallbackURL?: string;
}
