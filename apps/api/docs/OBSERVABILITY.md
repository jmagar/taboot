# Observability

What we log, what we measure, and how we trace across crawl → embed → ingest.

## Logging

* **Format:** JSON, one event per line.
* **Required fields:** `ts`, `level`, `service`, `job_id?`, `worker_id?`, `domain?`, `url?`, `event`, `elapsed_ms?`, `error_code?`, `attempt?`.
* **PII:** scrub tokens, cookies, Authorization headers, query secrets.
* **Sampling:** info-level sampling at high QPS; errors always logged.

## Metrics

Use Prometheus-style names and labels.

* **Job pipeline**

  * `jobs_inflight{type="crawl|ingest"}` gauge
  * `job_duration_seconds{type}` histogram (buckets: 1,2,5,10,30,60,120,300)
  * `job_failures_total{type, code}` counter
  * `retry_attempts_total{type}` counter
* **Crawler**

  * `requests_total{domain,status}`
  * `request_latency_ms{domain}` histogram
  * `robots_respected_total{domain}` counter
  * `captcha_encounters_total{domain}` counter
  * `sessions_active` gauge
* **Embeddings / Reranker**

  * `embedding_latency_ms{model}` histogram
  * `embedding_batch_size{model}` summary
  * `rerank_latency_ms{model}` histogram
  * `gpu_memory_bytes{device}` gauge
* **Qdrant**

  * `qdrant_upserts_total`
  * `qdrant_search_latency_ms`
  * `qdrant_points_count`
* **Neo4j**

  * `neo4j_tx_latency_ms`
  * `neo4j_deadlocks_total`
  * `neo4j_nodes_count{label}`
  * `neo4j_rels_count{type}`

### Thresholds & Alerts (starting points)

* `job_duration_seconds{type="crawl"}` p95 > 300s for 5m → warn
* `job_failures_total{code=~"E_429|E_403_WAF"}` rate > 10/min → reduce concurrency
* `gpu_memory_bytes` > 90% for 2m → scale down batch size
* `neo4j_deadlocks_total` > 0 → enable retry and lower batch
* `qdrant_search_latency_ms` p95 > 200ms → check HNSW `ef` and CPU steal

## Tracing

* **Trace model:** parent trace for `job_id` with spans:

  * `crawl.fetch(url)`
  * `crawl.parse(url)`
  * `embed.batch(n)`
  * `qdrant.upsert(k)`
  * `extract.tierA/B/C(doc_id)`
  * `neo4j.write(batch)`
* **Baggage:** `job_id`, `namespace`, `domain` propagate through spans.
* **Exporters:** OTLP to your collector; visualize in Tempo/Jaeger.

## Dashboards

* **Pipeline Overview:** queue depth, job rates, failure codes, median/95th durations.
* **Crawler:** domain heatmap of status codes, time to first byte, active sessions.
* **Embeddings:** latency vs batch; GPU memory; throughput.
* **Vector search:** recall tests vs `ef_search`, hit@k trends.
* **Graph:** node/edge growth, write latency, deadlocks.

## SLOs

* **Availability (API):** 99.5% monthly.
* **Latency:** crawl sync p50 < 2s, p95 < 6s; search p95 < 200ms before rerank.
* **Quality:** top-5 recall ≥ 0.85 on eval set (see EVALUATION_PLAN.md).
