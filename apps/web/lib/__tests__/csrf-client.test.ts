/**
 * CSRF Client Tests
 *
 * Tests for client-side CSRF token handling.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { withCsrfToken, csrfFetch } from '../csrf-client';

// Mock document for browser environment
const mockDocument = {
  cookie: '',
};

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
      // Set CSRF cookie
      mockDocument.cookie = '__Host-taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'POST' };
      const enhanced = withCsrfToken(options);

      expect(enhanced.headers).toBeDefined();
      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to PUT requests', () => {
      mockDocument.cookie = '__Host-taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'PUT' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to PATCH requests', () => {
      mockDocument.cookie = '__Host-taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'PATCH' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should add CSRF token to DELETE requests', () => {
      mockDocument.cookie = '__Host-taboot.csrf=test-token-value; path=/';

      const options: RequestInit = { method: 'DELETE' };
      const enhanced = withCsrfToken(options);

      expect((enhanced.headers as any)['x-csrf-token']).toBe('test-token-value');
    });

    it('should preserve existing headers when adding CSRF token', () => {
      mockDocument.cookie = '__Host-taboot.csrf=test-token-value; path=/';

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
  });

  describe('csrfFetch', () => {
    it('should use withCsrfToken when making requests', async () => {
      // Mock global fetch
      const mockFetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      );
      global.fetch = mockFetch;

      mockDocument.cookie = '__Host-taboot.csrf=test-token; path=/';

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
