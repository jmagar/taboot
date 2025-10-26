/**
 * CSRF Protection Tests
 *
 * Tests for CSRF middleware, token generation, and validation.
 */

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest';
import { NextRequest } from 'next/server';
import { getCsrfToken, csrfMiddleware, withCsrf } from '../csrf';

describe('CSRF Protection', () => {
  beforeAll(() => {
    // Mock crypto API for Node.js environment
    // Note: In Node 18+, crypto.subtle exists but we need to ensure it works
    vi.stubGlobal('crypto', {
      getRandomValues: (array: Uint8Array) => {
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.floor(Math.random() * 256);
        }
        return array;
      },
      subtle: {
        importKey: vi.fn().mockResolvedValue('mock-key'),
        sign: vi.fn().mockResolvedValue(new ArrayBuffer(32)),
        verify: vi.fn().mockResolvedValue(false), // Default to invalid signature
      },
    });
  });

  afterAll(() => {
    // Restore all global stubs to prevent leakage to other test suites
    vi.unstubAllGlobals();
  });
  describe('getCsrfToken', () => {
    it('should generate a new CSRF token', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'GET',
      });

      const token = await getCsrfToken(request);

      expect(token).toBeTruthy();
      expect(typeof token).toBe('string');
      expect(token).toContain('.'); // Should contain signature separator
    });

    it('should return existing valid token from cookie', async () => {
      // Mock verify to return true so the existing token is accepted
      (crypto.subtle.verify as unknown as vi.Mock).mockResolvedValueOnce(true);
      const existingToken = 'test-token.test-signature';
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'GET',
        headers: {
          cookie: `__Host-taboot.csrf=${existingToken}`,
        },
      });

      const token = await getCsrfToken(request);

      expect(token).toBe(existingToken);
    });
  });

  describe('csrfMiddleware', () => {
    it('should allow GET requests and set CSRF token cookie', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'GET',
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(200);

      // Check if CSRF cookie was set (use development cookie name)
      const cookies = response.cookies.getAll();
      const csrfCookie = cookies.find((c) => c.name === 'taboot.csrf');

      expect(csrfCookie).toBeTruthy();
      expect(csrfCookie?.httpOnly).toBe(false); // Must be false for double-submit pattern
      expect(csrfCookie?.sameSite).toBe('lax');
    });

    it('should allow HEAD requests', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'HEAD',
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(200);
    });

    it('should allow OPTIONS requests', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'OPTIONS',
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(200);
    });

    it('should reject POST request without origin/referer', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
        },
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(403);
      const body = await response.json();
      expect(body.error).toContain('origin');
    });

    it('should reject POST request with mismatched origin', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
          origin: 'http://evil.com',
        },
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(403);
      const body = await response.json();
      expect(body.error).toContain('origin');
    });

    it('should reject POST request without CSRF token', async () => {
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
          origin: 'http://localhost:3000',
        },
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(403);
      const body = await response.json();
      expect(body.error).toContain('token');
    });

    it('should accept POST request with valid origin and CSRF token', async () => {
      // Mock verify to return true so token validation passes
      (crypto.subtle.verify as unknown as vi.Mock).mockResolvedValueOnce(true);
      const token = 'test-token.test-signature';
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
          origin: 'http://localhost:3000',
          'x-csrf-token': token,
          cookie: `__Host-taboot.csrf=${token}`,
        },
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(200);
    });

    it('should validate referer header when origin is missing', async () => {
      // Mock verify to return true so token validation passes
      (crypto.subtle.verify as unknown as vi.Mock).mockResolvedValueOnce(true);
      const token = 'test-token.test-signature';
      const request = new NextRequest('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
          referer: 'http://localhost:3000/page',
          'x-csrf-token': token,
          cookie: `__Host-taboot.csrf=${token}`,
        },
      });

      const response = await csrfMiddleware(request);

      expect(response.status).toBe(200);
    });
  });

  describe('withCsrf wrapper', () => {
    const mockHandler = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    beforeEach(() => {
      mockHandler.mockClear();
    });

    it('should allow GET requests without CSRF check', async () => {
      const handler = withCsrf(mockHandler);
      const request = new Request('http://localhost:3000/api/test', {
        method: 'GET',
      });

      const response = await handler(request);

      expect(response.status).toBe(200);
      expect(mockHandler).toHaveBeenCalledWith(request);
    });

    it('should reject POST without origin', async () => {
      const handler = withCsrf(mockHandler);
      const request = new Request('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
        },
      });

      const response = await handler(request);

      expect(response.status).toBe(403);
      expect(mockHandler).not.toHaveBeenCalled();
    });

    it('should reject POST with invalid CSRF token', async () => {
      const handler = withCsrf(mockHandler);
      const request = new Request('http://localhost:3000/api/test', {
        method: 'POST',
        headers: {
          host: 'localhost:3000',
          origin: 'http://localhost:3000',
          'x-csrf-token': 'invalid-token',
        },
      });

      const response = await handler(request);

      expect(response.status).toBe(403);
      expect(mockHandler).not.toHaveBeenCalled();
    });
  });
});
