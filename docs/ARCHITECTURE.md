# LlamaCrawl v2 — Project Architecture

## 1. Overview

LlamaCrawl v2 is a **Doc-to-Graph RAG platform** designed for self-hosted, GPU-accelerated retrieval and structured knowledge extraction. It integrates data ingestion (Firecrawl, APIs, configs) with vector search (Qdrant), graph storage (Neo4j), and selective LLM reasoning (Qwen3 via Ollama). The project emphasizes modularity, deterministic extraction, and reproducible data flow.

---

## 2. High-Level Design

The system is composed of three major planes:

### a. Ingestion Plane

* **Sources:** Firecrawl, GitHub, Reddit, YouTube, Gmail, Elasticsearch, SWAG configs, Docker Compose, Unifi, Tailscale, AI sessions.
* **Tasks:** Fetch, normalize, deduplicate, chunk, and embed documents.
* **Outputs:** Chunks stored in Qdrant, metadata in Postgres, and pending extraction tasks in Redis.

### b. Extraction Plane

* Multi-tier extractor converting text into entities and relationships for the Neo4j property graph.
* **Tier A:** Deterministic parsing (tables, code blocks, regex, Aho-Corasick).
* **Tier B:** spaCy pipeline for dependency parsing and entity recognition.
* **Tier C:** LLM window extraction (Qwen3-4B-Instruct via Ollama) on ambiguous spans.

### c. Retrieval Plane

* **Hybrid Search:** Vector search (TEI embeddings) + reranking + graph traversal.
* **Synthesis:** Answers generated via Ollama with inline citations and provenance links.
* **Result Structure:** (Answer + Sources + Graph context + Relevance metrics).

---

## 3. Repository Layout

```
.
├── apps/
│   ├── api/          # FastAPI app exposing REST endpoints
│   ├── cli/          # Typer-based CLI interface
│   ├── mcp/          # MCP protocol adapter
│   └── web/          # Next.js dashboard
│
├── packages/
│   ├── core/         # Business layer — domain models, use-cases, interfaces
│   ├── ingest/       # Firecrawl, GitHub, Reddit, Unifi, Tailscale readers
│   ├── extraction/   # Multi-tier extraction engine (spaCy + Qwen)
│   ├── graph/        # Neo4j adapter and Cypher writers
│   ├── vector/       # Qdrant client & hybrid retriever
│   ├── retrieval/    # LlamaIndex indices, retrievers, and query engines
│   ├── schemas/      # Pydantic and OpenAPI schemas
│   ├── clients/      # Auto-generated API clients (TS + Python)
│   └── common/       # Logging, config, observability utilities
│
├── docker/           # Dockerfiles for API, Neo4j, and Postgres
├── docs/             # Documentation and architectural references
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 4. Core Components

### A. Business Layer (`packages/core`)

Defines all **entities**, **value objects**, and **use-cases** shared across the stack. It’s framework-agnostic and depends only on schemas.

### B. Ingestion Adapters (`packages/ingest`)

Firecrawl and API readers normalize heterogeneous data into unified `Document` objects with metadata, chunking, and deduplication.

### C. Extraction Engine (`packages/extraction`)

Three-tier system:

1. **Tier A (Deterministic):** Regex, tables, and static dictionaries.
2. **Tier B (spaCy):** Entity and dependency-based pattern detection.
3. **Tier C (LLM):** Contextual relation extraction via Ollama/Qwen.

### D. Storage Layer

* **Qdrant:** Vector index (GPU HNSW) storing embeddings (TEI Qwen3 1024-dim).
* **Neo4j:** Graph store for entities/relations; optimized for batch `UNWIND` writes.
* **Redis:** Job state, caching, deduplication.
* **Postgres:** Metadata and ingestion job management.

### E. Retrieval Layer (`packages/retrieval`)

Implements **LlamaIndex PropertyGraphIndex**, combining Qdrant semantic search with Neo4j traversal. Includes reranking and hybrid scoring logic.

---

## 5. Data Flow

```mermaid
graph TD;
  A[Sources: Web, GitHub, Reddit, APIs] -->|Firecrawl| B[Normalizer]
  B --> C[Chunker]
  C -->|TEI Embedding| D[Qdrant]
  B -->|Extraction Queue| E[Tiered Extractor]
  E -->|Entities/Relations| F[Neo4j]
  E -->|Cache| G[Redis]
  D --> H[Retrieval Engine]
  F --> H
  H --> I[Synthesis (Ollama Qwen3)]
  I --> J[Answers + Citations]
```

---

## 6. Docker Services

| Service             | Role                          | GPU |
| ------------------- | ----------------------------- | --- |
| `taboot-vectors`    | Qdrant vector DB              | ✅   |
| `taboot-embed`      | TEI embedding inference       | ✅   |
| `taboot-rerank`     | SentenceTransformers reranker | ✅   |
| `taboot-graph`      | Neo4j graph store             | ❌   |
| `taboot-cache`      | Redis state & cache           | ❌   |
| `taboot-db`         | PostgreSQL metadata           | ❌   |
| `taboot-playwright` | Headless browser for scraping | ❌   |
| `taboot-crawler`    | Firecrawl orchestrator        | ❌   |
| `taboot-ollama`     | Ollama LLM runtime            | ✅   |
| `taboot-app`        | Unified API + MCP + Web       | ❌   |
| `taboot-worker`     | Extraction worker             | ❌   |

---

## 7. Performance Targets

| Tier   | Component                | Target                  |
| ------ | ------------------------ | ----------------------- |
| Tier A | Deterministic extraction | ≥50 pages/sec           |
| Tier B | spaCy NLP                | ≥200 sentences/sec (md) |
| Tier C | Qwen3 LLM                | ≤250ms median / window  |
| Neo4j  | Bulk writes              | ≥20k edges/min          |
| Qdrant | Upserts                  | ≥5k vectors/sec         |

---

## 8. Observability

* **Metrics:** Tier throughput, LLM latency, cache hits, RAG precision.
* **Logging:** JSON structured, Python `logging` + `python-json-logger`.
* **Tracing:** Request → Chunk → Extraction → Graph Tx → Query chain.
* **Dashboards:** Grafana + Prometheus integration.

---

## 9. Security & Access Control

* Secrets via `.env` (ignored except `.env.example`).
* Optional mTLS between API and data stores.
* SSH-based access for remote Docker Compose and SWAG parsing.

---

## 10. Future Enhancements

* Fine-tune spaCy relation extractor to reduce LLM calls.
* Introduce async extraction orchestrator via `llama-index-workflows`.
* Expand Firecrawl plugin architecture for custom sources.
* Add GraphQL API for Neo4j access.
* Integrate Triton Inference Server for TEI model optimization.

---

**Author:** Jacob Magar
**Version:** October 2025
**License:** Proprietary
