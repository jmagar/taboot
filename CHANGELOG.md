# Changelog

All notable changes to Taboot will be documented in this file.

**Note**: This is a single-user system with no backwards compatibility guarantees. Breaking changes are acceptable and expected. When in doubt, wipe and rebuild databases.

## [Unreleased]

## [0.4.0] - 2025-10-23

### Added

- **List Documents Feature (T163-T168)**: Complete implementation with filtering and pagination
  - Use case layer: `packages/core/use_cases/list_documents.py` with DocumentsClient protocol
  - CLI command: `taboot list documents` with rich table output
  - API endpoint: `GET /documents` with query parameter validation
  - Filters: source_type, extraction_state, limit, offset
  - Full test coverage (25 tests across use-case, CLI, and API layers)

- **Background Extraction Worker (T169-T170)**: Async job processing
  - Redis queue polling with configurable timeout
  - Graceful shutdown signal handling (SIGINT, SIGTERM)
  - Error handling with continuous operation on failures
  - Worker main entry point in `apps/worker/main.py`

- **Dead Letter Queue (DLQ) System (T171-T172)**: Retry policy with exponential backoff
  - `packages/common/dlq.py` with DeadLetterQueue class
  - Retry count tracking per job (max 3 retries by default)
  - Exponential backoff calculation: `base_delay * (2 ^ (retry_count - 1))`
  - Error metadata storage in Redis
  - Job retry eligibility checks

- **Performance Tuning Documentation (T173-T175)**: Comprehensive tuning guide
  - `docs/PERFORMANCE_TUNING.md` with batch size optimization guidance
  - Tier C LLM batching: 8-16 windows (configurable per GPU)
  - Neo4j write batching: 2,000-4,000 rows (configurable per heap size)
  - Qdrant upsert batching: 50-500 vectors (configurable per network latency)
  - Hardware-specific recommendations (RTX 4070, 3090, 3060)
  - Monitoring and benchmarking guidelines
  - Troubleshooting common performance issues

- **Enhanced Documentation (T176-T178)**: README and testing updates
  - Updated README.md with comprehensive Quick Start section
  - Example workflow with all major CLI commands
  - Key features list with technical details
  - Prerequisites and setup instructions (5-minute setup)

- Port mapping documentation in .env.example with inline comments
- Direct import pattern example in packages/core/README.md
- CHANGELOG.md for tracking project changes
- Project constitution (.specify/memory/constitution.md) defining core principles, tech stack, and development workflow
- Comprehensive testing documentation (docs/TESTING.md) covering unit/integration tests, markers, patterns, and troubleshooting
- LlamaIndex usage clarified across all adapter packages (ingest, extraction, vector, graph, retrieval)

### Changed

- Renamed project from LlamaCrawl to Taboot across all documentation and code
- Standardized all health check endpoints to `/health` (previously mixed `/health` and `/healthz`)
- Updated all environment variable references (`LLAMACRAWL_*→TABOOT_*`)
- Removed legacy `uv run taboot-api` entry point (API runs via Docker only)
- Docker service name changed from `taboot-api` to `taboot-app` in documentation
- Updated CLI command name from `llama` to `taboot`
- Removed abstract port pattern in favor of direct imports from adapter packages
- Added prominent single-user system philosophy notes to README.md and CLAUDE.md

### Fixed

- Fixed FIRECRAWL_PORT and FIRECRAWL_INTERNAL_PORT variable naming in .env files
- Fixed NUQ_DATABASE_URL to use ${POSTGRES_DB} variable instead of hardcoded 'postgres'
- Added TABOOT_HTTP_PORT environment variable
- Added port mapping comments (host→container) for all services in .env files
- Fixed Ollama model name in troubleshooting guide

## [0.3.0] - 2025-10-20

Initial taboot release with complete documentation audit and naming update.
