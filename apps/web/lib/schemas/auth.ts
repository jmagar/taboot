import { z } from 'zod';

/**
 * Zod schemas for auth-related API contracts
 * Provides runtime validation and TypeScript types
 */

// Common password validation schema
export const passwordSchema = z.string().min(8).max(100);

// Email validation schema
export const emailSchema = z.string().email();

// Password endpoints
export const hasPasswordResponseSchema = z.object({
  hasPassword: z.boolean(),
});

export const setPasswordRequestSchema = z.object({
  newPassword: passwordSchema,
});

export const setPasswordResponseSchema = z.object({
  message: z.string(),
});

export const changePasswordRequestSchema = z.object({
  currentPassword: passwordSchema,
  newPassword: passwordSchema,
});

export const changePasswordResponseSchema = z.object({
  message: z.string(),
});

// Sign-in endpoints
export const signInRequestSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  rememberMe: z.boolean().optional(),
});

export const signInResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    email: emailSchema,
    name: z.string().nullable(),
    image: z.string().nullable(),
  }),
  session: z.object({
    id: z.string(),
    expiresAt: z.string().datetime(),
  }),
});

// Sign-up endpoints
export const signUpRequestSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  name: z.string().min(1).max(100).optional(),
});

export const signUpResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    email: emailSchema,
    name: z.string().nullable(),
  }),
  message: z.string(),
});

// Forgot password endpoints
export const forgotPasswordRequestSchema = z.object({
  email: emailSchema,
});

export const forgotPasswordResponseSchema = z.object({
  message: z.string(),
});

// Reset password endpoints
export const resetPasswordRequestSchema = z.object({
  token: z.string().min(1),
  newPassword: passwordSchema,
});

export const resetPasswordResponseSchema = z.object({
  message: z.string(),
});

// Session endpoints
export const sessionResponseSchema = z.object({
  user: z.object({
    id: z.string(),
    email: emailSchema,
    name: z.string().nullable(),
    image: z.string().nullable(),
  }),
  session: z.object({
    id: z.string(),
    expiresAt: z.string().datetime(),
  }),
});

// Error responses
export const errorResponseSchema = z.object({
  error: z.string(),
});

export const validationErrorResponseSchema = z.object({
  error: z.string(),
  details: z.array(
    z.object({
      field: z.string(),
      message: z.string(),
    }),
  ).optional(),
});

// Inferred types
export type HasPasswordResponse = z.infer<typeof hasPasswordResponseSchema>;
export type SetPasswordRequest = z.infer<typeof setPasswordRequestSchema>;
export type SetPasswordResponse = z.infer<typeof setPasswordResponseSchema>;
export type ChangePasswordRequest = z.infer<typeof changePasswordRequestSchema>;
export type ChangePasswordResponse = z.infer<typeof changePasswordResponseSchema>;
export type SignInRequest = z.infer<typeof signInRequestSchema>;
export type SignInResponse = z.infer<typeof signInResponseSchema>;
export type SignUpRequest = z.infer<typeof signUpRequestSchema>;
export type SignUpResponse = z.infer<typeof signUpResponseSchema>;
export type ForgotPasswordRequest = z.infer<typeof forgotPasswordRequestSchema>;
export type ForgotPasswordResponse = z.infer<typeof forgotPasswordResponseSchema>;
export type ResetPasswordRequest = z.infer<typeof resetPasswordRequestSchema>;
export type ResetPasswordResponse = z.infer<typeof resetPasswordResponseSchema>;
export type SessionResponse = z.infer<typeof sessionResponseSchema>;
export type ErrorResponse = z.infer<typeof errorResponseSchema>;
export type ValidationErrorResponse = z.infer<typeof validationErrorResponseSchema>;
