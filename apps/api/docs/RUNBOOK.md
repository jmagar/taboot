# Runbook

"Pager goes off, do this." Commands assume a Compose-based deployment and a single-node Qdrant. Adjust service names to your stack.

## Health Checks

* API: `curl -sSf http://localhost:4209/health`
* Qdrant: `curl -sSf http://localhost:6333/health`
* Neo4j: `curl -sSf http://localhost:4205/ || true` then check logs
* Redis: `redis-cli PING`
* Postgres: `pg_isready -h localhost -p 5432`
* Playwright worker: check container logs and session count via `/sessions`

## Quick Restarts

```bash
# restart a single service
docker compose restart taboot-app

# nuke & relaunch crawler workers
docker compose restart taboot-crawler taboot-playwright

# bounce vector stack
docker compose restart taboot-vectors taboot-embed taboot-rerank
```

## Logs & Grep Recipes

```bash
# tail API
docker compose logs -f --since=10m taboot-app

# find repeated 429s
docker compose logs taboot-crawler | grep -E "429|rate|Retry-After" | sort | uniq -c

# Playwright crashes
docker compose logs taboot-playwright | grep -i "crash\|oom\|timeout"

# Neo4j lock/contention
docker compose logs taboot-graph | grep -i "deadlock\|lock"
```

## Common Failures

### 1. Captcha / WAF blocks

* Lower per-domain concurrency to 1.
* Increase backoff; enable slow-start.
* Rotate sessions; clear cookies.

### 2. GPU OOM on embeddings

* Reduce batch size; raise `--max-concurrent-batches` interval.
* Switch to quantized model variant.
* Confirm no other GPU consumers.

### 3. Neo4j write failures

* Apply constraints first (see GRAPH_SCHEMA.md).
* Batch with `UNWIND` and `tx.push_size=10k`.
* If `TransientsDeadlockDetected`, retry with jitter.

### 4. Qdrant unavailable

* Check /health endpoint, then restart `taboot-vectors`.
* Inspect disk usage; ensure WAL directory has free space.
* If collection corrupted, restore from snapshot.

### 5. Browser timeouts

* Bump navigation timeout to 45s.
* Disable JS rendering for static sites.
* Respect robots and crawl-delay; don’t hammer origins.

## Data Purge Procedures

### Purge a domain from Qdrant

```
POST /collections/taboot.documents/points/delete
{"filter": {"must": [{"key":"url","match": {"value":"https://example.com"}}]}}
```

### Purge a domain from Neo4j

```cypher
MATCH (d:Document) WHERE d.url STARTS WITH 'https://example.com'
OPTIONAL MATCH (d)-[m:MENTIONS]->(x)
DETACH DELETE d, m;
```

## Backups & Restores

* **Qdrant:** snapshot collection daily; store off-box.
* **Neo4j:** `neo4j-admin database dump neo4j --to-path=/backups` nightly.
* **Postgres:** use `pg_dump` for metadata.

## Emergency Feature Flags

* `CRAWL_RESPECT_ROBOTS=true|false`
* `CRAWL_MAX_CONCURRENCY_PER_DOMAIN=1..N`
* `EMBED_BATCH_SIZE=..`
* `GRAPH_WRITES_ENABLED=true|false`

## Contact Surfaces

* `/jobs` queue depth > threshold
* `/sessions` anomalous sessions
* Metrics: see OBSERVABILITY.md
