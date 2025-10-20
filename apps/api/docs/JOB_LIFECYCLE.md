# Job Lifecycle

State machine and operational rules for crawl and ingestion tasks. Works for both Firecrawl jobs and ingestion jobs with minor differences noted.

## States

```
queued -> running -> {succeeded | failed | canceled}
           ^             |
           |             v
           +------ retry_pending
```

* **queued**: accepted, awaiting worker.
* **running**: worker started and heartbeating.
* **retry_pending**: transient failure scheduled for retry.
* **succeeded**: completed successfully; results materialized.
* **failed**: terminal error after retries.
* **canceled**: user or system canceled.

## Events

* `accept(job)` → `queued`
* `start(worker_id)` → `running`
* `heartbeat(t)` → refresh `updated_at`; if missed beyond TTL, mark `failed: timeout` or reschedule.
* `progress(n)` → update counters and ETA.
* `complete(stats)` → `succeeded`
* `error(code)` → error classification; may route to `retry_pending`.
* `cancel()` → best-effort stop; mark `canceled`.

## Idempotency

* Creation endpoints support `Idempotency-Key`. Jobs with the same key within 24h return the original job.
* Worker upserts must be idempotent: writes keyed by natural IDs (`doc_id`, `chunk_id`) to avoid duplication on retries.

## Retry & Backoff

* **Transient classes**: `network_error`, `rate_limited`, `browser_crash`, `timeout_soft`, `qdrant_unavailable`, `neo4j_write_lock`.

  * Retry policy: exponential backoff with jitter, base 2s, factor 2, max 7 attempts.
* **Permanent classes**: `invalid_url`, `robots_disallowed`, `parse_error_strict`, `unsupported_mime`, `bad_request`.

  * No retry; mark `failed`.
* **Anti-bot signals**: `captcha`, `403_waf`, `503_shield`.

  * Switch to slow-start, rotate session, raise backoff cap, and lower per-domain concurrency.

## Cancellation

* Transition allowed from `queued` or `running`.
* Worker should set `canceled_at` and drop in-flight browser sessions; partial results may exist.

## Counters & Stats

Track per job:

* `urls_total`, `urls_enqueued`, `urls_processed`, `documents_emitted`, `chunks_indexed`, `tokens_estimated`, `duration_seconds`.

## Failure Classification

Record `error_code`, `message`, and `context` (domain, url, attempt, worker_id). Suggested codes:

* `E_URL_BAD`, `E_ROBOTS`, `E_403_WAF`, `E_429_RATE`, `E_5XX_ORIGIN`, `E_PARSE`, `E_TIMEOUT`, `E_BROWSER`, `E_QDRANT`, `E_NEO4J`, `E_GPU_OOM`.

## Heartbeat & TTL

* Worker heartbeat interval: 10s.
* Missed heartbeats for 90s → mark as `timeout_soft` and reschedule.
* Max job wall clock: default 300s sync, configurable per async job.

## State Persistence

* Store state in Redis with write-through to Postgres for reporting.
* Append-only event log for audits.

## Materialization

* On `succeeded`, store Firecrawl result documents in `Document` store and/or emit to Qdrant directly.
* Ingestion job reads from result store or inline docs, writes to Qdrant and/or Neo4j in batches.

## Observability Hooks

* Emit structured log on each transition: `{job_id, from, to, reason, attempt}`.
* Metrics: `jobs_inflight{type=...}`, `job_duration_seconds`, `job_failures_total{code}`, `retry_attempts_total`.
