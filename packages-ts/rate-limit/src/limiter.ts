import Redis from 'ioredis';
import { RateLimiterRedis, RateLimiterRes } from 'rate-limiter-flexible';

const redisUrl = process.env.REDIS_URL || 'redis://taboot-cache:6379';

let redisClient: Redis | undefined;
let rateLimiters: Map<string, RateLimiterRedis> = new Map();

/**
 * Create or get a Redis connection
 */
function getRedisConnection(): Redis {
  if (!redisClient) {
    redisClient = new Redis(redisUrl, {
      maxRetriesPerRequest: 3,
      enableReadyCheck: true,
      lazyConnect: false,
    });
  }
  return redisClient;
}

/**
 * Rate limit configuration
 */
interface RateLimitConfig {
  prefix: string;
  points: number;
  duration: number; // in seconds
}

/**
 * Wrapper around RateLimiterRedis with better-auth compatible API
 */
export interface RateLimiter {
  limit: (key: string) => Promise<{ success: boolean }>;
}

/**
 * Create a rate limiter instance
 */
export function createRateLimiter(config: RateLimitConfig): RateLimiter {
  const key = `${config.prefix}:${config.points}:${config.duration}`;

  // Return cached limiter if it exists
  const cached = rateLimiters.get(key);
  if (cached) {
    return {
      limit: async (identifier: string) => {
        try {
          await cached.consume(identifier, 1);
          return { success: true };
        } catch (error) {
          if (error instanceof RateLimiterRes) {
            return { success: false };
          }
          throw error;
        }
      },
    };
  }

  // Create new limiter
  const limiter = new RateLimiterRedis({
    storeClient: getRedisConnection(),
    points: config.points,
    duration: config.duration,
    keyPrefix: config.prefix,
  });

  rateLimiters.set(key, limiter);

  // Return wrapper with compatible API
  return {
    limit: async (identifier: string) => {
      try {
        await limiter.consume(identifier, 1);
        return { success: true };
      } catch (error) {
        if (error instanceof RateLimiterRes) {
          return { success: false };
        }
        throw error;
      }
    },
  };
}

/**
 * Check if a key has exceeded the rate limit
 */
export async function checkRateLimit(
  limiter: RateLimiterRedis,
  key: string,
  points: number = 1
): Promise<{
  success: boolean;
  remainingPoints: number;
  msBeforeNext: number;
}> {
  try {
    const res = await limiter.consume(key, points);
    return {
      success: true,
      remainingPoints: Math.max(0, res.remainingPoints),
      msBeforeNext: res.msBeforeNext,
    };
  } catch (error) {
    if (error instanceof RateLimiterRes) {
      return {
        success: false,
        remainingPoints: Math.max(0, error.remainingPoints),
        msBeforeNext: error.msBeforeNext,
      };
    }
    throw error;
  }
}

/**
 * Export the redis client for direct access if needed
 */
export const redis = {
  get client(): Redis {
    return getRedisConnection();
  },
};
