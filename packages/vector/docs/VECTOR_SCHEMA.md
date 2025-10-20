# Vector Schema (Qdrant)

This document defines the collection layout, payload schema, and operational settings for Qdrant. It reflects TEI embeddings (1024 dim) and supports multi-tenant logical namespaces.

## Collections

### `taboot.documents`

* **Vectors:** `embedding` size=1024, distance=`Cosine`.
* **Sharding:** `shard_number: 4` (adjust by CPU cores and data volume).
* **Replication:** `replication_factor: 1` for single-node; increase for HA.
* **Write consistency:** `Majority` when replicated.
* **Optimizers:**

  * `default_segment_number: 2`
  * `max_optimization_threads: auto`
* **HNSW params:**

  * `m: 32`
  * `ef_construct: 128`
  * `full_scan_threshold: 10000`
* **Quantization (optional, for memory pressure):** scalar or product quantization after validating recall impact.

## Payload Schema

All fields are filterable. Store only what you need for retrieval and provenance; the graph holds relational structure.

| Field         | Type     | Purpose                                       |        |     |        |         |
| ------------- | -------- | --------------------------------------------- | ------ | --- | ------ | ------- |
| `doc_id`      | keyword  | Stable ID linking to `Document` node in Neo4j |        |     |        |         |
| `chunk_id`    | keyword  | Unique chunk identifier                       |        |     |        |         |
| `namespace`   | keyword  | Logical tenant/app partition                  |        |     |        |         |
| `url`         | keyword  | Source URL                                    |        |     |        |         |
| `title`       | keyword  | Display title                                 |        |     |        |         |
| `source`      | keyword  | `web                                          | github | api | syslog | config` |
| `job_id`      | keyword  | Ingestion job provenance                      |        |     |        |         |
| `sha256`      | keyword  | De-duplication across jobs                    |        |     |        |         |
| `mime`        | keyword  | Content type                                  |        |     |        |         |
| `lang`        | keyword  | ISO language code                             |        |     |        |         |
| `chunk_index` | int      | Order within document                         |        |     |        |         |
| `text_len`    | int      | Characters for quick filters                  |        |     |        |         |
| `created_at`  | datetime | First indexed timestamp                       |        |     |        |         |
| `updated_at`  | datetime | Last updated timestamp                        |        |     |        |         |
| `tags`        | string[] | Arbitrary labels                              |        |     |        |         |

> Also consider `host`, `service`, or `entity_refs` arrays when cross-walking to graph entities for hybrid queries.

## Namespacing Strategy

Use a single collection with a `namespace` payload field instead of per-namespace collections. This simplifies operational overhead while enabling strict filtering:

```json
{"must": [{"key": "namespace", "match": {"value": "prod"}}]}
```

## Chunking Policy

* **Strategy:** token-based for general text, markdown-aware for docs, code-aware for repos.
* **Defaults:** `chunk_size=800`, `chunk_overlap=150` tokens.
* **Markdown:** split by headings, lists, code fences; then sub-split to token windows.
* **Code:** split by AST/function where possible; fallback to lines with windowing.
* **Why:** balances recall and context packing for rerankers and Qwen3 response quality.

Keep `chunk_index` contiguous per `doc_id` so client-side stitching and context windows are stable.

## Insert/Upsert

* De-duplicate by `(sha256, namespace)`; if content identical, update metadata and `updated_at` only.
* Idempotency via `point_id = chunk_id` so retries are safe.

## Example Create Collection (HTTP)

```json
POST /collections/taboot.documents
{
  "vectors": {"size": 1024, "distance": "Cosine"},
  "optimizers_config": {"default_segment_number": 2},
  "hnsw_config": {"m": 32, "ef_construct": 128}
}
```

## Example Insert Point

```json
PUT /collections/taboot.documents/points
{
  "points": [
    {
      "id": "chunk_01ABC",
      "vector": {"embedding": [/* 1024 floats */]},
      "payload": {
        "doc_id": "doc_01DX",
        "chunk_id": "chunk_01ABC",
        "chunk_index": 0,
        "namespace": "lab",
        "url": "https://example",
        "title": "Example",
        "source": "web",
        "job_id": "job_123",
        "sha256": "...",
        "mime": "text/html",
        "lang": "en",
        "text_len": 2048,
        "created_at": "2025-10-18T12:00:00Z",
        "tags": ["docs", "nginx"]
      }
    }
  ]
}
```

## Example Search with Filters

```json
POST /collections/taboot.documents/points/search
{
  "vector": {"name": "embedding", "vector": [/* q vector */]},
  "limit": 10,
  "filter": {"must": [
    {"key": "namespace", "match": {"value": "lab"}},
    {"key": "source", "match": {"value": "web"}}
  ]}
}
```

## Replication & Sharding Guidance

* Start with `shard_number=4` for 1–10M chunks. Increase when segment counts grow and compactions slow.
* If you introduce replicas, enable `read_fan_out` and track tail latency. Watch `optimizer_status` metrics.

## Reranking

Store only base embeddings in Qdrant. Use TEI reranker out-of-band on the top K (e.g., K=50) and re-score before synthesis. Persist rerank features only if you need offline evals.
