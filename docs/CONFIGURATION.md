# Configuration Reference

This guide expands on `.env.example` and `docker-compose.yaml`, outlining how to supply
credentials, tune service endpoints, and prepare the stack for local or remote
deployments.

---

## 1. Environment Files

1. Copy `.env.example` to `.env` at the repository root.
2. Edit `.env` before starting Docker services or running CLI/API workflows.

```bash
cp .env.example .env
$EDITOR .env
```

`uv run` will automatically read the file when invoked as
`uv run --env-file .env ...`. For team development, keep machine-specific values in
`.env.local` and source it before running commands.

---

## 2. Core Service Variables

### Firecrawl Orchestrator & Workers

| Key | Default | Description |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Bind address for the Firecrawl API container |
| `PORT` | `4200` | External HTTP port exposed by the API container |
| `INTERNAL_PORT` | `4200` | Internal port used by workers to reach the API |
| `WORKER_PORT` | `4210` | Queue worker metrics/debug port |
| `FIRECRAWL_API_URL` | `http://taboot-crawler:3002` | Base URL used by adapters |
| `FIRECRAWL_API_KEY` | `changeme` | Rotate per environment |
| `NUM_WORKERS_PER_QUEUE` | `16` | Worker processes per queue |
| `WORKER_CONCURRENCY` | `8` | Max concurrent jobs per worker |
| `SCRAPE_CONCURRENCY` | `8` | Browser concurrency per worker |
| `RETRY_DELAY` | `1000` | Delay (ms) before retry scheduling |
| `MAX_RETRIES` | `1` | Transient retry count |
| `BULL_AUTH_KEY` | `@` | Queue auth token (match Redis config) |
| `MAX_CPU` / `MAX_RAM` | `1.0` | Docker resource guardrails for workers |

### Postgres Metadata Store

| Key | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER` | `taboot` | Database user consumed by Firecrawl |
| `POSTGRES_PASSWORD` | `changeme` | Rotate in prod and update secrets |
| `POSTGRES_DB` | `taboot` | Application database |
| `POSTGRES_PORT` | `4201` | Host port mapped to container |
| `NUQ_DATABASE_URL` | derived | Full DSN used by queue services |

### Search & External AI Integrations

| Key | Default | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Required only when routing to OpenAI |
| `MODEL_NAME` | `gpt-4-turbo` | Default OpenAI model id |
| `SEARXNG_ENDPOINT` | `https://s.tootie.tv` | Metasearch endpoint |
| `SEARXNG_ENGINES` | `google,bing,duckduckgo,startpage,yandex` | Enabled engines |
| `SEARXNG_CATEGORIES` | `general,images,videos,news,map,music,science` | Query scopes |
| `HF_TOKEN` | empty | HuggingFace hub token for private models |

### Playwright Microservice

| Key | Default | Description |
| --- | --- | --- |
| `PLAYWRIGHT_PORT` | `4211` | Host port mapped to the scraping service |
| `PLAYWRIGHT_MICROSERVICE_URL` | `http://taboot-playwright:3000/scrape` | Internal base URL |

### Redis

| Key | Default | Description |
| --- | --- | --- |
| `REDIS_PORT` | `4202` | Host port for Redis CLI access |
| `REDIS_URL` | `redis://taboot-cache:6379` | Primary connection string |
| `REDIS_RATE_LIMIT_URL` | `redis://taboot-cache:6379` | Bucket store for throttling |

### Qdrant Vector Store

| Key | Default | Description |
| --- | --- | --- |
| `QDRANT_HTTP_PORT` | `4203` | Host port forwarded to 6333 inside container |
| `QDRANT_GRPC_PORT` | `4204` | Host port forwarded to 6334 inside container |
| `QDRANT_URL` | `http://taboot-vectors:6333` | In-cluster HTTP endpoint |
| `QDRANT_LOG_LEVEL` | `INFO` | Optional runtime logging level |

### Neo4j Graph

| Key | Default | Description |
| --- | --- | --- |
| `NEO4J_USER` | `neo4j` | Admin username |
| `NEO4J_PASSWORD` | `changeme` | Rotate immediately in non-local envs |
| `NEO4J_DB` | `neo4j` | Default database name |
| `NEO4J_HTTP_PORT` | `4205` | Host port mapped to browser/UI |
| `NEO4J_BOLT_PORT` | `4206` | Host port mapped to Bolt driver |
| `NEO4J_URI` | `bolt://taboot-graph:7687` | Driver URI used by adapters |

### Text Embeddings Inference (TEI)

| Key | Default | Description |
| --- | --- | --- |
| `TEI_HTTP_PORT` | `4207` | Host port for embedding service |
| `TEI_EMBEDDING_URL` | `http://taboot-embed:80` | In-cluster endpoint |
| `TEI_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-0.6B` | Model ID pulled at runtime |

### SentenceTransformers Reranker

| Key | Default | Description |
| --- | --- | --- |
| `RERANKER_HTTP_PORT` | `4208` | Host port exposed by the reranker service |
| `RERANKER_URL` | `http://taboot-rerank:8000` | In-cluster endpoint |
| `RERANKER_MODEL` | `Qwen/Qwen3-Reranker-0.6B` | Cross-encoder loaded via `sentence-transformers` |
| `RERANKER_BATCH_SIZE` | `16` | Pair scoring batch size |
| `RERANKER_DEVICE` | `auto` | Set to `cuda` or `cpu`; `auto` picks CUDA when available |

If you are pulling private or gated models, set `HF_TOKEN` in `.env` so the container
can authenticate with Hugging Face when downloading weights.

The worker image defaults to `uv run apps/cli worker start`. Override the service
command in `docker-compose.yaml` if you wire your own orchestration entrypoint (see
`docker/worker/Dockerfile`).

### Ollama

| Key | Default | Description |
| --- | --- | --- |
| `OLLAMA_PORT` | `4214` | Host port exposed by Ollama |
| `OLLAMA_FLASH_ATTENTION` | `true` | GPU optimization toggle |
| `OLLAMA_KEEP_ALIVE` | `30m` | Keep idle models in memory |
| `OLLAMA_USE_MMAP` | `true` | Memory-mapping for faster load |
| `OLLAMA_MAX_QUEUE` | `20000` | Max pending requests |

### Logging & Miscellaneous

| Key | Default | Description |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Global logging threshold for apps |
| `FASTTEXT_HOME` | `.cache/fasttext` | Local cache path |
| `LLAMACRAWL_API_URL` | `http://localhost:4209` | API base URL for clients |

---

## 3. Data Source Credentials

All third-party integrations should be injected via environment variables or a secrets
manager. Fields marked “optional” can be omitted if the source is unused.

| Integration | Keys | Notes |
| --- | --- | --- |
| GitHub | `GITHUB_TOKEN` | Repo access token with `repo` + `read:discussion` |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | Script app credentials |
| Gmail | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN` | Run the OAuth desktop flow to populate these values |
| YouTube | `YOUTUBE_API_KEY` | API key for channel/video ingestion |
| Elasticsearch | `ELASTICSEARCH_URL`, `ELASTICSEARCH_API_KEY` | Create a read-only API key; username/password not required |
| Unifi | `UNIFI_API_TOKEN` (preferred) or `UNIFI_USERNAME` / `UNIFI_PASSWORD` | Use scoped, read-only tokens |
| Tailscale | `TAILSCALE_API_KEY` | Rotate quarterly |

Paths to remote Docker Compose files, SWAG configurations, or other filesystem
artifacts should be kept in `config.yaml` rather than exported as environment
variables. That YAML file can describe multiple remote hosts and per-source mount
points without leaking absolute paths into `.env`.

Never commit populated credentials. For production, mount secrets via your orchestrator
or leverage a vault provider.

---

## 4. Docker Compose Configuration

`docker-compose.yaml` defines the baseline stack: Qdrant, Neo4j, Redis, TEI services,
SentenceTransformers reranker, the unified app container (API + MCP + Web), the
extraction worker, Ollama, Firecrawl, and Playwright. Key settings to review:

- **GPU usage**: GPU-capable services (`taboot-vectors`, `taboot-embed`, `taboot-rerank`,
  `taboot-ollama`) inherit the `x-gpu-deploy` profile and request one NVIDIA device.
  Update `NVIDIA_VISIBLE_DEVICES` / `CUDA_VISIBLE_DEVICES` under the `x-gpu-env`
  anchor if you want to target a different GPU index or run CPU-only.
- **Volume mounts**: Persistent volumes (`taboot-vectors`, `taboot-embed`, `taboot-rerank`,
  `taboot-graph_*`, `taboot-cache`, `taboot-ollama`) retain data between restarts.
  Map host directories if you need external backups or snapshots.
- **Ports**: Host ports default to the values listed in `.env.example`. Override them in
  `.env` when running alongside existing services.
- **Health checks**: Each service includes a readiness probe. Keep these enabled to
  ensure downstream dependencies wait for readiness.
- **Overrides**: Layer additional configuration with
  `docker compose -f docker-compose.yaml -f docker/overrides/<env>.yaml up -d` to
  customize resources, GPU assignment, or mounts without editing the base file.

When targeting remote hosts, couple Compose with SSH tunnels or set up remote Docker
contexts, and keep hostname-specific settings in `config.yaml`.

---

## 5. CLI Access

The Typer-based CLI exposes a root command named `llama`. Until it is packaged as a
Standalone executable, invoke it via `uv`:

```bash
uv run apps/cli --help
```

To simplify local usage, define a shell alias:

```bash
alias llama='uv run apps/cli'
```

Future packaging work will publish an installable console script so `llama` resolves
without an alias. Document CLI workflows in a dedicated `apps/cli/README.md` once the
interface stabilizes.

---

## 6. Security Checklist

1. Rotate all `changeme` defaults (`FIRECRAWL_API_KEY`, `POSTGRES_PASSWORD`,
   `NEO4J_PASSWORD`, Redis auth) before exposing services beyond localhost.
2. Limit Docker network exposure—avoid publishing database ports to the public
   internet; prefer SSH tunnels or VPN access.
3. Keep `.env`, `.env.local`, and `config.yaml` out of version control.
4. Align with [apps/api/docs/SECURITY_MODEL.md](../apps/api/docs/SECURITY_MODEL.md)
   and [apps/api/docs/DATA_GOVERNANCE.md](../apps/api/docs/DATA_GOVERNANCE.md) for
   threat modeling and retention policies.

---

## 7. Troubleshooting

- **Neo4j authentication failures**: confirm `NEO4J_URI`/credentials match the running
  container and that passwords were updated inside Neo4j.
- **Qdrant 401 / connection errors**: verify `QDRANT_URL`, port mappings, and any API
  keys configured at the service level.
- **Firecrawl timeouts**: adjust `SCRAPE_CONCURRENCY`, `RETRY_DELAY`, or add domains to
  a slow-start list per [apps/api/docs/BACKPRESSURE_RATELIMITING.md](../apps/api/docs/BACKPRESSURE_RATELIMITING.md).
- **LLM inference issues**: ensure Ollama has pulled required models and that the GPU
  reservation is satisfied.

Continue expanding this reference as additional adapters, secrets, or deployment modes
are introduced.
