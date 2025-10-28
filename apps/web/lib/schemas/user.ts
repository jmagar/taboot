import { z } from 'zod';

/**
 * Zod schemas for user-related API contracts
 */

export const userProfileSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  name: z.string().nullable(),
  image: z.string().nullable(),
  createdAt: z.iso.datetime(),
  updatedAt: z.iso.datetime(),
});

export const updateUserProfileRequestSchema = z
  .object({
    name: z.string().trim().min(1).max(100).optional(),
    image: z.string().url().refine(
      (url) => url.startsWith('http://') || url.startsWith('https://'),
      { message: 'Image URL must use http:// or https:// scheme' }
    ).optional(),
  })
  .refine(
    (data) => data.name !== undefined || data.image !== undefined,
    { message: 'At least one of name or image must be provided' }
  );

export const updateUserProfileResponseSchema = userProfileSchema;

// Inferred types
export type UserProfile = z.infer<typeof userProfileSchema>;
export type UpdateUserProfileRequest = z.infer<typeof updateUserProfileRequestSchema>;
export type UpdateUserProfileResponse = z.infer<typeof updateUserProfileResponseSchema>;
