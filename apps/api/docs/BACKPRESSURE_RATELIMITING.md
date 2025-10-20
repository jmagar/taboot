# Backpressure & Rate Limiting

Operational rules to avoid melting origin sites and your own stack.

## Per-Domain Concurrency

* Default `max_concurrent=2` per domain.
* Adaptive throttling: decrease to 1 on 429/403 spikes; increase gradually when healthy.
* Global cap across workers to avoid herd effects.

## Robots & Crawl-Delay

* Respect `robots.txt` by default; configurable override for internal tests.
* Parse `Crawl-delay` and enforce minimum delay per domain.

## Token Bucket

* Token bucket per domain with `rate` and `burst`.
* Start with `rate=0.5 req/s`, `burst=2`.

## Slow Start

* On first contact or after errors, begin at `0.25 req/s`, ramp up by 2x each success until ceiling.

## Circuit Breakers

* Open when failure rate > 50% over last 20 requests or consecutive 5xx ≥ 5.
* Half-open probes 1 request per 30s.
* Close after 10 consecutive successes.

## Timeout Policy

* Navigation timeout 30–45s depending on JS rendering.
* Total job wall time bounded; see JOB_LIFECYCLE.md.

## Queue Backpressure

* If `jobs_inflight` near worker capacity or `sessions_active` > threshold, push new work to `queued` and increase delay.
* Shed load by rejecting sync requests with 429 when queues are saturated.

## Identification & Politeness

* Set a stable `User-Agent` with contact URL/email.
* Honor `Retry-After` headers.

## Configuration Flags

* `CRAWL_RESPECT_ROBOTS=true`
* `CRAWL_MAX_CONCURRENCY_PER_DOMAIN=2`
* `CRAWL_TOKEN_BUCKET_RATE=0.5`
* `CRAWL_SLOW_START=true`
* `CRAWL_CIRCUIT_BREAKERS=true`
