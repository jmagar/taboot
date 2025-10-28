/**
 * Profile Service Module
 *
 * Core business logic for profile management operations.
 * Provides orchestration of profile updates across multiple auth endpoints.
 */

export { createProfileService, updateProfile } from './profile-service';
export type { ProfileUpdateResult, CurrentUser, ProfileServiceOptions } from './types';
