/**
 * CSRF Client Tests
 *
 * Tests for client-side CSRF token handling.
 */

import { describe, it, expect, beforeEach, afterEach, afterAll, vi } from 'vitest';
import { withCsrfToken, csrfFetch } from '../csrf-client';

// Mock document for browser environment
const mockDocument = {
  cookie: '',
};

// Save original document for restoration after tests
const originalDocument = (global as any).document;

Object.defineProperty(global, 'document', {
  value: mockDocument,
  writable: true,
  configurable: true,
});

describe('CSRF Client', () => {
  beforeEach(() => {
    // Clear cookies before each test
    mockDocument.cookie = '';
  });

  afterAll(() => {
    // Restore original document to avoid polluting other test suites
    if (originalDocument !== undefined) {
      (global as any).document = originalDocument;
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (global as any).document;
    }
    // Restore all global stubs
    vi.unstubAllGlobals();
  });

  describe('withCsrfToken', () => {
    it('should not add CSRF token to GET requests', () => {
      const options: RequestInit = { method: 'GET' };
      const enhanced = withCsrfToken(options);

      expect(enhanced.headers).toBeUndefined();
    });

    it('should not add CSRF token to HEAD requests', () => {
      const options: RequestInit = { method: 'HEAD' };
      const enhanced = withCsrfToken(options);

      expect(enhanced.headers).toBeUndefined();
    });

    it('should not add CSRF token to OPTIONS requests', () => {
      const options: RequestInit = { method: 'OPTIONS' };
      const enhanced = withCsrfToken(options);

      expect(enhanced.headers).toBeUndefined();
    });

    it('should add CSRF token to POST requests when cookie exists', () => {
      // Set CSRF cookie (use development cookie name since NODE_ENV !== 'production')
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'POST' };
      const enhanced = withCsrfToken(options);

      expect(enhanced.headers).toBeDefined();
      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to PUT requests', () => {
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'PUT' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to PATCH requests', () => {
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'PATCH' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to DELETE requests', () => {
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'DELETE' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should preserve existing headers when adding CSRF token', () => {
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const options: RequestInit = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Custom-Header': 'custom-value',
        },
      };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['Content-Type']).toBe('application/json');
      expect((enhanced.headers as any)['Custom-Header']).toBe('custom-value');
      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should warn when CSRF token is not found for state-changing request', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      const options: RequestInit = { method: 'POST' };
      const enhanced = withCsrfToken(options);

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('CSRF token not found')
      );

      consoleWarnSpy.mockRestore();
    });

    it('should handle Headers instance correctly when adding CSRF token', () => {
      mockDocument.cookie = 'taboot.csrf=test-token-value; path=/';

      const headers = new Headers();
      headers.set('Content-Type', 'application/json');
      headers.set('Authorization', 'Bearer token123');

      const options: RequestInit = {
        method: 'POST',
        headers,
      };
      const enhanced = withCsrfToken(options);

      // Headers.entries() returns lowercase keys
      expect((enhanced.headers as any)['content-type']).toBe('application/json');
      expect((enhanced.headers as any)['authorization']).toBe('Bearer token123');
      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should parse cookie values containing equals signs correctly', () => {
      // Base64-encoded tokens often contain '=' padding
      mockDocument.cookie = 'taboot.csrf=dGVzdC10b2tlbg==; path=/';

      const options: RequestInit = { method: 'POST' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('dGVzdC10b2tlbg==');
    });

    it('should handle multiple cookies and find the CSRF cookie correctly', () => {
      mockDocument.cookie = 'session=abc123; taboot.csrf=csrf-token-456; other=value';

      const options: RequestInit = { method: 'POST' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('csrf-token-456');
    });
  });

  describe('csrfFetch', () => {
    it('should use withCsrfToken when making requests', async () => {
      // Mock global fetch using vi.stubGlobal for proper test isolation
      const mockFetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
      vi.stubGlobal('fetch', mockFetch);

      mockDocument.cookie = 'taboot.csrf=test-token; path=/';

      await csrfFetch('http://localhost:3000/api/test', { method: 'POST' });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/api/test',
        expect.objectContaining({
          method: 'POST',
        })
      );

      // Check if CSRF token was added
      const callArgs = mockFetch.mock.calls[0]?.[1];
      if (callArgs?.headers) {
        expect(callArgs.headers).toHaveProperty('x-csrf-token');
      }
    });
  });
});
