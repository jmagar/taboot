import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('rate-limit', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset modules to ensure clean state
    vi.resetModules();
    // Create a copy of the original env
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    // Restore original env
    process.env = originalEnv;
    vi.clearAllMocks();
  });

  describe('build-time behavior', () => {
    it('should allow stub when NEXT_PHASE is phase-production-build', async () => {
      // Set build-time environment
      process.env.NEXT_PHASE = 'phase-production-build';
      delete process.env.UPSTASH_REDIS_REST_URL;
      delete process.env.UPSTASH_REDIS_REST_TOKEN;

      // Spy on console.warn
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      // Import module - should not throw
      const { passwordRateLimit, authRateLimit } = await import('./rate-limit');

      // Verify warning was logged
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Using build-time stub'),
      );

      // Verify stubs return success
      const passwordResult = await passwordRateLimit.limit('test-id');
      expect(passwordResult.success).toBe(true);

      const authResult = await authRateLimit.limit('test-id');
      expect(authResult.success).toBe(true);

      warnSpy.mockRestore();
    });

    it('should allow stub during build even if Redis vars are set', async () => {
      // Set build-time environment with Redis vars
      process.env.NEXT_PHASE = 'phase-production-build';
      process.env.UPSTASH_REDIS_REST_URL = 'https://test.upstash.io';
      process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';

      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      // Import module - should use stub, not real Redis
      const { passwordRateLimit } = await import('./rate-limit');

      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Using build-time stub'),
      );

      const result = await passwordRateLimit.limit('test-id');
      expect(result.success).toBe(true);

      warnSpy.mockRestore();
    });
  });

  describe('runtime behavior - fail closed', () => {
    it('should throw error when Redis URL is missing at runtime', async () => {
      // Ensure we are NOT in build time
      delete process.env.NEXT_PHASE;
      // Note: NODE_ENV is read-only in some environments, so we don't set it

      // Missing Redis URL
      delete process.env.UPSTASH_REDIS_REST_URL;
      process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';

      // Import should throw
      await expect(async () => {
        await import('./rate-limit');
      }).rejects.toThrow(/Rate limiting requires Redis configuration/);
    });

    it('should throw error when Redis token is missing at runtime', async () => {
      // Ensure we are NOT in build time
      delete process.env.NEXT_PHASE;

      // Missing Redis token
      process.env.UPSTASH_REDIS_REST_URL = 'https://test.upstash.io';
      delete process.env.UPSTASH_REDIS_REST_TOKEN;

      // Import should throw
      await expect(async () => {
        await import('./rate-limit');
      }).rejects.toThrow(/Rate limiting requires Redis configuration/);
    });

    it('should throw error when both Redis URL and token are missing at runtime', async () => {
      // Ensure we are NOT in build time
      delete process.env.NEXT_PHASE;

      // Missing both
      delete process.env.UPSTASH_REDIS_REST_URL;
      delete process.env.UPSTASH_REDIS_REST_TOKEN;

      // Import should throw
      await expect(async () => {
        await import('./rate-limit');
      }).rejects.toThrow(/Rate limiting requires Redis configuration/);
    });

    it('should create real Redis instance when credentials are provided at runtime', async () => {
      // Ensure we are NOT in build time
      delete process.env.NEXT_PHASE;

      // Set valid Redis credentials
      process.env.UPSTASH_REDIS_REST_URL = 'https://test.upstash.io';
      process.env.UPSTASH_REDIS_REST_TOKEN = 'test-token';

      // Import should not throw
      const module = await import('./rate-limit');

      // Verify exports exist
      expect(module.passwordRateLimit).toBeDefined();
      expect(module.authRateLimit).toBeDefined();
      expect(module.getClientIdentifier).toBeDefined();
    });
  });

  describe('getClientIdentifier', () => {
    describe('TRUST_PROXY=false (default - secure)', () => {
      it('should ignore x-forwarded-for header when TRUST_PROXY is false', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'false';

        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.1, 10.0.0.1',
          },
        });

        // Should fall back to 'unknown' since we can't get connection IP
        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });

      it('should ignore x-forwarded-for header when TRUST_PROXY is not set', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        delete process.env.TRUST_PROXY;

        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });

      it('should reject spoofed IP addresses when TRUST_PROXY is false', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'false';

        const { getClientIdentifier } = await import('./rate-limit');

        const spoofedIps = [
          '1.2.3.4',
          '192.168.1.100',
          '10.0.0.1',
          '8.8.8.8',
          '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
        ];

        for (const spoofedIp of spoofedIps) {
          const req = new Request('http://localhost', {
            headers: {
              'x-forwarded-for': spoofedIp,
            },
          });

          const identifier = getClientIdentifier(req);
          // Should NOT use the spoofed IP
          expect(identifier).not.toBe(spoofedIp);
          expect(identifier).toBe('unknown');
        }
      });
    });

    describe('TRUST_PROXY=true (behind proxy)', () => {
      it('should trust x-forwarded-for header when TRUST_PROXY is true', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '192.168.1.1, 10.0.0.1',
          },
        });

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('192.168.1.1');
      });

      it('should extract leftmost IP from x-forwarded-for chain', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost', {
          headers: {
            'x-forwarded-for': '203.0.113.1, 198.51.100.1, 192.0.2.1',
          },
        });

        // Should take leftmost IP (original client)
        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('203.0.113.1');
      });

      it('should validate IP format even when TRUST_PROXY is true', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const { getClientIdentifier } = await import('./rate-limit');

        const invalidIps = [
          'invalid-ip',
          '999.999.999.999',
          '192.168.1',
          '192.168.1.1.1',
          'not-an-ip',
          '<script>alert("xss")</script>',
        ];

        for (const invalidIp of invalidIps) {
          const req = new Request('http://localhost', {
            headers: {
              'x-forwarded-for': invalidIp,
            },
          });

          const identifier = getClientIdentifier(req);
          // Should reject invalid IP and fall back to 'unknown'
          expect(identifier).toBe('unknown');
        }

        warnSpy.mockRestore();
      });

      it('should accept valid IPv4 addresses', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const { getClientIdentifier } = await import('./rate-limit');

        const validIpv4s = [
          '192.168.1.1',
          '10.0.0.1',
          '8.8.8.8',
          '203.0.113.45',
          '0.0.0.0',
          '255.255.255.255',
        ];

        for (const validIp of validIpv4s) {
          const req = new Request('http://localhost', {
            headers: {
              'x-forwarded-for': validIp,
            },
          });

          const identifier = getClientIdentifier(req);
          expect(identifier).toBe(validIp);
        }
      });

      it('should accept valid IPv6 addresses', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const { getClientIdentifier } = await import('./rate-limit');

        const validIpv6s = [
          '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
          '2001:db8::8a2e:370:7334',
          'fe80::1',
          '::1',
        ];

        for (const validIp of validIpv6s) {
          const req = new Request('http://localhost', {
            headers: {
              'x-forwarded-for': validIp,
            },
          });

          const identifier = getClientIdentifier(req);
          expect(identifier).toBe(validIp);
        }
      });
    });

    describe('IP validation edge cases', () => {
      it('should reject IPv4 with octets > 255', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'true';

        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const { getClientIdentifier } = await import('./rate-limit');

        const invalidIps = ['256.1.1.1', '192.256.1.1', '192.168.1.256', '999.999.999.999'];

        for (const invalidIp of invalidIps) {
          const req = new Request('http://localhost', {
            headers: {
              'x-forwarded-for': invalidIp,
            },
          });

          const identifier = getClientIdentifier(req);
          expect(identifier).toBe('unknown');
        }

        warnSpy.mockRestore();
      });

      it('should log warning when IP cannot be determined', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        process.env.TRUST_PROXY = 'false';

        const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost');

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');

        // Should log warning about missing IP
        expect(warnSpy).toHaveBeenCalledWith(
          '[RATE_LIMIT] Unable to determine client IP for rate limiting',
          expect.objectContaining({
            trustProxy: false,
            hasForwardedFor: false,
          }),
        );

        warnSpy.mockRestore();
      });
    });

    describe('backward compatibility', () => {
      it('should return "unknown" when no headers are present', async () => {
        process.env.NEXT_PHASE = 'phase-production-build';
        delete process.env.TRUST_PROXY;

        const { getClientIdentifier } = await import('./rate-limit');

        const req = new Request('http://localhost');

        const identifier = getClientIdentifier(req);
        expect(identifier).toBe('unknown');
      });
    });
  });

  describe('security: no fail-open at runtime', () => {
    it('should never return stub instance at runtime regardless of env vars', async () => {
      vi.resetModules();
      process.env = { ...originalEnv };

      // Ensure NOT in build time
      delete process.env.NEXT_PHASE;

      // Missing Redis credentials
      delete process.env.UPSTASH_REDIS_REST_URL;
      delete process.env.UPSTASH_REDIS_REST_TOKEN;

      // Should throw, not return stub
      await expect(async () => {
        await import('./rate-limit');
      }).rejects.toThrow(/Rate limiting requires Redis configuration/);
    });

    it('should only allow stub when NEXT_PHASE is exactly "phase-production-build"', async () => {
      const invalidPhases = [
        'phase-development',
        'phase-production-server',
        'production-build', // missing "phase-" prefix
        'build',
        undefined,
        null,
        '',
      ];

      for (const phase of invalidPhases) {
        vi.resetModules();
        process.env = { ...originalEnv };

        if (phase !== undefined) {
          process.env.NEXT_PHASE = phase as string;
        } else {
          delete process.env.NEXT_PHASE;
        }

        // Missing Redis credentials
        delete process.env.UPSTASH_REDIS_REST_URL;
        delete process.env.UPSTASH_REDIS_REST_TOKEN;

        // Should throw, not return stub
        await expect(async () => {
          await import('./rate-limit');
        }).rejects.toThrow(/Rate limiting requires Redis configuration/);
      }
    });
  });
});
