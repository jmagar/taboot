/**
 * Edge-compatible session validation for middleware.
 *
 * Better-auth uses signed JWE cookies when cookie caching is enabled.
 * This module provides JWT verification for edge runtime environments
 * where database calls are not allowed.
 *
 * @module edge
 */

import { jwtDecrypt, type JWTPayload } from 'jose';
import type { Session, SessionTokenPayload } from './types';

/**
 * Verify a session token and return session data.
 *
 * This function validates JWT tokens in edge runtime without database calls:
 * 1. Decrypts the JWE token using the auth secret
 * 2. Validates expiry timestamp
 * 3. Validates required claims (userId, sessionId)
 * 4. Returns null for any validation failure (never throws)
 *
 * **Security:**
 * - Uses jose library for JWE decryption (same as better-auth)
 * - Validates cryptographic signature
 * - Checks expiry before returning session
 * - Fail-closed: returns null on any error
 *
 * **Edge Runtime:**
 * - No database calls
 * - No Node.js-specific APIs
 * - Compatible with Vercel Edge, Cloudflare Workers
 *
 * @param options - Verification options
 * @param options.sessionToken - The JWE token from cookie or bearer header
 * @param options.secret - AUTH_SECRET for decryption
 * @returns Session data if valid, null otherwise (never throws)
 *
 * @example
 * ```typescript
 * const session = await verifySession({
 *   sessionToken: request.cookies.get('better-auth.session_token')?.value,
 *   secret: process.env.AUTH_SECRET!,
 * });
 *
 * if (session?.user) {
 *   // User is authenticated
 * }
 * ```
 */
export async function verifySession(options: {
  sessionToken: string | undefined;
  secret: string;
}): Promise<Session | null> {
  if (!options.sessionToken) {
    return null;
  }

  if (!options.secret) {
    return null;
  }

  try {
    // Decode the secret to a Uint8Array for jose
    const secretKey = new TextEncoder().encode(options.secret);

    // Decrypt the JWE token
    const { payload } = await jwtDecrypt(options.sessionToken, secretKey, {
      // Better-auth uses HS256 for symmetric encryption
      // The jose library will validate the algorithm automatically
    });

    // Type assertion for better TypeScript support
    const sessionPayload = payload as JWTPayload & Partial<SessionTokenPayload>;

    // Validate expiry
    if (!sessionPayload.exp || sessionPayload.exp < Date.now() / 1000) {
      return null;
    }

    // Validate required claims
    if (!sessionPayload.userId || !sessionPayload.sessionId) {
      return null;
    }

    // Return minimal session structure for middleware
    // This matches the Session type from better-auth
    return {
      user: {
        id: sessionPayload.userId,
      },
      session: {
        id: sessionPayload.sessionId,
        userId: sessionPayload.userId,
        expiresAt: new Date(sessionPayload.exp * 1000),
      },
    };
  } catch (error) {
    // Invalid signature, malformed token, decryption error, etc.
    // FAIL CLOSED: Return null for any error
    return null;
  }
}
