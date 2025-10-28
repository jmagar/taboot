/**
 * Profile Service Wrapper
 *
 * Thin wrapper around @taboot/profile adapter package.
 * This file provides a convenient API for the web app while delegating
 * all business logic to the core profile service adapter.
 *
 * SOFT DELETE CONTEXT:
 * Soft delete context (user ID, IP, user-agent) is automatically set by
 * apps/web/middleware.ts for all authenticated API requests.
 * No manual context management is needed in this service.
 */

import { createProfileService } from '@taboot/profile';
import { logger } from '@/lib/logger';

// Re-export types for convenience
export type { ProfileUpdateResult, CurrentUser } from '@taboot/profile/types';

/**
 * Web app profile service instance with default logger
 */
const profileService = createProfileService(logger);

/**
 * Update user profile (name and/or email).
 *
 * This is a thin wrapper that delegates to the @taboot/profile adapter.
 * All business logic, orchestration, and error handling happens in the adapter layer.
 *
 * SOFT DELETE CONTEXT:
 * If this service were to perform database deletions, the soft delete context
 * would be automatically available through middleware (apps/web/middleware.ts).
 * Currently, this service only performs updates through better-auth APIs.
 *
 * @param userId - The user's ID (for logging and audit trail)
 * @param currentUser - Current user data for comparison
 * @param values - New profile values from the form
 * @returns Result indicating which fields were successfully updated
 * @throws Error with specific message describing the failure scenario
 */
export const updateProfile = profileService.updateProfile;
