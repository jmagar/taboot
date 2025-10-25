/**
 * Rate Limit Tests
 *
 * These tests verify:
 * 1. getClientIdentifier extracts IPs correctly from headers
 * 2. IP validation works for IPv4 and IPv6
 * 3. TRUST_PROXY environment variable controls header trust
 * 4. Invalid IPs are rejected
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { getClientIdentifier } from '../rate-limit';

describe('Rate Limiting', () => {
  let originalTrustProxy: string | undefined;

  beforeEach(() => {
    // Save original TRUST_PROXY value
    originalTrustProxy = process.env.TRUST_PROXY;
  });

  afterEach(() => {
    // Restore original TRUST_PROXY value
    if (originalTrustProxy === undefined) {
      delete process.env.TRUST_PROXY;
    } else {
      process.env.TRUST_PROXY = originalTrustProxy;
    }
  });

  describe('getClientIdentifier', () => {
    describe('with TRUST_PROXY=true', () => {
      beforeEach(() => {
        process.env.TRUST_PROXY = 'true';
      });

      it('should extract first IP from x-forwarded-for header', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.1, 10.0.0.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('192.168.1.1');
      });

      it('should handle single IP in x-forwarded-for', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '203.0.113.45',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('203.0.113.45');
      });

      it('should handle IPv6 addresses in x-forwarded-for', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('2001:0db8:85a3:0000:0000:8a2e:0370:7334');
      });

      it('should handle compressed IPv6 addresses', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '2001:db8::1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('2001:db8::1');
      });

      it('should reject invalid IPv4 addresses', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '999.999.999.999',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });

      it('should reject malformed IP addresses', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': 'not-an-ip',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });

      it('should trim whitespace from forwarded IPs', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '  192.168.1.1  , 10.0.0.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('192.168.1.1');
      });
    });

    describe('with TRUST_PROXY=false (default)', () => {
      beforeEach(() => {
        process.env.TRUST_PROXY = 'false';
      });

      it('should ignore x-forwarded-for header', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.1',
          },
        });

        const identifier = getClientIdentifier(req);
        // Should fallback to 'unknown' since we don't trust proxy headers
        expect(identifier).toBe('unknown');
      });

      it('should fallback to unknown when no connection info available', () => {
        const req = new Request('http://localhost');

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });
    });

    describe('with connection IP (Next.js)', () => {
      it('should use connection IP when available', () => {
        // Mock Next.js request with connection info
        const req = new Request('http://localhost') as Request & {
          ip?: string;
        };
        req.ip = '10.0.0.5';

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('10.0.0.5');
      });

      it('should use socket.remoteAddress when available', () => {
        const req = new Request('http://localhost') as Request & {
          socket?: { remoteAddress?: string };
        };
        req.socket = { remoteAddress: '10.0.0.10' };

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('10.0.0.10');
      });

      it('should reject invalid connection IPs', () => {
        const req = new Request('http://localhost') as Request & {
          ip?: string;
        };
        req.ip = 'invalid-ip';

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });
    });

    describe('IP validation edge cases', () => {
      beforeEach(() => {
        process.env.TRUST_PROXY = 'true';
      });

      it('should accept valid IPv4 boundary values', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '0.0.0.0',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('0.0.0.0');
      });

      it('should accept valid IPv4 max values', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '255.255.255.255',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('255.255.255.255');
      });

      it('should reject IPv4 with octets > 255', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.256',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });

      it('should handle localhost addresses', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '127.0.0.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('127.0.0.1');
      });

      it('should handle private network addresses', () => {
        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '10.0.0.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('10.0.0.1');
      });
    });

    describe('security considerations', () => {
      it('should log warning when unable to determine IP', () => {
        const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

        const req = new Request('http://localhost/api/test');

        getClientIdentifier(req);

        expect(consoleWarnSpy).toHaveBeenCalledWith(
          '[RATE_LIMIT] Unable to determine client IP for rate limiting',
          expect.objectContaining({
            trustProxy: false,
            hasForwardedFor: false,
          }),
        );

        consoleWarnSpy.mockRestore();
      });

      it('should not trust x-forwarded-for by default for security', () => {
        // Default behavior (no TRUST_PROXY set)
        delete process.env.TRUST_PROXY;

        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '1.2.3.4',
          },
        });

        const identifier = getClientIdentifier(req);
        // Should fallback to unknown, not trust the header
        expect(identifier).toBe('unknown');
      });
    });
  });
});
