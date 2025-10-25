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
    const isExcluded = csrfExcludedRoutes.some((route) => pathname.startsWith(route));
    if (!isExcluded) {
      const csrfResponse = await csrfMiddleware(request);
      // If CSRF check failed (403), return the error response
      if (csrfResponse.status === 403) {
        return csrfResponse;
      }
      // If CSRF check passed for GET requests, it may have set cookies/headers
      if (request.method === 'GET' || request.method === 'HEAD' || request.method === 'OPTIONS') {
        // Continue with auth checks but preserve CSRF cookies/headers
        request = new NextRequest(request.url, {
          headers: request.headers,
        });
        // Note: We'll apply CSRF response headers after auth checks
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

  // For API routes, apply CSRF token to response headers
  if (pathname.startsWith('/api') && (request.method === 'GET' || request.method === 'HEAD' || request.method === 'OPTIONS')) {
    const response = NextResponse.next();
    const csrfResponse = await csrfMiddleware(request);

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

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
