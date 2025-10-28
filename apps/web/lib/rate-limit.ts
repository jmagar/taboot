import Redis from 'ioredis';
import { RateLimiterRedis, RateLimiterRes } from 'rate-limiter-flexible';
import { isIP } from 'node:net';
import { getRedisUrl } from './container-detection';

const redisUrl = getRedisUrl();

// Only allow stub during actual Next.js build phase
const isBuildTime = process.env.NEXT_PHASE === 'phase-production-build';

/**
 * Response type that mimics Upstash Ratelimit response
 */
interface RateLimitResponse {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number;
}

/**
 * Create a build-time stub for rate limiting.
 * This is only used during Next.js build phase to allow static analysis.
 * @param limit - The rate limit count
 * @param windowMs - The time window in milliseconds
 * @returns A stub rate limit function
 */
function createBuildTimeStub(
  limit: number,
  windowMs: number
): (key: string) => Promise<RateLimitResponse> {
  console.warn('[RATE_LIMIT] Using build-time stub - rate limiting DISABLED during build');
  return async () => ({
    success: true,
    limit,
    remaining: limit,
    reset: Math.floor((Date.now() + windowMs) / 1000), // Convert to seconds
  });
}

/**
 * Create a rate limiter instance.
 * At build time: returns a stub that always allows requests.
 * At runtime: returns a real rate limiter or throws if Redis not configured (fail-closed).
 *
 * @param prefix - Rate limit key prefix (e.g., 'ratelimit:password')
 * @param limit - Maximum number of requests allowed
 * @param windowMs - Time window in milliseconds
 * @returns Rate limit function
 */
function createRateLimit(
  prefix: string,
  limit: number,
  windowMs: number
): (key: string) => Promise<RateLimitResponse> {
  // Only allow stub during build time
  if (isBuildTime) {
    return createBuildTimeStub(limit, windowMs);
  }

  // Runtime: fail-closed if no Redis URL
  if (!redisUrl) {
    throw new Error(
      '[RATE_LIMIT] Rate limiting requires Redis configuration. ' +
        'Set REDIS_URL environment variable (default: redis://taboot-cache:6379). ' +
        'See .env.example for details.'
    );
  }

  // Create dedicated Redis client and limiter instance for this prefix
  let redis: Redis;
  let rateLimiter: RateLimiterRedis;

  try {
    redis = new Redis(redisUrl, {
      maxRetriesPerRequest: 3,
      enableReadyCheck: true,
      lazyConnect: false,
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    });

    // Event handler should log errors, not throw (async handler)
    redis.on('error', (err) => {
      console.error('[RATE_LIMIT] Redis connection error:', err);
    });

    rateLimiter = new RateLimiterRedis({
      storeClient: redis,
      points: limit, // Number of requests
      duration: windowMs / 1000, // Window duration in seconds
      keyPrefix: prefix,
      insuranceLimiter: undefined, // No fallback during rate limit check
    });
  } catch (error) {
    throw new Error(
      `[RATE_LIMIT] Failed to initialize rate limiter: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  // Test connection explicitly (fail-closed if unavailable)
  redis.ping().catch((err) => {
    throw new Error(`[RATE_LIMIT] Failed to connect to Redis at ${redisUrl}: ${err.message}`);
  });

  // Return async function that limits requests
  return async (key: string): Promise<RateLimitResponse> => {
    try {
      // Consume 1 point (request)
      const rateLimiterRes: RateLimiterRes = await rateLimiter.consume(key, 1);

      return {
        success: true,
        limit,
        remaining: Math.max(0, rateLimiterRes.remainingPoints),
        reset: Math.floor(Date.now() / 1000) + Math.ceil(rateLimiterRes.msBeforeNext / 1000),
      };
    } catch (error) {
      // RateLimiterRedis throws RateLimiterRes when limit exceeded
      if (error instanceof RateLimiterRes) {
        return {
          success: false,
          limit,
          remaining: Math.max(0, error.remainingPoints),
          reset: Math.floor(Date.now() / 1000) + Math.ceil(error.msBeforeNext / 1000),
        };
      }

      // Fail-closed: any other error is treated as rate limit exceeded
      console.error('[RATE_LIMIT] Rate limit check error:', error);
      throw new Error(
        `[RATE_LIMIT] Failed to check rate limit: ${error instanceof Error ? error.message : String(error)}`
      );
    }
  };
}

// Get environment for key scoping to prevent collisions across environments
const env = process.env.APP_ENV ?? process.env.NODE_ENV ?? 'unknown';

// Create rate limiters with fixed environment scope
const passwordLimiter = createRateLimit(`ratelimit:${env}:password`, 5, 600000); // 5 req/10min
const authLimiter = createRateLimit(`ratelimit:${env}:auth`, 10, 60000); // 10 req/1min

/**
 * Password endpoints: 5 requests per 10 minutes
 * @param key - Client identifier (IP address)
 * @returns Rate limit response
 */
export const passwordRateLimit = {
  limit: passwordLimiter,
};

/**
 * General auth endpoints: 10 requests per 1 minute
 * @param key - Client identifier (IP address)
 * @returns Rate limit response
 */
export const authRateLimit = {
  limit: authLimiter,
};

/**
 * Validate IP address format (IPv4 or IPv6) using Node.js built-in validation.
 * @param ip - IP address string to validate
 * @returns true if valid IPv4 or IPv6 address
 */
function isValidIp(ip: string): boolean {
  // Node.js isIP returns: 4 for IPv4, 6 for IPv6, 0 for invalid
  return isIP(ip) !== 0;
}

/**
 * Get connection IP from Next.js request object.
 * This requires Next.js to expose connection information.
 * @param req - The incoming request
 * @returns Connection IP if available, null otherwise
 */
function getConnectionIp(req: Request): string | null {
  // Next.js 13+ may expose connection info
  // Check: req.ip, req.socket?.remoteAddress, etc.
  const nextReq = req as { ip?: string; socket?: { remoteAddress?: string } };
  return nextReq.ip || nextReq.socket?.remoteAddress || null;
}

/**
 * Get client identifier for rate limiting.
 *
 * SECURITY: Only trust X-Forwarded-For if behind verified reverse proxy.
 * Set TRUST_PROXY=true in production ONLY if using Cloudflare, nginx, etc.
 *
 * @param req - The incoming request
 * @returns Client identifier (IP address)
 */
export function getClientIdentifier(req: Request): string {
  const trustProxy = process.env.TRUST_PROXY === 'true';

  // Option 1: Trust proxy headers (if configured)
  if (trustProxy) {
    const forwardedFor = req.headers.get('x-forwarded-for');
    if (forwardedFor) {
      // Take leftmost IP (original client, not proxy)
      const clientIp = forwardedFor.split(',')[0]?.trim();

      // Validate IP format (basic sanity check)
      if (clientIp && isValidIp(clientIp)) {
        return clientIp;
      }
    }
  }

  // Option 2: Use connection IP (if available from Next.js)
  const connectionIp = getConnectionIp(req);
  if (connectionIp && isValidIp(connectionIp)) {
    return connectionIp;
  }

  // Option 3: Fallback with warning
  console.warn('[RATE_LIMIT] Unable to determine client IP for rate limiting', {
    trustProxy,
    hasForwardedFor: !!req.headers.get('x-forwarded-for'),
    url: req.url,
  });

  return 'unknown';
}
