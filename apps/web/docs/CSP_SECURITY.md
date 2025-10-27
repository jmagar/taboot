# Content-Security-Policy (CSP) Implementation

## Overview

Taboot implements **strict Content-Security-Policy (CSP) headers** with nonce-based script authorization to prevent XSS attacks and unauthorized script execution. This is a critical defense-in-depth layer protecting against code injection vulnerabilities.

## CSP Policy

### Directives

```text
default-src 'self'
  → Only allow resources from same origin by default

script-src 'self' 'nonce-{random}' https://app.posthog.com https://vercel.live https://*.sentry.io
  → Scripts must be same-origin, include nonce, or from trusted analytics/monitoring services

style-src 'self' 'unsafe-inline'
  → Tailwind CSS requires unsafe-inline (no way around this with dynamic styles)
  → Styles from same origin or inline

img-src 'self' data: https:
  → Images from same origin, data URIs, or HTTPS

font-src 'self' data:
  → Fonts from same origin or data URIs

connect-src 'self' https://*.posthog.com https://*.sentry.io https://*.ingest.sentry.io
  → API calls to same origin, PostHog, and Sentry

frame-ancestors 'none'
  → Prevent clickjacking (app cannot be embedded in iframes)

base-uri 'self'
  → Prevent <base> tag injection

form-action 'self'
  → Forms submit only to same origin

upgrade-insecure-requests
  → Upgrade HTTP to HTTPS automatically
```

## Implementation Details

### Nonce Generation

Nonce (number used once) is a random value generated per request in `apps/web/middleware.ts`:

```typescript
const nonce = Buffer.from(crypto.getRandomValues(new Uint8Array(16))).toString('base64');
```

- **Uniqueness**: Each request gets a unique nonce
- **Randomness**: Cryptographically secure random bytes
- **Size**: 16 bytes = 128 bits entropy (sufficient for one-time use)

### Nonce Propagation

1. **Middleware** (`middleware.ts`): Generates nonce, sets `x-nonce` header
2. **Layout** (`app/layout.tsx`): Reads nonce from headers using `headers()`
3. **CSPScripts Component** (`components/csp-scripts.tsx`): Passes nonce to script tags

### Analytics & Monitoring

All external scripts include the nonce to bypass CSP restrictions:

#### PostHog Analytics

```typescript
<script nonce={nonce} dangerouslySetInnerHTML={{...}} />
```

#### Sentry Error Tracking

```typescript
<script nonce={nonce} src="https://browser.sentry-cdn.com/..." />
```

#### Vercel Analytics

```typescript
<script nonce={nonce} src="/_vercel/insights/script.js" />
```

## Security Considerations

### Style-src 'unsafe-inline'

**Why**: Tailwind CSS requires dynamic inline styles (no way to avoid without major refactor)

**Risk**: Moderate - CSP still prevents script-based XSS via `script-src` restrictions

**Alternatives** (not used):
- Pre-generate all CSS (defeats Tailwind's benefits)
- Hash-based CSP (requires build step for all inline styles)
- Nonces for styles (Tailwind doesn't support this pattern)

### Trusted Domains

Only essential analytics/monitoring services allowed:
- **PostHog**: Product analytics (configurable)
- **Sentry**: Error tracking (configurable)
- **Vercel**: Performance monitoring (on Vercel deployments)

### Testing CSP Compliance

1. **Browser DevTools**: Check "CSP" warnings in Console
2. **CSP Report-Only** (future): Add report-uri endpoint to log violations
3. **Automated Scanning**: OWASP ZAP, Mozilla Observatory

## Common Issues

### Inline Style Errors

**Error**: `Content-Security-Policy: inline styles not allowed`

**Solution**:
- Styles with nonce: `<style nonce={nonce}>...</style>`
- Tailwind: Already handled by `style-src 'unsafe-inline'`

### Third-Party Script Errors

**Error**: `Content-Security-Policy: script blocked from https://example.com`

**Solution**:
- Add domain to `script-src` directive
- Or include nonce in `<script>` tag
- Review necessity of external script

### Form Submission Errors

**Error**: `Content-Security-Policy: form submit blocked`

**Solution**: Ensure form action is same origin (default for Next.js apps)

## Monitoring

### CSP Violations

When violations occur:
1. Browser blocks the resource
2. Logs to browser DevTools Console (in report-only mode)
3. Could be sent to report-uri endpoint (not configured yet)

### Performance Impact

- **Minimal**: Nonce generation ~1ms per request
- **Negligible**: Header size increase (~100 bytes)
- **Zero**: No runtime performance impact

## References

- [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [MDN CSP Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Next.js Security Headers](https://nextjs.org/docs/advanced-features/security-headers)
- [Content-Security-Policy Spec](https://w3c.github.io/webappsec-csp/)

## Future Improvements

- [ ] CSP report-uri endpoint for violation monitoring
- [ ] CSP report-only mode during development
- [ ] Hash-based CSP for additional inline style safety
- [ ] Frame-ancestors report for clickjacking attempts
- [ ] Periodic CSP compliance audits
