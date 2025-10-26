import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

// Only allow stub during actual Next.js build phase
const isBuildTime = process.env.NEXT_PHASE === 'phase-production-build';

/**
 * Create a build-time stub for rate limiting.
 * This is only used during Next.js build phase to allow static analysis.
 * @param limit - The rate limit count
 * @param windowMs - The time window in milliseconds
 * @returns A stub Ratelimit instance
 */
function createBuildTimeStub(limit: number, windowMs: number): Ratelimit {
  console.warn('[RATE_LIMIT] Using build-time stub - rate limiting DISABLED during build');
  return {
    limit: async () => ({ success: true, limit, remaining: limit, reset: Date.now() + windowMs }),
  } as unknown as Ratelimit;
}

let redis: Redis | undefined;
if (isBuildTime) {
  // Create stub Redis for build time only
  redis = {
    get: async () => null,
    set: async () => 'OK',
    del: async () => 1,
  } as unknown as Redis;
}

/**
 * Create a rate limiter instance.
 * At build time: returns a stub that always allows requests.
 * At runtime: returns a real rate limiter or throws if Redis not configured (fail-closed).
 *
 * @param prefix - Rate limit key prefix (e.g., 'ratelimit:password')
 * @param limit - Maximum number of requests allowed
 * @param windowMs - Time window in milliseconds
 * @returns Ratelimit instance
 */
function createRateLimit(prefix: string, limit: number, windowMs: number): Ratelimit {
  // Only allow stub during build time
  if (isBuildTime) {
    return createBuildTimeStub(limit, windowMs);
  }

  // Runtime: fail-closed if Redis not configured
  if (!redisUrl || !redisToken) {
    throw new Error(
      '[RATE_LIMIT] Rate limiting requires Redis configuration. ' +
        'Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables. ' +
        'See .env.example for details.',
    );
  }

  // Lazy initialization of Redis client
  if (!redis) {
    redis = new Redis({
      url: redisUrl,
      token: redisToken,
    });
  }

  // Runtime: Redis must be configured (already validated above)
  return new Ratelimit({
    redis,
    limiter: Ratelimit.slidingWindow(limit, `${windowMs / 1000} s`),
    prefix,
    analytics: true,
  });
}

// Get environment for key scoping to prevent collisions across environments
const env = process.env.APP_ENV ?? process.env.NODE_ENV ?? 'unknown';

// Password endpoints: 5 requests per 10 minutes (600,000 ms)
export const passwordRateLimit = createRateLimit(`ratelimit:${env}:password`, 5, 600000);

// General auth endpoints: 10 requests per 1 minute (60,000 ms)
export const authRateLimit = createRateLimit(`ratelimit:${env}:auth`, 10, 60000);

/**
 * Validate IP address format (IPv4 or IPv6).
 * @param ip - IP address string to validate
 * @returns true if valid IPv4 or IPv6 address
 */
function isValidIp(ip: string): boolean {
  // IPv4 regex pattern
  const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
  // IPv6 regex pattern (simplified - matches most common formats)
  const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
  // IPv6 compressed format (with ::)
  const ipv6CompressedRegex = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;

  if (ipv4Regex.test(ip)) {
    // Validate octets are 0-255
    const octets = ip.split('.').map(Number);
    return octets.every((octet) => octet >= 0 && octet <= 255);
  }

  return ipv6Regex.test(ip) || ipv6CompressedRegex.test(ip);
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
