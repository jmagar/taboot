# TABOOT Ingestion Orchestrator API

FastAPI surface for orchestrating Firecrawl crawling/scraping jobs and piping results into your retrieval stack (Qdrant, Neo4j, or both). This doc is human-friendly; the full machine spec lives in `openapi.yaml`.

## Authentication

Use an API key header. If enabled, every request must include:

```
X-API-Key: <your key>
```

## Base URL

```
http://localhost:8000
```

## Resources

### Health

* **GET /health** → 200 when the service is alive.

### Firecrawl Jobs

Manage asynchronous crawl/scrape jobs.

* **POST /jobs/firecrawl** – create a job

  * Body: `FirecrawlJobCreateRequest`
  * 202 → `FirecrawlJobCreateResponse`

* **GET /jobs** – list jobs (newest first)

  * Query: `status?`, `mode?`, `q?`, `limit?`, `cursor?`
  * 200 → `FirecrawlJobPage`

* **GET /jobs/{job_id}** – fetch job detail

  * 200 → `FirecrawlJobDetailResponse`
  * 404 if unknown

* **POST /jobs/{job_id}/cancel** – best-effort cancel

  * 202 → `FirecrawlJobDetailResponse`

* **GET /jobs/{job_id}/result** – materialized output

  * 200 → `FirecrawlResultResponse` (available after `succeeded`)
  * 409 if not yet complete

* **GET /jobs/{job_id}/logs** – concise job log lines

  * Query: `offset?`, `limit?`
  * 200 → `LogPage`

* **DELETE /jobs/{job_id}** – purge job and artifacts

  * 204 on success

### Synchronous crawl/scrape

If you like living dangerously on the request thread.

* **POST /crawl:sync**

  * Body: `FirecrawlSyncRequest` (same knobs as a job, but blocks)
  * 200 → `FirecrawlSyncResult`

### Ingestion

Move raw documents into your vector store and/or graph.

* **POST /ingestions** – create ingestion task

  * Body: `IngestionRequest`
  * 202 → `IngestionResponse`

* **GET /ingestions** – list ingestions

  * Query: `status?`, `limit?`, `cursor?`
  * 200 → `IngestionPage`

* **GET /ingestions/{ingestion_id}** – detail

  * 200 → `IngestionDetail`

* **POST /ingestions/{ingestion_id}/cancel** – best-effort cancel

  * 202 → `IngestionDetail`

### Sessions (Playwright/Browser workers)

* **GET /sessions** – list active sessions

  * 200 → `SessionPage`

* **DELETE /sessions/{session_id}** – force close a session

  * 204 on success

## Schemas (overview)

> Full shapes are in `openapi.yaml`.

* `FirecrawlMode`: `crawl` | `scrape`
* `JobStatus`: `queued` | `running` | `succeeded` | `failed` | `canceled`
* `FirecrawlJobCreateRequest`:

  * `urls: string[]` required
  * knobs: `mode`, `max_depth`, `include_patterns[]`, `exclude_patterns[]`, `respect_robots`, `render_js`, `concurrency`, `timeout_seconds`, `metadata`
* `Document`:

  * `url`, `title?`, `content?`, `markdown?`, `html?`, `extracted_at`, `meta?`
* `FirecrawlResultResponse`:

  * `job_id`, `status`, `documents[]`, `stats`
* `IngestionRequest`:

  * `source`: `job_id` or inline `documents[]`
  * `destination`: `qdrant` | `neo4j` | `both`
  * `namespace?`, `upsert?`, `chunking?`, `embedding_model?`, `rerank_model?`, `graph_extraction?`, `tags[]?`

## Error Model

Consistent error envelope:

```json
{
  "error": {
    "code": "string",
    "message": "human readable",
    "details": {}
  }
}
```

## Idempotency

For create operations, you may optionally send `Idempotency-Key` to safely retry.

## Rate limiting

If enabled, requests over the limit return 429 with `Retry-After`.

## Versioning

`X-API-Version: 1` today. Backwards-compatible changes won’t bump; breaking ones will.

## Notes on feature parity

* Async job pipeline mapped 1:1 with your previous Firecrawl job store and result model.
* Sync endpoint provided for parity with your quick-run path.
* Ingestion task supports both direct `job_id` source and inline documents, plus destination fanout.
* Sessions routes reflect your SessionsWatcherManager for introspection and cleanup.
