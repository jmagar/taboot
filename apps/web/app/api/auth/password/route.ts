/**
 * Password Management API
 *
 * Security Features:
 * - CSRF Protection: All state-changing requests protected by middleware (origin/referer + double-submit token)
 * - Rate Limiting: 5 requests per 10 minutes per IP
 * - Authentication: Requires valid session
 * - Input Validation: Zod schemas with strict password requirements
 */

import { auth } from '@taboot/auth';
import { logger } from '@/lib/logger';
import { passwordRateLimit } from '@/lib/rate-limit';
import { withRateLimit } from '@/lib/with-rate-limit';
import { revalidateSessionCache } from '@/lib/cache-utils';
import {
  hasPasswordResponseSchema,
  setPasswordRequestSchema,
  setPasswordResponseSchema,
  errorResponseSchema,
  type HasPasswordResponse,
  type SetPasswordRequest,
  type SetPasswordResponse,
} from '@/lib/schemas/auth';
import { authService } from '@/services/auth.service';
import { NextResponse } from 'next/server';
import { ZodError } from 'zod';

async function handleGET(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session?.user) {
      const error = errorResponseSchema.parse({ error: 'Unauthorized' });
      return NextResponse.json(error, { status: 401 });
    }

    // Use AuthService to check if user has a password
    const hasPassword = await authService.hasPassword(session.user.id);

    // Validate response with schema
    const response: HasPasswordResponse = hasPasswordResponseSchema.parse({ hasPassword });

    return NextResponse.json(response, {
      headers: {
        // Private cache (user-specific), max-age 5 minutes, stale-while-revalidate 10 minutes
        'Cache-Control': 'private, max-age=300, stale-while-revalidate=600',
      },
    });
  } catch (error) {
    if (error instanceof ZodError) {
      logger.error('Response validation error', { error: error.issues });
      const errorResponse = errorResponseSchema.parse({
        error: 'Internal validation error',
      });
      return NextResponse.json(errorResponse, { status: 500 });
    }

    logger.error('Error checking password status', { error });
    const errorResponse = errorResponseSchema.parse({ error: 'Internal server error' });
    return NextResponse.json(errorResponse, { status: 500 });
  }
}

async function handlePOST(req: Request) {
  try {
    const session = await auth.api.getSession({ headers: req.headers });
    if (!session?.user) {
      const error = errorResponseSchema.parse({ error: 'Unauthorized' });
      return NextResponse.json(error, { status: 401 });
    }

    // Parse and validate request body
    let requestData: SetPasswordRequest;
    try {
      const body = await req.json();
      requestData = setPasswordRequestSchema.parse(body);
    } catch (parseError) {
      if (parseError instanceof ZodError) {
        logger.warn('Invalid password request payload', { errors: parseError.issues });
        const errorResponse = errorResponseSchema.parse({
          error: parseError.issues[0]?.message || 'Invalid request body',
        });
        return NextResponse.json(errorResponse, { status: 400 });
      }
      logger.warn('Invalid password request payload', { error: parseError });
      const errorResponse = errorResponseSchema.parse({ error: 'Invalid request body' });
      return NextResponse.json(errorResponse, { status: 400 });
    }

    // Use AuthService to set password (includes validation for existing password)
    try {
      await authService.setPassword(session.user.id, requestData.newPassword, req.headers);
    } catch (serviceError) {
      if (serviceError instanceof Error && serviceError.message.includes('already exists')) {
        const errorResponse = errorResponseSchema.parse({
          error: serviceError.message,
        });
        return NextResponse.json(errorResponse, { status: 400 });
      }
      throw serviceError;
    }

    // Invalidate session cache after password change
    await revalidateSessionCache();

    // Validate response with schema
    const response: SetPasswordResponse = setPasswordResponseSchema.parse({
      message: 'Password set successfully',
    });

    return NextResponse.json(response);
  } catch (error) {
    if (error instanceof ZodError) {
      logger.error('Response validation error', { error: error.issues });
      const errorResponse = errorResponseSchema.parse({
        error: 'Internal validation error',
      });
      return NextResponse.json(errorResponse, { status: 500 });
    }

    logger.error('Error setting password', { error });
    const errorResponse = errorResponseSchema.parse({ error: 'Internal server error' });
    return NextResponse.json(errorResponse, { status: 500 });
  }
}

// Export rate-limited handlers
export const GET = withRateLimit(handleGET, passwordRateLimit);
export const POST = withRateLimit(handlePOST, passwordRateLimit);
