# @taboot/auth

Authentication package for Taboot using Better Auth.

## Modules

### Core Authentication (`server.ts`)

Better Auth server instance with database adapter, email verification, two-factor authentication, and social providers.

### Edge-Compatible Session Validation (`edge.ts`)

Edge runtime-compatible JWT session verification for use in middleware without database calls.

**Use case:** Next.js middleware running in edge runtime needs to validate sessions without database access.

**Implementation:**
- Uses `jose` library for JWE decryption (same as Better Auth)
- Validates cryptographic signature
- Checks token expiry
- Validates required claims (userId, sessionId)
- Never throws - returns `Session | null`

**Example:**

```typescript
import { verifySession } from '@taboot/auth/edge';

export async function middleware(request: NextRequest) {
  const session = await verifySession({
    sessionToken: request.cookies.get('better-auth.session_token')?.value,
    secret: process.env.AUTH_SECRET!,
  });

  if (!session?.user) {
    return NextResponse.redirect(new URL('/sign-in', request.url));
  }

  return NextResponse.next();
}
```

## Exports

- `@taboot/auth` - Main exports (client + server)
- `@taboot/auth/client` - Client-side auth helpers
- `@taboot/auth/server` - Server-side auth instance
- `@taboot/auth/edge` - Edge-compatible session validation
- `@taboot/auth/types` - TypeScript type definitions
- `@taboot/auth/next-handlers` - Next.js API route handlers
- `@taboot/auth/node-handlers` - Node.js/Express handlers

## Security

### Session Validation in Edge Runtime

The `verifySession` function provides **defense-in-depth** session validation:

1. **Cryptographic verification** - JWE decryption with secret key
2. **Expiry validation** - Rejects expired tokens
3. **Claim validation** - Requires userId and sessionId
4. **Fail-closed** - Returns null on any error (never throws)

**Important:** This is for **read-only validation** in middleware. State-changing operations should still verify sessions against the database using `auth.api.getSession()`.

### Better Auth Cookie Cache

Better Auth uses cookie caching when `session.cookieCache.enabled` is true:

- Short-lived signed JWE cookies (5 minutes default)
- Database remains source of truth
- Cookie refreshed on each request
- Automatic invalidation on sign-out

The edge validation function uses the same JWE decryption as Better Auth's cookie cache.

## Testing

**Note:** Unit tests are in `src/__tests__/edge.test.ts` but require ESM configuration to run with Jest. The implementation is validated via TypeScript type-checking.

To validate the implementation:

```bash
pnpm --filter @taboot/auth run check-types
```

## Dependencies

- `better-auth` - Core authentication framework
- `jose` - JWT/JWE cryptography (edge-compatible)
- `@taboot/db` - Prisma database client
- `@taboot/email` - Email sending (verification, password reset)
- `@taboot/rate-limit` - Rate limiting for auth endpoints
- `@taboot/logger` - Structured logging
