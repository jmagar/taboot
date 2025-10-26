import { auth } from '@taboot/auth';
import { NextRequest, NextResponse } from 'next/server';
import { csrfMiddleware } from '@/lib/csrf';

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
    // Fix #2: Boundary-aware route exclusion check
    const isExcluded = csrfExcludedRoutes.some(
      (route) => pathname === route || pathname.startsWith(`${route}/`)
    );

    if (!isExcluded) {
      // Fix #4: Call CSRF middleware only once
      const csrfResponse = await csrfMiddleware(request);

      // For safe methods (GET/HEAD/OPTIONS), merge CSRF cookies/headers and continue
      if (request.method === 'GET' || request.method === 'HEAD' || request.method === 'OPTIONS') {
        const response = NextResponse.next();

        // Copy CSRF cookies and headers to the response
        csrfResponse.cookies.getAll().forEach((cookie) => {
          response.cookies.set(cookie);
        });
        csrfResponse.headers.forEach((value, key) => {
          if (key.toLowerCase().startsWith('x-csrf')) {
            response.headers.set(key, value);
          }
        });

        return response;
      }

      // For unsafe methods (POST/PUT/PATCH/DELETE), return 403 if CSRF check failed
      if (csrfResponse.status === 403) {
        return csrfResponse;
      }
    }
  }

  // Helper to check if pathname matches route exactly or starts with route/
  const startsWithRoute = (route: string) => pathname === route || pathname.startsWith(route + '/');

  // Check if current route is protected or an auth route
  const isProtectedRoute = protectedRoutes.some(startsWithRoute);
  const isAuthRoute = authRoutes.some(startsWithRoute);

  // Only fetch session if needed for protected or auth routes
  let isAuthenticated = false;
  if (isProtectedRoute || isAuthRoute) {
    const session = await auth.api.getSession({
      headers: request.headers,
    });
    isAuthenticated = !!session?.user;
  }

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

  // Generate nonce for CSP
  const nonce = Buffer.from(crypto.getRandomValues(new Uint8Array(16))).toString('base64');

  // Create response with CSP headers
  const response = NextResponse.next();

  // Set Content-Security-Policy header with nonce for scripts
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' https://app.posthog.com https://vercel.live https://*.sentry.io`,
    "style-src 'self' 'unsafe-inline'", // Tailwind requires unsafe-inline
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://*.posthog.com https://*.sentry.io https://*.ingest.sentry.io",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests",
  ].join('; ');

  response.headers.set('Content-Security-Policy', csp);
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');

  // Pass nonce to response for script tags in layout
  response.headers.set('x-nonce', nonce);

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
