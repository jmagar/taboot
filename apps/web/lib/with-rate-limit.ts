import { NextResponse } from 'next/server';
import { logger } from '@/lib/logger';
import { getClientIdentifier } from '@/lib/rate-limit';

type Handler = (req: Request) => Promise<NextResponse>;

interface RateLimitResponse {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number; // Unix timestamp in seconds
}

interface RateLimiter {
  limit: (key: string) => Promise<RateLimitResponse>;
}

/**
 * Higher-order function that wraps API route handlers with rate limiting.
 *
 * Features:
 * - Returns 429 Too Many Requests when rate limit exceeded
 * - Adds rate limit headers to all responses (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset)
 * - Logs rate limit violations
 * - Fails closed: if rate limit check fails, returns 503 Service Unavailable
 *
 * Security Note: This middleware fails closed. If rate limiting cannot be verified
 * (e.g., Redis connection error), the request is rejected rather than allowed through.
 *
 * @param handler - The original route handler
 * @param ratelimit - The RateLimiter instance to use
 * @returns Wrapped handler with rate limiting
 */
export function withRateLimit(handler: Handler, ratelimit: RateLimiter): Handler {
  return async (req: Request): Promise<NextResponse> => {
    const identifier = getClientIdentifier(req);

    try {
      const { success, limit, reset, remaining } = await ratelimit.limit(identifier);

      // Build rate limit headers
      const rateLimitHeaders = {
        'X-RateLimit-Limit': limit.toString(),
        'X-RateLimit-Remaining': remaining.toString(),
        'X-RateLimit-Reset': new Date(reset * 1000).toISOString(),
      };

      if (!success) {
        logger.warn('Rate limit exceeded', {
          identifier,
          limit,
          remaining,
          reset: new Date(reset * 1000).toISOString(),
          path: new URL(req.url).pathname,
        });

        const retryAfterSeconds = Math.max(1, Math.round(reset - Math.floor(Date.now() / 1000)));
        return NextResponse.json(
          {
            error: 'Too many requests. Please try again later.',
            retryAfter: new Date(reset * 1000).toISOString(),
          },
          {
            status: 429,
            headers: {
              ...rateLimitHeaders,
              'Retry-After': String(retryAfterSeconds),
            },
          },
        );
      }

      // Rate limit passed, execute handler
      const response = await handler(req);

      // Add rate limit headers to successful response
      Object.entries(rateLimitHeaders).forEach(([key, value]) => {
        response.headers.set(key, value);
      });

      return response;
    } catch (error) {
      // Fail closed: rate limit check failed, reject the request
      logger.error('Rate limit check failed, failing closed (rejecting request)', {
        error,
        identifier,
        path: new URL(req.url).pathname,
      });

      // Return 503 Service Unavailable
      return NextResponse.json(
        {
          error: 'Service temporarily unavailable. Please try again later.',
        },
        {
          status: 503,
          headers: {
            'Retry-After': '60', // Suggest retry after 60 seconds
          },
        },
      );
    }
  };
}
