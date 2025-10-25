/**
 * CSRF Protection Implementation
 *
 * Implements defense-in-depth CSRF protection using:
 * 1. SameSite='lax' cookies (configured in better-auth)
 * 2. Double-submit cookie pattern with signed tokens
 * 3. Origin/Referer header validation
 *
 * Based on OWASP CSRF Prevention Cheat Sheet:
 * https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
 */

import { NextRequest, NextResponse } from 'next/server';
import { logger } from '@/lib/logger';

const CSRF_TOKEN_COOKIE_NAME = '__Host-taboot.csrf';
const CSRF_TOKEN_HEADER_NAME = 'x-csrf-token';
const CSRF_SECRET = process.env.CSRF_SECRET || process.env.AUTH_SECRET || 'development-csrf-secret';

// State-changing HTTP methods that require CSRF protection
const PROTECTED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];

/**
 * Generate a cryptographically secure CSRF token
 */
async function generateCsrfToken(): Promise<string> {
  // Generate 32 random bytes
  const buffer = new Uint8Array(32);
  crypto.getRandomValues(buffer);

  // Convert to base64url (URL-safe)
  const token = btoa(String.fromCharCode(...buffer))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  return token;
}

/**
 * Sign a CSRF token with HMAC-SHA256
 */
async function signToken(token: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(token);
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(CSRF_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', key, data);
  const signatureArray = new Uint8Array(signature);
  const signatureBase64 = btoa(String.fromCharCode(...signatureArray))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');

  return `${token}.${signatureBase64}`;
}

/**
 * Verify a signed CSRF token
 */
async function verifyToken(signedToken: string): Promise<boolean> {
  const [token, signature] = signedToken.split('.');
  if (!token || !signature) {
    return false;
  }

  const expectedSigned = await signToken(token);
  const [, expectedSignature] = expectedSigned.split('.');

  if (!expectedSignature) {
    return false;
  }

  // Constant-time comparison to prevent timing attacks
  if (signature.length !== expectedSignature.length) {
    return false;
  }

  let result = 0;
  for (let i = 0; i < signature.length; i++) {
    result |= signature.charCodeAt(i) ^ expectedSignature.charCodeAt(i);
  }

  return result === 0;
}

/**
 * Validate Origin/Referer headers match the request host
 * Provides additional protection against cross-origin attacks
 */
function validateOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  const referer = request.headers.get('referer');
  const host = request.headers.get('host');

  if (!host) {
    logger.warn('CSRF: Missing host header', {
      url: request.url,
      method: request.method,
    });
    return false;
  }

  // Check origin header (present for CORS requests and POST from forms)
  if (origin) {
    const originUrl = new URL(origin);
    if (originUrl.host !== host) {
      logger.warn('CSRF: Origin mismatch', {
        origin: originUrl.host,
        host,
        url: request.url,
      });
      return false;
    }
  }

  // Check referer header (fallback for browsers that don't send Origin)
  if (referer) {
    const refererUrl = new URL(referer);
    if (refererUrl.host !== host) {
      logger.warn('CSRF: Referer mismatch', {
        referer: refererUrl.host,
        host,
        url: request.url,
      });
      return false;
    }
  }

  // At least one header must be present for state-changing requests
  if (!origin && !referer) {
    logger.warn('CSRF: Missing origin and referer headers', {
      url: request.url,
      method: request.method,
    });
    return false;
  }

  return true;
}

/**
 * Get or generate CSRF token for the request
 */
export async function getCsrfToken(request: NextRequest): Promise<string> {
  const cookieToken = request.cookies.get(CSRF_TOKEN_COOKIE_NAME)?.value;

  if (cookieToken && await verifyToken(cookieToken)) {
    return cookieToken;
  }

  // Generate new token
  const newToken = await generateCsrfToken();
  const signedToken = await signToken(newToken);

  return signedToken;
}

/**
 * Validate CSRF token from request
 */
async function validateCsrfToken(request: NextRequest): Promise<boolean> {
  const cookieToken = request.cookies.get(CSRF_TOKEN_COOKIE_NAME)?.value;
  const headerToken = request.headers.get(CSRF_TOKEN_HEADER_NAME);

  // Both tokens must be present
  if (!cookieToken || !headerToken) {
    logger.warn('CSRF: Missing token', {
      hasCookie: !!cookieToken,
      hasHeader: !!headerToken,
      url: request.url,
      method: request.method,
    });
    return false;
  }

  // Verify cookie token signature
  const cookieValid = await verifyToken(cookieToken);
  if (!cookieValid) {
    logger.warn('CSRF: Invalid cookie token signature', {
      url: request.url,
      method: request.method,
    });
    return false;
  }

  // Tokens must match (double-submit pattern)
  if (cookieToken !== headerToken) {
    logger.warn('CSRF: Token mismatch', {
      url: request.url,
      method: request.method,
    });
    return false;
  }

  return true;
}

/**
 * CSRF middleware for Next.js middleware
 * Sets CSRF token cookie on all requests
 */
export async function csrfMiddleware(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.next();

  // Skip CSRF checks for safe methods (GET, HEAD, OPTIONS)
  if (!PROTECTED_METHODS.includes(request.method)) {
    // Set CSRF token cookie for GET requests (so it's available for subsequent mutations)
    const token = await getCsrfToken(request);
    response.cookies.set(CSRF_TOKEN_COOKIE_NAME, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/',
      maxAge: 60 * 60 * 24, // 24 hours
    });

    // Also expose token in header for client-side access
    response.headers.set(CSRF_TOKEN_HEADER_NAME, token);

    return response;
  }

  // For state-changing methods, validate CSRF protection

  // 1. Validate origin/referer headers
  if (!validateOrigin(request)) {
    logger.error('CSRF validation failed: origin/referer check', {
      url: request.url,
      method: request.method,
      origin: request.headers.get('origin'),
      referer: request.headers.get('referer'),
    });

    return NextResponse.json(
      { error: 'CSRF validation failed: invalid origin' },
      { status: 403 }
    );
  }

  // 2. Validate CSRF token (double-submit pattern)
  const tokenValid = await validateCsrfToken(request);
  if (!tokenValid) {
    logger.error('CSRF validation failed: token check', {
      url: request.url,
      method: request.method,
    });

    return NextResponse.json(
      { error: 'CSRF validation failed: invalid or missing token' },
      { status: 403 }
    );
  }

  // CSRF validation passed - log at info level since logger doesn't have debug
  logger.info('CSRF validation passed', {
    url: request.url,
    method: request.method,
  });

  return response;
}

/**
 * Higher-order function to wrap API route handlers with CSRF protection
 * Use this for individual route protection instead of middleware-level checks
 */
type Handler = (req: Request) => Promise<NextResponse>;

export function withCsrf(handler: Handler): Handler {
  return async (req: Request): Promise<NextResponse> => {
    const request = new NextRequest(req);

    // Skip CSRF for safe methods
    if (!PROTECTED_METHODS.includes(request.method)) {
      return handler(req);
    }

    // Validate origin/referer
    if (!validateOrigin(request)) {
      logger.error('CSRF validation failed in route handler: origin/referer check', {
        url: request.url,
        method: request.method,
      });

      return NextResponse.json(
        { error: 'CSRF validation failed: invalid origin' },
        { status: 403 }
      );
    }

    // Validate CSRF token
    const tokenValid = await validateCsrfToken(request);
    if (!tokenValid) {
      logger.error('CSRF validation failed in route handler: token check', {
        url: request.url,
        method: request.method,
      });

      return NextResponse.json(
        { error: 'CSRF validation failed: invalid or missing token' },
        { status: 403 }
      );
    }

    // CSRF validation passed, execute handler
    return handler(req);
  };
}
