/**
 * Tests for error message sanitization
 *
 * Validates that sensitive patterns are redacted while preserving
 * legitimate technical data needed for debugging.
 */

import { describe, it, expect } from 'vitest';
import { sanitizeErrorMessage, sanitizeError } from '../sanitize';

describe('sanitizeErrorMessage', () => {
  describe('Email Pattern', () => {
    it('should redact standard email addresses', () => {
      expect(sanitizeErrorMessage('User john.doe@example.com failed')).toBe(
        'User [REDACTED] failed'
      );
      expect(sanitizeErrorMessage('Contact: support@company.org')).toBe(
        'Contact: [REDACTED]'
      );
    });

    it('should redact multiple emails in same message', () => {
      expect(
        sanitizeErrorMessage('user1@test.com and user2@test.com failed')
      ).toBe('[REDACTED] and [REDACTED] failed');
    });

    it('should handle email-like patterns with special chars', () => {
      expect(sanitizeErrorMessage('user+tag@example.com')).toBe('[REDACTED]');
      expect(sanitizeErrorMessage('user_name@sub.domain.com')).toBe(
        '[REDACTED]'
      );
    });

    it('should NOT redact things that look similar but are not emails', () => {
      // Single @ without domain extension should still match (conservative approach)
      expect(sanitizeErrorMessage('npm@latest version')).toBe(
        'npm@latest version'
      );
    });
  });

  describe('Bearer Token Pattern', () => {
    it('should redact bearer tokens with standard chars', () => {
      expect(sanitizeErrorMessage('Authorization: Bearer abc123def456')).toBe(
        'Authorization: Bearer [REDACTED]'
      );
    });

    it('should redact bearer tokens with dots and underscores (JWTs)', () => {
      expect(
        sanitizeErrorMessage(
          'Auth failed: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123'
        )
      ).toBe('Auth failed: Bearer [REDACTED]');
    });

    it('should be case-insensitive for Bearer keyword', () => {
      expect(sanitizeErrorMessage('bearer token123')).toBe(
        'bearer [REDACTED]'
      );
      expect(sanitizeErrorMessage('BEARER token123')).toBe(
        'BEARER [REDACTED]'
      );
    });

    it('should redact even when bearer is followed by short word (trade-off)', () => {
      // Note: This is a known trade-off - we prioritize security over perfect precision
      // "of" matches [\w._-]+ pattern, so it gets redacted
      // Alternative would be to require minimum token length, but that could miss short tokens
      expect(sanitizeErrorMessage('The bearer of this message')).toBe(
        'The bearer [REDACTED] this message'
      );
    });

    it('should redact email when it appears before Bearer token', () => {
      // Pattern order: email redacted first, then Bearer token
      expect(
        sanitizeErrorMessage('Failed for user@example.com with Bearer abc123')
      ).toBe('Failed for [REDACTED] with Bearer [REDACTED]');
    });

    it('should redact email even in unrealistic Bearer email edge case', () => {
      // Edge case: "Bearer user@example.com" is not a realistic token format
      // but email pattern still redacts it before Bearer pattern runs
      expect(sanitizeErrorMessage('Bearer user@example.com')).toBe(
        'Bearer [REDACTED]'
      );

      // More realistic: Bearer token followed by email in error message
      expect(
        sanitizeErrorMessage('Auth failed: Bearer xyz123 for admin@company.com')
      ).toBe('Auth failed: Bearer [REDACTED] for [REDACTED]');
    });
  });

  describe('Session ID Pattern', () => {
    it('should redact session IDs with equals syntax', () => {
      expect(sanitizeErrorMessage('session_id=abc123def456')).toBe(
        'session_id=[REDACTED]'
      );
      expect(sanitizeErrorMessage('sessionid=xyz789')).toBe(
        'sessionid=[REDACTED]'
      );
      expect(sanitizeErrorMessage('session-id=test123')).toBe(
        'session-id=[REDACTED]'
      );
    });

    it('should redact session IDs with colon syntax', () => {
      expect(sanitizeErrorMessage('session_id: abc123')).toBe(
        'session_id=[REDACTED]'
      );
      expect(sanitizeErrorMessage('sid:xyz789')).toBe('sid=[REDACTED]');
    });

    it('should redact sid (short form)', () => {
      expect(sanitizeErrorMessage('sid=short123')).toBe('sid=[REDACTED]');
    });

    it('should be case-insensitive', () => {
      expect(sanitizeErrorMessage('SESSION_ID=abc123')).toBe(
        'SESSION_ID=[REDACTED]'
      );
      expect(sanitizeErrorMessage('SID=xyz789')).toBe('SID=[REDACTED]');
    });

    it('should NOT redact when session appears without key-value syntax', () => {
      expect(sanitizeErrorMessage('This session is invalid')).toBe(
        'This session is invalid'
      );
    });
  });

  describe('Long Hex Pattern (32+ chars)', () => {
    it('should redact long hex strings (likely secrets)', () => {
      const hex32 = 'a'.repeat(32);
      expect(sanitizeErrorMessage(`Token: ${hex32}`)).toBe(
        'Token: [REDACTED]'
      );

      const hex64 = 'abc123def456'.repeat(6); // 72 chars
      expect(sanitizeErrorMessage(`Hash: ${hex64}`)).toBe(
        'Hash: [REDACTED]'
      );
    });

    it('should redact UUIDs without dashes (128-bit hex)', () => {
      const uuid = 'a1b2c3d4e5f67890a1b2c3d4e5f67890';
      expect(sanitizeErrorMessage(`ID: ${uuid}`)).toBe('ID: [REDACTED]');
    });

    it('should NOT redact short hex strings', () => {
      // 31 chars - below threshold
      const hex31 = 'a'.repeat(31);
      expect(sanitizeErrorMessage(`Color: ${hex31}`)).toBe(`Color: ${hex31}`);

      // Color codes
      expect(sanitizeErrorMessage('Color: #ff5733')).toBe('Color: #ff5733');

      // Short commit hashes
      expect(sanitizeErrorMessage('Commit: abc123d')).toBe('Commit: abc123d');
    });

    it('should NOT redact hex within larger alphanumeric strings', () => {
      // Word boundary should prevent this, but test edge case
      const mixed = 'abc123def456' + 'x'.repeat(20); // Has hex but continues with non-hex
      expect(sanitizeErrorMessage(mixed)).toContain(mixed);
    });

    it('should handle multiple hex strings in one message', () => {
      const hex1 = 'a'.repeat(32);
      const hex2 = 'b'.repeat(32);
      expect(sanitizeErrorMessage(`First: ${hex1}, Second: ${hex2}`)).toBe(
        'First: [REDACTED], Second: [REDACTED]'
      );
    });
  });

  describe('Long Base64 Pattern (40+ chars)', () => {
    it('should redact long base64 strings (likely tokens)', () => {
      const base64_40 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn'; // 40 chars
      expect(sanitizeErrorMessage(`Token: ${base64_40}`)).toBe(
        'Token: [REDACTED]'
      );
    });

    it('should redact base64 with padding', () => {
      const base64WithPadding = 'A'.repeat(40) + '==';
      expect(sanitizeErrorMessage(`Key: ${base64WithPadding}`)).toBe(
        'Key: [REDACTED]'
      );

      const base64SinglePad = 'B'.repeat(40) + '=';
      expect(sanitizeErrorMessage(`Key: ${base64SinglePad}`)).toBe(
        'Key: [REDACTED]'
      );
    });

    it('should NOT redact short base64 strings', () => {
      // 39 chars - below threshold
      const base64_39 = 'A'.repeat(39);
      expect(sanitizeErrorMessage(`Short: ${base64_39}`)).toBe(
        `Short: ${base64_39}`
      );
    });

    it('should redact base64 part even when followed by invalid char', () => {
      // The 40 'A' chars form valid base64 and will be redacted
      // The @ is a word boundary (\W) so lookahead matches
      const withInvalidChar = 'A'.repeat(40) + '@';
      expect(sanitizeErrorMessage(withInvalidChar)).toBe('[REDACTED]@');
    });

    it('should handle JWT-like structures (already covered by Bearer pattern)', () => {
      // This would be caught by Bearer pattern first
      const jwt =
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
      expect(sanitizeErrorMessage(`Bearer ${jwt}`)).toBe('Bearer [REDACTED]');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty string', () => {
      expect(sanitizeErrorMessage('')).toBe('');
    });

    it('should handle null/undefined gracefully', () => {
      expect(sanitizeErrorMessage(null as any)).toBe(null);
      expect(sanitizeErrorMessage(undefined as any)).toBe(undefined);
    });

    it('should handle non-string input gracefully', () => {
      expect(sanitizeErrorMessage(123 as any)).toBe(123);
      expect(sanitizeErrorMessage({} as any)).toEqual({});
    });

    it('should handle messages with no sensitive data', () => {
      const clean = 'An error occurred during processing';
      expect(sanitizeErrorMessage(clean)).toBe(clean);
    });

    it('should handle mixed patterns in single message', () => {
      const mixed =
        'User john@example.com auth failed with Bearer abc123 and session_id=xyz789';
      expect(sanitizeErrorMessage(mixed)).toBe(
        'User [REDACTED] auth failed with Bearer [REDACTED] and session_id=[REDACTED]'
      );
    });

    it('should preserve structure of error messages', () => {
      const structured = `Error: Authentication failed
        User: user@example.com
        Token: Bearer abc123def456
        Session: session_id=xyz789`;

      const sanitized = sanitizeErrorMessage(structured);
      expect(sanitized).toContain('Error: Authentication failed');
      expect(sanitized).toContain('[REDACTED]');
      expect(sanitized).not.toContain('user@example.com');
      expect(sanitized).not.toContain('abc123def456');
    });
  });

  describe('False Positive Prevention', () => {
    it('should NOT redact legitimate technical identifiers', () => {
      // Short UUIDs with dashes (not matching hex pattern due to dashes)
      expect(
        sanitizeErrorMessage('Request ID: 550e8400-e29b-41d4-a716-446655440000')
      ).toBe('Request ID: 550e8400-e29b-41d4-a716-446655440000');

      // Version numbers
      expect(sanitizeErrorMessage('v1.2.3-alpha.4')).toBe('v1.2.3-alpha.4');

      // File paths
      expect(sanitizeErrorMessage('/path/to/file.txt')).toBe(
        '/path/to/file.txt'
      );
    });

    it('should NOT redact common technical terms', () => {
      expect(sanitizeErrorMessage('connection timeout')).toBe(
        'connection timeout'
      );
      expect(sanitizeErrorMessage('invalid input')).toBe('invalid input');
      expect(sanitizeErrorMessage('database error')).toBe('database error');
    });

    it('should preserve stack traces structure', () => {
      const stack = `Error: Test
        at Object.<anonymous> (/path/to/file.js:10:15)
        at Module._compile (internal/modules/cjs/loader.js:999:30)`;

      const sanitized = sanitizeErrorMessage(stack);
      expect(sanitized).toContain('at Object.<anonymous>');
      expect(sanitized).toContain('/path/to/file.js');
    });
  });

  describe('Known Trade-offs', () => {
    it('WILL redact long legitimate hex checksums (security over debuggability)', () => {
      // SHA-256 checksum (64 hex chars)
      const sha256 = 'e'.repeat(64);
      expect(sanitizeErrorMessage(`SHA256: ${sha256}`)).toBe(
        'SHA256: [REDACTED]'
      );

      // This is intentional - better to over-redact than under-redact
    });

    it('WILL redact long legitimate base64 encoded data (security over debuggability)', () => {
      // Long base64 string that might be legitimate encoded data
      const longBase64 = 'VGhpcyBpcyBhIGxlZ2l0aW1hdGUgbG9uZyBiYXNlNjQgc3RyaW5n';
      expect(sanitizeErrorMessage(`Data: ${longBase64}`)).toBe(
        'Data: [REDACTED]'
      );

      // This is intentional - better to over-redact than under-redact
    });
  });
});

describe('sanitizeError', () => {
  it('should sanitize Error object message', () => {
    const error = new Error('Auth failed for user@example.com');
    const sanitized = sanitizeError(error);

    expect(sanitized).toBeInstanceOf(Error);
    expect(sanitized.message).toBe('Auth failed for [REDACTED]');
  });

  it('should preserve error name', () => {
    const error = new TypeError('Invalid user@example.com');
    const sanitized = sanitizeError(error);

    expect(sanitized.name).toBe('TypeError');
  });

  it('should preserve stack trace', () => {
    const error = new Error('Test error user@example.com');
    const originalStack = error.stack;

    const sanitized = sanitizeError(error);

    expect(sanitized.stack).toBe(originalStack);
  });

  it('should create new Error instance (not mutate original)', () => {
    const original = new Error('user@example.com failed');
    const sanitized = sanitizeError(original);

    expect(sanitized).not.toBe(original);
    expect(original.message).toBe('user@example.com failed'); // Original unchanged
    expect(sanitized.message).toBe('[REDACTED] failed');
  });
});
