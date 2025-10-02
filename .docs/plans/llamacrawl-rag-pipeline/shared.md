# LlamaCrawl RAG Pipeline - Shared Architecture Reference

This is a **greenfield project** building a multi-source RAG pipeline with LlamaIndex. The architecture consists of three main layers: **data ingestion** (readers → chunking → deduplication), **storage** (Qdrant vectors, Neo4j graph, Redis state), and **retrieval** (embedding → search → rerank → synthesis). All infrastructure runs via Docker Compose on a remote GPU server (steamy-wsl), while the Python application connects remotely via service endpoints. The system uses custom TEI integration for embeddings/reranking and LlamaIndex's KnowledgeGraphIndex for automatic entity extraction into Neo4j.

## Relevant Files

### Existing Infrastructure
- [/docker-compose.yaml](../../../docker-compose.yaml): Current infrastructure with Qdrant, TEI embeddings, TEI reranker (needs Neo4j, Redis, Ollama added; Firecrawl uses hosted instance)
- [/INIT.md](../../../INIT.md): Original project vision with all planned data sources and tech stack

### Planned Project Structure (to be created)
- `/src/llamacrawl/__init__.py`: Package initialization with version and exports
- `/src/llamacrawl/cli.py`: Typer-based CLI entry point (commands: ingest, query, status)
- `/src/llamacrawl/config.py`: Configuration management loading `.env` and `config.yaml`
- `/src/llamacrawl/readers/base.py`: Abstract base class for all data source readers
- `/src/llamacrawl/readers/firecrawl.py`: FireCrawlWebReader wrapper with retry logic
- `/src/llamacrawl/readers/github.py`: GitHubRepositoryReader with incremental sync
- `/src/llamacrawl/readers/reddit.py`: RedditReader with PRAW integration
- `/src/llamacrawl/readers/elasticsearch.py`: ElasticsearchReader with bulk loading
- `/src/llamacrawl/readers/gmail.py`: GmailReader with OAuth and query-based incremental sync
- `/src/llamacrawl/ingestion/pipeline.py`: Core ingestion orchestration with LlamaIndex IngestionPipeline
- `/src/llamacrawl/ingestion/chunking.py`: Document chunking strategies (semantic, sentence window)
- `/src/llamacrawl/ingestion/deduplication.py`: SHA-256 content hashing with Redis storage
- `/src/llamacrawl/storage/qdrant.py`: QdrantVectorStore wrapper with collection management
- `/src/llamacrawl/storage/neo4j.py`: Neo4jGraphStore wrapper with PropertyGraphIndex
- `/src/llamacrawl/storage/redis.py`: Redis client for state, DLQ, and distributed locks
- `/src/llamacrawl/query/engine.py`: Query engine with hybrid search and graph traversal
- `/src/llamacrawl/query/synthesis.py`: Ollama integration for answer synthesis with source attribution
- `/src/llamacrawl/utils/logging.py`: Structured JSON logging setup
- `/src/llamacrawl/utils/metrics.py`: Prometheus metrics collectors
- `/src/llamacrawl/utils/retry.py`: Exponential backoff retry decorator
- `/src/llamacrawl/models/document.py`: Pydantic models for documents and metadata
- `/pyproject.toml`: UV-based project dependencies and metadata
- `/.env.example`: Template for environment variables (secrets)
- `/config.example.yaml`: Template for pipeline configuration (non-secrets)

## Relevant Tables

### Redis Key Schema
- `hash:<source>:<doc_id>`: SHA-256 content hash for deduplication (String)
- `cursor:<source>`: Last sync cursor/timestamp for incremental sync (String)
- `dlq:<source>`: Dead letter queue for failed documents (List)
- `lock:ingest:<source>`: Distributed lock to prevent duplicate ingestion jobs (String with TTL)

### Qdrant Collection Schema
- **Collection Name**: `llamacrawl_documents`
- **Vector Dimension**: 1024 (Qwen3-Embedding-0.6B output)
- **Distance Metric**: Cosine similarity
- **Payload Fields**:
  - `doc_id`: Unique document identifier (String, indexed)
  - `source_type`: Data source (String, indexed: "firecrawl", "github", "reddit", "gmail", "elasticsearch")
  - `source_url`: Original URL/reference (String)
  - `title`: Document title (String)
  - `content`: Full text content (String)
  - `timestamp`: Document creation/update time (DateTime, indexed)
  - `metadata`: Source-specific metadata (JSON object)
  - `content_hash`: SHA-256 hash for deduplication (String, indexed)

### Neo4j Graph Schema
- **Node Labels**:
  - `Document`: All ingested documents with `doc_id`, `source_type`, `title`, `content_hash`
  - `User`: Authors/senders/posters with `username`, `email`, `platform`
  - `Repository`: GitHub repositories with `owner`, `name`, `url`
  - `Issue`: GitHub issues with `number`, `title`, `state`
  - `PullRequest`: GitHub PRs with `number`, `title`, `state`
  - `Email`: Gmail messages with `message_id`, `subject`, `date`
  - `Person`: Email participants with `email`, `name`
  - `Post`: Reddit posts with `post_id`, `subreddit`, `title`
  - `Comment`: Reddit comments with `comment_id`, `body`
  - `Entity`: Extracted entities with `name`, `type` (person, organization, location, etc.)

- **Relationship Types**:
  - `AUTHORED`: (User)-[:AUTHORED]->(Issue|PullRequest|Post)
  - `SENT`: (Person)-[:SENT]->(Email)
  - `REPLIED_TO`: (Email|Comment)-[:REPLIED_TO]->(Email|Post|Comment)
  - `REFERENCES`: (Issue)-[:REFERENCES]->(PullRequest)
  - `COMMENTED_ON`: (User)-[:COMMENTED_ON]->(Issue|PullRequest|Post)
  - `MENTIONS`: (Document)-[:MENTIONS]->(Entity|Person|User)
  - `BELONGS_TO`: (Issue|PullRequest)-[:BELONGS_TO]->(Repository)
  - `RELATED_TO`: (Document)-[:RELATED_TO]->(Document) (semantic similarity)

## Relevant Patterns

**LlamaIndex Settings Pattern**: Use the global `Settings` object to configure embeddings, LLM, chunk size, and other parameters instead of deprecated `ServiceContext`. Example: `Settings.embed_model = custom_tei_embedding` (see [llamaindex-patterns.docs.md](llamaindex-patterns.docs.md#2-reader-integration))

**Custom TEI Embedding Pattern**: Extend `BaseEmbedding` to create a custom embedding class that calls the TEI HTTP endpoint, implementing `_get_query_embedding()`, `_get_text_embedding()`, and async variants. See complete implementation in [embeddings-reranking.docs.md](embeddings-reranking.docs.md#section-2-llamaindex-custom-embeddings)

**PropertyGraphIndex Pattern**: Use LlamaIndex's `PropertyGraphIndex` with `SimpleLLMPathExtractor` or `SchemaLLMPathExtractor` to automatically extract entities and relationships from documents into Neo4j during ingestion. Configure with `kg_extractors` parameter. (see [neo4j-knowledge-graph.docs.md](neo4j-knowledge-graph.docs.md#section-1-knowledgegraphindex-in-llamaindex))

**Incremental Sync Pattern**: Store source-specific cursors in Redis (`cursor:<source>`), compute SHA-256 content hashes (`hash:<source>:<doc_id>`), and skip documents with unchanged hashes. Use source APIs' native sync mechanisms when available: GitHub Issues `since` parameter (filters by update time), GitHub PRs via Search API with timestamp query, Gmail query-based filtering with `after:` operator, Reddit client-side filtering within 1000-item cap. (see [deduplication-state-management.docs.md](deduplication-state-management.docs.md#section-3-incremental-sync))

**Dead Letter Queue Pattern**: Use Redis Lists to store failed documents as JSON with error details and timestamps. Implement retry logic with exponential backoff and move permanently failed items to DLQ for manual review. Structure: `dlq:<source>` with 7-day TTL. (see [deduplication-state-management.docs.md](deduplication-state-management.docs.md#section-4-dead-letter-queue))

**Distributed Lock Pattern**: Use Redis SETNX with TTL to implement distributed locks preventing concurrent ingestion of the same source. Lock key: `lock:ingest:<source>` with automatic expiration. Use context manager pattern for automatic lock release. (see [deduplication-state-management.docs.md](deduplication-state-management.docs.md#section-5-concurrency-control))

**Hybrid Search Pattern**: Combine dense vector search (Qdrant) with sparse retrieval (BM25) and graph traversal (Neo4j) using LlamaIndex's `QueryFusionRetriever` or custom retrievers. Apply metadata filters before vector search for efficiency. Rerank combined results with TEI reranker. (see [qdrant-integration.docs.md](qdrant-integration.docs.md#section-5-llamaindex-integration))

**Multi-Source Ingestion Pattern**: Create a base `Reader` class with common methods (`load_data()`, `get_last_cursor()`, `set_last_cursor()`), then extend for each source. Use `IngestionPipeline` with Redis caching to handle deduplication automatically. Run sources concurrently with `asyncio.gather()`. (see [data-source-readers.docs.md](data-source-readers.docs.md#section-6-common-patterns))

**Reranking Pipeline Pattern**: After initial vector search retrieves top-k candidates (e.g., 20), pass them through TEI reranker endpoint to get top-n most relevant (e.g., 5). Integrate as LlamaIndex postprocessor using `TEIRerank` class. This significantly improves retrieval quality. (see [embeddings-reranking.docs.md](embeddings-reranking.docs.md#section-4-reranking-with-tei))

**Source Attribution Pattern**: Store document metadata with source URLs in Qdrant payload. After synthesis, format response with inline citations [1][2] and append source list with titles, URLs, scores, snippets, and timestamps. Query Neo4j for authorship relationships to add author attribution. (see [requirements.md](requirements.md#output-format))

**Retry with Exponential Backoff Pattern**: Decorator pattern for API calls with configurable max attempts, initial delay, and max delay. Catch transient errors (network, rate limits), respect `Retry-After` headers, and fail fast on auth errors. Log all retry attempts. (see [data-source-readers.docs.md](data-source-readers.docs.md#error-handling-patterns))

**Configuration Management Pattern**: Split configuration into two files: `.env` for secrets (API keys, passwords) and `config.yaml` for pipeline settings (chunk size, sources config, feature flags). Load with `python-dotenv` and `PyYAML`. Validate on startup and fail fast if required values missing. (see [requirements.md](requirements.md#configuration-management))

**Structured Logging Pattern**: Use Python's `logging` with JSON formatter (via `python-json-logger`). Include context fields: `timestamp`, `level`, `logger`, `message`, plus custom fields like `source`, `doc_id`, `duration_seconds`. Set log level via environment variable. (see [requirements.md](requirements.md#logging))

**IngestionPipeline with Caching Pattern**: Use LlamaIndex's `IngestionPipeline` with `RedisDocumentStore` as cache backend. Configure transformations (chunking, embedding) and let the pipeline handle deduplication automatically via document hashing. Enables incremental re-ingestion without re-embedding unchanged content. (see [llamaindex-patterns.docs.md](llamaindex-patterns.docs.md#section-7-ingestion-pipeline))

**Batch Processing Pattern**: Process documents in batches for efficiency. Qdrant supports batch upserts (100-1000 points per batch), TEI supports batch embedding requests (32-128 texts), and Neo4j supports batch Cypher writes. Use appropriate batch sizes per service to optimize throughput. (see [qdrant-integration.docs.md](qdrant-integration.docs.md#section-3-performance-optimization))

## Relevant Docs

**[llamaindex-patterns.docs.md](llamaindex-patterns.docs.md)**: You _must_ read this when working on LlamaIndex integration, reader setup, index creation, query engines, knowledge graph extraction, ingestion pipelines, or any core LlamaIndex functionality.

**[qdrant-integration.docs.md](qdrant-integration.docs.md)**: You _must_ read this when working on vector storage, collection setup, metadata filtering, hybrid search, performance optimization, or Qdrant client integration.

**[neo4j-knowledge-graph.docs.md](neo4j-knowledge-graph.docs.md)**: You _must_ read this when working on graph storage, PropertyGraphIndex setup, entity extraction, relationship modeling, Cypher queries, or graph-enhanced retrieval.

**[data-source-readers.docs.md](data-source-readers.docs.md)**: You _must_ read this when working on any data source reader (Firecrawl, GitHub, Reddit, Elasticsearch, Gmail), incremental sync, or source-specific integration patterns.

**[deduplication-state-management.docs.md](deduplication-state-management.docs.md)**: You _must_ read this when working on deduplication logic, content hashing, Redis state management, incremental sync cursors, dead letter queues, or distributed locks.

**[embeddings-reranking.docs.md](embeddings-reranking.docs.md)**: You _must_ read this when working on custom embedding integration, TEI API calls, reranking logic, query pipelines, or Qwen3 model configuration.

**[requirements.md](requirements.md)**: You _must_ read this when working on any feature to understand overall requirements, user flows, architecture decisions, configuration structure, deployment strategy, or success criteria.

**[docker-compose.yaml](../../../docker-compose.yaml)**: You _must_ read this when working on infrastructure setup, service configuration, adding new services (Neo4j, Redis, Ollama), or deployment to steamy-wsl.

**[INIT.md](../../../INIT.md)**: Reference this for the original project vision and links to all LlamaIndex reader documentation on LlamaHub.

## External Documentation References

### LlamaIndex Core
- **Main Docs**: https://developers.llamaindex.ai/
- **API Reference**: https://docs.llamaindex.ai/en/stable/api_reference/
- **LlamaHub (Readers)**: https://llamahub.ai/
- **PropertyGraphIndex Guide**: https://docs.llamaindex.ai/en/stable/examples/property_graph/

### Storage Backends
- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Qdrant Python Client**: https://github.com/qdrant/qdrant-client
- **Neo4j Python Driver**: https://neo4j.com/docs/python-manual/current/
- **Redis Python Client**: https://redis-py.readthedocs.io/

### Embeddings & Models
- **HuggingFace TEI**: https://github.com/huggingface/text-embeddings-inference
- **TEI API Docs**: https://huggingface.co/docs/text-embeddings-inference/
- **Qwen3 Embedding Model**: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- **Qwen3 Reranker Model**: https://huggingface.co/tomaarsen/Qwen3-Reranker-0.6B-seq-cls

### Data Source APIs
- **Firecrawl v2 API**: https://docs.firecrawl.dev/
- **GitHub REST API**: https://docs.github.com/en/rest
- **Reddit PRAW**: https://praw.readthedocs.io/
- **Gmail API**: https://developers.google.com/gmail/api
- **Elasticsearch Python**: https://elasticsearch-py.readthedocs.io/

### Tools & Libraries
- **UV Package Manager**: https://docs.astral.sh/uv/
- **Typer CLI**: https://typer.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **Python Logging**: https://docs.python.org/3/library/logging.html

## Development Workflow

### Initial Setup
1. Deploy infrastructure: `docker --context docker-mcp-steamy-wsl compose up -d`
2. Create project structure: `mkdir -p src/llamacrawl/{readers,ingestion,storage,query,utils,models}`
3. Initialize UV project: `uv init` and configure `pyproject.toml`
4. Install dependencies: `uv add llama-index qdrant-client neo4j redis typer pydantic pyyaml python-dotenv`
5. Copy config templates: `cp .env.example .env && cp config.example.yaml config.yaml`
6. Fill in credentials in `.env`

### Implementation Order (Recommended)
1. **Phase 1**: Configuration, logging, utilities (`config.py`, `utils/logging.py`, `utils/retry.py`)
2. **Phase 2**: Storage backends (`storage/redis.py`, `storage/qdrant.py`, `storage/neo4j.py`)
3. **Phase 3**: Custom embeddings (`models/document.py`, TEI embedding class)
4. **Phase 4**: Single reader E2E (`readers/base.py`, `readers/firecrawl.py`, basic `ingestion/pipeline.py`)
5. **Phase 5**: CLI and query (`cli.py`, `query/engine.py`, `query/synthesis.py`)
6. **Phase 6**: Remaining readers (`readers/github.py`, `readers/reddit.py`, etc.)
7. **Phase 7**: Advanced features (deduplication, reranking, graph queries)
8. **Phase 8**: Observability (metrics, structured logging enhancements)

### Testing Strategy
- **Unit Tests**: Test individual components (readers, utils) with mocked external services
- **Integration Tests**: Test storage backends with real Docker Compose services
- **E2E Tests**: Full ingestion and query workflows with small test datasets
- **Manual Testing**: CLI commands during development

### Key Design Principles
1. **Modularity**: Each reader is independent, storage backends are swappable
2. **Fail Fast**: Validate configuration and credentials on startup
3. **Observability**: Log all operations with structured context
4. **Resilience**: Retry transient failures, use DLQ for permanent failures
5. **Efficiency**: Batch operations, cache embeddings, skip unchanged documents
6. **Type Safety**: Use Pydantic models and type hints throughout
7. **Extensibility**: Design for easy addition of new data sources and storage backends