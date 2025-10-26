/**
 * withRateLimit Higher-Order Function Tests
 *
 * These tests verify:
 * 1. Rate limiter is called with correct identifier
 * 2. Rate limit headers are added to responses
 * 3. 429 status returned when limit exceeded
 * 4. Handler is called when rate limit passes
 * 5. Fail-closed behavior on rate limit check failure
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Set NEXT_PHASE before any module imports to bypass runtime env checks
vi.hoisted(() => {
  process.env.NEXT_PHASE = 'phase-production-build';
});

import { NextResponse } from 'next/server';
import { withRateLimit } from '../with-rate-limit';
import type { Ratelimit } from '@upstash/ratelimit';

describe('withRateLimit', () => {
  let originalTrustProxy: string | undefined;

  beforeEach(() => {
    originalTrustProxy = process.env.TRUST_PROXY;
    process.env.TRUST_PROXY = 'true'; // Enable for testing

    // Mock console to avoid noise in test output
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    if (originalTrustProxy === undefined) {
      delete process.env.TRUST_PROXY;
    } else {
      process.env.TRUST_PROXY = originalTrustProxy;
    }

    // Restore all mocks including console
    vi.restoreAllMocks();
  });

  describe('successful rate limit check', () => {
    it('should call handler when rate limit passes', async () => {
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: true,
          limit: 10,
          remaining: 9,
          reset: Date.now() + 60000,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }, { status: 200 }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      const response = await wrappedHandler(req);

      // Handler should be called
      expect(mockHandler).toHaveBeenCalledWith(req);

      // Response should be from handler
      expect(response.status).toBe(200);
      const body = await response.json();
      expect(body).toEqual({ message: 'Success' });
    });

    it('should add rate limit headers to successful response', async () => {
      const resetTime = Date.now() + 60000;
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: true,
          limit: 10,
          remaining: 7,
          reset: resetTime,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      const response = await wrappedHandler(req);

      // Check rate limit headers
      expect(response.headers.get('X-RateLimit-Limit')).toBe('10');
      expect(response.headers.get('X-RateLimit-Remaining')).toBe('7');
      expect(response.headers.get('X-RateLimit-Reset')).toBe(
        new Date(resetTime).toISOString(),
      );
    });

    it('should call rate limiter with correct identifier', async () => {
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: true,
          limit: 10,
          remaining: 9,
          reset: Date.now() + 60000,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '203.0.113.45',
        },
      });

      await wrappedHandler(req);

      // Verify rate limiter was called with extracted IP
      expect(mockRatelimit.limit).toHaveBeenCalledWith('203.0.113.45');
    });
  });

  describe('rate limit exceeded', () => {
    it('should return 429 when rate limit exceeded', async () => {
      const resetTime = Date.now() + 60000;
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: false,
          limit: 5,
          remaining: 0,
          reset: resetTime,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      const response = await wrappedHandler(req);

      // Should not call handler
      expect(mockHandler).not.toHaveBeenCalled();

      // Should return 429
      expect(response.status).toBe(429);

      const body = await response.json();
      expect(body.error).toBe('Too many requests. Please try again later.');
      expect(body.retryAfter).toBe(new Date(resetTime).toISOString());
    });

    it('should add rate limit headers to 429 response', async () => {
      const resetTime = Date.now() + 600000;
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: false,
          limit: 5,
          remaining: 0,
          reset: resetTime,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn();
      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/password-reset', {
        headers: {
          'x-forwarded-for': '192.168.1.100',
        },
      });

      const response = await wrappedHandler(req);

      // Verify rate limit headers present in error response
      expect(response.headers.get('X-RateLimit-Limit')).toBe('5');
      expect(response.headers.get('X-RateLimit-Remaining')).toBe('0');
      expect(response.headers.get('X-RateLimit-Reset')).toBe(
        new Date(resetTime).toISOString(),
      );
    });

    it('should log rate limit violations', async () => {
      const mockWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const resetTime = Date.now() + 60000;
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: false,
          limit: 5,
          remaining: 0,
          reset: resetTime,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn();
      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      await wrappedHandler(req);

      // Verify logging occurred - logger wraps call in structured object
      expect(mockWarn).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'warn',
          message: 'Rate limit exceeded',
          meta: expect.objectContaining({
            identifier: '192.168.1.1',
            limit: 5,
            remaining: 0,
            path: '/api/test',
          }),
        }),
      );
    });
  });

  describe('fail-closed behavior', () => {
    it('should return 503 when rate limit check fails', async () => {
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockRejectedValue(new Error('Redis connection failed')),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      const response = await wrappedHandler(req);

      // Should not call handler (fail closed)
      expect(mockHandler).not.toHaveBeenCalled();

      // Should return 503
      expect(response.status).toBe(503);

      const body = await response.json();
      expect(body.error).toBe('Service temporarily unavailable. Please try again later.');
    });

    it('should add Retry-After header on 503 response', async () => {
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockRejectedValue(new Error('Redis connection failed')),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn();
      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      const response = await wrappedHandler(req);

      expect(response.headers.get('Retry-After')).toBe('60');
    });

    it('should log rate limit check failures', async () => {
      const mockError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const error = new Error('Redis connection failed');
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockRejectedValue(error),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn();
      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      const req = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });

      await wrappedHandler(req);

      // Verify error logging - logger wraps call in structured object
      expect(mockError).toHaveBeenCalledWith(
        expect.objectContaining({
          level: 'error',
          message: 'Rate limit check failed, failing closed (rejecting request)',
          meta: expect.objectContaining({
            identifier: '192.168.1.1',
            path: '/api/test',
            error: expect.objectContaining({
              message: 'Redis connection failed',
              name: 'Error',
            }),
          }),
        }),
      );
    });
  });

  describe('different client identifiers', () => {
    it('should track different IPs separately', async () => {
      const limitFn = vi.fn();
      const mockRatelimit: Ratelimit = {
        limit: limitFn,
      } as unknown as Ratelimit;

      limitFn.mockResolvedValue({
        success: true,
        limit: 10,
        remaining: 9,
        reset: Date.now() + 60000,
      });

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      // Request from first IP
      const req1 = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.1',
        },
      });
      await wrappedHandler(req1);

      // Request from second IP
      const req2 = new Request('http://localhost/api/test', {
        headers: {
          'x-forwarded-for': '192.168.1.2',
        },
      });
      await wrappedHandler(req2);

      // Verify different identifiers were used
      expect(limitFn).toHaveBeenNthCalledWith(1, '192.168.1.1');
      expect(limitFn).toHaveBeenNthCalledWith(2, '192.168.1.2');
    });

    it('should handle unknown identifier gracefully', async () => {
      const mockRatelimit: Ratelimit = {
        limit: vi.fn().mockResolvedValue({
          success: true,
          limit: 10,
          remaining: 9,
          reset: Date.now() + 60000,
        }),
      } as unknown as Ratelimit;

      const mockHandler = vi.fn().mockResolvedValue(
        NextResponse.json({ message: 'Success' }),
      );

      const wrappedHandler = withRateLimit(mockHandler, mockRatelimit);

      // Request without any IP information (in production with TRUST_PROXY=false)
      process.env.TRUST_PROXY = 'false';
      const req = new Request('http://localhost/api/test');

      await wrappedHandler(req);

      // Should call rate limiter with 'unknown'
      expect(mockRatelimit.limit).toHaveBeenCalledWith('unknown');

      // Handler should still be called (rate limit check passed)
      expect(mockHandler).toHaveBeenCalled();
    });
  });
});
