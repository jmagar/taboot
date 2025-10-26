# Rate Limiting Flow Diagram

## Request Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│ Client Request                                                   │
│ GET /api/auth/password                                          │
│ Headers: x-forwarded-for: 192.168.1.1                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Next.js API Route                                               │
│ export const GET = withRateLimit(handleGET, passwordRateLimit) │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ withRateLimit Wrapper                                           │
│ 1. Extract client IP from headers                              │
│    identifier = getClientIdentifier(req)                       │
│    → "192.168.1.1"                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Check Rate Limit (Redis)                                       │
│ const { success, limit, reset, remaining }                     │
│   = await ratelimit.limit(identifier)                          │
│                                                                 │
│ Key: "ratelimit:${env}:password:192.168.1.1"                  │
│ Note: ${env} comes from APP_ENV or NODE_ENV                   │
│ Algorithm: Sliding Window (5 requests per 10 minutes)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         success = false    success = true
                │                 │
                ▼                 ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ Rate Limit       │  │ Execute Handler  │
    │ Exceeded         │  │ handleGET(req)   │
    │                  │  │                  │
    │ Log violation:   │  │ Check session    │
    │ logger.warn()    │  │ Check password   │
    │                  │  │ Return result    │
    │ Return 429:      │  └────────┬─────────┘
    │ {                │           │
    │   error: "..."   │           │
    │   retryAfter:    │           │
    │   "2025-..."     │           │
    │ }                │           │
    │                  │           │
    │ Headers:         │           │
    │ X-RateLimit-     │           │
    │ Limit: 5         │           │
    │ Remaining: 0     │           │
    │ Reset: 2025-...  │           │
    │ (ISO 8601)       │           │
    └────────┬─────────┘           │
             │                     │
             │                     ▼
             │         ┌──────────────────┐
             │         │ Add Rate Limit   │
             │         │ Headers          │
             │         │                  │
             │         │ X-RateLimit-     │
             │         │ Limit: 5         │
             │         │ Remaining: 4     │
             │         │ Reset: 2025-...  │
             │         │ (ISO 8601)       │
             │         └────────┬─────────┘
             │                  │
             └──────────┬───────┘
                        │
                        ▼
            ┌──────────────────────┐
            │ Response to Client   │
            │                      │
            │ 200 OK               │
            │ or                   │
            │ 429 Too Many Requests│
            │                      │
            │ + Rate Limit Headers │
            └──────────────────────┘
```

## Response Headers

All responses (both successful and rate-limited) include rate limit information headers:

- **X-RateLimit-Limit**: Maximum number of requests allowed in the window (e.g., `5`)
- **X-RateLimit-Remaining**: Number of requests remaining in current window (e.g., `4`)
- **X-RateLimit-Reset**: ISO 8601 timestamp when the limit resets (e.g., `2025-10-25T12:34:56.789Z`)

**Implementation Detail**: The rate limiter internally uses UNIX epoch seconds (seconds since January 1, 1970 UTC), but the `X-RateLimit-Reset` header is converted to ISO 8601 format for client convenience. Clients should parse this as a standard ISO timestamp.

Example response headers:
```text
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 2025-10-25T12:34:56.789Z
```

## Error Handling Flow

```text
┌─────────────────────────────────────────────────────────────────┐
│ Rate Limit Check                                                │
│ await ratelimit.limit(identifier)                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         Throws Error         Success
         (Redis down)            │
                │                │
                ▼                │
    ┌──────────────────┐         │
    │ Catch Error      │         │
    │                  │         │
    │ logger.error(    │         │
    │   "Rate limit    │         │
    │   check failed,  │         │
    │   failing open"  │         │
    │ )                │         │
    │                  │         │
    │ Return:          │         │
    │ handler(req) ◄───┼─────────┘
    │ (Allow request)  │ Continue normally
    └──────────────────┘
```

## Sliding Window Algorithm

```text
Time (minutes): 0    2    4    6    8    10   12   14   16   18   20
                │    │    │    │    │    │    │    │    │    │    │
Request Count:  │    │    │    │    │    │    │    │    │    │    │
                │                                                  │
Window:         ├──────────────────────┤                          │
                │ [5 requests max]     │                          │
                │                      │                          │
Request 1 ──────●                      │                          │
Request 2 ────────●                    │                          │
Request 3 ──────────●                  │                          │
Request 4 ────────────●                │                          │
Request 5 ──────────────●              │                          │
Request 6 ──────────────────● ❌ BLOCKED (limit exceeded)         │
                │            │         │                          │
                │            │         │                          │
After 10 min:   │            └─────────┴──────────────────────────┤
                │                      New Window                 │
                │                      ├──────────────────────┤   │
                │                      │ [5 requests max]     │   │
Request 7 ──────┼──────────────────────●  ✅ ALLOWED             │
                │  (Request 1 expired) │                      │   │
                │                      │                      │   │
```

## Per-IP Isolation

```text
┌─────────────────────────────────────────────────────────────────┐
│ Redis Keys (Rate Limit State)                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Note: ${env} = APP_ENV or NODE_ENV (e.g., "production")       │
│                                                                 │
│ ratelimit:${env}:password:192.168.1.1                          │
│ ├─ count: 5                                                    │
│ ├─ window_start: 2025-10-25T12:00:00Z                         │
│ └─ expires_at: 2025-10-25T12:10:00Z                           │
│                                                                 │
│ ratelimit:${env}:password:192.168.1.2                          │
│ ├─ count: 2                                                    │
│ ├─ window_start: 2025-10-25T12:05:00Z                         │
│ └─ expires_at: 2025-10-25T12:15:00Z                           │
│                                                                 │
│ ratelimit:${env}:password:10.0.0.1                             │
│ ├─ count: 1                                                    │
│ ├─ window_start: 2025-10-25T12:08:00Z                         │
│ └─ expires_at: 2025-10-25T12:18:00Z                           │
│                                                                 │
│ ratelimit:${env}:auth:192.168.1.1                              │
│ ├─ count: 3                                                    │
│ ├─ window_start: 2025-10-25T12:09:00Z                         │
│ └─ expires_at: 2025-10-25T12:10:00Z  (1 minute window)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Each IP address has independent rate limits.
IP 192.168.1.1 can exhaust its limit without affecting IP 192.168.1.2.
```

## Multi-Endpoint Rate Limiting

```text
┌──────────────────────────────────────────────────────────────┐
│ Password Endpoints (5 per 10 min)                            │
├──────────────────────────────────────────────────────────────┤
│ GET  /api/auth/password  ─┐                                  │
│ POST /api/auth/password  ─┼─► passwordRateLimit             │
│                            │   (sliding window, 10 min)      │
│                            └─► Redis key format:             │
│                                ratelimit:${env}:password:{ip}│
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Auth Endpoints (10 per 1 min) - Future                       │
├──────────────────────────────────────────────────────────────┤
│ POST /api/auth/login     ─┐                                  │
│ POST /api/auth/signup    ─┼─► authRateLimit                  │
│ POST /api/auth/reset     ─┤   (sliding window, 1 min)        │
│ POST /api/auth/verify    ─┘                                  │
│                            └─► Redis key format:             │
│                                ratelimit:${env}:auth:{ip}    │
└──────────────────────────────────────────────────────────────┘
```

## Code Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ apps/web/lib/rate-limit.ts                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Redis Client (ioredis)                                   │   │
│ │ new Redis(url) // Supports any Redis provider            │   │
│ │ Note: Upstash is a common hosted Redis option            │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ passwordRateLimit                                        │   │
│ │ new RateLimiterRedis({                                   │   │
│ │   points: 5,                                             │   │
│ │   duration: 600, // 10 minutes                           │   │
│ │   keyPrefix: 'ratelimit:${env}:password'                │   │
│ │ })                                                        │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ authRateLimit                                            │   │
│ │ new RateLimiterRedis({                                   │   │
│ │   points: 10,                                            │   │
│ │   duration: 60, // 1 minute                              │   │
│ │   keyPrefix: 'ratelimit:${env}:auth'                    │   │
│ │ })                                                        │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ getClientIdentifier(req)                                 │   │
│ │ Extract IP from x-forwarded-for / x-real-ip             │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ apps/web/lib/with-rate-limit.ts                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ withRateLimit(handler, ratelimit)                        │   │
│ │                                                          │   │
│ │ → Returns wrapped handler that:                         │   │
│ │   1. Extracts client identifier                         │   │
│ │   2. Checks rate limit                                  │   │
│ │   3. Returns 429 if exceeded                            │   │
│ │   4. Adds headers to response                           │   │
│ │   5. Logs violations                                    │   │
│ │   6. Fails open on errors                               │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ apps/web/app/api/auth/password/route.ts                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ async function handleGET(req) { ... }                          │
│ async function handlePOST(req) { ... }                         │
│                                                                 │
│ export const GET = withRateLimit(handleGET, passwordRateLimit);│
│ export const POST = withRateLimit(handlePOST,passwordRateLimit);│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Monitoring Dashboard

```text
┌─────────────────────────────────────────────────────────────────┐
│ Redis Monitoring (via Redis provider dashboard or CLI)         │
├─────────────────────────────────────────────────────────────────┤
│ Note: Upstash is a common hosted Redis option with built-in    │
│ analytics. Self-hosted Redis requires additional monitoring.   │
│                                                                 │
│ Total Requests:     12,450                                      │
│ Rate Limited:          234  (1.9%)                              │
│                                                                 │
│ Top IPs by Requests:                                            │
│ ┌──────────────────┬────────────┬──────────────┐              │
│ │ IP Address       │ Requests   │ Rate Limited │              │
│ ├──────────────────┼────────────┼──────────────┤              │
│ │ 192.168.1.1      │ 1,234      │ 12           │              │
│ │ 10.0.0.5         │   856      │  0           │              │
│ │ 172.16.0.10      │   642      │  3           │              │
│ └──────────────────┴────────────┴──────────────┘              │
│                                                                 │
│ Requests Over Time:                                             │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │                                                  ●       │  │
│ │                                             ●    │       │  │
│ │                                   ●    ●    │    │       │  │
│ │                          ●   ●    │    │    │    │       │  │
│ │                     ●    │   │    │    │    │    │       │  │
│ │         ●      ●    │    │   │    │    │    │    │       │  │
│ │    ●    │      │    │    │   │    │    │    │    │       │  │
│ └────┴────┴──────┴────┴────┴───┴────┴────┴────┴────┴───────┘  │
│     12am 2am   4am  6am  8am 10am 12pm 2pm  4pm  6pm  8pm     │
│                                                                 │
│ Monitoring Options:                                             │
│ • Upstash Console: Analytics tab with built-in metrics         │
│ • Redis CLI: KEYS "ratelimit:${env}:*" to inspect keys         │
│ • Redis Insight: GUI for exploring rate limit data             │
│ • Custom logging: Application-level metrics in rate-limit.ts   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
