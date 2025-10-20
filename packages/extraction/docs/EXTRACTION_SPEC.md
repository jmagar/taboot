# Extraction Specification — LlamaCrawl v2 (Oct 2025)

A detailed design of the tiered extraction system responsible for converting ingested documentation and configurations into structured triples for the Neo4j property graph. This defines patterns, schemas, and operational guidance for deterministic, NLP-based, and LLM-based extraction tiers.

---

## 1. Purpose

The extraction layer transforms unstructured or semi-structured data (text, markdown, HTML, YAML, JSON, logs, configs) into machine-interpretable knowledge:

* Entities (Service, Host, Endpoint, Proxy, Network, etc.)
* Relationships (DEPENDS_ON, ROUTES_TO, BINDS, RUNS, EXPOSES_ENDPOINT, etc.)
* Provenance metadata for traceability and reprocessing.

It is decoupled from ingestion to avoid blocking large crawls and supports asynchronous reprocessing and benchmarking.

---

## 2. Extraction Tiers

### Tier A — Deterministic (Rule-Based)

**Objective:** Fast, low-cost parsing of structured patterns in configs and documentation.

**Techniques:**

* Regex + YAML/JSON parsers.
* Aho-Corasick dictionary matching for known services, IPs, hosts, ports.
* Link graph and fenced code parsing.

**Outputs:**

* Direct edges: `(:Service)-[:BINDS]->(:IP)`, `(:Proxy)-[:ROUTES_TO]->(:Service)`.
* Placeholder edges for resolution: e.g., unknown container names, missing IPs.

**Performance Target:** ≥ 50 pages/sec on RTX 4070 CPU threads.

---

### Tier B — NLP (spaCy)

**Objective:** Capture grammatical relations and entity co-occurrences missed by deterministic rules.

**Pipeline:**

* Base model: `en_core_web_md`.
* Optional model: `en_core_web_trf` (transformer) for complex docs.
* Custom components:

  * `entity_ruler` with domain-specific patterns (services, proxies, IPs).
  * `DependencyMatcher` for verbs and relations like “depends on,” “connects to,” “routes to,” “binds port.”
  * `SentClassifier`: binary flag to filter technical vs. non-graph sentences.

**Outputs:**

* Entities: spaCy spans labeled with canonical graph types.
* Relations: dependency pairs → candidate edges.
* Annotated JSON for downstream LLM validation.

**Performance Target:** ≥ 200 sentences/sec (`md`), ≥ 40 sentences/sec (`trf`).

---

### Tier C — LLM Windows (Qwen3-4B-Instruct-2507)

**Objective:** Resolve ambiguous spans and extract nuanced relationships where spaCy is uncertain.

**Runtime:** Qwen3-4B-Instruct via **Ollama**, GPU-quantized inference.

**Window Policy:**

* Input window ≤ 512 tokens (2–4 sentences).
* Batching: 8–16 windows per request.
* Cache: SHA-256(window + extractor_version) in Redis.

**Prompt Template:**

```
You are a structured information extractor. Extract entities and relationships in strict JSON only.
Return only valid JSON with this schema:
{
  "entities": [
    {"type": "Service|Host|IP|Proxy|Endpoint", "name": "...", "props": {...}}
  ],
  "relations": [
    {"type": "DEPENDS_ON|ROUTES_TO|BINDS|RUNS|EXPOSES_ENDPOINT",
     "src": "...", "dst": "...", "props": {...}}
  ],
  "provenance": {"doc_id": "...", "section": "...", "span": [start, end]}
}
```

**Decoding:**

* Temperature 0.0, top_p 0.0, stop on `\n\n`.
* Post-validate with Pydantic schema.
* Reject and requeue malformed JSON.

**Performance Target:** Median 250ms/window, P95 ≤ 750ms.

---

## 3. Entity Resolution

* Cross-reference extracted entities against registries from:

  * Docker Compose / SWAG / Unifi / Tailscale APIs.
* Apply canonicalization (lowercase, snake_case) and merge aliases.
* Unresolved nodes stored as stubs for later merge.
* Batch writes to Neo4j in 1–5k triples via `UNWIND`.

---

## 4. Data Schema (Neo4j Property Graph)

**Node Labels:**

```
Service(name, image?, version?)
Host(hostname, ip?)
IP(addr)
Proxy(name)
Endpoint(service, method, path, auth?)
Doc(doc_id, url, source, ts)
```

**Relationship Types:**

```
DEPENDS_ON {reason, source_doc, confidence}
ROUTES_TO {host, path, tls}
BINDS {port, protocol}
RUNS {container_id?, compose_project?}
EXPOSES_ENDPOINT {auth?, rate_limit?}
MENTIONS {span, section, hash}
```

**Constraints:**

```cypher
CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT host_hostname IF NOT EXISTS FOR (h:Host) REQUIRE h.hostname IS UNIQUE;
CREATE INDEX endpoint_key IF NOT EXISTS FOR (e:Endpoint) ON (e.service, e.method, e.path);
```

---

## 5. Versioning & Validation

* Every extractor version stamped in output: `extractor_version = semver`.
* Regression suite: labeled windows → precision/recall/F1 guardrails.
* CI fails if F1 drops ≥ 2 pts vs. baseline.
* Unit tests for:

  * Regex and deterministic parsers.
  * spaCy matcher coverage.
  * LLM output validation.

---

## 6. Metrics

| Metric                        | Description                      | Source              |
| ----------------------------- | -------------------------------- | ------------------- |
| `extractor_windows_sec{tier}` | Throughput per tier              | Prometheus exporter |
| `llm_latency_ms{p50,p95}`     | LLM latency                      | Ollama monitor      |
| `cache_hit_rate`              | Redis hit ratio for window cache | Redis stats         |
| `neo4j_upserts_per_min`       | Graph insert throughput          | Writer logs         |
| `spaCy_ner_confidence`        | Mean entity confidence           | spaCy pipeline      |

---

## 7. Roadmap

1. Implement deterministic extractors (Tier A).
2. Integrate spaCy with entity_ruler patterns (Tier B).
3. Connect Ollama Qwen3-4B for Tier C micro-windows.
4. Build entity resolution layer with Docker/Unifi/Tailscale APIs.
5. Add batch write queue to Neo4j.
6. Set up Prometheus/Grafana for metrics.
7. Train lightweight relation classifier to skip unneeded LLM calls.

---

**Author:** Jacob Magar
**Version:** October 2025
**License:** Proprietary
