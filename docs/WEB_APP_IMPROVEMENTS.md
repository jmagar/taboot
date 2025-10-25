# Web App Improvement Implementation Plan

**Generated:** 2025-10-24
**Status:** Planning Phase
**Target:** apps/web Next.js application

## Executive Summary

This document outlines a comprehensive improvement plan for the Taboot web application based on architectural analysis. The plan addresses 13 identified issues across security, performance, developer experience, and user experience, prioritized by impact and implementation complexity.

---

## Critical Priority (Week 1-2)

### 1. Server-Side Authentication Enforcement

**Problem:** Protected routes rely on client-side redirect hooks (`useRequiredAuthUser`), which can be bypassed by disabling JavaScript or manipulating client state.

**Current Implementation:**
- Location: `apps/web/hooks/use-auth-user.ts:51-58`
- Method: Client-side `useEffect` redirects after page load
- Vulnerability: Pages render before auth check completes

**Solution:** Implement Next.js middleware for server-side authentication

**Implementation Steps:**

1. **Create middleware.ts**
   ```typescript
   // apps/web/middleware.ts
   import { NextResponse } from 'next/server';
   import type { NextRequest } from 'next/server';
   import { auth } from '@taboot/auth';

   const protectedRoutes = ['/dashboard', '/profile', '/settings'];
   const authRoutes = ['/sign-in', '/sign-up', '/forgot-password'];

   export async function middleware(request: NextRequest) {
     const pathname = request.nextUrl.pathname;

     // Check if route requires authentication
     const isProtected = protectedRoutes.some(route =>
       pathname.startsWith(route)
     );
     const isAuthRoute = authRoutes.some(route =>
       pathname.startsWith(route)
     );

     // Get session from request
     const session = await auth.api.getSession({
       headers: request.headers
     });

     const isAuthenticated = !!session?.user;

     // Redirect unauthenticated users from protected routes
     if (isProtected && !isAuthenticated) {
       const signInUrl = new URL('/sign-in', request.url);
       signInUrl.searchParams.set('callbackUrl', pathname);
       return NextResponse.redirect(signInUrl);
     }

     // Redirect authenticated users from auth routes
     if (isAuthRoute && isAuthenticated) {
       return NextResponse.redirect(new URL('/dashboard', request.url));
     }

     return NextResponse.next();
   }

   export const config = {
     matcher: [
       '/((?!api|_next/static|_next/image|favicon.ico).*)',
     ],
   };
   ```

2. **Simplify client-side hooks** (remove redirect logic, keep state only)
3. **Add session preloading** in protected layouts
4. **Test bypass scenarios** (JS disabled, token tampering)

**Files Modified:**
- `apps/web/middleware.ts` (create)
- `apps/web/hooks/use-auth-user.ts` (simplify)
- `apps/web/app/(default)/layout.tsx` (add session preload)

**Testing:**
- Verify redirect on unauthenticated access
- Test callback URL preservation
- Confirm authenticated users can't access auth pages
- Validate JS-disabled browser handling

**Impact:** Eliminates primary security vulnerability, adds defense-in-depth

---

### 2. Error Boundaries Implementation

**Problem:** No error boundaries exist in the application. Unhandled errors crash the entire app instead of providing graceful degradation.

**Current State:**
- No `error.tsx` files in route tree
- Client errors propagate to root, white screen
- No error reporting/logging

**Solution:** Add error boundaries at strategic layout levels

**Implementation Steps:**

1. **Root error boundary**
   ```typescript
   // apps/web/app/error.tsx
   'use client';

   import { useEffect } from 'react';
   import { Button } from '@taboot/ui/components/button';
   import { logger } from '@/lib/logger';

   export default function RootError({
     error,
     reset,
   }: {
     error: Error & { digest?: string };
     reset: () => void;
   }) {
     useEffect(() => {
       logger.error('Root error boundary caught error', {
         error: error.message,
         digest: error.digest,
         stack: error.stack
       });
     }, [error]);

     return (
       <div className="flex min-h-screen items-center justify-center p-4">
         <div className="max-w-md space-y-4 text-center">
           <h1 className="text-2xl font-bold">Something went wrong</h1>
           <p className="text-muted-foreground">
             We encountered an unexpected error. Please try again.
           </p>
           {error.digest && (
             <p className="text-sm text-muted-foreground">
               Error ID: {error.digest}
             </p>
           )}
           <div className="flex gap-2 justify-center">
             <Button onClick={reset}>Try Again</Button>
             <Button variant="outline" onClick={() => window.location.href = '/'}>
               Go Home
             </Button>
           </div>
         </div>
       </div>
     );
   }
   ```

2. **Auth group error boundary**
   ```typescript
   // apps/web/app/(auth)/error.tsx
   'use client';

   import { useEffect } from 'react';
   import { Button } from '@taboot/ui/components/button';
   import { logger } from '@/lib/logger';

   export default function AuthError({
     error,
     reset,
   }: {
     error: Error & { digest?: string };
     reset: () => void;
   }) {
     useEffect(() => {
       logger.error('Auth error boundary caught error', {
         error: error.message,
         digest: error.digest
       });
     }, [error]);

     return (
       <div className="flex min-h-screen items-center justify-center p-4">
         <div className="max-w-md space-y-4 text-center">
           <h1 className="text-2xl font-bold">Authentication Error</h1>
           <p className="text-muted-foreground">
             We couldn't process your authentication request. Please try again.
           </p>
           <div className="flex gap-2 justify-center">
             <Button onClick={reset}>Try Again</Button>
             <Button variant="outline" onClick={() => window.location.href = '/sign-in'}>
               Back to Sign In
             </Button>
           </div>
         </div>
       </div>
     );
   }
   ```

3. **Protected routes error boundary**
   ```typescript
   // apps/web/app/(default)/error.tsx
   'use client';

   import { useEffect } from 'react';
   import { Button } from '@taboot/ui/components/button';
   import { logger } from '@/lib/logger';

   export default function ProtectedError({
     error,
     reset,
   }: {
     error: Error & { digest?: string };
     reset: () => void;
   }) {
     useEffect(() => {
       logger.error('Protected route error', {
         error: error.message,
         digest: error.digest
       });
     }, [error]);

     return (
       <div className="flex items-center justify-center p-8">
         <div className="max-w-md space-y-4 text-center">
           <h2 className="text-xl font-bold">Something went wrong</h2>
           <p className="text-muted-foreground">
             We encountered an error loading this page.
           </p>
           <Button onClick={reset}>Try Again</Button>
         </div>
       </div>
     );
   }
   ```

4. **Global error handler** (for unhandled promises)
   ```typescript
   // apps/web/app/layout.tsx (add to Providers)
   useEffect(() => {
     const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
       logger.error('Unhandled promise rejection', {
         reason: event.reason
       });
     };

     window.addEventListener('unhandledrejection', handleUnhandledRejection);
     return () => {
       window.removeEventListener('unhandledrejection', handleUnhandledRejection);
     };
   }, []);
   ```

**Files Created:**
- `apps/web/app/error.tsx`
- `apps/web/app/(auth)/error.tsx`
- `apps/web/app/(default)/error.tsx`

**Files Modified:**
- `apps/web/components/providers.tsx` (add global error handler)

**Testing:**
- Trigger errors at different levels (root, auth, protected)
- Verify error boundaries catch and display appropriately
- Confirm reset functionality works
- Test error logging reaches logger

**Impact:** Prevents white screens, improves user experience during errors, enables error tracking

---

### 3. Rate Limiting for Auth Endpoints

**Problem:** Password and auth API routes lack rate limiting, vulnerable to brute force attacks and credential stuffing.

**Current Implementation:**
- Location: `apps/web/app/api/auth/password/route.ts`
- No request throttling
- Unlimited password attempts

**Solution:** Add rate limiting using Upstash Redis (already in stack)

**Implementation Steps:**

1. **Install rate limiting library**
   ```bash
   pnpm add @upstash/ratelimit @upstash/redis
   ```

2. **Create rate limiter utility**
   ```typescript
   // apps/web/lib/rate-limit.ts
   import { Ratelimit } from '@upstash/ratelimit';
   import { Redis } from '@upstash/redis';

   const redis = new Redis({
     url: process.env.UPSTASH_REDIS_REST_URL!,
     token: process.env.UPSTASH_REDIS_REST_TOKEN!,
   });

   // 5 requests per 10 minutes per IP for password operations
   export const passwordRateLimit = new Ratelimit({
     redis,
     limiter: Ratelimit.slidingWindow(5, '10 m'),
     prefix: 'ratelimit:password',
   });

   // 10 requests per minute per IP for auth operations
   export const authRateLimit = new Ratelimit({
     redis,
     limiter: Ratelimit.slidingWindow(10, '1 m'),
     prefix: 'ratelimit:auth',
   });

   // Helper to get client identifier (IP or user ID)
   export function getClientIdentifier(req: Request): string {
     const forwarded = req.headers.get('x-forwarded-for');
     const ip = forwarded ? forwarded.split(',')[0] :
                req.headers.get('x-real-ip') || 'unknown';
     return ip;
   }
   ```

3. **Add rate limiting middleware wrapper**
   ```typescript
   // apps/web/lib/with-rate-limit.ts
   import { NextResponse } from 'next/server';
   import { Ratelimit } from '@upstash/ratelimit';
   import { getClientIdentifier } from './rate-limit';
   import { logger } from './logger';

   export function withRateLimit(
     handler: (req: Request) => Promise<NextResponse>,
     ratelimit: Ratelimit
   ) {
     return async (req: Request) => {
       const identifier = getClientIdentifier(req);

       try {
         const { success, limit, remaining, reset } =
           await ratelimit.limit(identifier);

         if (!success) {
           logger.warn('Rate limit exceeded', {
             identifier,
             limit,
             reset
           });

           return NextResponse.json(
             { error: 'Too many requests. Please try again later.' },
             {
               status: 429,
               headers: {
                 'X-RateLimit-Limit': limit.toString(),
                 'X-RateLimit-Remaining': remaining.toString(),
                 'X-RateLimit-Reset': reset.toString(),
               }
             }
           );
         }

         const response = await handler(req);

         // Add rate limit headers to successful responses
         response.headers.set('X-RateLimit-Limit', limit.toString());
         response.headers.set('X-RateLimit-Remaining', remaining.toString());
         response.headers.set('X-RateLimit-Reset', reset.toString());

         return response;
       } catch (error) {
         logger.error('Rate limit check failed', { error });
         // Fail open - allow request but log error
         return handler(req);
       }
     };
   }
   ```

4. **Apply to password endpoints**
   ```typescript
   // apps/web/app/api/auth/password/route.ts
   import { passwordRateLimit } from '@/lib/rate-limit';
   import { withRateLimit } from '@/lib/with-rate-limit';

   async function handleGET(req: Request) {
     // ... existing GET logic
   }

   async function handlePOST(req: Request) {
     // ... existing POST logic
   }

   export const GET = withRateLimit(handleGET, passwordRateLimit);
   export const POST = withRateLimit(handlePOST, passwordRateLimit);
   ```

5. **Apply to other sensitive endpoints**
   - Sign in/up routes
   - Password reset
   - 2FA verification

6. **Add environment variables** to `.env.example`
   ```bash
   UPSTASH_REDIS_REST_URL=
   UPSTASH_REDIS_REST_TOKEN=
   ```

**Files Created:**
- `apps/web/lib/rate-limit.ts`
- `apps/web/lib/with-rate-limit.ts`

**Files Modified:**
- `apps/web/app/api/auth/password/route.ts`
- `apps/web/app/api/auth/[...all]/route.ts` (if applicable)
- `apps/web/.env.example`

**Testing:**
- Verify rate limits trigger after threshold
- Test rate limit headers in responses
- Confirm 429 status codes
- Validate per-IP and per-user tracking
- Test rate limit reset timing

**Impact:** Protects against brute force attacks, reduces abuse potential

---

## High Priority (Week 2-3)

### 4. Convert Pages to Server Components

**Problem:** All protected pages use `'use client'` directive, losing SSR benefits: slower TTFB, poor SEO, larger JS bundles.

**Current Implementation:**
- `apps/web/app/(default)/dashboard/page.tsx:1` - Client component
- Auth check happens after hydration
- Entire React Query tree sent to client

**Solution:** Convert to Server Components with server-side session checks

**Implementation Steps:**

1. **Create server-side session utility**
   ```typescript
   // apps/web/lib/auth-server.ts
   import { auth } from '@taboot/auth';
   import { cookies, headers } from 'next/headers';
   import { redirect } from 'next/navigation';

   export async function getServerSession() {
     const session = await auth.api.getSession({
       headers: await headers(),
     });
     return session;
   }

   export async function requireServerSession() {
     const session = await getServerSession();

     if (!session?.user) {
       redirect('/sign-in');
     }

     return session;
   }
   ```

2. **Convert dashboard to Server Component**
   ```typescript
   // apps/web/app/(default)/dashboard/page.tsx
   import { requireServerSession } from '@/lib/auth-server';
   import { Suspense } from 'react';
   import DashboardLoading from './loading';

   async function DashboardContent() {
     const session = await requireServerSession();

     return (
       <section className="max-w-2xl p-12">
         <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>
         <div className="rounded-md py-4">
           <p>
             <span>Welcome back, </span>
             <span className="font-bold">
               {session.user.name || session.user.email}
             </span>!
           </p>
         </div>
       </section>
     );
   }

   export default function DashboardPage() {
     return (
       <Suspense fallback={<DashboardLoading />}>
         <DashboardContent />
       </Suspense>
     );
   }
   ```

3. **Update profile page** (similar pattern)
4. **Update settings pages** (similar pattern)
5. **Extract interactive components** (buttons, forms) as separate Client Components
6. **Configure caching** for session data
   ```typescript
   // Add to server session utility
   export async function getServerSession() {
     const session = await auth.api.getSession({
       headers: await headers(),
     });
     return session;
   }

   // Cache for 5 minutes
   export const getServerSessionCached = unstable_cache(
     getServerSession,
     ['server-session'],
     { revalidate: 300 }
   );
   ```

**Files Created:**
- `apps/web/lib/auth-server.ts`

**Files Modified:**
- `apps/web/app/(default)/dashboard/page.tsx`
- `apps/web/app/(default)/profile/page.tsx`
- `apps/web/app/(default)/(settings)/settings/*/page.tsx`
- Extract interactive portions to separate client components

**Testing:**
- Verify SSR renders correctly
- Test session redirect on server
- Confirm no hydration mismatches
- Validate caching behavior
- Measure TTFB improvement

**Impact:** 2-3x faster initial page loads, improved SEO, reduced bundle size

---

### 5. Comprehensive Caching Strategy

**Problem:** API calls lack proper caching beyond default 5-minute React Query cache. Repeated fetches on navigation.

**Current Implementation:**
- `apps/web/hooks/use-has-password.ts:1-17` - 5min staleTime only
- No ISR or SSG for static content
- No HTTP caching headers

**Solution:** Implement tiered caching strategy

**Implementation Steps:**

1. **Configure React Query defaults**
   ```typescript
   // apps/web/components/providers.tsx
   const queryClient = new QueryClient({
     defaultOptions: {
       queries: {
         staleTime: 5 * 60 * 1000, // 5 minutes
         gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
         refetchOnWindowFocus: false,
         refetchOnReconnect: true,
         retry: 1,
       },
     },
   });
   ```

2. **Create query key factory**
   ```typescript
   // apps/web/lib/query-keys.ts
   export const queryKeys = {
     auth: {
       all: ['auth'] as const,
       session: () => [...queryKeys.auth.all, 'session'] as const,
       hasPassword: () => [...queryKeys.auth.all, 'hasPassword'] as const,
     },
     user: {
       all: ['user'] as const,
       profile: (id: string) => [...queryKeys.user.all, 'profile', id] as const,
     },
   };
   ```

3. **Add resource-specific cache configs**
   ```typescript
   // apps/web/hooks/use-has-password.ts
   import { queryKeys } from '@/lib/query-keys';

   export function useHasPassword() {
     return useQuery({
       queryKey: queryKeys.auth.hasPassword(),
       queryFn: async () => {
         const response = await api.get('/api/auth/password');
         if (response.error) throw new Error(response.error.message);
         return response.data;
       },
       staleTime: 30 * 60 * 1000, // 30 minutes (changes infrequently)
       gcTime: 60 * 60 * 1000, // 1 hour
     });
   }
   ```

4. **Add API route caching headers**
   ```typescript
   // apps/web/app/api/auth/password/route.ts
   export async function GET(req: Request) {
     try {
       // ... existing logic

       return NextResponse.json(
         { hasPassword },
         {
           headers: {
             'Cache-Control': 'private, max-age=300, stale-while-revalidate=600',
           },
         }
       );
     } catch (error) {
       // ... error handling
     }
   }
   ```

5. **Configure Next.js caching**
   ```typescript
   // apps/web/next.config.mjs
   const nextConfig = {
     transpilePackages: ['@taboot/ui'],
     output: 'standalone',

     // Add caching config
     async headers() {
       return [
         {
           source: '/api/:path*',
           headers: [
             {
               key: 'Cache-Control',
               value: 'private, no-cache, must-revalidate',
             },
           ],
         },
       ];
     },
   };
   ```

6. **Implement prefetching** for common routes
   ```typescript
   // apps/web/app/(default)/layout.tsx
   async function PrefetchData() {
     const queryClient = getQueryClient();

     await queryClient.prefetchQuery({
       queryKey: queryKeys.auth.hasPassword(),
       queryFn: async () => {
         const response = await api.get('/api/auth/password');
         if (response.error) throw new Error(response.error.message);
         return response.data;
       },
     });

     return null;
   }
   ```

7. **Add cache invalidation** on mutations
   ```typescript
   // apps/web/components/password-form.tsx
   const setPasswordMutation = useMutation({
     mutationFn: async (newPassword: string) => {
       // ... mutation logic
     },
     onSuccess: () => {
       // Invalidate relevant queries
       queryClient.invalidateQueries({
         queryKey: queryKeys.auth.hasPassword()
       });
       queryClient.invalidateQueries({
         queryKey: queryKeys.auth.session()
       });
     },
   });
   ```

**Files Created:**
- `apps/web/lib/query-keys.ts`

**Files Modified:**
- `apps/web/components/providers.tsx`
- `apps/web/hooks/use-has-password.ts`
- `apps/web/app/api/auth/password/route.ts`
- `apps/web/next.config.mjs`
- `apps/web/components/password-form.tsx`
- `apps/web/app/(default)/layout.tsx`

**Testing:**
- Verify cache hits in React Query devtools
- Test cache invalidation on mutations
- Confirm HTTP cache headers
- Measure reduced backend requests
- Test stale-while-revalidate behavior

**Impact:** Reduced backend load, faster perceived performance, better UX

---

### 6. Font Optimization

**Problem:** Geist fonts loaded without `display: swap`, causing FOIT (Flash of Invisible Text) on slow connections.

**Current Implementation:**
- Location: `apps/web/app/layout.tsx:14-22`
- No display strategy specified

**Solution:** Add `display: 'swap'` to font configs

**Implementation:**

```typescript
// apps/web/app/layout.tsx
const fontSans = Geist({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap', // Add this
});

const fontMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap', // Add this
});
```

**Files Modified:**
- `apps/web/app/layout.tsx`

**Testing:**
- Throttle network in DevTools
- Verify text renders immediately with fallback font
- Confirm font swap occurs smoothly
- Measure LCP improvement

**Impact:** Eliminates FOIT, improves LCP, better perceived performance

---

## Medium Priority (Week 3-4)

### 7. Testing Infrastructure

**Problem:** Zero test coverage, no test configs, no CI validation.

**Solution:** Add Vitest + Testing Library, prioritize auth flows and API client

**Implementation Steps:**

1. **Install testing dependencies**
   ```bash
   pnpm add -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
   ```

2. **Create Vitest config**
   ```typescript
   // apps/web/vitest.config.ts
   import { defineConfig } from 'vitest/config';
   import react from '@vitejs/plugin-react';
   import path from 'path';

   export default defineConfig({
     plugins: [react()],
     test: {
       environment: 'jsdom',
       setupFiles: ['./vitest.setup.ts'],
       include: ['**/*.{test,spec}.{ts,tsx}'],
       coverage: {
         provider: 'v8',
         reporter: ['text', 'json', 'html'],
         exclude: [
           'node_modules/',
           '.next/',
           'vitest.config.ts',
           '**/*.config.{ts,js}',
         ],
       },
     },
     resolve: {
       alias: {
         '@': path.resolve(__dirname, './'),
       },
     },
   });
   ```

3. **Create setup file**
   ```typescript
   // apps/web/vitest.setup.ts
   import '@testing-library/jest-dom';
   import { cleanup } from '@testing-library/react';
   import { afterEach, vi } from 'vitest';

   // Cleanup after each test
   afterEach(() => {
     cleanup();
   });

   // Mock Next.js router
   vi.mock('next/navigation', () => ({
     useRouter() {
       return {
         push: vi.fn(),
         replace: vi.fn(),
         prefetch: vi.fn(),
         back: vi.fn(),
       };
     },
     usePathname() {
       return '/';
     },
     useSearchParams() {
       return new URLSearchParams();
     },
   }));

   // Mock environment variables
   process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
   process.env.NEXT_PUBLIC_BASE_URL = 'http://localhost:3000';
   ```

4. **Add test utilities**
   ```typescript
   // apps/web/test/utils.tsx
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
   import { render, RenderOptions } from '@testing-library/react';
   import { ReactElement } from 'react';

   export function createTestQueryClient() {
     return new QueryClient({
       defaultOptions: {
         queries: {
           retry: false,
           gcTime: 0,
         },
       },
     });
   }

   interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
     queryClient?: QueryClient;
   }

   export function renderWithProviders(
     ui: ReactElement,
     { queryClient = createTestQueryClient(), ...options }: CustomRenderOptions = {}
   ) {
     return render(
       <QueryClientProvider client={queryClient}>
         {ui}
       </QueryClientProvider>,
       options
     );
   }
   ```

5. **Write initial tests**

   **API Client Tests:**
   ```typescript
   // apps/web/lib/api.test.ts
   import { describe, it, expect, beforeEach, vi } from 'vitest';
   import { api } from './api';

   describe('TabootAPIClient', () => {
     beforeEach(() => {
       global.fetch = vi.fn();
     });

     it('should make GET requests with correct URL', async () => {
       (global.fetch as any).mockResolvedValueOnce({
         ok: true,
         json: async () => ({ data: 'test' }),
       });

       await api.get('/health');

       expect(global.fetch).toHaveBeenCalledWith(
         'http://localhost:8000/health',
         expect.objectContaining({
           method: 'GET',
           credentials: 'include',
         })
       );
     });

     it('should handle errors correctly', async () => {
       (global.fetch as any).mockResolvedValueOnce({
         ok: false,
         status: 500,
         json: async () => ({ error: 'Server error' }),
       });

       const response = await api.get('/health');

       expect(response.error).toBeDefined();
     });
   });
   ```

   **Auth Hook Tests:**
   ```typescript
   // apps/web/hooks/use-auth-user.test.tsx
   import { describe, it, expect, vi } from 'vitest';
   import { renderHook, waitFor } from '@testing-library/react';
   import { useAuthUser } from './use-auth-user';
   import * as authClient from '@taboot/auth/client';

   vi.mock('@taboot/auth/client');

   describe('useAuthUser', () => {
     it('should return null user when not authenticated', async () => {
       vi.mocked(authClient.useSession).mockReturnValue({
         data: null,
         isPending: false,
         error: null,
         refetch: vi.fn(),
       });

       const { result } = renderHook(() => useAuthUser());

       await waitFor(() => {
         expect(result.current.user).toBeNull();
         expect(result.current.isAuthenticated).toBe(false);
       });
     });

     it('should return user when authenticated', async () => {
       const mockUser = { id: '1', email: 'test@example.com', name: 'Test' };

       vi.mocked(authClient.useSession).mockReturnValue({
         data: { user: mockUser, session: {} },
         isPending: false,
         error: null,
         refetch: vi.fn(),
       });

       const { result } = renderHook(() => useAuthUser());

       await waitFor(() => {
         expect(result.current.user).toEqual(mockUser);
         expect(result.current.isAuthenticated).toBe(true);
       });
     });
   });
   ```

   **Component Tests:**
   ```typescript
   // apps/web/components/credentials-form.test.tsx
   import { describe, it, expect, vi } from 'vitest';
   import { render, screen, waitFor } from '@testing-library/react';
   import userEvent from '@testing-library/user-event';
   import { renderWithProviders } from '@/test/utils';
   import CredentialsForm from './credentials-form';

   describe('CredentialsForm', () => {
     it('should render email and password fields', () => {
       renderWithProviders(<CredentialsForm type="sign-in" />);

       expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
       expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
     });

     it('should validate email format', async () => {
       const user = userEvent.setup();
       renderWithProviders(<CredentialsForm type="sign-in" />);

       const emailInput = screen.getByLabelText(/email/i);
       await user.type(emailInput, 'invalid-email');
       await user.tab();

       await waitFor(() => {
         expect(screen.getByText(/valid email/i)).toBeInTheDocument();
       });
     });

     it('should validate password length', async () => {
       const user = userEvent.setup();
       renderWithProviders(<CredentialsForm type="sign-in" />);

       const passwordInput = screen.getByLabelText(/password/i);
       await user.type(passwordInput, 'short');
       await user.tab();

       await waitFor(() => {
         expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
       });
     });
   });
   ```

6. **Add package.json scripts**
   ```json
   {
     "scripts": {
       "test": "vitest",
       "test:ui": "vitest --ui",
       "test:coverage": "vitest --coverage",
       "test:ci": "vitest run --coverage"
     }
   }
   ```

7. **Add GitHub Actions workflow**
   ```yaml
   # .github/workflows/web-test.yml
   name: Web App Tests

   on:
     pull_request:
       paths:
         - 'apps/web/**'
         - 'packages-ts/**'
     push:
       branches: [main]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: pnpm/action-setup@v2
           with:
             version: 9
         - uses: actions/setup-node@v4
           with:
             node-version: '20'
             cache: 'pnpm'
         - run: pnpm install
         - run: pnpm --filter=web test:ci
         - uses: codecov/codecov-action@v3
           with:
             files: ./apps/web/coverage/coverage-final.json
   ```

**Files Created:**
- `apps/web/vitest.config.ts`
- `apps/web/vitest.setup.ts`
- `apps/web/test/utils.tsx`
- `apps/web/lib/api.test.ts`
- `apps/web/hooks/use-auth-user.test.tsx`
- `apps/web/components/credentials-form.test.tsx`
- `.github/workflows/web-test.yml`

**Files Modified:**
- `apps/web/package.json`

**Testing Priority:**
1. Auth flows (sign in, sign up, password reset)
2. API client
3. Critical user paths (dashboard, profile, settings)
4. Form validation
5. Error boundaries

**Impact:** Catch regressions, enable confident refactoring, improve code quality

---

### 8. Type Safety for API Routes

**Problem:** API routes return raw JSON without schema validation. Runtime type errors possible.

**Current Implementation:**
- `apps/web/app/api/auth/password/route.ts:27,96` - Untyped responses
- No OpenAPI schema integration

**Solution:** Generate types from FastAPI OpenAPI schema, use Zod for validation

**Implementation Steps:**

1. **Install dependencies**
   ```bash
   pnpm add zod openapi-typescript
   pnpm add -D @hey-api/openapi-ts
   ```

2. **Generate TypeScript types from FastAPI OpenAPI**
   ```bash
   # Generate types from running API
   npx openapi-typescript http://localhost:8000/openapi.json -o apps/web/lib/api-types.ts
   ```

3. **Add generation script**
   ```json
   // apps/web/package.json
   {
     "scripts": {
       "generate:api-types": "openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts",
       "dev": "npm run generate:api-types && next dev --turbo"
     }
   }
   ```

4. **Create typed API client wrapper**
   ```typescript
   // apps/web/lib/api-typed.ts
   import { api } from './api';
   import type { paths } from './api-types';

   type ApiResponse<T> = {
     data: T;
     error: null;
   } | {
     data: null;
     error: { message: string; status: number };
   };

   export const apiTyped = {
     async get<P extends keyof paths>(
       path: P
     ): Promise<ApiResponse<paths[P]['get']['responses'][200]['content']['application/json']>> {
       const response = await api.get(path as string);
       return response as any;
     },

     async post<P extends keyof paths>(
       path: P,
       body: paths[P]['post']['requestBody']['content']['application/json']
     ): Promise<ApiResponse<paths[P]['post']['responses'][200]['content']['application/json']>> {
       const response = await api.post(path as string, body);
       return response as any;
     },

     // ... put, delete, etc.
   };
   ```

5. **Create Zod schemas for local API routes**
   ```typescript
   // apps/web/lib/schemas/auth.ts
   import { z } from 'zod';

   export const hasPasswordResponseSchema = z.object({
     hasPassword: z.boolean(),
   });

   export const setPasswordRequestSchema = z.object({
     newPassword: z.string().min(8).max(100),
   });

   export const setPasswordResponseSchema = z.object({
     message: z.string(),
   });

   export const errorResponseSchema = z.object({
     error: z.string(),
   });

   export type HasPasswordResponse = z.infer<typeof hasPasswordResponseSchema>;
   export type SetPasswordRequest = z.infer<typeof setPasswordRequestSchema>;
   export type SetPasswordResponse = z.infer<typeof setPasswordResponseSchema>;
   export type ErrorResponse = z.infer<typeof errorResponseSchema>;
   ```

6. **Update API routes with validation**
   ```typescript
   // apps/web/app/api/auth/password/route.ts
   import {
     hasPasswordResponseSchema,
     setPasswordRequestSchema,
     setPasswordResponseSchema,
     errorResponseSchema
   } from '@/lib/schemas/auth';

   export async function GET(req: Request) {
     try {
       // ... existing logic

       const response = hasPasswordResponseSchema.parse({ hasPassword });
       return NextResponse.json(response);
     } catch (error) {
       logger.error('Error checking password status', { error });
       const errorResponse = errorResponseSchema.parse({
         error: 'Internal server error'
       });
       return NextResponse.json(errorResponse, { status: 500 });
     }
   }

   export async function POST(req: Request) {
     try {
       // ... auth check

       const body = await req.json();
       const validated = setPasswordRequestSchema.parse(body);

       // ... rest of logic

       const response = setPasswordResponseSchema.parse({
         message: 'Password set successfully'
       });
       return NextResponse.json(response);
     } catch (error) {
       if (error instanceof z.ZodError) {
         const errorResponse = errorResponseSchema.parse({
           error: error.errors[0].message
         });
         return NextResponse.json(errorResponse, { status: 400 });
       }
       logger.error('Error setting password', { error });
       const errorResponse = errorResponseSchema.parse({
         error: 'Internal server error'
       });
       return NextResponse.json(errorResponse, { status: 500 });
     }
   }
   ```

7. **Update hooks to use typed schemas**
   ```typescript
   // apps/web/hooks/use-has-password.ts
   import { hasPasswordResponseSchema } from '@/lib/schemas/auth';

   export function useHasPassword() {
     return useQuery({
       queryKey: queryKeys.auth.hasPassword(),
       queryFn: async () => {
         const response = await api.get('/api/auth/password');
         if (response.error) throw new Error(response.error.message);

         // Validate response shape
         return hasPasswordResponseSchema.parse(response.data);
       },
       staleTime: 30 * 60 * 1000,
     });
   }
   ```

**Files Created:**
- `apps/web/lib/api-types.ts` (generated)
- `apps/web/lib/api-typed.ts`
- `apps/web/lib/schemas/auth.ts`
- `apps/web/lib/schemas/user.ts`

**Files Modified:**
- `apps/web/package.json`
- `apps/web/app/api/auth/password/route.ts`
- `apps/web/hooks/use-has-password.ts`
- Other API routes and hooks

**Testing:**
- Verify schema validation catches invalid data
- Test error messages for validation failures
- Confirm TypeScript catches type mismatches
- Validate generated types match FastAPI

**Impact:** Eliminate runtime type errors, better DX, catch bugs at compile time

---

### 9. Service Layer Extraction

**Problem:** Direct Prisma queries in API routes mix data access with HTTP layer, violating separation of concerns.

**Current Implementation:**
- `apps/web/app/api/auth/password/route.ts:15-23` - Prisma in route handler
- Duplicate queries across endpoints

**Solution:** Extract to service layer with repository pattern

**Implementation Steps:**

1. **Create service structure**
   ```typescript
   // apps/web/services/auth.service.ts
   import { prisma } from '@taboot/db';
   import { auth } from '@taboot/auth';
   import { logger } from '@/lib/logger';

   export class AuthService {
     async hasPassword(userId: string): Promise<boolean> {
       try {
         const account = await prisma.account.findFirst({
           where: {
             userId,
             providerId: 'credential',
           },
           select: {
             password: true,
           },
         });

         return !!account?.password;
       } catch (error) {
         logger.error('Failed to check password status', { userId, error });
         throw new Error('Failed to check password status');
       }
     }

     async setPassword(userId: string, newPassword: string): Promise<void> {
       try {
         // Check if user already has password
         const existingAccount = await prisma.account.findFirst({
           where: {
             userId,
             providerId: 'credential',
           },
         });

         if (existingAccount?.password) {
           throw new Error('Password already exists');
         }

         // Use Better Auth's setPassword method
         // This would need to be adapted to your auth setup
         await auth.api.setPassword({
           body: { newPassword },
           // Additional context needed
         });
       } catch (error) {
         logger.error('Failed to set password', { userId, error });
         throw error;
       }
     }

     async changePassword(
       userId: string,
       currentPassword: string,
       newPassword: string
     ): Promise<void> {
       try {
         // Verify current password
         // Change to new password
         // Implementation depends on Better Auth API
       } catch (error) {
         logger.error('Failed to change password', { userId, error });
         throw error;
       }
     }
   }

   // Singleton instance
   export const authService = new AuthService();
   ```

2. **Update API routes to use service**
   ```typescript
   // apps/web/app/api/auth/password/route.ts
   import { authService } from '@/services/auth.service';
   import { hasPasswordResponseSchema, setPasswordRequestSchema } from '@/lib/schemas/auth';

   export async function GET(req: Request) {
     try {
       const session = await auth.api.getSession({ headers: req.headers });
       if (!session?.user) {
         return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
       }

       const hasPassword = await authService.hasPassword(session.user.id);

       const response = hasPasswordResponseSchema.parse({ hasPassword });
       return NextResponse.json(response);
     } catch (error) {
       logger.error('Error checking password status', { error });
       return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
     }
   }

   export async function POST(req: Request) {
     try {
       const session = await auth.api.getSession({ headers: req.headers });
       if (!session?.user) {
         return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
       }

       const body = await req.json();
       const { newPassword } = setPasswordRequestSchema.parse(body);

       await authService.setPassword(session.user.id, newPassword);

       return NextResponse.json({ message: 'Password set successfully' });
     } catch (error) {
       if (error instanceof Error && error.message === 'Password already exists') {
         return NextResponse.json({ error: error.message }, { status: 400 });
       }
       logger.error('Error setting password', { error });
       return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
     }
   }
   ```

3. **Create user service**
   ```typescript
   // apps/web/services/user.service.ts
   import { prisma } from '@taboot/db';
   import { logger } from '@/lib/logger';

   export class UserService {
     async getUserProfile(userId: string) {
       try {
         return await prisma.user.findUnique({
           where: { id: userId },
           select: {
             id: true,
             email: true,
             name: true,
             image: true,
             createdAt: true,
             updatedAt: true,
           },
         });
       } catch (error) {
         logger.error('Failed to get user profile', { userId, error });
         throw new Error('Failed to get user profile');
       }
     }

     async updateUserProfile(userId: string, data: { name?: string; image?: string }) {
       try {
         return await prisma.user.update({
           where: { id: userId },
           data,
           select: {
             id: true,
             email: true,
             name: true,
             image: true,
             updatedAt: true,
           },
         });
       } catch (error) {
         logger.error('Failed to update user profile', { userId, error });
         throw new Error('Failed to update user profile');
       }
     }

     async deleteUser(userId: string): Promise<void> {
       try {
         await prisma.user.delete({
           where: { id: userId },
         });
       } catch (error) {
         logger.error('Failed to delete user', { userId, error });
         throw new Error('Failed to delete user');
       }
     }
   }

   export const userService = new UserService();
   ```

4. **Add service tests**
   ```typescript
   // apps/web/services/auth.service.test.ts
   import { describe, it, expect, vi, beforeEach } from 'vitest';
   import { authService } from './auth.service';
   import { prisma } from '@taboot/db';

   vi.mock('@taboot/db', () => ({
     prisma: {
       account: {
         findFirst: vi.fn(),
       },
     },
   }));

   describe('AuthService', () => {
     beforeEach(() => {
       vi.clearAllMocks();
     });

     describe('hasPassword', () => {
       it('should return true when account has password', async () => {
         vi.mocked(prisma.account.findFirst).mockResolvedValue({
           id: '1',
           userId: 'user-1',
           providerId: 'credential',
           password: 'hashed-password',
         } as any);

         const result = await authService.hasPassword('user-1');

         expect(result).toBe(true);
         expect(prisma.account.findFirst).toHaveBeenCalledWith({
           where: {
             userId: 'user-1',
             providerId: 'credential',
           },
           select: {
             password: true,
           },
         });
       });

       it('should return false when account has no password', async () => {
         vi.mocked(prisma.account.findFirst).mockResolvedValue(null);

         const result = await authService.hasPassword('user-1');

         expect(result).toBe(false);
       });

       it('should throw error on database failure', async () => {
         vi.mocked(prisma.account.findFirst).mockRejectedValue(
           new Error('Database error')
         );

         await expect(authService.hasPassword('user-1')).rejects.toThrow(
           'Failed to check password status'
         );
       });
     });
   });
   ```

**Files Created:**
- `apps/web/services/auth.service.ts`
- `apps/web/services/user.service.ts`
- `apps/web/services/auth.service.test.ts`
- `apps/web/services/user.service.test.ts`

**Files Modified:**
- `apps/web/app/api/auth/password/route.ts`
- Other API routes using direct Prisma

**Testing:**
- Unit test services with mocked Prisma
- Integration test with test database
- Verify error handling
- Test transaction rollback

**Impact:** Improved reusability, testability, maintainability

---

### 10. Loading States Everywhere

**Problem:** Only dashboard and profile have loading.tsx files. Other routes flash empty or broken content during navigation.

**Current Implementation:**
- `apps/web/app/(default)/dashboard/loading.tsx` exists
- `apps/web/app/(default)/profile/loading.tsx` exists
- Settings routes missing loading states

**Solution:** Add loading.tsx to all route segments or use Suspense boundaries

**Implementation Steps:**

1. **Create reusable loading components**
   ```typescript
   // apps/web/components/loading-states.tsx
   import { Skeleton } from '@taboot/ui/components/skeleton';

   export function PageHeaderLoading() {
     return (
       <div className="space-y-2">
         <Skeleton className="h-8 w-64" />
         <Skeleton className="h-4 w-96" />
       </div>
     );
   }

   export function CardLoading() {
     return (
       <div className="rounded-lg border p-6 space-y-4">
         <Skeleton className="h-6 w-48" />
         <Skeleton className="h-4 w-full" />
         <Skeleton className="h-4 w-3/4" />
       </div>
     );
   }

   export function FormLoading() {
     return (
       <div className="space-y-4">
         <div className="space-y-2">
           <Skeleton className="h-4 w-24" />
           <Skeleton className="h-10 w-full" />
         </div>
         <div className="space-y-2">
           <Skeleton className="h-4 w-24" />
           <Skeleton className="h-10 w-full" />
         </div>
         <Skeleton className="h-10 w-32" />
       </div>
     );
   }

   export function SettingsLoading() {
     return (
       <div className="max-w-2xl space-y-8 p-12">
         <PageHeaderLoading />
         <CardLoading />
         <CardLoading />
       </div>
     );
   }
   ```

2. **Add loading states to settings routes**
   ```typescript
   // apps/web/app/(default)/(settings)/settings/general/loading.tsx
   import { SettingsLoading } from '@/components/loading-states';

   export default function GeneralSettingsLoading() {
     return <SettingsLoading />;
   }
   ```

   ```typescript
   // apps/web/app/(default)/(settings)/settings/security/loading.tsx
   import { SettingsLoading } from '@/components/loading-states';

   export default function SecuritySettingsLoading() {
     return <SettingsLoading />;
   }
   ```

3. **Add loading state to auth pages**
   ```typescript
   // apps/web/app/(auth)/sign-in/loading.tsx
   import { FormLoading } from '@/components/loading-states';

   export default function SignInLoading() {
     return (
       <div className="flex min-h-screen items-center justify-center p-4">
         <div className="w-full max-w-md space-y-6">
           <div className="text-center">
             <Skeleton className="h-8 w-48 mx-auto" />
           </div>
           <FormLoading />
         </div>
       </div>
     );
   }
   ```

4. **Add Suspense boundaries in layouts**
   ```typescript
   // apps/web/app/(default)/layout.tsx
   import { Suspense } from 'react';
   import { AppSidebar } from '@/components/app-sidebar';
   import { SidebarProvider } from '@taboot/ui/components/sidebar';

   export default function ProtectedLayout({
     children,
   }: {
     children: React.ReactNode;
   }) {
     return (
       <SidebarProvider>
         <div className="flex h-screen w-full">
           <Suspense fallback={<SidebarLoading />}>
             <AppSidebar />
           </Suspense>
           <main className="flex-1 overflow-auto">
             <Suspense fallback={<PageLoading />}>
               {children}
             </Suspense>
           </main>
         </div>
       </SidebarProvider>
     );
   }

   function SidebarLoading() {
     return (
       <div className="w-64 border-r p-4 space-y-4">
         <Skeleton className="h-10 w-full" />
         <Skeleton className="h-8 w-full" />
         <Skeleton className="h-8 w-full" />
       </div>
     );
   }

   function PageLoading() {
     return (
       <div className="p-12">
         <PageHeaderLoading />
       </div>
     );
   }
   ```

5. **Add streaming with Suspense in Server Components**
   ```typescript
   // apps/web/app/(default)/dashboard/page.tsx
   import { Suspense } from 'react';
   import { requireServerSession } from '@/lib/auth-server';
   import { CardLoading } from '@/components/loading-states';

   async function WelcomeCard() {
     const session = await requireServerSession();

     return (
       <div className="rounded-md py-4">
         <p>
           <span>Welcome back, </span>
           <span className="font-bold">
             {session.user.name || session.user.email}
           </span>!
         </p>
       </div>
     );
   }

   async function DashboardStats() {
     // Slow async data fetch
     const stats = await fetchUserStats();

     return (
       <div className="grid grid-cols-3 gap-4">
         {/* Stats cards */}
       </div>
     );
   }

   export default function DashboardPage() {
     return (
       <section className="max-w-2xl p-12 space-y-8">
         <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>

         <Suspense fallback={<CardLoading />}>
           <WelcomeCard />
         </Suspense>

         <Suspense fallback={<CardLoading />}>
           <DashboardStats />
         </Suspense>
       </section>
     );
   }
   ```

**Files Created:**
- `apps/web/components/loading-states.tsx`
- `apps/web/app/(default)/(settings)/settings/general/loading.tsx`
- `apps/web/app/(default)/(settings)/settings/security/loading.tsx`
- `apps/web/app/(auth)/sign-in/loading.tsx`
- `apps/web/app/(auth)/sign-up/loading.tsx`

**Files Modified:**
- `apps/web/app/(default)/layout.tsx`
- `apps/web/app/(default)/dashboard/page.tsx`

**Testing:**
- Throttle network in DevTools
- Navigate between routes, verify loading states
- Test Suspense streaming with slow data fetches
- Confirm no content flash

**Impact:** Smoother UX during navigation, perceived performance improvement

---

## Nice-to-Have (Week 5+)

### 11. Analytics & Observability

**Problem:** No error tracking, performance monitoring, or user analytics.

**Solution:** Add Sentry (errors), Vercel Analytics (performance), PostHog (product analytics)

**Implementation Steps:**

1. **Install Sentry**
   ```bash
   pnpm add @sentry/nextjs
   npx @sentry/wizard@latest -i nextjs
   ```

2. **Configure Sentry**
   ```typescript
   // sentry.client.config.ts
   import * as Sentry from '@sentry/nextjs';

   Sentry.init({
     dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
     environment: process.env.NODE_ENV,
     tracesSampleRate: 0.1,
     debug: false,
     replaysOnErrorSampleRate: 1.0,
     replaysSessionSampleRate: 0.1,
     integrations: [
       new Sentry.BrowserTracing(),
       new Sentry.Replay({
         maskAllText: true,
         blockAllMedia: true,
       }),
     ],
   });
   ```

   ```typescript
   // sentry.server.config.ts
   import * as Sentry from '@sentry/nextjs';

   Sentry.init({
     dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
     environment: process.env.NODE_ENV,
     tracesSampleRate: 0.1,
     debug: false,
   });
   ```

3. **Add Vercel Analytics**
   ```bash
   pnpm add @vercel/analytics
   ```

   ```typescript
   // apps/web/app/layout.tsx
   import { Analytics } from '@vercel/analytics/react';

   export default function RootLayout({ children }) {
     return (
       <html>
         <body>
           {children}
           <Analytics />
         </body>
       </html>
     );
   }
   ```

4. **Add PostHog**
   ```bash
   pnpm add posthog-js
   ```

   ```typescript
   // apps/web/lib/posthog.ts
   import posthog from 'posthog-js';

   export function initPostHog() {
     if (typeof window !== 'undefined') {
       posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
         api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
         loaded: (posthog) => {
           if (process.env.NODE_ENV === 'development') posthog.debug();
         },
       });
     }
   }
   ```

   ```typescript
   // apps/web/components/providers.tsx
   import { useEffect } from 'react';
   import { initPostHog } from '@/lib/posthog';

   export function Providers({ children }) {
     useEffect(() => {
       initPostHog();
     }, []);

     return (
       // ... existing providers
     );
   }
   ```

5. **Add custom tracking**
   ```typescript
   // apps/web/lib/analytics.ts
   import posthog from 'posthog-js';

   export const analytics = {
     track: (event: string, properties?: Record<string, any>) => {
       posthog.capture(event, properties);
     },
     identify: (userId: string, traits?: Record<string, any>) => {
       posthog.identify(userId, traits);
     },
     page: () => {
       posthog.capture('$pageview');
     },
   };
   ```

**Files Created:**
- `sentry.client.config.ts`
- `sentry.server.config.ts`
- `apps/web/lib/posthog.ts`
- `apps/web/lib/analytics.ts`

**Files Modified:**
- `apps/web/app/layout.tsx`
- `apps/web/components/providers.tsx`
- `apps/web/.env.example`

**Impact:** Data-driven optimization, proactive bug fixing, user insights

---

### 12. Accessibility Improvements

**Problem:** No focus management, minimal ARIA attributes, keyboard navigation untested.

**Solution:** Add focus management, audit with axe-devtools, test keyboard-only

**Implementation Steps:**

1. **Install accessibility tools**
   ```bash
   pnpm add -D @axe-core/react eslint-plugin-jsx-a11y
   ```

2. **Add axe in development**
   ```typescript
   // apps/web/components/providers.tsx
   import { useEffect } from 'react';

   export function Providers({ children }) {
     useEffect(() => {
       if (process.env.NODE_ENV === 'development') {
         import('@axe-core/react').then((axe) => {
           axe.default(React, ReactDOM, 1000);
         });
       }
     }, []);

     return (
       // ... providers
     );
   }
   ```

3. **Update ESLint config**
   ```typescript
   // apps/web/eslint.config.js
   import jsxA11y from 'eslint-plugin-jsx-a11y';

   export default [
     // ... existing config
     {
       plugins: {
         'jsx-a11y': jsxA11y,
       },
       rules: {
         ...jsxA11y.configs.recommended.rules,
       },
     },
   ];
   ```

4. **Add focus trap for modals**
   ```typescript
   // apps/web/hooks/use-focus-trap.ts
   import { useEffect, useRef } from 'react';

   export function useFocusTrap(isActive: boolean) {
     const ref = useRef<HTMLDivElement>(null);

     useEffect(() => {
       if (!isActive || !ref.current) return;

       const element = ref.current;
       const focusableElements = element.querySelectorAll(
         'a[href], button:not([disabled]), textarea, input, select'
       );
       const firstElement = focusableElements[0] as HTMLElement;
       const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

       firstElement?.focus();

       function handleKeyDown(e: KeyboardEvent) {
         if (e.key !== 'Tab') return;

         if (e.shiftKey) {
           if (document.activeElement === firstElement) {
             lastElement?.focus();
             e.preventDefault();
           }
         } else {
           if (document.activeElement === lastElement) {
             firstElement?.focus();
             e.preventDefault();
           }
         }
       }

       element.addEventListener('keydown', handleKeyDown);
       return () => element.removeEventListener('keydown', handleKeyDown);
     }, [isActive]);

     return ref;
   }
   ```

5. **Add skip link**
   ```typescript
   // apps/web/components/skip-link.tsx
   export function SkipLink() {
     return (
       <a
         href="#main-content"
         className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground"
       >
         Skip to main content
       </a>
     );
   }
   ```

   ```typescript
   // apps/web/app/layout.tsx
   import { SkipLink } from '@/components/skip-link';

   export default function RootLayout({ children }) {
     return (
       <html lang="en">
         <body>
           <SkipLink />
           {/* ... rest */}
         </body>
       </html>
     );
   }
   ```

6. **Add ARIA labels**
   ```typescript
   // Update components with missing labels
   <button aria-label="Close dialog">
     <X className="h-4 w-4" />
   </button>

   <nav aria-label="Main navigation">
     {/* navigation items */}
   </nav>

   <form aria-labelledby="form-title">
     {/* form fields */}
   </form>
   ```

7. **Add live regions for notifications**
   ```typescript
   // apps/web/components/toast-provider.tsx
   <div
     role="region"
     aria-live="polite"
     aria-label="Notifications"
   >
     <Toaster />
   </div>
   ```

**Files Created:**
- `apps/web/hooks/use-focus-trap.ts`
- `apps/web/components/skip-link.tsx`

**Files Modified:**
- `apps/web/eslint.config.js`
- `apps/web/components/providers.tsx`
- `apps/web/app/layout.tsx`
- Various components (add ARIA labels)

**Testing:**
- Keyboard-only navigation
- Screen reader testing (NVDA, JAWS)
- axe-devtools audit
- Lighthouse accessibility score

**Impact:** WCAG compliance, broader user reach, better SEO

---

### 13. Mobile Optimization

**Problem:** Responsive breakpoints exist but mobile-first design untested on actual devices.

**Solution:** Test on real devices, optimize touch targets, improve mobile UX

**Implementation Steps:**

1. **Audit touch targets** (minimum 44x44px)
   ```typescript
   // Update buttons with small touch areas
   <Button
     size="icon"
     className="h-11 w-11" // Ensure min 44px
   >
     <Icon />
   </Button>
   ```

2. **Add mobile-specific navigation**
   ```typescript
   // apps/web/components/mobile-nav.tsx
   'use client';

   import { Sheet, SheetContent, SheetTrigger } from '@taboot/ui/components/sheet';
   import { Menu } from 'lucide-react';

   export function MobileNav() {
     return (
       <Sheet>
         <SheetTrigger asChild>
           <Button
             variant="ghost"
             size="icon"
             className="md:hidden"
             aria-label="Open menu"
           >
             <Menu className="h-6 w-6" />
           </Button>
         </SheetTrigger>
         <SheetContent side="left" className="w-80">
           {/* Navigation items */}
         </SheetContent>
       </Sheet>
     );
   }
   ```

3. **Optimize viewport settings**
   ```typescript
   // apps/web/config/viewport.ts
   export const viewportConfig = {
     width: 'device-width',
     initialScale: 1,
     maximumScale: 5, // Allow zoom for accessibility
     userScalable: true,
   };
   ```

4. **Add mobile-optimized forms**
   ```typescript
   // Use appropriate input types
   <Input
     type="email"
     inputMode="email"
     autoComplete="email"
   />

   <Input
     type="tel"
     inputMode="tel"
     autoComplete="tel"
   />

   <Input
     type="number"
     inputMode="numeric"
     pattern="[0-9]*"
   />
   ```

5. **Test on actual devices**
   - iOS Safari (iPhone 12, 13, 14)
   - Android Chrome (Pixel, Samsung)
   - Tablet sizes (iPad, Android tablets)

6. **Add viewport debugging**
   ```typescript
   // apps/web/components/viewport-debug.tsx (dev only)
   'use client';

   export function ViewportDebug() {
     if (process.env.NODE_ENV !== 'development') return null;

     return (
       <div className="fixed bottom-4 right-4 bg-black/80 text-white px-2 py-1 text-xs rounded z-50">
         <div className="block sm:hidden">xs</div>
         <div className="hidden sm:block md:hidden">sm</div>
         <div className="hidden md:block lg:hidden">md</div>
         <div className="hidden lg:block xl:hidden">lg</div>
         <div className="hidden xl:block">xl</div>
       </div>
     );
   }
   ```

**Files Created:**
- `apps/web/components/mobile-nav.tsx`
- `apps/web/components/viewport-debug.tsx`

**Files Modified:**
- `apps/web/config/viewport.ts`
- Various form components (input types)
- Buttons with small touch targets

**Testing:**
- BrowserStack real device testing
- Chrome DevTools device emulation
- Touch target size validation
- Form input on mobile keyboards
- Scroll behavior and gestures

**Impact:** Better mobile conversion, improved mobile UX, higher engagement

---

## Testing Strategy

### Unit Tests (Vitest)
- Services (auth, user)
- Utilities (query keys, rate limiting)
- Hooks (auth, data fetching)
- Components (forms, buttons)

### Integration Tests
- API routes with test database
- Auth flows end-to-end
- Form submissions with validation

### E2E Tests (Playwright - Future)
- Critical user journeys
- Auth flows
- Settings management
- Cross-browser compatibility

---

## Deployment Checklist

### Before Implementing
- [ ] Review and adjust priorities based on product needs
- [ ] Set up staging environment
- [ ] Configure error tracking (Sentry)
- [ ] Set up monitoring dashboards

### During Implementation
- [ ] Write tests for each feature
- [ ] Review code with security lens
- [ ] Update documentation
- [ ] Test on real devices (mobile)

### Before Production
- [ ] Run full test suite
- [ ] Perform accessibility audit
- [ ] Load test critical endpoints
- [ ] Security audit (rate limiting, auth)
- [ ] Performance profiling
- [ ] Review error boundaries
- [ ] Validate caching behavior
- [ ] Test middleware edge cases

---

## Success Metrics

### Security
- Zero unauthorized access attempts successful
- <1% rate limit violations
- 100% auth routes protected at server level

### Performance
- TTFB <200ms (p95)
- LCP <2.5s (p75)
- INP <200ms (p75)
- 0 hydration errors

### Reliability
- Error rate <0.1%
- 99.9% uptime
- <10s error resolution (via boundaries)

### Developer Experience
- >80% test coverage
- <5min full test suite
- Zero TypeScript errors
- 100% type-safe API calls

---

## Rollback Plan

Each improvement is independent and can be rolled back individually:

1. **Middleware**: Remove middleware.ts, restore client hooks
2. **Error boundaries**: Remove error.tsx files
3. **Rate limiting**: Remove rate limit wrapper from routes
4. **Server Components**: Re-add 'use client' directives
5. **Service layer**: Inline Prisma calls back into routes

Git tags at each major milestone for easy rollback.

---

## Notes

- Breaking changes acceptable (single-user system)
- Database wipes OK for schema changes
- Focus on implementation speed over backwards compatibility
- Iterate based on real usage patterns
- Security improvements non-negotiable
- Performance improvements high ROI
