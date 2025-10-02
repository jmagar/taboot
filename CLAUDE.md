# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LlamaCrawl is a multi-source RAG (Retrieval Augmented Generation) pipeline built on LlamaIndex. It ingests data from web content (Firecrawl), GitHub, Reddit, Gmail, and Elasticsearch, stores it in hybrid databases (Qdrant for vectors, Neo4j for knowledge graphs, Redis for state), and provides intelligent query capabilities with source attribution.

## Commands

### Environment Setup
```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --dev
```

### Development Commands
```bash
# Run type checking
uv run mypy src/

# Run linting
ruff check src/

# Format code
ruff format src/

# Run tests
pytest tests/
```

### Application Commands
```bash
# Initialize infrastructure (Qdrant collections, Neo4j schema, Redis)
uv run llamacrawl init

# Ingest data from a source
uv run llamacrawl ingest <source>  # github, reddit, gmail, elasticsearch
uv run llamacrawl ingest github --full  # Force full re-ingestion
uv run llamacrawl ingest reddit --limit 100  # Limit documents

# Firecrawl has direct URL commands (no config.yaml needed)
uv run llamacrawl scrape https://example.com  # Single page
uv run llamacrawl crawl https://example.com --limit 100 --max-depth 2  # Full site
uv run llamacrawl map https://example.com --limit 1000  # URL discovery
uv run llamacrawl extract https://example.com --prompt "Extract product info"  # AI extraction

# Query the system
uv run llamacrawl query "your question"
uv run llamacrawl query "recent issues" --sources github --after 2025-01-01

# Check system status
uv run llamacrawl status
uv run llamacrawl status --source github
```

### Infrastructure Management
```bash
# Deploy services 
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f
```

## Architecture

### Core Pipeline Flow

**Ingestion Pipeline** ([src/llamacrawl/ingestion/pipeline.py](src/llamacrawl/ingestion/pipeline.py)):
1. Reader loads documents → 2. Deduplication check (Redis hash) → 3. LlamaIndex chunking + embedding → 4. Vector storage (Qdrant) → 5. Entity extraction (Neo4j) → 6. Cursor update (Redis)

**Query Pipeline** ([src/llamacrawl/query/engine.py](src/llamacrawl/query/engine.py)):
1. Query embedding (TEI) → 2. Vector search (Qdrant, top_k=20) → 3. Metadata filtering → 4. Reranking (TEI, top_n=5) → 5. Graph traversal (Neo4j, optional) → 6. Answer synthesis (Ollama)

### Key Components

**Configuration** ([src/llamacrawl/config.py](src/llamacrawl/config.py)):
- Two-tier config: `.env` for secrets/URLs, `config.yaml` for pipeline settings
- Pydantic v2 models with strict validation
- Singleton pattern via `get_config()` - loaded once on startup
- Validates that enabled sources have required credentials

**Storage Layer**:
- **Qdrant** ([src/llamacrawl/storage/qdrant.py](src/llamacrawl/storage/qdrant.py)): Vector storage with 1024-dim embeddings, HNSW indexing, optional scalar quantization
- **Neo4j** ([src/llamacrawl/storage/neo4j.py](src/llamacrawl/storage/neo4j.py)): Knowledge graph with entity/relationship extraction via PropertyGraphIndex
- **Redis** ([src/llamacrawl/storage/redis.py](src/llamacrawl/storage/redis.py)): Cursor tracking, content hash deduplication, distributed locks, Dead Letter Queue (DLQ)

**Data Readers** ([src/llamacrawl/readers/](src/llamacrawl/readers/)):
- All extend `BaseReader` abstract class
- Support incremental sync via cursor-based state management in Redis
- Per-reader configuration from `config.yaml`
- Credential validation in constructor (fail fast)
- Return `list[Document]` from `load_data()`

**Embeddings**:
- **TEIEmbedding** ([src/llamacrawl/embeddings/tei.py](src/llamacrawl/embeddings/tei.py)): Text Embeddings Inference integration, implements LlamaIndex `BaseEmbedding` interface
- **TEIRerank** ([src/llamacrawl/embeddings/reranker.py](src/llamacrawl/embeddings/reranker.py)): Reranking postprocessor using TEI reranker endpoint

**Deduplication** ([src/llamacrawl/ingestion/deduplication.py](src/llamacrawl/ingestion/deduplication.py)):
- Content-based hashing (SHA-256) with optional normalization (whitespace, case, punctuation)
- Per-source hash storage in Redis (`dedup:{source}:{doc_id}`)
- Skips unchanged documents automatically

### Document Model

The `Document` class ([src/llamacrawl/models/document.py](src/llamacrawl/models/document.py)) is the universal data structure:
- `doc_id`: Unique identifier (source-specific format)
- `title`: Document title
- `content`: Full text content
- `content_hash`: SHA-256 hash for deduplication
- `metadata`: DocumentMetadata with source_type, source_url, timestamp, extra dict

### CLI Entry Point

[src/llamacrawl/cli.py](src/llamacrawl/cli.py) provides the Typer-based CLI with commands:
- `ingest`: Trigger ingestion with distributed locking
- `query`: Execute RAG query with filters
- `status`: Show service health and document counts
- `init`: Initialize storage backends

## Docker Compose Stack

Services defined in [docker-compose.yaml](docker-compose.yaml):
- `taboot-vectors`: Qdrant with GPU support
- `taboot-embed`: TEI embedding service (Qwen3-Embedding-0.6B)
- `taboot-rerank`: TEI reranker (BAAI/bge-reranker-v2-m3)
- `taboot-graph`: Neo4j community edition
- `taboot-cache`: Redis with persistence
- `taboot-ollama`: Ollama LLM service

All services use `taboot-net` bridge network and NVIDIA GPU device 0.

## Important Patterns

### Error Handling
- **Fail fast on initialization**: Config validation, credential checks, missing dependencies
- **Per-document error handling in ingestion**: Failed documents go to DLQ, processing continues
- **No fallbacks in production**: Throw errors early (per global CLAUDE.md instructions)

### State Management
- **Cursor tracking**: Last sync position stored in Redis (`cursor:{source}`)
- **Distributed locks**: Prevent concurrent ingestion via Redis (`ingest:{source}`)
- **Content hashes**: Track document changes for incremental updates

### LlamaIndex Integration
- Uses `IngestionPipeline` with `RedisDocumentStore` for caching
- `PropertyGraphIndex` with `SimpleLLMPathExtractor` for entity extraction
- `VectorStoreIndex` wraps Qdrant for querying
- Custom TEI embedding/reranking models plugged into LlamaIndex interfaces

### Type Safety
- Strict mypy config: `strict = true`, `disallow_untyped_defs = true`
- Never use `any` type - look up proper types from LlamaIndex, Qdrant, Neo4j SDKs
- Pydantic v2 for all configuration and data models

## Testing Notes

- Test infrastructure is in `tests/` directory
- Pytest with async support (`pytest-asyncio`)
- Mock external services (Qdrant, Neo4j, Redis, TEI) for unit tests
- Integration tests require running Docker Compose stack

## Firecrawl Commands

Firecrawl has dedicated top-level CLI commands that accept URLs directly (no `config.yaml` needed):

**Commands** ([src/llamacrawl/cli_firecrawl.py](src/llamacrawl/cli_firecrawl.py)):

1. **scrape**: Single page scraping
   ```bash
   llamacrawl scrape https://example.com
   llamacrawl scrape https://docs.python.org/3/ --formats markdown --formats links
   ```

2. **crawl**: Full website crawling with depth/limit control
   ```bash
   llamacrawl crawl https://example.com
   llamacrawl crawl https://docs.python.org/ --limit 50 --max-depth 2
   llamacrawl crawl https://blog.example.com --formats markdown --formats html
   ```

3. **map**: URL discovery from sitemaps (no content fetching)
   ```bash
   llamacrawl map https://example.com
   llamacrawl map https://docs.python.org/ --limit 500
   ```

4. **extract**: AI-powered structured data extraction
   ```bash
   llamacrawl extract https://example.com/product --prompt "Extract product name, price, and description"
   llamacrawl extract https://news.example.com/article --schema schema.json
   ```

**How it works**:
1. Command validates URL format (must be http/https)
2. Creates temporary `FirecrawlSourceConfig` with the URL and mode
3. Initializes `FirecrawlReader` with config
4. Runs ingestion pipeline (dedup, embedding, vector storage, graph extraction)
5. Reports document count on completion

**No Incremental Sync**: Firecrawl doesn't support cursor-based sync - each run processes from scratch. Deduplication happens via content hashing in the pipeline.

## Common Gotchas

1. **Embedding dimension must match**: TEI model outputs 1024-dim vectors, Qdrant collection must be configured for 1024
2. **Neo4j graph depth limits**: Keep max_depth ≤ 2 for graph traversal to avoid performance issues
3. **Redis connection pooling**: LlamaIndex `RedisDocumentStore` requires `host` and `port` separately, not full URL
4. **Content hashing is source-scoped**: Hash key is `dedup:{source}:{doc_id}`, not global
5. **Cursor updates only on success**: Only update cursor after all documents processed successfully
6. **LlamaIndex Settings.llm**: Must be set for PropertyGraphIndex entity extraction (uses Ollama)
7. **Firecrawl commands are top-level**: Use `llamacrawl scrape`, not `llamacrawl ingest firecrawl`

## File Organization

```
src/llamacrawl/
├── cli.py                 # Typer CLI entry point
├── config.py              # Config loading and Pydantic models
├── models/
│   └── document.py        # Document and metadata models
├── readers/               # Data source readers
│   ├── base.py           # Abstract BaseReader
│   ├── firecrawl.py      # Web scraping
│   ├── github.py         # GitHub repos/issues/PRs
│   ├── reddit.py         # Reddit posts/comments
│   ├── gmail.py          # Gmail messages
│   └── elasticsearch.py  # Elasticsearch indices
├── ingestion/
│   ├── pipeline.py       # Main IngestionPipeline
│   ├── deduplication.py  # Content hash deduplication
│   └── chunking.py       # Document chunking utilities
├── storage/
│   ├── qdrant.py         # Qdrant vector store client
│   ├── neo4j.py          # Neo4j graph database client
│   └── redis.py          # Redis state/cache client
├── query/
│   ├── engine.py         # QueryEngine for RAG retrieval
│   └── synthesis.py      # Answer synthesis with Ollama
├── embeddings/
│   ├── tei.py            # TEI embedding model
│   └── reranker.py       # TEI reranker
└── utils/
    ├── logging.py        # Structured JSON logging
    ├── retry.py          # Exponential backoff retry
    └── metrics.py        # Prometheus metrics collection
```

## Environment Variables

Required in `.env`:
- `FIRECRAWL_API_URL`, `FIRECRAWL_API_KEY`
- Infrastructure: `QDRANT_URL`, `NEO4J_URI`, `NEO4J_PASSWORD`, `REDIS_URL`, `TEI_EMBEDDING_URL`, `TEI_RERANKER_URL`, `OLLAMA_URL`

Optional (per enabled source):
- GitHub: `GITHUB_TOKEN`
- Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
- Gmail: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`
- Elasticsearch: `ELASTICSEARCH_URL`, `ELASTICSEARCH_API_KEY`
