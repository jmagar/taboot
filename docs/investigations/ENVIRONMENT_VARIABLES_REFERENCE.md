# Environment Variables Reference

Complete documentation of all environment variables used in Taboot, organized by concern and with validation rules.

---

## Table of Contents

1. [Authentication & Secrets](#authentication--secrets)
2. [Database Configuration](#database-configuration)
3. [Service URLs & Ports](#service-urls--ports)
4. [External API Credentials](#external-api-credentials)
5. [ML Model Configuration](#ml-model-configuration)
6. [Performance Tuning](#performance-tuning)
7. [Observability & Logging](#observability--logging)
8. [Docker & Build Configuration](#docker--build-configuration)

---

## Authentication & Secrets

### BETTER_AUTH_SECRET

**Status:** CRITICAL - Must be configured
**Type:** String (base64 or URL-safe base64)
**Length:** Minimum 32 characters (256 bits)
**Used By:** Next.js web app (TypeScript/better-auth)
**Fallback Chain:** BETTER_AUTH_SECRET → (Python fallback to AUTH_SECRET)

**Description:**
JWT signing secret for better-auth authentication library. Used to sign and verify session tokens on the frontend. Also used by Python API as fallback if AUTH_SECRET not set.

**How to Generate:**
```bash
# Option 1: URL-safe base64 (recommended)
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Option 2: Hex encoding
python -c 'import secrets; print(secrets.token_hex(32))'

# Option 3: OpenSSL
openssl rand -base64 32
```

**Validation Rules:**
- Must be exactly at least 32 characters
- Must contain high entropy (not all same character)
- Must NOT be: changeme, password, admin, secret, default
- Must NOT match pattern: `dev-*`, `test-*`

**Example:**
```env
BETTER_AUTH_SECRET=qHdPYaF/88J/g+Wz/T860GJYYQU548qv0NQH0f5Eh1o=
```

**Migration Notes:**
- Changing this value invalidates ALL existing sessions
- All users will be logged out and must re-authenticate
- Consider scheduling deployment during low-traffic period

### AUTH_SECRET

**Status:** CRITICAL - Or fallback to BETTER_AUTH_SECRET
**Type:** String (base64 or URL-safe base64)
**Length:** Minimum 32 characters (256 bits)
**Used By:** FastAPI Python API (JWT validation)
**Fallback Chain:** AUTH_SECRET → BETTER_AUTH_SECRET

**Description:**
JWT signing secret for Python API. Used to validate JWT tokens from Next.js frontend and sign API responses. Falls back to BETTER_AUTH_SECRET if not set.

**How to Generate:**
Same as BETTER_AUTH_SECRET - can be the same value.

**Validation Rules:**
- Same as BETTER_AUTH_SECRET
- Should match BETTER_AUTH_SECRET for single-secret systems

**Example:**
```env
AUTH_SECRET=qHdPYaF/88J/g+Wz/T860GJYYQU548qv0NQH0f5Eh1o=
```

**Recommendation:**
For single-user development systems, set both to same value:
```env
BETTER_AUTH_SECRET=<random-secret>
AUTH_SECRET=<random-secret>
```

### CSRF_SECRET

**Status:** OPTIONAL (defaults to AUTH_SECRET, then hardcoded dev secret)
**Type:** String
**Length:** Minimum 32 characters recommended
**Used By:** Next.js web app (CSRF protection middleware)
**Fallback Chain:** CSRF_SECRET → AUTH_SECRET → `'development-csrf-secret'` (HARDCODED ⚠️)

**Description:**
Secret for CSRF token signing via HMAC-SHA256. Protects against cross-site request forgery attacks.

**Validation Rules:**
- Should be 32+ characters for production
- MUST NOT be hardcoded default in production

**Example:**
```env
CSRF_SECRET=qHdPYaF/88J/g+Wz/T860GJYYQU548qv0NQH0f5Eh1o=
```

**⚠️ WARNING:**
If AUTH_SECRET not set AND CSRF_SECRET not set, will use hardcoded `'development-csrf-secret'` - INSECURE for production.

---

## Database Configuration

### POSTGRES_USER

**Status:** OPTIONAL
**Default:** `taboot`
**Type:** String (alphanumeric, underscore)
**Used By:** PostgreSQL container, Python API, Next.js app

**Description:**
PostgreSQL username for application access.

**Example:**
```env
POSTGRES_USER=taboot
```

### POSTGRES_PASSWORD

**Status:** CRITICAL
**Default:** `changeme` (INSECURE - DO NOT USE IN PRODUCTION)
**Type:** String
**Length:** Minimum 12 characters recommended
**Used By:** PostgreSQL container, Python API, Next.js app

**Description:**
PostgreSQL database password. Used in DATABASE_URL connection string.

**Requirements:**
- Minimum 12 characters
- Should contain: uppercase, lowercase, numbers, special characters
- Must NOT be: password, changeme, admin, test, default

**How to Generate:**
```bash
python -c 'import secrets; print(secrets.token_urlsafe(16))'
```

**Example:**
```env
POSTGRES_PASSWORD=zFp9g998BFwHuvsB9DcjerW8DyuNMQv2
```

### POSTGRES_DB

**Status:** OPTIONAL
**Default:** `taboot`
**Type:** String
**Used By:** PostgreSQL container, Python API, Next.js app

**Description:**
PostgreSQL database name to create/use.

**Example:**
```env
POSTGRES_DB=taboot
```

### POSTGRES_HOST

**Status:** OPTIONAL
**Default:** `taboot-db` (Docker service name)
**Type:** String (hostname or IP)
**Used By:** Python API, Next.js app

**Description:**
PostgreSQL hostname for connection. In Docker network is `taboot-db`. On host is `localhost`.

**Example (Docker):**
```env
POSTGRES_HOST=taboot-db
```

**Example (Host Development):**
```env
POSTGRES_HOST=localhost
```

### POSTGRES_PORT

**Status:** OPTIONAL
**Default:** `4201`
**Type:** Integer (1-65535)
**Used By:** Python API, Next.js app

**Description:**
PostgreSQL server port.

**Example:**
```env
POSTGRES_PORT=4201
```

### DATABASE_URL

**Status:** RECOMMENDED (used by Prisma)
**Default:** Constructed from POSTGRES_* variables
**Type:** URL (postgresql://user:pass@host:port/db)
**Used By:** Next.js app (Prisma), Python ingestion

**Description:**
PostgreSQL connection string. Prisma's primary configuration method.

**Format:**
```
postgresql://user:password@host:port/database?schema=auth
```

**Example:**
```env
DATABASE_URL="postgresql://taboot:zFp9g998BFwHuvsB9DcjerW8DyuNMQv2@taboot-db:5432/taboot?schema=auth"
```

**Schema Parameter:**
- `schema=auth` - Routes queries to `auth` schema in PostgreSQL
- Prevents table name collisions with Python's `rag` schema

### NEO4J_USER

**Status:** OPTIONAL
**Default:** `neo4j`
**Type:** String
**Used By:** Python API, Neo4j container

**Description:**
Neo4j database admin username.

**Example:**
```env
NEO4J_USER=neo4j
```

### NEO4J_PASSWORD

**Status:** CRITICAL
**Default:** `changeme` (INSECURE - DO NOT USE IN PRODUCTION)
**Type:** String
**Length:** Minimum 12 characters recommended
**Used By:** Python API, Neo4j container

**Description:**
Neo4j database password. Required for bolt:// connection.

**Requirements:**
- Minimum 12 characters (Neo4j enforces minimum)
- Should contain: uppercase, lowercase, numbers, special characters
- Must NOT be weak defaults

**How to Generate:**
```bash
python -c 'import secrets; print(secrets.token_urlsafe(16))'
```

**Example:**
```env
NEO4J_PASSWORD=AVqx64QRKmogToi2CykgYqA2ZkbbAGja
```

### NEO4J_DB

**Status:** OPTIONAL
**Default:** `neo4j`
**Type:** String
**Used By:** Python API

**Description:**
Neo4j database name (default database within Neo4j instance).

**Example:**
```env
NEO4J_DB=neo4j
```

### NEO4J_URI

**Status:** OPTIONAL
**Default:** `bolt://taboot-graph:7687` (Docker)
**Type:** URL (bolt://host:port)
**Used By:** Python API

**Description:**
Neo4j Bolt protocol connection URL. Rewritten to localhost:4206 when running on host.

**Example (Docker):**
```env
NEO4J_URI=bolt://taboot-graph:7687
```

**Example (Host Development):**
```env
NEO4J_URI=bolt://localhost:4206
```

---

## Service URLs & Ports

### REDIS_URL

**Status:** CRITICAL
**Default:** `redis://taboot-cache:6379`
**Type:** URL (redis://[host]:[port]/[db])
**Used By:** Python API, Next.js rate limiter, Firecrawl

**Description:**
Redis connection URL for caching, rate limiting, and task queues.

**Example (Docker):**
```env
REDIS_URL=redis://taboot-cache:6379
```

**Example (Host Development):**
```env
REDIS_URL=redis://localhost:4202
```

**Example (With Auth):**
```env
REDIS_URL=redis://:password@host:6379/0
```

### QDRANT_URL

**Status:** CRITICAL
**Default:** `http://taboot-vectors:6333`
**Type:** URL (http://host:port)
**Used By:** Python API (vector search)

**Description:**
Qdrant vector database HTTP endpoint.

**Example (Docker):**
```env
QDRANT_URL=http://taboot-vectors:6333
```

**Example (Host Development):**
```env
QDRANT_URL=http://localhost:4203
```

### NEO4J_URI

See [Database Configuration](#neo4j_uri) section above.

### FIRECRAWL_API_URL

**Status:** CRITICAL
**Default:** `http://taboot-crawler:3002`
**Type:** URL (http://host:port)
**Used By:** Python ingest service

**Description:**
Firecrawl web scraping service endpoint.

**Example (Docker):**
```env
FIRECRAWL_API_URL=http://taboot-crawler:3002
```

**Example (Host Development):**
```env
FIRECRAWL_API_URL=http://localhost:4200
```

### FIRECRAWL_API_KEY

**Status:** CRITICAL
**Default:** `changeme`
**Type:** String (hex or alphanumeric)
**Used By:** Firecrawl service

**Description:**
API key for Firecrawl service authentication (local, docker-compose managed).

**How to Generate:**
```bash
python -c 'import secrets; print(secrets.token_hex(16))'
```

**Example:**
```env
FIRECRAWL_API_KEY=8sHRjdGvk6wL58zP2QnM9N3h4ZBYa5M3
```

### TEI_EMBEDDING_URL

**Status:** CRITICAL
**Default:** `http://taboot-embed:80`
**Type:** URL (http://host:port)
**Used By:** Python ingest/extraction

**Description:**
Text Embeddings Inference (TEI) service endpoint for generating embeddings.

**Example (Docker):**
```env
TEI_EMBEDDING_URL=http://taboot-embed:80
```

**Example (Host Development):**
```env
TEI_EMBEDDING_URL=http://localhost:4207
```

### RERANKER_URL

**Status:** CRITICAL
**Default:** `http://taboot-rerank:8000`
**Type:** URL (http://host:port)
**Used By:** Python retrieval service

**Description:**
Reranker service endpoint (SentenceTransformers cross-encoder).

**Example (Docker):**
```env
RERANKER_URL=http://taboot-rerank:8000
```

**Example (Host Development):**
```env
RERANKER_URL=http://localhost:4208
```

### PLAYWRIGHT_MICROSERVICE_URL

**Status:** REQUIRED
**Default:** `http://taboot-playwright:3000/scrape`
**Type:** URL
**Used By:** Firecrawl service

**Description:**
Playwright browser microservice endpoint for dynamic rendering.

**Example (Docker):**
```env
PLAYWRIGHT_MICROSERVICE_URL=http://taboot-playwright:3000/scrape
```

---

## External API Credentials

### OPENAI_API_KEY

**Status:** REQUIRED (for Firecrawl extraction)
**Type:** String (sk-proj-*)
**Used By:** Firecrawl service (extraction)

**Description:**
OpenAI API key for GPT model access (used by Firecrawl for content extraction).

**How to Get:**
1. Go to: https://platform.openai.com/account/api-keys
2. Create new secret key
3. Copy full key (starts with `sk-proj-`)

**Example:**
```env
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Validation Rules:**
- Must start with `sk-proj-`
- Length typically 80+ characters
- Must NOT be placeholder like `sk-xxx...`

**Cost:** Usage-based (Firecrawl uses latest available GPT model for extraction)

### HF_TOKEN

**Status:** REQUIRED (for TEI/model downloads)
**Type:** String (hf_*)
**Used By:** TEI container, Reranker, Python models

**Description:**
HuggingFace API token for downloading models and tokenizers.

**How to Get:**
1. Go to: https://huggingface.co/settings/tokens
2. Create new token (full access recommended)
3. Copy token (starts with `hf_`)

**Example:**
```env
HF_TOKEN=hf_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Validation Rules:**
- Must start with `hf_`
- Typically 30+ characters
- Must NOT be placeholder

**Models Downloaded:**
- Qwen3-Embedding-0.6B (TEI)
- Qwen3-Reranker-0.6B (Reranker)
- en_core_web_md (spaCy)

### GITHUB_TOKEN

**Status:** OPTIONAL (required for GitHub ingestion)
**Type:** String (ghp_*)
**Used By:** Python ingest service

**Description:**
GitHub Personal Access Token for accessing GitHub APIs (repositories, discussions, etc).

**How to Get:**
1. Go to: https://github.com/settings/tokens
2. Create new fine-grained token
3. Permissions: `repository:read`, `discussion:read`
4. Expiration: 90 days recommended

**Example:**
```env
GITHUB_TOKEN=ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Validation Rules:**
- Must start with `ghp_` (classic) or `github_pat_` (fine-grained)
- Typically 36+ characters for classic tokens

### REDDIT_CLIENT_ID

**Status:** OPTIONAL (required for Reddit ingestion)
**Type:** String
**Used By:** Python ingest service

**Description:**
Reddit OAuth application ID for accessing Reddit APIs.

**How to Get:**
1. Go to: https://www.reddit.com/prefs/apps
2. Create new app (type: "script")
3. Copy Client ID (shown under app name)

**Example:**
```env
REDDIT_CLIENT_ID=sB5I2MeHhv2HNyPyyznElw
```

### REDDIT_CLIENT_SECRET

**Status:** OPTIONAL (required for Reddit ingestion)
**Type:** String
**Used By:** Python ingest service

**Description:**
Reddit OAuth application secret for accessing Reddit APIs.

**How to Get:**
1. Same as REDDIT_CLIENT_ID
2. Click "show" next to secret
3. Copy full secret string

**Example:**
```env
REDDIT_CLIENT_SECRET=PjKYfxfed7iqnY3bdRplMcxNE8EycA
```

### GOOGLE_CLIENT_ID

**Status:** OPTIONAL (required for Gmail ingestion)
**Type:** String (*.apps.googleusercontent.com)
**Used By:** Python ingest service

**Description:**
Google OAuth 2.0 Client ID for Gmail API access.

**How to Get:**
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID (Desktop app)
3. Copy Client ID

**Example:**
```env
GOOGLE_CLIENT_ID=123456789012-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.apps.googleusercontent.com
```

### GOOGLE_CLIENT_SECRET

**Status:** OPTIONAL (required for Gmail ingestion)
**Type:** String (GOCSPX-*)
**Used By:** Python ingest service

**Description:**
Google OAuth 2.0 Client Secret for Gmail API access.

**How to Get:**
1. Same as GOOGLE_CLIENT_ID
2. Click "show" next to secret
3. Copy full secret string

**Example:**
```env
GOOGLE_CLIENT_SECRET=GOCSPX-XXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### GOOGLE_OAUTH_REFRESH_TOKEN

**Status:** OPTIONAL (required for Gmail ingestion)
**Type:** String (1//*)
**Used By:** Python ingest service

**Description:**
Google OAuth 2.0 refresh token for persistent Gmail API access.

**How to Get:**
1. Run OAuth flow with GOOGLE_CLIENT_ID/SECRET
2. Grant permissions for Gmail API
3. Store returned refresh token

**Example:**
```env
GOOGLE_OAUTH_REFRESH_TOKEN=1//XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### TAILSCALE_API_KEY

**Status:** OPTIONAL (required for Tailscale ingestion)
**Type:** String (tskey-api-*)
**Used By:** Python ingest service

**Description:**
Tailscale Tailnet Admin API key for accessing network configuration.

**How to Get:**
1. Go to: https://login.tailscale.com/admin/settings/keys
2. Create new API key
3. Copy full key

**Example:**
```env
TAILSCALE_API_KEY=tskey-api-ki8UXDQgzf11CNTRL-MCSPVGCbG2Sqq9i7Gz5UwRsnFQvHoSasC
```

### ELASTICSEARCH_URL

**Status:** OPTIONAL (required for Elasticsearch ingestion)
**Type:** URL (http://host:port)
**Used By:** Python ingest service

**Description:**
Elasticsearch cluster endpoint for searching and indexing documents.

**Example:**
```env
ELASTICSEARCH_URL=http://100.75.111.118:9200
```

### ELASTICSEARCH_API_KEY

**Status:** OPTIONAL (required for Elasticsearch auth)
**Type:** String
**Used By:** Python ingest service

**Description:**
Elasticsearch API key for authentication (if not using basic auth in URL).

**Example:**
```env
ELASTICSEARCH_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### UNIFI_USERNAME

**Status:** OPTIONAL (required for UniFi ingestion)
**Type:** String
**Default:** `api`
**Used By:** Python ingest service

**Description:**
UniFi Network Application API user username.

**Example:**
```env
UNIFI_USERNAME=api
```

### UNIFI_PASSWORD

**Status:** OPTIONAL (required for UniFi ingestion)
**Type:** String
**Used By:** Python ingest service

**Description:**
UniFi Network Application API user password.

**Example:**
```env
UNIFI_PASSWORD=CNU!vYGdtTqWNvJXo*gqBt8&fF79gRhR
```

### UNIFI_API_TOKEN

**Status:** OPTIONAL (alternative to UNIFI_PASSWORD)
**Type:** String
**Used By:** Python ingest service

**Description:**
UniFi Network Application API token (alternative authentication method).

**Example:**
```env
UNIFI_API_TOKEN=<api-token>
```

### RESEND_API_KEY

**Status:** OPTIONAL (required for email notifications)
**Type:** String (re_*)
**Used By:** Next.js web app

**Description:**
Resend email service API key for sending transactional emails.

**How to Get:**
1. Go to: https://resend.com/api-keys
2. Create new API key
3. Copy full key (starts with `re_`)

**Example:**
```env
RESEND_API_KEY=re_GZZ2Xjqv_2j63eA1p7PkQh49ur9724M5d
```

---

## ML Model Configuration

### TEI_EMBEDDING_MODEL

**Status:** OPTIONAL
**Default:** `Qwen/Qwen3-Embedding-0.6B`
**Type:** String (HuggingFace model ID)
**Used By:** TEI container

**Description:**
HuggingFace model ID for embeddings. Used by Text Embeddings Inference.

**Supported Models:**
- `Qwen/Qwen3-Embedding-0.6B` (recommended, 768-dim)
- `BAAI/bge-base-en-v1.5` (768-dim)
- `BAAI/bge-small-en-v1.5` (384-dim, faster)

**Example:**
```env
TEI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
```

### RERANKER_MODEL

**Status:** OPTIONAL
**Default:** `Qwen/Qwen3-Reranker-0.6B`
**Type:** String (HuggingFace model ID)
**Used By:** Reranker container

**Description:**
HuggingFace model ID for reranking retrieved documents.

**Supported Models:**
- `Qwen/Qwen3-Reranker-0.6B` (recommended)
- `BAAI/bge-reranker-base`
- `cross-encoder/qnli-distilroberta-base`

**Example:**
```env
RERANKER_MODEL=Qwen/Qwen3-Reranker-0.6B
```

### RERANKER_BATCH_SIZE

**Status:** OPTIONAL
**Default:** `16`
**Type:** Integer (1-128)
**Used By:** Reranker container

**Description:**
Number of document pairs to rerank in parallel. Higher = faster but more memory.

**Recommended Values:**
- GPU with 8GB VRAM: 16
- GPU with 16GB VRAM: 32
- GPU with 24GB VRAM: 64
- CPU only: 4-8

**Example:**
```env
RERANKER_BATCH_SIZE=16
```

### RERANKER_DEVICE

**Status:** OPTIONAL
**Default:** `auto`
**Type:** String (auto|cuda|cpu)
**Used By:** Reranker container

**Description:**
Device for model inference. `auto` detects GPU automatically.

**Options:**
- `auto` - Auto-detect GPU, fallback to CPU
- `cuda` - Force GPU (fails if no CUDA available)
- `cpu` - Force CPU only

**Example:**
```env
RERANKER_DEVICE=auto
```

### OLLAMA_FLASH_ATTENTION

**Status:** OPTIONAL
**Default:** `true`
**Type:** Boolean (true|false)
**Used By:** Ollama container

**Description:**
Enable flash attention optimization for faster inference on compatible GPUs.

**Example:**
```env
OLLAMA_FLASH_ATTENTION=true
```

### OLLAMA_KEEP_ALIVE

**Status:** OPTIONAL
**Default:** `30m`
**Type:** Duration string (30m, 1h, etc)
**Used By:** Ollama container

**Description:**
How long to keep model in memory before unloading.

**Example:**
```env
OLLAMA_KEEP_ALIVE=30m
```

### OLLAMA_USE_MMAP

**Status:** OPTIONAL
**Default:** `true`
**Type:** Boolean (true|false)
**Used By:** Ollama container

**Description:**
Use memory-mapped file I/O for faster model loading.

**Example:**
```env
OLLAMA_USE_MMAP=true
```

---

## Performance Tuning

### EMBEDDING_BATCH_SIZE

**Status:** OPTIONAL
**Default:** `64`
**Type:** Integer (multiple of 8)
**Used By:** Python ingest service

**Description:**
Batch size for TEI embedding requests. Larger = faster but more memory/latency.

**Constraints:**
- Must be multiple of 8
- Maximum constrained by TEI_MAX_BATCH_TOKENS

**Recommended:**
- Development: 32-64
- Production: 64-128

**Example:**
```env
EMBEDDING_BATCH_SIZE=64
```

### QDRANT_UPSERT_BATCH_SIZE

**Status:** OPTIONAL
**Default:** `200`
**Type:** Integer
**Used By:** Python ingest service

**Description:**
Batch size for Qdrant vector upserts.

**Example:**
```env
QDRANT_UPSERT_BATCH_SIZE=200
```

### NEO4J_MAX_POOL_SIZE

**Status:** OPTIONAL
**Default:** `50`
**Type:** Integer
**Used By:** Python API

**Description:**
Maximum Neo4j connection pool size.

**Recommendation:**
- Small instance: 20
- Medium instance: 50
- Large instance: 100+

**Example:**
```env
NEO4J_MAX_POOL_SIZE=50
```

### REDIS_MAX_CONNECTIONS

**Status:** OPTIONAL
**Default:** `100`
**Type:** Integer
**Used By:** Python API, rate limiter

**Description:**
Maximum Redis connection pool size.

**Example:**
```env
REDIS_MAX_CONNECTIONS=100
```

### POSTGRES_MAX_POOL_SIZE

**Status:** OPTIONAL
**Default:** `20`
**Type:** Integer
**Used By:** Python API, Next.js app

**Description:**
Maximum PostgreSQL connection pool size.

**Recommendation:**
- Development: 5-10
- Production: 20-50

**Example:**
```env
POSTGRES_MAX_POOL_SIZE=20
```

---

## Observability & Logging

### LOG_LEVEL

**Status:** OPTIONAL
**Default:** `INFO`
**Type:** String (DEBUG|INFO|WARNING|ERROR|CRITICAL)
**Used By:** All services

**Description:**
Logging level for all services.

**Example:**
```env
LOG_LEVEL=INFO
```

### NEXT_PUBLIC_SENTRY_DSN

**Status:** OPTIONAL
**Type:** URL (https://key@sentry.io/project)
**Used By:** Next.js web app

**Description:**
Sentry error tracking DSN for frontend error monitoring.

**How to Get:**
1. Go to: https://sentry.io
2. Create new project (Next.js)
3. Copy DSN

**Example:**
```env
NEXT_PUBLIC_SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
```

### SENTRY_AUTH_TOKEN

**Status:** OPTIONAL
**Type:** String
**Used By:** Next.js build process

**Description:**
Sentry API token for uploading source maps during build.

**Example:**
```env
SENTRY_AUTH_TOKEN=sntrys_eyJpYXQ...
```

### NEXT_PUBLIC_POSTHOG_KEY

**Status:** OPTIONAL
**Type:** String (phc_*)
**Used By:** Next.js web app

**Description:**
PostHog product analytics API key.

**How to Get:**
1. Go to: https://posthog.com
2. Create new project
3. Copy API key

**Example:**
```env
NEXT_PUBLIC_POSTHOG_KEY=phc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Docker & Build Configuration

### NODE_ENV

**Status:** OPTIONAL
**Default:** `production`
**Type:** String (development|production)
**Used By:** Next.js web app

**Description:**
Node.js environment mode.

**Example:**
```env
NODE_ENV=production
```

### NEXT_PHASE

**Status:** BUILD-TIME ONLY
**Type:** String
**Used By:** Next.js build system

**Description:**
Build phase indicator (used by Next.js internally during builds).

**Note:** This is automatically set during docker build, don't manually configure.

### DOCKER_BUILDKIT

**Status:** OPTIONAL
**Default:** `1`
**Type:** Boolean (0|1)
**Used By:** Docker build process

**Description:**
Enable BuildKit for faster, more efficient Docker builds.

**Example:**
```env
DOCKER_BUILDKIT=1
```

### COMPOSE_DOCKER_CLI_BUILD

**Status:** OPTIONAL
**Default:** `1`
**Type:** Boolean (0|1)
**Used By:** Docker Compose

**Description:**
Use Docker CLI for building instead of Docker engine.

**Example:**
```env
COMPOSE_DOCKER_CLI_BUILD=1
```

### NEXT_TELEMETRY_DISABLED

**Status:** OPTIONAL
**Default:** `1`
**Type:** Boolean (0|1)
**Used By:** Next.js runtime

**Description:**
Disable Next.js telemetry collection.

**Example:**
```env
NEXT_TELEMETRY_DISABLED=1
```

---

## Configuration Matrix

### By Component

| Component | Required Variables | Optional Variables |
|-----------|-------------------|-------------------|
| PostgreSQL | POSTGRES_PASSWORD | POSTGRES_USER, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT |
| Neo4j | NEO4J_PASSWORD | NEO4J_USER, NEO4J_DB, NEO4J_URI |
| Redis | REDIS_URL | REDIS_MAX_CONNECTIONS |
| Qdrant | QDRANT_URL | QDRANT_MAX_CONNECTIONS |
| Firecrawl | FIRECRAWL_API_KEY | FIRECRAWL_API_URL, NUM_WORKERS_PER_QUEUE |
| TEI | TEI_EMBEDDING_URL | TEI_EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE |
| Reranker | RERANKER_URL | RERANKER_MODEL, RERANKER_BATCH_SIZE, RERANKER_DEVICE |
| Auth | BETTER_AUTH_SECRET, AUTH_SECRET | CSRF_SECRET |
| Email | | RESEND_API_KEY |
| Analytics | | NEXT_PUBLIC_SENTRY_DSN, NEXT_PUBLIC_POSTHOG_KEY |

### By Environment

**Development:**
- All defaults acceptable except secrets
- Can use localhost for service URLs
- LOG_LEVEL=DEBUG recommended

**Production:**
- All CRITICAL variables must be set
- No defaults like "changeme" allowed
- Service URLs must use stable hostnames
- Enable Sentry and PostHog
- LOG_LEVEL=WARNING recommended

---

## Troubleshooting

### Service Connection Errors

**Error:** `Connection refused to taboot-graph:7687`
- **Cause:** Docker network issue or Neo4j not running
- **Fix:** Verify docker-compose.yaml, check `docker compose ps`, ensure Neo4j is healthy
- **Config:** Verify NEO4J_URI matches docker service name

**Error:** `Redis connection timeout`
- **Cause:** REDIS_URL points to wrong host/port
- **Fix:** Verify REDIS_URL, check docker-compose.yaml, ensure Redis is healthy

**Error:** `CORS error: origin not allowed`
- **Cause:** Frontend URL not in CORS_ALLOW_ORIGINS
- **Fix:** Add frontend URL to CORS_ALLOW_ORIGINS in .env

### Authentication Errors

**Error:** `Invalid JWT signature`
- **Cause:** BETTER_AUTH_SECRET or AUTH_SECRET mismatch between services
- **Fix:** Ensure both are set to same value

**Error:** `CSRF token validation failed`
- **Cause:** CSRF_SECRET not set or doesn't match AUTH_SECRET
- **Fix:** Set CSRF_SECRET=<same-value-as-AUTH_SECRET>

### Missing Features

**Feature doesn't work:** GitHub integration not ingesting repos
- **Check:** GITHUB_TOKEN is set and not expired
- **Fix:** Generate new token at https://github.com/settings/tokens

**Feature doesn't work:** Gmail integration not working
- **Check:** GOOGLE_OAUTH_REFRESH_TOKEN is set and not revoked
- **Fix:** Re-run OAuth flow to get fresh token

---

## Quick Setup Commands

```bash
# Generate all required secrets
python << 'EOF'
import secrets
secrets_needed = {
    'BETTER_AUTH_SECRET': 32,
    'NEO4J_PASSWORD': 16,
    'POSTGRES_PASSWORD': 16,
    'FIRECRAWL_API_KEY': 16,
}
for name, length in secrets_needed.items():
    print(f"{name}={secrets.token_urlsafe(length)}")
EOF

# Create new .env
cp .env.example .env
# [Edit with generated secrets above]

# Verify all critical vars are set
for var in BETTER_AUTH_SECRET NEO4J_PASSWORD POSTGRES_PASSWORD FIRECRAWL_API_KEY; do
    [ -z "$(grep "^$var=" .env)" ] && echo "❌ Missing: $var" || echo "✓ $var set"
done

# Start services with fresh secrets
docker compose down --remove-orphans
docker compose up -d
docker compose ps  # Verify all healthy
```

---

**Last Updated:** 2025-10-27
**Maintainer:** DevOps Team
**Next Review:** Monthly (or after adding new integrations)
