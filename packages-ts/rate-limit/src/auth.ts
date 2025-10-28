import { createRateLimiter } from './limiter';

// Create rate limiters for authentication flows
export const verifyEmailRateLimiter = createRateLimiter({
  prefix: 'verify-email',
  points: 3, // 3 requests per hour
  duration: 3600, // 1 hour in seconds
});

export const changeEmailRateLimiter = createRateLimiter({
  prefix: 'change-email',
  points: 2, // 2 requests per 24 hours
  duration: 86400, // 24 hours in seconds
});

export const resetPasswordRateLimiter = createRateLimiter({
  prefix: 'reset-password',
  points: 3, // 3 requests per hour
  duration: 3600, // 1 hour in seconds
});
