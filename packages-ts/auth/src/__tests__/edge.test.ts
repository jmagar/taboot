/**
 * Unit tests for edge-compatible session validation.
 *
 * Tests cover all validation scenarios:
 * - Valid sessions return Session object
 * - Expired tokens return null
 * - Tampered signatures return null
 * - Missing claims return null
 * - Undefined tokens return null
 * - Malformed JWE returns null
 * - Missing secret returns null
 *
 * All tests ensure the function never throws (fail-closed).
 */

import { EncryptJWT } from 'jose';
import { verifySession } from '../edge';

describe('verifySession', () => {
  const TEST_SECRET = 'test-secret-key-for-jwt-encryption-minimum-32-characters';
  const secretKey = new TextEncoder().encode(TEST_SECRET);

  // Helper to create valid JWE tokens
  async function createToken(payload: {
    userId: string;
    sessionId: string;
    exp?: number;
    [key: string]: unknown;
  }): Promise<string> {
    const jwt = new EncryptJWT(payload)
      .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
      .setExpirationTime(payload.exp || Math.floor(Date.now() / 1000) + 3600);

    return await jwt.encrypt(secretKey);
  }

  describe('valid sessions', () => {
    it('should return session for valid token', async () => {
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
      });

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeTruthy();
      expect(result?.user.id).toBe('user-123');
      expect(result?.session.id).toBe('session-456');
      expect(result?.session.userId).toBe('user-123');
      expect(result?.session.expiresAt).toBeInstanceOf(Date);
    });

    it('should return session with correct expiry date', async () => {
      const expiryTime = Math.floor(Date.now() / 1000) + 7200; // 2 hours from now
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
        exp: expiryTime,
      });

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result?.session.expiresAt.getTime()).toBe(expiryTime * 1000);
    });

    it('should return session with additional payload fields ignored', async () => {
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
        customField: 'value',
        anotherField: 42,
      });

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result?.user.id).toBe('user-123');
      expect(result?.session.id).toBe('session-456');
    });
  });

  describe('expired tokens', () => {
    it('should return null for expired token', async () => {
      const expiredTime = Math.floor(Date.now() / 1000) - 3600; // 1 hour ago
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
        exp: expiredTime,
      });

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for token expiring now', async () => {
      const nowTime = Math.floor(Date.now() / 1000);
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
        exp: nowTime,
      });

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });
  });

  describe('tampered signatures', () => {
    it('should return null for tampered token', async () => {
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
      });

      // Tamper with the token by changing a character
      const tamperedToken = token.slice(0, -5) + 'XXXXX';

      const result = await verifySession({
        sessionToken: tamperedToken,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for token signed with different secret', async () => {
      const differentSecret = 'different-secret-key-minimum-32-characters-required';
      const differentSecretKey = new TextEncoder().encode(differentSecret);

      const jwt = new EncryptJWT({
        userId: 'user-123',
        sessionId: 'session-456',
      })
        .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
        .setExpirationTime(Math.floor(Date.now() / 1000) + 3600);

      const token = await jwt.encrypt(differentSecretKey);

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET, // Using wrong secret
      });

      expect(result).toBeNull();
    });
  });

  describe('missing claims', () => {
    it('should return null for token without userId', async () => {
      const jwt = new EncryptJWT({
        sessionId: 'session-456',
      } as any)
        .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
        .setExpirationTime(Math.floor(Date.now() / 1000) + 3600);

      const token = await jwt.encrypt(secretKey);

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for token without sessionId', async () => {
      const jwt = new EncryptJWT({
        userId: 'user-123',
      } as any)
        .setProtectedHeader({ alg: 'dir', enc: 'A256GCM' })
        .setExpirationTime(Math.floor(Date.now() / 1000) + 3600);

      const token = await jwt.encrypt(secretKey);

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for token without exp claim', async () => {
      // Manually create token without exp
      const jwt = new EncryptJWT({
        userId: 'user-123',
        sessionId: 'session-456',
        exp: undefined,
      } as any).setProtectedHeader({ alg: 'dir', enc: 'A256GCM' });

      const token = await jwt.encrypt(secretKey);

      const result = await verifySession({
        sessionToken: token,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });
  });

  describe('undefined or missing token', () => {
    it('should return null for undefined token', async () => {
      const result = await verifySession({
        sessionToken: undefined,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for empty string token', async () => {
      const result = await verifySession({
        sessionToken: '',
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });
  });

  describe('malformed tokens', () => {
    it('should return null for completely invalid JWT', async () => {
      const result = await verifySession({
        sessionToken: 'not-a-jwt-token',
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for random base64 string', async () => {
      const result = await verifySession({
        sessionToken: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid',
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });

    it('should return null for partial JWT', async () => {
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
      });

      // Take only first half of token
      const partialToken = token.slice(0, Math.floor(token.length / 2));

      const result = await verifySession({
        sessionToken: partialToken,
        secret: TEST_SECRET,
      });

      expect(result).toBeNull();
    });
  });

  describe('missing secret', () => {
    it('should return null for empty secret', async () => {
      const token = await createToken({
        userId: 'user-123',
        sessionId: 'session-456',
      });

      const result = await verifySession({
        sessionToken: token,
        secret: '',
      });

      expect(result).toBeNull();
    });
  });

  describe('error handling', () => {
    it('should never throw for any input', async () => {
      const badInputs = [
        { sessionToken: null as any, secret: TEST_SECRET },
        { sessionToken: 'bad', secret: '' },
        { sessionToken: undefined, secret: '' },
        { sessionToken: 'x'.repeat(10000), secret: TEST_SECRET },
      ];

      for (const input of badInputs) {
        await expect(verifySession(input)).resolves.toBeNull();
      }
    });
  });
});
