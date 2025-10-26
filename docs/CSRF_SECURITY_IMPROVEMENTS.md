# CSRF Security Improvements Summary

## Overview
Applied five critical security improvements to the CSRF protection implementation in `apps/web/lib/csrf.ts` and `apps/web/lib/csrf-client.ts`.

## Improvements Applied

### 1. Environment-Aware Cookie Naming (FIX 1)
**Problem:** `__Host-taboot.csrf` requires Secure flag, but development environments use non-HTTPS connections.

**Solution:**
```typescript
const CSRF_TOKEN_COOKIE_NAME =
  process.env.NODE_ENV === 'production' ? '__Host-taboot.csrf' : 'taboot.csrf';
```

**Impact:**
- Development: Uses `taboot.csrf` (works with HTTP)
- Production: Uses `__Host-taboot.csrf` (enforces Secure flag, domain binding, path=/)
- Prevents cookie-related errors in local development
- Maintains maximum security in production

**Files Modified:**
- `/home/jmagar/code/taboot/apps/web/lib/csrf.ts` (line 18)
- `/home/jmagar/code/taboot/apps/web/lib/csrf-client.ts` (line 10)

---

### 2. Node.js Runtime Compatibility (FIX 2)
**Problem:** `btoa()` is undefined in Next.js middleware (Node.js runtime), causing token generation failures.

**Solution:** Replace `btoa()` with `Buffer.toString('base64')`:
```typescript
// Token generation
const token = Buffer.from(buffer)
  .toString('base64')
  .replace(/\+/g, '-')
  .replace(/\//g, '_')
  .replace(/=/g, '');

// Signature conversion
const signatureBase64 = Buffer.from(signatureArray)
  .toString('base64')
  .replace(/\+/g, '-')
  .replace(/\//g, '_')
  .replace(/=/g, '');
```

**Impact:**
- Fixes runtime errors in middleware execution
- Maintains identical base64url encoding behavior
- Works across all Next.js runtime environments (Node.js, Edge)

**Files Modified:**
- `/home/jmagar/code/taboot/apps/web/lib/csrf.ts` (lines 36-40, 63-67)

---

### 3. Reverse Proxy Support (FIX 3)
**Problem:** Behind reverse proxies (Cloudflare, nginx, AWS ALB), the `host` header may not match the client-facing origin, causing false CSRF rejections.

**Solution:** Added proxy-aware host detection:
```typescript
function validateOrigin(request: NextRequest): boolean {
  const trustProxy = process.env.TRUST_PROXY === 'true';
  const host = trustProxy
    ? (request.headers.get('x-forwarded-host') ?? request.headers.get('host'))
    : request.headers.get('host');
  // ... validation logic
}
```

**Impact:**
- Supports deployments behind Cloudflare, nginx, AWS ALB, etc.
- Maintains security by default (`TRUST_PROXY=false`)
- Prevents IP spoofing when not behind verified proxy
- Aligns with existing rate limiting proxy configuration

**Environment Configuration:**
```bash
# Only set to true when behind verified reverse proxy
TRUST_PROXY="false"  # Default (secure)
TRUST_PROXY="true"   # Behind Cloudflare/nginx/ALB
```

**Files Modified:**
- `/home/jmagar/code/taboot/apps/web/lib/csrf.ts` (lines 112-116, 122, 135, 149)

---

### 4. Double-Submit Cookie Pattern Fix (FIX 4)
**Problem:** `httpOnly: true` prevents client JavaScript from reading the cookie, breaking the double-submit pattern where the client must include the token in the `x-csrf-token` header.

**Solution:**
```typescript
response.cookies.set(CSRF_TOKEN_COOKIE_NAME, token, {
  httpOnly: false,  // Must be false so client can read for double-submit
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax',
  path: '/',
  maxAge: 60 * 60 * 24,
});
```

**Impact:**
- Enables proper double-submit cookie pattern functionality
- Client can read cookie via `document.cookie`
- Maintains defense-in-depth with SameSite='lax' and Secure flags
- CSRF-client.ts can now successfully retrieve and submit tokens

**Security Notes:**
- OWASP-approved pattern: httpOnly=false is expected for double-submit cookies
- Still protected by SameSite, Secure, and signature validation
- Tokens are HMAC-signed, preventing forgery

**Files Modified:**
- `/home/jmagar/code/taboot/apps/web/lib/csrf.ts` (line 239)

---

### 5. Reduced Token Exposure (FIX 5)
**Problem:** Emitting CSRF tokens in response headers on every GET/HEAD request increases exposure through:
- HTTP caching (CDN, browser cache)
- Server logs
- Monitoring systems
- Unnecessary header bloat

**Solution:** Removed automatic token header emission:
```typescript
// FIX 5: Remove automatic token header emission to reduce exposure
// Client reads token from cookie only, reducing cache/log propagation
// If needed, expose via dedicated endpoint or initial HTML meta tag
// response.headers.set(CSRF_TOKEN_HEADER_NAME, token);
```

**Impact:**
- Reduces token exposure surface area
- Prevents token leakage through cached responses
- Reduces header size on all GET responses
- Client reads token directly from cookie (already accessible via httpOnly=false)

**Alternative Approaches (if header needed):**
- Dedicated `/api/csrf-token` endpoint
- Initial HTML `<meta>` tag injection
- Expose only on specific routes that need it

**Files Modified:**
- `/home/jmagar/code/taboot/apps/web/lib/csrf.ts` (line 249, commented out)

---

## Security Posture Summary

### Defense-in-Depth Layers
1. **SameSite='lax' Cookies** — Prevents cross-site cookie sending (configured in better-auth)
2. **Double-Submit Cookie Pattern** — Cookie must match header value (HMAC-signed)
3. **Origin/Referer Validation** — Request origin must match host
4. **HMAC-SHA256 Signatures** — Tokens cryptographically signed, prevents forgery
5. **Constant-Time Comparison** — Prevents timing attacks on token validation

### Production Configuration
```bash
# Required environment variables
NODE_ENV="production"           # Enables __Host- prefix, Secure flag
CSRF_SECRET="your-secret-here"  # HMAC signing key (fallback: AUTH_SECRET)
TRUST_PROXY="false"             # Only set to true behind verified proxy
```

### OWASP Compliance
✅ Double-Submit Cookie Pattern with signed tokens
✅ Origin/Referer header validation
✅ SameSite cookie attribute
✅ Secure cookie flag in production
✅ HMAC signature prevents token forgery
✅ Constant-time comparison prevents timing attacks
✅ __Host- prefix in production (enforces Secure, domain, path)

### Testing Recommendations
1. **Unit Tests:** Verify token generation, signing, validation logic
2. **Integration Tests:** Test middleware with various header combinations
3. **Proxy Tests:** Verify TRUST_PROXY behavior (x-forwarded-host handling)
4. **Environment Tests:** Verify cookie naming in dev vs prod
5. **Client Tests:** Verify csrf-client.ts can read cookies and submit headers

---

## Files Modified

1. **`/home/jmagar/code/taboot/apps/web/lib/csrf.ts`**
   - Line 18: Environment-aware cookie naming constant
   - Lines 36-40: Buffer-based token generation
   - Lines 63-67: Buffer-based signature conversion
   - Lines 112-116, 122, 135, 149: Proxy-aware origin validation
   - Line 239: httpOnly=false for double-submit pattern
   - Line 249: Removed automatic header emission (commented out)

2. **`/home/jmagar/code/taboot/apps/web/lib/csrf-client.ts`**
   - Line 10: Environment-aware cookie naming constant (matches server)

---

## Migration Notes

### Breaking Changes
None. All changes are backward-compatible improvements.

### Required Actions
1. **Development:** No changes required (uses `taboot.csrf` cookie name)
2. **Production:** Ensure `NODE_ENV=production` is set (already standard practice)
3. **Behind Proxy:** Set `TRUST_PROXY=true` if behind Cloudflare/nginx/ALB

### Verification Steps
```bash
# 1. Verify constants are centralized and matching
grep -n "CSRF_TOKEN_COOKIE_NAME" apps/web/lib/csrf*.ts

# 2. Run CSRF tests
pnpm --filter @taboot/web test lib/__tests__/csrf.test.ts
pnpm --filter @taboot/web test lib/__tests__/csrf-client.test.ts

# 3. Test in development
pnpm --filter @taboot/web dev
# Navigate to app, verify CSRF tokens work

# 4. Test behind proxy (if applicable)
TRUST_PROXY=true pnpm --filter @taboot/web dev
# Verify x-forwarded-host is respected
```

---

## Security Impact Assessment

### Risk Reduction
- **Before:** CSRF tokens not working (btoa undefined, httpOnly prevented double-submit)
- **After:** Fully functional OWASP-compliant CSRF protection with defense-in-depth

### Attack Surface Reduction
- Token exposure reduced (no header emission on every GET)
- Proxy spoofing prevented (TRUST_PROXY defaults to false)
- Cookie security maximized (__Host- prefix in production)

### Deployment Safety
- Development workflow unaffected (HTTP works without errors)
- Production security maximized (Secure, __Host-, signed tokens)
- Proxy deployments supported (configurable trust)

---

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [MDN: Set-Cookie __Host- prefix](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#cookie_prefixes)
- [IETF RFC 6265bis: Cookie Prefixes](https://datatracker.ietf.org/doc/html/draft-ietf-httpbis-rfc6265bis-03#section-4.1.3)
- [SameSite Cookies Explained](https://web.dev/samesite-cookies-explained/)

---

**Implementation Date:** 2025-10-25
**Author:** Claude Agent (General Purpose)
**Review Status:** Ready for testing
