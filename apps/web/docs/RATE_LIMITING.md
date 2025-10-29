# Rate Limiting Implementation

## Overview

Rate limiting has been implemented for authentication endpoints using Redis and the `rate-limiter-flexible` library. This prevents abuse and protects against brute-force attacks.

The implementation follows a **fail-closed** security model: if rate limiting cannot be verified (e.g., Redis unavailable), requests are rejected with `503 Service Unavailable` rather than allowed through.

## Architecture

### Core Components

1. **`apps/web/lib/rate-limit.ts`**
   - Creates Redis connection using `ioredis` client
   - Defines rate limiters with `rate-limiter-flexible` sliding window algorithm
   - Implements client IP extraction with proxy trust configuration
   - Enforces fail-closed behavior: throws error if Redis not configured

2. **`apps/web/lib/with-rate-limit.ts`**
   - Higher-order function wrapper for route handlers
   - Adds rate limit checks before handler execution
   - Returns 429 responses when limits exceeded
   - Injects rate limit headers into all responses
   - Fails closed on errors (rejects requests with 503 and logs issues)

3. **`apps/web/app/api/auth/password/route.ts`**
   - Updated to use rate limiting on GET and POST handlers
   - Protected against password enumeration and brute-force

## Rate Limits

### Password Endpoints

- **Limit**: 5 requests per 10 minutes
- **Prefix**: `ratelimit:{env}:password` (e.g., `ratelimit:production:password`)
- **Algorithm**: Sliding window
- **Applied to**:
  - `GET /api/auth/password` (check if user has password)
  - `POST /api/auth/password` (set new password)

### General Auth Endpoints

- **Limit**: 10 requests per 1 minute
- **Prefix**: `ratelimit:{env}:auth` (e.g., `ratelimit:production:auth`)
- **Algorithm**: Sliding window
- **Applied to**: (extensible to other auth endpoints)

**Note**: Rate limit keys are scoped by environment (`APP_ENV` or `NODE_ENV`) to prevent collisions between development, staging, and production.

## Client Identification

The system identifies clients using IP addresses with the following priority:

1. **Primary** (when `TRUST_PROXY=true`): `x-forwarded-for` header (first IP in comma-separated list)
   - Only used when `TRUST_PROXY=true` is set in environment
   - Takes the leftmost IP (original client, not proxy IP)
   - IP format is validated before use
2. **Fallback**: Connection IP from Next.js request object
   - Uses platform-provided `remoteAddress` or `ip` field
   - IP format is validated before use
3. **Default**: `'unknown'` if no valid IP can be determined

**SECURITY WARNING**: Only set `TRUST_PROXY=true` when behind a verified reverse proxy (nginx, Cloudflare, AWS ALB, etc.). When `false` (default), `x-forwarded-for` headers are ignored to prevent IP spoofing.

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

The implementation follows a **fail-closed** strategy:

- If Redis is unavailable or rate limit check fails, the request is **rejected**
- Returns `503 Service Unavailable` with `Retry-After: 60` header
- Errors are logged with full context
- This prevents bypassing rate limits during service degradation

**Response on rate limit check failure:**

```json
{
  "error": "Service temporarily unavailable. Please try again later."
}
```

**Status Code**: `503 Service Unavailable`
**Header**: `Retry-After: 60`

Example log on failure:

```json
{
  "level": "error",
  "message": "Rate limit check failed, failing closed (rejecting request)",
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

Add to `.env` or `.env.local`:

```env
# Redis connection (required for rate limiting)
REDIS_URL=redis://taboot-cache:6379

# Proxy trust configuration (optional, default: false)
TRUST_PROXY=false
```

**Required**: `REDIS_URL` must be set or the application will throw an error at startup (fail-closed).

**Optional**: Set `TRUST_PROXY=true` only when behind a verified reverse proxy (nginx, Cloudflare, AWS ALB, etc.).

### Redis Setup

The application uses Redis for rate limiting state:

- **Docker Compose**: Redis is provided as `taboot-cache` service (default: `redis://taboot-cache:6379`)
- **Production**: Point to your Redis instance (Redis 7.2+ recommended)
- **Cloud Options**: Compatible with any Redis-compatible service (AWS ElastiCache, Upstash, Redis Cloud, etc.)

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
     curl -X POST http://localhost:4211/api/auth/password \
       -H "Content-Type: application/json" \
       -H "Cookie: your-session-cookie" \
       -d '{"newPassword":"testpass123"}' \
       -i
   done
   ```

2. **Verify headers**:

   ```bash
   curl -X GET http://localhost:4211/api/auth/password \
     -H "Cookie: your-session-cookie" \
     -i | grep X-RateLimit
   ```

3. **Test different IPs**:

   ```bash
   # Simulate different clients
   curl -X GET http://localhost:4211/api/auth/password \
     -H "x-forwarded-for: 192.168.1.1" \
     -H "Cookie: your-session-cookie"

   curl -X GET http://localhost:4211/api/auth/password \
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


### Redis Monitoring

Monitor rate limiting via Redis:

```bash
# Connect to Redis (Docker Compose)
docker exec -it taboot-cache redis-cli

# View rate limit keys
KEYS ratelimit:*

# Check specific rate limit state
GET ratelimit:production:password:192.168.1.1

# Monitor real-time commands
MONITOR
```

For production deployments, use Redis monitoring tools:
- Redis Insight (GUI)
- RedisInsight Cloud
- Datadog/Prometheus Redis exporters

## Security Considerations

1. **IP Spoofing**: Proxy headers (`x-forwarded-for`) are only trusted when `TRUST_PROXY=true`. Default is `false` to prevent IP spoofing.
2. **IP Validation**: All IPs are validated (IPv4/IPv6 format) before use, even when proxy is trusted
3. **Distributed Attacks**: Rate limits are per-IP; distributed attacks from many IPs may bypass limits
4. **Fail-Closed Security**: Redis failures result in request rejection (503), preventing rate limit bypass during service degradation
5. **Sliding Window**: More accurate than fixed windows, prevents burst attacks at window boundaries

## Performance

- **Latency**: ~1-10ms overhead per request (local Redis) or ~10-50ms (cloud Redis)
- **Throughput**: Redis can handle tens of thousands of requests per second
- **Scalability**: Horizontal scaling supported (shared Redis state)
- **Retry Strategy**: Automatic reconnection with exponential backoff (max 2 seconds)

## Future Enhancements

1. **Tiered Limits**: Different limits for authenticated vs. anonymous users
2. **CAPTCHA Integration**: Require CAPTCHA after N failed attempts
3. **Allowlist**: Bypass rate limits for trusted IPs
4. **Custom Windows**: Per-endpoint configuration
5. **Rate Limit Pools**: Share limits across related endpoints
