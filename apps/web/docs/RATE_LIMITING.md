# Rate Limiting Implementation

## Overview

Rate limiting has been implemented for authentication endpoints using Upstash Redis and the `@upstash/ratelimit` library. This prevents abuse and protects against brute-force attacks.

## Architecture

### Core Components

1. **`apps/web/lib/rate-limit.ts`**
   - Creates Redis connection using Upstash credentials
   - Defines rate limiters with sliding window algorithm
   - Implements client IP extraction

2. **`apps/web/lib/with-rate-limit.ts`**
   - Higher-order function wrapper for route handlers
   - Adds rate limit checks before handler execution
   - Returns 429 responses when limits exceeded
   - Injects rate limit headers into all responses
   - Fails open on errors (allows requests but logs issues)

3. **`apps/web/app/api/auth/password/route.ts`**
   - Updated to use rate limiting on GET and POST handlers
   - Protected against password enumeration and brute-force

## Rate Limits

### Password Endpoints

- **Limit**: 5 requests per 10 minutes
- **Prefix**: `ratelimit:password`
- **Algorithm**: Sliding window
- **Applied to**:
  - `GET /api/auth/password` (check if user has password)
  - `POST /api/auth/password` (set new password)

### General Auth Endpoints

- **Limit**: 10 requests per 1 minute
- **Prefix**: `ratelimit:auth`
- **Algorithm**: Sliding window
- **Applied to**: (extensible to other auth endpoints)

## Client Identification

The system identifies clients using IP addresses extracted from request headers:

1. **Primary**: `x-forwarded-for` header (first IP in comma-separated list)
2. **Fallback**: `x-real-ip` header
3. **Default**: `'unknown'` if no headers present

This works with reverse proxies (nginx, Cloudflare, etc.) that inject these headers.

## Response Headers

All responses include rate limit information:

```text
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 2025-10-25T12:34:56.789Z
```


- **X-RateLimit-Limit**: Maximum requests allowed in the window
- **X-RateLimit-Remaining**: Requests remaining in current window
- **X-RateLimit-Reset**: ISO 8601 timestamp when limit resets

## Rate Limit Exceeded Response

When limits are exceeded, the API returns:

```json
{
  "error": "Too many requests. Please try again later.",
  "retryAfter": "2025-10-25T12:34:56.789Z"
}
```

**Status Code**: `429 Too Many Requests`

## Error Handling

The implementation follows a **fail-open** strategy:

- If Redis is unavailable or rate limit check fails, the request is **allowed**
- Errors are logged with full context
- This prevents rate limiting issues from breaking authentication for legitimate users

Example log on failure:

```json
{
  "level": "error",
  "message": "Rate limit check failed, failing open",
  "timestamp": "2025-10-25T12:34:56.789Z",
  "meta": {
    "error": { "name": "...", "message": "...", "stack": "..." },
    "identifier": "192.168.1.1",
    "path": "/api/auth/password"
  }
}
```

## Configuration

### Environment Variables

Add to `.env.local`:

```env
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token-here
```


**Required**: Both variables must be set or the application will throw an error at startup.

### Upstash Setup

1. Create account at [upstash.com](https://upstash.com)
2. Create a Redis database (choose region close to your deployment)
3. Copy REST URL and token from dashboard
4. Add to `.env` file

## Usage in Other Endpoints

To add rate limiting to other routes:

```typescript
import { authRateLimit } from '@/lib/rate-limit';
import { withRateLimit } from '@/lib/with-rate-limit';
import { NextResponse } from 'next/server';

async function handlePOST(req: Request) {
  // Your handler logic
  return NextResponse.json({ success: true });
}

// Export wrapped handler
export const POST = withRateLimit(handlePOST, authRateLimit);
```

## Testing

### Manual Testing

1. **Test rate limit threshold**:

   ```bash
   # Send 6 requests in quick succession
   for i in {1..6}; do
     curl -X POST http://localhost:3000/api/auth/password \
       -H "Content-Type: application/json" \
       -H "Cookie: your-session-cookie" \
       -d '{"newPassword":"testpass123"}' \
       -i
   done
   ```

2. **Verify headers**:

   ```bash
   curl -X GET http://localhost:3000/api/auth/password \
     -H "Cookie: your-session-cookie" \
     -i | grep X-RateLimit
   ```

3. **Test different IPs**:

   ```bash
   # Simulate different clients
   curl -X GET http://localhost:3000/api/auth/password \
     -H "x-forwarded-for: 192.168.1.1" \
     -H "Cookie: your-session-cookie"

   curl -X GET http://localhost:3000/api/auth/password \
     -H "x-forwarded-for: 192.168.1.2" \
     -H "Cookie: your-session-cookie"
   ```

### Unit Tests

Tests are located in `apps/web/lib/__tests__/rate-limit.test.ts`

Run tests:

```bash
cd apps/web
pnpm test lib/__tests__/rate-limit.test.ts
```


## Monitoring

### Log Analysis

Rate limit violations are logged with the following structure:

```json
{
  "level": "warn",
  "message": "Rate limit exceeded",
  "timestamp": "2025-10-25T12:34:56.789Z",
  "meta": {
    "identifier": "192.168.1.1",
    "limit": 5,
    "remaining": 0,
    "reset": "2025-10-25T12:44:56.789Z",
    "path": "/api/auth/password"
  }
}
```


### Upstash Analytics

Upstash provides built-in analytics:
- Request counts per identifier
- Hit/miss ratios
- Window statistics

Access via Upstash dashboard → Your Database → Analytics

## Security Considerations

1. **IP Spoofing**: Trust proxy headers (`x-forwarded-for`) only when behind a trusted reverse proxy
2. **Distributed Attacks**: Rate limits are per-IP; distributed attacks from many IPs may bypass limits
3. **Legitimate Users**: Fail-open strategy ensures Redis issues don't lock out users
4. **Sliding Window**: More accurate than fixed windows, prevents burst attacks at window boundaries

## Performance

- **Latency**: ~10-50ms overhead per request (Redis round-trip)
- **Throughput**: Upstash Redis can handle thousands of requests per second
- **Scalability**: Horizontal scaling supported (shared Redis state)

## Future Enhancements

1. **Tiered Limits**: Different limits for authenticated vs. anonymous users
2. **CAPTCHA Integration**: Require CAPTCHA after N failed attempts
3. **Allowlist**: Bypass rate limits for trusted IPs
4. **Custom Windows**: Per-endpoint configuration
5. **Rate Limit Pools**: Share limits across related endpoints
