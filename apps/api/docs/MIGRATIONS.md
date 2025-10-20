# Migrations

How to evolve Neo4j constraints and Qdrant payload/indexes safely.

## Neo4j

1. **Idempotent constraints**

```cypher
CREATE CONSTRAINT host_hostname IF NOT EXISTS FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
```

2. **Add new label or property**

* Add without dropping existing constraints.
* Backfill with batched `UNWIND`.

3. **Relationship type changes**

* Introduce new rel type; dual-write for a release; remove old after backfill.

4. **Zero-downtime tips**

* Use `dbms.tx_log.enabled=true` and monitor locks.
* Keep batches ≤ 10k rows per transaction.

## Qdrant

### Adding payload fields

* No downtime: points accept new payload keys.

### Changing vector params (size/distance)

* Create a new collection `taboot.documents.v2` with new params.
* Dual-write during migration.
* Snapshot `v1`, then bulk-copy with scroll API.
* Switch alias `taboot.documents -> v2`.

### HNSW/optimizer changes

* Safe in place; monitor recall and latency.

## Versioning

* Version schema in code: `GRAPH_SCHEMA_VERSION`, `VECTOR_SCHEMA_VERSION`.
* Tag migrations with these versions and write to Postgres.

## Rollbacks

* Keep last snapshot; revert alias and halt writers.
* In Neo4j, keep old relationship types until rollback window passes.
