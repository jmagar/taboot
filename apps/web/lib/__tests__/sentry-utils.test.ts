/**
 * Tests for Sentry utilities
 *
 * Validates that sensitive keys are properly scrubbed from data before
 * being sent to Sentry to prevent PII/secret leakage.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { scrubData, parseSampleRate, resolveSentryEnvironment } from '../sentry-utils';

describe('scrubData', () => {
  describe('Authentication & Authorization Keys', () => {
    it('should scrub basic auth keys', () => {
      const input = {
        email: 'user@example.com',
        password: 'secret123',
        pass: 'password',
        token: 'abc123',
        access_token: 'xyz789',
        refresh_token: 'refresh123',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.email).toBe('[Filtered]');
      expect(result.password).toBe('[Filtered]');
      expect(result.pass).toBe('[Filtered]');
      expect(result.token).toBe('[Filtered]');
      expect(result.access_token).toBe('[Filtered]');
      expect(result.refresh_token).toBe('[Filtered]');
    });

    it('should scrub authorization headers', () => {
      const input = {
        authorization: 'Bearer abc123',
        auth: 'token123',
        apikey: 'key123',
        key: 'secret',
        secret: 'mysecret',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.authorization).toBe('[Filtered]');
      expect(result.auth).toBe('[Filtered]');
      expect(result.apikey).toBe('[Filtered]');
      expect(result.key).toBe('[Filtered]');
      expect(result.secret).toBe('[Filtered]');
    });

    it('should scrub custom auth headers', () => {
      const input = {
        'x-api-key': 'api123',
        'x-authorization': 'Bearer token',
        'x-auth-token': 'auth123',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result['x-api-key']).toBe('[Filtered]');
      expect(result['x-authorization']).toBe('[Filtered]');
      expect(result['x-auth-token']).toBe('[Filtered]');
    });
  });

  describe('Session Management Keys', () => {
    it('should scrub session identifiers', () => {
      const input = {
        sessionid: 'session123',
        session_id: 'session456',
        sid: 'sid789',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.sessionid).toBe('[Filtered]');
      expect(result.session_id).toBe('[Filtered]');
      expect(result.sid).toBe('[Filtered]');
    });

    it('should scrub cookie headers', () => {
      const input = {
        cookie: 'session=abc123; token=xyz789',
        'set-cookie': 'session=abc123; HttpOnly',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.cookie).toBe('[Filtered]');
      expect(result['set-cookie']).toBe('[Filtered]');
    });
  });

  describe('PII Keys', () => {
    it('should scrub personal identifiable information', () => {
      const input = {
        phone: '+1-555-1234',
        address: '123 Main St',
        ssn: '123-45-6789',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.phone).toBe('[Filtered]');
      expect(result.address).toBe('[Filtered]');
      expect(result.ssn).toBe('[Filtered]');
    });
  });

  describe('Network & IP Keys', () => {
    it('should scrub IP addresses and forwarding headers', () => {
      const input = {
        ip: '192.168.1.1',
        ip_address: '10.0.0.1',
        'x-forwarded-for': '203.0.113.1',
        'x-real-ip': '198.51.100.1',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.ip).toBe('[Filtered]');
      expect(result.ip_address).toBe('[Filtered]');
      expect(result['x-forwarded-for']).toBe('[Filtered]');
      expect(result['x-real-ip']).toBe('[Filtered]');
    });
  });

  describe('Security Keys', () => {
    it('should scrub CSRF tokens', () => {
      const input = {
        csrf: 'csrf123',
        'x-csrf-token': 'token123',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.csrf).toBe('[Filtered]');
      expect(result['x-csrf-token']).toBe('[Filtered]');
    });
  });

  describe('Case Insensitivity', () => {
    it('should scrub keys regardless of case', () => {
      const input = {
        EMAIL: 'user@example.com',
        Password: 'secret',
        TOKEN: 'abc123',
        Session_ID: 'session123',
        'X-API-Key': 'key123',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.EMAIL).toBe('[Filtered]');
      expect(result.Password).toBe('[Filtered]');
      expect(result.TOKEN).toBe('[Filtered]');
      expect(result.Session_ID).toBe('[Filtered]');
      expect(result['X-API-Key']).toBe('[Filtered]');
    });
  });

  describe('Nested Objects', () => {
    it('should recursively scrub nested objects', () => {
      const input = {
        user: {
          email: 'user@example.com',
          password: 'secret',
          profile: {
            phone: '555-1234',
          },
        },
        request: {
          headers: {
            authorization: 'Bearer token',
            'x-real-ip': '192.168.1.1',
          },
        },
      };

      const result = scrubData(input) as Record<string, unknown>;
      const user = result.user as Record<string, unknown>;
      const profile = user.profile as Record<string, unknown>;
      const request = result.request as Record<string, unknown>;
      const headers = request.headers as Record<string, unknown>;

      expect(user.email).toBe('[Filtered]');
      expect(user.password).toBe('[Filtered]');
      expect(profile.phone).toBe('[Filtered]');
      expect(headers.authorization).toBe('[Filtered]');
      expect(headers['x-real-ip']).toBe('[Filtered]');
    });

    it('should scrub arrays', () => {
      const input = [
        { email: 'user1@example.com' },
        { email: 'user2@example.com', token: 'abc123' },
      ];

      const result = scrubData(input) as Array<Record<string, unknown>>;
      expect(result[0].email).toBe('[Filtered]');
      expect(result[1].email).toBe('[Filtered]');
      expect(result[1].token).toBe('[Filtered]');
    });
  });

  describe('Edge Cases', () => {
    it('should handle null and undefined', () => {
      expect(scrubData(null)).toBe(null);
      expect(scrubData(undefined)).toBe(undefined);
    });

    it('should preserve non-sensitive keys', () => {
      const input = {
        username: 'john_doe',
        id: 123,
        timestamp: '2025-01-26T12:00:00Z',
        error: 'Something went wrong',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.username).toBe('john_doe');
      expect(result.id).toBe(123);
      expect(result.timestamp).toBe('2025-01-26T12:00:00Z');
      expect(result.error).toBe('Something went wrong');
    });

    it('should handle primitive values', () => {
      expect(scrubData('string')).toBe('string');
      expect(scrubData(123)).toBe(123);
      expect(scrubData(true)).toBe(true);
    });

    it('should handle mixed sensitive and non-sensitive keys', () => {
      const input = {
        id: 123,
        email: 'user@example.com',
        username: 'john',
        password: 'secret',
        timestamp: Date.now(),
        token: 'abc123',
      };

      const result = scrubData(input) as Record<string, unknown>;
      expect(result.id).toBe(123);
      expect(result.email).toBe('[Filtered]');
      expect(result.username).toBe('john');
      expect(result.password).toBe('[Filtered]');
      expect(result.timestamp).toBe(input.timestamp);
      expect(result.token).toBe('[Filtered]');
    });
  });
});

describe('parseSampleRate', () => {
  it('should parse valid sample rates', () => {
    expect(parseSampleRate('0.5', 1.0)).toBe(0.5);
    expect(parseSampleRate('0.0', 1.0)).toBe(0.0);
    expect(parseSampleRate('1.0', 0.5)).toBe(1.0);
  });

  it('should clamp values to 0-1 range', () => {
    expect(parseSampleRate('1.5', 1.0)).toBe(1.0);
    expect(parseSampleRate('-0.5', 1.0)).toBe(0.0);
    expect(parseSampleRate('2.0', 0.5)).toBe(1.0);
  });

  it('should use fallback for invalid values', () => {
    expect(parseSampleRate('invalid', 0.8)).toBe(0.8);
    expect(parseSampleRate(undefined, 0.7)).toBe(0.7);
    expect(parseSampleRate('NaN', 0.6)).toBe(0.6);
  });

  it('should handle edge cases', () => {
    // Empty string converts to 0 (Number('') === 0)
    expect(parseSampleRate('', 0.5)).toBe(0.0);
    // Infinity is not finite, so uses fallback
    expect(parseSampleRate('Infinity', 0.5)).toBe(0.5);
    expect(parseSampleRate('-Infinity', 0.5)).toBe(0.5);
  });
});

describe('resolveSentryEnvironment', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should prioritize SENTRY_ENVIRONMENT', () => {
    process.env.SENTRY_ENVIRONMENT = 'production';
    process.env.NODE_ENV = 'development';
    expect(resolveSentryEnvironment()).toBe('production');
  });

  it('should fall back to NEXT_PUBLIC_SENTRY_ENVIRONMENT', () => {
    process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT = 'staging';
    process.env.NODE_ENV = 'development';
    expect(resolveSentryEnvironment()).toBe('staging');
  });

  it('should fall back to VERCEL_ENV variants', () => {
    process.env.NEXT_PUBLIC_VERCEL_ENV = 'preview';
    expect(resolveSentryEnvironment()).toBe('preview');

    delete process.env.NEXT_PUBLIC_VERCEL_ENV;
    process.env.VERCEL_ENV = 'production';
    expect(resolveSentryEnvironment()).toBe('production');
  });

  it('should fall back to NODE_ENV as last resort', () => {
    process.env.NODE_ENV = 'test';
    expect(resolveSentryEnvironment()).toBe('test');
  });

  it('should return undefined if no environment is set', () => {
    delete process.env.SENTRY_ENVIRONMENT;
    delete process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT;
    delete process.env.NEXT_PUBLIC_VERCEL_ENV;
    delete process.env.VERCEL_ENV;
    delete process.env.NEXT_PUBLIC_RUNTIME_ENV;
    delete process.env.NODE_ENV;
    expect(resolveSentryEnvironment()).toBe(undefined);
  });
});
