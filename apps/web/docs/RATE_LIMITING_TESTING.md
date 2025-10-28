# Rate Limiting Testing Guide

## Prerequisites

1. **Upstash Redis configured**:
   ```bash
   # Check .env has these set:
   grep UPSTASH_REDIS apps/web/.env
   ```

2. **Dependencies installed**:
   ```bash
   cd apps/web
   pnpm list @upstash/ratelimit @upstash/redis
   ```

3. **Application running**:
   ```bash
   docker compose up taboot-app
   # or
   cd apps/web && pnpm dev
   ```

## Test Scenarios

### 1. Verify Rate Limit Headers Present

**Test**: Send single request to password endpoint

```bash
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=YOUR_SESSION_TOKEN" \
  -v 2>&1 | grep X-RateLimit
```

**Expected**:
```
< X-RateLimit-Limit: 5
< X-RateLimit-Remaining: 4
< X-RateLimit-Reset: 2025-10-25T12:34:56.789Z
```

**Success Criteria**: All three headers present

---

### 2. Trigger Rate Limit (Password Endpoint)

**Test**: Send 6 requests in quick succession (limit is 5 per 10 minutes)

```bash
# Get a session token first (login via web UI)
SESSION_TOKEN="your-session-token-here"

for i in {1..6}; do
  echo "Request $i:"
  curl -X GET http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -s -o /dev/null -w "Status: %{http_code}\n"
  sleep 0.5
done
```

**Expected Output**:

```text
Request 1:
Status: 200
Request 2:
Status: 200
Request 3:
Status: 200
Request 4:
Status: 200
Request 5:
Status: 200
Request 6:
Status: 429
```


**Success Criteria**:
- First 5 requests return 200
- 6th request returns 429

---

### 3. Verify 429 Response Body

**Test**: Send request after hitting rate limit

```bash
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s | jq
```

**Expected**:

```json
{
  "error": "Too many requests. Please try again later.",
  "retryAfter": "2025-10-25T12:44:56.789Z"
}
```

**Success Criteria**: Error message and retryAfter timestamp present

---

### 4. Per-IP Tracking

**Test**: Verify different IPs have separate rate limits

```bash
# IP 1: Send 5 requests
for i in {1..5}; do
  curl -X GET http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -H "x-forwarded-for: 192.168.1.1" \
    -s -o /dev/null -w "IP1 Request $i: %{http_code}\n"
done

# IP 2: Should still have 5 requests available
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -H "x-forwarded-for: 192.168.1.2" \
  -s -o /dev/null -w "IP2 Request 1: %{http_code}\n"
```

**Expected**:

```text
IP1 Request 1: 200
IP1 Request 2: 200
IP1 Request 3: 200
IP1 Request 4: 200
IP1 Request 5: 200
IP2 Request 1: 200  ✓ (separate limit)
```


**Success Criteria**: IP2 request succeeds even though IP1 exhausted limit

---

### 5. Rate Limit Reset After Window

**Test**: Verify limit resets after 10 minutes

```bash
# Exhaust limit
for i in {1..5}; do
  curl -X GET http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -s -o /dev/null
done

# Should fail (429)
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s -o /dev/null -w "Before wait: %{http_code}\n"

# Wait 10 minutes (or use Redis CLI to clear: redis-cli DEL ratelimit:password:IP)
echo "Waiting 10 minutes..."
sleep 600

# Should succeed (200)
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s -o /dev/null -w "After wait: %{http_code}\n"
```

**Expected**:

```text
Before wait: 429
Waiting 10 minutes...
After wait: 200
```

**Alternative (Fast Test)**: Clear Redis key manually

```bash
# Connect to Upstash Redis via CLI or dashboard
# Delete key: ratelimit:password:192.168.1.1
```


**Success Criteria**: Limit resets after window expires

---

### 6. Logging Verification

**Test**: Verify rate limit violations are logged

```bash
# Trigger rate limit
for i in {1..6}; do
  curl -X GET http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -s -o /dev/null
done

# Check logs
docker compose logs taboot-app | grep "Rate limit exceeded"
# or
tail -f apps/web/.next/server/logs/app.log | grep "Rate limit exceeded"
```

**Expected Log**:

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


**Success Criteria**: Log entry present with correct structure

---

### 7. Fail-Open Behavior

**Test**: Verify requests allowed when Redis unavailable

```bash
# Stop Upstash Redis (or set invalid credentials)
export UPSTASH_REDIS_REST_URL="https://invalid.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="invalid"

# Restart app
docker compose restart taboot-app

# Send request - should succeed despite Redis error
curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s -o /dev/null -w "Status: %{http_code}\n"

# Check logs for error
docker compose logs taboot-app | grep "Rate limit check failed"
```

**Expected**:

```text
Status: 200  ✓ (request allowed)
```

**Expected Log**:

```json
{
  "level": "error",
  "message": "Rate limit check failed, failing open",
  ...
}
```


**Success Criteria**:
- Request succeeds (200) despite Redis failure
- Error logged with "failing open" message

---

### 8. POST Endpoint Rate Limiting

**Test**: Verify POST /api/auth/password is rate limited

```bash
for i in {1..6}; do
  echo "Request $i:"
  curl -X POST http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"newPassword":"TestPass123!"}' \
    -s -o /dev/null -w "Status: %{http_code}\n"
done
```

**Expected**:

```text
Request 1:
Status: 400  (or 200 if password not set)
...
Request 5:
Status: 400  (or 200)
Request 6:
Status: 429  ✓ (rate limited)
```


**Success Criteria**: 6th request returns 429

---

## Automated Test Suite

Run unit tests:

```bash
cd apps/web
pnpm test lib/__tests__/rate-limit.test.ts
```

**Expected**: All tests pass

---

## Performance Testing

### Latency Impact

**Test**: Measure overhead of rate limit check

```bash
# Without rate limiting (baseline - requires code change to disable)
time curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s -o /dev/null

# With rate limiting
time curl -X GET http://localhost:3000/api/auth/password \
  -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
  -s -o /dev/null
```

**Expected**: <50ms additional latency

---

### Concurrent Requests

**Test**: Verify behavior under concurrent load

```bash
# Send 10 concurrent requests
for i in {1..10}; do
  curl -X GET http://localhost:3000/api/auth/password \
    -H "Cookie: better-auth.session_token=$SESSION_TOKEN" \
    -s -o /dev/null -w "Status: %{http_code}\n" &
done
wait
```

**Expected**: First 5 succeed (200), next 5 fail (429)

**Success Criteria**: Rate limit enforced correctly under concurrency

---

## Checklist

- [ ] Rate limit headers present in responses
- [ ] 429 status returned after threshold (5 requests)
- [ ] Error message and retryAfter in 429 response body
- [ ] Per-IP tracking works (different IPs have separate limits)
- [ ] Limit resets after 10-minute window
- [ ] Rate limit violations logged with correct structure
- [ ] Fail-open behavior on Redis errors
- [ ] POST endpoint protected
- [ ] Latency overhead acceptable (<50ms)
- [ ] Concurrent requests handled correctly

---

## Troubleshooting

### Issue: No rate limit headers in response

**Cause**: Rate limiting not applied or wrapper not working

**Fix**: Verify handlers wrapped with `withRateLimit()`:

```typescript
export const GET = withRateLimit(handleGET, passwordRateLimit);
export const POST = withRateLimit(handlePOST, passwordRateLimit);
```


---

### Issue: Rate limit not triggering

**Cause**: Upstash Redis not configured or different IPs per request

**Fix**:
1. Check `.env` has `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`
2. Verify same IP used across requests (check `x-forwarded-for` header)
3. Check Upstash dashboard for requests

---

### Issue: All requests return 429

**Cause**: Rate limit window too aggressive or Redis state corrupted

**Fix**:
1. Clear Redis key: `DEL ratelimit:password:YOUR_IP`
2. Verify limit configuration in `apps/web/lib/rate-limit.ts`

---

### Issue: Requests succeed when Redis down

**Cause**: Expected behavior (fail-open)

**Fix**: Not an issue - this is intentional to prevent Redis outages from blocking users

---

## Next Steps

After testing, consider:

1. **Additional Endpoints**: Apply rate limiting to other auth endpoints (login, signup, password reset)
2. **Monitoring**: Set up alerts for high rate limit violation rates
3. **Tuning**: Adjust limits based on production traffic patterns
4. **CAPTCHA**: Integrate CAPTCHA after multiple failures
