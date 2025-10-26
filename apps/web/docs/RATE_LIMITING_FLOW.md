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
│ Check Rate Limit (Upstash Redis)                               │
│ const { success, limit, reset, remaining }                     │
│   = await ratelimit.limit(identifier)                          │
│                                                                 │
│ Key: "ratelimit:password:192.168.1.1"                          │
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
│ ratelimit:password:192.168.1.1                                 │
│ ├─ count: 5                                                    │
│ ├─ window_start: 2025-10-25T12:00:00Z                         │
│ └─ expires_at: 2025-10-25T12:10:00Z                           │
│                                                                 │
│ ratelimit:password:192.168.1.2                                 │
│ ├─ count: 2                                                    │
│ ├─ window_start: 2025-10-25T12:05:00Z                         │
│ └─ expires_at: 2025-10-25T12:15:00Z                           │
│                                                                 │
│ ratelimit:password:10.0.0.1                                    │
│ ├─ count: 1                                                    │
│ ├─ window_start: 2025-10-25T12:08:00Z                         │
│ └─ expires_at: 2025-10-25T12:18:00Z                           │
│                                                                 │
│ ratelimit:auth:192.168.1.1                                     │
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
│                            └─► Redis key prefix:             │
│                                ratelimit:password:{ip}       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Auth Endpoints (10 per 1 min) - Future                       │
├──────────────────────────────────────────────────────────────┤
│ POST /api/auth/login     ─┐                                  │
│ POST /api/auth/signup    ─┼─► authRateLimit                  │
│ POST /api/auth/reset     ─┤   (sliding window, 1 min)        │
│ POST /api/auth/verify    ─┘                                  │
│                            └─► Redis key prefix:             │
│                                ratelimit:auth:{ip}           │
└──────────────────────────────────────────────────────────────┘
```

## Code Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ apps/web/lib/rate-limit.ts                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ Redis Client                                             │   │
│ │ new Redis({ url, token })                               │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ passwordRateLimit                                        │   │
│ │ Ratelimit.slidingWindow(5, '10 m')                      │   │
│ │ prefix: 'ratelimit:password'                            │   │
│ └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────┐   │
│ │ authRateLimit                                            │   │
│ │ Ratelimit.slidingWindow(10, '1 m')                      │   │
│ │ prefix: 'ratelimit:auth'                                │   │
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

## Monitoring Dashboard (Upstash)

```text
┌─────────────────────────────────────────────────────────────────┐
│ Upstash Dashboard → Your Database → Analytics                  │
├─────────────────────────────────────────────────────────────────┤
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
└─────────────────────────────────────────────────────────────────┘
```
