import { NextRequest, NextResponse } from 'next/server';
import { csrfMiddleware } from '@/lib/csrf';
import { AUTH_COOKIE_NAME, AUTH_COOKIE_LEGACY_NAME, AUTH_BEARER_PREFIX } from '@taboot/auth/constants';
import { verifySession } from '@taboot/auth/edge';

/**
 * Transfer CSRF-related cookies and headers from one response to another.
 * Used to merge CSRF data for safe HTTP methods.
 */
function transferCsrfData(source: NextResponse, target: NextResponse): void {
  // Copy all cookies from source response
  source.cookies.getAll().forEach((cookie) => {
    target.cookies.set(cookie);
  });

  // Copy CSRF-specific headers
  source.headers.forEach((value, key) => {
    if (key.toLowerCase().startsWith('x-csrf')) {
      target.headers.set(key, value);
    }
  });
}

/**
 * Verify the request has a valid authenticated session.
 * Uses proper JWT validation instead of weak cookie presence checks.
 * Checks both bearer token authorization header and session cookies.
 *
 * @returns Promise<boolean> - True if session is valid, false otherwise (fail-closed)
 */
async function hasValidSession(request: NextRequest): Promise<boolean> {
  try {
    // Get token from cookie or bearer header
    const sessionToken =
      request.cookies.get(AUTH_COOKIE_NAME)?.value ||
      request.cookies.get(AUTH_COOKIE_LEGACY_NAME)?.value;

    const authHeader = request.headers.get('authorization');
    const bearerToken = authHeader?.startsWith(AUTH_BEARER_PREFIX)
      ? authHeader.slice(AUTH_BEARER_PREFIX.length)
      : undefined;

    const token = sessionToken || bearerToken;

    // Verify session with proper JWT validation (not just presence check)
    const session = await verifySession({
      sessionToken: token,
      secret: process.env.AUTH_SECRET!,
    });

    return !!session?.user;
  } catch (error) {
    // FAIL CLOSED: Log error, deny access
    console.error('Auth session check failed - denying access (fail-closed)', {
      pathname: request.nextUrl.pathname,
      error: error instanceof Error ? error.message : String(error),
    });
    return false;
  }
}

/**
 * Apply security headers to the response including CSP with nonce.
 */
function applySecurityHeaders(response: NextResponse): void {
  // Generate nonce for CSP script tags
  const nonce = Buffer.from(crypto.getRandomValues(new Uint8Array(16))).toString('base64');

  // Content Security Policy configuration
  const cspConfig = {
    'default-src': "'self'",
    'script-src': `'self' 'nonce-${nonce}' https://app.posthog.com https://vercel.live https://*.sentry.io`,
    'style-src': "'self' 'unsafe-inline'", // Required for Tailwind CSS
    'img-src': "'self' data: https:",
    'font-src': "'self' data:",
    'connect-src': "'self' https://*.posthog.com https://*.sentry.io https://*.ingest.sentry.io",
    'frame-ancestors': "'none'",
    'base-uri': "'self'",
    'form-action': "'self'",
    'upgrade-insecure-requests': '',
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
  '/api/auth/session',
  '/api/health',
  '/api/test',
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

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
        console.error('CSRF validation failed - rejecting request (fail-closed)', {
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
  }

  // Helper to check if pathname matches route exactly or starts with route/
  const startsWithRoute = (route: string) => pathname === route || pathname.startsWith(route + '/');

  // Check if current route needs authentication handling
  const isProtectedRoute = protectedRoutes.some(startsWithRoute);
  const isAuthRoute = authRoutes.some(startsWithRoute);

  // Check authentication status if needed for route decision
  const isAuthenticated = (isProtectedRoute || isAuthRoute) && await hasValidSession(request);

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
  applySecurityHeaders(response);

  return response;
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
