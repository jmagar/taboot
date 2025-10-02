# LlamaCrawl RAG Pipeline - Parallel Implementation Plan

This plan breaks down the implementation of a greenfield multi-source RAG pipeline into parallelizable tasks. The system consists of three layers: **infrastructure** (Docker services), **core components** (configuration, storage, utilities), and **features** (readers, ingestion, query). Tasks are organized to maximize parallel development while respecting dependencies. The critical path runs through infrastructure → storage backends → custom embeddings → ingestion pipeline → first reader E2E.

## Critically Relevant Files and Documentation

### Documentation (READ FIRST)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md) - Architecture patterns and project structure
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md) - Complete requirements and user flows
- [.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md](.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md) - LlamaIndex integration patterns
- [.docs/plans/llamacrawl-rag-pipeline/qdrant-integration.docs.md](.docs/plans/llamacrawl-rag-pipeline/qdrant-integration.docs.md) - Qdrant vector store patterns
- [.docs/plans/llamacrawl-rag-pipeline/neo4j-knowledge-graph.docs.md](.docs/plans/llamacrawl-rag-pipeline/neo4j-knowledge-graph.docs.md) - Neo4j PropertyGraphIndex patterns
- [.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md](.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md) - Redis state management patterns
- [.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md](.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md) - TEI custom embedding patterns
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md) - Data source reader patterns

### Existing Infrastructure
- [/docker-compose.yaml](/docker-compose.yaml) - Current infrastructure (Qdrant, TEI embeddings, TEI reranker)
- [/INIT.md](/INIT.md) - Original project vision

---

## Implementation Plan

### Phase 0: Infrastructure & Project Setup

#### Task 0.1: Extend Docker Compose Stack | Depends on [none]

**READ THESE BEFORE TASK**
- [/docker-compose.yaml](/docker-compose.yaml)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#infrastructure-stack)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#relevant-files)

**Instructions**

Files to Modify:
- `/docker-compose.yaml`

Add the following services to docker-compose.yaml:

1. **Neo4j** (graph database)
   - Image: `neo4j:5.15-community`
   - Ports: `${NEO4J_HTTP_PORT:-7474}:7474`, `${NEO4J_BOLT_PORT:-7687}:7687`
   - Environment variables:
     - `NEO4J_AUTH=${NEO4J_USER:-neo4j}/${NEO4J_PASSWORD:-changeme}`
     - `NEO4J_server_memory_heap_initial__size=2G`
     - `NEO4J_server_memory_heap_max__size=2G`
     - `NEO4J_server_memory_pagecache_size=2G`
     - `NEO4J_server_default__database=neo4j`
   - Volumes: neo4j_data:/data, neo4j_logs:/logs, neo4j_plugins:/plugins
   - Health check: `cypher-shell -u neo4j -p ${NEO4J_PASSWORD:-changeme} "RETURN 1"`

2. **Redis** (state/cache/DLQ)
   - Image: `redis:7.2-alpine`
   - Port: `${REDIS_PORT:-6379}:6379`
   - Command: `redis-server --appendonly yes --appendfsync everysec --save 900 1 --save 300 10 --save 60 10000`
   - Volume: redis_data:/data
   - Health check: `redis-cli ping`

3. **Ollama** (LLM synthesis)
   - Image: `ollama/ollama:latest`
   - Port: `${OLLAMA_PORT:-11434}:11434`
   - GPU: NVIDIA GPU access (count: 1, capabilities: [gpu])
   - Volume: ollama_data:/root/.ollama
   - Environment: `OLLAMA_HOST=0.0.0.0:11434`, `OLLAMA_KEEP_ALIVE=5m`
   - Health check: `curl -f http://localhost:11434/api/tags`

4. **Firecrawl** (web scraping) - **SKIP THIS SERVICE**
   - Use the existing hosted instance at `https://firecrawl.tootie.tv`
   - Configure `FIRECRAWL_API_URL` and `FIRECRAWL_API_KEY` in `.env` only
   - No Docker service needed (self-hosting requires multiple services: api, playwright, postgres)

Add corresponding volume declarations for Neo4j, Redis, and Ollama. Ensure all services use `crawler-network`. Use environment variable substitution with defaults for all ports.

**Gotchas:**
- Neo4j memory syntax uses double underscores: `NEO4J_server_memory_heap_max__size` (not single underscore)
- Redis persistence requires explicit command with --appendonly and --save flags
- GPU allocation: All GPU services (TEI x2, Ollama) share `CUDA_VISIBLE_DEVICES=0` - monitor VRAM usage
- Ollama model must be pulled after startup: `docker exec crawler-ollama ollama pull llama3.1:8b`
- Firecrawl: Use hosted instance - self-hosting adds complexity (3 extra services, postgres dependency)
- Test deployment to steamy-wsl after changes

---

#### Task 0.2: Initialize Python Project Structure | Depends on [none]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#relevant-files)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#project-structure)

**Instructions**

Files to Create:
- `/pyproject.toml`
- `/README.md`
- `/.gitignore`
- `/src/llamacrawl/__init__.py`
- `/src/llamacrawl/readers/__init__.py`
- `/src/llamacrawl/ingestion/__init__.py`
- `/src/llamacrawl/storage/__init__.py`
- `/src/llamacrawl/query/__init__.py`
- `/src/llamacrawl/utils/__init__.py`
- `/src/llamacrawl/models/__init__.py`
- `/tests/unit/.gitkeep`
- `/tests/integration/.gitkeep`

Create `pyproject.toml` with:
- `uv` as build backend
- Python 3.11+ requirement
- Project metadata (name: "llamacrawl", version: "0.1.0")
- Core dependencies: llama-index, qdrant-client, neo4j, redis, typer, pydantic, pyyaml, python-dotenv, python-json-logger
- Reader-specific dependencies: firecrawl-py, PyGithub, praw, elasticsearch, google-auth-oauthlib, google-api-python-client
- Dev dependencies: pytest, mypy, ruff, pytest-asyncio
- Entry point: `llamacrawl = "llamacrawl.cli:app"`

Create README.md with quickstart instructions. Create `.gitignore` with Python, UV, IDE, and `.env` patterns.

Package `__init__.py` files should export version and key classes (leave mostly empty for now).

**Gotchas:**
- Use `uv add` commands after project init, not manual pyproject.toml editing
- LlamaIndex has many optional packages - add core first: `llama-index-core`, `llama-index-readers-firecrawl`, etc.
- Ensure `.env` is in `.gitignore`

---

#### Task 0.3: Create Configuration Templates | Depends on [none]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#configuration-management)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#configuration-management-pattern)

**Instructions**

Files to Create:
- `/.env.example`
- `/config.example.yaml`

Create `.env.example` with all required environment variables (see requirements.md section "Configuration Files"):
- Data source credentials (Firecrawl, GitHub, Reddit, Gmail, Elasticsearch)
- Infrastructure URLs (Qdrant, Neo4j, Redis, TEI, Ollama)
- Observability settings (LOG_LEVEL, PROMETHEUS_PORT)

Use placeholder values like `fc-xxx`, `ghp_xxx`, etc. Include comments explaining where to obtain credentials (e.g., "Get from https://github.com/settings/tokens").

Create `config.example.yaml` with pipeline configuration structure (see requirements.md section "config.yaml"):
- Sources configuration with defaults
- Ingestion parameters (chunk_size, batch_size, retry settings)
- Query parameters (top_k, rerank_top_n, synthesis_model)
- Graph extraction settings
- Logging and metrics configuration

**Gotchas:**
- Do NOT include actual secrets in example files
- Gmail OAuth requires multiple steps - document the flow in comments
- Firecrawl URL should default to `https://firecrawl.tootie.tv`

---

### Phase 1: Core Utilities & Models

#### Task 1.1: Configuration Management Module | Depends on [0.2, 0.3]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#configuration-management-pattern)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#configuration-management)

**Instructions**

Files to Create:
- `/src/llamacrawl/config.py`

Implement configuration management with:
1. **Environment Variables**: Load `.env` using `python-dotenv`
2. **YAML Configuration**: Load `config.yaml` using `PyYAML`
3. **Config Classes**: Use Pydantic for validation
   - `SourceConfig` (per-source settings)
   - `IngestionConfig` (chunk size, batch size, retry settings)
   - `QueryConfig` (top_k, rerank settings)
   - `GraphConfig` (entity extraction settings)
   - `Config` (root config combining all)
4. **Config Loader**: `load_config()` function that:
   - Loads and validates both files
   - Merges environment variables
   - Fails fast if required values missing
   - Returns typed `Config` object
5. **Singleton Pattern**: Global `config` instance

**Gotchas:**
- Use Pydantic v2 syntax
- Environment variables should override YAML values
- Validate URLs, ports, and required fields
- Provide helpful error messages for missing credentials

---

#### Task 1.2: Structured Logging Setup | Depends on [0.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#structured-logging-pattern)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#logging)

**Instructions**

Files to Create:
- `/src/llamacrawl/utils/logging.py`

Implement structured JSON logging:
1. **JSON Formatter**: Use `python-json-logger` to format logs as JSON
2. **Logger Configuration**: `setup_logging()` function that:
   - Configures root logger
   - Sets log level from environment (LOG_LEVEL)
   - Adds console handler with JSON formatter
   - Includes context fields: timestamp, level, logger, message
3. **Context Logger**: Helper function `get_logger(name)` that returns logger with module context
4. **Log Utilities**:
   - `log_execution_time` decorator for timing functions
   - `add_log_context` context manager for temporary context fields

**Gotchas:**
- Ensure timestamps are ISO 8601 format with timezone
- Don't log sensitive information (API keys, passwords)
- Keep log messages concise but informative
- Test that JSON output is valid and parseable

---

#### Task 1.3: Retry Utility | Depends on [1.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#retry-with-exponential-backoff-pattern)
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#error-handling-patterns)

**Instructions**

Files to Create:
- `/src/llamacrawl/utils/retry.py`

Implement exponential backoff retry decorator:
1. **`@retry_with_backoff` Decorator**:
   - Parameters: max_attempts, initial_delay, max_delay, exceptions to catch
   - Exponential backoff: delay *= 2 after each failure
   - Respect `Retry-After` header if present (for rate limits)
   - Log each retry attempt with context
2. **Exception Handling**:
   - Catch transient errors (network timeouts, 5xx status codes)
   - Fail fast on auth errors (401, 403)
   - Configurable exception types via parameter
3. **Async Support**: Implement `@async_retry_with_backoff` for async functions

**Gotchas:**
- Add jitter to prevent thundering herd (random 0-20% variation)
- Log final failure with all attempt details
- Support both sync and async decorators
- Respect HTTP Retry-After header for rate limits

---

#### Task 1.4: Data Models | Depends on [0.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#relevant-tables)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#data-pipeline)

**Instructions**

Files to Create:
- `/src/llamacrawl/models/document.py`

Implement Pydantic models:
1. **`DocumentMetadata`**: Source-specific metadata
   - `source_type`: Literal["firecrawl", "github", "reddit", "gmail", "elasticsearch"]
   - `source_url`: str
   - `timestamp`: datetime
   - `extra`: dict[str, Any] for source-specific fields
2. **`Document`**: Core document model
   - `doc_id`: str (unique identifier)
   - `title`: str
   - `content`: str
   - `content_hash`: str (SHA-256 hash)
   - `metadata`: DocumentMetadata
   - `embedding`: Optional[list[float]] = None
3. **`QueryResult`**: Query response model
   - `answer`: str
   - `sources`: list[SourceAttribution]
   - `query_time_ms`: int
   - `retrieved_docs`: int
   - `reranked_docs`: int
4. **`SourceAttribution`**: Source reference
   - `doc_id`, `source_type`, `title`, `url`, `score`, `snippet`, `timestamp`

**Gotchas:**
- Use proper type hints (no `any`)
- Add JSON schema validation
- Implement `__hash__` and `__eq__` for Document
- Ensure datetime serialization works with JSON

---

#### Task 1.5: Metrics Module (Placeholder) | Depends on [1.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#metrics-prometheus-style)

**Instructions**

Files to Create:
- `/src/llamacrawl/utils/metrics.py`

Create placeholder metrics module:
1. **Metric Types**: Define Counter, Histogram, Gauge classes as simple wrappers
2. **Metric Registry**: Dictionary to store metrics
3. **Decorator Helpers**:
   - `@track_duration` - placeholder for timing
   - `@count_calls` - placeholder for counting
4. **No-op Implementation**: Metrics collect but don't export (Prometheus integration is future work)
5. **Documentation**: Comment explaining full Prometheus integration comes later

This allows code to use metrics decorators now without blocking implementation.

**Gotchas:**
- Keep interface compatible with `prometheus_client` for future migration
- Metrics should be no-ops but not break code
- Include type hints for metric names and labels

---

### Phase 2: Storage Backends

#### Task 2.1: Redis Client | Depends on [1.1, 1.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md](.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#redis-key-schema)

**Instructions**

Files to Create:
- `/src/llamacrawl/storage/redis.py`

Implement Redis client wrapper:
1. **`RedisClient` Class**:
   - Initialize from config (redis_url)
   - Connection pooling with `redis-py`
   - Health check method
2. **State Management Methods**:
   - `get_cursor(source)` / `set_cursor(source, cursor)` - for incremental sync
   - `get_hash(source, doc_id)` / `set_hash(source, doc_id, hash)` - for deduplication
3. **DLQ Methods**:
   - `push_to_dlq(source, doc_data, error)` - add to dead letter queue
   - `get_dlq(source, limit)` - retrieve DLQ entries
   - `clear_dlq(source)` - clear DLQ entries
4. **Distributed Lock Methods**:
   - `acquire_lock(key, ttl)` - SETNX with TTL
   - `release_lock(key)` - DELETE key
   - Context manager: `with_lock(key, ttl)`

Use Redis key naming conventions from shared.md: `hash:<source>:<doc_id>`, `cursor:<source>`, `dlq:<source>`, `lock:ingest:<source>`.

**Gotchas:**
- Use connection pooling (don't create new connections per operation)
- DLQ should use Redis Lists (LPUSH/LRANGE)
- Locks should auto-expire via TTL (default 5 minutes)
- Handle connection failures gracefully with retry logic

---

#### Task 2.2: Qdrant Client | Depends on [1.1, 1.2, 1.4]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/qdrant-integration.docs.md](.docs/plans/llamacrawl-rag-pipeline/qdrant-integration.docs.md)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#qdrant-collection-schema)

**Instructions**

Files to Create:
- `/src/llamacrawl/storage/qdrant.py`

Implement Qdrant client wrapper:
1. **`QdrantClient` Class**:
   - Initialize from config (qdrant_url)
   - Use `qdrant-client` library
   - Health check method
2. **Collection Management**:
   - `create_collection()` - create `llamacrawl_documents` collection
     - Vector size: 1024 (Qwen3-Embedding-0.6B)
     - Distance: Cosine
     - Indexed payload fields: doc_id, source_type, timestamp, content_hash
   - `collection_exists()` - check if collection exists
3. **Document Operations**:
   - `upsert_documents(documents)` - batch upsert with vectors and payload
   - `delete_document(doc_id)` - delete by doc_id
   - `get_document_count(source_type=None)` - count docs, optionally filtered by source
4. **Search Methods**:
   - `search(query_vector, filters, limit)` - vector search with metadata filters
   - Support filters: source_type, date ranges, custom metadata

Use payload structure from shared.md: `doc_id`, `source_type`, `source_url`, `title`, `content`, `timestamp`, `metadata`, `content_hash`.

**Gotchas:**
- Use batch operations for efficiency (100-1000 points per batch)
- Create collection with optimized HNSW parameters (m=16, ef_construct=100)
- Enable quantization (scalar quantization for 4x memory reduction)
- Metadata filters should use payload indexes for performance

---

#### Task 2.3: Neo4j Client | Depends on [1.1, 1.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/neo4j-knowledge-graph.docs.md](.docs/plans/llamacrawl-rag-pipeline/neo4j-knowledge-graph.docs.md)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#neo4j-graph-schema)

**Instructions**

Files to Create:
- `/src/llamacrawl/storage/neo4j.py`

Implement Neo4j client wrapper:
1. **`Neo4jClient` Class**:
   - Initialize from config (neo4j_uri, user, password)
   - Use `neo4j` Python driver
   - Health check method
   - Connection management (driver singleton)
2. **Schema Setup**:
   - `initialize_schema()` - create constraints and indexes
     - Unique constraints: Document.doc_id, User.username, Email.message_id, etc.
     - Indexes: Document.source_type, Document.timestamp, etc.
3. **Node Operations**:
   - `create_document_node(doc_id, properties)` - create Document node
   - `create_entity_node(name, type, properties)` - create Entity node
   - Batch operation: `create_nodes_batch(nodes)` for efficiency
4. **Relationship Operations**:
   - `create_relationship(from_id, to_id, rel_type, properties)` - create relationship
   - Batch operation: `create_relationships_batch(relationships)`
5. **Query Methods**:
   - `traverse_relationships(start_node_id, rel_types, depth)` - graph traversal
   - `find_related_documents(doc_id, max_depth)` - find connected documents

Use node labels and relationship types from shared.md.

**Gotchas:**
- Use parameterized queries (prevent Cypher injection)
- Batch operations should use UNWIND for efficiency
- Transactions should be explicit (driver.session())
- Close sessions properly (use context managers)

---

### Phase 3: Embeddings & Ingestion Core

#### Task 3.1: Custom TEI Embedding Class | Depends on [1.1, 1.2, 1.3]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md](.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md#section-2-llamaindex-custom-embeddings)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#custom-tei-embedding-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/embeddings/tei.py`

Implement custom TEI embedding class:
1. **`TEIEmbedding` Class**: Extend LlamaIndex `BaseEmbedding`
   - Constructor: takes TEI URL from config
   - HTTP client for API calls (use `httpx` or `requests`)
2. **Required Methods**:
   - `_get_query_embedding(query: str) -> list[float]` - embed single query
   - `_get_text_embedding(text: str) -> list[float]` - embed single text
   - `_get_text_embeddings(texts: list[str]) -> list[list[float]]` - batch embed (use TEI batch endpoint)
   - Async variants: `_aget_query_embedding`, etc.
3. **API Integration**:
   - POST to `/embed` endpoint with JSON: `{"inputs": ["text1", "text2"]}`
   - Handle batch sizes (max 128 texts per request)
   - Use retry decorator for transient failures
4. **Configuration**:
   - Embedding dimension: 1024 (Qwen3-Embedding-0.6B)
   - Pooling: last-token (matches TEI config)

**Gotchas:**
- TEI returns list of embeddings in same order as inputs
- Normalize embeddings if needed (check model requirements)
- Batch size should match TEI `--max-client-batch-size` (128)
- Add timeout for HTTP requests (30s default)

---

#### Task 3.2: TEI Reranker Class | Depends on [1.1, 1.2, 1.3]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md](.docs/plans/llamacrawl-rag-pipeline/embeddings-reranking.docs.md#section-4-reranking-with-tei)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#reranking-pipeline-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/embeddings/reranker.py`

Implement TEI reranker:
1. **`TEIRerank` Class**: Extend LlamaIndex `BaseNodePostprocessor`
   - Constructor: takes TEI reranker URL from config, top_n parameter
   - HTTP client for API calls
2. **Reranking Method**:
   - `_postprocess_nodes(nodes, query)` - rerank nodes
   - POST to `/rerank` endpoint with JSON:
     ```json
     {
       "query": "question text",
       "texts": ["doc1", "doc2", ...],
       "return_text": false
     }
     ```
   - Parse response scores and reorder nodes
   - Return top-n nodes
3. **Integration**:
   - Use retry decorator for API failures
   - Log reranking scores for debugging
   - Handle empty node lists gracefully

**Gotchas:**
- TEI reranker returns scores, not new embeddings
- Higher scores = more relevant
- Batch all candidates in single request (more efficient than sequential)
- Preserve node metadata during reranking

---

#### Task 3.3: Deduplication Module | Depends on [1.4, 2.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md](.docs/plans/llamacrawl-rag-pipeline/deduplication-state-management.docs.md#section-1-content-hashing)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#incremental-sync-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/ingestion/deduplication.py`

Implement deduplication logic:
1. **Content Hashing**:
   - `compute_content_hash(content: str) -> str` - SHA-256 hash
   - Normalize content before hashing:
     - Strip whitespace
     - Lowercase
     - Remove punctuation (optional, configurable)
2. **`DocumentDeduplicator` Class**:
   - Constructor: takes RedisClient
   - `is_duplicate(source, doc_id, content)` - check if content unchanged
     - Compute hash
     - Compare with Redis stored hash
     - Return True if identical
   - `mark_processed(source, doc_id, content_hash)` - store hash in Redis
   - `get_deduplicated_documents(source, documents)` - batch deduplication
     - Filter out documents with unchanged hashes
     - Return only new/modified documents

**Gotchas:**
- Hash normalization should be consistent across runs
- Store hashes in Redis with no TTL (permanent until explicitly cleared)
- Batch Redis operations for efficiency (use pipeline)
- Log deduplication hits for monitoring

---

#### Task 3.4: Chunking Strategy | Depends on [1.1, 1.4]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md](.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md#section-7-ingestion-pipeline)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#data-pipeline)

**Instructions**

Files to Create:
- `/src/llamacrawl/ingestion/chunking.py`

Implement document chunking:
1. **Chunking Configuration**: Read from config.yaml (chunk_size, chunk_overlap)
2. **`ChunkingStrategy` Class**:
   - `chunk_document(document: Document) -> list[Document]` - split into chunks
   - Use LlamaIndex `SentenceSplitter` with configured size/overlap
   - Preserve metadata in chunks
   - Add chunk index to metadata: `chunk_index`, `total_chunks`
3. **Chunking Options**:
   - Fixed-size chunking (default: 512 tokens, overlap 50)
   - Sentence-aware splitting (don't break mid-sentence)
   - Metadata preservation across chunks
4. **Integration Helper**:
   - `create_chunking_transformation(config)` - returns LlamaIndex transformation object

**Gotchas:**
- Chunk size is in tokens, not characters (use LlamaIndex tokenizer)
- Overlap prevents losing context at chunk boundaries
- Each chunk should be independently searchable
- Very small documents (< chunk size) should remain unchanged

---

#### Task 3.5: Core Ingestion Pipeline | Depends on [2.1, 2.2, 2.3, 3.1, 3.3, 3.4]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md](.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md#section-7-ingestion-pipeline)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#ingestionpipeline-with-caching-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/ingestion/pipeline.py`

Implement ingestion orchestration:
1. **`IngestionPipeline` Class**:
   - Constructor: takes config, storage clients (Redis, Qdrant, Neo4j), embedding model
   - Initialize LlamaIndex IngestionPipeline with:
     - Transformations: [SentenceSplitter, TEIEmbedding]
     - Docstore: RedisDocumentStore (for caching)
     - Vector store: QdrantVectorStore
2. **Ingestion Methods**:
   - `ingest_documents(source, documents)` - main ingestion flow
     - Deduplication check (via DocumentDeduplicator)
     - Run LlamaIndex pipeline (chunking + embedding + vector store)
     - Extract entities/relationships (PropertyGraphIndex)
     - Store in Neo4j
     - Update Redis cursor
     - Log progress
   - `ingest_with_lock(source, documents)` - wrap with distributed lock
3. **Error Handling**:
   - Catch exceptions per document
   - Log errors
   - Push failed documents to DLQ
   - Continue processing remaining documents
4. **Progress Tracking**:
   - Log every N documents processed
   - Return summary: total, processed, deduplicated, failed

**Gotchas:**
- Use LlamaIndex IngestionPipeline, don't reinvent the wheel
- RedisDocumentStore enables incremental updates (skips unchanged docs)
- PropertyGraphIndex should run after vector storage
- Distributed lock prevents concurrent ingestion of same source

---

### Phase 4: Data Source Readers

#### Task 4.1: Base Reader Interface | Depends on [1.1, 1.4, 2.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#multi-source-ingestion-pattern)
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-6-common-patterns)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/base.py`

Implement abstract base reader:
1. **`BaseReader` Abstract Class**:
   - Constructor: takes source name, config, RedisClient
   - Abstract methods (to be implemented by subclasses):
     - `load_data() -> list[Document]` - load documents from source
     - `supports_incremental_sync() -> bool` - whether source supports incremental sync
   - Common methods (implemented in base):
     - `get_last_cursor() -> Optional[str]` - retrieve cursor from Redis
     - `set_last_cursor(cursor: str)` - store cursor in Redis
     - `get_source_config() -> dict` - get source-specific config from config.yaml
2. **Helpers**:
   - `validate_credentials()` - check required env vars exist
   - `get_api_client()` - lazy initialization of API client
3. **Logging**: Include source name in all log messages

**Gotchas:**
- Cursor storage is Redis-backed (use `cursor:<source>` key)
- validate_credentials should fail fast if missing
- Each reader subclass implements load_data differently
- Common error handling (retry, logging) should be in base class

---

#### Task 4.2: Firecrawl Reader | Depends on [4.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-1-firecrawlwebreader)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#1-firecrawl-reader)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/firecrawl.py`

Implement Firecrawl reader:
1. **`FirecrawlReader` Class**: Extends BaseReader
   - Constructor: validate FIRECRAWL_API_URL and FIRECRAWL_API_KEY
   - Use LlamaIndex `FireCrawlWebReader` internally (now supports Firecrawl v2 SDK as of PR #19773)
2. **`load_data()` Method**:
   - Accept URL(s) from config or parameters
   - Support modes: scrape (single URL), crawl (full site), map (URL discovery), extract (structured data)
   - Use configured parameters:
     - `limit` (max_pages): default 1000
     - `maxDiscoveryDepth`: default 3 for crawl mode (v2 parameter name)
   - Convert FireCrawl results to Document model
   - Add metadata: source_type="firecrawl", source_url, timestamp
3. **Configuration**:
   - Read `sources.firecrawl` from config.yaml
   - Support URL lists for batch scraping
   - Formats: markdown (default) or html
4. **No Incremental Sync**: `supports_incremental_sync() -> False`

**Gotchas:**
- FireCrawlWebReader now uses v2 SDK - ensure you have latest llama-index-readers-web package
- Firecrawl API rate limits - use retry decorator
- Crawl mode can return many documents - respect max_pages limit (set via `limit` parameter)
- `limit` and `maxDepth` are API request parameters, not environment variables
- Validate URLs before sending to Firecrawl

---

#### Task 4.3: GitHub Reader | Depends on [4.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-2-githubrepositoryreader)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#2-github-reader)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/github.py`

Implement GitHub reader:
1. **`GitHubReader` Class**: Extends BaseReader
   - Constructor: validate GITHUB_TOKEN
   - Use LlamaIndex `GitHubRepositoryReader` and `GitHubIssuesClient`
   - Use PyGithub for PR search queries
2. **`load_data()` Method**:
   - Read repositories from config: `sources.github.repositories`
   - For each repository:
     - Load repository files (filter by extensions from config)
     - Load issues (if `include_issues: true`) - use `since` parameter for incremental
     - Load PRs (if `include_prs: true`) - use Search API (see below)
     - Load discussions (if `include_discussions: true`)
   - Convert to Document model with metadata
3. **Incremental Sync**:
   - **For Issues:** Use `since` parameter with last cursor timestamp (filters by last updated time)
   - **For PRs:** Use GitHub Search API instead of List API (PR List API lacks `since` parameter)
     - Query: `repo:owner/name is:pr updated:>=YYYY-MM-DD`
     - Use `github.search_issues()` with filter `is:pull-request`
     - Note: Search API has lower rate limit (30 requests/minute)
   - Update cursor to latest `updated_at` timestamp from all fetched items
   - `supports_incremental_sync() -> True`
4. **Entity Extraction Metadata**:
   - Add GitHub-specific fields: repo_owner, repo_name, issue_number, pr_number, author

**Gotchas:**
- GitHub API rate limits: REST API (5000 req/hour), Search API (30 req/minute) - handle 403 responses
- Use PAT (Personal Access Token) with appropriate scopes (repo, read:discussion)
- File content can be large - filter by extensions (e.g., .md, .py, .ts)
- Issues `since` parameter filters by UPDATE time, not creation time (this is correct for incremental sync)
- PRs require Search API for timestamp filtering - use PyGithub's `search_issues()` method

---

#### Task 4.4: Reddit Reader | Depends on [4.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-3-redditreader)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#3-reddit-reader)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/reddit.py`

Implement Reddit reader:
1. **`RedditReader` Class**: Extends BaseReader
   - Constructor: validate REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
   - Use PRAW library directly (LlamaIndex RedditReader is simple wrapper)
2. **`load_data()` Method**:
   - Read subreddits from config: `sources.reddit.subreddits`
   - For each subreddit:
     - Fetch posts (limit from config, max 1000 due to Reddit API hard cap)
     - Include comments and nested threads
   - Convert to Document model with metadata
3. **Incremental Sync**:
   - Store last post `created_utc` timestamp in cursor
   - Fetch posts and filter client-side by timestamp (posts created after cursor)
   - **CRITICAL LIMITATION:** Reddit API hard caps ALL listings at 1000 items maximum
   - For large/active subreddits, implement time-windowing strategy:
     - Query by time ranges (e.g., weekly chunks)
     - Use subreddit.search() with `timestamp:start..end` syntax
   - `supports_incremental_sync() -> True` (with limitations)
4. **Metadata**:
   - Add Reddit-specific fields: subreddit, post_id, author, score, created_utc, comment_id (for comments)

**Gotchas:**
- **CRITICAL:** Reddit hard limits ALL listings to 1000 items - this is an upstream API limitation, not PRAW
- PRAW requires all three credentials (client ID, secret, user agent)
- Comment threads can be deeply nested - limit depth (e.g., 5 levels)
- Posts can have many comments - may need to limit (e.g., top 100 per post)
- For high-volume subreddits, cannot fetch complete history - implement time-windowing
- Reddit API rate limits - PRAW handles automatically but be aware
- No true `since` parameter - must fetch and filter client-side within 1000-item constraint

---

#### Task 4.5: Elasticsearch Reader | Depends on [4.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-4-elasticsearchreader)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#4-elasticsearch-reader)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/elasticsearch.py`

Implement Elasticsearch reader:
1. **`ElasticsearchReader` Class**: Extends BaseReader
   - Constructor: validate ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY
   - Use `elasticsearch-py` client directly (for modern `search_after` support)
   - Consider using LlamaIndex `ElasticsearchReader` as fallback if it uses scroll API
2. **`load_data()` Method**:
   - Read indices from config: `sources.elasticsearch.indices`
   - Support index patterns (e.g., "docs-*", "logs-*")
   - **Use `search_after` with Point-in-Time (PIT) for pagination** (Elasticsearch 7.10+)
     - Open PIT: `es.open_point_in_time(index=index_pattern, keep_alive="5m")`
     - Paginate with `search_after` parameter using sort values from last hit
     - Close PIT when done
   - **Fallback to scroll API** for older Elasticsearch versions (< 7.10)
   - Map Elasticsearch fields to Document model:
     - Configurable field mappings (title, content, timestamp)
   - Add metadata: index name, document _id
3. **Incremental Sync**:
   - Use timestamp field for filtering (if available)
   - Store last timestamp in cursor
   - Query: `{"range": {"timestamp": {"gt": last_cursor}}}`
   - `supports_incremental_sync() -> bool` (depends on index having timestamp field)
4. **Bulk Loading**:
   - Use batch_size from config (default 200-1000 for search_after)

**Gotchas:**
- **Scroll API is deprecated** - use `search_after` + PIT for Elasticsearch 7.10+
- search_after requires sorted results - ensure sort parameter includes unique tie-breaker (e.g., _id)
- Not all indices have timestamp fields - make incremental sync optional
- Field mappings vary per index - make configurable
- PIT must be explicitly closed to free resources: `es.close_point_in_time(pit_id)`
- For Elasticsearch < 7.10, fall back to scroll API (still functional but not recommended)

---

#### Task 4.6: Gmail Reader | Depends on [4.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md](.docs/plans/llamacrawl-rag-pipeline/data-source-readers.docs.md#section-5-gmailreader)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#5-gmail-reader)

**Instructions**

Files to Create:
- `/src/llamacrawl/readers/gmail.py`

Implement Gmail reader:
1. **`GmailReader` Class**: Extends BaseReader
   - Constructor: validate GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN
   - Use LlamaIndex `GmailReader` with OAuth credentials
2. **`load_data()` Method**:
   - Read labels from config: `sources.gmail.labels` (e.g., ["INBOX", "SENT"])
   - Build query string with Gmail search operators
   - Fetch messages using query parameter
   - Parse email content (subject, body, sender, recipients, timestamp)
   - Include attachment metadata if configured
   - Convert to Document model
3. **Incremental Sync**:
   - **NOTE:** LlamaIndex GmailReader does NOT support `historyId`-based incremental sync
   - **Use query-based filtering instead** with Gmail search operators:
     - Store last sync date in cursor (format: YYYY/MM/DD)
     - Build query: `after:{last_sync_date} label:INBOX`
     - Example: `after:2024/09/30 label:INBOX` fetches emails after Sept 30, 2024
   - Update cursor to current date after successful sync
   - `supports_incremental_sync() -> True`
4. **OAuth Flow Helper**:
   - Implement `get_refresh_token()` helper for initial OAuth setup
   - Document OAuth setup process in docstring
   - Instructions for obtaining refresh token via OAuth consent flow

**Gotchas:**
- Gmail API requires OAuth 2.0 - refresh token must be obtained manually first (one-time setup)
- **LlamaIndex GmailReader does NOT support Gmail historyId** - use date-based queries instead
- Gmail search operator date format: YYYY/MM/DD (not ISO 8601)
- Query operators: `after:`, `before:`, `from:`, `to:`, `subject:`, `label:`, `has:attachment`
- Email body can be HTML or plain text - extract text content
- Attachments are separate API calls - metadata only (don't download files)
- Gmail API quota: 1 billion quota units/day - be mindful of batch sizes
- Date-based sync may re-fetch recently modified emails (less efficient than historyId)

---

### Phase 5: Query Engine

#### Task 5.1: Query Engine Core | Depends on [2.2, 2.3, 3.1, 3.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md](.docs/plans/llamacrawl-rag-pipeline/llamaindex-patterns.docs.md#section-6-query-engine-patterns)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#hybrid-search-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/query/engine.py`

Implement query engine:
1. **`QueryEngine` Class**:
   - Constructor: takes config, storage clients, embedding model, reranker
   - Initialize LlamaIndex components:
     - VectorStoreIndex from Qdrant
     - PropertyGraphIndex from Neo4j
     - Reranker postprocessor
2. **`query()` Method**:
   - Input: query text, optional filters (source_type, date range)
   - Steps:
     1. Generate query embedding (TEIEmbedding)
     2. Vector search in Qdrant (top_k candidates, default 20)
     3. Apply metadata filters
     4. Rerank results (TEIRerank, top_n, default 5)
     5. Graph traversal (find related documents via Neo4j)
     6. Return ranked results with metadata
   - Return: list of Document with scores
3. **Filter Support**:
   - `sources: list[str]` - filter by source_type
   - `after: datetime` - filter by timestamp
   - `before: datetime` - filter by timestamp
   - Custom metadata filters (e.g., `repo: "owner/name"`)
4. **Integration**:
   - Use LlamaIndex RetrieverQueryEngine or build custom retriever
   - Combine vector retriever with graph traversal

**Gotchas:**
- Metadata filters should be applied at Qdrant query time (not post-filtering)
- Graph traversal can be slow - limit depth (max 2 hops)
- Reranking is critical - don't skip even if slow
- Log query performance metrics (time per stage)

---

#### Task 5.2: Synthesis Module | Depends on [1.1, 5.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#query-pipeline)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#source-attribution-pattern)

**Instructions**

Files to Create:
- `/src/llamacrawl/query/synthesis.py`

Implement answer synthesis:
1. **`AnswerSynthesizer` Class**:
   - Constructor: takes config (Ollama URL, model name)
   - Use LlamaIndex `Ollama` LLM integration
2. **`synthesize()` Method**:
   - Input: query text, retrieved documents with scores
   - Steps:
     1. Format context from documents (include snippets)
     2. Build prompt with context and query
     3. Call Ollama API for synthesis (model from config, e.g., "llama3.1:8b")
     4. Parse response
     5. Add inline citations [1][2] referencing source documents
   - Return: QueryResult model (answer + sources + metadata)
3. **Source Attribution**:
   - Create SourceAttribution objects for each document
   - Include: doc_id, source_type, title, url, score, snippet, timestamp
   - Append to QueryResult.sources
4. **Prompt Engineering**:
   - System prompt: "You are a helpful assistant. Answer based on the provided context. Cite sources using [1], [2], etc."
   - Format context clearly with source numbers

**Gotchas:**
- Ollama model must be pulled first (`ollama pull llama3.1:8b`)
- Context length limits - truncate documents if needed (keep most relevant)
- Inline citations should match source list indexes
- Snippets should be short (100-200 chars) but informative

---

### Phase 6: CLI Interface

#### Task 6.1: CLI Core | Depends on [1.1, 1.2]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#user-flows)

**Instructions**

Files to Create:
- `/src/llamacrawl/cli.py`

Implement CLI with Typer:
1. **CLI App Setup**:
   - Create Typer app
   - Add version command
   - Setup logging on app startup
2. **Commands**:
   - `ingest <source>` - trigger ingestion for a source
   - `query <text>` - query the RAG system
   - `status` - show system status
   - `init` - initialize infrastructure (create collections, indexes)
3. **Global Options**:
   - `--config` - path to config.yaml (default: ./config.yaml)
   - `--log-level` - override LOG_LEVEL env var
4. **Error Handling**:
   - Catch exceptions and display user-friendly messages
   - Exit codes: 0 (success), 1 (error), 2 (invalid usage)

**Gotchas:**
- Load config early (before running commands)
- Validate config before proceeding
- Use rich text formatting for output (Typer supports this)
- Log to stdout for CLI visibility

---

#### Task 6.2: Ingest Command | Depends on [3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#flow-1-initial-data-ingestion)
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#multi-source-ingestion-pattern)

**Instructions**

Files to Modify:
- `/src/llamacrawl/cli.py`

Implement `ingest` command:
1. **Command Signature**:
   - `ingest <source>` - source name (firecrawl, github, reddit, gmail, elasticsearch)
   - Options:
     - `--full` - force full re-ingestion (ignore cursor)
     - `--limit <n>` - limit number of documents
2. **Implementation**:
   - Validate source name
   - Check source is enabled in config
   - Instantiate appropriate reader class
   - Instantiate IngestionPipeline
   - Call `pipeline.ingest_with_lock(source, reader.load_data())`
   - Display progress (use Typer progress bar or rich console)
   - Print summary: total docs, processed, deduplicated, failed
3. **Error Handling**:
   - Catch reader errors (auth failures, network issues)
   - Catch ingestion errors
   - Display user-friendly error messages

**Gotchas:**
- Distributed lock prevents concurrent ingestion - inform user if locked
- Progress updates should be real-time (not just at end)
- Handle KeyboardInterrupt gracefully (Ctrl+C)
- Log detailed info but display summary to user

---

#### Task 6.3: Query Command | Depends on [5.1, 5.2, 6.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#flow-3-querying-the-rag-system)
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#output-format)

**Instructions**

Files to Modify:
- `/src/llamacrawl/cli.py`

Implement `query` command:
1. **Command Signature**:
   - `query <text>` - query text
   - Options:
     - `--sources <list>` - filter by source types (comma-separated)
     - `--after <date>` - filter by date (YYYY-MM-DD format)
     - `--before <date>` - filter by date
     - `--top-k <n>` - override top_k from config
     - `--output-format <format>` - json or text (default text)
2. **Implementation**:
   - Parse query text and options
   - Instantiate QueryEngine and AnswerSynthesizer
   - Build filters from options
   - Call `query_engine.query(text, filters)`
   - Call `synthesizer.synthesize(text, results)`
   - Format output based on --output-format
3. **Output Formatting**:
   - **Text format**: Pretty-print answer with sources list
   - **JSON format**: Dump QueryResult model as JSON
   - Include query time and stats

**Gotchas:**
- Date parsing should handle multiple formats (YYYY-MM-DD, ISO 8601)
- Source list should be validated (only allowed source types)
- JSON output should be valid and parseable
- Handle case where no results found

---

#### Task 6.4: Status Command | Depends on [2.1, 2.2, 2.3, 6.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#flow-4-monitoring-status)

**Instructions**

Files to Modify:
- `/src/llamacrawl/cli.py`

Implement `status` command:
1. **Command Signature**:
   - `status` - no arguments
   - Options:
     - `--source <name>` - show status for specific source
     - `--format <format>` - json or text (default text)
2. **Implementation**:
   - Query storage backends for stats:
     - Qdrant: total documents, documents per source (call `get_document_count()`)
     - Neo4j: node counts by label (call `get_node_counts()`)
     - Redis: cursor values, DLQ sizes (call `get_dlq()` per source)
   - Check infrastructure health:
     - Qdrant, Neo4j, Redis health checks
     - TEI embeddings, TEI reranker, Ollama health checks
   - Display summary
3. **Output**:
   - Service health (✓ or ✗ for each)
   - Document counts per source
   - Last sync timestamps (from cursors)
   - DLQ sizes (errors per source)

**Gotchas:**
- Health checks should have short timeouts (5s)
- Some services might be down - handle gracefully
- Last sync timestamp might be missing for sources never ingested
- DLQ entries should show count and sample error messages

---

#### Task 6.5: Init Command | Depends on [2.2, 2.3, 6.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#development-workflow)

**Instructions**

Files to Modify:
- `/src/llamacrawl/cli.py`

Implement `init` command:
1. **Command Signature**:
   - `init` - initialize infrastructure
   - Options:
     - `--force` - recreate collections/indexes even if they exist
2. **Implementation**:
   - Check infrastructure health (Qdrant, Neo4j, Redis)
   - Qdrant: Create collection (via `QdrantClient.create_collection()`)
   - Neo4j: Initialize schema (via `Neo4jClient.initialize_schema()`)
   - Redis: Verify connection (via `RedisClient.health_check()`)
   - Display success/failure for each step
3. **Force Mode**:
   - If --force, delete existing collections/indexes first
   - Warn user that this is destructive

**Gotchas:**
- This should be run once before first use
- --force is dangerous - require confirmation (Typer.confirm())
- Some steps may fail - make idempotent where possible
- Neo4j schema initialization may take time (constraints + indexes)

---

### Phase 7: Integration & Testing

#### Task 7.1: Integration Test Suite | Depends on [6.2, 6.3, 6.4]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/shared.md](.docs/plans/llamacrawl-rag-pipeline/shared.md#testing-strategy)

**Instructions**

Files to Create:
- `/tests/integration/test_ingestion.py`
- `/tests/integration/test_query.py`
- `/tests/integration/conftest.py`

Implement integration tests:
1. **Test Fixtures** (conftest.py):
   - `docker_services` - ensure Docker Compose services are running
   - `test_config` - load test configuration
   - `test_documents` - sample documents for testing
2. **Ingestion Tests** (test_ingestion.py):
   - Test ingestion of sample documents
   - Verify documents stored in Qdrant
   - Verify entities/relationships in Neo4j
   - Test deduplication (ingest same document twice)
   - Test incremental sync
3. **Query Tests** (test_query.py):
   - Test basic vector search
   - Test with metadata filters
   - Test reranking
   - Test graph traversal
   - Test synthesis

**Gotchas:**
- Integration tests require Docker services running (check in fixtures)
- Use small test datasets (don't ingest thousands of docs)
- Clean up test data after tests (delete collections, clear Redis)
- Tests should be idempotent (can run multiple times)

---

#### Task 7.2: End-to-End Test | Depends on [7.1]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md#success-criteria)

**Instructions**

Files to Create:
- `/tests/integration/test_e2e.py`

Implement E2E test:
1. **E2E Workflow Test**:
   - Initialize infrastructure (`init` command)
   - Ingest sample documents from Firecrawl (small website)
   - Query for information from ingested documents
   - Verify query results include correct sources
   - Verify answer quality (contains expected keywords)
2. **Test Flow**:
   - Simulates user workflow from requirements.md (Flow 1 + Flow 3)
   - Uses CLI commands (invoke via subprocess or Typer testing)
   - Asserts on output and database state

**Gotchas:**
- This test is slow (full pipeline) - mark with `@pytest.mark.slow`
- Requires real API calls (Firecrawl, Ollama) - may need mocking for CI
- Test dataset should be deterministic (same results every time)
- Verify multiple stages: ingestion, vector storage, graph extraction, query, synthesis

---

#### Task 7.3: Documentation | Depends on [none]

**READ THESE BEFORE TASK**
- [.docs/plans/llamacrawl-rag-pipeline/requirements.md](.docs/plans/llamacrawl-rag-pipeline/requirements.md)

**Instructions**

Files to Create:
- `/README.md` (update with comprehensive docs)
- `/docs/setup.md`
- `/docs/configuration.md`
- `/docs/usage.md`
- `/docs/architecture.md`

Update documentation:
1. **README.md**:
   - Project overview
   - Quick start guide
   - Installation instructions
   - Basic usage examples
   - Links to detailed docs
2. **setup.md**:
   - Prerequisites
   - Infrastructure deployment (Docker Compose)
   - Python environment setup (UV)
   - Credential configuration
   - Running `init` command
3. **configuration.md**:
   - Detailed `.env` documentation
   - Detailed `config.yaml` documentation
   - Per-source configuration guides (OAuth setup for Gmail, etc.)
4. **usage.md**:
   - CLI command reference
   - Common workflows
   - Troubleshooting
5. **architecture.md**:
   - System architecture diagram
   - Component descriptions
   - Data flow diagrams

**Gotchas:**
- Keep README concise (detailed docs in /docs/)
- Include code examples and screenshots
- Document common errors and solutions
- Link to external docs (LlamaIndex, Qdrant, Neo4j)

---

## Advice

### Critical Path Dependencies
The critical path for first working prototype is: **0.1 → 0.2 → 1.1 → 1.2 → 2.1 → 2.2 → 3.1 → 3.3 → 3.4 → 3.5 → 4.1 → 4.2 → 6.1 → 6.2**. This gets you infrastructure + ingestion of one source (Firecrawl) + CLI. Everything else can be done in parallel after these tasks.

### Parallel Work Opportunities
- **Phase 0**: Tasks 0.1, 0.2, 0.3 can all run in parallel (different files, no dependencies)
- **Phase 1**: Tasks 1.2, 1.3, 1.4, 1.5 can run in parallel after 1.1 completes (only depend on config)
- **Phase 2**: Tasks 2.1, 2.2, 2.3 can run in parallel (independent storage backends)
- **Phase 3**: Tasks 3.1 and 3.2 can run in parallel (both only depend on config/logging/retry)
- **Phase 4**: All reader tasks (4.2-4.6) can run in parallel after 4.1 completes
- **Phase 6**: Tasks 6.2, 6.3, 6.4, 6.5 can run in parallel after 6.1 completes

### Common Pitfalls to Avoid

**Authentication Complexity**: Gmail OAuth is the most complex auth setup. Create a helper script for obtaining refresh tokens. Document the process thoroughly. Test with a dedicated test account.

**GPU Resource Contention**: All GPU services (TEI embeddings, TEI reranker, Ollama) share the same GPU. Monitor VRAM usage. If Ollama fails to load models, it's likely VRAM exhaustion. Consider using smaller Ollama models initially (e.g., llama3.1:8b instead of 70b).

**Neo4j PropertyGraphIndex Integration**: LlamaIndex's PropertyGraphIndex API changed significantly in recent versions. Use `SimpleLLMPathExtractor` for automatic entity extraction, NOT the legacy `KnowledgeGraphIndex`. The research docs have the correct patterns.

**Redis Connection Pooling**: Don't create new Redis connections per operation. Use a singleton RedisClient with connection pooling. Otherwise, you'll hit connection limits quickly.

**Qdrant Collection Creation**: Create the collection with indexed payload fields from the start. Adding indexes later requires rebuilding the collection. Key indexed fields: `doc_id`, `source_type`, `timestamp`, `content_hash`.

**LlamaIndex Settings vs ServiceContext**: LlamaIndex deprecated `ServiceContext` in favor of global `Settings` object. Use `Settings.embed_model = tei_embedding` instead of creating ServiceContext. All research docs use the new pattern.

**Batch Operations**: Always batch when possible. Qdrant: 100-1000 points per upsert. TEI: 32-128 texts per embed request. Neo4j: use UNWIND for batch Cypher writes. Single operations will be 10-100x slower.

**Content Hashing Normalization**: Be consistent with content normalization before hashing. If you change normalization (e.g., add/remove punctuation removal), all hashes become invalid. Document the normalization strategy and don't change it.

**Error Handling in Ingestion**: Ingestion should never halt completely on single document failures. Catch exceptions per document, log errors, push to DLQ, and continue. Otherwise, one bad document blocks the entire pipeline.

**TEI Model Dimensions**: Qwen3-Embedding-0.6B outputs 1024-dim vectors. Qdrant collection must be created with `vector_size=1024`. Mismatched dimensions will cause cryptic errors during upsert.

**Firecrawl v2 vs LlamaIndex**: The LlamaIndex FireCrawlWebReader may still use v0 API (as of January 2025). Verify version. If it's v0, consider using Firecrawl Python SDK directly and wrapping it yourself. The research docs have examples of both approaches.

**Ollama Model Pulling**: Ollama models must be pulled before use. Add a check in synthesis module: if model not available, call `ollama pull <model>` automatically. Document that first synthesis call may take 5-10 minutes for model download.

**Docker Context**: All Docker commands must use `--context docker-mcp-steamy-wsl` to deploy to remote server. Add this to all documentation. Consider creating a shell alias or wrapper script.

**Configuration Validation**: Fail fast on missing configuration. Check all required environment variables at startup (in config.py). Don't wait until the first API call to discover missing credentials.

**Type Hints Everywhere**: Use proper type hints (no `Any`). This catches bugs early and improves IDE autocomplete. Run `mypy` in strict mode to enforce this.

**Incremental Sync Complexity**: Not all sources support efficient incremental sync. Gmail (historyId) and GitHub (since timestamp) do. Reddit and Elasticsearch require workarounds. Firecrawl doesn't support incremental at all (re-crawl entire site). Set expectations accordingly in docs.

### Testing Strategy Notes

**Unit tests** should mock external services (API calls, database operations). Use `pytest-mock` and `responses` library for HTTP mocking.

**Integration tests** require running Docker Compose services. Use `pytest-docker-compose` plugin or manual service checks in fixtures. Tests should clean up after themselves (delete test data).

**E2E tests** are slow and may hit real APIs. Consider making them optional (run only on demand, not in CI). Use small test datasets to keep runtime under 1 minute.

### Performance Optimization

**Embedding Batch Size**: TEI supports batch embedding. Always batch (32-128 texts). Single-text embedding is 10x slower.

**Qdrant Quantization**: Enable scalar quantization when creating collection. Reduces memory by 4x with minimal accuracy loss. Critical for large corpora.

**Neo4j Batch Writes**: Use Cypher UNWIND for batch operations. Single writes are extremely slow. Batch 100-1000 nodes/relationships per transaction.

**Concurrent Ingestion**: Multiple sources can ingest in parallel. Use `asyncio.gather()` or threading. Distributed locks prevent conflicts.

**Query Optimization**: Apply metadata filters at Qdrant query time (not post-filtering). Saves network bandwidth and processing time. Ensure payload fields are indexed.

### Configuration Tips

**Start with Small Limits**: Set low limits initially (e.g., 100 documents per source) for testing. Increase after verifying pipeline works.

**Test with Single Source**: Get Firecrawl working E2E before adding other sources. It's the simplest (no auth, no incremental sync).

**Monitor Resource Usage**: Watch Docker stats (`docker stats`) to monitor RAM/VRAM usage. Adjust batch sizes if memory pressure.

**Ollama Model Selection**: Start with smaller models (llama3.1:8b) for testing. Larger models (70b) may not fit in VRAM with other services running.

### Documentation Priorities

**OAuth Setup Guide**: Gmail OAuth is complex. Create step-by-step guide with screenshots. Include troubleshooting section.

**Environment Variables**: Document every environment variable in `.env.example` with comments explaining where to obtain values.

**Common Errors**: Create troubleshooting section in docs with common errors and solutions (connection failures, auth errors, OOM, etc.).

**Architecture Diagrams**: Visual diagrams are critical for understanding system. Use Mermaid or draw.io for data flow and component diagrams.