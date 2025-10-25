import { z } from 'zod';

/**
 * Zod schemas for user-related API contracts
 */

export const userProfileSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().nullable(),
  image: z.string().nullable(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export const updateUserProfileRequestSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  image: z.string().url().optional(),
});

export const updateUserProfileResponseSchema = userProfileSchema;

// Inferred types
export type UserProfile = z.infer<typeof userProfileSchema>;
export type UpdateUserProfileRequest = z.infer<typeof updateUserProfileRequestSchema>;
export type UpdateUserProfileResponse = z.infer<typeof updateUserProfileResponseSchema>;
