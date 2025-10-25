# PostgreSQL/Database Infrastructure Analysis

**Date**: 2025-10-22
**Updated**: 2025-10-24 (Schema duplication cleanup)
**Repository**: taboot (Doc-to-Graph RAG Platform)

## Executive Summary

Taboot has **well-designed PostgreSQL infrastructure** with SQL schema as the source of truth. The Alembic migration system has been removed to formalize the current reality: manual schema management via `specs/001-taboot-rag-platform/contracts/postgresql-schema.sql`.

**Key Changes (2025-10-24):**
- ✅ Removed Alembic directory and dependency
- ✅ Deleted conflicting `ingestion_jobs` table definition from Alembic migration
- ✅ SQL schema file is now the single source of truth
- ✅ Added version tracking to SQL file
- ✅ Updated documentation to reflect manual migration approach

---

## PostgreSQL Infrastructure Status

### 1. Service Configuration ✓ Complete

**docker-compose.yaml** (lines 225-245):
```yaml
taboot-db:
  build:
    context: ./docker/postgres
    dockerfile: Dockerfile
    args:
      POSTGRES_DB: ${POSTGRES_DB:-taboot}
  image: taboot/postgres:16
  container_name: taboot-db
  env_file:
    - .env
  volumes:
    - taboot-db:/var/lib/postgresql/data
  ports:
    - "${POSTGRES_PORT:-5432}:5432"
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-taboot}"]
```

**Status**: ✓ Service is defined with health checks, volume persistence, and Docker image build

### 2. Docker Image Configuration ✓ Complete

**docker/postgres/Dockerfile**:
- PostgreSQL 16 with pg_cron extension enabled
- Builds with custom initialization SQL via `nuq.sql`
- Pre-loads pg_cron for scheduled maintenance

### 3. PostgreSQL Schema ✓ Complete

**specs/001-taboot-rag-platform/contracts/postgresql-schema.sql** (167 lines):

#### Tables Defined:

1. **documents** (8 columns)
   - Primary key: `doc_id` (UUID)
   - Unique constraint: `content_hash` (SHA-256)
   - Composite index: `(source_type, ingested_at)`
   - Index: `extraction_state`
   - Enum constraints on `source_type` and `extraction_state`
   - JSONB metadata field
   - Auto-updating `updated_at` trigger

2. **extraction_windows** (8 columns)
   - Primary key: `window_id` (UUID)
   - Foreign key: `doc_id` (CASCADE delete)
   - Tier enum: A, B, C
   - Indexes: `doc_id`, `(doc_id, tier)`, `processed_at`
   - Optional LLM metrics (latency_ms, cache_hit)

3. **ingestion_jobs** (9 columns)
   - Primary key: `job_id` (UUID)
   - State machine: pending → running → completed/failed
   - Indexes: `(source_type, state, created_at)`, `state`
   - Timestamp validation constraints
   - JSONB errors field

4. **extraction_jobs** (10 columns)
   - Primary key: `job_id` (UUID)
   - Foreign key: `doc_id` (CASCADE delete)
   - State machine: pending → tier_a_done → tier_b_done → tier_c_done → completed/failed
   - Tier-specific counters: `tier_a_triples`, `tier_b_windows`, `tier_c_triples`
   - Retry tracking (max 3)
   - Indexes: `doc_id`, `(state, started_at)`, `state`

**Total Indexes**: 12+ (primary keys + composite + state/date queries)

#### Schema Features:
- UUID v4 support via `uuid-ossp` extension
- Timezone-aware timestamps (WITH TIME ZONE)
- Comprehensive CHECK constraints
- Foreign key references with CASCADE deletion
- Auto-updating triggers for `updated_at`
- Detailed documentation comments

---

### 4. Configuration Management ✓ Complete

**packages/common/config/__init__.py** (lines 43-181):

```python
class TabootConfig(BaseSettings):
    # PostgreSQL credentials
    postgres_user: str = "taboot"
    postgres_password: str = "changeme"
    postgres_db: str = "taboot"
    postgres_port: int = 5432
    
    @property
    def postgres_connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@taboot-db:{self.postgres_port}/{self.postgres_db}"
```

**Status**: ✓ Configuration fully implemented with sensible defaults

### 5. Schema Initialization ✓ Complete

**packages/common/db_schema.py** (231 lines):

Three public functions:
1. `load_schema_file(path: Path) -> str` - Loads SQL from file
2. `create_schema(config: TabootConfig) -> None` - Executes schema creation with transaction handling
3. `verify_schema(config: TabootConfig) -> list[str]` - Queries information_schema for table names
4. `create_postgresql_schema() -> None` (async wrapper) - For HTTP endpoints

**Status**: ✓ Schema initialization fully implemented

---

## Critical Gap: Missing Document Client Implementation

### Problem Definition

Two locations attempt to import `get_postgres_client()`:

**apps/api/routes/documents.py** (line 77):
```python
from packages.common.db_schema import get_postgres_client

postgres_url = os.getenv("POSTGRES_URL", "postgresql://taboot:changeme@localhost:5432/taboot")
db_client = get_postgres_client(postgres_url)

async with db_client as client:
    use_case = ListDocumentsUseCase(db_client=client)
```

**apps/cli/commands/list_documents.py** (line 80):
```python
from packages.common.db_schema import get_postgres_client

postgres_url = os.getenv("POSTGRES_URL", "postgresql://taboot:changeme@localhost:5432/taboot")
db_client = get_postgres_client(postgres_url)

async with db_client as client:
    use_case = ListDocumentsUseCase(db_client=client)
```

### What's Expected

The code expects `get_postgres_client()` to return an **async context manager** that implements the `DocumentsClient` protocol:

```python
class DocumentsClient(Protocol):
    async def fetch_documents(
        self,
        limit: int,
        offset: int,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> list[Document]:
        ...

    async def count_documents(
        self,
        source_type: SourceType | None = None,
        extraction_state: ExtractionState | None = None,
    ) -> int:
        ...
```

### What's Provided

**packages/common/db_schema.py** exports (line 230):
```python
__all__ = ["load_schema_file", "create_schema", "verify_schema", "create_postgresql_schema"]
```

**Missing**: `get_postgres_client` is not defined or exported

### Runtime Impact

**Scenario 1**: When endpoint called:
```bash
curl http://localhost:8000/documents
# ImportError: cannot import name 'get_postgres_client' from 'packages.common.db_schema'
```

**Scenario 2**: When CLI command run:
```bash
uv run apps/cli list documents
# ImportError: cannot import name 'get_postgres_client' from 'packages.common.db_schema'
```

---

## Data Flow: Missing Pieces

### Current Ingestion Flow (Working ✓)

```
ingest_web_command (CLI)
  ↓ calls ↓
IngestWebUseCase.execute()
  ↓ creates Chunks with ↓
  - chunk_id (UUID)
  - doc_id (UUID)
  - content
  - source_type
  - source_url
  - ingested_at
  ↓ embeds via ↓
Embedder (TEI)
  ↓ writes to ↓
QdrantWriter.upsert_batch()
  ↓ stores in ↓
Qdrant vectors
```

**Status**: ✓ Fully implemented

### Missing: Document Record Creation (Broken ✗)

There is **no code path** that creates `documents` table records during ingestion:

1. **IngestWebUseCase** (lines 70-152):
   - ✓ Creates IngestionJob records (in memory, never persisted)
   - ✗ Never creates Document records
   - ✓ Creates Chunk records (only as vectors in Qdrant)

2. **QdrantWriter** (vector storage only):
   - ✓ Upserts chunks as vectors with payloads
   - ✗ Does not interact with PostgreSQL

3. **No DocumentStore adapter**:
   - No implementation of writing Document records to PostgreSQL
   - No adapter for `packages/common/db_schema`

### Result

After running `uv run apps/cli ingest web https://example.com`:
- ✓ Chunks are in Qdrant
- ✗ Documents table is empty
- ✓ IngestionJob is created in memory
- ✗ IngestionJob is never persisted
- ✗ ExtractionJob is never created

When querying via `GET /documents` or `taboot list documents`:
- ✗ Code crashes trying to import `get_postgres_client()`

---

## Where Documents Should Be Created

### During Ingestion Pipeline

The **correct place** to create document records is in `IngestWebUseCase._process_document()`:

**Current implementation** (packages/core/use_cases/ingest_web.py, lines 231-284):
```python
def _process_document(
    self, doc: LlamaDocument, job: IngestionJob, source_url: str
) -> list[Chunk]:
    # ... normalization and chunking ...
    
    chunks: list[Chunk] = []
    doc_id = uuid4()  # One doc_id per document
    
    for chunk_doc in chunk_docs:
        chunk = Chunk(
            chunk_id=uuid4(),
            doc_id=doc_id,  # ✓ doc_id assigned
            content=chunk_doc.text,
            # ... other fields ...
        )
        chunks.append(chunk)
    
    return chunks  # ✓ Returns chunks for embedding
```

**What's missing**:
- No code to create a `Document` record with this `doc_id`
- No persistence of document metadata to PostgreSQL
- No linking of IngestionJob to created Documents

### Proper Architecture

Following the CLAUDE.md pattern (apps → adapters → core):

1. **Adapter Layer** (new):
   ```python
   # packages/common/db_schema.py (or new packages/ingest/document_store.py)
   class PostgresDocumentStore:
       async def create_document(
           self,
           doc_id: UUID,
           source_url: str,
           source_type: SourceType,
           content_hash: str,
           metadata: dict | None = None,
       ) -> Document:
           """Create a document record in PostgreSQL"""
           # INSERT INTO documents(...)
   
   async def get_postgres_client(url: str) -> AsyncContextManager[DocumentsClient]:
       """Factory function returning async context manager"""
   ```

2. **Use Case Layer** (modification):
   ```python
   class IngestWebUseCase:
       def __init__(
           self,
           # ... existing ...
           document_store: DocumentStore,  # NEW
       ):
   
       def _process_document(...):
           # ... create chunks ...
           
           # NEW: Create document record
           doc = await self.document_store.create_document(
               doc_id=doc_id,
               source_url=source_url,
               source_type=SourceType.WEB,
               content_hash=hash_content(combined_chunks),
               metadata={...}
           )
   ```

3. **Command Layer** (wire up):
   ```python
   @app.command(name="web")
   def ingest_web_command(...):
       config = get_config()
       document_store = PostgresDocumentStore(config.postgres_connection_string)
       use_case = IngestWebUseCase(..., document_store=document_store)
   ```

---

## File Manifest

### Schema & Configuration
- `/home/jmagar/code/taboot/specs/001-taboot-rag-platform/contracts/postgresql-schema.sql` (167 lines)
  - Complete schema with 4 tables, 12+ indexes, constraints, triggers
  
- `/home/jmagar/code/taboot/packages/common/config/__init__.py` (182 lines)
  - PostgreSQL config with connection string property
  
- `/home/jmagar/code/taboot/packages/common/db_schema.py` (231 lines)
  - Schema loading, creation, verification (async-wrapped)
  
- `/home/jmagar/code/taboot/docker/postgres/Dockerfile` (23 lines)
  - PostgreSQL 16 with pg_cron
  
- `/home/jmagar/code/taboot/docker/postgres/nuq.sql` (56 lines)
  - Firecrawl queue schema (nuq.queue_scrape)

### Broken Endpoints
- `/home/jmagar/code/taboot/apps/api/routes/documents.py` (110 lines)
  - Imports `get_postgres_client` (not defined)
  - Implements `GET /documents` with filtering
  
- `/home/jmagar/code/taboot/apps/cli/commands/list_documents.py` (142 lines)
  - Imports `get_postgres_client` (not defined)
  - Implements `taboot list documents` CLI command

### Use Cases & Models
- `/home/jmagar/code/taboot/packages/core/use_cases/list_documents.py` (167 lines)
  - Defines `DocumentsClient` protocol
  - Defines `ListDocumentsUseCase` and `DocumentListResponse`
  
- `/home/jmagar/code/taboot/packages/core/use_cases/ingest_web.py` (289 lines)
  - Ingestion pipeline (missing document record creation)
  
- `/home/jmagar/code/taboot/packages/schemas/models/__init__.py`
  - Document, Chunk, IngestionJob models (see SCHEMA section)

### Documentation
- `/home/jmagar/code/taboot/specs/001-taboot-rag-platform/data-model.md` (582 lines)
  - Complete data model specification for Document and all related tables

---

## Questions & Answers

### Q1: Is there a PostgreSQL schema for Document records?

**Yes ✓** - Comprehensive schema defined in `postgresql-schema.sql`:
- `documents` table with 8 columns
- 3 additional tables: `extraction_windows`, `ingestion_jobs`, `extraction_jobs`
- 12+ indexes, constraints, triggers
- Fully documented with comments

### Q2: Where is the real DocumentStore implementation?

**Missing ✗** - No implementation exists:
- `get_postgres_client()` function is imported but never defined
- No adapter package for PostgreSQL document operations
- No async context manager returning `DocumentsClient`

### Q3: How should Document records be created during ingestion?

**Not currently done ✗** - Gap in pipeline:
- `IngestWebUseCase` creates chunks but never Document records
- Should call a DocumentStore adapter after normalizing each document
- Document record should include:
  - `doc_id` (UUID, already generated)
  - `source_url` (from URL parameter)
  - `source_type` (WEB)
  - `content_hash` (SHA-256 of normalized content)
  - `extraction_state` (initially PENDING)
  - `metadata` (optional: page count, author, etc.)

### Q4: Is the PostgreSQL database currently being used at all?

**Partially ✗**:
- ✓ Service is running (docker-compose defines it)
- ✓ Schema is created during `uv run apps/cli init`
- ✓ Firecrawl's `nuq` schema is used (queue_scrape)
- ✗ Taboot's own schema (documents, extraction_windows, etc.) is **never written to**
- ✗ IngestionJob and ExtractionJob are only in-memory
- ✗ Document records are never created

---

## Recommendations

### Immediate (Critical Path)

1. **Implement `get_postgres_client()` factory**
   - Location: `packages/common/db_schema.py`
   - Return type: `AsyncContextManager[DocumentsClient]`
   - Use: `asyncpg` for async PostgreSQL access
   - Implement `fetch_documents()` and `count_documents()` methods

2. **Create DocumentStore adapter**
   - Location: `packages/ingest/document_store.py` (new)
   - Implement: `create_document()`, `update_extraction_state()`
   - Follow the existing adapter pattern (WebReader, Normalizer, etc.)

3. **Wire DocumentStore into IngestWebUseCase**
   - Modify: `packages/core/use_cases/ingest_web.py`
   - Call `document_store.create_document()` in `_process_document()`
   - Calculate content_hash from normalized content

### Short-term (Data Integrity)

4. **Implement IngestionJob persistence**
   - Create methods: `save_ingestion_job()`, `update_ingestion_job_state()`
   - Call during job state transitions in IngestWebUseCase

5. **Implement ExtractionJob management**
   - Create methods: `create_extraction_job()`, `update_extraction_job_state()`
   - Call during extraction pipeline progress

6. **Add integration tests**
   - Verify documents are created during ingestion
   - Verify `GET /documents` returns created documents
   - Verify filtering and pagination work correctly

### Technical Debt

7. **Consider ORM vs. raw SQL**
   - Current approach: raw SQL (via psycopg2)
   - Alternative: SQLAlchemy async ORM
   - Trade-off: Type safety vs. boilerplate

8. **Add database migration tool**
   - Current: Manual schema file execution
   - Consider: Alembic for version control and migrations

---

## Summary Table

| Component | Status | Files | Notes |
|-----------|--------|-------|-------|
| PostgreSQL service | ✓ Ready | docker-compose.yaml | Healthy checks, volume persistence |
| Schema definition | ✓ Complete | postgresql-schema.sql | 4 tables, 12+ indexes, all constraints |
| Configuration | ✓ Complete | config/__init__.py | Connection string generation |
| Schema creation | ✓ Complete | db_schema.py | Async-wrapped, transaction handling |
| DocumentStore client | ✗ Missing | db_schema.py | `get_postgres_client()` not implemented |
| Document creation | ✗ Missing | ingest_web.py | Never called during ingestion |
| Job persistence | ✗ Missing | db_schema.py | IngestionJob/ExtractionJob never saved |
| List documents endpoint | ✗ Broken | routes/documents.py | Import error at runtime |
| List documents CLI | ✗ Broken | commands/list_documents.py | Import error at runtime |

---

## Conclusion

Taboot has **excellent infrastructure design** for PostgreSQL with a well-thought-out schema, proper configuration, and initialization logic. However, there is a **critical implementation gap**: the actual document store client is missing, making the document listing endpoints non-functional.

The fix is straightforward:
1. Implement `get_postgres_client()` with async PostgreSQL access
2. Create a DocumentStore adapter
3. Wire it into the ingestion pipeline
4. Add persistence for jobs

This is a **high-priority fix** to make the platform actually store and retrieve documents from PostgreSQL.
