# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

> **⚠️ Single-User System**: Taboot is designed for a single developer. Breaking changes are acceptable and expected. No backwards compatibility guarantees. When in doubt, wipe and rebuild databases. No need for multiple environments, migration guides, or CONTRIBUTING/SECURITY docs.

Taboot is a **Doc-to-Graph RAG platform** built on LlamaIndex, Firecrawl, Neo4j, and Qdrant. It ingests from 11+ sources (web, GitHub, Reddit, YouTube, Gmail, Elasticsearch, Docker Compose, SWAG, Tailscale, Unifi, AI sessions), converts technical docs/configs into a Neo4j property graph, stores chunks in Qdrant, and answers questions via hybrid retrieval with strict source attribution.

**Key Technologies:**
- Python 3.11+ (managed via `uv`)
- Neo4j 5.23+ (graph database)
- Qdrant (vector database with GPU acceleration)
- LlamaIndex (retrieval framework)
- Firecrawl (web crawling)
- spaCy (NLP extraction) + Qwen3-4B-Instruct (Ollama LLM)
- TEI (embeddings and reranking)
- FastAPI + Typer CLI (app shells)

## Architecture: The Core Layering

**Strict Dependency Flow:** `apps → adapters → core`

**`packages/core/`** — Orchestration logic, domain models, and interfaces. **No framework dependencies.** This is the business truth. Core depends only on `packages/schemas` and `packages/common`.

**Adapter packages** — Pluggable implementations:
- `packages/ingest/` — Firecrawl readers, normalizer, chunker, deterministic code/table parsers
- `packages/extraction/` — Multi-tier extraction engine (Tier A: regex/JSON; Tier B: spaCy; Tier C: LLM windows)
- `packages/graph/` — Neo4j driver, Cypher builders, bulk UNWIND writers
- `packages/vector/` — Qdrant client, hybrid search, reranking
- `packages/retrieval/` — LlamaIndex indices, retrievers, and query engines
- `packages/schemas/` — Pydantic models and OpenAPI schemas
- `packages/common/` — Logging, config, tracing, utilities

**App shells** — Thin I/O layers:
- `apps/api/` — FastAPI service (HTTP)
- `apps/cli/` — Typer CLI (TUI)
- `apps/mcp/` — MCP server protocol adapter
- `apps/web/` — Next.js dashboard (optional)

**Key Rule:** Apps never contain business logic. If an app needs to do something, move it to an adapter or core as a new use-case.

## Data Pipeline Architecture

### Ingestion Plane
Firecrawl + Playwright → Normalizer (de-boilerplate) → Chunker → TEI embeddings (GPU) → Qdrant upserts. Structured sources (Docker Compose, SWAG, Tailscale, Unifi) parsed deterministically to nodes/edges.

### Extraction Plane (Async, Decoupled)

1. **Tier A (Deterministic):** Regex, YAML/JSON parsing, Aho-Corasick for known services/IPs/hosts. Target ≥50 pages/sec (CPU).
1. **Tier B (spaCy):** Entity ruler + dependency matchers + sentence classifier on `en_core_web_md` (or `trf` for prose). Target ≥200 sentences/sec (md).
1. **Tier C (LLM Windows):** Qwen3-4B-Instruct (Ollama) on ≤512-token windows, temperature 0, JSON schema, batched 8–16, Redis cache. Target median ≤250ms/window.

### Retrieval Plane (6-Stage)

1. Query embedding (TEI) → 2. Metadata filter (source, date) → 3. Vector search (Qdrant, top-k) → 4. Rerank (Qwen/Qwen3-Reranker-0.6B) → 5. Graph traversal (≤2 hops Neo4j) → 6. Synthesis (Qwen3-4B) with inline citations + source list.

## Neo4j Graph Model

**Nodes:** `Service{name}`, `Host{hostname}`, `IP{addr}`, `Proxy{name}`, `Endpoint{service,method,path}`, `Doc{doc_id}`

**Edges:** `DEPENDS_ON`, `ROUTES_TO{host,path,tls}`, `BINDS{port,protocol}`, `RUNS{container_id}`, `EXPOSES_ENDPOINT{auth}`, `MENTIONS{span,section,hash}`

**Constraints:** Unique indexes on `Service.name` and `Host.hostname`; composite index on `Endpoint(service, method, path)`.

## Essential Development Commands

### Setup (First Time)
```bash
uv sync                               # install Python workspace deps
pnpm install                          # JS dependencies (web + codegen)
cp .env.example .env && $EDITOR .env # configure endpoints
docker compose up -d                  # start all services
uv run apps/cli init                  # initialize schema and collections
```

### Development Loop
```bash
uv run apps/cli --help                              # list workflows
uv run apps/cli ingest web https://example.com     # ingest a single URL
uv run apps/cli extract pending                     # run extraction worker
uv run apps/cli query "your question"               # test retrieval

uv run pytest -m "not slow"                         # fast unit tests
uv run pytest -m "integration" --tb=short           # integration tests
uv run pytest --cov=packages packages/core          # coverage: core layer

uv run ruff check . && uv run ruff format .         # lint and format
uv run mypy .                                       # strict type-check
```

### Running Services
```bash
# Start API (via Docker only - no CLI entry point)
docker compose up taboot-app

# View logs
docker compose logs -f <service-name>

# Health check
docker compose ps
```

### Debugging
```bash
# Direct Neo4j queries
uv run apps/cli graph query "MATCH (s:Service) RETURN s LIMIT 10"

# View extraction metadata (Redis)
uv run apps/cli status

# Reprocess docs with new extractor
uv run apps/cli extract reprocess --since 7d
```

### Data Management

```bash
# Soft delete cleanup (production)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts

# Dry run to see what would be deleted
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --dry-run

# Custom retention period (e.g., 30 days)
pnpm tsx apps/web/scripts/cleanup-deleted-users.ts --retention-days=30
```

## Security

### CSRF Protection (Next.js Web App)

**Implementation:** Defense-in-depth approach using multiple layers:

1. **SameSite Cookies:** All authentication cookies use `sameSite: 'lax'` (configured in `packages-ts/auth/src/server.ts`)
2. **Double-Submit Cookie Pattern:** Custom CSRF middleware (`apps/web/lib/csrf.ts`) with:
   - HMAC-SHA256 signed tokens (32-byte random values)
   - Cookie: `__Host-taboot.csrf` (HttpOnly, Secure in production)
   - Header: `x-csrf-token` (must match cookie for state-changing requests)
3. **Origin/Referer Validation:** All POST/PUT/PATCH/DELETE requests validate origin matches host

**Protected Methods:** POST, PUT, PATCH, DELETE (all state-changing operations)

**Excluded Routes:** Read-only endpoints (e.g., `/api/auth/session`, `/api/health`, `/api/test`)

**Client-Side Integration:**
- `apps/web/lib/csrf-client.ts` — Automatic token inclusion from cookies
- `apps/web/lib/api.ts` — CsrfAwareAPIClient extends TabootAPIClient with automatic CSRF headers
- All mutation requests automatically include `x-csrf-token` header

**Middleware Flow:**
1. GET request → Set CSRF cookie + expose token in header
2. POST/PUT/PATCH/DELETE → Validate origin/referer → Validate token (cookie == header) → Allow or reject (403)

**Testing:**
- Unit tests: `apps/web/lib/__tests__/csrf.test.ts`
- Client tests: `apps/web/lib/__tests__/csrf-client.test.ts`
- Integration: CSRF validation in middleware

**Environment Variables:**
- `CSRF_SECRET` — HMAC signing key (defaults to `AUTH_SECRET` or development secret)

**OWASP Compliance:** Implements CSRF Prevention Cheat Sheet recommendations (double-submit cookie + origin validation)

### Data Integrity & Soft Delete

**Soft Delete Implementation:**

All user account deletions are soft deletes with full audit trail. This provides:
- **Recovery grace period** (90 days default)
- **GDPR compliance** (Article 30 audit requirements)
- **Protection against accidents** (bugs, misclicks)
- **Full audit trail** (who, when, why, from where)

**How It Works:**

1. **DELETE converted to UPDATE**: Prisma middleware intercepts `user.delete()` and sets `deletedAt` timestamp
2. **Automatic filtering**: Queries exclude soft-deleted records automatically (unless explicitly included)
3. **Audit logging**: Every deletion writes to `AuditLog` table with user, IP, timestamp, metadata
4. **Restoration**: Admin API endpoint to undo deletions within retention period
5. **Hard cleanup**: Scheduled job permanently removes users after 90 days

**Developer Usage:**

```typescript
// Soft delete (standard operation)
await prisma.user.delete({ where: { id: userId } });
// → Sets deletedAt, writes audit log, user still in DB

// Query active users (soft-deleted filtered automatically)
const users = await prisma.user.findMany();
// → Only returns users where deletedAt IS NULL

// Query deleted users explicitly
const deletedUsers = await prisma.user.findMany({
  where: { deletedAt: { not: null } }
});

// Restore deleted user (admin only)
await restoreUser(prisma, userId, currentUserId, {
  ipAddress: req.headers['x-forwarded-for'],
  userAgent: req.headers['user-agent'],
});
```

**Setting Context for Audit Trail:**

```typescript
import { setSoftDeleteContext, clearSoftDeleteContext } from '@taboot/db';

// In API middleware
const requestId = `req-${Date.now()}`;
setSoftDeleteContext(requestId, {
  userId: session.user.id,
  ipAddress: req.headers['x-forwarded-for'],
  userAgent: req.headers['user-agent'],
});

// Perform operations...

// Clean up after request
clearSoftDeleteContext(requestId);
```

**Important Notes:**

- Only User model has soft delete (Session/Account cascade naturally when User soft-deleted)
- Hard cascade deletes (`onDelete: Cascade`) still work but won't trigger if User is soft-deleted
- For testing, use raw SQL to bypass middleware: `prisma.$executeRaw`
- Audit logs are never deleted (permanent compliance record)

## Code Style & Conventions

- **Line length:** 100 characters (enforced by Ruff)
- **Python naming:** modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`
- **Adapters:** Name for their system (`neo4j_writer.py`, `qdrant_client.py`)
- **Type hints:** All functions annotated; mypy strict mode enabled; never use bare `any` type
- **Error handling:** Throw errors early and often; pre-production codebase, no fallbacks
- **Imports:** Ruff auto-formats; respect layering rules (no reverse imports)

## Testing

- Tests mirror `tests/<package>/<module>/test_*.py` structure
- Markers: `unit`, `integration`, `slow`, `gmail`, `github`, `reddit`, `elasticsearch`, `firecrawl`
- Target: ≥85% coverage in `packages/core` and extraction logic
- Full integration tests require Docker services healthy
- Lightweight fixtures over static payloads

## Framework Integration Notes

**LlamaIndex:** Used across multiple adapter packages:
- `packages/ingest/` — LlamaIndex readers (web, GitHub, Reddit, YouTube, Gmail, file formats)
- `packages/extraction/` — LLM adapters (`llama-index-llms-ollama`) for Tier C extraction
- `packages/vector/` — VectorStoreIndex integration with Qdrant
- `packages/graph/` — PropertyGraphIndex integration with Neo4j
- `packages/retrieval/` — Core retrieval functionality:
  - `context/` — Settings (TEI, Ollama LLM), prompts
  - `indices/` — Index management and configuration
  - `retrievers/` — Hybrid retrievers and reranking
  - `query_engines/` — Graph-augmented QA

**Core never imports `llama_index.*`.** This ensures core is framework-agnostic. Core uses direct imports from adapter packages (`packages.graph`, `packages.vector`, etc.) when needed in use-cases.

## Docker Services & GPU

All services in `docker-compose.yaml`:

| Service | Purpose | GPU |
|---------|---------|-----|
| `taboot-vectors` | Qdrant (HNSW indexing) | ✅ |
| `taboot-embed` | TEI embeddings (Qwen3-Embedding-0.6B) | ✅ |
| `taboot-rerank` | SentenceTransformers Qwen3 reranker | ✅ |
| `taboot-ollama` | Ollama LLM server (Qwen3-4B-Instruct) | ✅ |
| `taboot-graph` | Neo4j 5.23+ with APOC | ❌ |
| `taboot-cache` | Redis 7.2 (state, cursors, DLQ) | ❌ |
| `taboot-db` | PostgreSQL 16 (Firecrawl metadata) | ❌ |
| `taboot-playwright` | Playwright browser microservice | ❌ |
| `taboot-crawler` | Firecrawl v2 API | ❌ |
| `taboot-app` | Unified API (8000) + MCP + Next.js Web (3000) | ❌ |
| `taboot-worker` | Extraction worker (spaCy tiers + LLM windows) | ❌ |

**taboot-app Details:**
- Runs both FastAPI (port 8000) and Next.js web dashboard (port 3000)
- Managed via supervisord for process orchestration
- Includes Python (uv/FastAPI) and Node.js (pnpm/Next.js) runtimes
- Web app includes auth (Prisma), UI components (shadcn/ui), and dashboard

**GPU Notes:** Requires NVIDIA driver + `nvidia-container-toolkit`. Model downloads (Ollama, spaCy) happen on first run; pull sizes may exceed 20GB total.

## Configuration

Primary config via `.env` (copy from `.env.example`). Key variables align with `docker-compose.yaml` defaults:

```env
FIRECRAWL_API_URL=http://taboot-crawler:3002
REDIS_URL=redis://taboot-cache:6379
QDRANT_URL=http://taboot-vectors:6333
NEO4J_URI=bolt://taboot-graph:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
TEI_EMBEDDING_URL=http://taboot-embed:80
RERANKER_URL=http://taboot-rerank:8000
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B
RERANKER_BATCH_SIZE=16
RERANKER_DEVICE=auto
OLLAMA_PORT=11434
LLAMACRAWL_API_URL=http://localhost:8000
```

Per-source credentials (GitHub, Reddit, Gmail, Elasticsearch, Unifi, Tailscale) documented in `docs/`.

## Schema Management

**PostgreSQL:**
- Source of truth: `specs/001-taboot-rag-platform/contracts/postgresql-schema.sql`
- **Schema Isolation:** Uses PostgreSQL schemas for namespace separation
  - `rag` schema: All RAG platform tables (documents, document_content, extraction_windows, ingestion_jobs, extraction_jobs)
  - `auth` schema: All auth tables (managed by Prisma - User, Session, Account, Verification, TwoFactor, AuditLog)
  - Prevents table name collisions between Python (RAG) and TypeScript (auth) systems
  - Migration script: `todos/scripts/migrate-to-schema-namespaces.sql` (one-time migration from public schema)
- No automated migrations (Alembic removed)
- Version tracking via `schema_versions` table with SHA-256 checksums
- Version constant: `packages.common.db_schema.CURRENT_SCHEMA_VERSION`
- Schema created during `taboot init` via `packages.common.db_schema.create_schema()`
- Breaking changes OK: wipe and rebuild with `docker volume rm taboot-db`

**Schema Workflow:**

```bash
# 1. Check current version
uv run apps/cli schema version

# 2. Edit schema SQL file
vim specs/001-taboot-rag-platform/contracts/postgresql-schema.sql
# Update: -- THIS VERSION: X.Y.Z

# 3. Update version constant in code
vim packages/common/db_schema.py
# Update: CURRENT_SCHEMA_VERSION = "X.Y.Z"

# 4. Apply schema (automatic version tracking)
uv run apps/cli init

# 5. Verify version was applied
uv run apps/cli schema version
uv run apps/cli schema history

# 6. View version history
uv run apps/cli schema history --limit 20
```

**Version Tracking Details:**
- `schema_versions` table logs all schema changes with timestamp, user, checksum, and execution time
- Checksums detect manual schema modifications
- Re-running `init` with same version+checksum is safe (no-op)
- Re-running `init` with same version but different checksum logs warning and reapplies
- Failed schema applications recorded with status='failed'
- Version history available via `taboot schema history`

**Neo4j:**
- Constraints: `specs/001-taboot-rag-platform/contracts/neo4j-constraints.cypher`
- Applied idempotently during `taboot init`
- No versioning needed (idempotent CREATE IF NOT EXISTS)

**Qdrant:**
- Collections created on-demand during `taboot init`
- Config: `specs/001-taboot-rag-platform/contracts/qdrant-collection.json`
- Versioning via aliases (managed by application)

**Prisma (TypeScript/Next.js Auth):**
- Schema: `packages-ts/db/prisma/schema.prisma`
- Separate concern from Python RAG platform
- Manages: User, Session, Account, Verification, TwoFactor, AuditLog tables
- Migrations: `pnpm db:migrate` in packages-ts/db
- **Soft Delete:** User model implements soft delete with audit trail
  - `deletedAt` and `deletedBy` fields track deletion
  - DELETE operations converted to UPDATE via Prisma middleware
  - Queries automatically filter soft-deleted records
  - 90-day retention period before hard delete
  - Full audit trail in AuditLog table
  - Admin restoration via API endpoint
  - Cleanup script: `pnpm tsx apps/web/scripts/cleanup-deleted-users.ts`

## Performance Targets (RTX 4070)

- Tier A: ≥50 pages/sec (CPU)
- Tier B: ≥200 sentences/sec (md model) or ≥40 (transformer model)
- Tier C: median ≤250ms/window, p95 ≤750ms (batched 8–16)
- Neo4j: ≥20k edges/min with 2k-row UNWIND batches
- Qdrant: ≥5k vectors/sec (1024-dim, HNSW)

## Observability

- **Metrics:** windows/sec, tier hit ratios, LLM p95, cache hit-rate, DB throughput
- **Tracing:** Chain `doc_id → section → windows → triples → Neo4j txId`
- **Validation:** ~300 labeled windows with F1 guardrails; CI fails if F1 drops ≥2 points
- **Logging:** JSON structured via `python-json-logger`

## Security: Rate Limiting

The Next.js web application (`apps/web/`) implements **fail-closed rate limiting** to prevent abuse:

**Build-Time vs Runtime Behavior:**
- **Build time** (`NEXT_PHASE=phase-production-build`): Uses stub that allows all requests (for static analysis)
- **Runtime** (production/development): Requires Upstash Redis; throws error if not configured

**Configuration:**

```bash
# Required for production deployments with rate limiting
UPSTASH_REDIS_REST_URL="https://your-database.upstash.io"
UPSTASH_REDIS_REST_TOKEN="your-upstash-token-here"

# TRUST_PROXY: Only set to 'true' if behind verified reverse proxy
# Default: 'false' (secure - ignores X-Forwarded-For)
TRUST_PROXY="false"
```

**Rate Limits:**
- Password endpoints (`/api/auth/password/*`): 5 requests per 10 minutes
- General auth endpoints: 10 requests per 1 minute

**Security Principles:**
- **Fail-closed**: Missing Redis credentials at runtime → service throws error and refuses to start
- **No silent failures**: Clear error messages with configuration instructions
- **Build-time safety**: Only uses stub during `NEXT_PHASE=phase-production-build`
- **Runtime enforcement**: All rate limit check failures return 503 Service Unavailable (fail-closed)
- **IP spoofing protection**: X-Forwarded-For only trusted when TRUST_PROXY=true; IP format validated

**Implementation Files:**
- `apps/web/lib/rate-limit.ts` - Core rate limiting logic with fail-closed initialization

### Rate Limiting Behind Reverse Proxy

If deploying behind Cloudflare, nginx, or other reverse proxy:

1. **Set TRUST_PROXY=true** in production `.env`:

   ```bash
   TRUST_PROXY="true"
   ```

2. **Configure proxy to set X-Forwarded-For correctly:**

   **nginx:**

   ```nginx
   location / {
     proxy_pass http://localhost:3000;
     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
     proxy_set_header X-Real-IP $remote_addr;
     proxy_set_header Host $host;
   }
   ```

   **Cloudflare:**
   - Automatically sets X-Forwarded-For and CF-Connecting-IP headers
   - No additional configuration needed

   **AWS Application Load Balancer:**
   - Automatically sets X-Forwarded-For header
   - No additional configuration needed

3. **Verify configuration:**

   ```bash
   # Test that rate limiting uses real client IP, not proxy IP
   curl -v https://yourdomain.com/api/auth/sign-in \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"wrong"}'

   # Make 6 requests rapidly to trigger rate limit (5 req/10min limit)
   # Should see 503 Service Unavailable after 5th attempt (fail-closed)
   ```

**SECURITY WARNING:**
- Never set `TRUST_PROXY=true` if directly exposed to internet without reverse proxy
- Only use behind verified proxy infrastructure (Cloudflare, nginx, AWS ALB, etc.)
- When `TRUST_PROXY=false` (default), X-Forwarded-For headers are ignored to prevent IP spoofing
- IP addresses are validated (IPv4/IPv6 format) even when proxy is trusted
- `apps/web/lib/with-rate-limit.ts` - Higher-order function wrapper for route handlers

**Testing:**

```bash
# Run rate limiting tests
pnpm --filter @taboot/web test lib/rate-limit.test.ts
pnpm --filter @taboot/web test lib/with-rate-limit.test.ts
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| Services won't start | `docker compose ps` and `docker compose logs <service-name>` |
| GPU not detected | NVIDIA driver + `nvidia-container-toolkit` installed |
| Ollama model missing | First run auto-pulls Qwen3-4B; or `docker exec taboot-ollama ollama pull qwen3:4b` |
| Neo4j connection refused | Wait for healthcheck: `docker compose ps taboot-graph` |
| Tests fail | Ensure `docker compose ps` shows all services healthy before running integration tests |
| spaCy model missing | First run auto-downloads `en_core_web_md`; or manually `python -m spacy download en_core_web_md` |
| Rate limiting error on web app startup | Set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` in `.env` (see `.env.example`) |

## Commits & PRs

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Keep commits focused on a single concern
- Note executed test command in PR body
- Request reviewers for cross-layer work (core + adapters)
- Link related issues or docs
