import { NextRequest, NextResponse } from 'next/server';
import { csrfMiddleware } from '@/lib/csrf';
import { AUTH_COOKIE_NAME, AUTH_COOKIE_LEGACY_NAME, AUTH_BEARER_PREFIX } from '@taboot/auth/constants';
import { verifySession } from '@taboot/auth/edge';
import { logger } from '@/lib/logger';
import {
  setupSoftDeleteContext,
  SOFT_DELETE_REQUEST_ID_HEADER,
  SOFT_DELETE_USER_ID_HEADER,
  SOFT_DELETE_IP_ADDRESS_HEADER,
  SOFT_DELETE_USER_AGENT_HEADER,
} from '@/lib/soft-delete-context.edge';

/**
 * Transfer CSRF-related cookies and headers from one response to another.
 * Used to merge CSRF data for safe HTTP methods.
 */
function transferCsrfData(source: NextResponse, target: NextResponse): void {
  // Copy only CSRF-related cookies from source response
  source.cookies.getAll().forEach((cookie) => {
    if (cookie.name.toLowerCase().includes('csrf')) {
      target.cookies.set(cookie);
    }
  });

  // Copy CSRF-specific headers
  source.headers.forEach((value, key) => {
    if (key.toLowerCase().startsWith('x-csrf')) {
      target.headers.set(key, value);
    }
  });
}

/**
 * Validate IP address format (IPv4 or IPv6).
 * Edge Runtime compatible implementation.
 * @param ip - IP address string to validate
 * @returns true if valid IPv4 or IPv6 address
 */
function isValidIp(ip: string): boolean {
  // IPv4 pattern: 0.0.0.0 - 255.255.255.255
  const ipv4Pattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

  // IPv6 pattern: simplified regex that catches most valid IPv6 addresses
  // Full validation includes: standard form, compressed form, IPv4-mapped, etc.
  const ipv6Pattern = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:)?[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}::[0-9a-fA-F]{1,4}$|^(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}::$/;

  return ipv4Pattern.test(ip) || ipv6Pattern.test(ip);
}

/**
 * Get client IP address from Next.js request.
 *
 * SECURITY: Only trust proxy headers if behind verified reverse proxy.
 * Set TRUST_PROXY=true in production ONLY if using Cloudflare, nginx, etc.
 *
 * @param request - The incoming NextRequest
 * @returns Client IP address or undefined
 */
function getClientIp(request: NextRequest): string | undefined {
  const trustProxy = /^true$/i.test(process.env.TRUST_PROXY ?? '');

  // Only trust proxy headers if configured
  if (trustProxy) {
    // Priority 1: Cloudflare connecting IP
    const cfIp = request.headers.get('cf-connecting-ip');
    if (cfIp && isValidIp(cfIp)) {
      return cfIp;
    }

    // Priority 2: X-Real-IP (nginx)
    const realIp = request.headers.get('x-real-ip');
    if (realIp && isValidIp(realIp)) {
      return realIp;
    }

    // Priority 3: X-Forwarded-For leftmost (generic proxies)
    const xff = request.headers.get('x-forwarded-for') ?? '';
    const leftmost = xff.split(',')[0]?.trim();
    if (leftmost && isValidIp(leftmost)) {
      return leftmost;
    }
  }

  // Fallback: Check if NextRequest exposes IP (Next.js 13+)
  const nextReq = request as { ip?: string };
  return nextReq.ip && isValidIp(nextReq.ip) ? nextReq.ip : undefined;
}

/**
 * Verify the request has a valid authenticated session.
 * Uses proper JWT validation instead of weak cookie presence checks.
 * Checks both bearer token authorization header and session cookies.
 *
 * @returns Promise with session object if valid, null otherwise (fail-closed)
 */
async function getValidSession(request: NextRequest): Promise<{ user: { id: string } } | null> {
  try {
    // Validate AUTH_SECRET is configured (fallback to BETTER_AUTH_SECRET for single-user systems)
    const authSecret = process.env.AUTH_SECRET || process.env.BETTER_AUTH_SECRET;
    if (!authSecret) {
      logger.error('Auth session check failed - AUTH_SECRET/BETTER_AUTH_SECRET not configured (fail-closed)', {
        pathname: request.nextUrl.pathname,
      });
      return null;
    }

    // Get token from cookie or bearer header
    let sessionToken =
      request.cookies.get(AUTH_COOKIE_NAME)?.value ||
      request.cookies.get(AUTH_COOKIE_LEGACY_NAME)?.value;

    // Validate cookie format to help debug auth issues
    if (sessionToken && !/^[A-Za-z0-9._-]+$/.test(sessionToken)) {
      logger.warn('Invalid session cookie format detected - treating as missing', {
        pathname: request.nextUrl.pathname,
        cookiePrefix: sessionToken.substring(0, 10),
      });
      sessionToken = undefined;
    }

    const authHeader = request.headers.get('authorization');
    const bearerToken = authHeader?.startsWith(AUTH_BEARER_PREFIX)
      ? authHeader.slice(AUTH_BEARER_PREFIX.length)
      : undefined;

    const token = sessionToken || bearerToken;

    // Verify session with proper JWT validation (not just presence check)
    const session = await verifySession({
      sessionToken: token,
      secret: authSecret,
    });

    return session?.user ? session : null;
  } catch (error) {
    // FAIL CLOSED: Log error, deny access
    logger.error('Auth session check failed - denying access (fail-closed)', {
      pathname: request.nextUrl.pathname,
      error: error instanceof Error ? error.message : String(error),
    });
    return null;
  }
}

/**
 * Apply security headers to the response including CSP with nonce.
 */
function applySecurityHeaders(response: NextResponse): void {
  // Generate nonce for CSP script tags (Edge runtime compatible)
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  const nonce = btoa(String.fromCharCode(...bytes));

  // Content Security Policy configuration
  const betterAuthUrl = process.env.BETTER_AUTH_URL || process.env.NEXT_PUBLIC_BETTER_AUTH_URL || '';

  const cspConfig = {
    'default-src': "'self'",
    'script-src': `'self' 'nonce-${nonce}' 'sha256-rbbnijHn7DZ6ps39myQ3cVQF1H+U/PJfHh5ei/Q2kb8=' https://app.posthog.com https://vercel.live https://*.sentry.io https://browser.sentry-cdn.com`,
    'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com", // Required for Tailwind CSS + Google Fonts
    'img-src': "'self' data: https:",
    'font-src': "'self' data: https://fonts.gstatic.com",
    'connect-src': `'self' ${betterAuthUrl} https://*.posthog.com https://us-eu.posthog.com https://*.sentry.io https://*.ingest.sentry.io`,
    'frame-ancestors': "'none'",
    'base-uri': "'self'",
    'form-action': "'self'",
    'upgrade-insecure-requests': '',
    'report-uri': '/api/csp-report',
  };

  // Build CSP string
  const csp = Object.entries(cspConfig)
    .map(([key, value]) => (value ? `${key} ${value}` : key))
    .join('; ');

  // Security headers
  const securityHeaders = {
    'Content-Security-Policy': csp,
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'x-nonce': nonce, // Pass nonce for script tags in layout
  };

  // Apply all security headers
  Object.entries(securityHeaders).forEach(([key, value]) => {
    response.headers.set(key, value);
  });
}

// Routes that require authentication
const protectedRoutes = ['/dashboard', '/profile', '/settings'];

// Routes that should redirect to dashboard if user is authenticated
// Note: /two-factor and /reset-password are excluded as they can be accessed during auth flow
const authRoutes = ['/sign-in', '/sign-up', '/forgot-password'];

// API routes that should skip CSRF checks (read-only endpoints)
const csrfExcludedRoutes = [
  '/api/auth', // Better Auth handles CSRF via state parameters (OAuth) and built-in protections
  '/api/health',
  '/api/test',
  '/api/csp-report', // Browser-initiated CSP violation reports
];

/**
 * Helper to check if pathname matches route exactly or starts with route/
 */
const startsWithRoute = (pathname: string, route: string) =>
  pathname === route || pathname.startsWith(route + '/');

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Track soft delete context metadata for headers
  let softDeleteMetadata: ReturnType<typeof setupSoftDeleteContext> | undefined;

  try {
    // Apply CSRF protection to API routes (unless excluded)
    if (pathname.startsWith('/api')) {
      const isExcluded = csrfExcludedRoutes.some(
        (route) => pathname === route || pathname.startsWith(`${route}/`)
      );

      if (!isExcluded) {
        try {
          const csrfResponse = await csrfMiddleware(request);

          // Handle safe methods (GET/HEAD/OPTIONS) - merge CSRF headers and continue
          const safeMethods = ['GET', 'HEAD', 'OPTIONS'];
          if (safeMethods.includes(request.method)) {
            const response = NextResponse.next();

            // Transfer CSRF-related cookies and headers
            transferCsrfData(csrfResponse, response);
            return response;
          }

          // For unsafe methods, enforce CSRF validation
          if (csrfResponse.status === 403) {
            return csrfResponse;
          }
        } catch (error) {
          // FAIL CLOSED: Reject request on CSRF validation error
          logger.error('CSRF validation failed - rejecting request (fail-closed)', {
            pathname: request.nextUrl.pathname,
            method: request.method,
            error: error instanceof Error ? error.message : String(error),
          });

          return NextResponse.json(
            { error: 'Security validation failed' },
            { status: 403 }
          );
        }
      }

      // Extract soft delete context metadata for authenticated API requests
      // Metadata is passed via headers to route handlers (Node.js runtime)
      const session = await getValidSession(request);
      if (session) {
        try {
          softDeleteMetadata = setupSoftDeleteContext(request, session);
        } catch (error) {
          // Log error but don't fail the request - context setup is non-critical
          logger.error('Failed to setup soft delete context', {
            pathname: request.nextUrl.pathname,
            error: error instanceof Error ? error.message : String(error),
          });
        }
      }
    }

    // Check if current route needs authentication handling
    const isProtectedRoute = protectedRoutes.some((route) => startsWithRoute(pathname, route));
    const isAuthRoute = authRoutes.some((route) => startsWithRoute(pathname, route));

    // Check authentication status if needed for route decision
    const session = (isProtectedRoute || isAuthRoute) ? await getValidSession(request) : null;
    const isAuthenticated = !!session;

    // Redirect unauthenticated users from protected routes to sign-in with callback
    if (isProtectedRoute && !isAuthenticated) {
      const fullPath = pathname + request.nextUrl.search;
      const signInUrl = new URL('/sign-in', request.url);
      signInUrl.searchParams.set('callbackUrl', encodeURIComponent(fullPath));
      return NextResponse.redirect(signInUrl);
    }

    // Redirect authenticated users from auth routes to dashboard
    if (isAuthRoute && isAuthenticated) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    // Create response with security headers
    const response = NextResponse.next();
    if (!pathname.startsWith('/api')) {
      applySecurityHeaders(response);
    }

    // Pass soft delete context metadata via headers for route handlers
    // Route handlers (Node.js runtime) will read these and call Prisma functions
    if (softDeleteMetadata) {
      response.headers.set(SOFT_DELETE_REQUEST_ID_HEADER, softDeleteMetadata.requestId);
      if (softDeleteMetadata.userId) {
        response.headers.set(SOFT_DELETE_USER_ID_HEADER, softDeleteMetadata.userId);
      }
      if (softDeleteMetadata.ipAddress) {
        response.headers.set(SOFT_DELETE_IP_ADDRESS_HEADER, softDeleteMetadata.ipAddress);
      }
      if (softDeleteMetadata.userAgent) {
        response.headers.set(SOFT_DELETE_USER_AGENT_HEADER, softDeleteMetadata.userAgent);
      }
    }

    return response;
  } catch (error) {
    // Catch-all error handler for middleware
    logger.error('Middleware error', {
      pathname: request.nextUrl.pathname,
      error: error instanceof Error ? error.message : String(error),
    });
    throw error;
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     *
     * Fix #1: Explicitly include /api routes so CSRF/auth branches run
     */
    '/api/:path*',
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
