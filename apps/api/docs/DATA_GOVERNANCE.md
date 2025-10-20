# Data Governance

What we store, where, and how long. How to purge cleanly.

## Inventory

* **Qdrant (`taboot.documents`)**: embeddings + chunk payload.
* **Neo4j**: entities, relationships, and document provenance.
* **Postgres**: job metadata, API keys, audit log.
* **Redis**: ephemeral queues, caches.
* **Object store (optional)**: raw HTML/markdown blobs.

## Retention

* Qdrant points: 365 days default; extend for `namespace=prod`.
* Neo4j provenance edges: 365 days; core entities retained until superseded.
* Job metadata: 90 days.
* Raw blobs: 30–90 days based on size.

## PII Handling

* Avoid collecting PII. If unavoidable, mark chunks with `tags:["pii"]` and restrict access.
* Do not log PII; scrub at ingest.

## Right to Erasure / Domain Purge

### Identify

* Find all `Document` nodes with `url` matching pattern or `namespace`.

### Delete from Graph

```cypher
MATCH (d:Document)
WHERE d.url STARTS WITH $prefix OR d.namespace = $ns
OPTIONAL MATCH (d)-[m:MENTIONS]->()
DETACH DELETE d, m;
```

### Delete from Qdrant

```
POST /collections/taboot.documents/points/delete
{"filter": {"should": [
  {"key":"namespace","match": {"value": "$ns"}},
  {"key":"url","match": {"value": "$prefix"}}
]}}
```

### Verify

* Count remaining docs and points; snapshot state.

## Provenance & Audit

* Every relationship created from extraction includes `doc_id` and `source_tier`.
* Audit log in Postgres with `{actor, action, resource, ts}`.

## Access Control

* API keys scoped to `namespace` and operations (read, write, admin).
* Admin-only endpoints for purge and snapshots.
