# LlamaCrawl RAG Pipeline - Requirements Document

**Version:** 1.0
**Date:** 2025-09-30
**Status:** Draft

## Overview

LlamaCrawl is a multi-source RAG (Retrieval Augmented Generation) pipeline built on LlamaIndex that ingests data from multiple sources (web content, GitHub, Reddit, Gmail, Elasticsearch), stores it in vector and graph databases, and provides intelligent query capabilities through a Model Context Protocol (MCP) server interface.

This replaces a previous custom Firecrawl-based implementation with a cleaner, more maintainable architecture using stock components.

---

## Goals

### Primary Goals
1. Build an operational RAG pipeline that ingests data from 5 initial sources
2. Store data in Qdrant (vectors), Neo4j (relationships), and Redis (state/cache)
3. Enable intelligent querying with source attribution and filtering
4. Deploy infrastructure to remote server (steamy-wsl) via Docker Compose
5. Provide CLI interface for testing and development

### Future Goals (Out of Scope for Initial Release)
- Full MCP server interface
- Web UI and chat interface
- Multi-user authentication
- Advanced scheduling mechanisms
- Additional data sources beyond the initial 5

---

## Scope

### In Scope - Initial Data Sources
1. **Firecrawl** - Web scraping and crawling via self-hosted instance
2. **GitHub** - Repositories, issues, pull requests, discussions
3. **Reddit** - Posts, comments from specific subreddits
4. **Elasticsearch** - Existing indexed documents
5. **Gmail** - Email messages and threads

### Architecture Foundation
- Extensible reader plugin system for easy addition of new sources
- Modular ingestion pipeline supporting concurrent source processing
- Unified configuration and credential management
- Comprehensive error handling and retry logic

---

## User Flows

### Flow 1: Initial Data Ingestion
1. User configures data sources in YAML config file
2. User adds credentials to `.env` file
3. User runs `llamacrawl ingest <source>` command
4. System:
   - Authenticates with source API
   - Loads documents via LlamaIndex reader
   - Chunks and embeds content via TEI
   - Stores vectors in Qdrant
   - Extracts entities/relationships and stores in Neo4j
   - Updates sync cursor in Redis
   - Logs progress and errors
5. User sees completion status or errors

### Flow 2: Incremental Sync
1. User runs `llamacrawl ingest <source>` on previously synced source
2. System:
   - Retrieves last sync cursor from Redis
   - Fetches only new/modified items using source-specific APIs
   - Computes hash of content for deduplication
   - Skips unchanged content
   - Updates vectors for modified content
   - Updates Neo4j relationships
   - Updates sync cursor in Redis

### Flow 3: Querying the RAG System
1. User runs `llamacrawl query "question text" --sources gmail,github`
2. System:
   - Generates query embedding via TEI
   - Searches Qdrant with metadata filters (source type)
   - Retrieves top-k candidates
   - Reranks results via TEI reranker
   - Queries Neo4j for related entities/relationships
   - Synthesizes answer via Ollama with source attribution
   - Returns formatted response with sources

### Flow 4: Monitoring Status
1. User runs `llamacrawl status`
2. System displays:
   - Active ingestion jobs
   - Document counts per source
   - Last sync timestamps
   - Recent errors from dead letter queue

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                      LlamaCrawl CLI                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                 LlamaIndex Core Engine                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Readers    │  │  Embeddings  │  │  Synthesis   │      │
│  │   (5 types)  │  │     (TEI)    │  │   (Ollama)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐  ┌──────▼──────┐  ┌───▼────┐
│ Qdrant │  │    Neo4j    │  │ Redis  │
│ Vector │  │    Graph    │  │ State  │
│  Store │  │    Store    │  │ Cache  │
└────────┘  └─────────────┘  └────────┘
```

### Infrastructure Stack

All services deployed via Docker Compose to `steamy-wsl` server (RTX 4070 GPU):

| Service | Purpose | Port(s) | GPU | Storage |
|---------|---------|---------|-----|---------|
| **Qdrant** | Vector database | 7000 (HTTP), 7001 (gRPC) | No | `qdrant_data` volume |
| **Neo4j** | Graph database | 7474 (HTTP), 7687 (Bolt) | No | `neo4j_data`, `neo4j_logs`, `neo4j_plugins` |
| **Redis** | State/cache/DLQ | 6379 | No | `redis_data` volume |
| **TEI Embeddings** | Generate embeddings (Qwen3-0.6B) | 8080 | Yes | `tei_data` volume |
| **TEI Reranker** | Rerank results (Qwen3-Reranker) | 8081 | Yes | `tei_reranker_data` volume |
| **Ollama** | LLM synthesis | 11434 | Yes | `ollama_data` volume |
| **Firecrawl** | Web scraping service | 3002 (API) | No | `firecrawl_data` volume |

### Data Source Readers

#### 1. Firecrawl Reader
- **Type:** `FireCrawlWebReader` (LlamaIndex built-in, v2 API)
- **Configuration:**
  - API URL: `https://firecrawl.tootie.tv`
  - Default crawl depth: 3
  - Max pages per crawl: 1000
  - Formats: markdown, html
- **Modes:** scrape (single URL), crawl (full site), map (URL discovery), extract (structured data)
- **Sync Strategy:** Manual trigger only (no incremental sync)

#### 2. GitHub Reader
- **Type:** `GitHubRepositoryReader` + custom extensions
- **Data Types:**
  - Repository files (code, docs)
  - Issues and comments
  - Pull requests and reviews
  - Discussions
- **Sync Strategy:** Incremental via `since` timestamp parameter
- **Deduplication:** Git commit SHA + issue/PR updated_at timestamp
- **Graph Relationships:**
  - `(User)-[:AUTHORED]->(Issue)`
  - `(Issue)-[:REFERENCES]->(PullRequest)`
  - `(User)-[:COMMENTED_ON]->(Issue)`

#### 3. Reddit Reader
- **Type:** `RedditReader` (PRAW-based)
- **Data Types:**
  - Subreddit posts
  - Comments and threads
- **Configuration:**
  - Configurable subreddit list
  - Optional time range filters
- **Sync Strategy:** Incremental via post ID and created timestamp
- **Deduplication:** Post/comment ID + edited timestamp
- **Graph Relationships:**
  - `(User)-[:POSTED]->(Post)`
  - `(Comment)-[:REPLIED_TO]->(Post|Comment)`

#### 4. Elasticsearch Reader
- **Type:** `ElasticsearchReader`
- **Configuration:**
  - Configurable index patterns
  - Query filters
  - Field mappings
- **Sync Strategy:** Manual bulk import (incremental sync TBD based on index timestamp fields)
- **Deduplication:** Document `_id` field

#### 5. Gmail Reader
- **Type:** `GmailReader`
- **Data Types:**
  - Email messages (subject, body, attachments metadata)
  - Thread context
- **Authentication:** OAuth 2.0 (Google Cloud Project credentials)
- **Sync Strategy:** Incremental via Gmail `historyId`
- **Deduplication:** Message ID + internal date
- **Graph Relationships:**
  - `(Person)-[:SENT]->(Email)`
  - `(Email)-[:REPLIED_TO]->(Email)`
  - `(Email)-[:MENTIONS]->(Person)`

---

## Data Pipeline

### Ingestion Flow

```
1. Reader Load
   ↓
2. Document Parsing & Chunking
   ↓
3. Hash Calculation (for deduplication)
   ↓
4. Check Redis Cache (skip if unchanged)
   ↓
5. Generate Embeddings (TEI)
   ↓
6. Store Vectors (Qdrant)
   ↓
7. Extract Entities/Relations (KnowledgeGraphIndex)
   ↓
8. Store Graph (Neo4j)
   ↓
9. Update Sync Cursor (Redis)
   ↓
10. Log Success/Failure
```

### Deduplication Strategy

1. **Content Hashing:** SHA-256 hash of normalized document content
2. **Redis Storage:** `hash:<source>:<id>` → hash value
3. **Comparison:** On sync, compare new hash with stored hash
4. **Action:**
   - If identical: Skip processing
   - If different: Update vector store and graph
   - If new: Full processing

### Error Handling

#### Retry Logic
- **Transient Errors:** Exponential backoff (initial: 1s, max: 60s, max retries: 5)
- **Rate Limits:** Respect `Retry-After` headers, exponential backoff if not provided
- **Auth Failures:** Fail immediately, log credential error

#### Dead Letter Queue (DLQ)
- **Storage:** Redis list `dlq:<source>`
- **Contents:** Failed document metadata + error details + timestamp
- **Retention:** 7 days
- **Reprocessing:** Manual via `llamacrawl reprocess-dlq <source>`

#### Error Categories
- **Non-blocking:** Network timeouts, rate limits, transient API errors → Retry + continue
- **Blocking:** Invalid credentials, malformed config → Halt source ingestion, log error
- **Skip:** Unparseable documents, empty content → Log warning, continue

---

## Query Pipeline

### Query Flow

```
1. User Query (text + optional filters)
   ↓
2. Generate Query Embedding (TEI)
   ↓
3. Vector Search (Qdrant) with metadata filters
   ↓
4. Retrieve Top-K Candidates (default: 20)
   ↓
5. Rerank Results (TEI Reranker) → Top-N (default: 5)
   ↓
6. Graph Traversal (Neo4j) for related entities
   ↓
7. Synthesize Answer (Ollama) with context
   ↓
8. Format Response with Source Attribution
```

### Query Capabilities

#### 1. Hybrid Search
- **Vector Similarity:** Semantic search via embeddings
- **Metadata Filters:**
  - Source type (e.g., `--sources gmail,github`)
  - Date ranges (e.g., `--after 2024-01-01`)
  - Custom filters (e.g., `--repo owner/repo`)

#### 2. Graph-Enhanced Retrieval
- Follow relationships in Neo4j to find connected documents
- Example: "Who authored issues related to authentication?" → traverse `(User)-[:AUTHORED]->(Issue)` where issue content matches query

#### 3. Source Attribution
- Each synthesized answer includes:
  - Source document titles/URLs
  - Relevance scores
  - Excerpt snippets
  - Timestamps

### Output Format

```json
{
  "answer": "Synthesized answer text with inline citations [1][2]",
  "sources": [
    {
      "id": "doc_123",
      "source_type": "gmail",
      "title": "Re: Authentication bug",
      "url": "https://mail.google.com/...",
      "score": 0.92,
      "snippet": "...relevant excerpt...",
      "timestamp": "2024-09-15T10:30:00Z"
    }
  ],
  "query_time_ms": 245,
  "retrieved_docs": 20,
  "reranked_docs": 5
}
```

---

## Configuration Management

### Configuration Files

#### 1. `.env` - Secrets and Credentials
```env
# Firecrawl
FIRECRAWL_API_URL=https://firecrawl.tootie.tv
FIRECRAWL_API_KEY=fc-xxx

# GitHub
GITHUB_TOKEN=ghp_xxx

# Reddit
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT=LlamaCrawl/1.0

# Gmail (OAuth 2.0)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxx
GOOGLE_OAUTH_REFRESH_TOKEN=xxx

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_API_KEY=xxx

# Infrastructure
QDRANT_URL=http://localhost:7000
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxx
REDIS_URL=redis://localhost:6379
TEI_EMBEDDING_URL=http://localhost:8080
TEI_RERANKER_URL=http://localhost:8081
OLLAMA_URL=http://localhost:11434

# Observability
LOG_LEVEL=INFO
PROMETHEUS_PORT=9090
```

#### 2. `config.yaml` - Pipeline Configuration
```yaml
sources:
  firecrawl:
    enabled: true
    default_crawl_depth: 3
    max_pages: 1000
    formats: [markdown, html]

  github:
    enabled: true
    repositories:
      - "owner/repo1"
      - "owner/repo2"
    include_issues: true
    include_prs: true
    include_discussions: true

  reddit:
    enabled: true
    subreddits:
      - "python"
      - "programming"
    post_limit: 1000

  elasticsearch:
    enabled: true
    indices: ["docs-*", "logs-*"]

  gmail:
    enabled: true
    labels: ["INBOX", "SENT"]
    include_attachments_metadata: true

ingestion:
  chunk_size: 512
  chunk_overlap: 50
  batch_size: 100
  concurrent_sources: 3

  retry:
    max_attempts: 5
    initial_delay_seconds: 1
    max_delay_seconds: 60

  deduplication:
    enabled: true
    strategy: hash

query:
  top_k: 20
  rerank_top_n: 5
  enable_graph_traversal: true
  synthesis_model: "llama3.1:8b"

graph:
  auto_extract_entities: true
  max_keywords_per_document: 10
  relationship_extraction: true

logging:
  format: json
  level: INFO

metrics:
  enabled: true
  prometheus_port: 9090
```

---

## Development Environment

### Setup

#### Prerequisites
- Python 3.11+
- Docker + Docker Compose
- Docker context configured for `steamy-wsl`
- `uv` package manager

#### Local Development

```bash
# Clone repository
git clone <repo-url>
cd llamacrawl

# Install dependencies
uv sync

# Copy example config
cp .env.example .env
cp config.example.yaml config.yaml

# Edit configs with your credentials
vi .env
vi config.yaml

# Deploy infrastructure to steamy-wsl
docker --context docker-mcp-steamy-wsl compose up -d

# Run CLI locally (connects to remote infrastructure)
uv run llamacrawl --help
```

### Project Structure

```
llamacrawl/
├── .docs/
│   └── plans/
│       └── llamacrawl-rag-pipeline/
│           └── requirements.md
├── src/
│   └── llamacrawl/
│       ├── __init__.py
│       ├── cli.py                 # CLI entry point
│       ├── config.py              # Configuration management
│       ├── readers/               # Data source readers
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── firecrawl.py
│       │   ├── github.py
│       │   ├── reddit.py
│       │   ├── elasticsearch.py
│       │   └── gmail.py
│       ├── ingestion/             # Ingestion pipeline
│       │   ├── __init__.py
│       │   ├── pipeline.py
│       │   ├── chunking.py
│       │   └── deduplication.py
│       ├── storage/               # Storage backends
│       │   ├── __init__.py
│       │   ├── qdrant.py
│       │   ├── neo4j.py
│       │   └── redis.py
│       ├── query/                 # Query engine
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   └── synthesis.py
│       ├── utils/                 # Utilities
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   ├── metrics.py
│       │   └── retry.py
│       └── models/                # Data models
│           ├── __init__.py
│           └── document.py
├── tests/
│   ├── unit/
│   └── integration/
├── docker-compose.yaml
├── pyproject.toml
├── .env.example
├── config.example.yaml
└── README.md
```

### Python Environment
- **Package Manager:** `uv`
- **Python Version:** 3.11+
- **Dependencies:** Defined in `pyproject.toml`
- **Type Checking:** `mypy` with strict mode
- **Linting:** `ruff`
- **Testing:** `pytest`

---

## Deployment

### Docker Compose Services

The complete stack is defined in [docker-compose.yaml](../../docker-compose.yaml) and deployed to `steamy-wsl` via Docker context.

#### Deployment Commands

```bash
# Deploy all services
docker --context docker-mcp-steamy-wsl compose up -d

# View logs
docker --context docker-mcp-steamy-wsl compose logs -f

# Check service health
docker --context docker-mcp-steamy-wsl compose ps

# Update specific service
docker --context docker-mcp-steamy-wsl compose up -d qdrant

# Stop all services
docker --context docker-mcp-steamy-wsl compose down
```

#### Resource Requirements

**GPU Allocation (RTX 4070 on steamy-wsl):**
- TEI Embeddings: Shared GPU access
- TEI Reranker: Shared GPU access
- Ollama: Shared GPU access
- All use `CUDA_VISIBLE_DEVICES=0`

**Memory Estimates:**
- Qdrant: 2-4GB RAM
- Neo4j: 4-8GB RAM (2GB heap + 2GB page cache)
- Redis: 2-4GB RAM
- TEI Embeddings: 4-6GB VRAM
- TEI Reranker: 4-6GB VRAM
- Ollama: 8-16GB VRAM (model dependent)
- Firecrawl: 2-4GB RAM
- **Total:** ~20-40GB RAM, 16-28GB VRAM

**Storage:**
- Qdrant data: Variable (10GB-1TB+ depending on corpus size)
- Neo4j data: Variable (5GB-500GB+)
- Redis data: 1-10GB
- Model caches (TEI, Ollama): 20-50GB
- Firecrawl temp storage: 5-10GB

---

## Observability

### Logging

#### Structured Logging (JSON)
```json
{
  "timestamp": "2024-09-30T14:23:45.123Z",
  "level": "INFO",
  "logger": "llamacrawl.ingestion.pipeline",
  "message": "Ingestion completed",
  "source": "github",
  "documents_processed": 1234,
  "duration_seconds": 45.2,
  "errors": 3
}
```

#### Log Levels
- **DEBUG:** Detailed diagnostic information
- **INFO:** General informational messages (default)
- **WARNING:** Non-critical issues (e.g., skipped documents)
- **ERROR:** Errors requiring attention (e.g., API failures)
- **CRITICAL:** System-level failures (e.g., database unavailable)

### Metrics (Prometheus-style)

#### Ingestion Metrics
```
llamacrawl_documents_ingested_total{source="github"}
llamacrawl_ingestion_duration_seconds{source="github"}
llamacrawl_ingestion_errors_total{source="github", error_type="rate_limit"}
llamacrawl_embeddings_generated_total
llamacrawl_deduplication_hits_total{source="github"}
```

#### Query Metrics
```
llamacrawl_queries_total{status="success"}
llamacrawl_query_duration_seconds{stage="embedding"}
llamacrawl_query_duration_seconds{stage="vector_search"}
llamacrawl_query_duration_seconds{stage="reranking"}
llamacrawl_query_duration_seconds{stage="synthesis"}
llamacrawl_documents_retrieved_total
llamacrawl_documents_reranked_total
```

#### System Metrics
```
llamacrawl_redis_connections_active
llamacrawl_qdrant_vectors_total
llamacrawl_neo4j_nodes_total{label="User"}
llamacrawl_dlq_size{source="gmail"}
```

**Note:** Basic Python logging is implemented initially. Prometheus metrics integration is planned for future phases.

---

## Security & Authentication

### Credential Management
- **Storage:** Environment variables via `.env` file
- **Never committed:** `.env` added to `.gitignore`
- **Example template:** `.env.example` provided in repository
- **Rotation:** Manual credential rotation via `.env` update + service restart

### OAuth 2.0 (Gmail)
1. User creates Google Cloud Project and OAuth 2.0 credentials
2. User runs OAuth flow locally to obtain refresh token
3. Refresh token stored in `.env` file
4. System automatically refreshes access tokens as needed

### API Keys (GitHub, Reddit, Firecrawl, Elasticsearch)
- Stored as environment variables
- Passed to LlamaIndex readers via configuration
- Validated on startup

### Future Multi-User Support
- Design allows for credential storage per user ID
- Redis structure: `credentials:<user_id>:<source>` → encrypted credentials
- Authentication module is single-user for now but extensible

---

## Constraints & Assumptions

### Constraints
1. **Single User:** Initial implementation supports single user account per data source
2. **No Scheduling:** Manual ingestion triggers only (no cron/batch jobs)
3. **No MCP Interface:** CLI only for initial phase
4. **Breaking Changes OK:** Backwards compatibility not required
5. **GPU Required:** RTX 4070 on steamy-wsl required for embeddings/reranking/synthesis

### Assumptions
1. User has valid credentials for all configured data sources
2. Docker context `docker-mcp-steamy-wsl` is properly configured
3. Remote server (steamy-wsl) has sufficient resources (see Resource Requirements)
4. Network connectivity between local dev machine and steamy-wsl
5. Firecrawl self-hosted instance (https://firecrawl.tootie.tv) is operational

### Non-Functional Requirements
- **Performance:** Query response time < 5 seconds for typical queries
- **Reliability:** 99% uptime for infrastructure services
- **Scalability:** Support for 100K+ documents initially, 1M+ eventually
- **Maintainability:** Modular architecture with clear separation of concerns

---

## Success Criteria

### Phase 1: Infrastructure (Week 1)
- ✅ Docker Compose stack deployed to steamy-wsl
- ✅ All services healthy and accessible
- ✅ Configuration files and environment setup complete

### Phase 2: Single Source E2E (Week 2)
- ✅ One data source (Firecrawl) fully implemented
- ✅ Documents ingested into Qdrant
- ✅ Entities/relationships extracted to Neo4j
- ✅ Basic query functionality working
- ✅ CLI commands functional

### Phase 3: Multi-Source Ingestion (Week 3-4)
- ✅ All 5 data sources implemented and tested
- ✅ Incremental sync working for supported sources
- ✅ Deduplication logic validated
- ✅ Error handling and retry logic tested

### Phase 4: Query Enhancement (Week 5)
- ✅ Reranking integrated
- ✅ Graph traversal working
- ✅ Source attribution in responses
- ✅ Metadata filtering operational

### Phase 5: Observability & Polish (Week 6)
- ✅ Structured logging implemented
- ✅ Error handling comprehensive
- ✅ Documentation complete
- ✅ Basic integration tests passing

---

## Future Enhancements (Post-MVP)

### Short Term
1. **MCP Server Interface:** Expose tools and resources for Claude Code integration
2. **Additional Data Sources:** Google Drive, Docs, Calendar, Keep, YouTube, etc.
3. **Scheduled Ingestion:** Background jobs for automatic syncing
4. **Advanced Metrics:** Full Prometheus integration with Grafana dashboards

### Medium Term
1. **Web UI:** Dashboard for managing sources, viewing stats, running queries
2. **Chat Interface:** Conversational query interface
3. **Multi-User Support:** User authentication and per-user credential management
4. **Advanced Graph Queries:** Complex relationship traversal and graph analytics

### Long Term
1. **Real-Time Sync:** Webhook-based continuous synchronization
2. **ML-Enhanced Retrieval:** Custom embeddings fine-tuned on user data
3. **Federated Search:** Query across multiple LlamaCrawl instances
4. **Enterprise Features:** SSO, RBAC, audit logging, compliance

---

## Open Questions

1. **Neo4j APOC Plugins:** Should we install APOC for advanced graph algorithms?
2. **Ollama Model Selection:** Which specific model(s) for synthesis? (llama3.1:8b suggested)
3. **Firecrawl Deployment:** Use official Firecrawl Docker image or build from source?
4. **Document Chunking Strategy:** Fixed-size vs. semantic chunking?
5. **Rate Limit Handling:** Should we implement token bucket algorithm per source?

---

## Appendix

### References
- [LlamaIndex Documentation](https://developers.llamaindex.ai/)
- [LlamaIndex MCP Guide](https://developers.llamaindex.ai/python/framework/module_guides/mcp/)
- [Firecrawl Documentation](https://docs.firecrawl.dev/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)

### Related Documents
- [INIT.md](../../../INIT.md) - Original project specification
- [docker-compose.yaml](../../../docker-compose.yaml) - Infrastructure definition

### Change Log
- **2025-09-30:** Initial requirements document created