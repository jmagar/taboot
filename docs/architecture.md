# Architecture Guide

This document describes the LlamaCrawl system architecture, component interactions, and data flows.

## System Overview

LlamaCrawl is a multi-source RAG pipeline built on three foundational layers:

1. **Data Ingestion Layer**: Readers extract data from sources, documents are chunked, embedded, and stored
2. **Storage Layer**: Qdrant (vectors), Neo4j (knowledge graph), Redis (state/cache)
3. **Retrieval Layer**: Hybrid search combining vector similarity, graph traversal, and reranking

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LlamaCrawl CLI (Typer)                       │
│  Commands: init | ingest | query | status                           │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────────┐
│                      Configuration Layer                             │
│  ┌─────────────────┐              ┌─────────────────┐               │
│  │  .env (secrets) │              │ config.yaml     │               │
│  │  - API keys     │              │ - Sources       │               │
│  │  - Credentials  │              │ - Pipeline      │               │
│  │  - URLs         │              │ - Query params  │               │
│  └─────────────────┘              └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────────────┐
│                     Data Ingestion Layer                             │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  Data Source Readers                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │   │
│  │  │Firecrawl │  │  GitHub  │  │  Reddit  │  │  Gmail   │ ... │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         │                                            │
│  ┌──────────────────────▼───────────────────────────────────────┐   │
│  │              LlamaIndex IngestionPipeline                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │Deduplication│  │  Chunking   │  │  Embedding  │          │   │
│  │  │(SHA-256)    │  │(Sentence)   │  │(TEI Qwen3)  │          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └────────────────────────────────────────────────────────────┬─┘   │
└─────────────────────────────────────────────────────────────┬─┼─────┘
                                                               │ │
┌──────────────────────────────────────────────────────────────▼─▼─────┐
│                         Storage Layer                                 │
│                                                                        │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐        │
│  │    Qdrant      │  │      Neo4j      │  │     Redis      │        │
│  │ Vector Storage │  │  Knowledge Graph│  │  State/Cache   │        │
│  │                │  │                 │  │                │        │
│  │ • 1024-dim     │  │ • Entities      │  │ • Cursors      │        │
│  │ • Cosine       │  │ • Relationships │  │ • Hashes       │        │
│  │ • Metadata     │  │ • Graph queries │  │ • DLQ          │        │
│  └────────────────┘  └─────────────────┘  │ • Locks        │        │
│         │                     │            └────────────────┘        │
└─────────┼─────────────────────┼───────────────────────────────────┬─┘
          │                     │                                   │
┌─────────▼─────────────────────▼───────────────────────────────────▼─┐
│                         Retrieval Layer                              │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Query Engine                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │  Query   │  │  Vector  │  │  Graph   │  │ Reranker │      │  │
│  │  │Embedding │→ │  Search  │→ │Traversal │→ │  (TEI)   │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
│                                   │                                  │
│  ┌────────────────────────────────▼──────────────────────────────┐  │
│  │                    Answer Synthesizer                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │  │
│  │  │  Ollama  │→ │ Response │→ │  Source  │                     │  │
│  │  │   LLM    │  │Formation │  │Attribution│                     │  │
│  │  └──────────┘  └──────────┘  └──────────┘                     │  │
│  └─────────────────────────────────────────────────────────────┬─┘  │
└────────────────────────────────────────────────────────────────┼────┘
                                                                  │
                          ┌───────────────────────────────────────▼────┐
                          │            User Output                     │
                          │  • Answer with citations                   │
                          │  • Source attribution                      │
                          │  • Metadata (scores, timestamps)           │
                          └────────────────────────────────────────────┘
```

## Component Descriptions

### CLI Layer

**Technology:** Typer

**Responsibilities:**
- Command-line interface for all operations
- Configuration validation
- User interaction and output formatting

**Commands:**
- `init`: Initialize storage backends
- `ingest <source>`: Trigger data ingestion
- `query <text>`: Query the RAG system
- `status`: Display system health and statistics

### Configuration Layer

**Files:**
- `.env`: Secrets and credentials (API keys, passwords, URLs)
- `config.yaml`: Pipeline configuration (sources, chunking, query parameters)

**Module:** `src/llamacrawl/config.py`

**Responsibilities:**
- Load and validate configuration
- Environment variable management
- Merge configurations (env vars override YAML)
- Fail-fast validation

### Data Source Readers

**Module:** `src/llamacrawl/readers/`

**Base Class:** `BaseReader` (abstract)

**Implementations:**
- `FirecrawlReader`: Web scraping via Firecrawl API
- `GitHubReader`: GitHub repositories, issues, PRs, discussions
- `RedditReader`: Reddit posts and comments via PRAW
- `GmailReader`: Email messages via OAuth 2.0
- `ElasticsearchReader`: Bulk import from Elasticsearch indices

**Responsibilities:**
- Load data from external sources
- Handle authentication and API calls
- Incremental sync (where supported)
- Error handling and retry logic
- Convert source data to unified Document model

**Key Features:**
- Cursor-based incremental sync (Redis storage)
- Content-based deduplication (SHA-256 hashing)
- Rate limiting and retry with exponential backoff
- Dead Letter Queue for failed documents

### Ingestion Pipeline

**Module:** `src/llamacrawl/ingestion/pipeline.py`

**Framework:** LlamaIndex IngestionPipeline

**Components:**

1. **Deduplication** (`deduplication.py`)
   - Compute SHA-256 hash of normalized content
   - Compare with stored hashes in Redis
   - Skip unchanged documents

2. **Chunking** (`chunking.py`)
   - Split documents into chunks (default: 512 tokens)
   - Sentence-aware splitting (LlamaIndex SentenceSplitter)
   - Overlap between chunks (default: 50 tokens)
   - Preserve metadata across chunks

3. **Embedding** (custom TEI integration)
   - Batch embedding requests to TEI service
   - Qwen3-Embedding-0.6B model (1024-dim vectors)
   - GPU-accelerated inference
   - Automatic retry on transient failures

4. **Vector Storage** (`storage/qdrant.py`)
   - Store embeddings in Qdrant
   - Indexed metadata: doc_id, source_type, timestamp, content_hash
   - Batch upserts (100-1000 points per batch)
   - Cosine similarity distance metric

5. **Entity Extraction** (LlamaIndex PropertyGraphIndex)
   - Extract entities (Person, Organization, Location, Concept)
   - Extract relationships (AUTHORED, MENTIONS, REPLIED_TO, etc.)
   - Store in Neo4j graph database

6. **State Management** (`storage/redis.py`)
   - Update sync cursors
   - Mark documents as processed
   - Distributed locks for concurrent ingestion

**Data Flow:**

```
Source Data
    │
    ▼
Load via Reader
    │
    ▼
Compute Content Hash ───────┐
    │                       │
    ▼                       ▼
Check Redis Cache      Store Hash
    │
    ├─(unchanged)──> Skip
    │
    ├─(changed/new)──> Continue
    │
    ▼
Chunk Document
    │
    ▼
Generate Embeddings
    │
    ├──────────────────────┐
    │                      │
    ▼                      ▼
Store in Qdrant     Extract Entities
                           │
                           ▼
                    Store in Neo4j
```

### Storage Layer

#### Qdrant (Vector Database)

**Module:** `src/llamacrawl/storage/qdrant.py`

**Collection:** `llamacrawl_documents`

**Schema:**
```json
{
  "vector": [1024 dimensions],
  "payload": {
    "doc_id": "string (indexed)",
    "source_type": "string (indexed)",
    "source_url": "string",
    "title": "string",
    "content": "string",
    "timestamp": "datetime (indexed)",
    "content_hash": "string (indexed)",
    "metadata": {
      "source-specific fields"
    }
  }
}
```

**Features:**
- Cosine similarity search
- Metadata filtering (pre-query)
- Scalar quantization (4x memory reduction)
- HNSW index (m=16, ef_construct=100)

#### Neo4j (Knowledge Graph)

**Module:** `src/llamacrawl/storage/neo4j.py`

**Node Labels:**
- `Document`: All ingested documents
- `User`: Authors/contributors
- `Entity`: Extracted entities (people, orgs, concepts)
- `Repository`, `Issue`, `PullRequest` (GitHub)
- `Email`, `Person` (Gmail)
- `Post`, `Comment` (Reddit)

**Relationship Types:**
- `AUTHORED`: User → Document
- `MENTIONS`: Document → Entity/Person
- `REPLIED_TO`: Document → Document
- `REFERENCES`: Issue → PullRequest
- `RELATED_TO`: Document → Document (semantic)

**Schema Initialization:**
```cypher
-- Constraints (uniqueness)
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
CREATE CONSTRAINT user_name IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE;

-- Indexes (performance)
CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source_type);
CREATE INDEX doc_timestamp IF NOT EXISTS FOR (d:Document) ON (d.timestamp);
```

**Use Cases:**
- Find related documents via relationships
- Author attribution queries
- Cross-reference discovery (e.g., GitHub issue mentioned in email)
- Graph-based similarity (traverse RELATED_TO edges)

#### Redis (State Management)

**Module:** `src/llamacrawl/storage/redis.py`

**Key Schema:**

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `hash:<source>:<doc_id>` | String | Content hash for deduplication | None |
| `cursor:<source>` | String | Last sync cursor/timestamp | None |
| `dlq:<source>` | List | Dead letter queue (failed docs) | 7 days |
| `lock:ingest:<source>` | String | Distributed lock | 5 min |

**Features:**
- Persistent storage (appendonly + snapshots)
- Connection pooling
- Atomic operations (SETNX for locks)
- Batch operations via pipelines

### Retrieval Layer

#### Query Engine

**Module:** `src/llamacrawl/query/engine.py`

**Query Flow:**

```
User Query
    │
    ▼
Generate Query Embedding (TEI)
    │
    ▼
Vector Search (Qdrant)
  • Apply metadata filters
  • Retrieve top_k candidates (default: 20)
    │
    ▼
Rerank Results (TEI Reranker)
  • Score candidates against query
  • Select top_n (default: 5)
    │
    ▼
Graph Traversal (Neo4j)
  • Find related documents
  • Add author/entity context
    │
    ▼
Combine Results
    │
    ▼
Return Ranked Documents
```

**Features:**
- Hybrid search (vector + metadata filters)
- Graph-enhanced retrieval
- Reranking for quality improvement
- Metadata filtering (source_type, date ranges)

#### Answer Synthesizer

**Module:** `src/llamacrawl/query/synthesis.py`

**LLM:** Ollama (llama3.1:8b)

**Process:**

```
Query + Retrieved Documents
    │
    ▼
Format Context
  • Numbered sources [1], [2], ...
  • Include snippets and metadata
    │
    ▼
Build Prompt
  System: "Answer based on context. Cite sources."
  Context: [formatted documents]
  Query: [user question]
    │
    ▼
Call Ollama API
  • Temperature: 0.7
  • Max tokens: 4096
    │
    ▼
Parse Response
    │
    ▼
Add Source Attribution
  • Extract citations [1], [2]
  • Build source list with metadata
    │
    ▼
Return QueryResult
  • answer: synthesized text
  • sources: list of SourceAttribution
  • metadata: query time, doc counts
```

### Custom Embeddings

**Module:** `src/llamacrawl/embeddings/tei.py`

**Class:** `TEIEmbedding` (extends LlamaIndex BaseEmbedding)

**Model:** Qwen3-Embedding-0.6B (1024 dimensions)

**API:**
```python
POST http://localhost:8080/embed
Content-Type: application/json

{
  "inputs": ["text1", "text2", ...]
}
```

**Features:**
- Batch embedding (32-128 texts per request)
- GPU-accelerated inference
- Last-token pooling
- Automatic retry on failures

### Reranker

**Module:** `src/llamacrawl/embeddings/reranker.py`

**Class:** `TEIRerank` (extends LlamaIndex BaseNodePostprocessor)

**Model:** Qwen3-Reranker-0.6B-seq-cls

**API:**
```python
POST http://localhost:8081/rerank
Content-Type: application/json

{
  "query": "question text",
  "texts": ["doc1", "doc2", ...],
  "return_text": false
}
```

**Purpose:**
- Improve retrieval quality (vector search can miss nuances)
- Score candidates against query
- Select most relevant documents for synthesis

## Data Models

**Module:** `src/llamacrawl/models/document.py`

### DocumentMetadata

```python
class DocumentMetadata(BaseModel):
    source_type: Literal["firecrawl", "github", "reddit", "gmail", "elasticsearch"]
    source_url: str
    timestamp: datetime
    extra: dict[str, Any]  # Source-specific fields
```

### Document

```python
class Document(BaseModel):
    doc_id: str
    title: str
    content: str
    content_hash: str  # SHA-256
    metadata: DocumentMetadata
    embedding: list[float] | None = None
```

### QueryResult

```python
class QueryResult(BaseModel):
    answer: str
    sources: list[SourceAttribution]
    query_time_ms: int
    retrieved_docs: int
    reranked_docs: int
```

### SourceAttribution

```python
class SourceAttribution(BaseModel):
    doc_id: str
    source_type: str
    title: str
    url: str
    score: float
    snippet: str
    timestamp: datetime
```

## Infrastructure Services

### Docker Compose Stack

**File:** `docker-compose.yaml`

**Services:**

| Service | Image | Ports | GPU | Purpose |
|---------|-------|-------|-----|---------|
| Qdrant | qdrant/qdrant:v1.15.1 | 7000, 7001 | No | Vector database |
| Neo4j | neo4j:5.15-community | 7474, 7687 | No | Graph database |
| Redis | redis:7.2-alpine | 6379 | No | Cache/state store |
| TEI Embeddings | huggingface/tei:1.8.2 | 8080 | Yes | Embedding generation |
| TEI Reranker | huggingface/tei:1.8.2 | 8081 | Yes | Result reranking |
| Ollama | ollama/ollama:latest | 11434 | Yes | LLM synthesis |

**Deployment:**
```bash
docker --context docker-mcp-steamy-wsl compose up -d
```

**Resource Requirements:**
- RAM: 20-40GB
- VRAM: 16-28GB (shared across GPU services)
- Storage: 100GB+ for databases and model caches

## Data Flow Diagrams

### Ingestion Flow

```
┌────────────┐
│Data Source │ (Firecrawl, GitHub, Reddit, Gmail, Elasticsearch)
└──────┬─────┘
       │ Load via Reader
       ▼
┌──────────────┐
│Document List │
└──────┬───────┘
       │
       ▼
┌────────────────────┐
│ Deduplication      │ Redis: hash:<source>:<doc_id>
│ (SHA-256 Hash)     │
└──────┬─────────────┘
       │
       ├─(unchanged)──> Skip
       │
       ├─(changed/new)
       ▼
┌────────────────────┐
│ Chunking           │ SentenceSplitter (512 tokens, 50 overlap)
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│ Embedding          │ TEI: POST /embed (batch)
└──────┬─────────────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌────────────┐   ┌──────────────────┐
│  Qdrant    │   │ Entity Extraction│ PropertyGraphIndex
│ (Vectors)  │   │ (LlamaIndex)     │
└────────────┘   └────────┬─────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │     Neo4j       │
                 │ (Knowledge Graph)│
                 └─────────────────┘
```

### Query Flow

```
┌──────────────┐
│ User Query   │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Query Embedding      │ TEI: POST /embed
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Vector Search        │ Qdrant: search with filters
│ (top_k=20)           │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Reranking            │ TEI: POST /rerank
│ (top_n=5)            │
└──────┬───────────────┘
       │
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐   ┌──────────────────┐
│Retrieved Docs│   │ Graph Traversal  │ Neo4j: MATCH queries
└──────┬───────┘   └────────┬─────────┘
       │                    │
       └──────┬─────────────┘
              │
              ▼
┌──────────────────────────┐
│ Context Formatting       │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ LLM Synthesis            │ Ollama: llama3.1:8b
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Source Attribution       │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ QueryResult              │
│ • answer                 │
│ • sources                │
│ • metadata               │
└──────────────────────────┘
```

## Security Considerations

### Credential Management

- **Storage:** Environment variables in `.env` file (gitignored)
- **Access:** Only application process reads credentials
- **Rotation:** Update `.env` and restart services

### Network Security

- **Internal Network:** All services on `crawler-network` bridge
- **External Access:** Only exposed ports accessible
- **Firewall:** Configure iptables/firewall rules on host

### Data Privacy

- **No Logs of Content:** Only metadata logged (doc_id, source, counts)
- **No Credential Logging:** API keys/tokens never logged
- **Redis Persistence:** Content hashes only (not full content)

## Performance Optimization

### Ingestion Performance

1. **Batch Operations:**
   - Qdrant: 100-1000 points per upsert
   - TEI: 32-128 texts per embed request
   - Neo4j: UNWIND for batch Cypher writes

2. **Concurrent Processing:**
   - Multiple sources can ingest simultaneously
   - Set `concurrent_sources` in config.yaml

3. **Deduplication:**
   - Skip unchanged documents (no re-embedding)
   - Redis hash lookups are fast (O(1))

4. **Caching:**
   - RedisDocumentStore caches processed documents
   - Embeddings cached in Qdrant

### Query Performance

1. **Metadata Filtering:**
   - Apply filters at Qdrant query time (not post-filtering)
   - Ensure fields are indexed

2. **Reranking:**
   - Balance quality vs. speed (top_n parameter)
   - Smaller top_n = faster synthesis

3. **Graph Traversal:**
   - Limit depth (max 2 hops)
   - Use indexed properties (doc_id, source_type)

4. **Synthesis:**
   - Smaller models faster (llama3.1:3b vs 8b)
   - Reduce max_context_tokens if needed

## Monitoring and Observability

### Structured Logging

**Format:** JSON

**Fields:**
- `timestamp`: ISO 8601 with timezone
- `level`: DEBUG|INFO|WARNING|ERROR|CRITICAL
- `logger`: Module name
- `message`: Log message
- `source`: Data source name (if applicable)
- `doc_id`: Document ID (if applicable)
- `duration_seconds`: Operation duration (if applicable)

**Example:**
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

### Metrics (Future)

**Prometheus-style metrics planned:**

- `llamacrawl_documents_ingested_total{source}`
- `llamacrawl_ingestion_duration_seconds{source}`
- `llamacrawl_ingestion_errors_total{source, error_type}`
- `llamacrawl_queries_total{status}`
- `llamacrawl_query_duration_seconds{stage}`

## Extensibility

### Adding New Data Sources

1. Create reader class extending `BaseReader`
2. Implement `load_data()` method
3. Implement `supports_incremental_sync()`
4. Add source configuration to `config.example.yaml`
5. Add credentials to `.env.example`
6. Update documentation

### Adding New Storage Backends

1. Create client wrapper in `src/llamacrawl/storage/`
2. Implement required interface methods
3. Update `IngestionPipeline` to use new backend
4. Add service to `docker-compose.yaml`
5. Update initialization in `init` command

### Custom Transformations

Add custom transformations to ingestion pipeline:

```python
from llama_index.core import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter

# Custom transformation
class CustomTransform:
    def __call__(self, documents):
        # Your custom logic
        return transformed_documents

pipeline = IngestionPipeline(
    transformations=[
        CustomTransform(),
        SentenceSplitter(chunk_size=512),
        embedding_model,
    ]
)
```

## Future Enhancements

### Short Term

- Full Prometheus metrics integration
- MCP (Model Context Protocol) server interface
- Web UI for querying and monitoring
- Additional data sources (Google Drive, Slack, etc.)

### Medium Term

- Multi-user support with per-user credentials
- Scheduled background ingestion (cron-like)
- Advanced graph queries and analytics
- Custom embedding models (fine-tuned on user data)

### Long Term

- Real-time sync via webhooks
- Federated search across multiple instances
- Advanced deduplication (fuzzy matching)
- Enterprise features (SSO, RBAC, audit logs)

## References

- [LlamaIndex Documentation](https://developers.llamaindex.ai/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Text Embeddings Inference](https://github.com/huggingface/text-embeddings-inference)
- [Ollama Documentation](https://ollama.ai/docs)
