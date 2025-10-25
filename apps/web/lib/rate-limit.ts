import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

// Check if running in build mode or if vars are missing
const isBuildTime = process.env.NODE_ENV === 'production' && !redisUrl;

let redis: Redis;
if (isBuildTime || !redisUrl || !redisToken) {
  // Create stub for build time or missing config
  redis = {
    get: async () => null,
    set: async () => 'OK',
    del: async () => 1,
  } as unknown as Redis;
} else {
  // Create real Redis instance
  redis = new Redis({
    url: redisUrl,
    token: redisToken,
  });
}

// Create no-op rate limiter for build time
function createRateLimit(prefix: string, limit: number, windowMs: number) {
  if (isBuildTime || !redisUrl || !redisToken) {
    return {
      limit: async () => ({ success: true, limit, remaining: limit, reset: Date.now() + 60000 }),
    } as unknown as Ratelimit;
  }
  return new Ratelimit({
    redis,
    limiter: Ratelimit.slidingWindow(limit, `${windowMs} ms`),
    prefix,
    analytics: true,
  });
}

// Password endpoints: 5 requests per 10 minutes (600,000 ms)
export const passwordRateLimit = createRateLimit('ratelimit:password', 5, 600000);

// General auth endpoints: 10 requests per 1 minute (60,000 ms)
export const authRateLimit = createRateLimit('ratelimit:auth', 10, 60000);

/**
 * Extract client identifier from request headers.
 * Uses x-forwarded-for or x-real-ip headers, falls back to a default.
 */
export function getClientIdentifier(req: Request): string {
  const forwardedFor = req.headers.get('x-forwarded-for');
  const realIp = req.headers.get('x-real-ip');

  if (forwardedFor) {
    // x-forwarded-for can contain multiple IPs, use the first one
    const ips = forwardedFor.split(',').map((ip) => ip.trim());
    return ips[0] || 'unknown';
  }

  if (realIp) {
    return realIp;
  }

  // Fallback identifier (not ideal, but prevents failures)
  return 'unknown';
}
